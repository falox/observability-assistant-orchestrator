"""FastAPI router for AG-UI endpoints."""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .encoder import SSEEncoder
from .handler import AGUIHandler
from .models import RunAgentInput

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agui", tags=["agui"])


@router.post("/chat")
async def chat(request: Request, input_data: RunAgentInput) -> StreamingResponse:
    """AG-UI chat endpoint.

    Receives RunAgentInput, streams AG-UI events as SSE.

    Args:
        request: The FastAPI request object.
        input_data: The AG-UI input containing messages and configuration.

    Returns:
        StreamingResponse with AG-UI events as SSE.
    """
    logger.info(
        "[AG-UI] IN: threadId=%s runId=%s messages=%d",
        input_data.threadId,
        input_data.runId,
        len(input_data.messages),
    )

    encoder = SSEEncoder()
    handler = AGUIHandler()

    async def event_generator():
        try:
            async for event in handler.run(input_data):
                encoded = encoder.encode(event)
                logger.debug("[AG-UI] OUT: %s", event.type.value)
                yield encoded
        except Exception as e:
            logger.exception("[AG-UI] Error during streaming: %s", str(e))
            yield encoder.encode_error(str(e))
        finally:
            yield encoder.encode_done()

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
