from __future__ import annotations

import re
import unicodedata
from collections import Counter


def clean_text(text: str) -> str:
    """Normalise and de-noise extracted document text.

    Steps (in order):
    1. Unicode normalisation — collapses ligatures, fullwidth chars, etc.
    2. Control character removal — strips bytes that break tokenisers.
    3. Repeated-line removal — eliminates headers/footers that appear 3+ times.
    4. Blank-line collapse — more than two consecutive blank lines → two.
    5. Horizontal-whitespace collapse — tabs and multi-spaces → single space.
    """
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = _remove_repeated_lines(text, threshold=3)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _remove_repeated_lines(text: str, threshold: int) -> str:
    """Drop lines that appear >= threshold times (typical of running headers/footers)."""
    lines = text.split("\n")
    counts: Counter[str] = Counter(ln.strip() for ln in lines if ln.strip())
    return "\n".join(
        ln for ln in lines
        if not ln.strip() or counts[ln.strip()] < threshold
    )
