import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.db.database_service import DatabaseService
from app.utils.llm_provider import LLMProvider

class TestHeaderFixEndToEnd:
    """Integration tests for document upload to report generation with header fixes"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
        self.test_user_id = "test-user-123"
        self.test_case_id = "test-case-456"
        
        # Mock document content that would cause header issues
        self.problematic_document_content = """
# Medisch rapport

Patiënt: Jan de Vries
Geboortedatum: 01-01-1980

## Huidige klachten

De patiënt heeft rugklachten sinds 6 maanden.

### Fysiek onderzoek

Beperkte mobiliteit in de onderrug.

#### Behandeling

Fysiotherapie wordt aanbevolen.

##### Prognose

Verwachte herstel binnen 3 maanden.

###### Follow-up

Controle over 6 weken.
        """
        
        # Expected LLM responses (with headers that should be filtered by frontend)
        self.mock_llm_responses = {
            "samenvatting": """
# Samenvatting

De heer Jan de Vries is een 43-jarige man die rugklachten heeft ontwikkeld.

## Situatie

Hij is werkzaam als magazijnmedewerker en heeft beperkte mobiliteit.

### Conclusie

Geleidelijke werkhervatting wordt aanbevolen.
            """,
            "belastbaarheid": """
# Belastbaarheidsanalyse

<h1>Fysieke belastbaarheid</h1>

**Tillen:** Maximaal 10 kg

<h2>Mentale belastbaarheid</h2>

Geen beperkingen geconstateerd.
            """,
            "visie_ad": """
## Arbeidsdeskundige visie

**Professionele beoordeling:** De cliënt heeft goede vooruitzichten.

### Aanbevelingen

- Geleidelijke opbouw
- Werkplek aanpassingen
            """,
            "matching": """
# Matching criteria

<h3>Fysieke eisen</h3>

(E) Licht fysiek werk

<h1>Werkomgeving</h1>

