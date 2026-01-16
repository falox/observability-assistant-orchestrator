"""Unit tests for AG-UI handler."""

from unittest.mock import MagicMock, patch

import pytest

from orchestrator.a2a.models import (
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
from orchestrator.agui.handler import AGUIHandler
from orchestrator.agui.models import (
    EventType,
    Message,
    Role,
    RunAgentInput,
)
from orchestrator.utils.errors import A2AConnectionError


class TestAGUIHandler:
    """Tests for AGUIHandler."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.a2a_agent_url = "http://localhost:9999"
        settings.a2a_agent_timeout = 300
        return settings

    @pytest.fixture
    def handler(self, mock_settings):
        """Create handler with mock settings."""
        return AGUIHandler(settings=mock_settings)

    @pytest.fixture
    def sample_input(self):
        """Create sample AG-UI input."""
        return RunAgentInput(
            threadId="thread-123",
            runId="run-456",
            messages=[
                Message(
                    id="msg-1",
                    role=Role.USER,
                    content="Hello, agent!",
                )
            ],
        )


class TestRunSuccess(TestAGUIHandler):
    """Tests for successful run scenarios."""

    @pytest.mark.asyncio
    async def test_run_emits_started_and_finished(self, handler, sample_input):
        """Test that run emits RUN_STARTED and RUN_FINISHED events."""
        # Mock A2A client to return empty stream
        async def empty_stream(*args, **kwargs):
            return
            yield  # Makes this an async generator

        with patch.object(
            handler.a2a_client, "send_message_streaming", side_effect=empty_stream
        ):
            events = []
            async for event in handler.run(sample_input):
                events.append(event)

        assert len(events) == 2
        assert events[0].type == EventType.RUN_STARTED
        assert events[0].threadId == "thread-123"
        assert events[0].runId == "run-456"

        assert events[-1].type == EventType.RUN_FINISHED
        assert events[-1].threadId == "thread-123"
        assert events[-1].runId == "run-456"

    @pytest.mark.asyncio
    async def test_run_translates_status_updates(self, handler, sample_input):
        """Test that status updates are translated to text events."""
        async def mock_stream(*args, **kwargs):
            yield TaskStatusUpdateEvent(
                kind="status-update",
                taskId="task-1",
                contextId="thread-123",
                status=TaskStatus(
                    state=TaskState.WORKING,
                    message=A2AMessage(
                        role=MessageRole.AGENT,
                        parts=[TextPart(text="Processing your request...")],
                    ),
                ),
                final=False,
            )

        with patch.object(
            handler.a2a_client, "send_message_streaming", side_effect=mock_stream
        ):
            events = []
            async for event in handler.run(sample_input):
                events.append(event)

        # Should have: RUN_STARTED, TEXT_MESSAGE_START, TEXT_MESSAGE_CONTENT,
        # TEXT_MESSAGE_END (from finalize), RUN_FINISHED
        event_types = [e.type for e in events]
        assert EventType.RUN_STARTED in event_types
        assert EventType.TEXT_MESSAGE_START in event_types
        assert EventType.TEXT_MESSAGE_CONTENT in event_types
        assert EventType.RUN_FINISHED in event_types

    @pytest.mark.asyncio
    async def test_run_translates_artifact_updates(self, handler, sample_input):
        """Test that artifact updates are translated to text events."""
        async def mock_stream(*args, **kwargs):
            yield TaskArtifactUpdateEvent(
                kind="artifact-update",
                taskId="task-1",
                contextId="thread-123",
                artifact=Artifact(
                    artifactId="art-1",
                    parts=[TextPart(text="Here is the response.")],
                    lastChunk=True,
                ),
            )

        with patch.object(
            handler.a2a_client, "send_message_streaming", side_effect=mock_stream
        ):
            events = []
            async for event in handler.run(sample_input):
                events.append(event)

        event_types = [e.type for e in events]
        assert EventType.TEXT_MESSAGE_START in event_types
        assert EventType.TEXT_MESSAGE_CONTENT in event_types
        assert EventType.TEXT_MESSAGE_END in event_types

    @pytest.mark.asyncio
    async def test_run_handles_streaming_chunks(self, handler, sample_input):
        """Test handling of multiple streaming chunks."""
        async def mock_stream(*args, **kwargs):
            # First chunk
            yield TaskArtifactUpdateEvent(
                kind="artifact-update",
                taskId="task-1",
                contextId="thread-123",
                artifact=Artifact(
                    artifactId="art-1",
                    parts=[TextPart(text="Hello ")],
                    lastChunk=False,
                    append=False,
                ),
            )
            # Second chunk
            yield TaskArtifactUpdateEvent(
                kind="artifact-update",
                taskId="task-1",
                contextId="thread-123",
                artifact=Artifact(
                    artifactId="art-1",
                    parts=[TextPart(text="world!")],
                    lastChunk=True,
                    append=True,
                ),
            )

        with patch.object(
            handler.a2a_client, "send_message_streaming", side_effect=mock_stream
        ):
            events = []
            async for event in handler.run(sample_input):
                events.append(event)

        # Find content events
        content_events = [e for e in events if e.type == EventType.TEXT_MESSAGE_CONTENT]
        assert len(content_events) == 2
        assert content_events[0].delta == "Hello "
        assert content_events[1].delta == "world!"

    @pytest.mark.asyncio
    async def test_run_handles_completed_task(self, handler, sample_input):
        """Test handling of completed task."""
        async def mock_stream(*args, **kwargs):
            yield TaskArtifactUpdateEvent(
                kind="artifact-update",
                taskId="task-1",
                contextId="thread-123",
                artifact=Artifact(
                    artifactId="art-1",
                    parts=[TextPart(text="Done!")],
                    lastChunk=False,
                ),
            )
            yield Task(
                taskId="task-1",
                contextId="thread-123",
                status=TaskStatus(state=TaskState.COMPLETED),
            )

        with patch.object(
            handler.a2a_client, "send_message_streaming", side_effect=mock_stream
        ):
            events = []
            async for event in handler.run(sample_input):
                events.append(event)

        # Message should be ended
        event_types = [e.type for e in events]
        assert EventType.TEXT_MESSAGE_END in event_types


class TestRunErrors(TestAGUIHandler):
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_run_handles_connection_error(self, handler, sample_input):
        """Test that connection errors are caught and emitted as RUN_ERROR."""
        async def mock_stream(*args, **kwargs):
            raise A2AConnectionError(
                "Failed to connect",
                url="http://localhost:9999",
            )
            yield  # Make it a generator

        with patch.object(
            handler.a2a_client, "send_message_streaming", side_effect=mock_stream
        ):
            events = []
            async for event in handler.run(sample_input):
                events.append(event)

        assert events[0].type == EventType.RUN_STARTED
        assert events[-1].type == EventType.RUN_ERROR
        assert "Failed to connect" in events[-1].message
        assert events[-1].code == "A2A_ERROR"

    @pytest.mark.asyncio
    async def test_run_handles_mid_stream_error(self, handler, sample_input):
        """Test error occurring mid-stream finalizes open message."""
        async def mock_stream(*args, **kwargs):
            yield TaskArtifactUpdateEvent(
                kind="artifact-update",
                taskId="task-1",
                contextId="thread-123",
                artifact=Artifact(
                    artifactId="art-1",
                    parts=[TextPart(text="Starting...")],
                    lastChunk=False,
                ),
            )
            raise Exception("Connection lost")

        with patch.object(
            handler.a2a_client, "send_message_streaming", side_effect=mock_stream
        ):
            events = []
            async for event in handler.run(sample_input):
                events.append(event)

        event_types = [e.type for e in events]

        # Should have started a message
        assert EventType.TEXT_MESSAGE_START in event_types
        assert EventType.TEXT_MESSAGE_CONTENT in event_types

        # Should finalize the message before error
        assert EventType.TEXT_MESSAGE_END in event_types

        # Should emit error
        assert events[-1].type == EventType.RUN_ERROR
        assert "Connection lost" in events[-1].message

    @pytest.mark.asyncio
    async def test_run_handles_failed_task(self, handler, sample_input):
        """Test handling of failed task from A2A agent."""
        async def mock_stream(*args, **kwargs):
            yield Task(
                taskId="task-1",
                contextId="thread-123",
                status=TaskStatus(
                    state=TaskState.FAILED,
                    message=A2AMessage(
                        role=MessageRole.AGENT,
                        parts=[TextPart(text="Task failed due to internal error")],
                    ),
                ),
            )

        with patch.object(
            handler.a2a_client, "send_message_streaming", side_effect=mock_stream
        ):
            events = []
            async for event in handler.run(sample_input):
                events.append(event)

        # Should emit RUN_ERROR for failed task (translated from Task)
        error_events = [e for e in events if e.type == EventType.RUN_ERROR]
        assert len(error_events) >= 1


class TestHandlerConfiguration(TestAGUIHandler):
    """Tests for handler configuration."""

    def test_handler_uses_settings(self, mock_settings):
        """Test that handler uses provided settings."""
        handler = AGUIHandler(settings=mock_settings)
        assert handler.a2a_client.base_url == "http://localhost:9999"
        assert handler.a2a_client.timeout == 300

    def test_handler_loads_default_settings(self):
        """Test that handler loads settings from environment if not provided."""
        with patch("orchestrator.agui.handler.Settings") as mock_settings_cls:
            mock_instance = MagicMock()
            mock_instance.a2a_agent_url = "http://default:8080"
            mock_instance.a2a_agent_timeout = 60
            mock_settings_cls.return_value = mock_instance

            handler = AGUIHandler()
            assert handler.settings == mock_instance
