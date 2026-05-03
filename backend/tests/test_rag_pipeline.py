import pytest

from app.services import rag_pipeline
from app.services.rag_pipeline import RAGChunkPlanner, RAGDecisionPolicy, RAGDocumentParser


def test_markdown_parser_and_chunk_hashes_are_deterministic():
    parser = RAGDocumentParser()
    planner = RAGChunkPlanner()
    parsed = parser.parse_markdown(
        "# Protein\n\nProtein supports muscle repair.\n\n## Timing\n\nEat enough across the day.",
        title="Nutrition",
        source_uri="internal://nutrition",
    )

    plans_a = planner.build_chunks(
        parsed,
        source_title="Nutrition",
        category="nutrition",
        tags=["protein"],
        source_grade="B",
        embedding_model="gemini-embedding-001",
    )
    plans_b = planner.build_chunks(
        parsed,
        source_title="Nutrition",
        category="nutrition",
        tags=["protein"],
        source_grade="B",
        embedding_model="gemini-embedding-001",
    )

    assert parsed.parser_type == "markdown"
    assert parsed.parser_confidence >= 0.8
    assert plans_a[0].chunk_strategy == "section"
    assert plans_a[0].content_hash == plans_b[0].content_hash
    assert plans_a[0].anchor_hash == plans_b[0].anchor_hash
    assert plans_a[0].embedding_input_hash == plans_b[0].embedding_input_hash
    assert plans_a[0].metadata["metadata_schema_version"] == 1
    assert plans_a[0].metadata["normalization_version"] == "chunk-normalize-v1"


def test_text_parser_uses_paragraph_anchor_metadata():
    parser = RAGDocumentParser()
    planner = RAGChunkPlanner()
    parsed = parser.parse_text(
        "First paragraph about warmups.\n\nSecond paragraph about progressive overload.",
        title="Exercise",
    )
    plans = planner.build_chunks(
        parsed,
        source_title="Exercise",
        category="exercise",
        tags=["training"],
        source_grade="B",
        embedding_model="gemini-embedding-001",
    )

    assert parsed.parser_type == "text"
    assert plans[0].chunk_strategy == "paragraph"
    assert "paragraph_range" in plans[0].metadata


def test_pdf_text_parser_records_page_anchor(monkeypatch, tmp_path):
    class FakePage:
        def __init__(self, text):
            self.text = text

        def extract_text(self):
            return self.text

    class FakeReader:
        pages = [FakePage("Page one text."), FakePage("")]

    monkeypatch.setattr(rag_pipeline, "PdfReader", lambda path: FakeReader())

    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF fake")
    parsed = RAGDocumentParser().parse_file(pdf_path, parser_type="pdf_text")

    assert parsed.parser_type == "pdf_text"
    assert parsed.sections[0].page_number == 1
    assert parsed.skipped_sections == 1
    assert 0.7 <= parsed.parser_confidence < 0.95


def test_html_parser_uses_hybrid_parent_child_chunk_metadata():
    parser = RAGDocumentParser()
    planner = RAGChunkPlanner()
    html = """
    <html>
      <head><title>Official Training Guide</title></head>
      <body>
        <nav>navigation should be removed</nav>
        <main>
          <h1>Physical Activity</h1>
          <p>Adults should move regularly and reduce sedentary time.</p>
          <ul><li>Strength training supports healthy muscles.</li></ul>
          <h2>Safety</h2>
          <p>People with concerning symptoms should seek professional guidance.</p>
          <table><tr><th>Goal</th><th>Example</th></tr><tr><td>Cardio</td><td>Brisk walking</td></tr></table>
        </main>
      </body>
    </html>
    """

    parsed = parser.parse_html(
        html,
        source_uri="https://example.org/activity",
        source_url="https://example.org/activity",
        content_type="text/html",
        fetch_metadata={"etag": '"abc"', "last_modified": "Mon, 01 Jan 2024 00:00:00 GMT"},
    )
    plans_a = planner.build_chunks(
        parsed,
        source_title=parsed.title,
        category="exercise",
        tags=["guideline"],
        source_grade="A",
        embedding_model="gemini-embedding-001",
    )
    plans_b = planner.build_chunks(
        parsed,
        source_title=parsed.title,
        category="exercise",
        tags=["guideline"],
        source_grade="A",
        embedding_model="gemini-embedding-001",
    )

    assert parsed.parser_type == "html"
    assert parsed.parser_version == "html-parser-v1"
    assert parsed.parser_confidence == 0.95
    assert plans_a[0].chunk_strategy == "hybrid_evidence"
    assert plans_a[0].anchor_hash == plans_b[0].anchor_hash
    assert plans_a[0].metadata["chunk_role"] == "child_evidence"
    assert plans_a[0].metadata["parent_heading_path"] == ["Physical Activity"]
    assert plans_a[0].metadata["parent_section_hash"] == plans_b[0].metadata["parent_section_hash"]
    assert plans_a[0].metadata["source_url"] == "https://example.org/activity"
    assert "navigation should be removed" not in parsed.normalized_content
    assert "Goal | Example" in parsed.normalized_content


@pytest.mark.parametrize(
    ("kwargs", "expected_action"),
    [
        (
            {
                "source_exists": True,
                "source_hash_same": True,
                "parser_confidence": 0.95,
                "change_ratio": 0.0,
                "parser_or_chunker_changed": False,
                "estimated_embedding_seconds": 0.0,
            },
            "skip_refresh",
        ),
        (
            {
                "source_exists": True,
                "source_hash_same": False,
                "parser_confidence": 0.95,
                "change_ratio": 0.10,
                "parser_or_chunker_changed": False,
                "estimated_embedding_seconds": 2.0,
            },
            "partial_refresh",
        ),
        (
            {
                "source_exists": True,
                "source_hash_same": False,
                "parser_confidence": 0.95,
                "change_ratio": 0.60,
                "parser_or_chunker_changed": False,
                "estimated_embedding_seconds": 2.0,
            },
            "full_reindex",
        ),
        (
            {
                "source_exists": True,
                "source_hash_same": True,
                "parser_confidence": 0.95,
                "change_ratio": 0.0,
                "parser_or_chunker_changed": True,
                "estimated_embedding_seconds": 2.0,
            },
            "full_reindex",
        ),
        (
            {
                "source_exists": False,
                "source_hash_same": False,
                "parser_confidence": 0.50,
                "change_ratio": 1.0,
                "parser_or_chunker_changed": False,
                "estimated_embedding_seconds": 2.0,
            },
            "manual_review_required",
        ),
        (
            {
                "source_exists": True,
                "source_hash_same": False,
                "parser_confidence": 0.95,
                "change_ratio": 0.10,
                "parser_or_chunker_changed": False,
                "estimated_embedding_seconds": 999.0,
            },
            "defer_reembedding",
        ),
    ],
)
def test_decision_policy_selects_action_by_operational_context(kwargs, expected_action):
    decision = RAGDecisionPolicy().choose_ingest_action(
        **kwargs,
        allowed_embedding_seconds=300.0,
        partial_refresh_threshold=0.30,
        parser_confidence_threshold=0.70,
        source_grade="B",
        category="nutrition",
    )

    assert decision.selected_action == expected_action
    assert decision.policy_version == "rag-policy-v1"
    assert "accepted" in decision.tradeoffs
