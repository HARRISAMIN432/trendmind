from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.agents.cleaner_agent import (
    CleaningError,
    clean_all,
    clean_article,
    cleaner_node,
)
from app.agents.collector_agent import CollectedArticle


ARTICLE_HTML = """
<html><head><title>Big AI News</title></head>
<body>
<nav>Home | About | Contact</nav>
<article>
<h1>Big AI News</h1>
<p>Researchers today announced a major breakthrough in transformer architectures
that promises to reduce training costs significantly across the industry.</p>
<p>The team, spread across three continents, spent over a year refining the
approach before publishing their results in a peer reviewed venue, and industry
watchers expect rapid adoption given the magnitude of the reported gains.</p>
</article>
<footer>Copyright 2026 - Privacy Policy - Terms</footer>
</body></html>
"""


def make_article(**overrides) -> CollectedArticle:
    defaults = dict(
        title="Big AI News",
        url="https://example.com/big-ai-news",
        source_name="TechCrunch AI",
        published_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
        raw_content=ARTICLE_HTML,
    )
    defaults.update(overrides)
    return CollectedArticle(**defaults)


class TestCleanArticle:
    def test_normal_extraction(self):
        cleaned, error = clean_article(make_article())
        assert error is None
        assert cleaned is not None
        assert cleaned.url == "https://example.com/big-ai-news"
        assert cleaned.title == "Big AI News"
        assert "breakthrough in transformer architectures" in cleaned.clean_content
        # Boilerplate should not survive extraction.
        assert "Copyright 2026" not in cleaned.clean_content
        assert "Home | About | Contact" not in cleaned.clean_content
        # Original fields carried through untouched.
        assert cleaned.raw_content == ARTICLE_HTML
        assert cleaned.published_at == datetime(2026, 7, 20, tzinfo=timezone.utc)

    def test_missing_raw_content_is_skipped_not_raised(self):
        cleaned, error = clean_article(make_article(raw_content=None))
        assert cleaned is None
        assert isinstance(error, CleaningError)
        assert "no raw_content" in error.error

    def test_blank_raw_content_is_skipped(self):
        cleaned, error = clean_article(make_article(raw_content="   "))
        assert cleaned is None
        assert isinstance(error, CleaningError)

    def test_teaser_only_content_below_threshold_is_skipped(self):
        # Simulates feeds (e.g. some ArXiv/Google News entries) whose
        # raw_content is just a short RSS summary, not full HTML.
        cleaned, error = clean_article(make_article(raw_content="<p>Short teaser.</p>"))
        assert cleaned is None
        assert isinstance(error, CleaningError)
        assert "no usable content" in error.error

    def test_trafilatura_exception_is_isolated(self):
        with patch("app.agents.cleaner_agent.trafilatura.extract", side_effect=RuntimeError("boom")):
            cleaned, error = clean_article(make_article())
        assert cleaned is None
        assert isinstance(error, CleaningError)
        assert "boom" in error.error

    def test_malformed_html_does_not_raise(self):
        # Missing closing tags etc. — trafilatura is generally lenient,
        # this just confirms clean_article never propagates an exception.
        cleaned, error = clean_article(make_article(raw_content="<html><body><p>Unclosed paragraph"))
        assert cleaned is None or isinstance(cleaned.clean_content, str)
        assert error is None or isinstance(error, CleaningError)


class TestCleanAll:
    def test_batch_isolates_failures(self):
        good = make_article()
        bad = make_article(url="https://example.com/empty", raw_content=None)
        result = clean_all([good, bad])
        assert len(result.articles) == 1
        assert result.articles[0].url == good.url
        assert len(result.errors) == 1
        assert result.errors[0].url == bad.url

    def test_exact_url_dedup(self):
        first = make_article()
        duplicate = make_article()  # same URL
        result = clean_all([first, duplicate])
        assert len(result.articles) == 1

    def test_empty_input(self):
        result = clean_all([])
        assert result.articles == []
        assert result.errors == []


class TestCleanerNode:
    def test_state_contract(self):
        state = {"articles": [make_article()]}
        new_state = cleaner_node(state)
        assert "articles" in new_state
        assert "cleaner_errors" in new_state
        assert len(new_state["articles"]) == 1
        assert new_state["articles"][0].clean_content is not None

    def test_missing_articles_key_defaults_to_empty(self):
        state: dict = {}
        new_state = cleaner_node(state)
        assert new_state["articles"] == []
        assert new_state["cleaner_errors"] == []

    def test_failed_articles_are_dropped_from_pipeline_state(self):
        state = {"articles": [make_article(raw_content=None)]}
        new_state = cleaner_node(state)
        assert new_state["articles"] == []
        assert len(new_state["cleaner_errors"]) == 1