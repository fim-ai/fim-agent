"""Tests for the vision-aware document processing module."""

from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fim_one.core.document.processor import (
    DocumentProcessor,
    DocumentResult,
    _extract_text_sync,
    _get_doc_processing_mode,
    _get_doc_vision_dpi,
    _get_doc_vision_max_pages,
)


# ---------------------------------------------------------------------------
# DocumentResult dataclass
# ---------------------------------------------------------------------------


class TestDocumentResult:
    """Tests for the DocumentResult dataclass."""

    def test_defaults(self) -> None:
        result = DocumentResult(text="hello")
        assert result.text == "hello"
        assert result.page_images == []
        assert result.mode_used == "text"
        assert result.page_count == 0

    def test_vision_result(self) -> None:
        result = DocumentResult(
            text="content",
            page_images=["data:image/png;base64,abc"],
            mode_used="vision",
            page_count=1,
        )
        assert result.mode_used == "vision"
        assert len(result.page_images) == 1
        assert result.page_count == 1

    def test_none_text(self) -> None:
        result = DocumentResult(text=None)
        assert result.text is None


# ---------------------------------------------------------------------------
# Environment configuration helpers
# ---------------------------------------------------------------------------


class TestEnvConfig:
    """Tests for environment variable configuration helpers."""

    def test_default_mode(self) -> None:
        assert _get_doc_processing_mode() == "auto"

    def test_custom_mode(self) -> None:
        with patch.dict("os.environ", {"DOCUMENT_PROCESSING_MODE": "vision"}):
            assert _get_doc_processing_mode() == "vision"

    def test_default_dpi(self) -> None:
        assert _get_doc_vision_dpi() == 150

    def test_custom_dpi(self) -> None:
        with patch.dict("os.environ", {"DOCUMENT_VISION_DPI": "300"}):
            assert _get_doc_vision_dpi() == 300

    def test_default_max_pages(self) -> None:
        assert _get_doc_vision_max_pages() == 20

    def test_custom_max_pages(self) -> None:
        with patch.dict("os.environ", {"DOCUMENT_VISION_MAX_PAGES": "10"}):
            assert _get_doc_vision_max_pages() == 10


# ---------------------------------------------------------------------------
# _extract_text_sync
# ---------------------------------------------------------------------------


