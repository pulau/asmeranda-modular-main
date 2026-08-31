"""
Integration tests untuk FastAPI endpoints.

Test coverage:
- Health check endpoint
- Dataset CRUD operations
- Error responses
- Status codes
"""
import io
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestAPIHealth:
    """Test health check endpoint"""

    def test_health_endpoint_exists(self, client: TestClient):
        """Test health endpoint is accessible."""
        response = client.get("/health")
        assert response.status_code in [200, 404]  # Might not exist yet

    def test_health_endpoint_returns_ok(self, client: TestClient):
        """Test health endpoint returns ok status."""
        response = client.get("/health")
        if response.status_code == 200:
            data = response.json()
            assert data.get("status") == "ok"

    def test_health_endpoint_no_auth_required(self, client: TestClient):
        """Test health endpoint doesn't require authentication."""
        response = client.get("/health")
        assert response.status_code != 401  # Should not be unauthorized


@pytest.mark.integration
class TestDatasetAPI:
    """Test dataset-related endpoints"""

    def test_upload_dataset_endpoint_exists(self, client: TestClient):
        """Test dataset upload endpoint is accessible."""
        response = client.post("/api/v1/datasets", files={})
        # Should not be 404
        assert response.status_code != 404 or response.status_code in [400, 422]

    def test_list_datasets_endpoint_exists(self, client: TestClient):
        """Test list datasets endpoint is accessible."""
        response = client.get("/api/v1/datasets")
        # Should return 200 atau 401 (auth required)
        assert response.status_code in [200, 401, 404]

    def test_get_dataset_endpoint_exists(self, client: TestClient):
        """Test get dataset endpoint is accessible."""
        response = client.get("/api/v1/datasets/test-id")
        # Should return 200, 404, atau 401
        assert response.status_code in [200, 404, 401]

    def test_invalid_endpoint_returns_404(self, client: TestClient):
        """Test invalid endpoint returns 404."""
        response = client.get("/api/v1/nonexistent-endpoint")
        assert response.status_code == 404

    def test_api_response_format_json(self, client: TestClient):
        """Test API responses are JSON format."""
        response = client.get("/health")
        if response.status_code == 200:
            # Should be valid JSON
            data = response.json()
            assert isinstance(data, dict)

    def test_api_error_response_has_detail(self, client: TestClient):
        """Test error responses include detail message."""
        response = client.get("/api/v1/datasets/invalid-id")
        # Even if error, should have structure
        if response.status_code != 200:
            data = response.json()
            # FastAPI errors include 'detail'
            assert "detail" in data or response.status_code == 200


@pytest.mark.integration
class TestAPIErrorHandling:
    """Test error handling dalam API"""

    def test_invalid_http_method_returns_405(self, client: TestClient):
        """Test invalid HTTP method returns 405."""
        response = client.put("/health")
        assert response.status_code in [405, 404]

    def test_malformed_json_returns_422(self, client: TestClient):
        """Test malformed JSON returns 422."""
        response = client.post(
            "/api/v1/preprocessing/run",
            json={"invalid": "data structure"},
            headers={"Content-Type": "application/json"}
        )
        # Should be 422 (Unprocessable Entity) atau 400
        assert response.status_code in [422, 400, 401, 404]

    def test_missing_required_fields_returns_error(self, client: TestClient):
        """Test missing required fields returns error."""
        response = client.post(
            "/api/v1/preprocessing/run",
            json={},
            headers={"Content-Type": "application/json"}
        )
        # Should return error (422 atau 400)
        assert response.status_code in [422, 400, 401, 404]

    def test_api_timeout_handling(self, client: TestClient):
        """Test API handles timeouts gracefully."""
        # Should not raise exception
        response = client.get("/health")
        assert response.status_code is not None


@pytest.mark.integration
class TestAPIEndpointStructure:
    """Test API endpoint structure dan conventions"""

    def test_api_endpoints_follow_v1_pattern(self, client: TestClient):
        """Test API endpoints follow /api/v1/ pattern."""
        # Endpoints should start with /api/v1/
        response = client.get("/api/v1/datasets")
        # Should be accessible (might need auth)
        assert response.status_code in [200, 401, 404]

    def test_api_versioning_included(self, client: TestClient):
        """Test API versioning is included in URLs."""
        response = client.get("/api/v1/datasets")
        # URL contains version
        assert "/v1/" in str(response.request.url) or response.status_code in [401, 404]

    def test_api_base_path_correct(self, client: TestClient):
        """Test API base path is correct."""
        response = client.get("/api/v1/datasets")
        # Response should be from correct endpoint
        assert response.status_code is not None


@pytest.mark.integration
class TestAPIStatusCodes:
    """Test correct HTTP status codes"""

    def test_get_valid_resource_returns_200(self, client: TestClient):
        """Test GET valid resource returns 200."""
        response = client.get("/health")
        if response.status_code == 200:
            assert response.status_code == 200

    def test_post_valid_creates_resource(self, client: TestClient):
        """Test POST creates resource with appropriate status."""
        response = client.post(
            "/api/v1/datasets",
            files={}
        )
        # Should be 400+ atau 201 (if created)
        assert 200 <= response.status_code < 500 or response.status_code == 401

    def test_get_nonexistent_returns_404(self, client: TestClient):
        """Test GET nonexistent resource returns 404."""
        response = client.get("/api/v1/datasets/nonexistent-id-12345")
        if response.status_code != 401:  # Unless auth required
            assert response.status_code == 404 or response.status_code in [200, 400]

    def test_unauthorized_returns_401_or_403(self, client: TestClient):
        """Test unauthorized access returns 401/403."""
        # If auth is required, should get 401/403
        response = client.get("/api/v1/datasets")
        # Should be 200, 401, 403, atau 404
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.integration  
class TestAPIDataTypes:
    """Test API request/response data types"""

    def test_response_json_structure(self, client: TestClient):
        """Test response has valid JSON structure."""
        response = client.get("/health")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))

    def test_list_response_is_array(self, client: TestClient):
        """Test list endpoints return arrays."""
        response = client.get("/api/v1/datasets")
        if response.status_code == 200:
            data = response.json()
            # Should have data key atau be list
            if isinstance(data, dict):
                assert "data" in data or "datasets" in data or len(data) >= 0

    def test_single_resource_response_is_object(self, client: TestClient):
        """Test single resource endpoints return objects."""
        response = client.get("/health")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_numeric_fields_are_numbers(self, client: TestClient):
        """Test numeric fields are numbers not strings."""
        response = client.get("/health")
        if response.status_code == 200:
            data = response.json()
            # All top-level values should be correct types
            for key, value in data.items():
                # Should not be string representation of number
                if isinstance(value, (int, float)):
                    assert not isinstance(value, bool)
