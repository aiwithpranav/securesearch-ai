"""retrieval indexes: GIN on the full-text column, HNSW on the vectors

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-21
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX ix_document_chunks_tsv ON document_chunks USING gin (tsv)")
    # Cosine distance, because the vectors are normalised. m and ef_construction are the pgvector defaults.
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_document_chunks_embedding_hnsw")
    op.execute("DROP INDEX ix_document_chunks_tsv")
