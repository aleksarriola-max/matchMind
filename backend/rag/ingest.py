import re
import sys
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"


def _convert_pdf(pdf_path: str):
    # Imported lazily -- docling pulls in heavy ML dependencies (torch,
    # transformers) that would otherwise slow down every test run that
    # merely imports this module, even when the conversion itself is mocked.
    from docling.document_converter import DocumentConverter

    return DocumentConverter().convert(pdf_path)


def ingest(pdf_path: str) -> Path:
    result = _convert_pdf(pdf_path)
    markdown = result.document.export_to_markdown()
    normalized = _normalize_headings(markdown)

    stem = Path(pdf_path).stem
    output_path = KNOWLEDGE_DIR / f"{stem}.md"
    output_path.write_text(normalized, encoding="utf-8")
    return output_path


def _normalize_headings(markdown: str) -> str:
    # Collapse PDF text-extraction's irregular inter-word spacing
    # (justified-text artifacts), then drop any "## " section with no
    # body text -- e.g. a document title heading with nothing before the
    # next heading -- since it would only add an empty, zero-signal
    # chunk to the retriever.
    markdown = re.sub(r" {2,}", " ", markdown)

    lines = markdown.splitlines()
    sections: list[tuple[str, str]] = []
    current_title = None
    current_body: list[str] = []
    for line in lines:
        if line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_body).strip()))
            current_title = line
            current_body = []
        elif current_title is not None:
            current_body.append(line)
    if current_title is not None:
        sections.append((current_title, "\n".join(current_body).strip()))

    kept = [f"{title}\n\n{body}" for title, body in sections if body]
    return "\n\n".join(kept) + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m backend.rag.ingest <path/to/document.pdf>")
        sys.exit(1)
    output = ingest(sys.argv[1])
    print(f"Wrote {output}")
