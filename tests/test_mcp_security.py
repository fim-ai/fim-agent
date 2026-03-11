"""Security tests for MCP transport policies."""

import os

import pytest
from fim_one.core.security.mcp import (
    get_allowed_stdio_commands,
    is_stdio_allowed,
    validate_stdio_command,
)


class TestIsStdioAllowed:
    def test_default_is_false(self, monkeypatch):
        monkeypatch.delenv("ALLOW_STDIO_MCP", raising=False)
        assert is_stdio_allowed() is False

    def test_true_when_set_true(self, monkeypatch):
        monkeypatch.setenv("ALLOW_STDIO_MCP", "true")
        assert is_stdio_allowed() is True

    def test_true_when_set_1(self, monkeypatch):
        monkeypatch.setenv("ALLOW_STDIO_MCP", "1")
        assert is_stdio_allowed() is True

    def test_true_when_set_yes(self, monkeypatch):
        monkeypatch.setenv("ALLOW_STDIO_MCP", "yes")
        assert is_stdio_allowed() is True

    def test_false_when_set_false(self, monkeypatch):
        monkeypatch.setenv("ALLOW_STDIO_MCP", "false")
        assert is_stdio_allowed() is False

    def test_false_when_set_empty(self, monkeypatch):
        monkeypatch.setenv("ALLOW_STDIO_MCP", "")
        assert is_stdio_allowed() is False


class TestValidateStdioCommand:
    def test_npx_allowed(self):
        validate_stdio_command("npx")  # Should not raise

    def test_full_path_allowed(self):
        validate_stdio_command("/usr/bin/npx")  # Should not raise

    def test_uvx_allowed(self):
        validate_stdio_command("uvx")

    def test_python_allowed(self):
        validate_stdio_command("python3")

    def test_bash_blocked(self):
        with pytest.raises(ValueError, match="bash"):
            validate_stdio_command("bash")

    def test_sh_blocked(self):
        with pytest.raises(ValueError, match="sh"):
            validate_stdio_command("sh")

    def test_curl_blocked(self):
        with pytest.raises(ValueError, match="curl"):
            validate_stdio_command("curl")

    def test_empty_blocked(self):
        with pytest.raises(ValueError, match="empty"):
            validate_stdio_command("")

    def test_whitespace_only_blocked(self):
        with pytest.raises(ValueError, match="empty"):
            validate_stdio_command("   ")

    def test_custom_allowlist(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_STDIO_COMMANDS", "custom-tool,another")
        validate_stdio_command("custom-tool")  # Should not raise
        with pytest.raises(ValueError):
            validate_stdio_command("npx")  # No longer in list


class TestGetAllowedStdioCommands:
    def test_default_list(self, monkeypatch):
        monkeypatch.delenv("ALLOWED_STDIO_COMMANDS", raising=False)
        allowed = get_allowed_stdio_commands()
        assert "npx" in allowed
        assert "uvx" in allowed
        assert "node" in allowed
        assert "python" in allowed
        assert "python3" in allowed

    def test_custom_list(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_STDIO_COMMANDS", "foo,bar")
        allowed = get_allowed_stdio_commands()
        assert allowed == {"foo", "bar"}
