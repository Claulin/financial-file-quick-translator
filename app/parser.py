from __future__ import annotations

import re
from bs4 import BeautifulSoup


def html_to_readable_text(html: str) -> str:
    """
    Converts SEC filing HTML into readable plain text.
    """
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = text.strip()
    return text


def clamp_text_for_llm(text: str, max_chars: int = 120_000) -> str:
    """
    Keeps prompt size bounded for reliability.
    """
    if len(text) <= max_chars:
        return text
    head = text[: max_chars // 2]
    tail = text[-max_chars // 2 :]
    return head + "\n\n[...TRUNCATED...]\n\n" + tail
