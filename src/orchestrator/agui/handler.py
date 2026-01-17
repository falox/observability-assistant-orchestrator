"""AG-UI request handler - orchestrates A2A communication."""

import logging
import time
from typing import AsyncIterator

from ..a2a.client import A2AClient
from ..a2a.translator import A2AToAGUITranslator
from ..config.settings import Settings
from .models import (
    AGUIEvent,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
)

logger = logging.getLogger(__name__)


class AGUIHandler:
    """Handles AG-UI requests and orchestrates A2A communication."""

    def __init__(self, settings: Settings | None = None):
        """Initialize the handler.

        Args:
            settings: Application settings. If None, loads from environment.
        """
        self.settings = settings or Settings()
        self._observability_client = A2AClient(
            base_url=self.settings.observability_agent_url,
            timeout=self.settings.a2a_agent_timeout,
            path=self.settings.observability_agent_path,
        )
        self._generic_client = A2AClient(
            base_url=self.settings.generic_agent_url,
            timeout=self.settings.a2a_agent_timeout,
            path=self.settings.generic_agent_path,
        )

    def _get_client_for_message(
        self, input_data: RunAgentInput
    ) -> tuple[A2AClient | None, str, list]:
        """Determine which A2A client to use based on message content.

        Routes to Generic agent if the last user message starts with 'LS' (case insensitive).
        If routing to Generic agent, strips the 'LS ' prefix from the message.
        If the message is just 'LS' with no content after, returns None client.

        Returns:
            Tuple of (client, agent_url, messages) to use. Client is None if no request
            should be sent (e.g., message is just "LS" with no content).
        """
        messages = list(input_data.messages)

        # Find the last user message
        for i, message in enumerate(reversed(messages)):
            if message.role.value == "user" and message.content:
                content = message.content.strip()
                if content.upper().startswith("LS"):
                    # Strip the "LS" prefix (and any following space)
                    stripped_content = content[2:].lstrip()

                    # If message is just "LS" with no content, don't send anything
                    if not stripped_content:
                        logger.info("[Handler] Message is just 'LS' with no content, skipping")
                        return None, "", messages

                    logger.info("[Handler] Routing to Generic agent based on message prefix")
                    # Create a modified copy of messages with the prefix removed
                    idx = len(messages) - 1 - i
                    messages = messages.copy()
                    # Create a new message with stripped content
                    original_msg = messages[idx]
                    from .models import Message

                    messages[idx] = Message(
                        id=original_msg.id,
                        role=original_msg.role,
                        content=stripped_content,
                        name=original_msg.name,
                        tool_call_id=original_msg.tool_call_id,
                    )
                    return (
                        self._generic_client,
                        self.settings.generic_agent_url,
                        messages,
                    )
                break

        return (
            self._observability_client,
            self.settings.observability_agent_url,
            messages,
        )

    async def run(self, input_data: RunAgentInput) -> AsyncIterator[AGUIEvent]:
        """Process AG-UI input and yield AG-UI events.

        Translates to A2A, streams response, translates back.

        Args:
            input_data: The AG-UI input containing messages and configuration.

        Yields:
            AG-UI events for the frontend.
        """
        timestamp = int(time.time() * 1000)
        translator = A2AToAGUITranslator()

        # Emit run started
        yield RunStartedEvent(
            threadId=input_data.threadId,
            runId=input_data.runId,
            timestamp=timestamp,
        )

        try:
            # Route to appropriate agent based on message content
            client, agent_url, messages = self._get_client_for_message(input_data)

            # If client is None, skip sending (e.g., message was just "LS")
            if client is not None:
                logger.info(
                    "[Handler] Dispatching to A2A agent: %s",
                    agent_url,
                )

                # Send to A2A agent and stream response
                async for a2a_event in client.send_message_streaming(
                    context_id=input_data.threadId,
                    messages=messages,
                ):
                    logger.debug(
                        "[Handler] Received A2A event: %s", type(a2a_event).__name__
                    )

                    # Translate A2A events to AG-UI events
                    agui_events = translator.translate(a2a_event, input_data.runId)
                    for event in agui_events:
                        yield event

                # Finalize any open events
                for event in translator.finalize():
                    yield event

            # Emit run finished
            yield RunFinishedEvent(
                threadId=input_data.threadId,
                runId=input_data.runId,
                timestamp=int(time.time() * 1000),
            )

        except Exception as e:
            logger.exception("[Handler] Error during A2A communication: %s", str(e))

            # Finalize any open events before error
            for event in translator.finalize():
                yield event

            yield RunErrorEvent(
                message=str(e),
                code="A2A_ERROR",
                timestamp=int(time.time() * 1000),
            )
