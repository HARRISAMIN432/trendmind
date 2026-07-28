from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0002_add_graph_tables"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "graph_nodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("name", "type", name="uq_graph_node_name_type"),
    )
    op.create_index("ix_graph_nodes_name", "graph_nodes", ["name"])

    op.create_table(
        "graph_edges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("graph_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            sa.Integer(),
            sa.ForeignKey("graph_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relation", sa.String(length=255), nullable=False),
        sa.Column(
            "article_id",
            sa.Integer(),
            sa.ForeignKey("articles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "source_id", "target_id", "relation", name="uq_graph_edge_source_target_relation"
        ),
    )


def downgrade() -> None:
    op.drop_table("graph_edges")
    op.drop_table("graph_nodes")