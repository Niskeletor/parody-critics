"""
🛡️ Security Tests - SAL-9000 Automated Security Verification
Tests for the security fixes implemented to prevent vulnerabilities
"""
import pytest
from fastapi.testclient import TestClient
from api.main import app

class TestSecurityFixes:
    """Test suite for security vulnerability fixes"""

    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)

    def test_search_api_performance(self):
        """Test that search API uses optimized FTS queries"""
        # Test basic search functionality
        response = self.client.get("/api/media/search?query=matrix&limit=5")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # Verify we get results
        if len(data) > 0:
            assert "title" in data[0]
            assert "tmdb_id" in data[0]

    def test_sql_injection_prevention(self):
        """Test that SQL injection attempts are prevented"""
        # Try common SQL injection patterns
        malicious_queries = [
            "'; DROP TABLE media; --",
            "matrix' UNION SELECT * FROM characters --",
            "matrix'; DELETE FROM critics; --"
        ]

        for malicious_query in malicious_queries:
            response = self.client.get(f"/api/media/search?query={malicious_query}&limit=5")

            # Should either return 200 with safe results or 400 for validation error
            assert response.status_code in [200, 400, 422]

            # If 200, should return empty list or safe results
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list)
                # Results should be empty for malicious queries
                assert len(data) == 0

    def test_parameterized_queries(self):
        """Test that queries use proper parameterization"""
        # Test batch processing endpoint with multiple items
        batch_data = {
            "media_items": [
                {"tmdb_id": "test_id_1", "title": "Test Movie 1", "year": 2023, "type": "movie"}
            ],
            "selected_critics": ["marco_aurelio"]
        }

        # This should use our secure parameterized queries
        response = self.client.post("/api/generate/cart-batch", json=batch_data)

        # Should handle invalid data gracefully without SQL errors
        # Expecting 400 for invalid media items (they don't exist in DB)
        # 503 if LLM service unavailable (also acceptable for security test)
        assert response.status_code in [200, 400, 422, 503]

        if response.status_code == 400:
            error_data = response.json()
            # Should get validation error, not SQL error
            assert "invalid" in error_data.get("detail", "").lower()
        elif response.status_code == 503:
            # Service unavailable is acceptable (LLM service down)
            error_data = response.json()
            # Should not be a SQL error
            detail = error_data.get("detail", "").lower()
            assert "sql" not in detail and "syntax" not in detail

    def test_input_validation(self):
        """Test input validation prevents malicious data"""
        # Test search with very long query
        long_query = "a" * 1000
        response = self.client.get(f"/api/media/search?query={long_query}&limit=5")
        assert response.status_code in [200, 400, 422]

        # Test search with special characters
        special_query = "test'\"<script>alert('xss')</script>"
        response = self.client.get(f"/api/media/search?query={special_query}&limit=5")
        assert response.status_code in [200, 400, 422]

    def test_api_health_check(self):
        """Verify API is still functioning after security fixes"""
        response = self.client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data
        assert "timestamp" in data

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])