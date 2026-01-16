"""A2A protocol models.

Defines A2A protocol types for communication with A2A agents.
Reference: https://a2a-protocol.org/latest/specification/
"""

import uuid
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class TaskState(str, Enum):
    """A2A task states."""

    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class MessageRole(str, Enum):
    """A2A message role."""

    USER = "user"
    AGENT = "agent"


# Message Parts
class TextPart(BaseModel):
    """Text content part."""

    type: str = "text"
    text: str


class FilePart(BaseModel):
    """File content part."""

    type: str = "file"
    mimeType: str
    data: Optional[str] = None
    uri: Optional[str] = None


class DataPart(BaseModel):
    """Structured data part."""

    type: str = "data"
    data: dict[str, Any]


Part = Union[TextPart, FilePart, DataPart]


class A2AMessage(BaseModel):
    """A2A protocol message."""

    role: MessageRole
    parts: list[Part]
    messageId: str = Field(default_factory=lambda: str(uuid.uuid4()))


class TaskStatus(BaseModel):
    """A2A task status."""

    state: TaskState
    message: Optional[A2AMessage] = None
    timestamp: Optional[str] = None


class Artifact(BaseModel):
    """A2A artifact output."""

    artifactId: str
    name: Optional[str] = None
    parts: list[Part]
    index: int = 0
    append: bool = False
    lastChunk: bool = False
    metadata: Optional[dict[str, Any]] = None


class Task(BaseModel):
    """A2A Task object."""

    taskId: str
    contextId: str
    status: TaskStatus
    artifacts: Optional[list[Artifact]] = None
    history: Optional[list[A2AMessage]] = None
    metadata: Optional[dict[str, Any]] = None


class TaskStatusUpdateEvent(BaseModel):
    """A2A status update event during streaming."""

    kind: str = "status-update"
    taskId: str
    contextId: str
    status: TaskStatus
    final: bool = False


class TaskArtifactUpdateEvent(BaseModel):
    """A2A artifact update event during streaming."""

    kind: str = "artifact-update"
    taskId: str
    contextId: str
    artifact: Artifact


# Union of all A2A event types
A2AEvent = Union[Task, TaskStatusUpdateEvent, TaskArtifactUpdateEvent]


class SendMessageRequest(BaseModel):
    """Request to send message to A2A agent (JSON-RPC 2.0)."""

    jsonrpc: str = "2.0"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    method: str = "message/send"
    params: dict[str, Any]


class SendStreamingMessageRequest(BaseModel):
    """Request to send streaming message to A2A agent (JSON-RPC 2.0)."""

    jsonrpc: str = "2.0"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    method: str = "message/stream"
    params: dict[str, Any]
