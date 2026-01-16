"""Unit tests for A2A models."""

import json

from orchestrator.a2a.models import (
    A2AMessage,
    Artifact,
    DataPart,
    FilePart,
    MessageRole,
    SendMessageRequest,
    SendStreamingMessageRequest,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)


class TestTaskState:
    """Tests for TaskState enum."""

    def test_all_states_exist(self):
        """Test that all expected states are defined."""
        expected = [
            "submitted", "working", "input-required",
            "completed", "failed", "cancelled", "rejected",
        ]
        for state in expected:
            assert TaskState(state) is not None

    def test_state_values(self):
        """Test state values match protocol."""
        assert TaskState.SUBMITTED.value == "submitted"
        assert TaskState.WORKING.value == "working"
        assert TaskState.COMPLETED.value == "completed"
        assert TaskState.FAILED.value == "failed"


class TestMessageRole:
    """Tests for MessageRole enum."""

    def test_role_values(self):
        """Test role values."""
        assert MessageRole.USER.value == "user"
        assert MessageRole.AGENT.value == "agent"


class TestTextPart:
    """Tests for TextPart model."""

    def test_text_part_creation(self):
        """Test TextPart creation."""
        part = TextPart(text="Hello world")
        assert part.type == "text"
        assert part.text == "Hello world"

    def test_text_part_serialization(self):
        """Test TextPart JSON serialization."""
        part = TextPart(text="Test")
        data = json.loads(part.model_dump_json())
        assert data["type"] == "text"
        assert data["text"] == "Test"


class TestFilePart:
    """Tests for FilePart model."""

    def test_file_part_with_data(self):
        """Test FilePart with base64 data."""
        part = FilePart(mimeType="image/png", data="base64encodeddata")
        assert part.type == "file"
        assert part.mimeType == "image/png"
        assert part.data == "base64encodeddata"
        assert part.uri is None

    def test_file_part_with_uri(self):
        """Test FilePart with URI reference."""
        part = FilePart(mimeType="application/pdf", uri="https://example.com/doc.pdf")
        assert part.uri == "https://example.com/doc.pdf"


class TestDataPart:
    """Tests for DataPart model."""

    def test_data_part_creation(self):
        """Test DataPart creation."""
        part = DataPart(data={"key": "value", "count": 42})
        assert part.type == "data"
        assert part.data["key"] == "value"
        assert part.data["count"] == 42


class TestA2AMessage:
    """Tests for A2AMessage model."""

    def test_message_with_text(self):
        """Test message with text part."""
        msg = A2AMessage(
            role=MessageRole.USER,
            parts=[TextPart(text="Hello")],
        )
        assert msg.role == MessageRole.USER
        assert len(msg.parts) == 1
        assert msg.messageId is not None

    def test_message_with_custom_id(self):
        """Test message with custom ID."""
        msg = A2AMessage(
            role=MessageRole.AGENT,
            parts=[TextPart(text="Response")],
            messageId="msg-123",
        )
        assert msg.messageId == "msg-123"

    def test_message_with_multiple_parts(self):
        """Test message with multiple parts."""
        msg = A2AMessage(
            role=MessageRole.AGENT,
            parts=[
                TextPart(text="Here is an image:"),
                FilePart(mimeType="image/png", uri="https://example.com/img.png"),
            ],
        )
        assert len(msg.parts) == 2


class TestTaskStatus:
    """Tests for TaskStatus model."""

    def test_status_working(self):
        """Test working status."""
        status = TaskStatus(state=TaskState.WORKING)
        assert status.state == TaskState.WORKING
        assert status.message is None

    def test_status_with_message(self):
        """Test status with message."""
        status = TaskStatus(
            state=TaskState.COMPLETED,
            message=A2AMessage(
                role=MessageRole.AGENT,
                parts=[TextPart(text="Done")],
            ),
        )
        assert status.message is not None
        assert len(status.message.parts) == 1


