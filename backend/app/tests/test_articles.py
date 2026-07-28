from __future__ import annotations
from datetime import datetime, timedelta, timezone

def test_list_articles_empty(client):
    resp = client.get("/articles")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_list_articles_returns_items(client, make_article):
    make_article(title="A")
    make_article(title="B")

    resp = client.get("/articles")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_list_articles_excludes_duplicates_by_default(client, make_article):
    canonical = make_article(title="Original")
    make_article(title="Dupe", duplicate_of_id=canonical.id)

    resp = client.get("/articles")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Original"


def test_list_articles_include_duplicates_flag(client, make_article):
    canonical = make_article(title="Original")
    make_article(title="Dupe", duplicate_of_id=canonical.id)

    resp = client.get("/articles", params={"include_duplicates": True})
    body = resp.json()
    assert body["total"] == 2


def test_list_articles_filter_by_category(client, make_article):
    make_article(title="Research one", category="Research")
    make_article(title="Funding one", category="Funding")

    resp = client.get("/articles", params={"category": "Research"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["category"] == "Research"


def test_list_articles_filter_by_importance(client, make_article):
    make_article(title="High imp", importance="High")
    make_article(title="Low imp", importance="Low")

    resp = client.get("/articles", params={"importance": "High"})
    body = resp.json()
    assert body["total"] == 1


def test_list_articles_filter_by_source_id(client, make_article, make_source):
    s1 = make_source(name="Source One", rss_url="https://one.com/feed")
    s2 = make_source(name="Source Two", rss_url="https://two.com/feed")
    make_article(title="From one", source_id=s1.id)
    make_article(title="From two", source_id=s2.id)

    resp = client.get("/articles", params={"source_id": s1.id})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["source_name"] == "Source One"


def test_list_articles_filter_by_company_exact_case_insensitive(client, db_session, make_article, make_company):
    openai = make_company("OpenAI")
    a = make_article(title="OpenAI news")
    a.companies = [openai]
    db_session.commit()
    make_article(title="Unrelated")

    resp = client.get("/articles", params={"company": "openai"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["companies"] == ["OpenAI"]


def test_list_articles_company_filter_no_substring_match(client, db_session, make_article, make_company):
    openai = make_company("OpenAI")
    a = make_article(title="OpenAI news")
    a.companies = [openai]
    db_session.commit()

    # "open" is a substring of "OpenAI" but the filter is exact-match only.
    resp = client.get("/articles", params={"company": "open"})
    assert resp.json()["total"] == 0


def test_list_articles_search_title_substring(client, make_article):
    make_article(title="LangGraph orchestration explained")
    make_article(title="Something unrelated")

    resp = client.get("/articles", params={"search": "langgraph"})
    body = resp.json()
    assert body["total"] == 1


def test_list_articles_pagination(client, make_article):
    for i in range(5):
        make_article(title=f"Article {i}")

    resp = client.get("/articles", params={"limit": 2, "offset": 0})
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2

    resp2 = client.get("/articles", params={"limit": 2, "offset": 4})
    assert len(resp2.json()["items"]) == 1


def test_list_articles_sort_by_published_at_nulls_last(client, make_article):
    now = datetime.now(timezone.utc)
    make_article(title="No date", published_at=None)
    make_article(title="Older", published_at=now - timedelta(days=2))
    make_article(title="Newer", published_at=now)

    resp = client.get("/articles", params={"sort_by": "published_at"})
    titles = [item["title"] for item in resp.json()["items"]]
    assert titles == ["Newer", "Older", "No date"]


def test_list_articles_invalid_sort_by_rejected(client):
    resp = client.get("/articles", params={"sort_by": "not_a_real_column"})
    assert resp.status_code == 422


def test_get_article_by_id(client, make_article):
    a = make_article(title="Detail target", clean_content="full body text")
    resp = client.get(f"/articles/{a.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Detail target"
    assert body["clean_content"] == "full body text"


def test_get_article_404(client):
    resp = client.get("/articles/999999")
    assert resp.status_code == 404


def test_create_article_minimal(client):
    resp = client.post("/articles", json={
        "title": "New article",
        "url": "https://example.com/new-article",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "New article"
    assert body["companies"] == []


def test_create_article_resolves_company_names(client):
    resp = client.post("/articles", json={
        "title": "Funding news",
        "url": "https://example.com/funding",
        "company_names": ["Anthropic", "OpenAI"],
    })
    assert resp.status_code == 201
    body = resp.json()
    assert sorted(body["companies"]) == ["Anthropic", "OpenAI"]


def test_create_article_reuses_existing_company(client, make_company):
    make_company("Anthropic")
    resp = client.post("/articles", json={
        "title": "More Anthropic news",
        "url": "https://example.com/more-anthropic",
        "company_names": ["anthropic"],  # different case, should match existing row
    })
    assert resp.status_code == 201

    # Confirm no duplicate Company row was created.
    resp2 = client.get("/articles", params={"company": "Anthropic"})
    assert resp2.json()["total"] == 1


def test_create_article_duplicate_url_conflict(client, make_article):
    make_article(title="Existing", url="https://example.com/dupe-url")
    resp = client.post("/articles", json={
        "title": "Same URL different title",
        "url": "https://example.com/dupe-url",
    })
    assert resp.status_code == 409


def test_update_article_partial_fields_only(client, make_article):
    a = make_article(title="Original", category="Research", importance="Low")
    resp = client.patch(f"/articles/{a.id}", json={"importance": "High"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["importance"] == "High"
    assert body["category"] == "Research"  # untouched


def test_update_article_replaces_companies(client, db_session, make_article, make_company):
    a = make_article(title="Original")
    old_co = make_company("OldCo")
    a.companies = [old_co]
    db_session.commit()

    resp = client.patch(f"/articles/{a.id}", json={"company_names": ["NewCo"]})
    assert resp.status_code == 200
    assert resp.json()["companies"] == ["NewCo"]


def test_update_article_url_field_not_accepted(client, make_article):
    a = make_article(title="Original", url="https://example.com/keep-me")
    resp = client.patch(f"/articles/{a.id}", json={"url": "https://example.com/hacked"})
    # Extra field is silently ignored by pydantic (not in ArticleUpdate schema);
    # confirm the stored url is unchanged either way.
    assert resp.status_code == 200
    resp2 = client.get(f"/articles/{a.id}")
    assert resp2.json()["url"] == "https://example.com/keep-me"


def test_update_article_404(client):
    resp = client.patch("/articles/999999", json={"importance": "High"})
    assert resp.status_code == 404


def test_delete_article(client, make_article):
    a = make_article(title="To delete")
    resp = client.delete(f"/articles/{a.id}")
    assert resp.status_code == 204

    resp2 = client.get(f"/articles/{a.id}")
    assert resp2.status_code == 404


def test_delete_article_404(client):
    resp = client.delete("/articles/999999")
    assert resp.status_code == 404


def test_delete_canonical_article_nulls_duplicate_pointer(client, db_session, make_article):
    canonical = make_article(title="Canonical")
    dupe = make_article(title="Dupe", duplicate_of_id=canonical.id)

    resp = client.delete(f"/articles/{canonical.id}")
    assert resp.status_code == 204

    db_session.expire_all()
    from app.models.article import Article
    refreshed = db_session.query(Article).filter(Article.id == dupe.id).first()
    assert refreshed.duplicate_of_id is None