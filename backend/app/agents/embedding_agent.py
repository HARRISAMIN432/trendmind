from __future__ import annotations
import hashlib
import logging
from dataclasses import asdict, dataclass
from typing import Any, Optional
from app.vectorstore.chroma_client import get_vectorstore, upsert_embeddings
from app.core.config import get_settings
from app.agents.key_manager import SequentialKeyManager

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

EMBEDDING_MODEL_NAME = "models/gemini-embedding-001"
EMBEDDING_DIMENSIONS = 784

_google_embedding_key_manager: Optional[SequentialKeyManager] = None

_embedding_model_cache: dict[str, Any] = {}


def _get_google_embedding_manager() -> SequentialKeyManager:
    global _google_embedding_key_manager
    if _google_embedding_key_manager is None:
        settings = get_settings()
        _google_embedding_key_manager = SequentialKeyManager(settings.GOOGLE_API_KEYS)
        logger.info(
            f"Google embedding key manager initialized with "
            f"{len(_google_embedding_key_manager.keys)} keys"
        )
    return _google_embedding_key_manager


def _build_embedding_model(key: str):
    if key not in _embedding_model_cache:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        _embedding_model_cache[key] = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL_NAME,
            google_api_key=key,
            output_dimensionality=EMBEDDING_DIMENSIONS,
        )
    return _embedding_model_cache[key]


def get_embedding_model():
    manager = _get_google_embedding_manager()
    current_key = manager.get_current_key()
    if current_key is None:
        raise RuntimeError("All Google API keys exhausted or invalid for embeddings.")
    return _build_embedding_model(current_key)


def build_embedding_text(article: SummarizedArticle) -> str:
    return f"{article.title}\n\n{article.summary_short}".strip()


def build_embedding_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()  # 64 hex chars


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


def _embed_query_with_rotation(text: str) -> list[float]:
    manager = _get_google_embedding_manager()

    while manager.has_keys and manager.get_current_key():
        current_key = manager.get_current_key()
        key_short = manager.current_key_short
        try:
            logger.info(f"Attempting embed_query with key: {key_short} "
                        f"(remaining: {manager.remaining_keys})")
            model = _build_embedding_model(current_key)
            vector = model.embed_query(text)
            logger.info(f"embed_query succeeded with key: {key_short}")
            return vector
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Google embedding key {key_short} failed: {exc}")
            manager.mark_current_key_failed()
            continue

    raise RuntimeError("All Google API keys exhausted or invalid for embeddings.")


def _embed_documents_with_rotation(texts: list[str]) -> list[list[float]]:
    manager = _get_google_embedding_manager()

    while manager.has_keys and manager.get_current_key():
        current_key = manager.get_current_key()
        key_short = manager.current_key_short
        try:
            logger.info(f"Attempting embed_documents with key: {key_short} "
                        f"(remaining: {manager.remaining_keys}, batch size: {len(texts)})")
            model = _build_embedding_model(current_key)
            vectors = model.embed_documents(texts)
            logger.info(f"embed_documents succeeded with key: {key_short}")
            return vectors
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Google embedding key {key_short} failed: {exc}")
            manager.mark_current_key_failed()
            continue

    raise RuntimeError("All Google API keys exhausted or invalid for embeddings.")


def embed_article(
    article: SummarizedArticle,
) -> tuple[EmbeddedArticle | None, EmbeddingError | None]:
    text = build_embedding_text(article)
    if not text.strip():
        return None, EmbeddingError(
            url=article.url, reason="empty title+summary_short, nothing to embed"
        )

    try:
        vector = _embed_query_with_rotation(text)
    except Exception as exc:  # noqa: BLE001 - model load / encode failure
        return None, EmbeddingError(url=article.url, reason=f"encoding failed: {exc}")

    embedding_id = build_embedding_id(article.url)
    return EmbeddedArticle.from_summarized(article, embedding_id, vector), None


def embed_all(
    articles: list[SummarizedArticle],
    write_to_chroma: bool = True,
) -> tuple[list[EmbeddedArticle], list[EmbeddingError]]:
    valid: list[tuple[SummarizedArticle, str]] = []
    errors: list[EmbeddingError] = []

    for article in articles:
        text = build_embedding_text(article)
        if not text.strip():
            errors.append(
                EmbeddingError(
                    url=article.url,
                    reason="empty title+summary_short, nothing to embed",
                )
            )
            continue
        valid.append((article, text))

    embedded: list[EmbeddedArticle] = []

    if valid:
        try:
            vectors = _embed_documents_with_rotation([text for _, text in valid])
        except Exception as exc:  # noqa: BLE001 - batch encode failure
            for article, _ in valid:
                errors.append(
                    EmbeddingError(url=article.url, reason=f"encoding failed: {exc}")
                )
            vectors = None

        if vectors is not None:
            for (article, _), vector in zip(valid, vectors):
                embedding_id = build_embedding_id(article.url)
                embedded.append(
                    EmbeddedArticle.from_summarized(article, embedding_id, vector)
                )

    if write_to_chroma and embedded:
        vectorstore = get_vectorstore(get_embedding_model())
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

    return embedded, errors


def reset_embedding_key_manager() -> None:
    global _google_embedding_key_manager
    if _google_embedding_key_manager:
        _google_embedding_key_manager.reset()
        logger.info("Google embedding key manager reset to first key")


def embedding_node(state: dict) -> dict:
    articles = state.get("articles", [])
    embedded, errors = embed_all(articles, write_to_chroma=True)
    if errors:
        print("EMBED ERRORS:", errors[0].reason, "| count:", len(errors))  # temp
    else:
        print('No errors in embedding node')
    state["articles"] = embedded
    state["embedding_errors"] = errors
    return state