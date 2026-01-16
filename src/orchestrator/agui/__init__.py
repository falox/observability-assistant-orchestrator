"""AG-UI protocol module."""

from .encoder import SSEEncoder
from .models import AGUIEvent, EventType, Message, Role, RunAgentInput

# Note: AGUIHandler and router are not exported at package level to avoid
# circular imports with the a2a module. Import them directly when needed:
#   from orchestrator.agui.handler import AGUIHandler
#   from orchestrator.agui.router import router

__all__ = ["SSEEncoder", "AGUIEvent", "EventType", "Message", "Role", "RunAgentInput"]
