# Observability Assistant Orchestrator

## Project Overview

Orchestrator that dispatches observability and troubleshooting tasks to the most appropriate A2A agent. Supports both proactive and reactive workflows. Bridges the AG-UI protocol (frontend) with the A2A protocol (backend agents).

```
Frontend (AG-UI) → Orchestrator → A2A Agent
```

## Tech Stack

- **Python 3.12+** with **FastAPI** + **Uvicorn**
- **httpx** for async HTTP streaming
- **Pydantic v2** for data validation
- **a2a-sdk** for A2A protocol
- **google-adk** for future ADK agent integration
- **uv** package manager

## Project Structure

```
src/orchestrator/
├── main.py              # FastAPI app entry point
├── config/
│   └── settings.py      # Pydantic Settings (env vars)
├── agui/                # AG-UI protocol
│   ├── models.py        # Event types (RUN_*, TEXT_MESSAGE_*, TOOL_CALL_*)
│   ├── router.py        # POST /api/agui/chat endpoint
│   ├── encoder.py       # SSE encoder
│   └── handler.py       # Orchestration logic
├── a2a/                 # A2A protocol
│   ├── models.py        # Task, Message, Events
│   ├── client.py        # Streaming A2A client
│   └── translator.py    # A2A → AG-UI event translation
└── utils/
    └── logging.py
```

## Key Commands

```bash
make install    # Install dependencies
make run        # Run server (port 5050, A2A agent at localhost:9999)
make lint       # Run ruff + mypy
make format     # Format code
make test       # Run tests
```

## Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `ORCHESTRATOR_A2A_AGENT_URL` | `http://localhost:9999` | A2A agent URL |
| `ORCHESTRATOR_HOST` | `0.0.0.0` | Server host |
| `ORCHESTRATOR_PORT` | `5050` | Server port |
| `ORCHESTRATOR_LOG_LEVEL` | `INFO` | Log level |

## API Endpoints

- `POST /api/agui/chat` - AG-UI chat (SSE streaming)
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe

## Data Flow

1. Frontend sends `RunAgentInput` to `/api/agui/chat`
2. `AGUIHandler` emits `RUN_STARTED`, forwards to A2A client
3. `A2AClient` streams to A2A agent, receives `TaskStatusUpdateEvent`/`TaskArtifactUpdateEvent`
4. `A2AToAGUITranslator` converts to `TEXT_MESSAGE_*` events
5. SSE encoder streams back to frontend
6. `RUN_FINISHED` sent on completion

## Key Files

- [src/orchestrator/agui/handler.py](src/orchestrator/agui/handler.py) - Main orchestration logic
- [src/orchestrator/a2a/client.py](src/orchestrator/a2a/client.py) - A2A streaming client
- [src/orchestrator/a2a/translator.py](src/orchestrator/a2a/translator.py) - Event translation
- [src/orchestrator/agui/models.py](src/orchestrator/agui/models.py) - AG-UI event types

## Testing

```bash
# Terminal 1: Start your A2A agent on port 9999

# Terminal 2: Start orchestrator
make run

# Terminal 3: Start your AG-UI frontend
# Configure it to connect to localhost:5050
```

Frontend connects to orchestrator at `localhost:5050`, which forwards to A2A agent at `localhost:9999`.
