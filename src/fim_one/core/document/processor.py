"""Vision-aware document processing.

Provides text extraction and PDF page rendering for both traditional
text-based and vision-model-based document understanding.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------


def _get_doc_processing_mode() -> str:
    """Return the configured document processing mode (auto | vision | text)."""
    return os.environ.get("DOCUMENT_PROCESSING_MODE", "auto")


def _get_doc_vision_dpi() -> int:
    """Return the configured DPI for PDF page rendering."""
    return int(os.environ.get("DOCUMENT_VISION_DPI", "150"))


def _get_doc_vision_max_pages() -> int:
    """Return the maximum number of PDF pages to render as images."""
    return int(os.environ.get("DOCUMENT_VISION_MAX_PAGES", "20"))


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}


@dataclass
class DocumentResult:
    """Result of processing a document through the vision-aware pipeline."""

    text: str | None
    page_images: list[str] = field(default_factory=list)  # base64 data URLs
    mode_used: str = "text"  # "vision" | "text"
    page_count: int = 0


# ---------------------------------------------------------------------------
# Main processor
# ---------------------------------------------------------------------------


class DocumentProcessor:
    """Vision-aware document processing.

    Combines traditional text extraction with optional PDF page rendering
    for vision-capable LLMs.
    """

    @staticmethod
    async def extract_text(file_path: Path) -> str | None:
        """Extract text content from a file.

        Supports plain text, JSON, CSV, PDF (via pdfplumber), and
        Office documents (via markitdown). Images return ``None``.

        Args:
            file_path: Path to the file to extract text from.

        Returns:
            Extracted text content, a fallback message when optional
            dependencies are missing, or ``None`` for unsupported types.
        """
        return await asyncio.to_thread(_extract_text_sync, file_path)

    @staticmethod
    async def render_pdf_pages(
        file_path: Path,
        dpi: int = 150,
        max_pages: int = 20,
    ) -> list[bytes]:
        """Render PDF pages as PNG images using PyMuPDF (fitz).

        Args:
            file_path: Path to the PDF file.
            dpi: Rendering resolution (default 150).
            max_pages: Maximum number of pages to render (default 20).

        Returns:
            List of PNG image bytes, one per rendered page.

        Raises:
            ImportError: If PyMuPDF is not installed.
        """

        def _render() -> list[bytes]:
            import fitz  # type: ignore[import-untyped]

            doc = fitz.open(str(file_path))
            images: list[bytes] = []
            try:
                for i, page in enumerate(doc):
                    if i >= max_pages:
                        break
                    mat = fitz.Matrix(dpi / 72, dpi / 72)
                    pix = page.get_pixmap(matrix=mat)
                    images.append(pix.tobytes("png"))
            finally:
                doc.close()
            return images

        return await asyncio.to_thread(_render)

    @staticmethod
    async def process_document(
        file_path: Path,
        mode: str = "auto",
        supports_vision: bool = False,
        max_pages: int | None = None,
        dpi: int | None = None,
    ) -> DocumentResult:
        """Process a document with a vision-aware strategy.

        Args:
            file_path: Path to the document file.
            mode: Processing mode — ``"vision"``, ``"text"``, or ``"auto"``
                (default). In auto mode, vision is used when the model
                supports it and the document is a PDF.
            supports_vision: Whether the active model supports vision.
            max_pages: Maximum PDF pages to render (falls back to env var).
            dpi: Rendering DPI (falls back to env var).

        Returns:
            A :class:`DocumentResult` with extracted text and optional
            rendered page images.
        """
        if max_pages is None:
            max_pages = _get_doc_vision_max_pages()
        if dpi is None:
            dpi = _get_doc_vision_dpi()

        suffix = file_path.suffix.lower()

        # Always extract text (needed for both modes)
        text = await DocumentProcessor.extract_text(file_path)

        # Determine effective mode
        if mode == "auto":
            effective = (
                "vision" if supports_vision and suffix == ".pdf" else "text"
            )
        else:
            effective = mode

        page_images: list[str] = []
        page_count = 0

        if effective == "vision" and suffix == ".pdf":
            try:
                raw_images = await DocumentProcessor.render_pdf_pages(
                    file_path, dpi, max_pages
                )
                page_count = len(raw_images)
                page_images = [
                    f"data:image/png;base64,{base64.b64encode(img).decode('ascii')}"
                    for img in raw_images
                ]
            except ImportError:
                logger.warning(
                    "PyMuPDF not installed, falling back to text-only "
                    "document processing. Install with: uv add PyMuPDF"
                )
                effective = "text"
            except Exception:
                logger.warning(
                    "PDF rendering failed, falling back to text",
                    exc_info=True,
                )
                effective = "text"

        if not page_images:
            effective = "text"

        return DocumentResult(
            text=text,
            page_images=page_images,
            mode_used=effective,
            page_count=page_count,
        )

    @staticmethod
    async def get_or_create_cached_pages(
        file_path: Path,
        dpi: int | None = None,
        max_pages: int | None = None,
    ) -> list[str]:
        """Return cached PDF page images, rendering them if not yet cached.

        Page images are stored as individual PNG files under a ``.pages/``
        directory next to the original file for fast retrieval during chat.

        Args:
            file_path: Path to the PDF file.
            dpi: Rendering DPI (falls back to env var).
            max_pages: Maximum pages to render (falls back to env var).

        Returns:
            List of base64 data URL strings for each page.
        """
        if dpi is None:
            dpi = _get_doc_vision_dpi()
        if max_pages is None:
            max_pages = _get_doc_vision_max_pages()

        pages_dir = file_path.parent / ".pages" / file_path.stem
        pages_dir.mkdir(parents=True, exist_ok=True)

        # Check for existing cached pages
        existing = sorted(pages_dir.glob("page_*.png"))
        if existing:
            data_urls: list[str] = []
            for pg in existing[:max_pages]:
                raw = await asyncio.to_thread(pg.read_bytes)
                b64 = base64.b64encode(raw).decode("ascii")
                data_urls.append(f"data:image/png;base64,{b64}")
            return data_urls

        # Render and cache
        try:
            raw_images = await DocumentProcessor.render_pdf_pages(
                file_path, dpi, max_pages
            )
        except ImportError:
            logger.warning("PyMuPDF not installed, cannot render PDF pages")
            return []
        except Exception:
            logger.warning("PDF rendering failed", exc_info=True)
            return []

        data_urls = []
        for i, img_bytes in enumerate(raw_images):
            page_file = pages_dir / f"page_{i:04d}.png"
            await asyncio.to_thread(page_file.write_bytes, img_bytes)
            b64 = base64.b64encode(img_bytes).decode("ascii")
            data_urls.append(f"data:image/png;base64,{b64}")

        return data_urls


# ---------------------------------------------------------------------------
# Sync text extraction (delegated from the upload flow)
# ---------------------------------------------------------------------------


def _extract_text_sync(file_path: Path) -> str | None:
    """Synchronous text extraction implementation.

    This is the single source of truth for text extraction logic.
    Both the async :meth:`DocumentProcessor.extract_text` and the
    upload-time ``_extract_content`` call this function.
    """
    suffix = file_path.suffix.lower()

    # Images have no extractable text content
    if suffix in IMAGE_EXTENSIONS:
        return None

    # Plain text family
    if suffix in {".txt", ".md", ".py", ".js", ".html", ".htm"}:
        return file_path.read_text(encoding="utf-8", errors="replace")

    # JSON -- parse and pretty-print
    if suffix == ".json":
        try:
            data = json.loads(
                file_path.read_text(encoding="utf-8", errors="replace")
            )
            return json.dumps(data, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            return file_path.read_text(encoding="utf-8", errors="replace")

    # CSV -- raw text
    if suffix == ".csv":
        return file_path.read_text(encoding="utf-8", errors="replace")

    # PDF -- requires pdfplumber (optional)
    if suffix == ".pdf":
        try:
            import pdfplumber
        except ImportError:
            return "[PDF content extraction requires pdfplumber]"
        pages_text: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
        return "\n".join(pages_text) if pages_text else None

    # Office documents (DOCX, XLSX, XLS, PPTX) -- requires markitdown
    if suffix in {".docx", ".xlsx", ".xls", ".pptx"}:
        try:
            from markitdown import MarkItDown
        except ImportError:
            return (
                f"[{suffix.upper().lstrip('.')} content extraction "
                f"requires markitdown]"
            )
        converter = MarkItDown()
        result = converter.convert(str(file_path))
        content = result.text_content or ""
        return content if content.strip() else None

    return None