class TestArtifact:
    """Tests for Artifact model."""

    def test_artifact_creation(self):
        """Test artifact creation."""
        artifact = Artifact(
            artifactId="art-1",
            parts=[TextPart(text="Result content")],
        )
        assert artifact.artifactId == "art-1"
        assert artifact.index == 0
        assert artifact.append is False
        assert artifact.lastChunk is False

    def test_artifact_with_all_fields(self):
        """Test artifact with all fields."""
        artifact = Artifact(
            artifactId="art-1",
            name="result",
            parts=[TextPart(text="Chunk")],
            index=2,
            append=True,
            lastChunk=True,
            metadata={"source": "test"},
        )
        assert artifact.name == "result"
        assert artifact.index == 2
        assert artifact.append is True
        assert artifact.lastChunk is True
        assert artifact.metadata["source"] == "test"


class TestTask:
    """Tests for Task model."""

    def test_task_creation(self):
        """Test task creation."""
        task = Task(
            taskId="task-1",
            contextId="ctx-1",
            status=TaskStatus(state=TaskState.WORKING),
        )
        assert task.taskId == "task-1"
        assert task.contextId == "ctx-1"
        assert task.status.state == TaskState.WORKING

    def test_task_with_artifacts(self):
        """Test task with artifacts."""
        task = Task(
            taskId="task-1",
            contextId="ctx-1",
            status=TaskStatus(state=TaskState.COMPLETED),
            artifacts=[
                Artifact(
                    artifactId="art-1",
                    parts=[TextPart(text="Result")],
                )
            ],
        )
        assert task.artifacts is not None
        assert len(task.artifacts) == 1


class TestTaskStatusUpdateEvent:
    """Tests for TaskStatusUpdateEvent model."""

    def test_status_update_event(self):
        """Test status update event creation."""
        event = TaskStatusUpdateEvent(
            taskId="task-1",
            contextId="ctx-1",
            status=TaskStatus(state=TaskState.WORKING),
        )
        assert event.kind == "status-update"
        assert event.taskId == "task-1"
        assert event.final is False

    def test_final_status_update(self):
        """Test final status update."""
        event = TaskStatusUpdateEvent(
            taskId="task-1",
            contextId="ctx-1",
            status=TaskStatus(state=TaskState.COMPLETED),
            final=True,
        )
        assert event.final is True


class TestTaskArtifactUpdateEvent:
    """Tests for TaskArtifactUpdateEvent model."""

    def test_artifact_update_event(self):
        """Test artifact update event creation."""
        event = TaskArtifactUpdateEvent(
            taskId="task-1",
            contextId="ctx-1",
            artifact=Artifact(
                artifactId="art-1",
                parts=[TextPart(text="Content")],
            ),
        )
        assert event.kind == "artifact-update"
        assert event.artifact.artifactId == "art-1"


class TestSendMessageRequest:
    """Tests for SendMessageRequest model."""

    def test_request_creation(self):
        """Test request creation."""
        request = SendMessageRequest(
            params={
                "message": {"role": "user", "parts": [{"type": "text", "text": "Hi"}]},
                "contextId": "ctx-1",
            },
        )
        assert request.jsonrpc == "2.0"
        assert request.method == "message/send"
        assert request.id is not None
        assert request.params["contextId"] == "ctx-1"


class TestSendStreamingMessageRequest:
    """Tests for SendStreamingMessageRequest model."""

    def test_streaming_request_creation(self):
        """Test streaming request creation."""
        request = SendStreamingMessageRequest(
            params={
                "message": {"role": "user", "parts": [{"type": "text", "text": "Hi"}]},
                "contextId": "ctx-1",
                "taskId": "task-1",
            },
        )
        assert request.jsonrpc == "2.0"
        assert request.method == "message/stream"
        assert request.params["taskId"] == "task-1"

    def test_request_serialization(self):
        """Test request JSON serialization."""
        request = SendStreamingMessageRequest(
            id="req-123",
            params={"message": {}, "contextId": "ctx-1"},
        )
        data = json.loads(request.model_dump_json())
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "req-123"
        assert data["method"] == "message/stream"
