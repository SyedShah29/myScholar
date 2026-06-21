from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import httpx

from app.services import chroma_store, embeddings

logger = logging.getLogger(__name__)

# Topics mapping for Quranic surahs
SURAH_TOPICS: dict[int, list[str]] = {
    1: ["fatiha", "opening", "prayer", "guidance"],
    2: ["al-baqarah", "law", "faith", "fasting", "salah", "charity", "family", "aqeedah"],
    3: ["aal-imran", "faith", "battle", "jesus", "mary", "isa", "maryam"],
    4: ["an-nisa", "women", "family", "inheritance", "marriage", "justice"],
    5: ["al-maidah", "food", "halal", "law", "people of the book", "justice"],
    6: ["al-anam", "tawhid", "polytheism", "shirk", "creation"],
    7: ["al-araf", "prophets", "history", "adam", "moses", "musa"],
    8: ["al-anfal", "battle", "spoils", "war", "jihad"],
    9: ["at-tawbah", "repentance", "tawbah", "jizyah", "war", "hypocrites"],
    10: ["yunus", "jonah", "tawhid", "prophets"],
    11: ["hud", "hud prophet", "history", "nations"],
    12: ["yusuf", "joseph", "yusuf", "patience", "sabr", "prophets"],
    13: ["ar-ra'd", "thunder", "creation", "signs", "tawhid"],
    14: ["ibrahim", "abraham", "tawhid", "prophets"],
    15: ["al-hijr", "creation", "iblis", "satan", "adam"],
    16: ["an-nahl", "bees", "creation", "blessings", "halal"],
    17: ["al-isra", "night journey", "isra", "bani israel", "prayer"],
    18: ["al-kahf", "cave", "dajjal", "knowledge", "stories", "friday"],
    19: ["maryam", "mary", "jesus", "isa", "yahya", "john", "prophets"],
    20: ["ta-ha", "moses", "musa", "prayer", "quran"],
    21: ["al-anbiya", "prophets", "all prophets", "tawhid"],
    22: ["al-hajj", "hajj", "pilgrimage", "worship"],
    23: ["al-muminun", "believers", "paradise", "prayer", "salah"],
    24: ["an-nur", "light", "modesty", "hijab", "adultery", "slander"],
    25: ["al-furqan", "criterion", "quran", "mercy"],
    26: ["ash-shuara", "poets", "prophets", "moses", "ibrahim"],
    27: ["an-naml", "ants", "solomon", "sulayman", "sheba"],
    28: ["al-qasas", "stories", "moses", "musa", "egypt"],
    29: ["al-ankabut", "spider", "trials", "patience", "prophets"],
    30: ["ar-rum", "romans", "byzantines", "creation", "signs"],
    31: ["luqman", "luqman", "wisdom", "parents", "gratitude"],
    32: ["as-sajdah", "prostration", "creation", "afterlife"],
    33: ["al-ahzab", "confederates", "prophet muhammad", "family", "hijab"],
    34: ["saba", "sheba", "gratitude", "solomon", "david"],
    35: ["fatir", "originator", "creation", "angels"],
    36: ["ya-sin", "heart of quran", "resurrection", "tawhid"],
    37: ["as-saffat", "ranged", "angels", "ibrahim", "ismail"],
    38: ["sad", "david", "sulayman", "ayyub", "prophets"],
    39: ["az-zumar", "groups", "tawhid", "repentance", "tawbah", "afterlife"],
    40: ["ghafir", "forgiver", "pharaoh", "tawhid", "prayer"],
    41: ["fussilat", "explained", "creation", "quran"],
    42: ["ash-shura", "consultation", "shura", "revelation"],
    43: ["az-zukhruf", "ornaments", "jesus", "isa", "tawhid"],
    44: ["ad-dukhan", "smoke", "qiyamah", "judgment"],
    45: ["al-jathiyah", "kneeling", "judgment", "creation", "signs"],
    46: ["al-ahqaf", "wind-curved sandhills", "prophets", "jinn"],
    47: ["muhammad", "war", "hypocrites", "prophet"],
    48: ["al-fath", "victory", "hudaybiyah", "fatah mecca"],
    49: ["al-hujurat", "rooms", "brotherhood", "akhlaq", "ethics", "unity"],
    50: ["qaf", "afterlife", "resurrection", "qiyamah"],
    51: ["adh-dhariyat", "winds", "creation", "prophets", "ibrahim"],
    52: ["at-tur", "mount sinai", "afterlife", "judgment"],
    53: ["an-najm", "star", "revelation", "isra miraj"],
    54: ["al-qamar", "moon", "splitting of moon", "judgment"],
    55: ["ar-rahman", "mercy of allah", "blessings", "paradise"],
    56: ["al-waqiah", "event", "afterlife", "paradise", "hell"],
    57: ["al-hadid", "iron", "charity", "sadaqah", "dunya"],
    58: ["al-mujadilah", "pleading", "knowledge", "scholars", "majlis"],
    59: ["al-hashr", "exile", "banu nadir", "asmaul husna"],
    60: ["al-mumtahanah", "tested", "relations with non-muslims"],
    61: ["as-saf", "ranks", "jihad", "jesus", "isa", "ahmad"],
    62: ["al-jumuah", "friday", "jummah prayer", "friday prayer"],
    63: ["al-munafiqun", "hypocrites", "nifaq"],
    64: ["at-taghabun", "mutual disillusion", "charity", "dunya"],
    65: ["at-talaq", "divorce", "family law", "talaq"],
    66: ["at-tahrim", "prohibition", "family", "prophets wives"],
    67: ["al-mulk", "sovereignty", "creation", "afterlife", "death"],
    68: ["al-qalam", "pen", "revelation", "akhlaq"],
    69: ["al-haqqah", "reality", "judgment", "quran"],
    70: ["al-maarij", "ways of ascent", "patience", "prayer", "salah"],
    71: ["nuh", "noah", "nuh", "history"],
    72: ["al-jinn", "jinn", "tawhid", "quran"],
    73: ["al-muzzammil", "enshrouded", "prayer", "night prayer", "tahajjud"],
    74: ["al-muddaththir", "cloaked", "warning", "hell", "quran"],
    75: ["al-qiyamah", "resurrection", "judgment", "qiyamah"],
    76: ["al-insan", "man", "creation", "paradise", "sabr"],
    77: ["al-mursalat", "emissaries", "judgment"],
    78: ["an-naba", "tidings", "resurrection", "qiyamah"],
    79: ["an-naziat", "those who drag forth", "death", "judgment"],
    80: ["abasa", "he frowned", "akhlaq", "revelation"],
    81: ["at-takwir", "folding up", "qiyamah", "judgment"],
    82: ["al-infitar", "cleaving", "judgment", "recording angels"],
    83: ["al-mutaffifin", "defrauding", "honesty", "judgment"],
    84: ["al-inshiqaq", "splitting open", "judgment", "burden"],
    85: ["al-buruj", "mansions of stars", "persecution", "patience"],
    86: ["at-tariq", "morning star", "creation", "quran"],
    87: ["al-ala", "most high", "quran", "purification", "tazkiyah"],
    88: ["al-ghashiyah", "overwhelming", "judgment", "paradise", "hell"],
    89: ["al-fajr", "dawn", "judgment", "history", "ad thamud"],
    90: ["al-balad", "city", "mecca", "tests", "charity"],
    91: ["ash-shams", "sun", "soul", "tazkiyah", "purification"],
    92: ["al-layl", "night", "charity", "sadaqah", "purification"],
    93: ["ad-duha", "morning hours", "orphan", "gratitude", "prophet"],
    94: ["ash-sharh", "relief", "sabr", "patience", "prophet"],
    95: ["at-tin", "fig", "creation of man", "judgment"],
    96: ["al-alaq", "clot", "first revelation", "reading", "knowledge"],
    97: ["al-qadr", "power", "laylat al-qadr", "night of power", "ramadan"],
    98: ["al-bayyinah", "clear evidence", "people of the book", "shirk"],
    99: ["az-zalzalah", "earthquake", "judgment", "deeds"],
    100: ["al-adiyat", "coursers", "gratitude", "human ingratitude"],
    101: ["al-qariah", "calamity", "judgment", "deeds"],
    102: ["at-takathur", "rivalry", "dunya", "materialism"],
    103: ["al-asr", "time", "iman", "sabr", "haqq"],
    104: ["al-humazah", "traducer", "backbiting", "wealth", "hell"],
    105: ["al-fil", "elephant", "history", "mecca", "kabah"],
    106: ["quraysh", "quraysh", "mecca", "trade"],
    107: ["al-maun", "small kindnesses", "prayer", "charity", "orphan", "akhlaq"],
    108: ["al-kawthar", "abundance", "prophet", "prayer"],
    109: ["al-kafirun", "disbelievers", "tawhid", "freedom of religion"],
    110: ["an-nasr", "victory", "fath mecca", "tawbah"],
    111: ["al-masad", "palm fiber", "abu lahab", "enemies"],
    112: ["al-ikhlas", "sincerity", "tawhid", "oneness", "allah"],
    113: ["al-falaq", "daybreak", "protection", "evil eye", "sihr", "magic"],
    114: ["an-nas", "mankind", "protection", "whispering", "shaytan"],
}