(W) Flexibele werktijden
            """
        }
        
    @pytest.fixture
    def mock_database(self):
        """Mock database service"""
        with patch('app.db.database_service.DatabaseService') as mock_db:
            db_instance = Mock()
            mock_db.return_value = db_instance
            
            # Mock database operations
            db_instance.create_case.return_value = {'id': self.test_case_id}
            db_instance.upload_document.return_value = {'id': 'doc-123'}
            db_instance.create_report.return_value = {'id': 'report-789'}
            db_instance.get_case_documents.return_value = [
                {'id': 'doc-123', 'content': self.problematic_document_content}
            ]
            
            yield db_instance
            
    @pytest.fixture 
    def mock_llm(self):
        """Mock LLM provider"""
        with patch('app.utils.llm_provider.LLMProvider') as mock_provider:
            llm_instance = Mock()
            mock_provider.return_value = llm_instance
            
            def generate_response(prompt, **kwargs):
                # Determine section based on prompt content
                if "samenvatting" in prompt.lower():
                    return self.mock_llm_responses["samenvatting"]
                elif "belastbaarheid" in prompt.lower():
                    return self.mock_llm_responses["belastbaarheid"]
                elif "visie" in prompt.lower():
                    return self.mock_llm_responses["visie_ad"]
                elif "matching" in prompt.lower():
                    return self.mock_llm_responses["matching"]
                else:
                    return "Generic response"
                    
            llm_instance.generate_text.side_effect = generate_response
            yield llm_instance
            
    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store"""
        with patch('app.utils.vector_store_improved.VectorStoreImproved') as mock_vs:
            vs_instance = Mock()
            mock_vs.return_value = vs_instance
            
            # Mock vector search results
            vs_instance.search.return_value = [
                {'content': self.problematic_document_content, 'score': 0.95}
            ]
            
            yield vs_instance
            
    def test_document_upload_with_headers(self, mock_database, mock_vector_store):
        """Test document upload containing various header types"""
        # Create a temporary file with problematic content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(self.problematic_document_content)
            temp_file_path = temp_file.name
            
        try:
            with open(temp_file_path, 'rb') as file:
                response = self.client.post(
                    f"/api/v1/documents/upload",
                    files={"file": ("test_document.txt", file, "text/plain")},
                    data={"case_id": self.test_case_id}
                )
                
            assert response.status_code == 200
            upload_result = response.json()
            assert "id" in upload_result
            
            # Verify document was stored (mock should have been called)
            mock_database.upload_document.assert_called_once()
            
        finally:
            os.unlink(temp_file_path)
            
    def test_report_generation_with_header_prevention(self, mock_database, mock_llm, mock_vector_store):
        """Test full report generation with header prevention measures"""
        # Test report generation endpoint
        response = self.client.post(
            f"/api/v1/reports/generate",
            json={
                "case_id": self.test_case_id,
                "sections": ["samenvatting", "belastbaarheid", "visie_ad", "matching"]
            }
        )
        
        assert response.status_code == 200
        report_result = response.json()
        
        # Verify all sections were generated
        assert "content" in report_result
        content = report_result["content"]
        
        # Verify all expected sections are present
        expected_sections = ["samenvatting", "belastbaarheid", "visie_ad", "matching"]
        for section in expected_sections:
            assert section in content
            assert len(content[section]) > 0
            
        # Verify LLM was called for each section
        assert mock_llm.generate_text.call_count == len(expected_sections)
        
        # Verify prompts contained BELANGRIJK instructions
        for call in mock_llm.generate_text.call_args_list:
            prompt = call[0][0]  # First argument is the prompt
            assert "BELANGRIJK:" in prompt
            assert "Schrijf GEEN koppen, titels, headers" in prompt
            
    def test_report_content_structure(self, mock_database, mock_llm, mock_vector_store):
        """Test that generated report content follows expected structure"""
        response = self.client.post(
            f"/api/v1/reports/generate",
            json={
                "case_id": self.test_case_id,
                "sections": ["samenvatting", "belastbaarheid"]
            }
        )
        
        assert response.status_code == 200
        report_result = response.json()
        content = report_result["content"]
        
        # Check that content contains expected information (with headers from LLM)
        samenvatting = content["samenvatting"]
        assert "Jan de Vries" in samenvatting
        assert "rugklachten" in samenvatting
        
        belastbaarheid = content["belastbaarheid"]
        assert "Maximaal 10 kg" in belastbaarheid
        assert "Geen beperkingen" in belastbaarheid
        
        # Headers are present in backend response (will be filtered by frontend)
        assert "#" in samenvatting or "<h" in samenvatting
        assert "#" in belastbaarheid or "<h" in belastbaarheid
        
    def test_multiple_document_processing(self, mock_database, mock_llm, mock_vector_store):
        """Test processing multiple documents with various header formats"""
        # Mock multiple documents with different header styles
        documents = [
            {
                'id': 'doc-1',
                'content': '# Document 1\n\nContent with markdown headers.'
            },
            {
                'id': 'doc-2', 
                'content': '<h1>Document 2</h1>\n\nContent with HTML headers.'
            },
            {
                'id': 'doc-3',
                'content': '**Title Document:**\n\nContent with bold headers.'
            }
        ]
        
        mock_database.get_case_documents.return_value = documents
        
        response = self.client.post(
            f"/api/v1/reports/generate",
            json={
                "case_id": self.test_case_id,
                "sections": ["samenvatting"]
            }
        )
        
        assert response.status_code == 200
        report_result = response.json()
        
        # Verify content was generated
        assert "content" in report_result
        assert "samenvatting" in report_result["content"]
        
        # Verify LLM received combined context from all documents
        mock_llm.generate_text.assert_called()
        prompt_used = mock_llm.generate_text.call_args[0][0]
        
        # Context should contain information from multiple documents
        assert len(prompt_used) > 500  # Should be substantial with multiple docs
        
    def test_error_handling_malformed_documents(self, mock_database, mock_llm, mock_vector_store):
        """Test handling of documents with malformed headers"""
        malformed_content = """
        #Not a proper header
        ##Also not proper  
        ### This one is ok
        ####Not proper again
        
        <h1>Good HTML header</h1>
        <h2 class="test">Header with attributes</h2>
        <h3>Unclosed header
        
        **Good bold title:**
        **Not a title because no colon**
        """
        
        mock_database.get_case_documents.return_value = [
            {'id': 'doc-malformed', 'content': malformed_content}
        ]
        
        response = self.client.post(
            f"/api/v1/reports/generate",
            json={
                "case_id": self.test_case_id,
                "sections": ["samenvatting"]
            }
        )
        
        # Should handle malformed content gracefully
        assert response.status_code == 200
        report_result = response.json()
        assert "content" in report_result
        
    def test_template_rendering_integration(self, mock_database, mock_llm, mock_vector_store):
        """Test that backend generates content compatible with all template types"""
        response = self.client.post(
            f"/api/v1/reports/generate",
            json={
                "case_id": self.test_case_id,
                "sections": ["samenvatting", "belastbaarheid", "visie_ad", "matching"]
            }
        )
        
        assert response.status_code == 200
        report_result = response.json()
        content = report_result["content"]
        
        # Test that content works with all template types
        template_types = ["standaard", "modern", "professioneel", "compact"]
        
        for template_type in template_types:
            # Get report with template specification
            template_response = self.client.get(
                f"/api/v1/reports/{report_result['id']}?template={template_type}"
            )
            
            # Should work with all template types
            assert template_response.status_code == 200
            
    def test_performance_with_large_documents(self, mock_database, mock_llm, mock_vector_store):
        """Test performance with large documents containing many headers"""
        # Create large document with many headers
        large_content = ""
        for i in range(100):
            large_content += f"\n\n# Header {i}\n\nContent section {i} with important information.\n"
            large_content += f"\n## Subheader {i}\n\nMore detailed content here.\n"
            
        mock_database.get_case_documents.return_value = [
            {'id': 'large-doc', 'content': large_content}
        ]
        
        import time
        start_time = time.time()
        
        response = self.client.post(
            f"/api/v1/reports/generate",
            json={
                "case_id": self.test_case_id,
                "sections": ["samenvatting"]
            }
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert processing_time < 30  # 30 seconds max
        assert response.status_code == 200
        
    def test_concurrent_report_generation(self, mock_database, mock_llm, mock_vector_store):
        """Test concurrent report generation with header fixes"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def generate_report(case_id):
            response = self.client.post(
                f"/api/v1/reports/generate",
                json={
                    "case_id": case_id,
                    "sections": ["samenvatting"]
                }
            )
            results.put((case_id, response.status_code, response.json()))
            
        # Start multiple concurrent requests
        threads = []
        for i in range(3):
            thread = threading.Thread(target=generate_report, args=(f"case-{i}",))
            threads.append(thread)
            thread.start()
            
        # Wait for all threads
        for thread in threads:
            thread.join()
            
        # Check all requests succeeded
        assert results.qsize() == 3
        while not results.empty():
            case_id, status_code, response_data = results.get()
            assert status_code == 200
            assert "content" in response_data
            
    def test_regression_existing_functionality(self, mock_database, mock_llm, mock_vector_store):
        """Test that existing functionality still works after header fixes"""
        # Test case creation
        case_response = self.client.post(
            "/api/v1/cases/",
            json={
                "title": "Test Case",
                "description": "Regression test case"
            }
        )
        assert case_response.status_code == 200
        
        # Test document upload
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write("Simple test content without headers.")
            temp_file_path = temp_file.name
            
        try:
            with open(temp_file_path, 'rb') as file:
                upload_response = self.client.post(
                    f"/api/v1/documents/upload",
                    files={"file": ("simple.txt", file, "text/plain")},
                    data={"case_id": self.test_case_id}
                )
            assert upload_response.status_code == 200
            
        finally:
            os.unlink(temp_file_path)
            
        # Test report generation
        report_response = self.client.post(
            f"/api/v1/reports/generate",
            json={
                "case_id": self.test_case_id,
                "sections": ["samenvatting"]
            }
        )
        assert report_response.status_code == 200
        
        # Verify basic structure is maintained
        report_data = report_response.json()
        assert "id" in report_data
        assert "content" in report_data
        assert "created_at" in report_data
