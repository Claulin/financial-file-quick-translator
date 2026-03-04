from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

import requests


SEC_BASE = "https://data.sec.gov"
SEC_WWW = "https://www.sec.gov"


@dataclass(frozen=True)
class FilingCandidate:
    cik: str
    accession_number: str
    filing_date: str
    form: str
    primary_document: str
    company_name: str | None


class SecClient:
    """
    Minimal SEC EDGAR client with polite rate limiting.
    """

    def __init__(self, user_agent: str, min_interval_seconds: float = 0.25, timeout_seconds: float = 20.0):
        self._ua = user_agent
        self._min_interval = min_interval_seconds
        self._timeout = timeout_seconds
        self._last_request_ts = 0.0
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": self._ua,
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "application/json,text/html,*/*",
                "Connection": "keep-alive",
            }
        )

    def _sleep_if_needed(self) -> None:
        now = time.time()
        elapsed = now - self._last_request_ts
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_ts = time.time()

    def _get(self, url: str) -> requests.Response:
        self._sleep_if_needed()
        resp = self._session.get(url, timeout=self._timeout)
        resp.raise_for_status()
        return resp

    @staticmethod
    def _normalize_cik(cik: str) -> str:
        digits = re.sub(r"\D", "", cik)
        if not digits:
            raise ValueError("CIK is empty/invalid.")
        return digits.lstrip("0") or "0"

    @staticmethod
    def _cik_10(cik: str) -> str:
        digits = re.sub(r"\D", "", cik)
        return digits.zfill(10)

    def fetch_ticker_map(self) -> dict[str, dict[str, Any]]:
        """
        Returns map keyed by lowercase ticker -> {cik_str, title, ticker}.
        """
        url = f"{SEC_WWW}/files/company_tickers.json"
        data = self._get(url).json()
        out: dict[str, dict[str, Any]] = {}
        for _, row in data.items():
            t = str(row.get("ticker", "")).strip()
            cik_str = str(row.get("cik_str", "")).strip()
            title = str(row.get("title", "")).strip()
            if t and cik_str:
                out[t.lower()] = {"ticker": t.upper(), "cik": str(cik_str), "name": title or None}
        return out

    def resolve_to_cik(self, query: str, ticker_map: dict[str, dict[str, Any]]) -> tuple[str, str | None, str | None]:
        q = query.strip()
        if re.fullmatch(r"\d+", q):
            cik = self._normalize_cik(q)
            return cik, None, None
        key = q.lower()
        if key not in ticker_map:
            raise ValueError(f"Ticker not found: {q}")
        rec = ticker_map[key]
        cik = self._normalize_cik(str(rec["cik"]))
        return cik, rec.get("ticker"), rec.get("name")

    def get_recent_s1_candidate(self, cik: str) -> FilingCandidate:
        cik10 = self._cik_10(cik)
        url = f"{SEC_BASE}/submissions/CIK{cik10}.json"
        sub = self._get(url).json()

        company_name = sub.get("name") or None
        recent = sub.get("filings", {}).get("recent", {})
        forms: list[str] = recent.get("form", []) or []
        accession_numbers: list[str] = recent.get("accessionNumber", []) or []
        filing_dates: list[str] = recent.get("filingDate", []) or []
        primary_docs: list[str] = recent.get("primaryDocument", []) or []

        best_idx: int | None = None
        best_date: str = ""

        for i, form in enumerate(forms):
            if form not in ("S-1", "S-1/A"):
                continue
            date = filing_dates[i] if i < len(filing_dates) else ""
            if date and date >= best_date:
                best_date = date
                best_idx = i

        if best_idx is None:
            raise ValueError("No recent S-1 or S-1/A found for this company.")

        return FilingCandidate(
            cik=self._normalize_cik(cik),
            accession_number=accession_numbers[best_idx],
            filing_date=filing_dates[best_idx],
            form=forms[best_idx],
            primary_document=primary_docs[best_idx],
            company_name=company_name,
        )

    @staticmethod
    def _accession_nodashes(accession_number: str) -> str:
        return accession_number.replace("-", "")

    def get_filing_html_url(self, cik: str, accession_number: str, primary_document: str) -> str:
        """
        Enforces HTML-only. If primary doc isn't .htm/.html, consult index.json and pick an .htm/.html file.
        """
        cik_norm = self._normalize_cik(cik)
        acc_no_dash = self._accession_nodashes(accession_number)

        def archives_url(filename: str) -> str:
            return f"{SEC_WWW}/Archives/edgar/data/{cik_norm}/{acc_no_dash}/{filename}"

        if primary_document.lower().endswith((".htm", ".html")):
            return archives_url(primary_document)

        index_url = f"{SEC_WWW}/Archives/edgar/data/{cik_norm}/{acc_no_dash}/index.json"
        idx = self._get(index_url).json()
        items = (((idx.get("directory") or {}).get("item")) or [])
        html_files = [it.get("name") for it in items if str(it.get("name", "")).lower().endswith((".htm", ".html"))]

        if not html_files:
            raise ValueError("Filing does not appear to have an HTML document available.")

        preferred = None
        for name in html_files:
            n = str(name).lower()
            if "s-1" in n or "s1" in n or "registration" in n:
                preferred = name
                break

        return archives_url(preferred or html_files[0])

    def fetch_filing_html(self, html_url: str) -> str:
        resp = self._get(html_url)
        ctype = resp.headers.get("Content-Type", "")
        if "text/html" not in ctype and not html_url.lower().endswith((".htm", ".html")):
            raise ValueError("Fetched document is not HTML.")
        return resp.text
