from __future__ import annotations
from typing import Any, TypedDict
from app.agents.classification_agent import ClassificationError
from app.agents.cleaner_agent import CleaningError
from app.agents.collector_agent import FeedFetchError
from app.agents.embedding_agent import EmbeddedArticle, EmbeddingError
from app.agents.summarization_agent import SummarizationError


class PipelineState(TypedDict, total=False):
    articles: list[Any]
    existing_urls: set[str]
    existing_embedded_articles: list[EmbeddedArticle]
    collector_errors: list[FeedFetchError]
    cleaner_errors: list[CleaningError]
    classification_errors: list[ClassificationError]
    summarization_errors: list[SummarizationError]
    embedding_errors: list[EmbeddingError]
    duplicate_count: int