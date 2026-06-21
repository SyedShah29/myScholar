from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from app.models import Citation, SearchHit
from app.services import chroma_store, embeddings

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "how", "i", "in", "is", "it", "me", "of", "on", "or", "that", "the",
    "this", "to", "was", "what", "when", "where", "who", "why", "with",
    "you", "your", "tell", "me", "about", "explain", "does", "do", "can",
    "could", "would", "should", "did", "will", "has", "have", "had", "please",
}


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {t for t in tokens if t not in STOPWORDS and len(t) > 2}


def _parse_topics(raw: str | list[str]) -> list[str]:
    if isinstance(raw, list):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _metadata_to_citation(doc: str, meta: dict[str, Any]) -> Citation:
    source = meta.get("source", "quran")
    topics = _parse_topics(meta.get("topics", "[]"))
    return Citation(
        id=meta.get("id", ""),
        reference=meta.get("reference", ""),
        text=doc,
        arabic=meta.get("arabic", ""),
        audio_url=meta.get("audio_url", ""),
        source=source,
        collection=meta.get("collection", meta.get("surah_name", meta.get("scholar", ""))),
        topics=topics,
    )


@dataclass
class RawHit:
    citation: Citation
    tfidf_score: float
    semantic_score: float

    @property
    def combined_score(self) -> float:
        return 0.4 * self.tfidf_score + 0.6 * self.semantic_score


def search(
    query: str,
    chroma_path: str,
    embedding_model: str,
    top_k: int = 8,
    expanded_query: str | None = None,
) -> list[SearchHit]:
    """
    Hybrid retrieval across quran, hadith, and scholars collections.
    Returns top-K SearchHits with citation keys (Q1, H1, S1...).
    """
    query_tokens = _tokenize(query)
    search_query = expanded_query or query
    expanded_tokens = _tokenize(search_query)
    query_vec = embeddings.embed_one(search_query, embedding_model)

    collections = ["quran", "hadith", "scholars"]
    all_hits: list[RawHit] = []

    for col_name in collections:
        if chroma_store.collection_count(col_name, chroma_path) == 0:
            continue
        try:
            results = chroma_store.query_collection(
                col_name,
                chroma_path,
                query_vec,
                n_results=min(top_k * 2, 20),
            )
        except Exception:
            continue

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, distance in zip(docs, metas, distances):
            if not doc or not meta:
                continue
            # Cosine distance → similarity (ChromaDB returns distance not similarity)
            semantic_score = max(0.0, 1.0 - float(distance))

            doc_tokens = _tokenize(doc)
            topic_tokens = _tokenize(" ".join(_parse_topics(meta.get("topics", "[]"))))
            ref_tokens = _tokenize(meta.get("reference", ""))
            all_tokens = doc_tokens | topic_tokens | ref_tokens
            
            # Match against expanded tokens, but normalize by the original query's token length
            overlap = expanded_tokens & all_tokens
            
            # Normalize TFIDF by a softer curve so long queries aren't heavily penalized
            base_tfidf = min(1.0, len(overlap) / max(len(query_tokens) * 0.5, 1.0))
            tfidf_score = base_tfidf * 0.5  # Max base TFIDF is 0.5

            # Exact topic match bonus
            for topic in _parse_topics(meta.get("topics", "[]")):
                if topic.lower() in query.lower():
                    tfidf_score += 0.2

            citation = _metadata_to_citation(doc, {**meta, "id": meta.get("id", doc[:20])})
            combined = 0.4 * min(tfidf_score, 1.0) + 0.6 * semantic_score
            
            # Minimum threshold to prevent irrelevant verses from showing
            if combined > 0.35:
                all_hits.append(RawHit(citation=citation, tfidf_score=min(tfidf_score, 1.0), semantic_score=semantic_score))

    # Deduplicate by reference
    seen: set[str] = set()
    unique_hits: list[RawHit] = []
    for h in all_hits:
        key = h.citation.reference
        if key not in seen:
            seen.add(key)
            unique_hits.append(h)

    # Sort by combined score
    unique_hits.sort(key=lambda h: h.combined_score, reverse=True)
    top = unique_hits[:top_k]

    # Assign citation keys by source
    q_idx = h_idx = s_idx = 1
    result: list[SearchHit] = []
    for hit in top:
        if hit.citation.source == "quran":
            key = f"Q{q_idx}"
            q_idx += 1
        elif hit.citation.source == "hadith":
            key = f"H{h_idx}"
            h_idx += 1
        else:
            key = f"S{s_idx}"
            s_idx += 1
        result.append(SearchHit(citation=hit.citation, score=hit.combined_score, key=key))

    return result
