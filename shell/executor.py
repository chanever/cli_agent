"""Vulnerable shell command executor for research baseline use."""

from __future__ import annotations

import subprocess


def _tail(value: str, max_chars: int) -> str:
    """Keep the final max_chars characters from command output."""
    return value[-max_chars:] if len(value) > max_chars else value


def run_command(command: str, cwd: str, timeout: int, max_output_chars: int) -> dict:
    """Run a shell command directly with minimal mediation."""
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": completed.returncode == 0,
            "stdout": _tail(completed.stdout or "", max_output_chars),
            "stderr": _tail(completed.stderr or "", max_output_chars),
            "exit_code": completed.returncode,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        return {
            "success": False,
            "stdout": _tail(stdout, max_output_chars),
            "stderr": _tail(stderr, max_output_chars),
            "exit_code": None,
            "timed_out": True,
        }
