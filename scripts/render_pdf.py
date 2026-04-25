"""
Markdown → PDF export with FT-inspired styling.

Requires weasyprint system libs. On macOS: brew install pango gdk-pixbuf
On Render: handled by Dockerfile (libpango-1.0-0, libcairo2, libgdk-pixbuf2.0-0).

Usage:
    python scripts/render_pdf.py [YYYY-MM-DD]
    # reads outputs/YYYY-MM-DD-briefing.md
    # writes outputs/pdf/YYYY-MM-DD-briefing.pdf

Or import:
    from scripts.render_pdf import render_pdf
    pdf_path = render_pdf(markdown_text, "2026-04-25")
"""

from __future__ import annotations

import sys
from pathlib import Path

import markdown as md_lib
from weasyprint import CSS, HTML

PDF_OUTPUT_DIR = Path("outputs/pdf")

# FT-inspired: cream background, Georgia serif body, Helvetica headers
_FT_CSS = """
@page {
    size: A4;
    margin: 2.8cm 2.2cm 2.5cm 2.2cm;
}
body {
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 10.5pt;
    line-height: 1.72;
    color: #1a1a1a;
    background: #fffff8;
}
.page-header {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 8pt;
    color: #888;
    border-bottom: 1.5px solid #ccc;
    padding-bottom: 5pt;
    margin-bottom: 20pt;
    display: flex;
    justify-content: space-between;
}
h1 {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 20pt;
    font-weight: 700;
    color: #1a1a1a;
    border-bottom: 2.5px solid #1a1a1a;
    padding-bottom: 7pt;
    margin: 0 0 18pt 0;
    line-height: 1.2;
}
h2 {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 12.5pt;
    font-weight: 700;
    color: #1a1a1a;
    margin: 22pt 0 7pt 0;
    border-top: 1px solid #ddd;
    padding-top: 10pt;
    page-break-after: avoid;
}
h3 {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 10.5pt;
    font-weight: 700;
    margin: 14pt 0 5pt 0;
    page-break-after: avoid;
}
p {
    margin: 0 0 9pt 0;
    text-align: justify;
    hyphens: auto;
    orphans: 3;
    widows: 3;
}
hr {
    border: none;
    border-top: 1px solid #ddd;
    margin: 14pt 0;
}
strong { font-weight: bold; }
em     { font-style: italic; }
code {
    font-family: 'Courier New', monospace;
    font-size: 9pt;
    background: #f5f5f0;
    padding: 1pt 3pt;
}
ul, ol {
    margin: 4pt 0 9pt 18pt;
}
li {
    margin-bottom: 3pt;
}
"""


def render_pdf(markdown_text: str, run_date: str) -> Path:
    """
    Convert a Markdown briefing string to a PDF file.
    Returns the path to the written PDF.
    """
    PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    html_body = md_lib.markdown(
        markdown_text,
        extensions=["tables", "fenced_code"],
    )

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Daily Briefing {run_date}</title>
</head>
<body>
  <div class="page-header">
    <span>Julio's Daily Briefing</span>
    <span>{run_date}</span>
  </div>
  {html_body}
</body>
</html>"""

    output_path = PDF_OUTPUT_DIR / f"{run_date}-briefing.pdf"
    HTML(string=full_html).write_pdf(str(output_path), stylesheets=[CSS(string=_FT_CSS)])
    return output_path


if __name__ == "__main__":
    from scripts.utils import today

    run_date = sys.argv[1] if len(sys.argv) > 1 else today()
    md_path = Path(f"outputs/{run_date}-briefing.md")

    if not md_path.exists():
        print(f"Error: {md_path} does not exist. Generate a briefing first.")
        sys.exit(1)

    pdf_path = render_pdf(md_path.read_text(encoding="utf-8"), run_date)
    print(f"PDF written: {pdf_path}")
