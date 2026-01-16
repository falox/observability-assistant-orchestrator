"""Unit tests for AG-UI models."""

import json
from unittest.mock import patch

from orchestrator.agui.models import (
    CustomEvent,
    EventType,
    Message,
    MessagesSnapshotEvent,
    Role,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StateDeltaEvent,
    StateSnapshotEvent,
    StepFinishedEvent,
    StepStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    Tool,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)


class TestRole:
    """Tests for Role enum."""

    def test_role_values(self):
        """Test that all role values are correct."""
        assert Role.USER.value == "user"
        assert Role.ASSISTANT.value == "assistant"
        assert Role.SYSTEM.value == "system"
        assert Role.TOOL.value == "tool"


class TestMessage:
    """Tests for Message model."""

    def test_message_with_defaults(self):
        """Test message creation with default ID."""
        msg = Message(role=Role.USER, content="Hello")
        assert msg.role == Role.USER
        assert msg.content == "Hello"
        assert msg.id is not None
        assert len(msg.id) == 36  # UUID format

    def test_message_with_custom_id(self):
        """Test message creation with custom ID."""
        msg = Message(id="custom-id", role=Role.ASSISTANT, content="Hi there")
        assert msg.id == "custom-id"

    def test_message_with_tool_call_id(self):
        """Test message with tool call reference."""
        msg = Message(
            role=Role.TOOL,
            content="Result",
            tool_call_id="tool-123",
            name="get_weather",
        )
        assert msg.tool_call_id == "tool-123"
        assert msg.name == "get_weather"

    def test_message_serialization(self):
        """Test message JSON serialization."""
        msg = Message(id="msg-1", role=Role.USER, content="Test")
        data = json.loads(msg.model_dump_json())
        assert data["id"] == "msg-1"
        assert data["role"] == "user"
        assert data["content"] == "Test"


class TestTool:
    """Tests for Tool model."""

    def test_tool_creation(self):
        """Test tool definition creation."""
        tool = Tool(
            name="get_weather",
            description="Get weather for a location",
            parameters={
                "type": "object",
                "properties": {"location": {"type": "string"}},
            },
        )
        assert tool.name == "get_weather"
        assert "location" in tool.parameters["properties"]


class TestRunAgentInput:
    """Tests for RunAgentInput model."""

    def test_minimal_input(self):
        """Test minimal required fields."""
        input_data = RunAgentInput(
            threadId="thread-1",
            runId="run-1",
            messages=[Message(role=Role.USER, content="Hello")],
        )
        assert input_data.threadId == "thread-1"
        assert input_data.runId == "run-1"
        assert len(input_data.messages) == 1
        assert input_data.state is None
        assert input_data.tools is None

    def test_full_input(self):
        """Test with all optional fields."""
        input_data = RunAgentInput(
            threadId="thread-1",
            runId="run-1",
            messages=[Message(role=Role.USER, content="Hello")],
            state={"key": "value"},
            tools=[
                Tool(name="test", description="desc", parameters={})
            ],
            context=[{"type": "document", "content": "..."}],
            forwardedProps={"custom": True},
        )
        assert input_data.state == {"key": "value"}
        assert len(input_data.tools) == 1
        assert input_data.forwardedProps["custom"] is True


class TestEventType:
    """Tests for EventType enum."""

    def test_all_event_types_exist(self):
        """Test that all expected event types are defined."""
        expected = [
            "RUN_STARTED", "RUN_FINISHED", "RUN_ERROR",
            "TEXT_MESSAGE_START", "TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END",
            "TOOL_CALL_START", "TOOL_CALL_ARGS", "TOOL_CALL_END", "TOOL_CALL_RESULT",
            "STEP_STARTED", "STEP_FINISHED",
            "STATE_SNAPSHOT", "STATE_DELTA",
            "MESSAGES_SNAPSHOT", "CUSTOM",
        ]
        for event_type in expected:
            assert hasattr(EventType, event_type)


class TestRunLifecycleEvents:
    """Tests for run lifecycle events."""

    @patch("orchestrator.agui.models.time.time", return_value=1234567890.123)
    def test_run_started_event(self, mock_time):
        """Test RunStartedEvent creation."""
        event = RunStartedEvent(threadId="t-1", runId="r-1")
        assert event.type == EventType.RUN_STARTED
        assert event.threadId == "t-1"
        assert event.runId == "r-1"
        assert event.timestamp == 1234567890123

    def test_run_finished_event(self):
        """Test RunFinishedEvent creation."""
        event = RunFinishedEvent(threadId="t-1", runId="r-1", timestamp=12345)
        assert event.type == EventType.RUN_FINISHED
        assert event.timestamp == 12345

    def test_run_error_event(self):
        """Test RunErrorEvent creation."""
        event = RunErrorEvent(message="Something failed", code="ERR_001")
        assert event.type == EventType.RUN_ERROR
        assert event.message == "Something failed"
        assert event.code == "ERR_001"

    def test_run_error_event_without_code(self):
        """Test RunErrorEvent without error code."""
        event = RunErrorEvent(message="Failed")
        assert event.code is None