def _build_quran_topics(surah_num: int, text: str) -> list[str]:
    base = SURAH_TOPICS.get(surah_num, [])
    extra: list[str] = []
    lower = text.lower()
    if "prayer" in lower or "salah" in lower or "salat" in lower:
        extra.append("salah")
    if "fasting" in lower or "ramadan" in lower:
        extra.append("sawm")
    if "zakat" in lower or "charity" in lower or "alms" in lower:
        extra.append("zakat")
    if "hajj" in lower or "pilgrimage" in lower:
        extra.append("hajj")
    if "paradise" in lower or "jannah" in lower:
        extra.append("jannah")
    if "hell" in lower or "jahannam" in lower:
        extra.append("jahannam")
    if "prophet" in lower or "messenger" in lower:
        extra.append("prophet")
    return list(dict.fromkeys(base + extra))


HADITH_TOPIC_MAP: dict[str, list[str]] = {
    "revelation": ["revelation", "quran", "wahi"],
    "faith": ["iman", "faith", "belief", "tawhid"],
    "knowledge": ["knowledge", "ilm", "learning"],
    "purification": ["taharah", "wudu", "ghusl", "purification", "cleanliness"],
    "prayers": ["salah", "prayer", "salat", "worship"],
    "zakat": ["zakat", "charity", "sadaqah", "alms"],
    "fasting": ["sawm", "fasting", "ramadan", "siyam"],
    "hajj": ["hajj", "pilgrimage", "umrah", "mecca", "kabah"],
    "marriage": ["marriage", "nikah", "family", "wife", "husband"],
    "sales": ["trade", "business", "sales", "commerce", "riba", "interest"],
    "judgments": ["judgment", "qadi", "justice", "courts"],
    "blood_money": ["diyah", "blood money", "crime", "punishment"],
    "hudud": ["hudud", "punishment", "hadd", "theft", "adultery"],
    "jihad": ["jihad", "struggle", "war", "self-defense"],
    "food_drink": ["food", "halal", "haram", "drink", "intoxicant"],
    "dress": ["clothing", "dress", "hijab", "modesty"],
    "etiquette": ["akhlaq", "manners", "etiquette", "adab"],
    "heart_softeners": ["heart", "zuhd", "asceticism", "dunya", "akhirah"],
    "divine_decree": ["qadar", "decree", "destiny", "predestination"],
    "repentance": ["tawbah", "repentance", "forgiveness", "istighfar"],
    "supplications": ["dua", "supplication", "dhikr", "remembrance"],
}


