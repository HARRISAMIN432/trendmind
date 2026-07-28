from __future__ import annotations
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.agents.entity_extraction_agent import extract_entities
from app.models.article import Article
from app.models.graph import GraphEdge, GraphNode
from app.schemas.graph import GraphEdgeItem, GraphNodeItem, GraphResponse


def _get_recent_articles_for_extraction(db: Session, days: int) -> list[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return (
        db.query(Article)
        .filter(Article.duplicate_of_id.is_(None))  # canonical articles only, same M07 contract as M12
        .filter(Article.clean_content.isnot(None))
        .filter(Article.published_at.isnot(None))
        .filter(Article.published_at >= cutoff)
        .all()
    )


def _get_or_create_node(
    db: Session, cache: dict[tuple[str, str], GraphNode], name: str, type_: str
) -> GraphNode:
    """
    Dedup key is (name lowercased+stripped, type) - same entity mentioned under
    slightly different casing across articles collapses into one node. Type is
    compared case-sensitively (not normalized), so callers should stick to the
    ENTITY_TYPES constants rather than free-text casing variants.
    """
    key = (name.strip().lower(), type_)
    if key in cache:
        return cache[key]

    node = (
        db.query(GraphNode)
        .filter(GraphNode.name.ilike(name.strip()))
        .filter(GraphNode.type == type_)
        .first()
    )
    if node is None:
        node = GraphNode(name=name.strip(), type=type_)
        db.add(node)
        db.flush()  # need node.id before any edge can reference it
    cache[key] = node
    return node


def build_graph(db: Session, days: int = 30) -> tuple[int, int, int, list[str]]:
    """
    Runs entity extraction over recent canonical articles with clean_content, upserting
    GraphNode/GraphEdge rows. Returns (articles_processed, nodes_created, edges_created, errors).

    Fail-soft per article (same pattern as M02-M07's node functions): an extraction
    failure on one article is recorded in `errors` and skipped, never raises and never
    aborts the rest of the batch.

    No dedup-across-runs check beyond the node/edge uniqueness constraints themselves -
    running this twice over overlapping windows re-extracts already-seen articles, but
    since nodes/edges are upserted by (name,type) / (source,target,relation), re-running
    is idempotent rather than creating duplicate graph data (unlike M12's trend
    generation, which has no such protection).
    """
    articles = _get_recent_articles_for_extraction(db, days)
    node_cache: dict[tuple[str, str], GraphNode] = {}
    nodes_before = db.query(GraphNode).count()
    edges_before = db.query(GraphEdge).count()
    errors: list[str] = []

    for article in articles:
        result, error = extract_entities(article.id, article.title, article.clean_content)
        if result is None:
            if error:
                errors.append(f"article {article.id}: {error.reason}")
            continue

        entity_type_by_name: dict[str, str] = {}
        for entity in result.entities:
            _get_or_create_node(db, node_cache, entity.name, entity.type)
            entity_type_by_name[entity.name.strip().lower()] = entity.type

        for rel in result.relationships:
            source_type = entity_type_by_name.get(rel.source.strip().lower())
            target_type = entity_type_by_name.get(rel.target.strip().lower())
            if source_type is None or target_type is None:
                # LLM referenced a source/target not present in its own entities list for
                # this article - skip rather than guess a type for a node we can't
                # otherwise place. This is the enforcement point for the prompt's
                # "must match a name in entities" instruction, since the LLM's structured
                # output isn't otherwise validated against itself.
                continue

            source_node = _get_or_create_node(db, node_cache, rel.source, source_type)
            target_node = _get_or_create_node(db, node_cache, rel.target, target_type)

            existing_edge = (
                db.query(GraphEdge)
                .filter(GraphEdge.source_id == source_node.id)
                .filter(GraphEdge.target_id == target_node.id)
                .filter(GraphEdge.relation == rel.relation)
                .first()
            )
            if existing_edge is None:
                db.add(
                    GraphEdge(
                        source_id=source_node.id,
                        target_id=target_node.id,
                        relation=rel.relation,
                        article_id=article.id,
                    )
                )

    db.commit()
    nodes_created = db.query(GraphNode).count() - nodes_before
    edges_created = db.query(GraphEdge).count() - edges_before
    return len(articles), nodes_created, edges_created, errors


def get_graph(db: Session) -> GraphResponse:
    """The one sanctioned way to serialize the full graph - GET /graph returns
    everything in one shot (no pagination), fine at portfolio scale (low hundreds of
    nodes/edges at most)."""
    nodes = db.query(GraphNode).all()
    edges = db.query(GraphEdge).all()
    return GraphResponse(
        nodes=[GraphNodeItem(id=n.id, name=n.name, type=n.type) for n in nodes],
        edges=[
            GraphEdgeItem(
                id=e.id,
                source_id=e.source_id,
                target_id=e.target_id,
                relation=e.relation,
                article_id=e.article_id,
            )
            for e in edges
        ],
    )