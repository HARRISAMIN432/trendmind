from __future__ import annotations

from typing import Any

import chromadb
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from app.core.config import get_settings

settings = get_settings()

DEFAULT_COLLECTION_NAME = "articles"

if not settings.CHROMA_API_KEY or not settings.CHROMA_TENANT:
    raise RuntimeError("CHROMA_API_KEY and CHROMA_TENANT must be configured.")

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=settings.OPENAI_API_KEY,
)

client = chromadb.CloudClient(
    api_key=settings.CHROMA_API_KEY,
    tenant=settings.CHROMA_TENANT,
    database=settings.CHROMA_DATABASE,
)

vector_store = Chroma(
    client=client,
    collection_name=DEFAULT_COLLECTION_NAME,
    embedding_function=embeddings,
    collection_metadata={"hnsw:space": "cosine"},
)


def get_vectorstore(embedding_function=None) -> Chroma:
    return vector_store


def upsert_embeddings(
    vectorstore: Chroma,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict[str, Any]],
) -> None:
    if not ids:
        return

    vectorstore._collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def get_embeddings_by_ids(
    vectorstore: Chroma,
    ids: list[str],
) -> dict[str, list[float]]:
    if not ids:
        return {}

    result = vectorstore._collection.get(
        ids=ids,
        include=["embeddings"],
    )

    result_ids = result.get("ids", [])
    result_embeddings = result.get("embeddings", [])

    return {
        id_: embedding
        for id_, embedding in zip(result_ids, result_embeddings)
    }


def query_similar(
    vectorstore: Chroma,
    query: str,
    n_results: int = 5,
):
    return vectorstore.similarity_search(
        query=query,
        k=n_results,
    )


def query_similar_with_scores(
    vectorstore: Chroma,
    query_embedding: list[float],
    n_results: int = 5,
    where: dict | None = None,
):
    result = vectorstore._collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    return [
        {
            "id": id_,
            "document": document,
            "metadata": metadata,
            "score": 1.0 - distance,  
        }
        for id_, document, metadata, distance in zip(ids, documents, metadatas, distances)
    ]