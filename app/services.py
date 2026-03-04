from __future__ import annotations

import json
from sqlalchemy.orm import Session

from .models import Company, Filing, Report
from .sec import SecClient
from .parser import html_to_readable_text, clamp_text_for_llm
from .llm import LlmClient


def get_or_create_company(session: Session, cik: str, ticker: str | None, name: str | None) -> Company:
    company = session.query(Company).filter(Company.cik == cik).one_or_none()
    if company:
        updated = False
        if ticker and company.ticker != ticker:
            company.ticker = ticker
            updated = True
        if name and company.name != name:
            company.name = name
            updated = True
        if updated:
            session.add(company)
            session.commit()
        return company

    company = Company(cik=cik, ticker=ticker, name=name)
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def get_or_create_filing(
    session: Session,
    company_id: int,
    accession_number: str,
    filing_date: str,
    html_url: str,
) -> Filing:
    filing = session.query(Filing).filter(Filing.accession_number == accession_number).one_or_none()
    if filing:
        return filing

    filing = Filing(
        company_id=company_id,
        accession_number=accession_number,
        filing_date=filing_date,
        html_url=html_url,
        parsed_text=None,
    )
    session.add(filing)
    session.commit()
    session.refresh(filing)
    return filing


def get_cached_report(session: Session, filing_id: int) -> Report | None:
    return session.query(Report).filter(Report.filing_id == filing_id).one_or_none()


def create_report(session: Session, filing_id: int, report: dict) -> Report:
    rep = Report(filing_id=filing_id, status="COMPLETED", report_json=json.dumps(report))
    session.add(rep)
    session.commit()
    session.refresh(rep)
    return rep


def ensure_parsed_text(session: Session, sec: SecClient, filing: Filing) -> Filing:
    if filing.parsed_text:
        return filing
    html = sec.fetch_filing_html(filing.html_url)
    filing.parsed_text = html_to_readable_text(html)
    session.add(filing)
    session.commit()
    session.refresh(filing)
    return filing


def run_full_flow(
    session: Session,
    sec: SecClient,
    llm: LlmClient | None,
    ticker_map: dict,
    query: str,
) -> Report:
    cik, ticker, name_from_map = sec.resolve_to_cik(query, ticker_map)
    cand = sec.get_recent_s1_candidate(cik)

    company = get_or_create_company(session, cik=cik, ticker=ticker, name=cand.company_name or name_from_map)
    html_url = sec.get_filing_html_url(
        cik=cand.cik, accession_number=cand.accession_number, primary_document=cand.primary_document
    )
    filing = get_or_create_filing(
        session,
        company_id=company.id,
        accession_number=cand.accession_number,
        filing_date=cand.filing_date,
        html_url=html_url,
    )

    cached = get_cached_report(session, filing.id)
    if cached:
        return cached

    filing = ensure_parsed_text(session, sec, filing)

    if llm is None:
        report = {
            "sixty_second_snapshot": {
                "revenue_trend_3y": None,
                "revenue_values_3y": None,
                "net_income_latest_year": None,
                "cash_on_hand": None,
                "total_debt": None,
                "cash_runway_months": None,
            },
            "plain_english_summary": (
                "LLM is not configured (missing OPENAI_API_KEY). "
                "Set OPENAI_API_KEY in your .env to enable automated extraction."
            ),
            "risk_stickers": [],
            "narrative_vs_numbers_check": {
                "status": "NARRATIVE_TENSION_DETECTED",
                "explanation": "LLM not configured; unable to validate narrative vs numbers.",
            },
            "financial_table": {"revenue_3y": None, "net_income_latest_year": None, "cash": None, "debt": None},
            "confidence_level": "MANUAL_REVIEW_REQUIRED",
        }
        return create_report(session, filing.id, report)

    filing_text_for_llm = clamp_text_for_llm(filing.parsed_text or "")
    report = llm.generate_report_json(filing_text_for_llm)
    return create_report(session, filing.id, report)
