"""Load hooks configuration from .claude/settings.json files.

Search order (highest priority last — later values win):
  1. ~/.claude/settings.json          (user-level defaults)
  2. <cwd>/.claude/settings.json      (project-level, found by walking upward)

Project-level settings take priority over user-level settings.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .types import HooksConfig, HookMatcher, HookCommand


# ── Settings file search ───────────────────────────────────────────────────

def _find_project_settings(cwd: str) -> Path | None:
    """Walk upward from cwd looking for .claude/settings.json."""
    current = Path(cwd).resolve()
    while True:
        candidate = current / ".claude" / "settings.json"
        if candidate.exists():
            return candidate
        parent = current.parent
        if parent == current:
            return None
        current = parent


def load_settings_json(cwd: str) -> dict:
    """Load and merge user + project settings.json files.

    Returns a merged dict; project-level keys override user-level keys.
    Returns {} if neither file exists.
    """
    merged: dict = {}

    # 1. User-level baseline
    user_settings = Path.home() / ".claude" / "settings.json"
    if user_settings.exists():
        try:
            merged.update(json.loads(user_settings.read_text(encoding="utf-8")))
        except Exception:
            pass

    # 2. Project-level override
    project_settings = _find_project_settings(cwd)
    if project_settings:
        try:
            proj = json.loads(project_settings.read_text(encoding="utf-8"))
            # Deep-merge 'hooks' section; other keys are overwritten
            if "hooks" in proj and "hooks" in merged:
                for event_key, matchers in proj["hooks"].items():
                    merged["hooks"][event_key] = matchers
            else:
                merged.update(proj)
        except Exception:
            pass

    return merged


# ── Parser ─────────────────────────────────────────────────────────────────

def _parse_matchers(raw_list: list) -> list[HookMatcher]:
    """Parse a list of {matcher, hooks:[{type, command}]} dicts."""
    result = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        matcher = item.get("matcher", "")
        raw_hooks = item.get("hooks", [])
        commands = []
        for h in raw_hooks:
            if isinstance(h, dict) and h.get("type") == "command":
                commands.append(HookCommand(type="command", command=h.get("command", "")))
        result.append(HookMatcher(matcher=matcher, hooks=commands))
    return result


def parse_hooks_config(raw: dict) -> HooksConfig:
    """Parse the 'hooks' section of a settings dict into a HooksConfig."""
    hooks_raw = raw.get("hooks", {})
    if not isinstance(hooks_raw, dict):
        return HooksConfig()
    return HooksConfig(
        pre_tool_use=_parse_matchers(hooks_raw.get("PreToolUse", [])),
        post_tool_use=_parse_matchers(hooks_raw.get("PostToolUse", [])),
        stop=_parse_matchers(hooks_raw.get("Stop", [])),
        notification=_parse_matchers(hooks_raw.get("Notification", [])),
        pre_compact=_parse_matchers(hooks_raw.get("PreCompact", [])),
    )


# ── Cached entry point ─────────────────────────────────────────────────────

@lru_cache(maxsize=16)
def get_hooks_config(cwd: str) -> HooksConfig:
    """Return parsed HooksConfig for the given cwd (result is cached per cwd)."""
    raw = load_settings_json(cwd)
    return parse_hooks_config(raw)
