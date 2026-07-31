from __future__ import annotations
import gc
import hashlib
import logging
from dataclasses import asdict, dataclass
from typing import Any, Optional
from app.core.config import get_settings
from app.vectorstore.chroma_client import get_vectorstore, upsert_embeddings

try:
    from app.agents.summarization_agent import SummarizedArticle
except ImportError:
    from dataclasses import dataclass as _dc, field as _field

    @_dc
    class SummarizedArticle:
        title: str
        url: str
        source_name: str
        published_at: Any
        raw_content: str
        clean_content: str
        category: str
        sub_category: str
        companies: list[str] = _field(default_factory=list)
        importance: str = "Medium"
        summary_short: str = ""
        key_takeaway: str = ""
        why_it_matters: str = ""
        technical_highlights: str = ""


logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

_embedding_model: Optional[Any] = None


def get_embedding_function():
    global _embedding_model
    if _embedding_model is None:
        from langchain_openai import OpenAIEmbeddings

        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY must be set to use OpenAI embeddings. "
                "Add it to your environment/.env."
            )
        logger.info(f"Initializing OpenAIEmbeddings: {EMBEDDING_MODEL_NAME}")
        _embedding_model = OpenAIEmbeddings(
            model=EMBEDDING_MODEL_NAME,
            api_key=settings.OPENAI_API_KEY,
        )
    return _embedding_model


