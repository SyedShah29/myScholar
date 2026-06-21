from __future__ import annotations

import json

from app.models import Citation, SearchHit
from app.services import chroma_store, embeddings


def cross_reference(
    hits: list[SearchHit],
    chroma_path: str,
    embedding_model: str,
    max_refs: int = 3,
) -> list[Citation]:
    """
    Given retrieved hits, find cross-references from the other corpus.
    e.g. for Quran hits → find related Hadith, and vice versa.
    Returns up to max_refs Citations.
    """
    if not hits:
        return []

    # Determine dominant source
    quran_hits = [h for h in hits if h.citation.source == "quran"]
    hadith_hits = [h for h in hits if h.citation.source == "hadith"]

    cross: list[Citation] = []
    seen_refs: set[str] = {h.citation.reference for h in hits}

    def _find_related(from_hits: list[SearchHit], target_collection: str) -> list[Citation]:
        results: list[Citation] = []
        if not from_hits or chroma_store.collection_count(target_collection, chroma_path) == 0:
            return results

        # Use the top hit's text as query
        query_text = from_hits[0].citation.text
        query_vec = embeddings.embed_one(query_text, embedding_model)
        try:
            raw = chroma_store.query_collection(
                target_collection, chroma_path, query_vec, n_results=5
            )
        except Exception:
            return results

        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]

        for doc, meta in zip(docs, metas):
            ref = meta.get("reference", "")
            if ref in seen_refs or not doc:
                continue
            seen_refs.add(ref)
            topics_raw = meta.get("topics", "[]")
            try:
                topics = json.loads(topics_raw) if isinstance(topics_raw, str) else topics_raw
            except Exception:
                topics = []

            results.append(Citation(
                id=meta.get("id", ""),
                reference=ref,
                text=doc,
                arabic=meta.get("arabic", ""),
                audio_url=meta.get("audio_url", ""),
                source=target_collection.rstrip("s"),  # "quran", "hadith", "scholar"
                collection=meta.get("collection", meta.get("surah_name", "")),
                topics=topics,
            ))
            if len(results) >= max_refs:
                break

        return results

    if quran_hits:
        cross.extend(_find_related(quran_hits, "hadith"))
    if hadith_hits and len(cross) < max_refs:
        cross.extend(_find_related(hadith_hits, "quran"))

    return cross[:max_refs]
