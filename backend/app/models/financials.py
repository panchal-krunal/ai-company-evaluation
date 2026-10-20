import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin
from app.models.company import ReportingBasis


class FinancialFact(IdMixin, TimestampMixin, Base):
    """One normalised line item (e.g. revenue, total_debt) for a company, period and basis."""

    __tablename__ = "financial_facts"
    __table_args__ = (UniqueConstraint("company_id", "metric", "period_end", "period_type", "basis"),)

    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    metric: Mapped[str] = mapped_column(String(64), index=True)
    period_end: Mapped[date]
    period_type: Mapped[str] = mapped_column(String(8))  # "FY" or "Q"
    basis: Mapped[ReportingBasis] = mapped_column(Enum(ReportingBasis))
    value: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    unit: Mapped[str] = mapped_column(String(16), default="INR_CR")
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_documents.id"))
    source_page: Mapped[int | None]
