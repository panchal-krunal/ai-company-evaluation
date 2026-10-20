import hashlib
from dataclasses import dataclass
from io import BytesIO

import pdfplumber


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_pages(pdf_bytes: bytes) -> list[PageText]:
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        return [PageText(i + 1, page.extract_text() or "") for i, page in enumerate(pdf.pages)]


def chunk_page(page: PageText, *, max_chars: int = 2000, overlap: int = 200) -> list[str]:
    """Split a page into overlapping character windows, keeping page provenance with the caller."""
    text = page.text.strip()
    if not text:
        return []
    step = max_chars - overlap
    return [text[i : i + max_chars] for i in range(0, max(len(text) - overlap, 1), step)]
