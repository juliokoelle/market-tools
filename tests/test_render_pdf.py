"""Unit tests for PDF rendering."""
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_render_pdf_returns_correct_path(tmp_path):
    from scripts.render_pdf import render_pdf

    md_text = "# Daily Briefing — 2026-04-25\n\n## Major Story\n\nTest paragraph."

    with patch("scripts.render_pdf.PDF_OUTPUT_DIR", tmp_path):
        with patch("scripts.render_pdf.HTML") as mock_html:
            mock_doc = MagicMock()
            mock_html.return_value = mock_doc
            mock_doc.write_pdf.side_effect = lambda path, **kw: Path(path).touch()

            result = render_pdf(md_text, "2026-04-25")

    assert result == tmp_path / "2026-04-25-briefing.pdf"


def test_render_pdf_filename_uses_date(tmp_path):
    from scripts.render_pdf import render_pdf

    with patch("scripts.render_pdf.PDF_OUTPUT_DIR", tmp_path):
        with patch("scripts.render_pdf.HTML") as mock_html:
            mock_doc = MagicMock()
            mock_html.return_value = mock_doc
            mock_doc.write_pdf.side_effect = lambda path, **kw: Path(path).touch()

            result = render_pdf("# Briefing", "2026-05-01")

    assert result.name == "2026-05-01-briefing.pdf"
    assert result.parent == tmp_path


def test_render_pdf_creates_output_dir(tmp_path):
    from scripts.render_pdf import render_pdf

    subdir = tmp_path / "nested" / "pdf"

    with patch("scripts.render_pdf.PDF_OUTPUT_DIR", subdir):
        with patch("scripts.render_pdf.HTML") as mock_html:
            mock_doc = MagicMock()
            mock_html.return_value = mock_doc
            mock_doc.write_pdf.side_effect = lambda path, **kw: Path(path).touch()

            render_pdf("# Test", "2026-04-25")

    assert subdir.exists()
