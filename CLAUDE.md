# Observability Assistant Orchestrator

## Project Overview

Orchestrator that dispatches observability and troubleshooting tasks to the most appropriate A2A agent. Supports both proactive and reactive workflows. Bridges the AG-UI protocol (frontend) with the A2A protocol (backend agents).

```
Frontend (AG-UI) → Orchestrator → Observability Agent (default)
                                → Generic Agent (for "LS" prefixed messages)
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
make run        # Run server (port 5050)
make lint       # Run ruff + mypy
make format     # Format code
make test       # Run tests
```

## Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `ORCHESTRATOR_OBSERVABILITY_AGENT_URL` | `http://localhost:9999` | Observability agent URL (default) |
| `ORCHESTRATOR_OBSERVABILITY_AGENT_PATH` | `/` | Observability agent endpoint path |
| `ORCHESTRATOR_GENERIC_AGENT_URL` | `http://localhost:8080` | Generic agent URL (for "LS" prefixed messages) |
| `ORCHESTRATOR_GENERIC_AGENT_PATH` | `/a2a` | Generic agent endpoint path |
| `ORCHESTRATOR_HOST` | `0.0.0.0` | Server host |
| `ORCHESTRATOR_PORT` | `5050` | Server port |
| `ORCHESTRATOR_LOG_LEVEL` | `INFO` | Log level |

## Routing Logic

Messages are routed based on their content:
- Messages starting with **"LS"** (case insensitive) → Generic Agent (`ORCHESTRATOR_GENERIC_AGENT_URL`)
  - The "LS " prefix is stripped before forwarding
  - If the message is just "LS" with no content, nothing is sent
- All other messages → Observability Agent (`ORCHESTRATOR_OBSERVABILITY_AGENT_URL`)

## API Endpoints

- `POST /api/agui/chat` - AG-UI chat (SSE streaming)
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe

## Data Flow

1. Frontend sends `RunAgentInput` to `/api/agui/chat`
2. `AGUIHandler` emits `RUN_STARTED`, routes to appropriate A2A client based on message prefix
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
# Terminal 1: Start your Observability agent on port 9999

# Terminal 2: Start your Generic agent on port 8080

# Terminal 3: Start orchestrator
make run

# Terminal 4: Start your AG-UI frontend
# Configure it to connect to localhost:5050
```

Frontend connects to orchestrator at `localhost:5050`, which routes:
- Messages starting with "LS" → Generic agent at `localhost:8080`
- All other messages → Observability agent at `localhost:9999`
