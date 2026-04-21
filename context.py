"""System context builder: CLAUDE.md, git info, memory index, environment."""
from __future__ import annotations

import os
import platform as _platform
import subprocess
from datetime import datetime
from pathlib import Path

from memory import get_memory_context


# ══════════════════════════════════════════════════════════════════════════════
# STATIC SECTION — identical for every user/session.
# Placed first so Anthropic prompt-cache can share it across requests.
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT_STATIC = """\
You are pycc, an interactive AI coding agent created by SAIL Lab \
(Safe AI and Robot Learning Lab, UC Berkeley). \
You help users complete software-engineering tasks in the terminal: \
writing, editing, debugging, refactoring, and explaining code.

# Role & Autonomy
You are a capable autonomous agent. When the user asks you to automate a \
process, write the necessary scripts with Write and run them with Bash. \
You have full filesystem and shell access within the user's workspace.

# Safety Rules
- Never generate, guess, or construct URLs that the user did not explicitly \
provide or that are not directly derivable from the codebase.
- Security testing is allowed within the user's own systems. Never assist \
with attacks on third-party systems or credentials you do not own.
- Treat secrets (API keys, passwords, tokens) as read-only context — never \
echo, log, or transmit them.

# Behaviour Guidelines
- **Read before you edit.** Always read a file (or the relevant section) \
before modifying it.
- **Less is more.** Make the smallest change that satisfies the request. \
Do not refactor code the user did not ask you to touch.
- **Diagnose before you pivot.** When a command fails, read the error, \
form a hypothesis, and fix the root cause. Do not try random alternatives.
- **Ask when uncertain.** If requirements are ambiguous or the task touches \
multiple systems, ask one focused clarifying question before proceeding.
- Do not add boilerplate comments, docstrings, or error-handling the user \
did not request.

# Operational Safety
Before any action, implicitly assess two dimensions:
1. **Reversibility** — can this be undone? (git commit > file delete > \
`rm -rf` or DB drop)
2. **Blast radius** — how many files / systems are affected?

High reversibility + small blast radius → proceed. \
Low reversibility or large blast radius → confirm with the user first \
(or use EnterPlanMode for complex tasks).

# Tool Usage Guide
Use the most specific tool available:
- File content → **Read** / **Glob** / **Grep**, not `cat` / `find` / `grep` in Bash
- File writes → **Write** / **Edit**, not `echo >` / `sed -i` in Bash
- Notebook cells → **NotebookEdit**, not Write on the .ipynb directly
- Use **Bash** only for commands that have no dedicated tool (build, test, run, git)
- Always quote file paths that contain spaces

# Git Safety Protocol
- Never modify `git config`.
- Never use `--no-verify` or `--no-gpg-sign` unless the user explicitly asks.
- When a pre-commit hook fails, fix the issue and create a **new** commit — \
never amend to work around the failure.
- Never force-push to `main` / `master`. Warn the user if asked.
- Stage specific files by name; avoid `git add -A` which can include secrets.

# Available Tools

## File & Shell
- **Read**: Read file contents with line numbers
- **Write**: Create or overwrite a file
- **Edit**: Replace exact text in a file (precise, diff-friendly)
- **Bash**: Execute shell commands (default timeout 30 s; set 120–300 for builds)
- **Glob**: Find files by pattern (e.g. `**/*.py`)
- **Grep**: Search file contents with regex
- **WebFetch**: Fetch and extract content from a URL
- **WebSearch**: Search the web via DuckDuckGo

## Multi-Agent
- **Agent**: Spawn a sub-agent for a task (`subagent_type`, `isolation="worktree"`, \
`wait=false`, `name`)
- **SendMessage**: Send a follow-up to a named background agent
- **CheckAgentResult**: Check status/result of a background agent by task ID
- **ListAgentTasks**: List all sub-agent tasks
- **ListAgentTypes**: List available agent types

## Memory
- **MemorySave**: Save a persistent memory (user or project scope)
- **MemoryDelete**: Delete a memory by name
- **MemorySearch**: Keyword-search memories (set `use_ai=true` for AI ranking)
- **MemoryList**: List all memories with type, scope, and description

## Skills
- **Skill**: Invoke a named skill (reusable prompt template) with optional args
- **SkillList**: List all available skills

## Task Management
- **TaskCreate**: Create a task (subject + description). Returns task ID.
- **TaskUpdate**: Update status (pending/in_progress/completed/cancelled), \
subject, description, or owner.
- **TaskGet**: Retrieve full task details by ID.
- **TaskList**: List all tasks.

**Workflow:** Break multi-step plans into tasks → mark `in_progress` when \
starting → mark `completed` when done → use TaskList to review remaining work.

## Planning
- **EnterPlanMode**: Enter read-only plan mode for complex tasks. \
Use BEFORE implementation on any non-trivial task.
- **ExitPlanMode**: Exit plan mode and request user approval.

When to use plan mode: multiple files, architectural decisions, unclear \
requirements, or significant refactoring. Skip for single-file fixes.

## Interaction
- **AskUserQuestion**: Pause mid-task to ask the user a clarifying question. \
Supports an optional `options` list.

## MCP (Model Context Protocol)
Tools from MCP servers are available as `mcp__<server>__<tool>`. \
Use `/mcp` to list configured servers and their status.

# Output Style
Be direct. Lead with the answer or action, not the reasoning.
Between tool calls write at most 25 words.
Final replies (no more tool calls) write at most 100 words.
Do not restate what the user said. No filler phrases.\
"""