def _embed_texts(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    if not texts:
        return []
    embed_fn = get_embedding_function()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        vectors.extend(embed_fn.embed_documents(batch))
    return vectors


CHUNK_SUMMARY = "summary"
CHUNK_CONTEXT = "context"
CHUNK_TECHNICAL = "technical"

MAX_CHUNK_WORDS = 150


def _cap_words(text: str, max_words: int = MAX_CHUNK_WORDS) -> str:
    words = text.strip().split()
    return " ".join(words[:max_words])


def build_chunk_texts(article: SummarizedArticle) -> dict[str, str]:
    """Build up to 3 focused embedding chunks per article instead of one
    combined blob.

    Each chunk is single-purpose and short, which retrieves far better than
    one long vector representing several different kinds of information at
    once (a query about a benchmark number has to compete against summary
    prose diluting the same vector in the single-chunk approach). Chunks:

    - summary:   title + key_takeaway + summary_short    ("what happened")
    - context:   title + why_it_matters                  ("why it matters")
    - technical: title + technical_highlights             ("the numbers/specs")
      - only created if technical_highlights is non-empty, since most
        funding/policy articles have none.

    Each chunk is capped at MAX_CHUNK_WORDS words to stay dense/focused.

    If a later chunk's text ends up identical to one already built (e.g. a
    thin article where why_it_matters/technical_highlights are effectively
    empty and only the title survives), it's skipped - storing 2-3 identical
    vectors for the same article wastes cost/storage with zero retrieval
    benefit (doubly true now that each embedding call is a billed API request).
    """
    chunks: dict[str, str] = {}
    seen_texts: set[str] = set()

    def _add_if_unique(chunk_type: str, text: str) -> None:
        if text and text not in seen_texts:
            chunks[chunk_type] = text
            seen_texts.add(text)

    summary_parts = [article.title, article.key_takeaway, article.summary_short]
    summary_text = " ".join(p.strip() for p in summary_parts if p and p.strip())
    if summary_text:
        _add_if_unique(CHUNK_SUMMARY, _cap_words(summary_text))

    if article.why_it_matters and article.why_it_matters.strip():
        context_text = " ".join(
            p.strip() for p in [article.title, article.why_it_matters] if p and p.strip()
        )
        _add_if_unique(CHUNK_CONTEXT, _cap_words(context_text))

    if article.technical_highlights and article.technical_highlights.strip():
        technical_text = " ".join(
            p.strip() for p in [article.title, article.technical_highlights] if p and p.strip()
        )
        _add_if_unique(CHUNK_TECHNICAL, _cap_words(technical_text))

    return chunks


def build_embedding_id(url: str) -> str:
    """Base id derived from the article's URL. Chroma chunk ids are built as
    f"{embedding_id}:{chunk_type}" - this base value itself is what's stored
    in Postgres (articles.embedding_id), unchanged by the provider switch."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def build_chunk_id(embedding_id: str, chunk_type: str) -> str:
    return f"{embedding_id}:{chunk_type}"


@dataclass
class EmbeddedArticle:
    title: str
    url: str
    source_name: str
    published_at: Any
    raw_content: str
    clean_content: str
    category: str
    sub_category: str
    companies: list[str]
    importance: str
    summary_short: str
    key_takeaway: str
    why_it_matters: str
    technical_highlights: str
    embedding_id: str
    embedding: list[float]                    # primary vector (summary chunk) - kept for any
                                                # existing code expecting one vector per article
                                                # (e.g. duplicate-detection similarity checks)
    chunk_embeddings: dict[str, list[float]]   # all chunks actually produced, keyed by chunk type

    @classmethod
    def from_summarized(
        cls,
        article: SummarizedArticle,
        embedding_id: str,
        chunk_embeddings: dict[str, list[float]],
    ) -> "EmbeddedArticle":
        primary = chunk_embeddings.get(CHUNK_SUMMARY) or next(iter(chunk_embeddings.values()), [])
        return cls(
            **asdict(article),
            embedding_id=embedding_id,
            embedding=primary,
            chunk_embeddings=chunk_embeddings,
        )


@dataclass
class EmbeddingError:
    url: str
    reason: str


def embed_article(
    article: SummarizedArticle,
) -> tuple[EmbeddedArticle | None, EmbeddingError | None]:
    chunk_texts = build_chunk_texts(article)
    if not chunk_texts:
        return None, EmbeddingError(
            url=article.url, reason="empty summarized fields, nothing to embed"
        )

    try:
        chunk_types = list(chunk_texts.keys())
        vectors = _embed_texts([chunk_texts[t] for t in chunk_types])
    except Exception as exc:  # noqa: BLE001
        return None, EmbeddingError(url=article.url, reason=f"encoding failed: {exc}")

    embedding_id = build_embedding_id(article.url)
    chunk_embeddings = dict(zip(chunk_types, vectors))
    return EmbeddedArticle.from_summarized(article, embedding_id, chunk_embeddings), None


def embed_all(
    articles: list[SummarizedArticle],
    write_to_chroma: bool = True,
    batch_size: int = 100,
) -> tuple[list[EmbeddedArticle], list[EmbeddingError]]:
    valid: list[tuple[SummarizedArticle, dict[str, str]]] = []
    errors: list[EmbeddingError] = []

    for article in articles:
        chunk_texts = build_chunk_texts(article)
        if not chunk_texts:
            errors.append(
                EmbeddingError(url=article.url, reason="empty summarized fields, nothing to embed")
            )
            continue
        valid.append((article, chunk_texts))

    embedded: list[EmbeddedArticle] = []

    if valid:
        # Flatten every article's chunks into one list so a small number of
        # batched API calls covers all chunks across all articles, then
        # regroup by article afterward.
        flat_texts: list[str] = []
        flat_index: list[tuple[int, str]] = []  # (position in valid, chunk_type)
        for i, (_, chunk_texts) in enumerate(valid):
            for chunk_type, text in chunk_texts.items():
                flat_texts.append(text)
                flat_index.append((i, chunk_type))

        vectors: list[list[float]] | None
        try:
            vectors = _embed_texts(flat_texts, batch_size=batch_size)
        except Exception as exc:  # noqa: BLE001
            for article, _ in valid:
                errors.append(EmbeddingError(url=article.url, reason=f"encoding failed: {exc}"))
            vectors = None

        if vectors is not None:
            per_article_chunks: list[dict[str, list[float]]] = [dict() for _ in valid]
            for (article_i, chunk_type), vector in zip(flat_index, vectors):
                per_article_chunks[article_i][chunk_type] = vector

            for (article, _), chunk_embeddings in zip(valid, per_article_chunks):
                embedding_id = build_embedding_id(article.url)
                embedded.append(EmbeddedArticle.from_summarized(article, embedding_id, chunk_embeddings))

    if write_to_chroma and embedded:
        vectorstore = get_vectorstore(get_embedding_function())

        ids: list[str] = []
        embeddings: list[list[float]] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for a in embedded:
            chunk_texts = build_chunk_texts(a)
            for chunk_type, vector in a.chunk_embeddings.items():
                ids.append(build_chunk_id(a.embedding_id, chunk_type))
                embeddings.append(vector)
                documents.append(chunk_texts.get(chunk_type, ""))
                metadatas.append({
                    "url": a.url,
                    "title": a.title,
                    "category": a.category or "",
                    "importance": a.importance or "",
                    "chunk_type": chunk_type,
                })

        upsert_embeddings(
            vectorstore,
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    gc.collect()
    return embedded, errors


def embedding_node(state: dict) -> dict:
    articles = state.get("articles", [])
    embedded, errors = embed_all(articles, write_to_chroma=True)
    if errors:
        print("EMBED ERRORS:", errors[0].reason, "| count:", len(errors))
    else:
        print("No errors in embedding node")
    state["articles"] = embedded
    state["embedding_errors"] = errors
    return state