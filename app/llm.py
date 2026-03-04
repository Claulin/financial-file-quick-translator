from __future__ import annotations

import json
from dataclasses import dataclass
import requests


@dataclass(frozen=True)
class LlmConfig:
    api_key: str
    base_url: str
    model: str
    temperature: float = 0.1
    timeout_seconds: float = 60.0


class LlmClient:
    """
    OpenAI-compatible Chat Completions client.
    """

    def __init__(self, cfg: LlmConfig):
        self._cfg = cfg
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {cfg.api_key}",
                "Content-Type": "application/json",
            }
        )

    def generate_report_json(self, filing_text: str) -> dict:
        system = (
            "You are an extraction engine for SEC S-1 filings.\n"
            "Rules:\n"
            "- Output JSON only. No markdown. No commentary.\n"
            "- Temperature low.\n"
            "- Never guess numbers.\n"
            "- If a number is unclear or not present, use null.\n"
            "- If any key data is unclear, set confidence_level to MANUAL_REVIEW_REQUIRED.\n"
            "- risk_stickers max 5.\n\n"
            "Return JSON with EXACT top-level keys:\n"
            "sixty_second_snapshot, plain_english_summary, risk_stickers, narrative_vs_numbers_check, "
            "financial_table, confidence_level\n\n"
            "sixty_second_snapshot keys:\n"
            "revenue_trend_3y (string|null), revenue_values_3y (array of numbers|null), "
            "net_income_latest_year (number|null), cash_on_hand (number|null), total_debt (number|null), "
            "cash_runway_months (number|null)\n\n"
            "risk_stickers: array of objects with keys: type, description, source_reference\n\n"
            "narrative_vs_numbers_check: object with keys: status (ALIGNED or NARRATIVE_TENSION_DETECTED), explanation\n\n"
            "financial_table keys:\n"
            "revenue_3y (array of numbers|null), net_income_latest_year (number|null), cash (number|null), debt (number|null)\n\n"
            "confidence_level: HIGH, MEDIUM, or MANUAL_REVIEW_REQUIRED\n"
        )

        user = (
            "Extract the requested report from the following filing text.\n"
            "Important:\n"
            "- Use numbers only when explicitly stated.\n"
            "- Use null when not explicitly stated or ambiguous.\n"
            "- Keep the plain_english_summary to 10-15 sentences.\n\n"
            "FILING TEXT:\n"
            f"{filing_text}"
        )

        payload = {
            "model": self._cfg.model,
            "temperature": self._cfg.temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }

        url = self._cfg.base_url.rstrip("/") + "/v1/chat/completions"
        resp = self._session.post(url, data=json.dumps(payload), timeout=self._cfg.timeout_seconds)
        resp.raise_for_status()

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
