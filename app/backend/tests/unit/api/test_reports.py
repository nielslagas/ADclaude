"""
Unit tests for Reports API endpoints.
Tests all report generation, template management, and export functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime
import json

from fastapi import status
from httpx import AsyncClient

# Test data
@pytest.fixture
def mock_report_data():
    return {
        "id": str(uuid4()),
        "case_id": str(uuid4()),
        "user_id": "test_user",
        "template_id": "staatvandienst",
        "content": {
            "sections": {
                "persoonsgegevens": {
                    "title": "Persoonsgegevens",
                    "content": "Jan de Vries, geboren 15-03-1980"
                },
                "medische_situatie": {
                    "title": "Medische Situatie", 
                    "content": "Chronische rugpijn, hernia L4-L5"
                }
            }
        },
        "status": "generated",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }


@pytest.mark.unit
@pytest.mark.api
class TestReportsAPI:
    """Test cases for Reports API endpoints."""
    
    async def test_get_templates_success(self, async_client: AsyncClient, auth_headers):
        """Test successful retrieval of report templates."""
        with patch('app.api.v1.endpoints.reports.verify_token') as mock_auth:
            mock_auth.return_value = {"user_id": "test_user"}
            
            response = await async_client.get(
                "/api/v1/reports/templates",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            templates = response.json()
            assert "staatvandienst" in templates
            assert templates["staatvandienst"]["name"] == "Staatvandienst Format"
            assert "sections" in templates["staatvandienst"]
    
    
    async def test_get_templates_unauthorized(self, async_client: AsyncClient):
        """Test unauthorized access to templates."""
        response = await async_client.get("/api/v1/reports/templates")
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    
    async def test_create_report_success(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_celery_task):
        """Test successful report creation."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.reports.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.reports.db_service', mock_db_service), \
             patch('app.api.v1.endpoints.reports.celery') as mock_celery:
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_celery.send_task.return_value = Mock(id="task_123")
            mock_db_service.get_case.return_value = {"id": case_id, "user_id": "test_user"}
            
            report_data = {
                "case_id": case_id,
                "template_id": "staatvandienst",
                "sections": ["persoonsgegevens", "medische_situatie"]
            }
            
            response = await async_client.post(
                "/api/v1/reports/generate",
                headers=auth_headers,
                json=report_data
            )
            
            assert response.status_code == status.HTTP_202_ACCEPTED
            result = response.json()
            assert "task_id" in result
            assert result["status"] == "processing"
    
    
    async def test_create_report_case_not_found(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test report creation with non-existent case."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.reports.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.reports.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = None
            
            report_data = {
                "case_id": case_id,
                "template_id": "staatvandienst",
                "sections": ["persoonsgegevens"]
            }
            
            response = await async_client.post(
                "/api/v1/reports/generate",
                headers=auth_headers,
                json=report_data
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Case not found" in response.json()["detail"]
    
    
    async def test_create_report_invalid_template(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test report creation with invalid template."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.reports.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.reports.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = {"id": case_id, "user_id": "test_user"}
            
            report_data = {
                "case_id": case_id,
                "template_id": "invalid_template",
                "sections": ["persoonsgegevens"]
            }
            
            response = await async_client.post(
                "/api/v1/reports/generate",
                headers=auth_headers,
                json=report_data
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Template not found" in response.json()["detail"]
    
    
    async def test_get_report_success(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_report_data):
        """Test successful report retrieval."""
        report_id = mock_report_data["id"]
        
        with patch('app.api.v1.endpoints.reports.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.reports.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_report.return_value = mock_report_data
            
            response = await async_client.get(
                f"/api/v1/reports/{report_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert result["id"] == report_id
            assert result["template_id"] == "staatvandienst"
            assert "sections" in result["content"]
    
    
    async def test_get_report_not_found(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test retrieval of non-existent report."""
        report_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.reports.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.reports.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_report.return_value = None
            
            response = await async_client.get(
                f"/api/v1/reports/{report_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    
    async def test_get_reports_by_case(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_report_data):
        """Test retrieval of reports by case ID."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.reports.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.reports.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case_reports.return_value = [mock_report_data]
            
            response = await async_client.get(
                f"/api/v1/reports/case/{case_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert len(result) == 1
            assert result[0]["id"] == mock_report_data["id"]
    
    
    async def test_update_report_success(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_report_data):
        """Test successful report update."""
        report_id = mock_report_data["id"]
        
        with patch('app.api.v1.endpoints.reports.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.reports.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_report.return_value = mock_report_data
            mock_db_service.update_report.return_value = {**mock_report_data, "status": "revised"}
            
            update_data = {
                "content": {
                    "sections": {
                        "persoonsgegevens": {
                            "title": "Persoonsgegevens",
                            "content": "Updated content"
                        }
                    }
                }
            }
            
            response = await async_client.put(
                f"/api/v1/reports/{report_id}",
                headers=auth_headers,
                json=update_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert result["status"] == "revised"
    
    
    async def test_delete_report_success(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_report_data):
        """Test successful report deletion."""
        report_id = mock_report_data["id"]
        
        with patch('app.api.v1.endpoints.reports.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.reports.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_report.return_value = mock_report_data
            mock_db_service.delete_report.return_value = True
            
            response = await async_client.delete(
                f"/api/v1/reports/{report_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_204_NO_CONTENT
    
    
    async def test_export_report_docx(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_report_data):
        """Test report export to DOCX format."""
        report_id = mock_report_data["id"]
        
        with patch('app.api.v1.endpoints.reports.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.reports.db_service', mock_db_service), \
             patch('app.api.v1.endpoints.reports.FileResponse') as mock_file_response:
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_report.return_value = mock_report_data
            
            # Mock successful file creation
            mock_file_response.return_value = Mock()
            
            response = await async_client.get(
                f"/api/v1/reports/{report_id}/export/docx",
                headers=auth_headers
            )
            
            # For mocked file response, we just check that the endpoint was called correctly
            mock_file_response.assert_called_once()
    
    
    async def test_generate_section_success(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_celery_task):
        """Test successful individual section generation."""
        report_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.reports.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.reports.db_service', mock_db_service), \
             patch('app.api.v1.endpoints.reports.celery') as mock_celery:
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_report.return_value = {"id": report_id, "user_id": "test_user"}
            mock_celery.send_task.return_value = Mock(id="section_task_123")
            
            section_data = {
                "section_id": "medische_situatie",
                "custom_prompt": "Focus on physical limitations"
            }
            
            response = await async_client.post(
                f"/api/v1/reports/{report_id}/sections/generate",
                headers=auth_headers,
                json=section_data
            )
            
            assert response.status_code == status.HTTP_202_ACCEPTED
            result = response.json()
            assert "task_id" in result
            assert result["section_id"] == "medische_situatie"
    
    
    @pytest.mark.parametrize("template_id,expected_sections", [
        ("staatvandienst", ["persoonsgegevens", "werkgever_functie", "aanleiding"]),
        ("invalid_template", None)
    ])
    async def test_template_sections(self, async_client: AsyncClient, auth_headers, template_id, expected_sections):
        """Test template section validation."""
        with patch('app.api.v1.endpoints.reports.verify_token') as mock_auth:
            mock_auth.return_value = {"user_id": "test_user"}
            
            response = await async_client.get(
                "/api/v1/reports/templates",
                headers=auth_headers
            )
            
            templates = response.json()
            
            if expected_sections:
                assert template_id in templates
                template = templates[template_id]
                for section in expected_sections:
                    assert section in template["sections"]
            else:
                assert template_id not in templates
    
    
    @pytest.mark.performance  
    async def test_report_generation_performance(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test report generation performance under load."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.reports.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.reports.db_service', mock_db_service), \
             patch('app.api.v1.endpoints.reports.celery') as mock_celery:
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = {"id": case_id, "user_id": "test_user"}
            mock_celery.send_task.return_value = Mock(id="perf_task")
            
            # Test multiple concurrent requests
            import asyncio
            import time
            
            async def create_report():
                report_data = {
                    "case_id": case_id,
                    "template_id": "staatvandienst",
                    "sections": ["persoonsgegevens", "medische_situatie"]
                }
                
                return await async_client.post(
                    "/api/v1/reports/generate",
                    headers=auth_headers,
                    json=report_data
                )
            
            start_time = time.time()
            tasks = [create_report() for _ in range(5)]
            responses = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # All requests should succeed
            for response in responses:
                assert response.status_code == status.HTTP_202_ACCEPTED
            
            # Performance check - should complete within reasonable time
            total_time = end_time - start_time
            assert total_time < 10.0  # Should complete within 10 seconds
    
    
    async def test_malformed_request_data(self, async_client: AsyncClient, auth_headers):
        """Test handling of malformed request data."""
        with patch('app.api.v1.endpoints.reports.verify_token') as mock_auth:
            mock_auth.return_value = {"user_id": "test_user"}
            
            # Test with invalid JSON
            response = await async_client.post(
                "/api/v1/reports/generate",
                headers=auth_headers,
                content="invalid json"
            )
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    
    async def test_large_report_content(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test handling of large report content."""
        report_id = str(uuid4())
        
        # Create large content (simulate a big report)
        large_content = {
            "sections": {}
        }
        
        for i in range(100):
            large_content["sections"][f"section_{i}"] = {
                "title": f"Section {i}",
                "content": "Very long content " * 1000  # 17KB per section
            }
        
        with patch('app.api.v1.endpoints.reports.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.reports.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_report.return_value = {"id": report_id, "user_id": "test_user"}
            mock_db_service.update_report.return_value = {"id": report_id, "content": large_content}
            
            response = await async_client.put(
                f"/api/v1/reports/{report_id}",
                headers=auth_headers,
                json={"content": large_content}
            )
            
            # Should handle large content without issues
            assert response.status_code == status.HTTP_200_OK