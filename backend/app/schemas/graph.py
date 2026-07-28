from __future__ import annotations
from pydantic import BaseModel


class GraphNodeItem(BaseModel):
    id: int
    name: str
    type: str


class GraphEdgeItem(BaseModel):
    id: int
    source_id: int
    target_id: int
    relation: str
    article_id: int | None


class GraphResponse(BaseModel):
    nodes: list[GraphNodeItem]
    edges: list[GraphEdgeItem]


class GraphBuildRequest(BaseModel):
    days: int = 30


class GraphBuildResponse(BaseModel):
    articles_processed: int
    nodes_created: int
    edges_created: int
    errors: list[str]