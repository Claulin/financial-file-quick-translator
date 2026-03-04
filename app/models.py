from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from .db import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ticker: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    cik: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    filings: Mapped[list["Filing"]] = relationship(back_populates="company")

    __table_args__ = (UniqueConstraint("cik", name="uq_companies_cik"),)


class Filing(Base):
    __tablename__ = "filings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)

    accession_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    filing_date: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    html_url: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    company: Mapped["Company"] = relationship(back_populates="filings")
    reports: Mapped[list["Report"]] = relationship(back_populates="filing")

    __table_args__ = (UniqueConstraint("accession_number", name="uq_filings_accession_number"),)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("filings.id"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPLETED")
    report_json: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    filing: Mapped["Filing"] = relationship(back_populates="reports")

    __table_args__ = (UniqueConstraint("filing_id", name="uq_reports_filing_id"),)