def _infer_hadith_topics(chapter_title: str, text: str) -> list[str]:
    topics: list[str] = []
    combined = (chapter_title + " " + text).lower()
    for key, keywords in HADITH_TOPIC_MAP.items():
        if any(kw in combined for kw in keywords):
            topics.append(key)
    return topics or ["general"]


async def seed_all(chroma_path: str, cache_dir: str, embedding_model: str) -> dict[str, int]:
    """Seed all corpora. Returns counts per collection."""
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}

    logger.info("Starting corpus seeding...")

    quran_count = await _seed_quran(chroma_path, cache_dir, embedding_model)
    counts["quran"] = quran_count

    hadith_count = await _seed_hadith(chroma_path, cache_dir, embedding_model)
    counts["hadith"] = hadith_count

    scholar_count = _seed_scholars(chroma_path, embedding_model)
    counts["scholars"] = scholar_count

    fabricated_count = _seed_fabricated_hadith(chroma_path, embedding_model)
    counts["fabricated"] = fabricated_count

    logger.info("Seeding complete: %s", counts)
    return counts


async def _seed_quran(chroma_path: str, cache_dir: str, embedding_model: str) -> int:
    existing = chroma_store.collection_count("quran", chroma_path)
    if existing > 100:
        logger.info("Quran collection already seeded (%d docs). Skipping.", existing)
        return existing

    cache_file = Path(cache_dir) / "quran_cache.json"
    ayahs: list[dict[str, Any]] = []

    if cache_file.exists():
        logger.info("Loading Quran from cache...")
        raw = json.loads(cache_file.read_text(encoding="utf-8"))
        ayahs = raw.get("ayahs", [])
    else:
        logger.info("Downloading Quran from AlQuran.cloud...")
        ayahs = await _fetch_quran(cache_file)

    if not ayahs:
        logger.warning("No Quran data available. Skipping Quran seeding.")
        return 0

    logger.info("Embedding %d ayahs...", len(ayahs))
    texts = [a["text"] for a in ayahs]
    vecs = embeddings.embed(texts, embedding_model)

    ids = [a["id"] for a in ayahs]
    metas = [
        {
            "reference": a["reference"],
            "arabic": a.get("arabic", ""),
            "audio_url": a.get("audio_url", ""),
            "surah_name": a.get("surah_name", ""),
            "surah_number": a.get("surah_number", 0),
            "ayah_number": a.get("ayah_number", 0),
            "topics": json.dumps(a.get("topics", [])),
            "source": "quran",
        }
        for a in ayahs
    ]

    chroma_store.upsert_documents("quran", chroma_path, ids, vecs, texts, metas)
    return len(ayahs)


