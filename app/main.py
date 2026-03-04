from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from .config import Settings
from .db import Base, make_engine, make_session_factory
from .models import Company, Filing, Report
from .sec import SecClient
from .llm import LlmClient, LlmConfig
from .services import run_full_flow


def create_app() -> FastAPI:
    settings = Settings.load()

    engine = make_engine(str(settings.db_path))
    SessionLocal = make_session_factory(engine)
    Base.metadata.create_all(bind=engine)

    sec = SecClient(user_agent=settings.sec_user_agent)

    llm = None
    if settings.openai_api_key:
        llm = LlmClient(
            LlmConfig(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=settings.openai_model,
                temperature=0.1,
            )
        )

    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

    app = FastAPI(title="Filing Translation Engine", version="0.1.0")
    app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

    ticker_map_cache: dict | None = None

    def get_db() -> Session:
        return SessionLocal()

    def get_ticker_map() -> dict:
        nonlocal ticker_map_cache
        if ticker_map_cache is None:
            ticker_map_cache = sec.fetch_ticker_map()
        return ticker_map_cache

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def homepage(request: Request, error: str | None = None):
        return templates.TemplateResponse("index.html", {"request": request, "error": error})

    @app.get("/search")
    def search(request: Request, q: str):
        session = get_db()
        try:
            report = run_full_flow(
                session=session,
                sec=sec,
                llm=llm,
                ticker_map=get_ticker_map(),
                query=q,
            )
            return RedirectResponse(url=f"/report/{report.id}", status_code=302)
        except Exception as e:
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "error": str(e)},
                status_code=400,
            )
        finally:
            session.close()

    @app.get("/report/{id}", response_class=HTMLResponse)
    def report_page(request: Request, id: int):
        session = get_db()
        try:
            rep = session.query(Report).filter(Report.id == id).one_or_none()
            if not rep:
                return templates.TemplateResponse("error.html", {"request": request, "message": "Report not found."}, status_code=404)

            filing = session.query(Filing).filter(Filing.id == rep.filing_id).one()
            company = session.query(Company).filter(Company.id == filing.company_id).one()

            report_json = json.loads(rep.report_json)

            return templates.TemplateResponse(
                "report.html",
                {
                    "request": request,
                    "report": report_json,
                    "company_name": company.name,
                    "ticker": company.ticker,
                    "cik": company.cik,
                    "filing_date": filing.filing_date,
                    "accession_number": filing.accession_number,
                    "html_url": filing.html_url,
                },
            )
        except Exception as e:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "message": str(e)},
                status_code=500,
            )
        finally:
            session.close()

    @app.get("/api/report/{id}")
    def report_json(id: int):
        session = get_db()
        try:
            rep = session.query(Report).filter(Report.id == id).one_or_none()
            if not rep:
                return JSONResponse({"error": "not_found"}, status_code=404)
            return JSONResponse(json.loads(rep.report_json))
        finally:
            session.close()

    return app


app = create_app()
