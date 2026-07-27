from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import mktime
from typing import Any, Iterable, Optional
import feedparser
import requests
from app.config.feeds import AI_NEWS_FEEDS, FeedConfig

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 10
USER_AGENT = "TrendMind-Collector/1.0 (+https://github.com/your-repo/trendmind)"


@dataclass
class CollectedArticle:
    """Common normalized schema every feed's entries get mapped into."""

    title: str
    url: str
    source_name: str
    published_at: Optional[datetime]
    raw_content: Optional[str]


@dataclass
class FeedFetchError:
    source_name: str
    rss_url: str
    error: str


@dataclass
class CollectionResult:
    articles: list[CollectedArticle] = field(default_factory=list)
    errors: list[FeedFetchError] = field(default_factory=list)


def _parse_published_at(entry: dict[str, Any]) -> Optional[datetime]:
    """
    feedparser exposes a pre-parsed time.struct_time on `published_parsed`
    (or `updated_parsed` for feeds that only set that). Not every feed
    sets either, so we fall back to None rather than guessing.
    """
    struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if not struct_time:
        return None
    try:
        return datetime.fromtimestamp(mktime(struct_time), tz=timezone.utc)
    except (OverflowError, ValueError):
        return None


def _extract_raw_content(entry: dict[str, Any]) -> Optional[str]:
    """
    Prefer full content (`content`) over the short `summary`/`description`
    when a feed provides both. This is still HTML at this stage — the
    Cleaner Agent (M03) is responsible for stripping tags/boilerplate.
    """
    if entry.get("content"):
        # feedparser's `content` is a list of dicts with a `value` key
        pieces = [c.get("value", "") for c in entry["content"] if c.get("value")]
        if pieces:
            return "\n".join(pieces)
    return entry.get("summary") or entry.get("description")


def fetch_feed(feed: FeedConfig) -> tuple[list[CollectedArticle], Optional[FeedFetchError]]:
    """
    Fetch and normalize a single feed. Never raises — on any failure it
    returns an empty article list plus a FeedFetchError describing why.
    """
    try:
        response = requests.get(
            feed.rss_url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Failed to fetch feed %s: %s", feed.name, exc)
        return [], FeedFetchError(feed.name, feed.rss_url, str(exc))

    parsed = feedparser.parse(response.content)

    articles: list[CollectedArticle] = []
    for entry in parsed.entries:
        url = entry.get("link")
        title = entry.get("title")
        if not url or not title:
            # Skip entries missing the two fields we treat as required
            continue
        articles.append(
            CollectedArticle(
                title=title.strip(),
                url=url.strip(),
                source_name=feed.name,
                published_at=_parse_published_at(entry),
                raw_content=_extract_raw_content(entry),
            )
        )

    # feedparser sets `bozo=1` on malformed XML rather than raising, and
    # is often lenient enough to recover a stub entry with no usable
    # fields (which the loop above then skips). We only treat bozo as a
    # hard per-feed failure when it left us with zero usable articles —
    # a feed that's merely slightly off-spec but still yields real
    # entries should not be discarded.
    if parsed.bozo and not articles:
        error_msg = str(parsed.get("bozo_exception", "unknown parse error"))
        logger.warning("Malformed feed %s: %s", feed.name, error_msg)
        return [], FeedFetchError(feed.name, feed.rss_url, f"parse error: {error_msg}")

    return articles, None


def _dedupe_by_url(articles: Iterable[CollectedArticle]) -> list[CollectedArticle]:
    seen: set[str] = set()
    deduped: list[CollectedArticle] = []
    for article in articles:
        if article.url in seen:
            continue
        seen.add(article.url)
        deduped.append(article)
    return deduped


def collect_all(
    feeds: list[FeedConfig] | None = None,
    existing_urls: set[str] | None = None,
) -> CollectionResult:
    """
    Fetch every configured feed and return normalized, deduped articles.

    Args:
        feeds: override the default feed list (mainly for tests).
        existing_urls: optional set of URLs already present in the
            `articles` table. When provided, matching articles are
            filtered out so re-runs don't reprocess old news. Pass
            this in from the caller (e.g. the LangGraph node or the
            scheduler) rather than importing the DB session here, to
            keep this module DB-agnostic and easy to unit test.
    """
    feeds = feeds if feeds is not None else AI_NEWS_FEEDS
    result = CollectionResult()

    for feed in feeds:
        feed_articles, error = fetch_feed(feed)
        if error:
            result.errors.append(error)
        result.articles.extend(feed_articles)

    result.articles = _dedupe_by_url(result.articles)

    if existing_urls:
        result.articles = [a for a in result.articles if a.url not in existing_urls]

    logger.info(
        "Collector run complete: %d new articles, %d feed errors",
        len(result.articles),
        len(result.errors),
    )
    return result


def collector_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph-compatible node for the M08 pipeline graph.

    Reads (optional, from state):
        - "existing_urls": set[str] of URLs already in the DB, if the
          caller wants to skip already-collected articles.

    Writes to state:
        - "articles": list[CollectedArticle] ready for the Cleaner
          Agent (M03).
        - "collector_errors": list[FeedFetchError] for observability /
          error-handling edges in the graph (M08 constraint: "conditional
          edges and error handling/retries").
    """
    existing_urls = state.get("existing_urls")
    result = collect_all(existing_urls=existing_urls)
    state["articles"] = result.articles
    state["collector_errors"] = result.errors
    return state