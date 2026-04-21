"""Run a single hook shell command and return its parsed JSON output."""
from __future__ import annotations

import json
import subprocess
import sys


def run_hook(command: str, stdin_data: dict, timeout: int = 10) -> dict | None:
    """Execute a hook command, feeding stdin_data as JSON on stdin.

    Args:
        command:    shell command string (run with shell=True)
        stdin_data: dict serialized to JSON and passed on stdin
        timeout:    seconds before the process is killed (default 10)

    Returns:
        Parsed JSON dict from stdout, or None on error / non-zero exit.

    Side effects:
        Prints a warning to stderr on failure (non-zero exit, timeout, exception).
    """
    try:
        proc = subprocess.run(
            command,
            shell=True,
            input=json.dumps(stdin_data).encode(),
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"[hooks] Warning: hook timed out after {timeout}s: {command!r}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"[hooks] Warning: hook failed to start: {exc}", file=sys.stderr)
        return None

    if proc.returncode != 0:
        stderr_text = proc.stderr.decode(errors="replace").strip()
        msg = f"[hooks] Warning: hook exited {proc.returncode}: {command!r}"
        if stderr_text:
            msg += f"\n  stderr: {stderr_text[:300]}"
        print(msg, file=sys.stderr)
        return None

    stdout = proc.stdout.decode(errors="replace").strip()
    if not stdout:
        return {}

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        # Hook printed non-JSON — ignore output, treat as success with no decision
        return {}
