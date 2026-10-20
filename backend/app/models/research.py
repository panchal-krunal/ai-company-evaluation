import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.models.base import Base, IdMixin, TimestampMixin


class DocumentChunk(IdMixin, TimestampMixin, Base):
    """A retrievable passage of a source document, embedded for RAG."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        Index(
            "ix_document_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    source_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_documents.id"), index=True)
    page_number: Mapped[int | None]
    chunk_index: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    # Null until the chunk has been embedded (text extraction and embedding run separately).
    embedding: Mapped[list[float] | None] = mapped_column(Vector(get_settings().embedding_dimensions))
