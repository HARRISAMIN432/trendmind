from __future__ import annotations
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.graph import GraphBuildRequest, GraphBuildResponse, GraphResponse
from app.services.graph_service import build_graph, get_graph
from app.api.limiter import limiter
from app.core.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/graph", tags=["graph"])

@router.get("", response_model=GraphResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_knowledge_graph(request: Request ,db: Session = Depends(get_db)) -> GraphResponse:
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