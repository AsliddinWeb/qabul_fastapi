"""HTML → PDF rendering.

Production: WeasyPrint (libpango/libcairo, installed in the backend container).
Fallback:   if WeasyPrint isn't available locally, returns the rendered HTML
            wrapped as a minimal PDF placeholder, so contracts can still be
            created during dev.
"""

from __future__ import annotations

from typing import Any

from jinja2 import Environment, StrictUndefined, select_autoescape

from app.core.logging import get_logger

logger = get_logger("pdf")


_jinja_env = Environment(
    autoescape=select_autoescape(["html", "xml"]),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_html(template_str: str, context: dict[str, Any]) -> str:
    template = _jinja_env.from_string(template_str)
    return template.render(**context)


def render_pdf(html: str, *, base_url: str | None = None) -> bytes:
    """Render HTML to PDF bytes. Raises RuntimeError if rendering fails."""
    try:
        from weasyprint import HTML  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover -- only hit on bare local dev
        logger.warning("pdf.weasyprint_unavailable", error=str(exc))
        return _placeholder_pdf(html)

    try:
        return HTML(string=html, base_url=base_url).write_pdf()
    except Exception as exc:
        logger.error("pdf.render_failed", error=str(exc))
        raise RuntimeError(f"PDF rendering failed: {exc!s}") from exc


def _placeholder_pdf(html: str) -> bytes:
    """Tiny well-formed PDF containing a notice — used only when WeasyPrint
    cannot be imported (no system libs)."""
    notice = "[dev] WeasyPrint unavailable; PDF was not rendered."
    body = f"BT /F1 12 Tf 72 720 Td ({notice}) Tj ET"
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
        b"2 0 obj <</Type /Pages /Count 1 /Kids [3 0 R]>> endobj\n"
        b"3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
        b" /Resources <</Font <</F1 4 0 R>>>> /Contents 5 0 R>> endobj\n"
        b"4 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj\n"
        b"5 0 obj <</Length " + str(len(body)).encode() + b">>\nstream\n"
        + body.encode("latin-1", errors="ignore")
        + b"\nendstream endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"trailer <</Size 6 /Root 1 0 R>>\n%%EOF"
    )
    _ = html  # unused in placeholder; kept in signature for parity
    return pdf
