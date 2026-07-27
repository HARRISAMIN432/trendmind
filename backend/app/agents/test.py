from __future__ import annotations
from unittest.mock import Mock, patch
import pytest

from app.agents.collector_agent import (
    CollectedArticle,
    collect_all,
    collector_node,
    fetch_feed,
)
from app.config.feeds import FeedConfig

VALID_FEED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Fake AI News</title>
    <item>
      <title>New Model Beats Benchmark</title>
      <link>https://example.com/articles/1</link>
      <pubDate>Mon, 27 Jul 2026 10:00:00 GMT</pubDate>
      <description>&lt;p&gt;A new model was announced today.&lt;/p&gt;</description>
    </item>
    <item>
      <title>Second Story</title>
      <link>https://example.com/articles/2</link>
      <pubDate>Mon, 27 Jul 2026 09:00:00 GMT</pubDate>
      <description>Some other AI news.</description>
    </item>
  </channel>
</rss>
"""

MALFORMED_XML = b"<rss><channel><item><title>Broken"

DUPLICATE_ITEM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Dup Story</title>
      <link>https://example.com/articles/1</link>
      <description>Same URL as feed A</description>
    </item>
  </channel>
</rss>
"""


def _mock_response(content: bytes, status: int = 200) -> Mock:
    response = Mock()
    response.content = content
    response.status_code = status
    response.raise_for_status = Mock()
    if status >= 400:
        import requests

        response.raise_for_status.side_effect = requests.HTTPError(f"{status} error")
    return response


FEED_A = FeedConfig(name="Feed A", rss_url="https://feeda.example.com/rss")
FEED_B = FeedConfig(name="Feed B", rss_url="https://feedb.example.com/rss")
FEED_BROKEN = FeedConfig(name="Feed Broken", rss_url="https://broken.example.com/rss")
FEED_UNREACHABLE = FeedConfig(name="Feed Unreachable", rss_url="https://down.example.com/rss")


class TestFetchFeed:
    def test_normalizes_valid_entries(self):
        with patch("app.agents.collector_agent.requests.get") as mock_get:
            mock_get.return_value = _mock_response(VALID_FEED_XML.encode())
            articles, error = fetch_feed(FEED_A)

        assert error is None
        assert len(articles) == 2
        first = articles[0]
        assert isinstance(first, CollectedArticle)
        assert first.title == "New Model Beats Benchmark"
        assert first.url == "https://example.com/articles/1"
        assert first.source_name == "Feed A"
        assert first.published_at is not None
        assert first.published_at.year == 2026
        assert "A new model was announced today." in (first.raw_content or "")

    def test_network_failure_is_captured_not_raised(self):
        import requests

        with patch("app.agents.collector_agent.requests.get") as mock_get:
            mock_get.side_effect = requests.ConnectionError("DNS failure")
            articles, error = fetch_feed(FEED_UNREACHABLE)

        assert articles == []
        assert error is not None
        assert error.source_name == "Feed Unreachable"
        assert "DNS failure" in error.error

    def test_http_error_status_is_captured_not_raised(self):
        with patch("app.agents.collector_agent.requests.get") as mock_get:
            mock_get.return_value = _mock_response(b"", status=503)
            articles, error = fetch_feed(FEED_UNREACHABLE)

        assert articles == []
        assert error is not None

    def test_malformed_xml_with_no_entries_is_captured_not_raised(self):
        with patch("app.agents.collector_agent.requests.get") as mock_get:
            mock_get.return_value = _mock_response(MALFORMED_XML)
            articles, error = fetch_feed(FEED_BROKEN)

        assert articles == []
        assert error is not None
        assert "parse error" in error.error

    def test_entries_missing_link_or_title_are_skipped(self):
        xml = """<?xml version="1.0"?>
        <rss version="2.0"><channel>
          <item><title>Has both</title><link>https://example.com/ok</link></item>
          <item><title>No link here</title></item>
          <item><link>https://example.com/no-title</link></item>
        </channel></rss>"""
        with patch("app.agents.collector_agent.requests.get") as mock_get:
            mock_get.return_value = _mock_response(xml.encode())
            articles, error = fetch_feed(FEED_A)

        assert error is None
        assert len(articles) == 1
        assert articles[0].url == "https://example.com/ok"


class TestCollectAll:
    def test_one_dead_feed_does_not_block_others(self):
        def fake_get(url, timeout, headers):
            if "feeda" in url:
                return _mock_response(VALID_FEED_XML.encode())
            raise __import__("requests").ConnectionError("unreachable")

        with patch("app.agents.collector_agent.requests.get", side_effect=fake_get):
            result = collect_all(feeds=[FEED_A, FEED_UNREACHABLE])

        assert len(result.articles) == 2
        assert len(result.errors) == 1
        assert result.errors[0].source_name == "Feed Unreachable"

    def test_dedupes_across_feeds_by_url(self):
        def fake_get(url, timeout, headers):
            if "feeda" in url:
                return _mock_response(VALID_FEED_XML.encode())
            return _mock_response(DUPLICATE_ITEM_XML.encode())

        with patch("app.agents.collector_agent.requests.get", side_effect=fake_get):
            result = collect_all(feeds=[FEED_A, FEED_B])

        urls = [a.url for a in result.articles]
        assert urls.count("https://example.com/articles/1") == 1
        # Feed A's 2 unique items + Feed B's duplicate collapsed away
        assert len(result.articles) == 2

    def test_filters_out_existing_urls(self):
        with patch("app.agents.collector_agent.requests.get") as mock_get:
            mock_get.return_value = _mock_response(VALID_FEED_XML.encode())
            result = collect_all(
                feeds=[FEED_A],
                existing_urls={"https://example.com/articles/1"},
            )

        urls = [a.url for a in result.articles]
        assert "https://example.com/articles/1" not in urls
        assert "https://example.com/articles/2" in urls


class TestCollectorNode:
    def test_populates_state_with_articles_and_errors(self):
        with patch("app.agents.collector_agent.requests.get") as mock_get:
            mock_get.return_value = _mock_response(VALID_FEED_XML.encode())
            with patch("app.agents.collector_agent.AI_NEWS_FEEDS", [FEED_A]):
                state = collector_node({})

        assert "articles" in state
        assert "collector_errors" in state
        assert len(state["articles"]) == 2
        assert state["collector_errors"] == []

    def test_passes_through_existing_urls_from_state(self):
        with patch("app.agents.collector_agent.requests.get") as mock_get:
            mock_get.return_value = _mock_response(VALID_FEED_XML.encode())
            with patch("app.agents.collector_agent.AI_NEWS_FEEDS", [FEED_A]):
                state = collector_node(
                    {"existing_urls": {"https://example.com/articles/1"}}
                )

        urls = [a.url for a in state["articles"]]
        assert urls == ["https://example.com/articles/2"]