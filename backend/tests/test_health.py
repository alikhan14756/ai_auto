"""Test health endpoints and system indicators."""


def test_root_endpoint(client):
    """Test the root index endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["app_name"] == "Creator Studio AI"
    assert "version" in data


def test_health_check_endpoint(client):
    """Test the /api/v1/health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "Creator Studio AI"
    assert "services" in data
    assert "database" in data["services"]
    assert "ai_provider" in data["services"]
    assert "audio_engine" in data["services"]
    assert "storage" in data["services"]


def test_health_root_alias(client):
    """Test the root /health alias."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
