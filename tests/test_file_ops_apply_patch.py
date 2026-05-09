"""Tests for the ``file_ops`` tool's ``apply_patch`` operation.

Covers the happy path plus parse errors, missing files, and path-traversal
defense.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fim_one.core.tool.builtin.file_ops import FileOpsTool


@pytest.fixture()
def tool(tmp_path: Path) -> FileOpsTool:
    return FileOpsTool(workspace_dir=tmp_path)


@pytest.mark.asyncio
async def test_apply_patch_happy_path_replaces_lines(tool: FileOpsTool, tmp_path: Path) -> None:
    target = tmp_path / "hello.txt"
    target.write_text("line1\nline2\nline3\n", encoding="utf-8")

    diff = "\n".join(["@@ line1", "-line2", "+updated", " line3"])
    result = await tool.run(operation="apply_patch", path="hello.txt", patch=diff)

    assert isinstance(result, str)
    assert result.startswith("Patch applied to hello.txt")
    assert "fuzz=0" in result
    assert target.read_text(encoding="utf-8") == "line1\nupdated\nline3\n"


@pytest.mark.asyncio
async def test_apply_patch_malformed_patch_returns_error(
    tool: FileOpsTool, tmp_path: Path
) -> None:
    target = tmp_path / "f.txt"
    target.write_text("one\ntwo\n", encoding="utf-8")

    # Context line ' x' does not exist in the file — V4A treats this as a
    # parse/apply failure.
    bad_diff = "\n".join(["@@ -1,2 +1,2 @@", " x", "-two", "+2"])
    result = await tool.run(operation="apply_patch", path="f.txt", patch=bad_diff)

    assert isinstance(result, str)
    assert result.startswith("[Error] Patch parse/apply failed:")
    # File must remain untouched on failure.
    assert target.read_text(encoding="utf-8") == "one\ntwo\n"


@pytest.mark.asyncio
async def test_apply_patch_requires_patch_argument(tool: FileOpsTool, tmp_path: Path) -> None:
    target = tmp_path / "g.txt"
    target.write_text("hi\n", encoding="utf-8")

    result = await tool.run(operation="apply_patch", path="g.txt", patch="")
    assert result == "[Error] patch is required for apply_patch"


@pytest.mark.asyncio
async def test_apply_patch_file_not_found(tool: FileOpsTool) -> None:
    diff = "\n".join(["@@ line1", "-line2", "+updated"])
    result = await tool.run(operation="apply_patch", path="missing.txt", patch=diff)

    assert isinstance(result, str)
    assert result.startswith("[Error] File not found:")


@pytest.mark.asyncio
async def test_apply_patch_rejects_path_traversal(tool: FileOpsTool, tmp_path: Path) -> None:
    # Attempt to escape the workspace via parent-directory references.
    diff = "\n".join(["@@", "+pwn"])
    result = await tool.run(
        operation="apply_patch", path="../../etc/passwd", patch=diff
    )
    assert result == "[Error] Path traversal detected — access denied."


@pytest.mark.asyncio
async def test_apply_patch_rejects_non_file_target(
    tool: FileOpsTool, tmp_path: Path
) -> None:
    (tmp_path / "subdir").mkdir()
    diff = "\n".join(["@@", "+x"])
    result = await tool.run(operation="apply_patch", path="subdir", patch=diff)

    assert isinstance(result, str)
    assert result.startswith("[Error] Not a file:")


@pytest.mark.asyncio
async def test_apply_patch_records_fuzz_for_whitespace_drift(
    tool: FileOpsTool, tmp_path: Path
) -> None:
    # Anchor matches by stripped content only — V4A bumps fuzz by 1 for the
    # rstrip-tolerant pass on context line lookup.
    target = tmp_path / "h.txt"
    target.write_text("line1   \nline2\nline3\n", encoding="utf-8")

    diff = "\n".join(["@@ line1", "-line2", "+updated", " line3"])
    result = await tool.run(operation="apply_patch", path="h.txt", patch=diff)

    assert isinstance(result, str)
    assert result.startswith("Patch applied to h.txt")
    # fuzz should be > 0 because the anchor "line1" has trailing spaces in
    # the source file, so an exact match fails and the rstrip fallback kicks in.
    assert "fuzz=" in result
    fuzz_part = result.rsplit("fuzz=", 1)[1].rstrip(")")
    assert int(fuzz_part) >= 1
