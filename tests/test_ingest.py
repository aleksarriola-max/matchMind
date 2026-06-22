from backend.rag import ingest


def test_normalize_headings_collapses_whitespace_and_drops_empty_sections():
    raw = (
        "## Document Title\n\n"
        "## Law 11 -- Offside\n\n"
        "A player  is  in  an  offside  position.\n\n"
        "## Law 12 -- Handball\n\n"
        "Handling the ball is an offence.\n"
    )
    normalized = ingest._normalize_headings(raw)

    assert "## Document Title" not in normalized
    assert normalized.count("## ") == 2
    assert "## Law 11 -- Offside" in normalized
    assert "A player is in an offside position." in normalized
    assert "## Law 12 -- Handball" in normalized
    assert "Handling the ball is an offence." in normalized


def test_normalize_headings_drops_all_empty_sections():
    raw = "## Only A Title\n\n## Another Empty One\n\n"
    assert ingest._normalize_headings(raw) == "\n"


class _FakeDocument:
    def __init__(self, markdown):
        self._markdown = markdown

    def export_to_markdown(self):
        return self._markdown


class _FakeResult:
    def __init__(self, markdown):
        self.document = _FakeDocument(markdown)


def test_ingest_writes_normalized_markdown_to_knowledge_dir(tmp_path, monkeypatch):
    fake_markdown = (
        "## Title\n\n"
        "## Law 99 -- Sample Rule\n\n"
        "This is a  sample  rule  body.\n"
    )
    monkeypatch.setattr(ingest, "KNOWLEDGE_DIR", tmp_path)
    monkeypatch.setattr(ingest, "_convert_pdf", lambda pdf_path: _FakeResult(fake_markdown))

    output_path = ingest.ingest("some/path/my_document.pdf")

    assert output_path == tmp_path / "my_document.md"
    content = output_path.read_text(encoding="utf-8")
    assert "## Title" not in content
    assert "## Law 99 -- Sample Rule" in content
    assert "This is a sample rule body." in content
