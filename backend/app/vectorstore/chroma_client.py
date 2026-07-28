from __future__ import annotations
import os
from typing import Any

DEFAULT_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
DEFAULT_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "articles")

_vectorstore = None  

def get_vectorstore(embedding_function):
    global _vectorstore
    if _vectorstore is None:
        from langchain_chroma import Chroma

        _vectorstore = Chroma(
            collection_name=DEFAULT_COLLECTION_NAME,
            embedding_function=embedding_function,
            persist_directory=DEFAULT_PERSIST_DIR,
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
    """
    Bypasses the langchain wrapper to get raw distances back (its
    similarity_search_by_vector helper drops them). Collection is created with
    collection_metadata={"hnsw:space": "cosine"}, so distance = 1 - cosine_similarity.
    """
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