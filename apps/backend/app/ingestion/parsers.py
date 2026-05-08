from __future__ import annotations

import io
import json
from abc import ABC, abstractmethod

import pdfplumber


class BaseParser(ABC):
    @abstractmethod
    def extract(self, file_bytes: bytes) -> str:
        ...


class PDFParser(BaseParser):
    def extract(self, file_bytes: bytes) -> str:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages: list[str] = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if text.strip():
                    # Page markers aid chunk-to-page traceability later
                    pages.append(f"[Page {i + 1}]\n{text}")
        return "\n\n".join(pages)


class TXTParser(BaseParser):
    def extract(self, file_bytes: bytes) -> str:
        return file_bytes.decode("utf-8", errors="replace")


class JSONParser(BaseParser):
    """Flattens a JSON document into labelled key: value lines.

    Expects either arbitrary dicts/lists or a structured format like:
    {"sections": [{"title": "...", "content": "..."}]}
    Both are handled by recursive flattening.
    """

    def extract(self, file_bytes: bytes) -> str:
        data = json.loads(file_bytes.decode("utf-8"))
        return _flatten(data)


def _flatten(data: object, prefix: str = "") -> str:
    if isinstance(data, dict):
        parts = [_flatten(v, f"{prefix}.{k}" if prefix else str(k)) for k, v in data.items()]
        return "\n".join(p for p in parts if p)
    if isinstance(data, list):
        parts = [_flatten(item, prefix) for item in data]
        return "\n".join(p for p in parts if p)
    if isinstance(data, str):
        return f"{prefix}: {data}" if prefix else data
    return f"{prefix}: {data}" if prefix else str(data)


# ── Registry ──────────────────────────────────────────────────────────────────

_PARSERS: dict[str, BaseParser] = {
    "pdf": PDFParser(),
    "txt": TXTParser(),
    "json": JSONParser(),
}

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(_PARSERS)


def get_parser(file_extension: str) -> BaseParser:
    ext = file_extension.lower().lstrip(".")
    parser = _PARSERS.get(ext)
    if parser is None:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    return parser
