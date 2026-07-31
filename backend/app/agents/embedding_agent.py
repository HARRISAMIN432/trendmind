from __future__ import annotations
import gc
import hashlib
import logging
from dataclasses import asdict, dataclass
from typing import Any, Optional
from app.vectorstore.chroma_client import get_vectorstore, upsert_embeddings, FastEmbedWrapper

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

EMBEDDING_MODEL_NAME = "d"
EMBEDDING_DIMENSIONS = 384

_embedding_model: Optional[Any] = None
_wrapped_model: Optional[FastEmbedWrapper] = None


def get_embedding_model():
    """Lazily load a single quantized ONNX MiniLM instance, reused for the process lifetime."""
    global _embedding_model
    if _embedding_model is None:
        from fastembed import TextEmbedding

        logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
        _embedding_model = TextEmbedding(
            model_name=EMBEDDING_MODEL_NAME,
            threads=1,
            cache_dir="/tmp/fastembed_cache",
        )
        logger.info("Embedding model loaded")
    return _embedding_model


def get_embedding_function() -> FastEmbedWrapper:
    """LangChain-compatible wrapper around the fastembed model, for use with Chroma(embedding_function=...)."""
    global _wrapped_model
    if _wrapped_model is None:
        _wrapped_model = FastEmbedWrapper(get_embedding_model())
    return _wrapped_model


def build_embedding_text(article: SummarizedArticle) -> str:
    return f"{article.title}\n\n{article.summary_short}".strip()


def build_embedding_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


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
    embedding: list[float]

    @classmethod
    def from_summarized(
        cls, article: SummarizedArticle, embedding_id: str, embedding: list[float]
    ) -> "EmbeddedArticle":
        return cls(**asdict(article), embedding_id=embedding_id, embedding=embedding)


@dataclass
class EmbeddingError:
    url: str
    reason: str


def embed_article(
    article: SummarizedArticle,
) -> tuple[EmbeddedArticle | None, EmbeddingError | None]:
    text = build_embedding_text(article)
    if not text.strip():
        return None, EmbeddingError(
            url=article.url, reason="empty title+summary_short, nothing to embed"
        )

    try:
        model = get_embedding_model()
        vector = next(model.embed([text])).tolist()
    except Exception as exc:  # noqa: BLE001
        return None, EmbeddingError(url=article.url, reason=f"encoding failed: {exc}")

    embedding_id = build_embedding_id(article.url)
    return EmbeddedArticle.from_summarized(article, embedding_id, vector), None


def embed_all(
    articles: list[SummarizedArticle],
    write_to_chroma: bool = True,
    batch_size: int = 8,
) -> tuple[list[EmbeddedArticle], list[EmbeddingError]]:
    valid: list[tuple[SummarizedArticle, str]] = []
    errors: list[EmbeddingError] = []

    for article in articles:
        text = build_embedding_text(article)
        if not text.strip():
            errors.append(
                EmbeddingError(url=article.url, reason="empty title+summary_short, nothing to embed")
            )
            continue
        valid.append((article, text))

    embedded: list[EmbeddedArticle] = []

    if valid:
        try:
            model = get_embedding_model()
            texts = [text for _, text in valid]
            vectors: list[list[float]] = []
            for vec in model.embed(texts, batch_size=batch_size):
                vectors.append(vec.tolist())
        except Exception as exc:  # noqa: BLE001
            for article, _ in valid:
                errors.append(EmbeddingError(url=article.url, reason=f"encoding failed: {exc}"))
            vectors = None

        if vectors is not None:
            for (article, _), vector in zip(valid, vectors):
                embedding_id = build_embedding_id(article.url)
                embedded.append(EmbeddedArticle.from_summarized(article, embedding_id, vector))

    if write_to_chroma and embedded:
        vectorstore = get_vectorstore(get_embedding_function())
        upsert_embeddings(
            vectorstore,
            ids=[a.embedding_id for a in embedded],
            embeddings=[a.embedding for a in embedded],
            documents=[build_embedding_text(a) for a in embedded],
            metadatas=[
                {
                    "url": a.url,
                    "title": a.title,
                    "category": a.category or "",
                    "importance": a.importance or "",
                }
                for a in embedded
            ],
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