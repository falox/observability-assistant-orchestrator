"""A2A client for communicating with A2A agents.

This module provides an async client for the A2A (Agent-to-Agent) protocol,
supporting streaming message communication with A2A-compatible agents.
"""

import json
import logging
import uuid
from typing import Any, AsyncIterator, Optional

import httpx

from ..agui.models import Message as AGUIMessage
from ..utils.errors import A2AConnectionError, A2AProtocolError, A2ATimeoutError
from .models import (
    A2AEvent,
    A2AMessage,
    Artifact,
    MessageRole,
    Part,
    SendStreamingMessageRequest,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)

logger = logging.getLogger(__name__)


class A2AClient:
    """Client for communicating with A2A agents.

    This client implements the A2A protocol for sending messages to agents
    and receiving streaming responses via Server-Sent Events.

    Attributes:
        base_url: Base URL of the A2A agent.
        timeout: Request timeout in seconds.
    """

    def __init__(self, base_url: str, timeout: int = 300, path: str = "/"):
        """Initialize A2A client.

        Args:
            base_url: Base URL of the A2A agent (e.g., "http://localhost:9999").
            timeout: Request timeout in seconds. Default is 300 (5 minutes).
            path: Path for the A2A endpoint. Default is "/".
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.path = path.rstrip("/") if path != "/" else ""
        self._agent_card: Optional[dict[str, Any]] = None

    async def get_agent_card(self) -> dict[str, Any]:
        """Fetch agent card from /.well-known/agent.json.

        The agent card contains metadata about the agent's capabilities,
        supported skills, and communication preferences.

        Returns:
            Agent card as dictionary.

        Raises:
            A2AConnectionError: If connection to agent fails.
            A2AProtocolError: If agent card is invalid.
        """
        if self._agent_card is None:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/.well-known/agent.json",
                        timeout=30,
                    )
                    response.raise_for_status()
                    self._agent_card = response.json()
            except httpx.ConnectError as e:
                raise A2AConnectionError(
                    f"Failed to connect to A2A agent: {e}",
                    url=self.base_url,
                ) from e
            except httpx.HTTPStatusError as e:
                raise A2AProtocolError(
                    f"A2A agent returned error: {e.response.status_code}"
                ) from e
        return self._agent_card

    def _convert_agui_messages_to_a2a(
        self, messages: list[AGUIMessage]
    ) -> list[A2AMessage]:
        """Convert AG-UI messages to A2A format.

        Args:
            messages: List of AG-UI messages.

        Returns:
            List of A2A messages with converted roles and content.
        """
        a2a_messages = []
        for msg in messages:
            # Map AG-UI roles to A2A roles
            role = MessageRole.USER if msg.role.value == "user" else MessageRole.AGENT
            a2a_messages.append(
                A2AMessage(
                    role=role,
                    parts=[TextPart(text=msg.content)],
                    messageId=msg.id,
                )
            )
        return a2a_messages

    async def send_message_streaming(
        self,
        context_id: str,
        messages: list[AGUIMessage],
        task_id: Optional[str] = None,
    ) -> AsyncIterator[A2AEvent]:
        """Send message to A2A agent and stream response events.

        Args:
            context_id: Context/thread ID for conversation continuity.
            messages: List of AG-UI messages to send.
            task_id: Optional existing task ID for continuing a task.

        Yields:
            A2A events (Task, TaskStatusUpdateEvent, TaskArtifactUpdateEvent).

        Raises:
            A2AConnectionError: If connection to agent fails.
            A2ATimeoutError: If request times out.
            A2AProtocolError: If protocol communication fails.
        """
        # Convert messages to A2A format
        a2a_messages = self._convert_agui_messages_to_a2a(messages)

        # Get the last user message (the one to send)
        last_message = a2a_messages[-1] if a2a_messages else None
        if not last_message:
            logger.warning("No messages to send to A2A agent")
            return

        # Generate task ID if not provided
        if task_id is None:
            task_id = str(uuid.uuid4())

        # Build JSON-RPC request
        request_data = SendStreamingMessageRequest(
            method="message/stream",
            params={
                "message": last_message.model_dump(),
                "contextId": context_id,
                "taskId": task_id,
            },
        )

        logger.info(
            "[A2A] Sending request to %s: contextId=%s taskId=%s",
            self.base_url,
            context_id,
            task_id,
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}{self.path}",
                    json=request_data.model_dump(),
                    headers={
                        "Accept": "text/event-stream",
                        "Content-Type": "application/json",
                    },
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data = line[5:].strip()
                            if data and data != "[DONE]":
                                try:
                                    parsed = json.loads(data)
                                    event = self._parse_event(parsed)
                                    if event:
                                        yield event
                                except json.JSONDecodeError as e:
                                    logger.warning(
                                        "[A2A] Failed to parse event: %s - %s",
                                        data[:100],
                                        e,
                                    )

        except httpx.ConnectError as e:
            raise A2AConnectionError(
                f"Failed to connect to A2A agent: {e}",
                url=self.base_url,
            ) from e
        except httpx.TimeoutException as e:
            raise A2ATimeoutError(
                f"A2A agent request timed out after {self.timeout}s",
                timeout=self.timeout,
            ) from e
        except httpx.HTTPStatusError as e:
            raise A2AProtocolError(
                f"A2A agent returned error: {e.response.status_code}"
            ) from e

    def _parse_event(self, data: dict[str, Any]) -> Optional[A2AEvent]:
        """Parse raw event data into typed A2A event.

        Args:
            data: Raw event dictionary from SSE stream.

        Returns:
            Typed A2A event or None if unrecognized.
        """
        # Check for result field (JSON-RPC response wrapper)
        if "result" in data:
            result = data["result"]
            return self._parse_event_object(result)
        return self._parse_event_object(data)

    def _parse_event_object(self, obj: dict[str, Any]) -> Optional[A2AEvent]:
        """Parse event object based on its kind or structure.

        Args:
            obj: Event object dictionary.

        Returns:
            Typed A2A event or None if unrecognized.
        """
        kind = obj.get("kind")

        if kind == "status-update":
            return self._parse_status_update(obj)
        elif kind == "artifact-update":
            return self._parse_artifact_update(obj)
        elif "taskId" in obj and "status" in obj:
            # Task object (initial response)
            return self._parse_task(obj)

        logger.debug("[A2A] Unrecognized event: %s", obj)
        return None

    def _parse_status_update(self, obj: dict[str, Any]) -> TaskStatusUpdateEvent:
        """Parse TaskStatusUpdateEvent from dict."""
        status_dict = obj.get("status", {})
        status = TaskStatus(
            state=TaskState(status_dict.get("state", "working")),
            message=self._parse_message(status_dict.get("message")),
            timestamp=status_dict.get("timestamp"),
        )
        return TaskStatusUpdateEvent(
            kind="status-update",
            taskId=obj.get("taskId", ""),
            contextId=obj.get("contextId", ""),
            status=status,
            final=obj.get("final", False),
        )

    def _parse_artifact_update(self, obj: dict[str, Any]) -> TaskArtifactUpdateEvent:
        """Parse TaskArtifactUpdateEvent from dict."""
        artifact_dict = obj.get("artifact", {})
        artifact = Artifact(
            artifactId=artifact_dict.get("artifactId", str(uuid.uuid4())),
            name=artifact_dict.get("name"),
            parts=self._parse_parts(artifact_dict.get("parts", [])),
            index=artifact_dict.get("index", 0),
            append=artifact_dict.get("append", False),
            lastChunk=artifact_dict.get("lastChunk", False),
            metadata=artifact_dict.get("metadata"),
        )
        return TaskArtifactUpdateEvent(
            kind="artifact-update",
            taskId=obj.get("taskId", ""),
            contextId=obj.get("contextId", ""),
            artifact=artifact,
        )

    def _parse_task(self, obj: dict[str, Any]) -> Task:
        """Parse Task from dict."""
        status_dict = obj.get("status", {})
        status = TaskStatus(
            state=TaskState(status_dict.get("state", "submitted")),
            message=self._parse_message(status_dict.get("message")),
            timestamp=status_dict.get("timestamp"),
        )
        return Task(
            taskId=obj.get("taskId", ""),
            contextId=obj.get("contextId", ""),
            status=status,
            artifacts=None,
            history=None,
            metadata=obj.get("metadata"),
        )

    def _parse_message(self, msg_dict: Optional[dict[str, Any]]) -> Optional[A2AMessage]:
        """Parse A2AMessage from dict."""
        if not msg_dict:
            return None
        return A2AMessage(
            role=MessageRole(msg_dict.get("role", "agent")),
            parts=self._parse_parts(msg_dict.get("parts", [])),
            messageId=msg_dict.get("messageId", str(uuid.uuid4())),
        )

    def _parse_parts(self, parts_list: list[Any]) -> list[Part]:
        """Parse message parts from list of dicts.

        Args:
            parts_list: List of part dictionaries.

        Returns:
            List of typed Part objects.
        """
        parts: list[Part] = []
        for p in parts_list:
            if isinstance(p, dict):
                part_type = p.get("type", "text")
                if part_type == "text":
                    parts.append(TextPart(text=p.get("text", "")))
                # Future: Add support for FilePart, DataPart
            elif hasattr(p, "root"):
                # Handle a2a-sdk Part wrapper objects
                actual = p.root if hasattr(p, "root") else p
                if hasattr(actual, "text"):
                    parts.append(TextPart(text=actual.text))
        return parts
