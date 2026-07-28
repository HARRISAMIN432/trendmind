from __future__ import annotations
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services import newsletter_service


def _article(
    title="Title",
    url="https://example.com/a",
    category="Research",
    importance="High",
    published_at=None,
    summary_short="Summary.",
    source_name="TechCrunch",
):
    return SimpleNamespace(
        title=title,
        url=url,
        category=category,
        importance=importance,
        published_at=published_at or datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc),
        summary_short=summary_short,
        source=SimpleNamespace(name=source_name),
    )


def _trend(
    title="Agentic AI heats up",
    description="Multiple labs shipped agent frameworks this week.",
    articles=None,
):
    return SimpleNamespace(
        title=title,
        description=description,
        articles=articles if articles is not None else [SimpleNamespace(), SimpleNamespace()],
    )


class TestSortKey:
    def test_high_importance_sorts_before_low(self):
        articles = [
            _article(title="Low prio", importance="Low"),
            _article(title="High prio", importance="High"),
        ]
        articles.sort(key=newsletter_service._sort_key)
        assert articles[0].title == "High prio"

    def test_missing_importance_sorts_last(self):
        articles = [
            _article(title="Unranked", importance=None),
            _article(title="Medium", importance="Medium"),
        ]
        articles.sort(key=newsletter_service._sort_key)
        assert articles[0].title == "Medium"
        assert articles[1].title == "Unranked"

    def test_same_importance_sorts_most_recent_first(self):
        older = _article(title="Older", published_at=datetime(2026, 7, 25, tzinfo=timezone.utc))
        newer = _article(title="Newer", published_at=datetime(2026, 7, 27, tzinfo=timezone.utc))
        articles = [older, newer]
        articles.sort(key=newsletter_service._sort_key)
        assert articles[0].title == "Newer"

    def test_missing_published_at_does_not_crash_sort(self):
        articles = [_article(title="No date", published_at=None), _article(title="Has date")]
        # published_at=None falls back to datetime(...) constructor default above via `or`,
        # so exercise the true None path directly instead.
        articles[0].published_at = None
        articles.sort(key=newsletter_service._sort_key)
        assert len(articles) == 2


class TestRenderMarkdown:
    def test_includes_all_top_stories(self):
        articles = [
            _article(title="Story One", url="https://x.com/1"),
            _article(title="Story Two", url="https://x.com/2"),
        ]
        md = newsletter_service._render_markdown(date(2026, 7, 27), articles, None)
        assert "Story One" in md
        assert "Story Two" in md
        assert "https://x.com/1" in md

    def test_empty_top_stories_shows_placeholder(self):
        md = newsletter_service._render_markdown(date(2026, 7, 27), [], None)
        assert "No qualifying stories" in md

    def test_trend_section_included_when_present(self):
        md = newsletter_service._render_markdown(date(2026, 7, 27), [], _trend())
        assert "Agentic AI heats up" in md
        assert "Tracked across 2 articles" in md

    def test_trend_section_singular_article_count(self):
        md = newsletter_service._render_markdown(
            date(2026, 7, 27), [], _trend(articles=[SimpleNamespace()])
        )
        assert "Tracked across 1 article." in md

    def test_trend_section_placeholder_when_missing(self):
        md = newsletter_service._render_markdown(date(2026, 7, 27), [], None)
        assert "No trend has been generated yet" in md

    def test_output_starts_with_digest_title(self):
        md = newsletter_service._render_markdown(date(2026, 7, 27), [], None)
        assert md.startswith("# TrendMind Daily Digest — 2026-07-27")

    def test_missing_summary_falls_back_to_placeholder_text(self):
        article = _article(summary_short=None)
        md = newsletter_service._render_markdown(date(2026, 7, 27), [article], None)
        assert "No summary available." in md


class TestGenerateNewsletter:
    @patch("app.services.newsletter_service._get_biggest_trend")
    @patch("app.services.newsletter_service._get_top_stories")
    def test_creates_new_entry_when_none_exists_for_date(self, mock_top_stories, mock_trend):
        mock_top_stories.return_value = [_article()]
        mock_trend.return_value = None

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        entry, top_story_count, trend_included = newsletter_service.generate_newsletter(
            db, digest_date=date(2026, 7, 27)
        )

        assert db.add.called
        assert db.commit.called
        assert entry.digest_date == date(2026, 7, 27)
        assert top_story_count == 1
        assert trend_included is False

    @patch("app.services.newsletter_service._get_biggest_trend")
    @patch("app.services.newsletter_service._get_top_stories")
    def test_overwrites_existing_entry_for_same_date_instead_of_duplicating(
        self, mock_top_stories, mock_trend
    ):
        mock_top_stories.return_value = []
        mock_trend.return_value = _trend()

        existing_entry = SimpleNamespace(digest_date=date(2026, 7, 27), content_markdown="stale")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = existing_entry

        entry, top_story_count, trend_included = newsletter_service.generate_newsletter(
            db, digest_date=date(2026, 7, 27)
        )

        assert not db.add.called  # existing row mutated, no second row created
        assert entry is existing_entry
        assert entry.content_markdown != "stale"
        assert "Agentic AI heats up" in entry.content_markdown
        assert trend_included is True

    @patch("app.services.newsletter_service._get_biggest_trend")
    @patch("app.services.newsletter_service._get_top_stories")
    def test_window_spans_lookback_days(self, mock_top_stories, mock_trend):
        mock_top_stories.return_value = []
        mock_trend.return_value = None
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        newsletter_service.generate_newsletter(db, digest_date=date(2026, 7, 27), lookback_days=3)

        args, _ = mock_top_stories.call_args
        window_start, window_end = args[1], args[2]
        assert (window_end - window_start).days == 3
        assert window_end == datetime(2026, 7, 28, tzinfo=timezone.utc)

    @patch("app.services.newsletter_service._get_biggest_trend")
    @patch("app.services.newsletter_service._get_top_stories")
    def test_top_stories_limit_is_forwarded(self, mock_top_stories, mock_trend):
        mock_top_stories.return_value = []
        mock_trend.return_value = None
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        newsletter_service.generate_newsletter(
            db, digest_date=date(2026, 7, 27), top_stories_limit=8
        )

        args, _ = mock_top_stories.call_args
        assert args[3] == 8

    @patch("app.services.newsletter_service._get_biggest_trend")
    @patch("app.services.newsletter_service._get_top_stories")
    def test_defaults_digest_date_to_today_utc_when_omitted(self, mock_top_stories, mock_trend):
        mock_top_stories.return_value = []
        mock_trend.return_value = None
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        entry, _, _ = newsletter_service.generate_newsletter(db, digest_date=None)

        assert entry.digest_date == datetime.now(timezone.utc).date()


class TestGetAndListNewsletters:
    def test_get_newsletter_by_date_returns_none_when_missing(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        assert newsletter_service.get_newsletter_by_date(db, date(2026, 7, 27)) is None

    def test_list_newsletters_returns_items_and_total(self):
        db = MagicMock()
        query = db.query.return_value
        query.order_by.return_value = query
        query.limit.return_value = query
        query.offset.return_value = query
        query.all.return_value = ["entry1", "entry2"]
        query.count.return_value = 2

        items, total = newsletter_service.list_newsletters(db, limit=20, offset=0)

        assert items == ["entry1", "entry2"]
        assert total == 2