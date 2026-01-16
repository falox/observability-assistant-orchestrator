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
        self.a2a_client = A2AClient(
            base_url=self.settings.a2a_agent_url,
            timeout=self.settings.a2a_agent_timeout,
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
            logger.info(
                "[Handler] Dispatching to A2A agent: %s",
                self.settings.a2a_agent_url,
            )

            # Send to A2A agent and stream response
            async for a2a_event in self.a2a_client.send_message_streaming(
                context_id=input_data.threadId,
                messages=input_data.messages,
            ):
                logger.debug("[Handler] Received A2A event: %s", type(a2a_event).__name__)

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
