"""SSE encoder for AG-UI events.

This module provides encoding of AG-UI events into Server-Sent Events (SSE) format
for streaming responses to clients.
"""

from .models import AGUIEvent, EventType, RunErrorEvent


class SSEEncoder:
    """Encodes AG-UI events as Server-Sent Events.

    SSE format: Each event is sent as 'data: {json}\\n\\n'
    The stream terminates with 'data: [DONE]\\n\\n'
    """

    CONTENT_TYPE = "text/event-stream"

    def encode(self, event: AGUIEvent) -> str:
        """Encode an event as SSE format.

        Args:
            event: The AG-UI event to encode.

        Returns:
            SSE formatted string with 'data: {json}\\n\\n' format.
        """
        data = event.model_dump_json(exclude_none=True)
        return f"data: {data}\n\n"

    def encode_error(self, message: str, code: str = "INTERNAL_ERROR") -> str:
        """Encode an error event.

        Args:
            message: Error message to include in the event.
            code: Error code for categorization.

        Returns:
            SSE formatted error event.
        """
        error_event = RunErrorEvent(
            type=EventType.RUN_ERROR,
            message=message,
            code=code,
        )
        return self.encode(error_event)

    def encode_done(self) -> str:
        """Encode the stream termination signal.

        Returns:
            SSE formatted done signal.
        """
        return "data: [DONE]\n\n"

    @staticmethod
    def get_content_type() -> str:
        """Return SSE content type.

        Returns:
            The MIME type for SSE (text/event-stream).
        """
        return SSEEncoder.CONTENT_TYPE
