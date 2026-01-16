"""Unit tests for A2A to AG-UI translator."""


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
from orchestrator.a2a.translator import A2AToAGUITranslator
from orchestrator.agui.models import (
    Role,
    RunErrorEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)


class TestA2AToAGUITranslator:
    """Tests for the A2A to AG-UI translator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.translator = A2AToAGUITranslator()
        self.run_id = "run-123"

    def test_initial_state(self):
        """Test translator initial state."""
        assert self.translator._current_message_id is None
        assert self.translator._message_started is False

    def test_reset(self):
        """Test reset clears state."""
        self.translator._current_message_id = "msg-1"
        self.translator._message_started = True

        self.translator.reset()

        assert self.translator._current_message_id is None
        assert self.translator._message_started is False


class TestTranslateTask:
    """Tests for Task translation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.translator = A2AToAGUITranslator()
        self.run_id = "run-123"

    def test_completed_task_ends_open_message(self):
        """Test completed task ends any open message."""
        # Start a message first
        self.translator._current_message_id = "msg-1"
        self.translator._message_started = True

        task = Task(
            taskId="task-1",
            contextId="ctx-1",
            status=TaskStatus(state=TaskState.COMPLETED),
        )

        events = self.translator.translate(task, self.run_id)

        assert len(events) == 1
        assert isinstance(events[0], TextMessageEndEvent)
        assert events[0].messageId == "msg-1"
        assert self.translator._message_started is False

    def test_completed_task_no_open_message(self):
        """Test completed task with no open message."""
        task = Task(
            taskId="task-1",
            contextId="ctx-1",
            status=TaskStatus(state=TaskState.COMPLETED),
        )

        events = self.translator.translate(task, self.run_id)

        assert len(events) == 0

    def test_failed_task_emits_error(self):
        """Test failed task emits error event."""
        task = Task(
            taskId="task-1",
            contextId="ctx-1",
            status=TaskStatus(
                state=TaskState.FAILED,
                message=A2AMessage(
                    role=MessageRole.AGENT,
                    parts=[TextPart(text="Connection timeout")],
                ),
            ),
        )

        events = self.translator.translate(task, self.run_id)

        assert len(events) == 1
        assert isinstance(events[0], RunErrorEvent)
        assert events[0].message == "Connection timeout"
        assert events[0].code == "TASK_FAILED"

    def test_failed_task_default_message(self):
        """Test failed task with no message uses default."""
        task = Task(
            taskId="task-1",
            contextId="ctx-1",
            status=TaskStatus(state=TaskState.FAILED),
        )

        events = self.translator.translate(task, self.run_id)

        assert len(events) == 1
        assert events[0].message == "Task failed"

    def test_working_task_no_events(self):
        """Test working task produces no events."""
        task = Task(
            taskId="task-1",
            contextId="ctx-1",
            status=TaskStatus(state=TaskState.WORKING),
        )

        events = self.translator.translate(task, self.run_id)

        assert len(events) == 0


class TestTranslateStatusUpdate:
    """Tests for TaskStatusUpdateEvent translation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.translator = A2AToAGUITranslator()
        self.run_id = "run-123"

    def test_status_with_message_starts_text(self):
        """Test status update with message starts text message."""
        event = TaskStatusUpdateEvent(
            taskId="task-1",
            contextId="ctx-1",
            status=TaskStatus(
                state=TaskState.WORKING,
                message=A2AMessage(
                    role=MessageRole.AGENT,
                    parts=[TextPart(text="Hello")],
                ),
            ),
        )

        events = self.translator.translate(event, self.run_id)

        assert len(events) == 2
        assert isinstance(events[0], TextMessageStartEvent)
        assert events[0].role == Role.ASSISTANT
        assert isinstance(events[1], TextMessageContentEvent)
        assert events[1].delta == "Hello"

    def test_status_continues_existing_message(self):
        """Test status update continues existing message."""
        # Start a message
        self.translator._current_message_id = "msg-1"
        self.translator._message_started = True

        event = TaskStatusUpdateEvent(
            taskId="task-1",
            contextId="ctx-1",
            status=TaskStatus(
                state=TaskState.WORKING,
                message=A2AMessage(
                    role=MessageRole.AGENT,
                    parts=[TextPart(text=" world")],
                ),
            ),
        )

        events = self.translator.translate(event, self.run_id)

        # Should only emit content, not start
        assert len(events) == 1
        assert isinstance(events[0], TextMessageContentEvent)
        assert events[0].messageId == "msg-1"
        assert events[0].delta == " world"

    def test_final_status_ends_message(self):
        """Test final status update ends message."""
        self.translator._current_message_id = "msg-1"
        self.translator._message_started = True

        event = TaskStatusUpdateEvent(
            taskId="task-1",
            contextId="ctx-1",
            status=TaskStatus(state=TaskState.COMPLETED),
            final=True,
        )

        events = self.translator.translate(event, self.run_id)

        assert len(events) == 1
        assert isinstance(events[0], TextMessageEndEvent)
        assert events[0].messageId == "msg-1"

    def test_status_without_message_no_events(self):
        """Test status update without message produces no events."""
        event = TaskStatusUpdateEvent(
            taskId="task-1",
            contextId="ctx-1",
            status=TaskStatus(state=TaskState.WORKING),
        )

        events = self.translator.translate(event, self.run_id)

        assert len(events) == 0

    def test_status_with_empty_text(self):
        """Test status with empty text part is ignored."""
        event = TaskStatusUpdateEvent(
            taskId="task-1",
            contextId="ctx-1",
            status=TaskStatus(
                state=TaskState.WORKING,
                message=A2AMessage(
                    role=MessageRole.AGENT,
                    parts=[TextPart(text="")],
                ),
            ),
        )

        events = self.translator.translate(event, self.run_id)

        assert len(events) == 0


class TestTranslateArtifactUpdate:
    """Tests for TaskArtifactUpdateEvent translation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.translator = A2AToAGUITranslator()
        self.run_id = "run-123"

    def test_artifact_starts_message(self):
        """Test artifact update starts new message."""
        event = TaskArtifactUpdateEvent(
            taskId="task-1",
            contextId="ctx-1",
            artifact=Artifact(
                artifactId="art-1",
                parts=[TextPart(text="Result")],
            ),
        )

        events = self.translator.translate(event, self.run_id)

        assert len(events) == 2
        assert isinstance(events[0], TextMessageStartEvent)
        assert isinstance(events[1], TextMessageContentEvent)
        assert events[1].delta == "Result"

    def test_artifact_continues_message(self):
        """Test artifact update continues existing message."""
        self.translator._current_message_id = "msg-1"
        self.translator._message_started = True

        event = TaskArtifactUpdateEvent(
            taskId="task-1",
            contextId="ctx-1",
            artifact=Artifact(
                artifactId="art-1",
                parts=[TextPart(text=" more")],
                append=True,
            ),
        )

        events = self.translator.translate(event, self.run_id)

        assert len(events) == 1
        assert isinstance(events[0], TextMessageContentEvent)

    def test_last_chunk_ends_message(self):
        """Test last chunk artifact ends message."""
        self.translator._current_message_id = "msg-1"
        self.translator._message_started = True

        event = TaskArtifactUpdateEvent(
            taskId="task-1",
            contextId="ctx-1",
            artifact=Artifact(
                artifactId="art-1",
                parts=[TextPart(text="done")],
                lastChunk=True,
            ),
        )

        events = self.translator.translate(event, self.run_id)

        assert len(events) == 2
        assert isinstance(events[0], TextMessageContentEvent)
        assert isinstance(events[1], TextMessageEndEvent)
        assert self.translator._message_started is False

    def test_artifact_with_multiple_parts(self):
        """Test artifact with multiple text parts."""
        event = TaskArtifactUpdateEvent(
            taskId="task-1",
            contextId="ctx-1",
            artifact=Artifact(
                artifactId="art-1",
                parts=[
                    TextPart(text="First"),
                    TextPart(text="Second"),
                ],
            ),
        )

        events = self.translator.translate(event, self.run_id)

        # Start + 2 content events
        assert len(events) == 3
        assert isinstance(events[0], TextMessageStartEvent)
        assert events[1].delta == "First"
        assert events[2].delta == "Second"


