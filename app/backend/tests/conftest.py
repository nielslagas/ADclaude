"""
Test configuration and shared fixtures for AI-Arbeidsdeskundige application.
"""

import pytest
import pytest_asyncio
import asyncio
import os
import sys
from typing import Dict, Any, Generator, AsyncGenerator
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timedelta
import json
import tempfile
from pathlib import Path

# Add app to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import application modules
from app.main import app
from app.core.config import settings
from app.db.database_service import DatabaseService
from app.utils.llm_provider import LLMProvider
from app.utils.vector_store_improved import VectorStoreService
from app.utils.smart_document_classifier import SmartDocumentClassifier
from app.utils.optimized_rag_pipeline import OptimizedRAGPipeline
from app.utils.quality_controller import QualityController
from app.utils.rag_monitoring import RAGMonitoring

# Test client
from httpx import AsyncClient

# Fixtures for database service
@pytest.fixture
def mock_db_service():
    """Mock database service for unit tests."""
    mock_service = Mock(spec=DatabaseService)
    
    # Mock common database operations
    mock_service.create_case.return_value = {
        "id": str(uuid4()),
        "user_id": "test_user",
        "title": "Test Case",
        "description": "Test description",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    mock_service.create_document.return_value = {
        "id": str(uuid4()),
        "case_id": str(uuid4()),
        "user_id": "test_user", 
        "filename": "test_doc.txt",
        "storage_path": "/test/path",
        "mimetype": "text/plain",
        "size": 1000,
        "status": "uploaded",
        "created_at": datetime.utcnow()
    }
    
    mock_service.create_report.return_value = {
        "id": str(uuid4()),
        "case_id": str(uuid4()),
        "user_id": "test_user",
        "template_id": "staatvandienst",
        "content": {"sections": {}},
        "status": "generated",
        "created_at": datetime.utcnow()
    }
    
    mock_service.get_case.return_value = {
        "id": str(uuid4()),
        "user_id": "test_user",
        "title": "Test Case",
        "description": "Test description"
    }
    
    return mock_service


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing."""
    mock_provider = AsyncMock(spec=LLMProvider)
    
    # Mock responses for different providers
    mock_provider.generate_response.return_value = {
        "content": "Test AI response",
        "tokens_used": 150,
        "model": "claude-3-haiku",
        "provider": "anthropic"
    }
    
    mock_provider.generate_embedding.return_value = [0.1] * 1536  # Mock embedding vector
    
    mock_provider.get_available_providers.return_value = ["anthropic", "openai", "google"]
    mock_provider.get_current_provider.return_value = "anthropic"
    
    return mock_provider


@pytest.fixture
def mock_vector_store():
    """Mock vector store service."""
    mock_store = Mock(spec=VectorStoreService)
    
    mock_store.add_embedding.return_value = str(uuid4())
    mock_store.search_similar.return_value = [
        {
            "id": str(uuid4()),
            "content": "Similar content chunk",
            "similarity": 0.85,
            "metadata": {"document_id": str(uuid4()), "chunk_index": 0}
        }
    ]
    
    mock_store.hybrid_search.return_value = {
        "semantic_results": [],
        "keyword_results": [],
        "combined_results": [],
        "strategy_used": "hybrid"
    }
    
    return mock_store


@pytest.fixture
def sample_document_content():
    """Sample Dutch document content for testing."""
    return """
    MEDISCH RAPPORT
    
    Naam: Jan de Vries
    BSN: 123456789
    Geboortedatum: 15-03-1980
    
    DIAGNOSE:
    De patiënt heeft last van chronische rugpijn als gevolg van een hernia nuclei pulposi ter hoogte van L4-L5.
    
    BEPERKINGEN:
    - Maximaal 2 uur per dag zitten
    - Geen tillen boven 5 kg
    - Regelmatige pauzes noodzakelijk
    
    PROGNOSE:
    Met adequate behandeling en aanpassingen is er perspectief op verbetering binnen 6 maanden.
    """


@pytest.fixture
def sample_case_data():
    """Sample case data for testing."""
    return {
        "user_id": "test_user_123",
        "title": "Arbeidsdeskundige beoordeling Jan de Vries", 
        "description": "Beoordeling van arbeidsgeschiktheid na rugletsel",
        "status": "active",
        "client_info": {
            "name": "Jan de Vries",
            "bsn": "123456789",
            "birth_date": "1980-03-15"
        }
    }


@pytest.fixture
def sample_report_template():
    """Sample report template for testing."""
    return {
        "id": "test_template",
        "name": "Test Template",
        "sections": {
            "persoonsgegevens": {
                "title": "Persoonsgegevens",
                "prompt": "Generate personal information section"
            },
            "medische_situatie": {
                "title": "Medische Situatie", 
                "prompt": "Describe medical situation based on documents"
            }
        }
    }


@pytest.fixture
def test_audio_file():
    """Create a temporary test audio file."""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        # Create minimal WAV file header
        f.write(b'RIFF')
        f.write((36).to_bytes(4, 'little'))
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write((16).to_bytes(4, 'little'))
        f.write((1).to_bytes(2, 'little'))  # PCM
        f.write((1).to_bytes(2, 'little'))  # Mono
        f.write((44100).to_bytes(4, 'little'))  # Sample rate
        f.write((88200).to_bytes(4, 'little'))  # Byte rate
        f.write((2).to_bytes(2, 'little'))  # Block align
        f.write((16).to_bytes(2, 'little'))  # Bits per sample
        f.write(b'data')
        f.write((0).to_bytes(4, 'little'))  # Data size
        
        yield f.name
    
    # Cleanup
    os.unlink(f.name)


@pytest.fixture
def test_document_file():
    """Create a temporary test document file."""
    content = "Dit is een test document voor arbeidsdeskundige beoordeling."
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        yield f.name
    
    # Cleanup
    os.unlink(f.name)


@pytest.fixture
async def async_client():
    """Async HTTP client for API testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def auth_headers():
    """Mock authentication headers."""
    return {
        "Authorization": "Bearer test_token_123",
        "Content-Type": "application/json"
    }


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for testing background jobs."""
    with patch('app.celery_worker.celery') as mock_celery:
        mock_task = Mock()
        mock_task.delay.return_value = Mock(id="test_task_id")
        mock_celery.send_task.return_value = mock_task.delay.return_value
        yield mock_task


# RAG and AI-specific fixtures
@pytest.fixture
def mock_document_classifier():
    """Mock smart document classifier."""
    mock_classifier = AsyncMock(spec=SmartDocumentClassifier)
    
    mock_classifier.classify_document.return_value = {
        "type": "medical_report",
        "confidence": 0.95,
        "processing_strategy": "hybrid",
        "metadata": {
            "language": "dutch",
            "sections_detected": ["diagnose", "beperkingen"],
            "estimated_tokens": 500
        }
    }
    
    return mock_classifier


@pytest.fixture
def mock_rag_pipeline():
    """Mock optimized RAG pipeline."""
    mock_pipeline = AsyncMock(spec=OptimizedRAGPipeline)
    
    mock_pipeline.process_query.return_value = {
        "response": "Generated RAG response based on documents",
        "sources": [
            {"document_id": str(uuid4()), "chunk_index": 0, "relevance": 0.9}
        ],
        "confidence": 0.85,
        "tokens_used": 200,
        "processing_time": 1.5
    }
    
    return mock_pipeline


@pytest.fixture
def mock_quality_controller():
    """Mock quality controller."""
    mock_quality = AsyncMock(spec=QualityController)
    
    mock_quality.validate_content.return_value = {
        "is_valid": True,
        "quality_score": 0.88,
        "issues": [],
        "suggestions": ["Consider adding more specific details"],
        "confidence": 0.92
    }
    
    return mock_quality


@pytest.fixture
def mock_monitoring():
    """Mock RAG monitoring service."""
    mock_monitor = Mock(spec=RAGMonitoring)
    
    mock_monitor.log_operation.return_value = None
    mock_monitor.get_metrics.return_value = {
        "total_operations": 100,
        "success_rate": 0.95,
        "avg_response_time": 2.3,
        "token_usage": {"total": 50000, "avg_per_operation": 500}
    }
    
    return mock_monitor


# Performance testing fixtures
@pytest.fixture
def performance_test_documents():
    """Generate multiple test documents for performance testing."""
    documents = []
    
    for i in range(10):
        doc_content = f"""
        Document {i + 1}
        
        Dit is een test document voor performance testing.
        Het bevat meerdere paragrafen met Nederlandse tekst.
        
        Sectie A: Algemene informatie
        Deze sectie bevat algemene informatie over de casus.
        
        Sectie B: Medische gegevens  
        Hier staan de medische gegevens beschreven.
        
        Sectie C: Conclusies
        Ten slotte worden hier de conclusies gepresenteerd.
        """ * (i + 1)  # Make each document progressively larger
        
        documents.append({
            "filename": f"test_doc_{i + 1}.txt",
            "content": doc_content,
            "size": len(doc_content.encode('utf-8'))
        })
    
    return documents


# Environment and configuration fixtures
@pytest.fixture(scope="session", autouse=True)
def test_settings():
    """Override settings for testing."""
    # Set test-specific configuration
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test_db"
    os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/1"
    
    yield
    
    # Cleanup
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


@pytest.fixture(autouse=True)
def isolate_tests():
    """Isolate tests by mocking external dependencies."""
    with patch('app.utils.llm_provider.get_llm_provider') as mock_llm, \
         patch('app.db.database_service.get_database_service') as mock_db:
        
        # Setup default mocks
        mock_llm.return_value = AsyncMock()
        mock_db.return_value = Mock()
        
        yield {
            'llm_provider': mock_llm,
            'db_service': mock_db
        }


# Utility functions for tests
def assert_valid_uuid(uuid_string: str) -> bool:
    """Utility to validate UUID format."""
    try:
        UUID(uuid_string)
        return True
    except (ValueError, TypeError):
        return False


def assert_dutch_content(text: str) -> bool:
    """Utility to check if content contains Dutch language elements."""
    dutch_indicators = [
        "de", "het", "een", "van", "en", "in", "op", "met", "voor", "door",
        "arbeidsdeskundige", "rapport", "beoordeling", "medisch", "diagnose"
    ]
    text_lower = text.lower()
    return any(indicator in text_lower for indicator in dutch_indicators)


def create_mock_response(content: str, status_code: int = 200) -> Mock:
    """Create a mock HTTP response."""
    response = Mock()
    response.status_code = status_code
    response.json.return_value = {"content": content}
    response.text = content
    return response