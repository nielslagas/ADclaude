"""
Unit tests for Documents API endpoints.
Tests document upload, processing, and management functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
from uuid import uuid4
from datetime import datetime
import io

from fastapi import status, UploadFile
from httpx import AsyncClient


@pytest.fixture
def mock_upload_file():
    """Mock uploaded file."""
    content = b"Dit is een test document voor arbeidsdeskundige beoordeling.\n\nDe patient heeft rugklachten."
    
    file_mock = Mock(spec=UploadFile)
    file_mock.filename = "test_document.txt"
    file_mock.content_type = "text/plain"
    file_mock.size = len(content)
    file_mock.read = AsyncMock(return_value=content)
    file_mock.file = io.BytesIO(content)
    
    return file_mock


@pytest.fixture
def mock_document_data():
    return {
        "id": str(uuid4()),
        "case_id": str(uuid4()),
        "user_id": "test_user",
        "filename": "test_document.txt",
        "storage_path": "/test/storage/path/test_document.txt",
        "mimetype": "text/plain",
        "size": 1000,
        "status": "uploaded",
        "metadata": {},
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.document
class TestDocumentsAPI:
    """Test cases for Documents API endpoints."""
    
    async def test_upload_document_success(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_celery_task):
        """Test successful document upload."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.documents.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.documents.db_service', mock_db_service), \
             patch('app.api.v1.endpoints.documents.celery') as mock_celery, \
             patch('builtins.open', mock_open()) as mock_file:
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = {"id": case_id, "user_id": "test_user"}
            mock_celery.send_task.return_value = Mock(id="upload_task_123")
            
            # Create test file data
            file_content = b"Test document content"
            files = {"file": ("test.txt", file_content, "text/plain")}
            data = {"case_id": case_id}
            
            response = await async_client.post(
                "/api/v1/documents/upload",
                headers={"Authorization": auth_headers["Authorization"]},
                files=files,
                data=data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            result = response.json()
            assert "id" in result
            assert result["filename"] == "test.txt"
            assert result["status"] == "uploaded"
    
    
    async def test_upload_document_case_not_found(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test document upload with non-existent case."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.documents.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.documents.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = None
            
            file_content = b"Test document content"
            files = {"file": ("test.txt", file_content, "text/plain")}
            data = {"case_id": case_id}
            
            response = await async_client.post(
                "/api/v1/documents/upload",
                headers={"Authorization": auth_headers["Authorization"]},
                files=files,
                data=data
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Case not found" in response.json()["detail"]
    
    
    async def test_upload_document_unauthorized(self, async_client: AsyncClient):
        """Test unauthorized document upload."""
        case_id = str(uuid4())
        
        file_content = b"Test document content"
        files = {"file": ("test.txt", file_content, "text/plain")}
        data = {"case_id": case_id}
        
        response = await async_client.post(
            "/api/v1/documents/upload",
            files=files,
            data=data
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    
    async def test_upload_document_invalid_file_type(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test upload of unsupported file type."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.documents.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.documents.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = {"id": case_id, "user_id": "test_user"}
            
            # Upload unsupported file type
            file_content = b"Binary executable content"
            files = {"file": ("malware.exe", file_content, "application/octet-stream")}
            data = {"case_id": case_id}
            
            response = await async_client.post(
                "/api/v1/documents/upload",
                headers={"Authorization": auth_headers["Authorization"]},
                files=files,
                data=data
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Unsupported file type" in response.json()["detail"]
    
    
    async def test_get_document_success(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_document_data):
        """Test successful document retrieval."""
        document_id = mock_document_data["id"]
        
        with patch('app.api.v1.endpoints.documents.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.documents.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_document.return_value = mock_document_data
            
            response = await async_client.get(
                f"/api/v1/documents/{document_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert result["id"] == document_id
            assert result["filename"] == "test_document.txt"
    
    
    async def test_get_document_not_found(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test retrieval of non-existent document."""
        document_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.documents.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.documents.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_document.return_value = None
            
            response = await async_client.get(
                f"/api/v1/documents/{document_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    
    async def test_get_case_documents(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_document_data):
        """Test retrieval of documents by case ID."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.documents.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.documents.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case_documents.return_value = [mock_document_data]
            
            response = await async_client.get(
                f"/api/v1/documents/case/{case_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert len(result) == 1
            assert result[0]["id"] == mock_document_data["id"]
    
    
    async def test_delete_document_success(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_document_data):
        """Test successful document deletion."""
        document_id = mock_document_data["id"]
        
        with patch('app.api.v1.endpoints.documents.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.documents.db_service', mock_db_service), \
             patch('os.remove') as mock_remove:
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_document.return_value = mock_document_data
            mock_db_service.delete_document.return_value = True
            
            response = await async_client.delete(
                f"/api/v1/documents/{document_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_204_NO_CONTENT
            mock_remove.assert_called_once()  # File should be deleted from storage
    
    
    async def test_get_document_content(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_document_data):
        """Test retrieval of document content."""
        document_id = mock_document_data["id"]
        file_content = "Dit is de inhoud van het test document."
        
        with patch('app.api.v1.endpoints.documents.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.documents.db_service', mock_db_service), \
             patch('builtins.open', mock_open(read_data=file_content)):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_document.return_value = mock_document_data
            
            response = await async_client.get(
                f"/api/v1/documents/{document_id}/content",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert result["content"] == file_content
            assert result["mimetype"] == "text/plain"
    
    
    async def test_update_document_status(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_document_data):
        """Test document status update."""
        document_id = mock_document_data["id"]
        
        with patch('app.api.v1.endpoints.documents.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.documents.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_document.return_value = mock_document_data
            mock_db_service.update_document_status.return_value = {
                **mock_document_data, 
                "status": "processed"
            }
            
            update_data = {"status": "processed"}
            
            response = await async_client.patch(
                f"/api/v1/documents/{document_id}/status",
                headers=auth_headers,
                json=update_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert result["status"] == "processed"
    
    
    async def test_reprocess_document(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_document_data, mock_celery_task):
        """Test document reprocessing trigger."""
        document_id = mock_document_data["id"]
        
        with patch('app.api.v1.endpoints.documents.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.documents.db_service', mock_db_service), \
             patch('app.api.v1.endpoints.documents.celery') as mock_celery:
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_document.return_value = mock_document_data
            mock_celery.send_task.return_value = Mock(id="reprocess_task_123")
            
            response = await async_client.post(
                f"/api/v1/documents/{document_id}/reprocess",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_202_ACCEPTED
            result = response.json()
            assert "task_id" in result
            assert result["status"] == "reprocessing"
    
    
    @pytest.mark.parametrize("file_extension,mimetype,should_succeed", [
        ("txt", "text/plain", True),
        ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", True),
        ("pdf", "application/pdf", True),
        ("jpg", "image/jpeg", False),
        ("exe", "application/octet-stream", False),
        ("js", "application/javascript", False)
    ])
    async def test_file_type_validation(self, async_client: AsyncClient, auth_headers, mock_db_service, 
                                       file_extension, mimetype, should_succeed):
        """Test file type validation for various formats."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.documents.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.documents.db_service', mock_db_service), \
             patch('app.api.v1.endpoints.documents.celery') as mock_celery:
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = {"id": case_id, "user_id": "test_user"}
            mock_celery.send_task.return_value = Mock(id="task_123")
            
            file_content = b"Test file content"
            filename = f"test.{file_extension}"
            files = {"file": (filename, file_content, mimetype)}
            data = {"case_id": case_id}
            
            response = await async_client.post(
                "/api/v1/documents/upload",
                headers={"Authorization": auth_headers["Authorization"]},
                files=files,
                data=data
            )
            
            if should_succeed:
                assert response.status_code == status.HTTP_201_CREATED
            else:
                assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    
    async def test_large_file_upload(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test handling of large file uploads."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.documents.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.documents.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = {"id": case_id, "user_id": "test_user"}
            
            # Create a large file (50MB simulated)
            large_content = b"x" * (50 * 1024 * 1024)  # 50MB
            files = {"file": ("large_file.txt", large_content, "text/plain")}
            data = {"case_id": case_id}
            
            response = await async_client.post(
                "/api/v1/documents/upload",
                headers={"Authorization": auth_headers["Authorization"]},
                files=files,
                data=data
            )
            
            # Should reject files that are too large
            assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    
    
    async def test_concurrent_uploads(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test handling of concurrent document uploads."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.documents.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.documents.db_service', mock_db_service), \
             patch('app.api.v1.endpoints.documents.celery') as mock_celery, \
             patch('builtins.open', mock_open()):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = {"id": case_id, "user_id": "test_user"}
            mock_celery.send_task.return_value = Mock(id="concurrent_task")
            
            import asyncio
            
            async def upload_document(filename):
                file_content = f"Content of {filename}".encode()
                files = {"file": (filename, file_content, "text/plain")}
                data = {"case_id": case_id}
                
                return await async_client.post(
                    "/api/v1/documents/upload",
                    headers={"Authorization": auth_headers["Authorization"]},
                    files=files,
                    data=data
                )
            
            # Test 5 concurrent uploads
            tasks = [upload_document(f"file_{i}.txt") for i in range(5)]
            responses = await asyncio.gather(*tasks)
            
            # All uploads should succeed
            for response in responses:
                assert response.status_code == status.HTTP_201_CREATED
    
    
    async def test_document_metadata_extraction(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test extraction of document metadata."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.documents.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.documents.db_service', mock_db_service), \
             patch('app.api.v1.endpoints.documents.celery') as mock_celery, \
             patch('builtins.open', mock_open()):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = {"id": case_id, "user_id": "test_user"}
            mock_celery.send_task.return_value = Mock(id="metadata_task")
            
            # Mock document creation with metadata extraction
            def mock_create_document(*args, **kwargs):
                return {
                    "id": str(uuid4()),
                    "filename": kwargs.get("filename", "test.txt"),
                    "size": kwargs.get("size", 1000),
                    "mimetype": kwargs.get("mimetype", "text/plain"),
                    "metadata": {
                        "word_count": 150,
                        "character_count": 1000,
                        "language": "dutch",
                        "has_tables": False
                    }
                }
            
            mock_db_service.create_document.side_effect = mock_create_document
            
            file_content = b"Dit is een Nederlands document met medische informatie."
            files = {"file": ("medical_report.txt", file_content, "text/plain")}
            data = {"case_id": case_id}
            
            response = await async_client.post(
                "/api/v1/documents/upload",
                headers={"Authorization": auth_headers["Authorization"]},
                files=files,
                data=data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            result = response.json()
            assert "metadata" in result
            assert result["metadata"]["language"] == "dutch"
    
    
    @pytest.mark.performance
    async def test_document_processing_performance(self, async_client: AsyncClient, auth_headers, mock_db_service, performance_test_documents):
        """Test document processing performance with multiple documents."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.documents.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.documents.db_service', mock_db_service), \
             patch('app.api.v1.endpoints.documents.celery') as mock_celery, \
             patch('builtins.open', mock_open()):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = {"id": case_id, "user_id": "test_user"}
            mock_celery.send_task.return_value = Mock(id="perf_task")
            
            import time
            
            start_time = time.time()
            
            # Upload multiple documents of varying sizes
            for doc in performance_test_documents[:5]:  # Test with first 5 documents
                files = {"file": (doc["filename"], doc["content"].encode(), "text/plain")}
                data = {"case_id": case_id}
                
                response = await async_client.post(
                    "/api/v1/documents/upload",
                    headers={"Authorization": auth_headers["Authorization"]},
                    files=files,
                    data=data
                )
                
                assert response.status_code == status.HTTP_201_CREATED
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Should process multiple documents efficiently
            assert total_time < 5.0  # Should complete within 5 seconds
            
            # Verify all documents were created
            assert mock_db_service.create_document.call_count == 5