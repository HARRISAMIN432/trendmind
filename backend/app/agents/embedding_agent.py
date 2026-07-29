from __future__ import annotations
import hashlib
from dataclasses import asdict, dataclass
from typing import Any
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


EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None  


def get_embedding_model():
    global _model
    if _model is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        _model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            encode_kwargs={"normalize_embeddings": True},
        )
    return _model


def build_embedding_text(article: SummarizedArticle) -> str:
    """The exact text that gets embedded. See module docstring for reasoning."""
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
        vector = model.embed_query(text)
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
            model = get_embedding_model()
            vectors = model.embed_documents([text for _, text in valid])
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