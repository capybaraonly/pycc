"""Dataclasses for the hooks system."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class HookCommand:
    """A single hook action — currently only 'command' type is supported."""
    type: str       # "command"
    command: str


@dataclass
class HookMatcher:
    """A matcher + list of hook commands for one hook event entry."""
    matcher: str                       # "" or "*" = match all, else tool name prefix
    hooks: list[HookCommand] = field(default_factory=list)


@dataclass
class HooksConfig:
    """Parsed hooks configuration from settings.json."""
    pre_tool_use:  list[HookMatcher] = field(default_factory=list)
    post_tool_use: list[HookMatcher] = field(default_factory=list)
    stop:          list[HookMatcher] = field(default_factory=list)
    notification:  list[HookMatcher] = field(default_factory=list)
    pre_compact:   list[HookMatcher] = field(default_factory=list)


@dataclass
class HookDecision:
    """Decision returned by a pre-tool hook."""
    decision: Literal["block", "approve", "ask"] = "ask"
    reason: str = ""
