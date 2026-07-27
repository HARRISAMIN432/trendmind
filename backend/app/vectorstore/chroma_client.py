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