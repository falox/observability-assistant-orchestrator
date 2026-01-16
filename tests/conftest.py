"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from orchestrator.a2a.translator import A2AToAGUITranslator
from orchestrator.agui.models import Message, Role, RunAgentInput
from orchestrator.config.settings import Settings
from orchestrator.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        host="127.0.0.1",
        port=5050,
        a2a_agent_url="http://localhost:9999",
        a2a_agent_timeout=30,
        log_level="DEBUG",
    )


@pytest.fixture
def translator():
    """Create a fresh translator instance."""
    return A2AToAGUITranslator()


@pytest.fixture
def sample_run_input():
    """Create a sample RunAgentInput for testing."""
    return RunAgentInput(
        threadId="test-thread-123",
        runId="test-run-456",
        messages=[
            Message(
                id="msg-1",
                role=Role.USER,
                content="Hello, how are you?",
            ),
        ],
    )


@pytest.fixture
def sample_conversation_input():
    """Create a multi-turn conversation input."""
    return RunAgentInput(
        threadId="test-thread-123",
        runId="test-run-789",
        messages=[
            Message(id="msg-1", role=Role.USER, content="What is 2+2?"),
            Message(id="msg-2", role=Role.ASSISTANT, content="2+2 equals 4."),
            Message(id="msg-3", role=Role.USER, content="And 3+3?"),
        ],
    )
