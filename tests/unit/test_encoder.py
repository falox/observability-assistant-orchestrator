"""Unit tests for SSE encoder."""

import json

from orchestrator.agui.encoder import SSEEncoder
from orchestrator.agui.models import (
    Role,
    RunErrorEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageStartEvent,
)


class TestSSEEncoder:
    """Tests for SSEEncoder."""

    def setup_method(self):
        """Set up test fixtures."""
        self.encoder = SSEEncoder()

    def test_content_type(self):
        """Test content type is correct."""
        assert SSEEncoder.CONTENT_TYPE == "text/event-stream"
        assert self.encoder.get_content_type() == "text/event-stream"

    def test_encode_event(self):
        """Test encoding a simple event."""
        event = RunStartedEvent(
            threadId="t-1",
            runId="r-1",
            timestamp=1000,
        )

        result = self.encoder.encode(event)

        assert result.startswith("data: ")
        assert result.endswith("\n\n")

        # Parse the JSON part
        json_str = result[6:-2]  # Remove "data: " and "\n\n"
        data = json.loads(json_str)
        assert data["type"] == "RUN_STARTED"
        assert data["threadId"] == "t-1"
        assert data["runId"] == "r-1"

    def test_encode_excludes_none(self):
        """Test that None values are excluded from output."""
        event = RunErrorEvent(
            message="Error occurred",
            timestamp=1000,
            # code is None
        )

        result = self.encoder.encode(event)
        json_str = result[6:-2]
        data = json.loads(json_str)

        assert "code" not in data

    def test_encode_error(self):
        """Test encoding an error message."""
        result = self.encoder.encode_error("Something went wrong", "ERR_001")

        json_str = result[6:-2]
        data = json.loads(json_str)

        assert data["type"] == "RUN_ERROR"
        assert data["message"] == "Something went wrong"
        assert data["code"] == "ERR_001"

    def test_encode_error_default_code(self):
        """Test encoding error with default code."""
        result = self.encoder.encode_error("Failed")

        json_str = result[6:-2]
        data = json.loads(json_str)

        assert data["code"] == "INTERNAL_ERROR"

    def test_encode_done(self):
        """Test encoding done signal."""
        result = self.encoder.encode_done()

        assert result == "data: [DONE]\n\n"

    def test_encode_text_message_events(self):
        """Test encoding text message events."""
        start = TextMessageStartEvent(
            messageId="msg-1",
            role=Role.ASSISTANT,
            timestamp=1000,
        )
        content = TextMessageContentEvent(
            messageId="msg-1",
            delta="Hello world",
            timestamp=1001,
        )

        start_result = self.encoder.encode(start)
        content_result = self.encoder.encode(content)

        start_data = json.loads(start_result[6:-2])
        content_data = json.loads(content_result[6:-2])

        assert start_data["type"] == "TEXT_MESSAGE_START"
        assert start_data["messageId"] == "msg-1"
        assert start_data["role"] == "assistant"

        assert content_data["type"] == "TEXT_MESSAGE_CONTENT"
        assert content_data["delta"] == "Hello world"

    def test_encode_special_characters(self):
        """Test encoding content with special characters."""
        event = TextMessageContentEvent(
            messageId="msg-1",
            delta='Line 1\nLine 2\t"quoted"',
            timestamp=1000,
        )

        result = self.encoder.encode(event)

        # Should be valid JSON
        json_str = result[6:-2]
        data = json.loads(json_str)
        assert data["delta"] == 'Line 1\nLine 2\t"quoted"'

    def test_encode_unicode(self):
        """Test encoding unicode content."""
        event = TextMessageContentEvent(
            messageId="msg-1",
            delta="Hello 世界 🌍",
            timestamp=1000,
        )

        result = self.encoder.encode(event)

        json_str = result[6:-2]
        data = json.loads(json_str)
        assert "世界" in data["delta"]
        assert "🌍" in data["delta"]

    def test_encode_empty_delta(self):
        """Test encoding empty delta."""
        event = TextMessageContentEvent(
            messageId="msg-1",
            delta="",
            timestamp=1000,
        )

        result = self.encoder.encode(event)
        data = json.loads(result[6:-2])
        assert data["delta"] == ""

    def test_multiple_events_stream(self):
        """Test encoding a stream of events."""
        events = [
            RunStartedEvent(threadId="t-1", runId="r-1", timestamp=1000),
            TextMessageStartEvent(messageId="msg-1", timestamp=1001),
            TextMessageContentEvent(messageId="msg-1", delta="Hi", timestamp=1002),
        ]

        stream = ""
        for event in events:
            stream += self.encoder.encode(event)
        stream += self.encoder.encode_done()

        # Parse individual events
        lines = stream.strip().split("\n\n")
        assert len(lines) == 4  # 3 events + done

        # Verify each line is properly formatted
        for line in lines[:-1]:  # Exclude [DONE]
            assert line.startswith("data: ")
            json_str = line[6:]
            json.loads(json_str)  # Should not raise

        assert lines[-1] == "data: [DONE]"