async def _fetch_quran(cache_file: Path) -> list[dict[str, Any]]:
    ayahs: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Fetch English translation
            logger.info("Fetching English Quran (Sahih International)...")
            resp_en = await client.get("https://api.alquran.cloud/v1/quran/en.sahih")
            resp_en.raise_for_status()
            data_en = resp_en.json()

            # Fetch Arabic text
            logger.info("Fetching Arabic Quran...")
            resp_ar = await client.get("https://api.alquran.cloud/v1/quran/ar.alafasy")
            resp_ar.raise_for_status()
            data_ar = resp_ar.json()

        en_surahs = data_en["data"]["surahs"]
        ar_surahs = data_ar["data"]["surahs"]

        ar_map: dict[str, str] = {}
        audio_map: dict[str, str] = {}
        for surah in ar_surahs:
            for ayah in surah["ayahs"]:
                key = f"{surah['number']}_{ayah['numberInSurah']}"
                ar_map[key] = ayah.get("text", "")
                audio_map[key] = ayah.get("audio", "")

        for surah in en_surahs:
            s_num = surah["number"]
            s_name = surah.get("englishName", f"Surah {s_num}")
            for ayah in surah["ayahs"]:
                a_num = ayah["numberInSurah"]
                key = f"{s_num}_{a_num}"
                topics = _build_quran_topics(s_num, ayah.get("text", ""))
                ayahs.append({
                    "id": f"quran_{s_num}_{a_num}",
                    "reference": f"Quran {s_num}:{a_num}",
                    "surah_name": s_name,
                    "surah_number": s_num,
                    "ayah_number": a_num,
                    "text": ayah.get("text", ""),
                    "arabic": ar_map.get(key, ""),
                    "audio_url": audio_map.get(key, ""),
                    "topics": topics,
                })

        cache_file.write_text(json.dumps({"ayahs": ayahs}, ensure_ascii=False), encoding="utf-8")
        logger.info("Quran cache saved (%d ayahs).", len(ayahs))
    except Exception as exc:
        logger.error("Failed to fetch Quran: %s", exc)
    return ayahs


async def _seed_hadith(chroma_path: str, cache_dir: str, embedding_model: str) -> int:
    existing = chroma_store.collection_count("hadith", chroma_path)
    if existing > 100:
        logger.info("Hadith collection already seeded (%d docs). Skipping.", existing)
        return existing

    cache_file = Path(cache_dir) / "hadith_cache.json"
    hadiths: list[dict[str, Any]] = []

    if cache_file.exists():
        logger.info("Loading Hadith from cache...")
        raw = json.loads(cache_file.read_text(encoding="utf-8"))
        hadiths = raw.get("hadiths", [])
    else:
        logger.info("Downloading Hadith from fawazahmed0 CDN...")
        hadiths = await _fetch_hadith(cache_file)

    if not hadiths:
        logger.warning("No Hadith data available. Skipping Hadith seeding.")
        return 0

    logger.info("Embedding %d hadith...", len(hadiths))
    texts = [h["text"] for h in hadiths]
    vecs = embeddings.embed(texts, embedding_model)

    ids = [h["id"] for h in hadiths]
    metas = [
        {
            "reference": h["reference"],
            "collection": h.get("collection", ""),
            "chapter": h.get("chapter", ""),
            "topics": json.dumps(h.get("topics", [])),
            "source": "hadith",
        }
        for h in hadiths
    ]

    chroma_store.upsert_documents("hadith", chroma_path, ids, vecs, texts, metas)
    return len(hadiths)


