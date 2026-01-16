"""A2A protocol module."""

from .models import (
    A2AEvent,
    A2AMessage,
    Artifact,
    MessageRole,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)
from .translator import A2AToAGUITranslator

# Note: A2AClient is not exported at package level to avoid circular imports.
# Import directly when needed: from orchestrator.a2a.client import A2AClient

__all__ = [
    "A2AEvent",
    "A2AMessage",
    "A2AToAGUITranslator",
    "Artifact",
    "MessageRole",
    "Task",
    "TaskArtifactUpdateEvent",
    "TaskState",
    "TaskStatus",
    "TaskStatusUpdateEvent",
    "TextPart",
]
