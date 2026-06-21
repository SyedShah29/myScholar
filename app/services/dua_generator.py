from __future__ import annotations

import json
import re
from pathlib import Path

from app.models import DuaItem


class DuaGenerator:
    def __init__(self) -> None:
        data_file = Path(__file__).resolve().parents[1] / "data" / "duas.json"
        self._duas: list[dict[str, object]] = []
        if data_file.exists():
            raw = json.loads(data_file.read_text(encoding="utf-8"))
            self._duas = raw.get("duas", [])

    def detect_and_generate(self, message: str) -> DuaItem | None:
        """
        Detect if the user is requesting a dua and return an appropriate one.
        Returns None if no dua context detected.
        """
        lowered = message.lower()

        intent_words = {"dua", "du'a", "supplication", "supplicate", "pray", "prayer"}
        has_intent = any(re.search(rf"\b{w}\b", lowered) for w in intent_words)
        
        # Check each dua's context for keyword matches
        words = set(re.findall(r'\b\w+\b', lowered))
        
        # Stop words to ignore during matching
        stop_words = {
            "a", "an", "the", "for", "to", "in", "on", "of", "and", "or", "is", "am", "are", "was", "were",
            "be", "been", "being", "have", "has", "had", "do", "does", "did", "what", "when", "where", "why",
            "how", "who", "which", "i", "you", "he", "she", "it", "we", "they", "my", "your", "his", "her",
            "its", "our", "their", "this", "that", "these", "those", "if", "then", "else", "dua", "du'a",
            "pray", "supplication", "me", "can", "could", "would", "should", "will", "shall", "about", "like",
            "just", "know", "want", "need", "make", "tell", "say", "saying"
        }
        keywords = {kw for kw in words if kw not in stop_words and len(kw) > 2}
        
        best_dua = None
        best_score = 0
        
        for dua in self._duas:
            context = str(dua.get("context", "")).lower()
            # Score based on how many keywords match the context string or their 5-char prefix matches
            score = sum(1 for kw in keywords if kw in context or (len(kw) >= 5 and kw[:5] in context))
            if score > best_score:
                best_score = score
                best_dua = dua
                
        # Require intent OR a very high context score to prevent false positives
        if best_dua and (has_intent or best_score >= 2):
            return DuaItem(
                context=str(best_dua.get("context", "general")),
                text=str(best_dua.get("text", "")),
                arabic=str(best_dua.get("arabic", "")),
                transliteration=str(best_dua.get("transliteration", "")),
                source=str(best_dua.get("source", ""))
            )

        # General dua request patterns
        if not has_intent:
            return None

        general_patterns = [
            r"\b(dua|du'a|supplication|pray for|make dua)\b",
            r"\bteach me (a|the) (dua|prayer|supplication)\b",
        ]
        for pattern in general_patterns:
            if re.search(pattern, lowered):
                # Return general dua
                general = next((d for d in self._duas if d.get("context") == "general"), None)
                if general:
                    return DuaItem(
                        context="general",
                        text=str(general.get("text", "")),
                        arabic=str(general.get("arabic", "")),
                        transliteration=str(general.get("transliteration", "")),
                        source=str(general.get("source", "")),
                    )

        return None
