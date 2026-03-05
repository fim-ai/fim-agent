"""Docker-based sandbox backend.

Executes code and shell commands inside ephemeral Docker containers for
full OS-level isolation.  No module blocklists are needed — the container
boundary IS the security boundary.

Requirements:
  - Docker CLI must be installed and the daemon must be running.
  - Images are pulled on first use (may add latency on first call).
    Pre-pull recommended: ``docker pull python:3.11-slim node:20-slim``

Environment variables (all optional):
  DOCKER_PYTHON_IMAGE  — Python image (default: python:3.11-slim)
  DOCKER_NODE_IMAGE    — Node.js image (default: node:20-slim)
  DOCKER_SHELL_IMAGE   — Shell image   (default: python:3.11-slim)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from .protocol import SandboxResult

logger = logging.getLogger(__name__)

# Default images — overridable via env vars (see __init__.py factory)
_DEFAULT_PYTHON_IMAGE = "python:3.11-slim"
_DEFAULT_NODE_IMAGE = "node:20-slim"
_DEFAULT_SHELL_IMAGE = "python:3.11-slim"

# Map language → (image, entrypoint argv)
_LANGUAGE_CONFIG: dict[str, tuple[str, list[str]]] = {
    "python": (_DEFAULT_PYTHON_IMAGE, ["python"]),
    "javascript": (_DEFAULT_NODE_IMAGE, ["node"]),
}


class DockerBackend:
    """Sandbox backend that runs all code inside Docker containers.

    Security properties (per container):
      - ``--network=none`` for code execution (no exfiltration possible)
      - ``--memory=256m`` RAM cap
      - ``--cpus=0.5`` CPU cap
      - ``--rm`` containers are removed immediately on exit
      - exec_dir / sandbox_dir are volume-mounted as ``/workspace``

    Shell execution gets network access (for curl etc.) but the same
    memory/CPU limits apply.
    """

    def __init__(
        self,
        *,
        python_image: str = _DEFAULT_PYTHON_IMAGE,
        node_image: str = _DEFAULT_NODE_IMAGE,
        shell_image: str = _DEFAULT_SHELL_IMAGE,
    ) -> None:
        self._images = {
            "python": python_image,
            "javascript": node_image,
        }
        self._shell_image = shell_image
        # Entrypoints per language (image is per-instance, not global)
        self._entrypoints: dict[str, list[str]] = {
            "python": ["python"],
            "javascript": ["node"],
        }

    async def run_code(
        self,
        code: str,
        *,
        language: str,
        exec_dir: Path,
        timeout: int,
    ) -> SandboxResult:
        image = self._images.get(language)
        if image is None:
            return SandboxResult(
                stdout="",
                stderr="",
                exit_code=-1,
                error=f"Unsupported language '{language}' in docker backend.",
            )

        ext = "py" if language == "python" else "js"
        exec_dir.mkdir(parents=True, exist_ok=True)
        script_name = f"script_{uuid.uuid4().hex[:8]}.{ext}"
        script_path = exec_dir / script_name
        script_path.write_text(code, encoding="utf-8")

        entrypoint = self._entrypoints[language]
        container_name = f"fim-sandbox-{uuid.uuid4().hex[:8]}"

        cmd = [
            "docker", "run", "--rm",
            "--name", container_name,
            "--network=none",
            "--memory=256m", "--cpus=0.5",
            "-v", f"{exec_dir}:/workspace",
            "-w", "/workspace",
            image, *entrypoint, f"/workspace/{script_name}",
        ]

        logger.debug(
            "docker run_code: container=%s image=%s language=%s exec_dir=%s script=%s timeout=%ds",
            container_name, image, language, exec_dir, script_name, timeout,
        )
        result = await self._run_container(cmd, stdin_data="", timeout=timeout,
                                           container_name=container_name)
        result.script_path = script_path
        return result

    async def run_shell(
        self,
        command: str,
        *,
        sandbox_dir: Path,
        timeout: int,
    ) -> SandboxResult:
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        container_name = f"fim-sandbox-{uuid.uuid4().hex[:8]}"

        # Shell execution allows network access (curl, wget, etc.)
        cmd = [
            "docker", "run", "--rm", "-i",
            "--name", container_name,
            "--memory=256m", "--cpus=0.5",
            "-v", f"{sandbox_dir}:/workspace",
            "-w", "/workspace",
            self._shell_image, "/bin/sh",
        ]

        logger.debug(
            "docker run_shell: container=%s image=%s sandbox_dir=%s timeout=%ds",
            container_name, self._shell_image, sandbox_dir, timeout,
        )
        return await self._run_container(cmd, stdin_data=command, timeout=timeout,
                                         container_name=container_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_container(
        self,
        cmd: list[str],
        *,
        stdin_data: str,
        timeout: int,
        container_name: str = "",
    ) -> SandboxResult:
        """Spawn a Docker container, pipe *stdin_data*, and collect output."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            return SandboxResult(
                stdout="",
                stderr="",
                exit_code=-1,
                error=(
                    "Docker CLI not found. Install Docker or set "
                    "CODE_EXEC_BACKEND=local to use local execution."
                ),
            )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=stdin_data.encode()),
                timeout=timeout,
            )
        except TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            await proc.wait()
            logger.debug("docker container=%s timed out", container_name)
            return SandboxResult(
                stdout="", stderr="", exit_code=124, timed_out=True
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = proc.returncode or 0

        logger.debug("docker container=%s exited exit_code=%d", container_name, exit_code)

        # Detect OOM kill
        error: str | None = None
        if exit_code == 137:
            error = "Container killed (OOM): memory limit exceeded (256m)."
            logger.warning("Docker container OOM killed. cmd=%s", cmd[3:6])

        # Detect missing image (first-run scenario)
        if "Unable to find image" in stderr:
            logger.warning(
                "Docker image not pre-pulled — pulling now. This may add latency. "
                "Run 'docker pull %s' to avoid this delay.", cmd[-2]
            )

        return SandboxResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            error=error,
        )