class TestFinalize:
    """Tests for translator finalize method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.translator = A2AToAGUITranslator()

    def test_finalize_closes_open_message(self):
        """Test finalize closes any open message."""
        self.translator._current_message_id = "msg-1"
        self.translator._message_started = True

        events = self.translator.finalize()

        assert len(events) == 1
        assert isinstance(events[0], TextMessageEndEvent)
        assert events[0].messageId == "msg-1"
        assert self.translator._message_started is False

    def test_finalize_no_open_message(self):
        """Test finalize with no open message."""
        events = self.translator.finalize()

        assert len(events) == 0

    def test_finalize_with_custom_timestamp(self):
        """Test finalize with custom timestamp."""
        self.translator._current_message_id = "msg-1"
        self.translator._message_started = True

        events = self.translator.finalize(timestamp=12345)

        assert events[0].timestamp == 12345


class TestCompleteConversation:
    """Integration tests for complete conversation flows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.translator = A2AToAGUITranslator()
        self.run_id = "run-123"

    def test_simple_response_flow(self):
        """Test a simple response: start -> content -> end."""
        # Working status with initial content
        status1 = TaskStatusUpdateEvent(
            taskId="task-1",
            contextId="ctx-1",
            status=TaskStatus(
                state=TaskState.WORKING,
                message=A2AMessage(
                    role=MessageRole.AGENT,
                    parts=[TextPart(text="Hello")],
                ),
            ),
        )
        events1 = self.translator.translate(status1, self.run_id)
        assert len(events1) == 2  # Start + Content

        # More content via artifact
        artifact = TaskArtifactUpdateEvent(
            taskId="task-1",
            contextId="ctx-1",
            artifact=Artifact(
                artifactId="art-1",
                parts=[TextPart(text=" world!")],
                lastChunk=True,
            ),
        )
        events2 = self.translator.translate(artifact, self.run_id)
        assert len(events2) == 2  # Content + End

        # Verify message is closed
        assert self.translator._message_started is False

    def test_streaming_chunks_flow(self):
        """Test streaming multiple artifact chunks."""
        chunks = ["The ", "quick ", "brown ", "fox"]
        all_events = []

        for i, chunk in enumerate(chunks):
            is_last = i == len(chunks) - 1
            event = TaskArtifactUpdateEvent(
                taskId="task-1",
                contextId="ctx-1",
                artifact=Artifact(
                    artifactId="art-1",
                    parts=[TextPart(text=chunk)],
                    append=i > 0,
                    lastChunk=is_last,
                ),
            )
            all_events.extend(self.translator.translate(event, self.run_id))

        # Should have: Start + 4 Content + End = 6 events
        assert len(all_events) == 6
        assert isinstance(all_events[0], TextMessageStartEvent)
        assert isinstance(all_events[-1], TextMessageEndEvent)

        # Check content order
        content_events = [e for e in all_events if isinstance(e, TextMessageContentEvent)]
        assert len(content_events) == 4
        assert "".join(e.delta for e in content_events) == "The quick brown fox"
