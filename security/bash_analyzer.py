"""Bash command safety analyzer.

Replaces the simple prefix whitelist with three-level structural analysis:

  safe      — auto-approve (well-known read-only / build commands)
  warn      — show to user before running (state-modifying but common)
  dangerous — require explicit confirmation (potentially irreversible at scale)

Usage::

    from security.bash_analyzer import analyze_bash, BashRiskLevel

    risk, reason = analyze_bash("curl https://example.com/install.sh | bash")
    # → (BashRiskLevel.dangerous, "pipe download to shell execution")
"""
from __future__ import annotations

import re
from enum import Enum


class BashRiskLevel(Enum):
    safe      = "safe"
    warn      = "warn"
    dangerous = "dangerous"


# ── Dangerous patterns ─────────────────────────────────────────────────────
# These match commands that can cause catastrophic, hard-to-reverse damage.

_DANGEROUS: list[tuple[re.Pattern, str]] = [
    # rm -rf on / or /* (root filesystem wipe)
    (
        re.compile(
            r'\brm\b[^#\n]*-[A-Za-z]*r[A-Za-z]*f[A-Za-z]*\s+(/[\s*]?$|/\*|/\s)',
            re.IGNORECASE,
        ),
        "recursive force-delete on root path",
    ),
    (
        re.compile(
            r'\brm\b[^#\n]*-[A-Za-z]*f[A-Za-z]*r[A-Za-z]*\s+(/[\s*]?$|/\*|/\s)',
            re.IGNORECASE,
        ),
        "recursive force-delete on root path",
    ),
    # Pipe download directly into a shell interpreter
    (
        re.compile(
            r'(curl|wget)\b[^#\n]*\|\s*(bash|sh|zsh|fish|python[23]?|perl|ruby)\b',
            re.IGNORECASE,
        ),
        "pipe download to shell execution",
    ),
    # Download then execute pattern: wget -O /tmp/x.sh && bash /tmp/x.sh
    (
        re.compile(
            r'(curl|wget)\b[^#\n]*&&[^#\n]*(bash|sh|zsh|python[23]?|perl|ruby)\b',
            re.IGNORECASE,
        ),
        "download and execute pattern",
    ),
    # Direct write to block devices
    (
        re.compile(r'>\s*/dev/sd[a-z]\b', re.IGNORECASE),
        "direct write to disk block device",
    ),
    (
        re.compile(r'\bdd\b[^#\n]*\bof=/dev/sd[a-z]\b', re.IGNORECASE),
        "dd write to disk block device",
    ),
    # Privileged recursive delete
    (
        re.compile(r'\bsudo\b[^#\n]*\brm\b[^#\n]*-[A-Za-z]*r', re.IGNORECASE),
        "privileged recursive delete",
    ),
    # chmod 777 on root or system directories
    (
        re.compile(
            r'\bchmod\b[^#\n]*777[^#\n]*/(?:$|\s|etc|usr|bin|sbin|lib|var|home)',
            re.IGNORECASE,
        ),
        "world-writable permissions on system path",
    ),
    # Overwrite /etc/passwd, /etc/hosts, /etc/shadow
    (
        re.compile(r'>\s*/etc/(passwd|shadow|hosts|sudoers)\b', re.IGNORECASE),
        "overwrite critical system file",
    ),
]


# ── Warn patterns ──────────────────────────────────────────────────────────
# State-modifying but commonly legitimate; user should see before running.

_WARN: list[tuple[re.Pattern, str]] = [
    # Any rm -r (not already caught as dangerous)
    (
        re.compile(r'\brm\b[^#\n]*-[A-Za-z]*r[A-Za-z]*', re.IGNORECASE),
        "recursive delete",
    ),
    # chmod on any path
    (
        re.compile(r'\bchmod\b', re.IGNORECASE),
        "file permission change",
    ),
    # chown
    (
        re.compile(r'\bchown\b', re.IGNORECASE),
        "file ownership change",
    ),
    # Environment variable tampering (PATH, LD_PRELOAD, etc.)
    (
        re.compile(
            r'(?:^|export\s+)(PATH|LD_PRELOAD|LD_LIBRARY_PATH|DYLD_LIBRARY_PATH)\s*=',
            re.IGNORECASE | re.MULTILINE,
        ),
        "environment variable modification",
    ),
    # Network download (without shell pipe — already caught above)
    (
        re.compile(r'\b(curl|wget)\b(?![^#\n]*\|\s*(bash|sh|zsh))', re.IGNORECASE),
        "network download",
    ),
    # git push / git force-push
    (
        re.compile(r'\bgit\s+push\b', re.IGNORECASE),
        "push to remote repository",
    ),
    # Package installation
    (
        re.compile(r'\b(pip[23]?|pip)\s+install\b', re.IGNORECASE),
        "Python package installation",
    ),
    (
        re.compile(r'\bnpm\s+install\b', re.IGNORECASE),
        "npm package installation",
    ),
    (
        re.compile(r'\bcargo\s+install\b', re.IGNORECASE),
        "Rust package installation",
    ),
    (
        re.compile(r'\bapt(?:-get)?\s+(install|remove|purge)\b', re.IGNORECASE),
        "system package management",
    ),
    (
        re.compile(r'\bbrew\s+install\b', re.IGNORECASE),
        "Homebrew package installation",
    ),
    # Command substitution in arguments (e.g. cmd $(evil))
    (
        re.compile(r'\$\([^)]+\)', re.IGNORECASE),
        "command substitution",
    ),
    # Path traversal escaping cwd
    (
        re.compile(r'(\.\./){4,}'),
        "deep path traversal",
    ),
]


