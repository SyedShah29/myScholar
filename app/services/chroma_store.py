from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_client: Any = None
_collections: dict[str, Any] = {}


def _get_client(chroma_path: str) -> Any:
    global _client
    if _client is not None:
        return _client
    import chromadb  # type: ignore
    Path(chroma_path).mkdir(parents=True, exist_ok=True)
    _client = chromadb.PersistentClient(path=chroma_path)
    logger.info("ChromaDB initialized at: %s", chroma_path)
    return _client


def get_collection(name: str, chroma_path: str) -> Any:
    if name in _collections:
        return _collections[name]
    client = _get_client(chroma_path)
    col = client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )
    _collections[name] = col
    return col


def collection_count(name: str, chroma_path: str) -> int:
    try:
        col = get_collection(name, chroma_path)
        return col.count()
    except Exception:
        return 0


def upsert_documents(
    collection_name: str,
    chroma_path: str,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict[str, Any]],
) -> None:
    col = get_collection(collection_name, chroma_path)
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        col.upsert(
            ids=ids[i : i + batch_size],
            embeddings=embeddings[i : i + batch_size],
            documents=documents[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
        )
    logger.info("Upserted %d documents into collection '%s'", len(ids), collection_name)


def query_collection(
    collection_name: str,
    chroma_path: str,
    query_embedding: list[float],
    n_results: int = 8,
    where: dict[str, Any] | None = None,
) -> dict[str, Any]:
    col = get_collection(collection_name, chroma_path)
    kwargs: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": min(n_results, col.count() or 1),
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where
    return col.query(**kwargs)
