from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal


ConfidenceLevel = Literal["HIGH", "MEDIUM", "MANUAL_REVIEW_REQUIRED"]
NarrativeStatus = Literal["ALIGNED", "NARRATIVE_TENSION_DETECTED"]


class RiskSticker(BaseModel):
    type: str = Field(..., description="Short risk label")
    description: str = Field(..., description="One or two sentences")
    source_reference: str = Field(..., description="Where in the filing this came from (e.g., section name)")


class Snapshot(BaseModel):
    revenue_trend_3y: str | None = None
    revenue_values_3y: list[float] | None = None
    net_income_latest_year: float | None = None
    cash_on_hand: float | None = None
    total_debt: float | None = None
    cash_runway_months: float | None = None


class FinancialTable(BaseModel):
    revenue_3y: list[float] | None = None
    net_income_latest_year: float | None = None
    cash: float | None = None
    debt: float | None = None


class ReportJSON(BaseModel):
    sixty_second_snapshot: Snapshot
    plain_english_summary: str
    risk_stickers: list[RiskSticker] = Field(..., max_length=5)
    narrative_vs_numbers_check: dict
    financial_table: FinancialTable
    confidence_level: ConfidenceLevel
