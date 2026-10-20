import enum
import uuid
from datetime import date

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin


class CompanyType(enum.StrEnum):
    """Banks, NBFCs and insurers need their own rule templates (out of MVP scope)."""

    NON_FINANCIAL = "non_financial"
    BANK = "bank"
    NBFC = "nbfc"
    INSURER = "insurer"


class ReportingBasis(enum.StrEnum):
    CONSOLIDATED = "consolidated"
    STANDALONE = "standalone"


class Coverage(enum.StrEnum):
    EVALUATED = "evaluated"  # a company analysts evaluate
    PEER = "peer"  # loaded only as a competitor benchmark


class Company(IdMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255))
    nse_symbol: Mapped[str | None] = mapped_column(String(32), unique=True)
    bse_code: Mapped[str | None] = mapped_column(String(16), unique=True)
    isin: Mapped[str | None] = mapped_column(String(12), unique=True)
    sector: Mapped[str | None] = mapped_column(String(128))
    company_type: Mapped[CompanyType] = mapped_column(Enum(CompanyType), default=CompanyType.NON_FINANCIAL)
    coverage: Mapped[str] = mapped_column(String(16), default=Coverage.EVALUATED, server_default="evaluated")

    filings: Mapped[list[Filing]] = relationship(back_populates="company")


class CompanyPeer(IdMixin, TimestampMixin, Base):
    """An agreed competitor of a company, used by the Competitors module."""

    __tablename__ = "company_peers"
    __table_args__ = (UniqueConstraint("company_id", "peer_company_id"),)

    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    peer_company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"))


class Filing(IdMixin, TimestampMixin, Base):
    """A regulatory filing / disclosure (annual report, quarterly results, shareholding, ...)."""

    __tablename__ = "filings"
    __table_args__ = (UniqueConstraint("company_id", "filing_type", "period_end", "basis"),)

    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    filing_type: Mapped[str] = mapped_column(String(64))
    period_end: Mapped[date]
    filing_date: Mapped[date | None]
    basis: Mapped[ReportingBasis] = mapped_column(Enum(ReportingBasis))

    company: Mapped[Company] = relationship(back_populates="filings")
    documents: Mapped[list[SourceDocument]] = relationship(back_populates="filing")


class SourceDocument(IdMixin, TimestampMixin, Base):
    """A source that figures are traced to.

    Once ingested, the raw file is stored immutably in S3 (`s3_key`, `sha256`). A source that is
    registered by URL but not downloaded yet has both left empty.
    """

    __tablename__ = "source_documents"

    filing_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("filings.id"), index=True)
    title: Mapped[str] = mapped_column(String(512))
    s3_key: Mapped[str | None] = mapped_column(String(1024), unique=True)
    sha256: Mapped[str | None] = mapped_column(String(64), unique=True)  # skip re-processing unchanged docs
    content_type: Mapped[str] = mapped_column(String(128))
    source_url: Mapped[str | None] = mapped_column(String(2048), unique=True)
    publisher: Mapped[str | None] = mapped_column(String(255))
    is_primary: Mapped[bool] = mapped_column(default=False)  # exchange filing / annual report vs aggregator
    doc_type: Mapped[str | None] = mapped_column(String(64))
    page_count: Mapped[int | None]
    # registered -> extracted (text chunks stored) -> embedded (searchable); or failed
    ingestion_status: Mapped[str] = mapped_column(
        String(16), default="registered", server_default="registered"
    )
    ingestion_error: Mapped[str | None] = mapped_column(Text)

    filing: Mapped[Filing | None] = relationship(back_populates="documents")
