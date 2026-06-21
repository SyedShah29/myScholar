from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Core knowledge models
# ---------------------------------------------------------------------------

class Citation(BaseModel):
    id: str
    reference: str
    text: str
    arabic: str = ""
    audio_url: str = ""
    source: Literal["quran", "hadith", "scholar"] = "quran"
    collection: str = ""          # e.g. "Sahih Bukhari", "Al-Baqarah"
    madhab_note: str = ""         # if a madhab-specific note applies
    topics: list[str] = Field(default_factory=list)


class DuaItem(BaseModel):
    context: str                  # e.g. "before_eating"
    text: str                     # English text
    arabic: str = ""
    transliteration: str = ""
    source: str = ""              # e.g. "Sahih Bukhari 5376"


class ModerationResult(BaseModel):
    allowed: bool = True
    category: str = "ok"
    severity: Literal["low", "medium", "high", "critical"] = "low"
    reason: str = ""
    safe_alternative: str = ""


class SearchHit(BaseModel):
    citation: Citation
    score: float
    key: str                      # Q1, H1, S1 etc.


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str = ""
    message: str
    madhab: Literal["hanafi", "maliki", "shafii", "hanbali", "jafari", "general"] = "general"
    tone: Literal["scholarly", "pastoral", "concise"] = "scholarly"
    stream: bool = True


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    cross_references: list[Citation] = Field(default_factory=list)
    dua: DuaItem | None = None
    moderation: ModerationResult = Field(default_factory=ModerationResult)
    madhab: str = "general"
    memory_used: int = 0
    trace_id: str = ""
    provider: str = "groq"


class ImageRequest(BaseModel):
    session_id: str = ""
    prompt: str
    style: Literal["geometric", "calligraphy", "arabesque", "miniature", "architectural"] = "geometric"
    width: int = 1024
    height: int = 1024


class ImageResponse(BaseModel):
    session_id: str
    image_url: str
    safe_prompt: str
    provider: str = "pollinations"
    moderation: ModerationResult = Field(default_factory=ModerationResult)


class CalendarResponse(BaseModel):
    hijri_date: str
    hijri_month: str
    hijri_year: int
    gregorian_date: str
    prayer_times: dict[str, str] = Field(default_factory=dict)
    qibla_direction: float = 0.0
    upcoming_events: list[dict[str, str]] = Field(default_factory=list)
    timezone: str = "UTC"
    calculation_method: str = "MWL"


class HealthResponse(BaseModel):
    status: str
    app: str
    groq_configured: bool
    seed_complete: bool
    offline_demo: bool