# ── Safe prefixes ──────────────────────────────────────────────────────────
# Commands that are clearly read-only or well-understood safe operations.
# Checked with startswith — keep entries sorted longest-first for specificity.

_SAFE_PREFIXES: tuple[str, ...] = (
    # git read-only
    "git log", "git status", "git diff", "git show", "git branch",
    "git remote -v", "git remote show", "git stash list", "git tag",
    "git describe", "git shortlog", "git rev-parse", "git ls-files",
    "git blame", "git annotate", "git bisect",
    # Metadata / inspection
    "ls", "ll", "la", "dir",
    "cat ", "bat ", "head ", "tail ", "wc ",
    "pwd", "echo ", "printf ",
    "date", "which ", "type ", "command ",
    "env", "printenv", "uname", "whoami", "id",
    "file ", "stat ",
    # Search / find (read-only)
    "find ", "grep ", "rg ", "ag ", "fd ",
    "ack ",
    # System info (read-only)
    "df ", "du ", "free ", "top -bn", "ps ",
    "lsof ", "netstat ", "ss ", "ifconfig", "ip ",
    "uptime", "hostname",
    # Language runtimes (local script execution)
    "python -c", "python3 -c",
    "python -m pytest", "python -m py_compile", "python -m mypy",
    "python -m flake8", "python -m black --check", "python -m ruff check",
    "pytest", "py.test",
    "node -e", "node -p",
    "ruby -e", "perl -e",
    # Build / test (well-known safe)
    "make ", "make\n", "make ",
    "cargo build", "cargo test", "cargo check", "cargo clippy", "cargo fmt",
    "cargo run",
    "npm run ", "npm test", "npm run build", "npm run lint",
    "go build", "go test", "go vet", "go fmt", "go mod",
    "mvn test", "mvn compile", "mvn package",
    "gradle test", "gradle build",
    # Package info (read-only)
    "pip show", "pip list", "pip freeze", "pip check",
    "npm list", "npm ls", "npm info", "npm audit",
    "cargo metadata",
    "brew list", "brew info", "brew outdated",
    # HTTP read-only
    "curl -I ", "curl --head ",
    "curl -s https://", "curl -s http://",
)


# ── Core analyzer ──────────────────────────────────────────────────────────

def analyze_bash(command: str) -> tuple[BashRiskLevel, str]:
    """Analyze a shell command and return a risk level with a short reason.

    Args:
        command: the shell command string to analyze

    Returns:
        (BashRiskLevel.safe,      "")       — auto-approvable
        (BashRiskLevel.warn,      reason)   — show to user, but not catastrophic
        (BashRiskLevel.dangerous, reason)   — must confirm before running

    The analysis is conservative on both ends: known-safe commands are
    whitelisted, known-dangerous patterns are flagged; everything else
    lands in ``warn``.
    """
    cmd = command.strip()
    if not cmd:
        return BashRiskLevel.safe, ""

    # 1. Check dangerous patterns first (highest priority)
    for pattern, reason in _DANGEROUS:
        if pattern.search(cmd):
            return BashRiskLevel.dangerous, reason

    # 2. Check safe prefixes
    cmd_lower = cmd.lower()
    for prefix in _SAFE_PREFIXES:
        if cmd_lower.startswith(prefix.lower()):
            # Extra guard: safe prefix followed by a pipe into a shell?
            if re.search(r'\|\s*(bash|sh|zsh|fish)\b', cmd, re.IGNORECASE):
                return BashRiskLevel.dangerous, "pipe to shell execution"
            return BashRiskLevel.safe, ""

    # 3. Check warn patterns
    for pattern, reason in _WARN:
        if pattern.search(cmd):
            return BashRiskLevel.warn, reason

    # 4. Default: unknown command — warn
    first_word = cmd.split()[0] if cmd.split() else cmd
    return BashRiskLevel.warn, f"unrecognised command '{first_word}'"
