"""AG-UI protocol models.

Defines all AG-UI event types and request/response models based on the AG-UI specification.
Reference: https://docs.ag-ui.com/concepts/events
"""

import time
import uuid
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class Role(str, Enum):
    """Message role in AG-UI protocol."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(BaseModel):
    """AG-UI Message structure."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: Role
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


class Tool(BaseModel):
    """Tool definition for AG-UI."""

    name: str
    description: str
    parameters: dict[str, Any]


class RunAgentInput(BaseModel):
    """Input for running an agent via AG-UI protocol."""

    threadId: str
    runId: str
    messages: list[Message]
    state: Optional[dict[str, Any]] = None
    tools: Optional[list[Tool]] = None
    context: Optional[list[Any]] = None
    forwardedProps: Optional[dict[str, Any]] = None


# Event Types
class EventType(str, Enum):
    """All AG-UI event types."""

    # Run lifecycle events
    RUN_STARTED = "RUN_STARTED"
    RUN_FINISHED = "RUN_FINISHED"
    RUN_ERROR = "RUN_ERROR"

    # Text message events
    TEXT_MESSAGE_START = "TEXT_MESSAGE_START"
    TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT"
    TEXT_MESSAGE_END = "TEXT_MESSAGE_END"

    # Tool call events
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_ARGS = "TOOL_CALL_ARGS"
    TOOL_CALL_END = "TOOL_CALL_END"
    TOOL_CALL_RESULT = "TOOL_CALL_RESULT"

    # Step events
    STEP_STARTED = "STEP_STARTED"
    STEP_FINISHED = "STEP_FINISHED"

    # State events
    STATE_SNAPSHOT = "STATE_SNAPSHOT"
    STATE_DELTA = "STATE_DELTA"

    # Message events
    MESSAGES_SNAPSHOT = "MESSAGES_SNAPSHOT"

    # Custom events
    CUSTOM = "CUSTOM"


def _current_timestamp() -> int:
    """Return current timestamp in milliseconds."""
    return int(time.time() * 1000)


# Base Event
class BaseEvent(BaseModel):
    """Base class for all AG-UI events."""

    type: EventType
    timestamp: Optional[int] = Field(default_factory=_current_timestamp)


# Run Lifecycle Events
class RunStartedEvent(BaseEvent):
    """Signals that request processing has begun."""

    type: EventType = EventType.RUN_STARTED
    threadId: str
    runId: str


class RunFinishedEvent(BaseEvent):
    """Signals that the run is complete."""

    type: EventType = EventType.RUN_FINISHED
    threadId: str
    runId: str


class RunErrorEvent(BaseEvent):
    """Signals that an error occurred during processing."""

    type: EventType = EventType.RUN_ERROR
    message: str
    code: Optional[str] = None


# Text Message Events
class TextMessageStartEvent(BaseEvent):
    """Create a new text message block."""

    type: EventType = EventType.TEXT_MESSAGE_START
    messageId: str
    role: Role = Role.ASSISTANT


class TextMessageContentEvent(BaseEvent):
    """Append text content to the current message."""

    type: EventType = EventType.TEXT_MESSAGE_CONTENT
    messageId: str
    delta: str


class TextMessageEndEvent(BaseEvent):
    """Close the current text message block."""

    type: EventType = EventType.TEXT_MESSAGE_END
    messageId: str


# Tool Call Events
class ToolCallStartEvent(BaseEvent):
    """Start a tool call."""

    type: EventType = EventType.TOOL_CALL_START
    toolCallId: str
    toolCallName: str
    parentMessageId: Optional[str] = None


class ToolCallArgsEvent(BaseEvent):
    """Stream tool call arguments."""

    type: EventType = EventType.TOOL_CALL_ARGS
    toolCallId: str
    delta: str


class ToolCallEndEvent(BaseEvent):
    """End tool call argument streaming."""

    type: EventType = EventType.TOOL_CALL_END
    toolCallId: str


class ToolCallResultEvent(BaseEvent):
    """Tool call result."""

    type: EventType = EventType.TOOL_CALL_RESULT
    toolCallId: str
    result: str
    messageId: Optional[str] = None


# Step Events
class StepStartedEvent(BaseEvent):
    """Start a step in multi-step processing."""

    type: EventType = EventType.STEP_STARTED
    stepName: str
    stepId: Optional[str] = None


class StepFinishedEvent(BaseEvent):
    """Finish a step in multi-step processing."""

    type: EventType = EventType.STEP_FINISHED
    stepName: str
    stepId: Optional[str] = None


# State Events
class StateSnapshotEvent(BaseEvent):
    """Full state snapshot."""

    type: EventType = EventType.STATE_SNAPSHOT
    snapshot: dict[str, Any]


class StateDeltaEvent(BaseEvent):
    """Incremental state update."""

    type: EventType = EventType.STATE_DELTA
    delta: list[dict[str, Any]]


# Messages Snapshot Event
class MessagesSnapshotEvent(BaseEvent):
    """Full messages snapshot."""

    type: EventType = EventType.MESSAGES_SNAPSHOT
    messages: list[Message]


# Custom Event
class CustomEvent(BaseEvent):
    """Custom event for extension purposes."""

    type: EventType = EventType.CUSTOM
    name: str
    value: Any


# Union type for all events
AGUIEvent = Union[
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    StepStartedEvent,
    StepFinishedEvent,
    StateSnapshotEvent,
    StateDeltaEvent,
    MessagesSnapshotEvent,
    CustomEvent,
]
