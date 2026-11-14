"""Prepare the selected PDF pages; no embedding or retrieval is run here."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/principles-economics-3e_-_WEB.pdf"
SOURCE_ID = "openstax-principles-economics-3e-local-2026"


def normalize(text: str) -> str:
    # Keep line boundaries and attribution. Do not guess damaged characters.
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(re.sub(r"[^\S\n]+", " ", line).strip() for line in text.split("\n")).strip()


def main() -> None:
    output = ROOT / "data/processed"
    results = ROOT / "results"
    output.mkdir(parents=True, exist_ok=True)
    results.mkdir(exist_ok=True)
    pages, audit = [], []
    with pymupdf.open(PDF) as document:
        physical_pages = len(document)
        for first, last, chapter, title in [
            (64, 93, 3, "Demand and Supply"),
            (102, 119, 4, "Labor and Financial Markets"),
        ]:
            for number in range(first, last + 1):
                raw = document[number - 1].get_text(sort=False)
                text = normalize(raw)
                if not text:
                    raise ValueError(f"Selected PDF page {number} has no extracted text")
                pages.append({
                    "document_id": SOURCE_ID,
                    "page_id": f"{SOURCE_ID}:pdf:{number}",
                    "source": PDF.relative_to(ROOT).as_posix(),
                    "page": number,
                    "text": text,
                    "metadata": {"chapter": chapter, "chapter_title": title, "language": "en"},
                })
                audit.append({
                    "pdf_page": number,
                    "normalized_char_count": len(text),
                    "replacement_char_count": text.count("\ufffd"),
                    "status": "review_extraction" if "\ufffd" in text else "text_extracted",
                })
    manifest = {
        "source_id": SOURCE_ID,
        "title": "Principles of Economics 3e",
        "publisher": "OpenStax, Rice University",
        "source_path_or_url": PDF.relative_to(ROOT).as_posix(),
        "reference_url_from_pdf": "https://openstax.org/details/books/principles-economics-3e",
        "accessed_at": "2026-11-14",
        "access_note": "Local PDF inspected on this date; original download date/URL not independently verified.",
        "license_or_permission": "CC BY-NC-SA 4.0, as stated on physical PDF page 4; retain attribution and observe noncommercial/share-alike terms and exclusions stated there.",
        "attribution": "Principles of Economics 3e, OpenStax, Rice University. Access for free at openstax.org.",
        "snapshot": {"sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(), "bytes": PDF.stat().st_size, "pdf_physical_page_count": physical_pages},
        "scope": "Supply and demand in goods, labor and financial markets (main exposition in chapters 3 and 4).",
        "counting_rule": "Count each selected physical PDF page once, including figures/tables supporting the exposition. Exclude front matter, contents, chapter opening pages, end-of-chapter terms/summaries/exercises, and all other pages. PDF pages are one-based; these are not printed page labels. The 1500-character rule for unpaginated sources is not applied to PDF pages.",
        "selected_pdf_page_ranges_inclusive": [[64, 93], [102, 119]],
        "content_page_count": len(pages),
        "normalized_char_count": sum(len(page["text"]) for page in pages),
        "pages": [{"page_id": page["page_id"], "pdf_page": page["page"], "chapter": page["metadata"]["chapter"], "normalized_char_count": len(page["text"])} for page in pages],
        "metadata_schema": {
            "document_id": "string: stable source ID for this local snapshot",
            "source": "string: repository-relative original PDF path",
            "page": "integer: one-based physical PDF page",
            "chapter": "integer: 3 or 4, verified against PDF bookmarks",
            "chapter_title": "string: title from PDF bookmarks",
            "language": "string: en, observed source language",
        },
        "filter_rationale": "chapter distinguishes two source-backed scopes; apply a chapter filter only when supplied by question/context before retrieval, never inferred from gold evidence.",
        "extraction": {"library": "PyMuPDF", "version": pymupdf.VersionBind, "unicode": "NFC", "normalization": "Normalize whitespace within lines; retain line boundaries, headers/footers and attribution. No OCR, dehyphenation or guessed replacement of damaged characters."},
        "limitations": ["Text order, figures and tables require evidence-level review before building benchmark gold.", "Some special characters extract as U+FFFD; counts are logged per page. Evidence has not yet been verified.", "Normalized character counts include retained headers/footers; page eligibility is based on main exposition, not character threshold."],
    }
    (ROOT / "data/manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "pages.jsonl").write_text("".join(json.dumps(page, ensure_ascii=False) + "\n" for page in pages), encoding="utf-8")
    (results / "corpus_extraction_audit.json").write_text(json.dumps({"selected_pages": len(pages), "empty_pages": 0, "pages": audit}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(pages)} pages; {manifest['normalized_char_count']} normalized characters. PyMuPDF {pymupdf.VersionBind}.")


if __name__ == "__main__":
    main()