class TestTextMessageEvents:
    """Tests for text message events."""

    def test_text_message_start(self):
        """Test TextMessageStartEvent creation."""
        event = TextMessageStartEvent(messageId="msg-1", timestamp=1000)
        assert event.type == EventType.TEXT_MESSAGE_START
        assert event.messageId == "msg-1"
        assert event.role == Role.ASSISTANT  # Default

    def test_text_message_start_custom_role(self):
        """Test TextMessageStartEvent with custom role."""
        event = TextMessageStartEvent(
            messageId="msg-1",
            role=Role.USER,
            timestamp=1000,
        )
        assert event.role == Role.USER

    def test_text_message_content(self):
        """Test TextMessageContentEvent creation."""
        event = TextMessageContentEvent(
            messageId="msg-1",
            delta="Hello ",
            timestamp=1000,
        )
        assert event.type == EventType.TEXT_MESSAGE_CONTENT
        assert event.delta == "Hello "

    def test_text_message_end(self):
        """Test TextMessageEndEvent creation."""
        event = TextMessageEndEvent(messageId="msg-1", timestamp=1000)
        assert event.type == EventType.TEXT_MESSAGE_END


class TestToolCallEvents:
    """Tests for tool call events."""

    def test_tool_call_start(self):
        """Test ToolCallStartEvent creation."""
        event = ToolCallStartEvent(
            toolCallId="tc-1",
            toolCallName="get_weather",
            parentMessageId="msg-1",
            timestamp=1000,
        )
        assert event.type == EventType.TOOL_CALL_START
        assert event.toolCallId == "tc-1"
        assert event.toolCallName == "get_weather"
        assert event.parentMessageId == "msg-1"

    def test_tool_call_args(self):
        """Test ToolCallArgsEvent creation."""
        event = ToolCallArgsEvent(
            toolCallId="tc-1",
            delta='{"location":',
            timestamp=1000,
        )
        assert event.type == EventType.TOOL_CALL_ARGS
        assert event.delta == '{"location":'

    def test_tool_call_end(self):
        """Test ToolCallEndEvent creation."""
        event = ToolCallEndEvent(toolCallId="tc-1", timestamp=1000)
        assert event.type == EventType.TOOL_CALL_END

    def test_tool_call_result(self):
        """Test ToolCallResultEvent creation."""
        event = ToolCallResultEvent(
            toolCallId="tc-1",
            result='{"temp": 72}',
            timestamp=1000,
        )
        assert event.type == EventType.TOOL_CALL_RESULT
        assert event.result == '{"temp": 72}'


class TestStepEvents:
    """Tests for step events."""

    def test_step_started(self):
        """Test StepStartedEvent creation."""
        event = StepStartedEvent(stepName="processing", timestamp=1000)
        assert event.type == EventType.STEP_STARTED
        assert event.stepName == "processing"
        assert event.stepId is None

    def test_step_started_with_id(self):
        """Test StepStartedEvent with step ID."""
        event = StepStartedEvent(
            stepName="processing",
            stepId="step-1",
            timestamp=1000,
        )
        assert event.stepId == "step-1"

    def test_step_finished(self):
        """Test StepFinishedEvent creation."""
        event = StepFinishedEvent(stepName="processing", timestamp=1000)
        assert event.type == EventType.STEP_FINISHED


class TestStateEvents:
    """Tests for state events."""

    def test_state_snapshot(self):
        """Test StateSnapshotEvent creation."""
        event = StateSnapshotEvent(
            snapshot={"count": 5, "items": ["a", "b"]},
            timestamp=1000,
        )
        assert event.type == EventType.STATE_SNAPSHOT
        assert event.snapshot["count"] == 5

    def test_state_delta(self):
        """Test StateDeltaEvent creation."""
        event = StateDeltaEvent(
            delta=[{"op": "add", "path": "/count", "value": 1}],
            timestamp=1000,
        )
        assert event.type == EventType.STATE_DELTA
        assert len(event.delta) == 1


class TestMessagesSnapshotEvent:
    """Tests for MessagesSnapshotEvent."""

    def test_messages_snapshot(self):
        """Test MessagesSnapshotEvent creation."""
        messages = [
            Message(role=Role.USER, content="Hello"),
            Message(role=Role.ASSISTANT, content="Hi!"),
        ]
        event = MessagesSnapshotEvent(messages=messages, timestamp=1000)
        assert event.type == EventType.MESSAGES_SNAPSHOT
        assert len(event.messages) == 2


class TestCustomEvent:
    """Tests for CustomEvent."""

    def test_custom_event(self):
        """Test CustomEvent creation."""
        event = CustomEvent(
            name="custom_action",
            value={"key": "value"},
            timestamp=1000,
        )
        assert event.type == EventType.CUSTOM
        assert event.name == "custom_action"
        assert event.value["key"] == "value"


class TestEventSerialization:
    """Tests for event JSON serialization."""

    def test_event_excludes_none(self):
        """Test that None values are excluded from JSON."""
        event = RunErrorEvent(message="Error", timestamp=1000)
        data = json.loads(event.model_dump_json(exclude_none=True))
        assert "code" not in data  # None value excluded

    def test_event_includes_all_fields(self):
        """Test that all fields are included when set."""
        event = RunStartedEvent(
            threadId="t-1",
            runId="r-1",
            timestamp=1000,
        )
        data = json.loads(event.model_dump_json())
        assert "type" in data
        assert "threadId" in data
        assert "runId" in data
        assert "timestamp" in data
