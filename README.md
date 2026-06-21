# myScholar — Islamic AI Assistant

A production-quality Islamic AI assistant grounded in Quran, Hadith, and authentic scholarship.

## Features

- 🕌 **Full Quran corpus** — All 6,236 ayahs with Arabic text and recitation audio (AlQuran.cloud)
- 📜 **Hadith corpus** — 3,000+ authentic hadith from Bukhari, Muslim, Abu Dawud, Tirmidhi, Ibn Majah
- 🎓 **Scholar quotes** — Curated wisdom from Al-Ghazali, Ibn Taymiyyah, Imam Nawawi, Ibn al-Qayyim, and more
- 🔍 **Hybrid semantic search** — TF-IDF + ChromaDB vector embeddings (sentence-transformers)
- 🔗 **Cross-reference engine** — Finds related Hadith for Quran hits and vice versa
- ☝️ **Madhab-aware answering** — Hanafi, Maliki, Shafi'i, Hanbali, Ja'fari, General
- 🤲 **Dua generator** — Context-aware duas with Arabic, transliteration, and source
- 🗓 **Islamic calendar** — Real-time prayer times, Hijri date, Qibla direction (AlAdhan API)
- ⚡ **Streaming responses** — Real-time token-by-token streaming via Groq (ultra-fast LLM)
- 🎨 **Islamic art generation** — Pollinations.ai (geometric, calligraphy, arabesque, miniature)
- 🛡️ **Islamic safety layer** — Fabricated hadith detection, blasphemy, extremism, injection protection
- 🌙 **Premium UI** — Dark/light mode, Arabic font, citation cards with audio playback

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

Copy `.env.example` to `.env` and add your Groq API key:

```env
GROQ_API_KEY=your-groq-key-here  # Free at console.groq.com
```

Run:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open: `http://127.0.0.1:8000`

**First startup**: The app automatically downloads and indexes the full Quran + Hadith corpus (~3-5 minutes). Subsequent startups are instant.

## Free APIs Used

| API | Purpose | Key Required? |
|---|---|---|
| [AlQuran.cloud](https://alquran.cloud) | Full Quran (6,236 ayahs + Arabic + audio) | ❌ None |
| [fawazahmed0/hadith-api](https://github.com/fawazahmed0/hadith-api) | 22,000+ hadith (CDN) | ❌ None |
| [AlAdhan API](https://aladhan.com/prayer-times-api) | Prayer times + Hijri + Qibla | ❌ None |
| [Pollinations.ai](https://pollinations.ai) | Islamic art generation | ❌ None |
| [Groq](https://console.groq.com) | Ultra-fast LLM (Llama 4 Scout) | ✅ Free signup |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | Non-streaming chat |
| `POST` | `/api/chat/stream` | SSE streaming chat |
| `POST` | `/api/images` | Islamic art generation |
| `GET` | `/api/calendar` | Prayer times + Hijri date + Qibla |
| `GET` | `/api/search?q=` | Debug: semantic search |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/sessions/{id}/clear` | Clear session memory |

## Evaluation

```bash
uvicorn app.main:app --port 8000 &
python scripts/run_evals.py --base-url http://127.0.0.1:8000
```

## Testing

```bash
pip install pytest pytest-asyncio httpx
python -m pytest tests/ -v
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design.

## Tech Stack

- **Backend**: FastAPI + Python 3.11+
- **LLM**: Groq API (Llama 4 Scout — free tier)
- **Vector DB**: ChromaDB (in-process, no Docker)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 (local, free)
- **Memory**: SQLite
- **Frontend**: Vanilla HTML/CSS/JS with SSE streaming