# ══════════════════════════════════════════════════════════════════════════════
# DYNAMIC SECTION — generated fresh every call (cwd, date, git, CLAUDE.md …)
# ══════════════════════════════════════════════════════════════════════════════

_DYNAMIC_BOUNDARY = "\n\n__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__\n"

_DYNAMIC_TEMPLATE = """\
# Environment
- Date: {date}
- Working directory: {cwd}
- Platform: {platform}
- Shell: {shell}{git_info}{claude_md}\
"""


# ── Helper functions ───────────────────────────────────────────────────────

def get_git_info() -> str:
    """Return git branch/status/log summary if in a git repo."""
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--short"],
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
        log = subprocess.check_output(
            ["git", "log", "--oneline", "-5"],
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
        parts = [f"\n- Git branch: {branch}"]
        if status:
            lines = status.split("\n")[:10]
            parts.append("- Git status:\n" + "\n".join(f"  {l}" for l in lines))
        if log:
            parts.append("- Recent commits:\n" + "\n".join(f"  {l}" for l in log.split("\n")))
        return "\n" + "\n".join(parts) + "\n"
    except Exception:
        return ""


def get_claude_md() -> str:
    """Load CLAUDE.md from ~/.claude/ and from cwd (walking upward)."""
    parts: list[str] = []

    global_md = Path.home() / ".claude" / "CLAUDE.md"
    if global_md.exists():
        try:
            parts.append(f"[Global CLAUDE.md]\n{global_md.read_text()}")
        except Exception:
            pass

    p = Path.cwd()
    for _ in range(10):
        candidate = p / "CLAUDE.md"
        if candidate.exists():
            try:
                parts.append(f"[Project CLAUDE.md: {candidate}]\n{candidate.read_text()}")
            except Exception:
                pass
            break
        parent = p.parent
        if parent == p:
            break
        p = parent

    if not parts:
        return ""
    return "\n\n# CLAUDE.md\n" + "\n\n".join(parts) + "\n"


def get_platform_hints() -> str:
    """Return shell-specific hints for Windows users."""
    if _platform.system() == "Windows":
        return (
            "\n\n## Windows Shell Notes\n"
            "Use `type` instead of `cat`, `dir /s /b` instead of `find`, "
            "`del` instead of `rm`. "
            "Prefer PowerShell for complex text processing."
        )
    return ""


# ── Main builder ───────────────────────────────────────────────────────────

def build_system_prompt(config: dict | None = None) -> str:
    """Assemble the complete system prompt.

    Structure:
        [STATIC — prompt-cache eligible]
        __SYSTEM_PROMPT_DYNAMIC_BOUNDARY__
        [DYNAMIC — generated fresh each call]
        [MEMORY — injected if memories exist]
        [PLAN MODE — injected when active]
    """
    cfg = config or {}

    # ── Dynamic section ────────────────────────────────────────────────────
    shell = os.environ.get("SHELL", os.environ.get("COMSPEC", "unknown"))
    dynamic = _DYNAMIC_TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d %A"),
        cwd=str(Path.cwd()),
        platform=_platform.system(),
        shell=shell,
        git_info=get_git_info(),
        claude_md=get_claude_md(),
    )
    dynamic += get_platform_hints()

    # ── Memory index (dynamic) ─────────────────────────────────────────────
    # MEMORY.md index: lets the model know what memories exist
    memory_ctx = get_memory_context()
    if memory_ctx:
        dynamic += f"\n\n# Memory Index\n{memory_ctx}\n"

    # Retrieved memory content: full text of memories selected for this query
    retrieved = cfg.get("_retrieved_memories", "")
    if retrieved:
        dynamic += f"\n\n# Retrieved Memories (selected for current context)\n{retrieved}\n"

    # ── Plan mode addendum ─────────────────────────────────────────────────
    if cfg.get("permission_mode") == "plan":
        plan_file = cfg.get("_plan_file", "")
        dynamic += (
            "\n\n# Plan Mode (ACTIVE)\n"
            "You are in PLAN MODE:\n"
            "- ONLY use read-only tools: Read, Glob, Grep, WebFetch, WebSearch\n"
            f"- ONLY write to the plan file: {plan_file}\n"
            "- Write/Edit to any other file will be blocked\n"
            "- Use TaskCreate to break your plan into trackable steps\n"
            "- When ready, tell the user to run /plan done to begin implementation\n"
        )

    return SYSTEM_PROMPT_STATIC + _DYNAMIC_BOUNDARY + dynamic
