from __future__ import annotations
import os
from typing import Any
from app.core.config import get_settings

settings = get_settings()

DEFAULT_COLLECTION_NAME = 'articles'

_vectorstore = None
_client = None


def _get_chroma_client():
    global _client
    if _client is None:
        import chromadb

        api_key = settings.CHROMA_API_KEY
        tenant = settings.CHROMA_TENANT
        database = settings.CHROMA_DATABASE

        if not api_key or not tenant:
            raise RuntimeError(
                "CHROMA_API_KEY and CHROMA_TENANT must be set to use Chroma Cloud. "
                "Create a free database at https://trychroma.com and set these "
                "(plus optionally CHROMA_DATABASE) in your environment / .env."
            )

        _client = chromadb.CloudClient(
            tenant=tenant,
            database=database,
            api_key=api_key,
        )
    return _client


def get_vectorstore(embedding_function):
    global _vectorstore
    if _vectorstore is None:
        from langchain_chroma import Chroma

        _vectorstore = Chroma(
            client=_get_chroma_client(),
            collection_name=DEFAULT_COLLECTION_NAME,
            embedding_function=embedding_function,
            collection_metadata={"hnsw:space": "cosine"},
        )
    return _vectorstore


def upsert_embeddings(
    vectorstore,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict[str, Any]],
) -> None:
    if not ids:
        return
    vectorstore._collection.upsert(
        ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas
    )


def query_similar(vectorstore, embedding: list[float], n_results: int = 5):
    return vectorstore.similarity_search_by_vector(embedding, k=n_results)


def query_similar_with_scores(
    vectorstore,
    embedding: list[float],
    n_results: int = 5,
    where: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    kwargs: dict[str, Any] = dict(
        query_embeddings=[embedding],
        n_results=n_results,
        include=["metadatas", "documents", "distances"],
    )
    if where:
        kwargs["where"] = where

    raw = vectorstore._collection.query(**kwargs)

    ids = raw.get("ids", [[]])[0]
    documents = raw.get("documents", [[]])[0]
    metadatas = raw.get("metadatas", [[]])[0]
    distances = raw.get("distances", [[]])[0]

    results: list[dict[str, Any]] = []
    for i, doc_id in enumerate(ids):
        distance = distances[i] if i < len(distances) else None
        results.append({
            "id": doc_id,
            "document": documents[i] if i < len(documents) else None,
            "metadata": metadatas[i] if i < len(metadatas) else {},
            "distance": distance,
            "score": (1.0 - distance) if distance is not None else None,
        })
    return results


def get_embeddings_by_ids(vectorstore, ids: list[str]) -> dict[str, list[float]]:
    if not ids:
        return {}
    raw = vectorstore._collection.get(ids=ids, include=["embeddings"])
    return dict(zip(raw.get("ids", []), raw.get("embeddings", [])))