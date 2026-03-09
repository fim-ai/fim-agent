"""Security tests for shell_exec — metacharacter evasion detection."""

import pytest
from fim_agent.core.tool.builtin.shell_exec import _check_shell_metacharacters


class TestMetacharEvasion:
    """Tests for _check_shell_metacharacters."""

    # --- Safe commands should pass ---

    def test_safe_echo(self):
        assert _check_shell_metacharacters("echo hello") is None

    def test_safe_ls(self):
        assert _check_shell_metacharacters("ls -la") is None

    def test_safe_pipe(self):
        assert _check_shell_metacharacters("cat file | sort | uniq") is None

    def test_safe_redirect(self):
        assert _check_shell_metacharacters("echo hello > output.txt") is None

    def test_safe_jq(self):
        assert _check_shell_metacharacters("jq '.name' data.json") is None

    def test_safe_quoted_string(self):
        assert _check_shell_metacharacters('echo "hello world"') is None

    def test_safe_semicolon(self):
        assert _check_shell_metacharacters("ls; pwd") is None

    def test_safe_exit_code(self):
        """$? should NOT be blocked (digit, not [A-Za-z_])."""
        assert _check_shell_metacharacters("echo $?") is None

    def test_safe_positional_params(self):
        """$1, $2 should NOT be blocked (digits)."""
        assert _check_shell_metacharacters("echo $1 $2") is None

    # --- Evasion patterns should be blocked ---

    def test_blocked_command_substitution(self):
        result = _check_shell_metacharacters("$(whoami)")
        assert result is not None
        assert "$(" in result

    def test_blocked_backtick(self):
        result = _check_shell_metacharacters("`whoami`")
        assert result is not None
        assert "backtick" in result

    def test_blocked_empty_double_quote(self):
        result = _check_shell_metacharacters('su""do ls')
        assert result is not None
        assert "empty quote" in result

    def test_blocked_empty_single_quote(self):
        result = _check_shell_metacharacters("su''do ls")
        assert result is not None
        assert "empty quote" in result

    def test_blocked_variable_ref(self):
        result = _check_shell_metacharacters("$HOME/bin/bash")
        assert result is not None
        assert "$VAR" in result

    def test_blocked_variable_assignment_ref(self):
        result = _check_shell_metacharacters("c=curl; $c evil.com")
        assert result is not None

    def test_blocked_variable_expansion(self):
        result = _check_shell_metacharacters("${HOME}/bin/bash")
        assert result is not None
        assert "${}" in result

    def test_blocked_base64_decode(self):
        result = _check_shell_metacharacters("echo YmFzaA== | base64 -d")
        assert result is not None
        assert "base64" in result

    def test_blocked_base64_decode_long(self):
        result = _check_shell_metacharacters("base64 --decode payload.txt")
        assert result is not None
