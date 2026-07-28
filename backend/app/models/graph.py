from __future__ import annotations
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class GraphNode(Base):
    """
    An extracted entity (Company/Model/Researcher/Dataset/Product). Deliberately
    NOT the same table as `companies` - a GraphNode of type "Company" and a `companies`
    row for the same org are two separate records with no FK link between them in this
    pass. (See CLAUDE.md M14 notes for why, and what a future module would need to do
    to unify them.)
    """

    __tablename__ = "graph_nodes"
    __table_args__ = (UniqueConstraint("name", "type", name="uq_graph_node_name_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GraphEdge(Base):
    """A directed relationship between two GraphNodes, optionally traceable back to the
    article it was extracted from."""

    __tablename__ = "graph_edges"
    __table_args__ = (
        UniqueConstraint(
            "source_id", "target_id", "relation", name="uq_graph_edge_source_target_relation"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[int] = mapped_column(
        ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False
    )
    relation: Mapped[str] = mapped_column(String(255), nullable=False)
    article_id: Mapped[int | None] = mapped_column(
        ForeignKey("articles.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source: Mapped["GraphNode"] = relationship(foreign_keys=[source_id])
    target: Mapped["GraphNode"] = relationship(foreign_keys=[target_id])