async def _fetch_hadith(cache_file: Path) -> list[dict[str, Any]]:
    hadiths: list[dict[str, Any]] = []
    collections = [
        ("eng-bukhari", "Sahih Bukhari"),
        ("eng-muslim", "Sahih Muslim"),
        ("eng-abudawud", "Sunan Abu Dawud"),
        ("eng-tirmidhi", "Jami al-Tirmidhi"),
        ("eng-ibnmajah", "Sunan Ibn Majah"),
        ("eng-nasai", "Sunan an-Nasa'i"),
    ]

    async with httpx.AsyncClient(timeout=120.0) as client:
        for edition, name in collections:
            try:
                url = f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/{edition}.json"
                logger.info("Fetching %s...", name)
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                hadith_list = data.get("hadiths", [])

                for h in hadith_list:
                    text = h.get("text", "").strip()
                    if not text or len(text) < 30:
                        continue
                    hadith_num = h.get("hadithnumber", 0)
                    chapter = h.get("chapter", "")
                    topics = _infer_hadith_topics(chapter, text)
                    hadiths.append({
                        "id": f"hadith_{edition}_{hadith_num}",
                        "reference": f"{name} {hadith_num}",
                        "collection": name,
                        "chapter": chapter,
                        "text": text,
                        "topics": topics,
                    })
            except Exception as exc:
                logger.warning("Failed to fetch %s: %s", name, exc)

    cache_file.write_text(json.dumps({"hadiths": hadiths}, ensure_ascii=False), encoding="utf-8")
    logger.info("Hadith cache saved (%d hadiths).", len(hadiths))
    return hadiths


def _seed_scholars(chroma_path: str, embedding_model: str) -> int:
    data_file = Path(__file__).resolve().parents[1] / "data" / "scholars.json"
    if not data_file.exists():
        logger.warning("scholars.json not found.")
        return 0

    raw = json.loads(data_file.read_text(encoding="utf-8"))
    scholars = raw.get("scholars", [])
    
    existing = chroma_store.collection_count("scholars", chroma_path)
    if existing >= len(scholars):
        logger.info("Scholars collection already seeded (%d docs). Skipping.", existing)
        return existing

    texts = [s["text"] for s in scholars]
    vecs = embeddings.embed(texts, embedding_model)
    ids = [s["id"] for s in scholars]
    metas = [
        {
            "reference": f"{s['scholar']}, {s.get('source', '')}",
            "scholar": s["scholar"],
            "school": s.get("school", ""),
            "arabic": s.get("arabic", ""),
            "topics": json.dumps(s.get("topics", [])),
            "source": "scholar",
        }
        for s in scholars
    ]

    chroma_store.upsert_documents("scholars", chroma_path, ids, vecs, texts, metas)
    return len(scholars)


def _seed_fabricated_hadith(chroma_path: str, embedding_model: str) -> int:
    import csv
    data_file = Path(__file__).resolve().parents[1] / "data" / "MAHADDAT.csv"
    if not data_file.exists():
        logger.warning("MAHADDAT.csv not found.")
        return 0

    existing = chroma_store.collection_count("fabricated_hadith", chroma_path)
    if existing > 100:
        logger.info("Fabricated Hadith collection already seeded (%d docs). Skipping.", existing)
        return existing

    fabricated = []
    with open(data_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        # Headers: ['Book', 'No.', 'Full Hadith', 'Isnad', 'Matan', "Author's Comments", 'Degree', 'Authenticity', 'Topic']
        for i, row in enumerate(reader):
            if len(row) >= 5:
                matan = row[4].strip()
                if matan:
                    fabricated.append({
                        "id": f"fab_{i}_{row[1]}",
                        "text": matan,
                        "reference": row[0],
                        "topic": row[8] if len(row) >= 9 else ""
                    })

    if not fabricated:
        return 0

    logger.info("Embedding %d fabricated hadiths in Arabic...", len(fabricated))
    texts = [f["text"] for f in fabricated]
    vecs = embeddings.embed(texts, embedding_model)
    ids = [f["id"] for f in fabricated]
    metas = [
        {
            "reference": f["reference"],
            "arabic": f["text"],
            "topic": f["topic"],
            "source": "fabricated_hadith"
        }
        for f in fabricated
    ]

    chroma_store.upsert_documents("fabricated_hadith", chroma_path, ids, vecs, texts, metas)
    return len(fabricated)
