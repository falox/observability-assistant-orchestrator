"""Translator from A2A events to AG-UI events."""

import logging
import time
import uuid
from typing import Optional

from ..agui.models import (
    AGUIEvent,
    Role,
    RunErrorEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)
from .models import (
    A2AEvent,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
    TextPart,
)

logger = logging.getLogger(__name__)


class A2AToAGUITranslator:
    """Translates A2A events to AG-UI events."""

    def __init__(self):
        """Initialize translator state."""
        self._current_message_id: Optional[str] = None
        self._message_started: bool = False

    def reset(self) -> None:
        """Reset translator state for a new run."""
        self._current_message_id = None
        self._message_started = False

    def translate(self, a2a_event: A2AEvent, run_id: str) -> list[AGUIEvent]:
        """Translate an A2A event to one or more AG-UI events.

        Args:
            a2a_event: The A2A event to translate.
            run_id: The current run ID.

        Returns:
            List of AG-UI events.
        """
        timestamp = int(time.time() * 1000)

        if isinstance(a2a_event, Task):
            return self._translate_task(a2a_event, run_id, timestamp)
        elif isinstance(a2a_event, TaskStatusUpdateEvent):
            return self._translate_status_update(a2a_event, run_id, timestamp)
        elif isinstance(a2a_event, TaskArtifactUpdateEvent):
            return self._translate_artifact_update(a2a_event, run_id, timestamp)

        logger.warning("[Translator] Unknown A2A event type: %s", type(a2a_event))
        return []

    def _translate_task(
        self, task: Task, run_id: str, timestamp: int
    ) -> list[AGUIEvent]:
        """Translate Task object to AG-UI events."""
        events: list[AGUIEvent] = []

        if task.status.state == TaskState.COMPLETED:
            # End any open message
            if self._message_started and self._current_message_id:
                events.append(
                    TextMessageEndEvent(
                        messageId=self._current_message_id,
                        timestamp=timestamp,
                    )
                )
                self._message_started = False

        elif task.status.state == TaskState.FAILED:
            msg = "Task failed"
            if task.status.message and task.status.message.parts:
                for part in task.status.message.parts:
                    if isinstance(part, TextPart):
                        msg = part.text
                        break
            events.append(
                RunErrorEvent(
                    message=msg,
                    code="TASK_FAILED",
                    timestamp=timestamp,
                )
            )

        return events

    def _translate_status_update(
        self, event: TaskStatusUpdateEvent, run_id: str, timestamp: int
    ) -> list[AGUIEvent]:
        """Translate TaskStatusUpdateEvent to AG-UI events."""
        events: list[AGUIEvent] = []

        # Extract text from status message if present
        if event.status.message and event.status.message.parts:
            for part in event.status.message.parts:
                if isinstance(part, TextPart) and part.text:
                    # Start new message if needed
                    if not self._message_started:
                        self._current_message_id = str(uuid.uuid4())
                        events.append(
                            TextMessageStartEvent(
                                messageId=self._current_message_id,
                                role=Role.ASSISTANT,
                                timestamp=timestamp,
                            )
                        )
                        self._message_started = True

                    # Stream content (message_id is guaranteed to be set here)
                    assert self._current_message_id is not None
                    events.append(
                        TextMessageContentEvent(
                            messageId=self._current_message_id,
                            delta=part.text,
                            timestamp=timestamp,
                        )
                    )

        # Handle terminal states
        if event.final:
            if self._message_started and self._current_message_id:
                events.append(
                    TextMessageEndEvent(
                        messageId=self._current_message_id,
                        timestamp=timestamp,
                    )
                )
                self._message_started = False

        return events

    def _translate_artifact_update(
        self, event: TaskArtifactUpdateEvent, run_id: str, timestamp: int
    ) -> list[AGUIEvent]:
        """Translate TaskArtifactUpdateEvent to AG-UI events."""
        events: list[AGUIEvent] = []

        # Extract text from artifact parts
        for part in event.artifact.parts:
            if isinstance(part, TextPart) and part.text:
                # Start new message if needed
                if not self._message_started:
                    self._current_message_id = str(uuid.uuid4())
                    events.append(
                        TextMessageStartEvent(
                            messageId=self._current_message_id,
                            role=Role.ASSISTANT,
                            timestamp=timestamp,
                        )
                    )
                    self._message_started = True

                # Stream artifact content (message_id is guaranteed to be set here)
                assert self._current_message_id is not None
                events.append(
                    TextMessageContentEvent(
                        messageId=self._current_message_id,
                        delta=part.text,
                        timestamp=timestamp,
                    )
                )

        # End message if this is the last chunk
        if event.artifact.lastChunk and self._message_started and self._current_message_id:
            events.append(
                TextMessageEndEvent(
                    messageId=self._current_message_id,
                    timestamp=timestamp,
                )
            )
            self._message_started = False

        return events

    def finalize(self, timestamp: Optional[int] = None) -> list[AGUIEvent]:
        """Finalize any open events at the end of a run.

        Args:
            timestamp: Optional timestamp to use.

        Returns:
            List of finalizing AG-UI events.
        """
        if timestamp is None:
            timestamp = int(time.time() * 1000)

        events: list[AGUIEvent] = []

        # Close any open message
        if self._message_started and self._current_message_id:
            events.append(
                TextMessageEndEvent(
                    messageId=self._current_message_id,
                    timestamp=timestamp,
                )
            )
            self._message_started = False

        return events
