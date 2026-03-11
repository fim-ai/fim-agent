"""Security tests for the Python sandbox — AST dunder validation."""

import tempfile
from pathlib import Path

import pytest
from fim_one.core.tool.sandbox.local_backend import _validate_python_ast


class TestASTDunderValidation:
    """Tests for _validate_python_ast."""

    # --- Safe code should pass ---

    def test_safe_print(self):
        assert _validate_python_ast('print("hello")') is None

    def test_safe_class_with_init(self):
        code = """
class Foo:
    def __init__(self):
        self.x = 1
"""
        assert _validate_python_ast(code) is None

    def test_safe_dict_with_dunder_key(self):
        assert _validate_python_ast('d = {"__class__": 1}') is None

    def test_safe_string_with_dunder(self):
        assert _validate_python_ast('s = "__class__"') is None

    def test_safe_math(self):
        assert _validate_python_ast("x = 1 + 2 * 3") is None

    def test_safe_list_comprehension(self):
        assert _validate_python_ast("[x**2 for x in range(10)]") is None

    def test_syntax_error_returns_none(self):
        """Syntax errors should pass AST check (exec handles them)."""
        assert _validate_python_ast("def foo(") is None

    # --- Dangerous code should be blocked ---

    def test_blocked_class_attr(self):
        result = _validate_python_ast("().__class__")
        assert result is not None
        assert "__class__" in result

    def test_blocked_bases_attr(self):
        result = _validate_python_ast("obj.__bases__")
        assert result is not None
        assert "__bases__" in result

    def test_blocked_subclasses(self):
        result = _validate_python_ast("obj.__subclasses__()")
        assert result is not None
        assert "__subclasses__" in result

    def test_blocked_globals(self):
        result = _validate_python_ast("func.__globals__")
        assert result is not None
        assert "__globals__" in result

    def test_blocked_full_exploit_chain(self):
        code = "().__class__.__bases__[0].__subclasses__()"
        result = _validate_python_ast(code)
        assert result is not None

    def test_blocked_init_globals(self):
        code = 'x.__init__.__globals__["system"]("id")'
        result = _validate_python_ast(code)
        assert result is not None


@pytest.mark.asyncio
class TestSandboxIntegration:
    """Integration tests using LocalBackend."""

    async def test_exploit_blocked_by_sandbox(self):
        from fim_one.core.tool.sandbox.local_backend import LocalBackend

        backend = LocalBackend()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await backend.run_code(
                code="print(().__class__.__bases__[0].__subclasses__())",
                language="python",
                exec_dir=Path(tmpdir),
                timeout=10,
            )
        assert "[Sandbox]" in result.stdout
        assert "dunder attribute" in result.stdout

    async def test_safe_code_runs_fine(self):
        from fim_one.core.tool.sandbox.local_backend import LocalBackend

        backend = LocalBackend()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await backend.run_code(
                code="print(sum(range(10)))",
                language="python",
                exec_dir=Path(tmpdir),
                timeout=10,
            )
        assert "45" in result.stdout

    async def test_class_definition_allowed(self):
        from fim_one.core.tool.sandbox.local_backend import LocalBackend

        backend = LocalBackend()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await backend.run_code(
                code="class Foo:\n    def __init__(self):\n        self.x = 42\nprint(Foo().x)",
                language="python",
                exec_dir=Path(tmpdir),
                timeout=10,
            )
        assert "42" in result.stdout
