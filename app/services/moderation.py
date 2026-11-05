from __future__ import annotations

import json
import re
from pathlib import Path

from app.config import get_settings
from app.models import ModerationResult
from app.services import chroma_store, embeddings

_KNOWN_FALSE_HADITH_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "known_false_hadith.json"
)


class IslamicModerator:
    def __init__(self) -> None:
        self._blasphemy_re = re.compile(
            r"\b(mock|insult|ridicule|humiliate|desecrate|defile|blaspheme|disrespect)"
            r".{0,80}\b(allah|prophet|muhammad|quran|islam|mosque|masjid|kaaba|kabah|sahaba|companion)\b",
            re.I,
        )
        self._sacred_mockery_image_re = re.compile(
            r"\b(mock|nude|naked|sexual|erotic|porn|cartoon|caricature|draw|depict|picture)"
            r".{0,80}\b(prophet|muhammad|allah|angel|jibril|quran|companion|sahaba)\b",
            re.I,
        )
        self._violence_re = re.compile(
            r"\b(kill|murder|attack|bomb|slaughter|exterminate|genocide|eradicate|behead|massacre)\b",
            re.I,
        )
        self._religious_group_re = re.compile(
            r"\b(muslim|christian|jew|kafir|infidel|apostate|murtad|hindu|atheist|non-muslim)\b",
            re.I,
        )
        self._takfiri_re = re.compile(
            r"\b(declare kafir|call kafir|takfir|all (muslims|christians|jews) should|"
            r"(kill|destroy|eliminate).{0,40}(kafirs?|infidels?|non-muslims?|christians?|jews?))\b",
            re.I,
        )
        self._scripture_manipulation_re = re.compile(
            r"\b(rewrite|alter|change|fake|forge|invent|fabricate|manipulate)"
            r".{0,80}\b(quran|ayah|verse|surah|hadith|sunnah|islam)\b",
            re.I,
        )
        self._injection_re = re.compile(
            r"\b(ignore|bypass|override|forget|disregard|pretend|act as if).{0,80}"
            r"\b(instructions|guardrails|policy|safety|system prompt|rules)\b",
            re.I,
        )
        self._sexual_re = re.compile(
            r"\b(porn|nude|naked|sexual|erotic|fetish|seductive|explicit)\b",
            re.I,
        )
        self._coercion_re = re.compile(
            r"\b(force|coerce|threaten|intimidate).{0,80}\b(convert|conversion|religion|islam|muslim)\b",
            re.I,
        )

        # False hadith fallback
        self._false_hadith: list[dict[str, object]] = self._load_known_false_hadith()

    @staticmethod
    def _load_known_false_hadith() -> list[dict[str, object]]:
        """Load the curated list so detection also works without a vector store."""
        try:
            payload = json.loads(_KNOWN_FALSE_HADITH_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        entries = payload.get("fabricated_hadith", [])
        return entries if isinstance(entries, list) else []

    def evaluate_chat(self, text: str) -> ModerationResult:
        # Scripture manipulation
        if self._scripture_manipulation_re.search(text):
            return ModerationResult(
                allowed=False,
                category="scripture_manipulation",
                severity="high",
                reason="The request asks to falsify or manipulate the Quran or Hadith.",
                safe_alternative="I can help compare different scholarly interpretations or explain tafsir without altering the text.",
            )
        # Takfiri/extremist content
        if self._takfiri_re.search(text):
            return ModerationResult(
                allowed=False,
                category="takfiri_extremism",
                severity="critical",
                reason="The request promotes takfir (declaring others non-Muslim) or religious violence.",
                safe_alternative="I can discuss scholarly perspectives on Islamic ethics and the prohibition of unjust takfir.",
            )
        # Violence toward religious groups
        if self._violence_re.search(text) and self._religious_group_re.search(text):
            return ModerationResult(
                allowed=False,
                category="religious_hate_or_violence",
                severity="critical",
                reason="The request combines religion with violence or dehumanization.",
                safe_alternative="I can help reframe this toward peaceful understanding, justice, and Islamic ethics.",
            )
        # Coercive conversion
        if self._coercion_re.search(text):
            return ModerationResult(
                allowed=False,
                category="coercive_religion",
                severity="high",
                reason="The request promotes forced religious conversion.",
                safe_alternative="I can help discuss the Islamic perspective on peaceful da'wah and freedom of conscience.",
            )
        # Blasphemy
        if self._blasphemy_re.search(text):
            return ModerationResult(
                allowed=False,
                category="blasphemy",
                severity="high",
                reason="The request contains content disrespectful to Islamic sacred subjects.",
                safe_alternative="I can engage with critical academic questions about Islam in a respectful manner.",
            )
        # Prompt injection
        if self._injection_re.search(text):
            return ModerationResult(
                allowed=True,
                category="prompt_injection",
                severity="medium",
                reason="The prompt appears to attempt bypassing system instructions.",
            )
        return ModerationResult()

    def evaluate_image(self, text: str) -> ModerationResult:
        chat_result = self.evaluate_chat(text)
        if not chat_result.allowed:
            return chat_result
        if self._sacred_mockery_image_re.search(text):
            return ModerationResult(
                allowed=False,
                category="figurative_sacred_imagery",
                severity="high",
                reason="Figurative depictions of the Prophet ﷺ, angels, or sacred subjects are not permissible in Islamic tradition.",
                safe_alternative="I can generate Islamic geometric art, arabesque patterns, or calligraphy instead.",
            )
        if self._sexual_re.search(text):
            return ModerationResult(
                allowed=False,
                category="sexual_content",
                severity="high",
                reason="The image prompt requests sexual or explicit content.",
                safe_alternative="I can generate a modest, Islamic-themed visual instead.",
            )
        return chat_result

    def find_false_hadith(self, text: str) -> list[dict[str, object]]:
        """Detect references to known fabricated or weak hadith."""
        normalized = text.casefold()
        for entry in self._false_hadith:
            aliases = entry.get("aliases")
            phrases = [str(entry.get("phrase", "")), *([str(a) for a in aliases] if isinstance(aliases, list) else [])]
            if any(phrase and phrase.casefold() in normalized for phrase in phrases):
                return [
                    {
                        "phrase": text,
                        "correction": str(entry.get("correction", "")),
                        "status": str(entry.get("status", "fabricated")),
                        "arabic": str(entry.get("arabic", "")),
                        "reference": str(
                            entry.get("better_reference", entry.get("reference", ""))
                        ),
                        "topic": str(entry.get("topic", "")),
                    }
                ]

        matches = []
        try:
            settings = get_settings()
            vec = embeddings.embed_one(text, settings.local_embedding_model)
            results = chroma_store.query_collection(
                "fabricated_hadith", 
                settings.chroma_path, 
                vec, 
                n_results=1
            )
            
            # Distance < 0.3 means very highly semantically identical
            if results and results["distances"] and results["distances"][0]:
                if results["distances"][0][0] < 0.35:
                    meta = results["metadatas"][0][0]
                    matches.append({
                        "phrase": text,
                        "correction": "This matches a known fabricated (Mawdu) hadith in the MAHADDAT database.",
                        "status": "fabricated",
                        "arabic": meta.get("arabic", ""),
                        "reference": meta.get("reference", ""),
                        "topic": meta.get("topic", "")
                    })
        except Exception as e:
            pass
            
        return matches
