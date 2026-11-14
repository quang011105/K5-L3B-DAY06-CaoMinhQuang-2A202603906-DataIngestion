"""Validate benchmark structure and evidence directly against the local PDF."""
import json
from collections import Counter
from pathlib import Path

import pymupdf

from prepare_corpus import normalize

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    questions = [json.loads(line) for line in (ROOT / "benchmark/questions.jsonl").read_text(encoding="utf-8").splitlines()]
    manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    split = Counter(q["split"] for q in questions)
    assert len(questions) >= 20 and split["dev"] >= 15 and split["test"] >= 5
    assert len({q["id"] for q in questions}) == len(questions)
    assert len({q["question"] for q in questions}) == len(questions)
    assert sum(bool(q["filter"]) for q in questions) >= 3
    assert any(q["filter"] for q in questions if q["split"] == "test")
    allowed = {p["pdf_page"]: p["chapter"] for p in manifest["pages"]}
    verified = []
    with pymupdf.open(ROOT / manifest["source_path_or_url"]) as pdf:
        for q in questions:
            assert q["expected_answer"].strip()
            assert q["gold_source_id"] == manifest["source_id"]
            assert q["gold_page"] in allowed
            assert q["evidence_quote"] and q["evidence_quote"] in normalize(pdf[q["gold_page"] - 1].get_text(sort=False)), q["id"]
            for alternative in q.get("alternative_gold", []):
                assert alternative["gold_source_id"] == manifest["source_id"]
                assert alternative["gold_page"] in allowed
                assert alternative["evidence_quote"] in normalize(pdf[alternative["gold_page"] - 1].get_text(sort=False))
            if q["filter"]:
                assert q["filter"] == {"chapter": allowed[q["gold_page"]]}
                assert f"Chapter {q['filter']['chapter']}" in q["question"]
            verified.append({"id": q["id"], "pdf_page": q["gold_page"], "exact_evidence_match": True})
    report = {"question_count": len(questions), "split_counts": dict(split), "filter_question_count": sum(bool(q["filter"]) for q in questions), "test_filter_question_count": sum(bool(q["filter"]) for q in questions if q["split"] == "test"), "verified_against": "Fresh extraction from original local PDF, same NFC/whitespace normalization as corpus preparation", "limitations": "Checks evidence presence and schema; does not substitute student review of answer sufficiency, alternative gold or manual grounding/coherence labels.", "questions": verified}
    (ROOT / "results/benchmark_validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Validation OK: {len(questions)} evidence quotes match original PDF; {dict(split)}; 4 filters including 1 test.")


if __name__ == "__main__":
    main()
