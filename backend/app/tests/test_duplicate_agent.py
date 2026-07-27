from datetime import datetime, timedelta, timezone

from app.agents.duplicate_agent import (
    DeduplicatedArticle,
    cosine_similarity,
    duplicate_node,
    find_duplicates,
)
from app.agents.embedding_agent import EmbeddedArticle

BASE_TIME = datetime(2026, 7, 1, tzinfo=timezone.utc)


def make_embedded(
    url,
    embedding,
    published_at=None,
    title="Some title",
):
    return EmbeddedArticle(
        title=title,
        url=url,
        source_name="TechCrunch AI",
        published_at=published_at,
        raw_content="<html>...</html>",
        clean_content="clean text",
        category="Product Launch",
        sub_category="Model Release",
        companies=["OpenAI"],
        importance="High",
        summary_short="summary",
        key_takeaway="takeaway",
        why_it_matters="matters",
        technical_highlights="",
        embedding_id=f"id-{url}",
        embedding=embedding,
    )


class TestCosineSimilarity:
    def test_identical_vectors(self):
        assert cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == 1.0

    def test_orthogonal_vectors(self):
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0

    def test_opposite_vectors(self):
        assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == -1.0

    def test_empty_vector_returns_zero(self):
        assert cosine_similarity([], [1.0]) == 0.0

    def test_mismatched_length_returns_zero(self):
        assert cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0

    def test_zero_vector_returns_zero(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


class TestFindDuplicates:
    def test_no_duplicates_when_dissimilar(self):
        a = make_embedded("https://a.com", [1.0, 0.0], BASE_TIME)
        b = make_embedded("https://b.com", [0.0, 1.0], BASE_TIME + timedelta(hours=1))

        result = find_duplicates([a, b])

        assert len(result) == 2
        assert all(not r.is_duplicate for r in result)

    def test_near_identical_vectors_flagged_as_duplicate(self):
        earlier = make_embedded("https://earlier.com", [1.0, 0.0], BASE_TIME)
        later = make_embedded(
            "https://later.com", [0.99, 0.01], BASE_TIME + timedelta(hours=2)
        )

        result = find_duplicates([earlier, later])
        by_url = {r.url: r for r in result}

        assert by_url["https://earlier.com"].is_duplicate is False
        assert by_url["https://later.com"].is_duplicate is True
        assert by_url["https://later.com"].duplicate_of_url == "https://earlier.com"
        assert by_url["https://later.com"].similarity_score >= 0.92

    def test_earliest_published_becomes_canonical_regardless_of_input_order(self):
        later = make_embedded(
            "https://later.com", [1.0, 0.0], BASE_TIME + timedelta(hours=5)
        )
        earlier = make_embedded("https://earlier.com", [1.0, 0.0], BASE_TIME)

        # Pass `later` first in the input list -- canonical selection should
        # still prefer `earlier` based on published_at, not input order.
        result = find_duplicates([later, earlier])
        by_url = {r.url: r for r in result}

        assert by_url["https://earlier.com"].is_duplicate is False
        assert by_url["https://later.com"].is_duplicate is True
        assert by_url["https://later.com"].duplicate_of_url == "https://earlier.com"

    def test_original_input_order_preserved_in_output(self):
        a = make_embedded("https://a.com", [1.0, 0.0], BASE_TIME)
        b = make_embedded("https://b.com", [0.0, 1.0], BASE_TIME)
        c = make_embedded("https://c.com", [0.5, 0.5], BASE_TIME)

        result = find_duplicates([c, a, b])

        assert [r.url for r in result] == ["https://c.com", "https://a.com", "https://b.com"]

    def test_undated_article_sorts_after_dated_ones_for_canonical_selection(self):
        dated = make_embedded("https://dated.com", [1.0, 0.0], BASE_TIME)
        undated = make_embedded("https://undated.com", [1.0, 0.0], None)

        result = find_duplicates([undated, dated])
        by_url = {r.url: r for r in result}

        assert by_url["https://dated.com"].is_duplicate is False
        assert by_url["https://undated.com"].is_duplicate is True
        assert by_url["https://undated.com"].duplicate_of_url == "https://dated.com"

    def test_duplicate_chain_all_point_to_same_original_not_daisy_chained(self):
        original = make_embedded("https://original.com", [1.0, 0.0], BASE_TIME)
        dup1 = make_embedded(
            "https://dup1.com", [0.99, 0.01], BASE_TIME + timedelta(hours=1)
        )
        dup2 = make_embedded(
            "https://dup2.com", [0.98, 0.02], BASE_TIME + timedelta(hours=2)
        )

        result = find_duplicates([original, dup1, dup2])
        by_url = {r.url: r for r in result}

        assert by_url["https://dup1.com"].duplicate_of_url == "https://original.com"
        assert by_url["https://dup2.com"].duplicate_of_url == "https://original.com"

    def test_matches_against_existing_articles_cross_run(self):
        existing = make_embedded(
            "https://existing.com", [1.0, 0.0], BASE_TIME - timedelta(days=1)
        )
        new_article = make_embedded(
            "https://new.com", [0.99, 0.01], BASE_TIME
        )

        result = find_duplicates([new_article], existing_articles=[existing])

        assert len(result) == 1  # existing_articles never re-emitted
        assert result[0].is_duplicate is True
        assert result[0].duplicate_of_url == "https://existing.com"

    def test_empty_batch(self):
        assert find_duplicates([]) == []

    def test_nothing_ever_dropped(self):
        a = make_embedded("https://a.com", [1.0, 0.0], BASE_TIME)
        b = make_embedded("https://b.com", [0.99, 0.01], BASE_TIME + timedelta(hours=1))
        c = make_embedded("https://c.com", [0.98, 0.02], BASE_TIME + timedelta(hours=2))

        result = find_duplicates([a, b, c])
        assert len(result) == 3  # all three present even though b, c are duplicates


class TestDuplicateNode:
    def test_state_contract(self):
        a = make_embedded("https://a.com", [1.0, 0.0], BASE_TIME)
        b = make_embedded("https://b.com", [0.99, 0.01], BASE_TIME + timedelta(hours=1))
        state = {"articles": [a, b]}

        new_state = duplicate_node(state)

        assert len(new_state["articles"]) == 2
        assert all(isinstance(x, DeduplicatedArticle) for x in new_state["articles"])
        assert new_state["duplicate_count"] == 1

    def test_missing_articles_key_defaults_to_empty(self):
        new_state = duplicate_node({})
        assert new_state["articles"] == []
        assert new_state["duplicate_count"] == 0

    def test_uses_existing_embedded_articles_from_state(self):
        existing = make_embedded(
            "https://existing.com", [1.0, 0.0], BASE_TIME - timedelta(days=1)
        )
        new_article = make_embedded("https://new.com", [0.99, 0.01], BASE_TIME)
        state = {
            "articles": [new_article],
            "existing_embedded_articles": [existing],
        }

        new_state = duplicate_node(state)

        assert new_state["articles"][0].is_duplicate is True
        assert new_state["articles"][0].duplicate_of_url == "https://existing.com"