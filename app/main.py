from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.models import (
    CalendarResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ImageRequest,
    ImageResponse,
)
from app.services import seeder
from app.services.assistant import ScholarAssistant
from app.services.calendar import get_calendar
from app.services.dua_generator import DuaGenerator
from app.services.groq_client import GroqClient
from app.services.image_service import ImageService
from app.services.memory import ConversationMemory
from app.services.moderation import IslamicModerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

# Services (instantiated once)
memory = ConversationMemory(settings.database_url)
moderator = IslamicModerator()
groq = GroqClient(
    api_key=settings.groq_api_key,
    base_url=settings.groq_base_url,
    model=settings.groq_model,
    timeout=settings.request_timeout_seconds,
)
dua_gen = DuaGenerator()
assistant = ScholarAssistant(settings, memory, moderator, groq, dua_gen)
image_service = ImageService(settings.pollinations_base, moderator)

_seed_counts: dict[str, int] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _seed_counts
    if settings.seed_on_startup:
        cache_dir = str(Path(settings.chroma_path).parent / "cache")
        logger.info("Starting corpus seeding (this may take a few minutes on first run)...")
        try:
            _seed_counts = await seeder.seed_all(
                settings.chroma_path, cache_dir, settings.local_embedding_model
            )
            logger.info("Corpus ready: %s", _seed_counts)
        except Exception as exc:
            logger.error("Seeding failed (offline demo will be used): %s", exc)
    yield
    await groq.close()


app = FastAPI(
    title="myScholar — Islamic AI Assistant",
    description="Grounded Islamic Q&A with Quran, Hadith, scholar quotes, madhab-aware answering, and streaming.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        groq_configured=settings.has_groq_key,
        seed_complete=bool(_seed_counts),
        offline_demo=settings.allow_offline_demo,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Non-streaming chat endpoint."""
    request.stream = False
    return await assistant.chat(request)


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming SSE chat endpoint."""
    request.stream = True
    return await assistant.stream_chat(request)


@app.post("/api/images", response_model=ImageResponse)
async def generate_image(request: ImageRequest) -> ImageResponse:
    return await image_service.generate(request)


@app.get("/api/calendar", response_model=CalendarResponse)
async def calendar(
    lat: float = Query(default=21.3891, description="Latitude (default: Mecca)"),
    lon: float = Query(default=39.8579, description="Longitude (default: Mecca)"),
    madhab: str = Query(default="general"),
    tz: str = Query(default="UTC"),
) -> CalendarResponse:
    return await get_calendar(lat, lon, settings.aladhan_api_base, madhab, tz)


@app.get("/api/sessions")
async def list_sessions() -> dict[str, list[str]]:
    return {"sessions": memory.list_sessions()}


@app.post("/api/sessions/{session_id}/clear")
async def clear_session(session_id: str) -> dict[str, str]:
    memory.clear(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.get("/api/search")
async def search(q: str = Query(...), top_k: int = Query(default=5)) -> dict:
    from app.services import retriever
    hits = retriever.search(q, settings.chroma_path, settings.local_embedding_model, top_k=top_k)
    return {
        "query": q,
        "results": [
            {
                "key": h.key,
                "score": round(h.score, 4),
                "reference": h.citation.reference,
                "source": h.citation.source,
                "text": h.citation.text[:200],
                "arabic": h.citation.arabic[:100] if h.citation.arabic else "",
            }
            for h in hits
        ],
    }
