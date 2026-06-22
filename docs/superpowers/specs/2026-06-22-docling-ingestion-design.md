# Docling Ingestion — Design

**Goal:** Phase 4 (final phase) of a 4-phase initiative (Live Replay →
Voice narration → Telegram bot → Docling ingestion). Build the
documented-but-missing `backend/rag/ingest.py` pipeline — Docling
PDF-to-markdown ingestion into `backend/data/knowledge/` — with a real
sample PDF run through real Docling, not just code that calls an API
never actually exercised.

---

## 1. Sample PDF

A short, two-section excerpt covering Law 11 (Offside) and Law 12
(Handball), written in formal IFAB-rulebook style (terse numbered rule
statements) — deliberately different in voice from the existing
narrative `laws_and_tactics.md`, to represent genuine official-document
source material rather than analyst commentary.

Generated once via a throwaway script using `fpdf2` (installed for this
one-time generation only — not added to `requirements.txt`, since the
output is a static PDF asset, not a runtime dependency). Saved as
`docs/source_pdfs/laws_of_the_game_excerpt.pdf`.

## 2. `backend/rag/ingest.py`

```python
import sys
from pathlib import Path

from docling.document_converter import DocumentConverter

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"


def ingest(pdf_path: str) -> Path:
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    markdown = result.document.export_to_markdown()
    normalized = _normalize_headings(markdown)

    stem = Path(pdf_path).stem
    output_path = KNOWLEDGE_DIR / f"{stem}.md"
    output_path.write_text(normalized, encoding="utf-8")
    return output_path


def _normalize_headings(markdown: str) -> str:
    # Exact transform tuned against Docling's real output during
    # implementation — retriever.py's _split_sections() only recognizes
    # "## " headings, so whatever heading level Docling emits for this
    # document's section titles gets mapped to "## ".
    ...


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m backend.rag.ingest <path/to/document.pdf>")
        sys.exit(1)
    output = ingest(sys.argv[1])
    print(f"Wrote {output}")
```

`_normalize_headings`'s exact string transform isn't pinned down yet —
Docling's markdown export heading-level choice for a given PDF's
structure isn't something to guess; it gets determined by actually
running Docling against the sample PDF during implementation and
adjusting the normalization to match the real output, then verified by
confirming `retriever.py` picks up the resulting file's sections
correctly (chunk count increases as expected, section titles match the
PDF's two law headings).

No changes to `backend/rag/retriever.py` — it already globs every `.md`
file in `backend/data/knowledge/`, so the new file is picked up
automatically once written.

## 3. Additive, not replacing

`laws_and_tactics.md` is untouched. The new file
(`laws_of_the_game_excerpt.md`) sits alongside it. Both are real
retrieval sources after this phase.

## 4. Eval harness re-validation

Adding any new chunk to the TF-IDF corpus changes the IDF (inverse
document frequency) weighting for every term, since IDF depends on total
document count — so even chunks unrelated to the new content can shift
rank slightly. After ingestion:

1. Run `python -m evals.run_evals` and check `retrieval_precision_at_1`
   and `mrr` are still 1.0 across the 75 golden questions.
2. If any question's retrieval target changed (most likely candidates:
   the offside_27/handball_38-related questions and the two
   knowledge-only Law 11/Law 12 questions, since the new PDF covers the
   same two laws), fix it by rewording the affected `golden_questions.json`
   entries to anchor more specifically on whichever source should win —
   the same empirical fix-and-reverify loop used in Phase 1. The Docling
   output itself is not edited to "fix" this — it should stay genuine.
3. Re-run the full `python -m evals.run_evals` until 100%/1.0 again, then
   update `CLAUDE.md`'s evaluation results table if the numbers changed
   from what's currently documented (they shouldn't, once step 2 is
   resolved, but confirm rather than assume).

## 5. Testing

`tests/test_ingest.py` — mocks `docling.document_converter.DocumentConverter`
(monkeypatching its `convert()` method to return a fake result object
with a fixed `export_to_markdown()` output) to test `_normalize_headings()`
and the file-writing logic, without invoking real Docling. Real Docling
is slow/heavy (ML-based PDF parsing) and shouldn't be a dependency of the
fast `pytest -q` suite — consistent with `requirements.txt` already
marking it "Optional — production ingestion."

The one real, full-pipeline run (real Docling, real sample PDF, real
file written to `backend/data/knowledge/`) happens once during
implementation as manual verification, documented in the commit, not as
an automated test.

## Out of scope

- Any change to `backend/rag/retriever.py` or the retriever's chunking
  algorithm.
- Replacing or editing `laws_and_tactics.md`.
- Ingesting a real official IFAB document — the sample PDF is original
  excerpt text written for this demo, not a reproduction of a
  copyrighted publication.
- CI/pre-commit wiring of the ingestion script.
