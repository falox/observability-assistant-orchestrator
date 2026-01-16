# Observability Assistant Orchestrator

Orchestrator for observability and troubleshooting tasks.

## Overview

This orchestrator dispatches observability and troubleshooting tasks (both proactive and reactive) to the most appropriate A2A agent. It bridges the AG-UI protocol (used by frontends) with the A2A (Agent-to-Agent) protocol used by backend agents.

```
┌─────────────────────┐     AG-UI      ┌──────────────────┐      A2A       ┌─────────────────┐
│  Frontend (UI)      │ ──────────────▶│   Orchestrator   │──────────────▶ │  Agent (A2A)    │
│                     │ ◀──────────────│   (this project) │◀────────────── │                 │
└─────────────────────┘     SSE        └──────────────────┘     SSE        └─────────────────┘
```

## Features

- **AG-UI Interface**: Exposes `/api/agui/chat` endpoint compatible with AG-UI protocol
- **A2A Client**: Communicates with A2A agents via streaming JSON-RPC
- **Event Translation**: Converts A2A events to AG-UI events in real-time
- **Streaming**: End-to-end streaming via Server-Sent Events (SSE)

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- A running A2A agent

### Installation

```bash
# Install dependencies
make install

# Or with dev dependencies
make dev
```

### Running

```bash
# Run with default A2A agent URL (localhost:9999)
make run

# Or specify a custom A2A agent URL
ORCHESTRATOR_A2A_AGENT_URL=http://my-agent:9999 make run
```

The orchestrator will start on port 5050 by default.

### Configuration

Configuration is done via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ORCHESTRATOR_A2A_AGENT_URL` | `http://localhost:9999` | URL of the A2A agent |
| `ORCHESTRATOR_HOST` | `0.0.0.0` | Server host |
| `ORCHESTRATOR_PORT` | `5050` | Server port |
| `ORCHESTRATOR_LOG_LEVEL` | `INFO` | Logging level |

## API Endpoints

- `POST /api/agui/chat` - AG-UI chat endpoint (SSE streaming)
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe
- `GET /` - API info

## Development

```bash
# Run linting
make lint

# Format code
make format

# Run tests
make test
```

## Architecture

### Modules

- **agui/**: AG-UI protocol implementation
  - `models.py`: Pydantic models for AG-UI events
  - `router.py`: FastAPI router for `/api/agui/chat`
  - `encoder.py`: SSE encoder
  - `handler.py`: Request handler and orchestration

- **a2a/**: A2A protocol implementation
  - `models.py`: Pydantic models for A2A messages and events
  - `client.py`: Async streaming A2A client
  - `translator.py`: A2A to AG-UI event translation

- **config/**: Configuration management
  - `settings.py`: Pydantic Settings with env var support

## License

Apache-2.0
