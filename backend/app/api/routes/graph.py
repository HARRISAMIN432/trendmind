from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.graph import GraphBuildRequest, GraphBuildResponse, GraphResponse
from app.services.graph_service import build_graph, get_graph

router = APIRouter(prefix="/graph", tags=["graph"])

@router.get("", response_model=GraphResponse)
def get_knowledge_graph(db: Session = Depends(get_db)) -> GraphResponse:
    return get_graph(db)


@router.post("/build", response_model=GraphBuildResponse)
def build_knowledge_graph(
    payload: GraphBuildRequest, db: Session = Depends(get_db)
) -> GraphBuildResponse:
    articles_processed, nodes_created, edges_created, errors = build_graph(
        db, days=payload.days
    )
    return GraphBuildResponse(
        articles_processed=articles_processed,
        nodes_created=nodes_created,
        edges_created=edges_created,
        errors=errors,
    )