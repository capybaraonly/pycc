"""Hooks system: run external commands in response to agent lifecycle events."""
from .dispatcher import (  # noqa: F401
    fire_pre_tool,
    fire_post_tool,
    fire_stop,
    fire_notification,
    fire_pre_compact,
)
