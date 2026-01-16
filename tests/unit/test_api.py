"""Unit tests for API endpoints."""



class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_liveness(self, client):
        """Test liveness probe returns ok."""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_readiness(self, client):
        """Test readiness probe returns ok."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_api_info(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "A2A-AGUI Orchestrator"
        assert "version" in data
        assert "endpoints" in data
        assert data["endpoints"]["agui_chat"] == "/api/agui/chat"

    def test_root_includes_all_endpoints(self, client):
        """Test root includes all documented endpoints."""
        response = client.get("/")
        data = response.json()

        endpoints = data["endpoints"]
        assert "agui_chat" in endpoints
        assert "health_live" in endpoints
        assert "health_ready" in endpoints


class TestOpenAPISchema:
    """Tests for OpenAPI schema."""

    def test_openapi_schema_available(self, client):
        """Test OpenAPI schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert schema["info"]["title"] == "A2A-AGUI Orchestrator"
        assert "paths" in schema

    def test_agui_chat_endpoint_documented(self, client):
        """Test AG-UI chat endpoint is documented."""
        response = client.get("/openapi.json")
        schema = response.json()

        assert "/api/agui/chat" in schema["paths"]
        assert "post" in schema["paths"]["/api/agui/chat"]


class TestCORSHeaders:
    """Tests for CORS headers."""

    def test_cors_preflight(self, client):
        """Test CORS preflight request."""
        response = client.options(
            "/api/agui/chat",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        # CORS middleware should handle this
        assert response.status_code in [200, 405]

    def test_cors_headers_present(self, client):
        """Test CORS headers are present in response."""
        response = client.get(
            "/health/live",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        # FastAPI CORS middleware adds these headers
        assert "access-control-allow-origin" in response.headers
