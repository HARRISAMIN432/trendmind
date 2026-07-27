from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional
import trafilatura
from app.agents.collector_agent import CollectedArticle

logger = logging.getLogger(__name__)

MIN_CLEAN_CONTENT_LENGTH = 200


@dataclass
class CleanedArticle:
    """
    Common normalized schema every M03-processed article gets mapped
    into. This is CollectedArticle (M02) plus `clean_content`, which is
    what M04 (Classification Agent) and M05 (Summarization Agent)
    consume next.
    """

    title: str
    url: str
    source_name: str
    published_at: Any  # Optional[datetime], re-exported as-is from CollectedArticle
    raw_content: Optional[str]
    clean_content: Optional[str]


@dataclass
class CleaningError:
    url: str
    source_name: str
    error: str


@dataclass
class CleaningResult:
    articles: list[CleanedArticle] = field(default_factory=list)
    errors: list[CleaningError] = field(default_factory=list)


def _dedupe_by_url(articles: Iterable[CollectedArticle]) -> list[CollectedArticle]:
    """
    Exact-URL dedup. This is a second, defensive pass — collect_all()
    (M02) already dedupes within a single collector run — but M03 may
    be called on articles assembled from multiple runs/sources (e.g.
    the LangGraph state accumulating across retries), so we re-apply
    it here rather than assume the input is already clean.
    """
    seen: set[str] = set()
    deduped: list[CollectedArticle] = []
    for article in articles:
        if article.url in seen:
            continue
        seen.add(article.url)
        deduped.append(article)
    return deduped


def clean_article(article: CollectedArticle) -> tuple[Optional[CleanedArticle], Optional[CleaningError]]:
    """
    Extract clean article text from one CollectedArticle's raw_content.
    Never raises — on any failure it returns (None, CleaningError).

    Uses trafilatura against the raw HTML we already fetched in M02
    (no second network request — trafilatura.extract() works directly
    on a string of HTML, it does not need to fetch the URL itself).
    """
    if not article.raw_content or not article.raw_content.strip():
        return None, CleaningError(
            article.url, article.source_name, "no raw_content to clean (empty or missing)"
        )

    try:
        extracted = trafilatura.extract(
            article.raw_content,
            url=article.url,
            include_comments=False,
            include_tables=False,
            favor_recall=True,
        )
    except Exception as exc:  # trafilatura can raise on pathological/malformed HTML
        logger.warning("trafilatura raised while cleaning %s: %s", article.url, exc)
        return None, CleaningError(article.url, article.source_name, str(exc))

    if not extracted or len(extracted.strip()) < MIN_CLEAN_CONTENT_LENGTH:
        # Common for feeds whose raw_content is just a short RSS
        # summary/teaser rather than full article HTML (e.g. some
        # ArXiv/Google News entries) — trafilatura has nothing
        # substantial to pull out of a one-line teaser.
        return None, CleaningError(
            article.url,
            article.source_name,
            "extraction produced no usable content (raw_content likely a teaser, not full HTML)",
        )

    cleaned = CleanedArticle(
        title=article.title,
        url=article.url,
        source_name=article.source_name,
        published_at=article.published_at,
        raw_content=article.raw_content,
        clean_content=extracted.strip(),
    )
    return cleaned, None


def clean_all(articles: list[CollectedArticle]) -> CleaningResult:
    """
    Clean a batch of CollectedArticles. Isolates failures per-article
    (one unparseable article never blocks the rest of the batch),
    same isolation pattern as M02's collect_all().
    """
    result = CleaningResult()
    deduped = _dedupe_by_url(articles)

    for article in deduped:
        cleaned, error = clean_article(article)
        if error:
            result.errors.append(error)
            continue
        result.articles.append(cleaned)

    logger.info(
        "Cleaner run complete: %d cleaned, %d skipped/errored",
        len(result.articles),
        len(result.errors),
    )
    return result


def cleaner_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph-compatible node for the M08 pipeline graph.

    Reads (from state):
        - "articles": list[CollectedArticle] written by M02's
          collector_node.

    Writes to state:
        - "articles": overwritten with list[CleanedArticle] — articles
          that failed cleaning are dropped from the pipeline here
          rather than carried forward with a null clean_content, since
          M04/M05 both require clean_content to do their job.
        - "cleaner_errors": list[CleaningError] for observability /
          error-handling edges in the graph (same M08 constraint as
          M02's "collector_errors").
    """
    incoming: list[CollectedArticle] = state.get("articles", [])
    result = clean_all(incoming)
    state["articles"] = result.articles
    state["cleaner_errors"] = result.errors
    return state