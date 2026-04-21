"""Dispatch hook events to configured shell commands.

Hook event functions:
  fire_pre_tool(tool_name, tool_input, session_id, cwd) -> HookDecision
  fire_post_tool(tool_name, tool_input, tool_response, session_id, cwd) -> None
  fire_stop(stop_reason, session_id, cwd) -> None
  fire_notification(message, session_id, cwd) -> None
  fire_pre_compact(messages_count, token_count, session_id, cwd) -> None
"""
from __future__ import annotations

from .loader import get_hooks_config
from .executor import run_hook
from .types import HookDecision, HookMatcher


# ── Matcher ────────────────────────────────────────────────────────────────

def _matches(matcher: str, tool_name: str) -> bool:
    """Return True if matcher applies to tool_name.

    Rules:
      - "" or "*" → matches everything
      - otherwise → exact match OR tool_name starts with matcher
    """
    if not matcher or matcher == "*":
        return True
    return tool_name == matcher or tool_name.startswith(matcher)


# ── Pre-tool hook ──────────────────────────────────────────────────────────

def fire_pre_tool(
    tool_name: str,
    tool_input: dict,
    session_id: str,
    cwd: str,
) -> HookDecision:
    """Run all matching PreToolUse hooks and return the resulting decision.

    Decision priority:
      - First 'block' response → immediately return block (abort tool)
      - Any 'approve' response → return approve (skip permission prompt)
      - No decision or 'ask' → return ask (normal permission flow)
    """
    cfg = get_hooks_config(cwd)
    stdin_data = {
        "session_id": session_id,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "cwd": cwd,
    }

    approved = False
    for hm in cfg.pre_tool_use:
        if not _matches(hm.matcher, tool_name):
            continue
        for hcmd in hm.hooks:
            result = run_hook(hcmd.command, stdin_data)
            if result is None:
                continue
            decision = result.get("decision", "ask")
            if decision == "block":
                return HookDecision(decision="block", reason=result.get("reason", ""))
            if decision == "approve":
                approved = True

    if approved:
        return HookDecision(decision="approve")
    return HookDecision(decision="ask")


# ── Post-tool hook ─────────────────────────────────────────────────────────

def fire_post_tool(
    tool_name: str,
    tool_input: dict,
    tool_response: dict,
    session_id: str,
    cwd: str,
) -> None:
    """Run all matching PostToolUse hooks (fire-and-forget, no decision)."""
    cfg = get_hooks_config(cwd)
    stdin_data = {
        "session_id": session_id,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_response": tool_response,
        "cwd": cwd,
    }
    for hm in cfg.post_tool_use:
        if not _matches(hm.matcher, tool_name):
            continue
        for hcmd in hm.hooks:
            run_hook(hcmd.command, stdin_data)


# ── Stop hook ──────────────────────────────────────────────────────────────

def fire_stop(stop_reason: str, session_id: str, cwd: str) -> None:
    """Run all Stop hooks after the agent turn completes."""
    cfg = get_hooks_config(cwd)
    stdin_data = {
        "session_id": session_id,
        "stop_reason": stop_reason,
        "cwd": cwd,
    }
    for hm in cfg.stop:
        for hcmd in hm.hooks:
            run_hook(hcmd.command, stdin_data)


# ── Notification hook ──────────────────────────────────────────────────────

def fire_notification(message: str, session_id: str, cwd: str) -> None:
    """Run all Notification hooks (e.g. for permission prompts)."""
    cfg = get_hooks_config(cwd)
    stdin_data = {
        "session_id": session_id,
        "message": message,
        "cwd": cwd,
    }
    for hm in cfg.notification:
        for hcmd in hm.hooks:
            run_hook(hcmd.command, stdin_data)


# ── Pre-compact hook ───────────────────────────────────────────────────────

def fire_pre_compact(
    messages_count: int,
    token_count: int,
    session_id: str,
    cwd: str,
) -> None:
    """Run all PreCompact hooks before context compaction."""
    cfg = get_hooks_config(cwd)
    stdin_data = {
        "session_id": session_id,
        "messages_count": messages_count,
        "token_count": token_count,
        "cwd": cwd,
    }
    for hm in cfg.pre_compact:
        for hcmd in hm.hooks:
            run_hook(hcmd.command, stdin_data)
