from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_model: Any = None
_model_name: str = ""


def _load_model(model_name: str) -> Any:
    global _model, _model_name
    if _model is not None and _model_name == model_name:
        return _model
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        logger.info("Loading embedding model: %s", model_name)
        _model = SentenceTransformer(model_name)
        _model_name = model_name
        logger.info("Embedding model loaded successfully.")
        return _model
    except Exception as exc:
        logger.warning("sentence-transformers not available: %s. Semantic search disabled.", exc)
        return None


def embed(texts: list[str], model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2") -> list[list[float]]:
    """Embed a list of texts. Returns list of float vectors. Falls back to empty vectors."""
    if not texts:
        return []
    model = _load_model(model_name)
    if model is None:
        return [[0.0] * 384 for _ in texts]
    try:
        vectors = model.encode(texts, show_progress_bar=False, batch_size=32)
        return [v.tolist() for v in vectors]
    except Exception as exc:
        logger.error("Embedding failed: %s", exc)
        return [[0.0] * 384 for _ in texts]


def embed_one(text: str, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2") -> list[float]:
    results = embed([text], model_name)
    return results[0] if results else [0.0] * 384