class TestExtractTextSync:
    """Tests for the synchronous text extraction function."""

    def test_plain_text(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("Hello world", encoding="utf-8")
        assert _extract_text_sync(f) == "Hello world"

    def test_markdown(self, tmp_path: Path) -> None:
        f = tmp_path / "readme.md"
        f.write_text("# Title", encoding="utf-8")
        assert _extract_text_sync(f) == "# Title"

    def test_json_pretty_prints(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text('{"key":"value"}', encoding="utf-8")
        result = _extract_text_sync(f)
        assert result is not None
        assert json.loads(result) == {"key": "value"}
        assert "\n" in result  # pretty-printed

    def test_json_malformed_returns_raw(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.json"
        f.write_text("{broken", encoding="utf-8")
        assert _extract_text_sync(f) == "{broken"

    def test_csv(self, tmp_path: Path) -> None:
        f = tmp_path / "data.csv"
        f.write_text("a,b\n1,2\n", encoding="utf-8")
        assert _extract_text_sync(f) == "a,b\n1,2\n"

    def test_image_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "photo.jpg"
        f.write_bytes(b"\xff\xd8\xff\xe0")
        assert _extract_text_sync(f) is None

    def test_png_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "img.png"
        f.write_bytes(b"\x89PNG")
        assert _extract_text_sync(f) is None

    def test_unsupported_extension_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "binary.dat"
        f.write_bytes(b"\x00\x01\x02")
        assert _extract_text_sync(f) is None

    def test_pdf_with_pdfplumber(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page 1 text"
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"pdfplumber": MagicMock()}):
            import sys

            sys.modules["pdfplumber"].open.return_value = mock_pdf
            result = _extract_text_sync(f)
            assert result == "Page 1 text"

    def test_pdf_without_pdfplumber(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")

        with patch.dict("sys.modules", {"pdfplumber": None}):
            result = _extract_text_sync(f)
            assert result is not None
            assert "pdfplumber" in result

    def test_docx_with_markitdown(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.docx"
        f.write_bytes(b"PK")

        mock_result = MagicMock()
        mock_result.text_content = "Document content"
        mock_converter = MagicMock()
        mock_converter.convert.return_value = mock_result

        mock_module = MagicMock()
        mock_module.MarkItDown.return_value = mock_converter

        with patch.dict("sys.modules", {"markitdown": mock_module}):
            result = _extract_text_sync(f)
            assert result == "Document content"

    def test_docx_without_markitdown(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.docx"
        f.write_bytes(b"PK")

        with patch.dict("sys.modules", {"markitdown": None}):
            result = _extract_text_sync(f)
            assert result is not None
            assert "markitdown" in result

    def test_html_extraction(self, tmp_path: Path) -> None:
        f = tmp_path / "page.html"
        f.write_text("<html><body>Hello</body></html>", encoding="utf-8")
        result = _extract_text_sync(f)
        assert result is not None
        assert "Hello" in result

    def test_python_extraction(self, tmp_path: Path) -> None:
        f = tmp_path / "script.py"
        f.write_text("print('hello')", encoding="utf-8")
        assert _extract_text_sync(f) == "print('hello')"


# ---------------------------------------------------------------------------
# DocumentProcessor.extract_text (async wrapper)
# ---------------------------------------------------------------------------


class TestExtractTextAsync:
    """Tests for the async extract_text method."""

    @pytest.mark.asyncio
    async def test_delegates_to_sync(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("async test", encoding="utf-8")
        result = await DocumentProcessor.extract_text(f)
        assert result == "async test"


# ---------------------------------------------------------------------------
# DocumentProcessor.render_pdf_pages
# ---------------------------------------------------------------------------


class TestRenderPdfPages:
    """Tests for PDF page rendering using PyMuPDF."""

    @pytest.mark.asyncio
    async def test_renders_pages(self) -> None:
        fake_png = b"\x89PNG\r\n\x1a\nfake_image_data"

        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = fake_png

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page, mock_page]))
        mock_doc.close = MagicMock()

        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix.return_value = MagicMock()

        with patch.dict("sys.modules", {"fitz": mock_fitz}):
            result = await DocumentProcessor.render_pdf_pages(
                Path("/fake/doc.pdf"), dpi=150, max_pages=20
            )
            assert len(result) == 2
            assert result[0] == fake_png

    @pytest.mark.asyncio
    async def test_respects_max_pages(self) -> None:
        fake_png = b"PNG"

        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = fake_png

        pages = []
        for _ in range(5):
            p = MagicMock()
            p.get_pixmap.return_value = mock_pix
            pages.append(p)

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter(pages))
        mock_doc.close = MagicMock()

        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix.return_value = MagicMock()

        with patch.dict("sys.modules", {"fitz": mock_fitz}):
            result = await DocumentProcessor.render_pdf_pages(
                Path("/fake/doc.pdf"), dpi=150, max_pages=2
            )
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_import_error_propagates(self) -> None:
        """When fitz is not installed, ImportError should propagate."""
        with patch.dict("sys.modules", {"fitz": None}):
            # The import inside the thread will fail
            with pytest.raises(Exception):
                await DocumentProcessor.render_pdf_pages(
                    Path("/fake/doc.pdf"), dpi=150, max_pages=20
                )


# ---------------------------------------------------------------------------
# DocumentProcessor.process_document
# ---------------------------------------------------------------------------


class TestProcessDocument:
    """Tests for the main process_document method."""

    @pytest.mark.asyncio
    async def test_text_mode_for_non_pdf(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")

        result = await DocumentProcessor.process_document(
            f, mode="auto", supports_vision=True
        )
        assert result.mode_used == "text"
        assert result.text == "hello"
        assert result.page_images == []

    @pytest.mark.asyncio
    async def test_text_mode_explicit(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")

        with patch.object(
            DocumentProcessor, "extract_text", return_value="PDF text"
        ):
            result = await DocumentProcessor.process_document(
                f, mode="text", supports_vision=True
            )
            assert result.mode_used == "text"
            assert result.text == "PDF text"
            assert result.page_images == []

    @pytest.mark.asyncio
    async def test_vision_mode_for_pdf(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")

        fake_png = b"\x89PNGfake"
        b64_png = base64.b64encode(fake_png).decode("ascii")

        with (
            patch.object(
                DocumentProcessor, "extract_text", return_value="PDF text"
            ),
            patch.object(
                DocumentProcessor,
                "render_pdf_pages",
                return_value=[fake_png, fake_png],
            ),
        ):
            result = await DocumentProcessor.process_document(
                f, mode="auto", supports_vision=True, max_pages=20, dpi=150
            )
            assert result.mode_used == "vision"
            assert result.text == "PDF text"
            assert len(result.page_images) == 2
            assert result.page_count == 2
            assert f"data:image/png;base64,{b64_png}" in result.page_images[0]

    @pytest.mark.asyncio
    async def test_auto_mode_no_vision_support(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")

        with patch.object(
            DocumentProcessor, "extract_text", return_value="PDF text"
        ):
            result = await DocumentProcessor.process_document(
                f, mode="auto", supports_vision=False
            )
            assert result.mode_used == "text"

    @pytest.mark.asyncio
    async def test_vision_fallback_on_render_error(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")

        with (
            patch.object(
                DocumentProcessor, "extract_text", return_value="PDF text"
            ),
            patch.object(
                DocumentProcessor,
                "render_pdf_pages",
                side_effect=RuntimeError("render failed"),
            ),
        ):
            result = await DocumentProcessor.process_document(
                f, mode="vision", supports_vision=True
            )
            assert result.mode_used == "text"
            assert result.text == "PDF text"

    @pytest.mark.asyncio
    async def test_vision_fallback_on_import_error(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")

        with (
            patch.object(
                DocumentProcessor, "extract_text", return_value="PDF text"
            ),
            patch.object(
                DocumentProcessor,
                "render_pdf_pages",
                side_effect=ImportError("No fitz"),
            ),
        ):
            result = await DocumentProcessor.process_document(
                f, mode="vision", supports_vision=True
            )
            assert result.mode_used == "text"

    @pytest.mark.asyncio
    async def test_vision_mode_non_pdf_falls_to_text(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.docx"
        f.write_bytes(b"PK")

        with patch.object(
            DocumentProcessor, "extract_text", return_value="docx text"
        ):
            result = await DocumentProcessor.process_document(
                f, mode="vision", supports_vision=True
            )
            # Vision mode only applies to PDFs; others fall back to text
            assert result.mode_used == "text"

    @pytest.mark.asyncio
    async def test_env_defaults_used(self, tmp_path: Path) -> None:
        """When max_pages and dpi are None, env defaults are used."""
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")

        with (
            patch.object(
                DocumentProcessor, "extract_text", return_value="text"
            ),
            patch.object(
                DocumentProcessor, "render_pdf_pages", return_value=[b"PNG"]
            ) as mock_render,
            patch(
                "fim_one.core.document.processor._get_doc_vision_dpi",
                return_value=200,
            ),
            patch(
                "fim_one.core.document.processor._get_doc_vision_max_pages",
                return_value=5,
            ),
        ):
            await DocumentProcessor.process_document(
                f, mode="vision", supports_vision=True
            )
            mock_render.assert_called_once_with(f, 200, 5)


# ---------------------------------------------------------------------------
# DocumentProcessor.get_or_create_cached_pages
# ---------------------------------------------------------------------------


class TestCachedPages:
    """Tests for the page caching mechanism."""

    @pytest.mark.asyncio
    async def test_creates_cache(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")

        fake_png = b"\x89PNGdata"
        with patch.object(
            DocumentProcessor,
            "render_pdf_pages",
            return_value=[fake_png],
        ):
            urls = await DocumentProcessor.get_or_create_cached_pages(
                f, dpi=150, max_pages=20
            )
            assert len(urls) == 1
            assert urls[0].startswith("data:image/png;base64,")

            # Verify cache files were created
            pages_dir = tmp_path / ".pages" / "doc"
            assert pages_dir.exists()
            cached = list(pages_dir.glob("page_*.png"))
            assert len(cached) == 1

    @pytest.mark.asyncio
    async def test_uses_existing_cache(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")

        # Pre-create cache
        pages_dir = tmp_path / ".pages" / "doc"
        pages_dir.mkdir(parents=True)
        cached_png = b"\x89PNGcached"
        (pages_dir / "page_0000.png").write_bytes(cached_png)

        with patch.object(
            DocumentProcessor, "render_pdf_pages"
        ) as mock_render:
            urls = await DocumentProcessor.get_or_create_cached_pages(
                f, dpi=150, max_pages=20
            )
            # Should NOT call render since cache exists
            mock_render.assert_not_called()
            assert len(urls) == 1
            b64 = base64.b64encode(cached_png).decode("ascii")
            assert urls[0] == f"data:image/png;base64,{b64}"

    @pytest.mark.asyncio
    async def test_cache_respects_max_pages(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")

        # Pre-create cache with 5 pages
        pages_dir = tmp_path / ".pages" / "doc"
        pages_dir.mkdir(parents=True)
        for i in range(5):
            (pages_dir / f"page_{i:04d}.png").write_bytes(b"PNG")

        urls = await DocumentProcessor.get_or_create_cached_pages(
            f, dpi=150, max_pages=3
        )
        assert len(urls) == 3

    @pytest.mark.asyncio
    async def test_render_failure_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")

        with patch.object(
            DocumentProcessor,
            "render_pdf_pages",
            side_effect=RuntimeError("render failed"),
        ):
            urls = await DocumentProcessor.get_or_create_cached_pages(
                f, dpi=150, max_pages=20
            )
            assert urls == []

    @pytest.mark.asyncio
    async def test_import_error_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")

        with patch.object(
            DocumentProcessor,
            "render_pdf_pages",
            side_effect=ImportError("No fitz"),
        ):
            urls = await DocumentProcessor.get_or_create_cached_pages(
                f, dpi=150, max_pages=20
            )
            assert urls == []


# ---------------------------------------------------------------------------
# Files.py delegation
# ---------------------------------------------------------------------------


class TestFilesExtractContent:
    """Test that files.py _extract_content delegates to DocumentProcessor."""

    def test_delegates_to_processor(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("delegated", encoding="utf-8")

        from fim_one.web.api.files import _extract_content

        result = _extract_content(f)
        assert result == "delegated"
