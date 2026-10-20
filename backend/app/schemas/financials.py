import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.company import ReportingBasis


class FinancialFactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric: str
    period_end: date
    period_type: str
    basis: ReportingBasis
    value: float
    unit: str
    source_document_id: uuid.UUID | None


class SourceDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    source_url: str | None
    publisher: str | None
    is_primary: bool


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    doc_type: str | None
    source_url: str | None
    publisher: str | None
    is_primary: bool
    page_count: int | None
    ingestion_status: str
    ingestion_error: str | None
    period_end: date | None = None
    filing_date: date | None = None
    chunks: int = 0
    embedded_chunks: int = 0
