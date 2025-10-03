"""
Tests for ADReportSectionGenerator class

This module tests the helper methods of the ADReportSectionGenerator class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.tasks.generate_report_tasks.section_generator import ADReportSectionGenerator


class TestADReportSectionGenerator:
    """Test cases for ADReportSectionGenerator class"""
    
    @pytest.fixture
    def mock_db_service(self):
        """Create a mock database service"""
        mock_db = Mock()
        mock_db.get_document_chunks.return_value = []
        mock_db.get_row_by_id.return_value = {"filename": "test.docx"}
        return mock_db
    
    @pytest.fixture
    def user_profile(self):
        """Create a sample user profile"""
        return {
            "display_name": "Test User",
            "certification": "CRA",
            "registration_number": "12345",
            "company_name": "Test Company"
        }
    
    @pytest.fixture
    def fml_context(self):
        """Create a sample FML context"""
        return {
            "rubrieken": [
                {
                    "rubriek": "I",
                    "naam": "Persoonlijk Functioneren",
                    "items": ["Concentratie", "Geheugen"]
                },
                {
                    "rubriek": "IV",
                    "naam": "Dynamische Handelingen",
                    "items": ["Tillen", "Draaien"]
                }
            ]
        }
    
    @pytest.fixture
    def section_generator(self, mock_db_service, user_profile, fml_context):
        """Create a section generator instance with mocked dependencies"""
        with patch('app.tasks.generate_report_tasks.section_generator.get_database_service', return_value=mock_db_service):
            return ADReportSectionGenerator(user_profile=user_profile, fml_context=fml_context)
    
    @pytest.fixture
    def section_generator_minimal(self, mock_db_service):
        """Create a minimal section generator instance"""
        with patch('app.tasks.generate_report_tasks.section_generator.get_database_service', return_value=mock_db_service):
            return ADReportSectionGenerator()
    
    def test_init_with_user_profile_and_fml_context(self, user_profile, fml_context):
        """Test initialization with user profile and FML context"""
        with patch('app.tasks.generate_report_tasks.section_generator.get_database_service') as mock_get_db:
            generator = ADReportSectionGenerator(user_profile=user_profile, fml_context=fml_context)
            
            assert generator.user_profile == user_profile
            assert generator.fml_context == fml_context
            mock_get_db.assert_called_once()
    
    def test_init_minimal(self):
        """Test initialization with minimal parameters"""
        with patch('app.tasks.generate_report_tasks.section_generator.get_database_service') as mock_get_db:
            generator = ADReportSectionGenerator()
            
            assert generator.user_profile is None
            assert generator.fml_context is None
            mock_get_db.assert_called_once()
    
    def test_check_rag_availability_success(self):
        """Test successful RAG availability check"""
        with patch('app.tasks.generate_report_tasks.section_generator.get_database_service'):
            with patch('app.tasks.generate_report_tasks.section_generator.generate_content_for_section'):
                generator = ADReportSectionGenerator()
                assert generator.has_rag is True
    
    def test_check_rag_availability_failure(self):
        """Test RAG availability check when import fails"""
        with patch('app.tasks.generate_report_tasks.section_generator.get_database_service'):
            with patch('app.tasks.generate_report_tasks.section_generator.generate_content_for_section', side_effect=ImportError):
                generator = ADReportSectionGenerator()
                assert generator.has_rag is False
    
    # Tests for _get_document_content method
    def test_get_document_content_empty_list(self, section_generator):
        """Test _get_document_content with empty document_ids list"""
        result = section_generator._get_document_content([])
        
        assert result == ""
        section_generator.db_service.get_document_chunks.assert_not_called()
    
    def test_get_document_content_valid_ids(self, section_generator, mock_db_service):
        """Test _get_document_content with valid document IDs"""
        # Setup mock responses
        mock_db_service.get_document_chunks.side_effect = [
            [{"content": "Content 1"}],
            [{"content": "Content 2"}]
        ]
        mock_db_service.get_row_by_id.side_effect = [
            {"filename": "doc1.docx"},
            {"filename": "doc2.docx"}
        ]
        
        result = section_generator._get_document_content(["doc1", "doc2"])
        
        # Verify the result contains both documents
        assert "doc1.docx:" in result
        assert "doc2.docx:" in result
        assert "Content 1" in result
        assert "Content 2" in result
        assert "=== DOCUMENT SEPARATOR ===" in result
        
        # Verify database calls
        assert mock_db_service.get_document_chunks.call_count == 2
        assert mock_db_service.get_row_by_id.call_count == 2
    
    def test_get_document_content_no_chunks(self, section_generator, mock_db_service):
        """Test _get_document_content when documents have no chunks"""
        # Setup mock responses
        mock_db_service.get_document_chunks.side_effect = [
            [],  # No chunks for first document
            [{"content": "Content 2"}]  # Chunks for second document
        ]
        mock_db_service.get_row_by_id.side_effect = [
            {"filename": "doc1.docx"},
            {"filename": "doc2.docx"}
        ]
        
        result = section_generator._get_document_content(["doc1", "doc2"])
        
        # Verify only the document with chunks is included
        assert "doc1.docx:" not in result
        assert "doc2.docx:" in result
        assert "Content 2" in result
        assert "Content 1" not in result
    
    def test_get_document_content_missing_filename(self, section_generator, mock_db_service):
        """Test _get_document_content when document has no filename"""
        # Setup mock responses
        mock_db_service.get_document_chunks.return_value = [{"content": "Content"}]
        mock_db_service.get_row_by_id.return_value = {}  # No filename
        
        result = section_generator._get_document_content(["doc1"])
        
        # Verify default filename is used
        assert "Unnamed:" in result
        assert "Content" in result
    
    def test_get_document_content_multiple_chunks(self, section_generator, mock_db_service):
        """Test _get_document_content with multiple chunks per document"""
        # Setup mock responses
        mock_db_service.get_document_chunks.return_value = [
            {"content": "Chunk 1"},
            {"content": "Chunk 2"}
        ]
        mock_db_service.get_row_by_id.return_value = {"filename": "doc1.docx"}
        
        result = section_generator._get_document_content(["doc1"])
        
        # Verify chunks are combined with newlines
        assert "Chunk 1\n\nChunk 2" in result
        assert "doc1.docx:" in result
    
    # Tests for _create_section_prompt method
    @patch('app.tasks.generate_report_tasks.section_generator.create_ad_specific_prompt')
    def test_create_section_prompt_belastbaarheid_with_context(
        self, mock_create_prompt, section_generator, fml_context
    ):
        """Test _create_section_prompt for belastbaarheid section with FML context"""
        # Setup
        section_id = "belastbaarheid"
        section_info = {"title": "Belastbaarheid", "description": "Test section"}
        expected_prompt = "Generated prompt"
        mock_create_prompt.return_value = expected_prompt
        
        # Execute
        result = section_generator._create_section_prompt(section_id, section_info)
        
        # Verify
        assert result == expected_prompt
        mock_create_prompt.assert_called_once_with(
            section_id=section_id,
            section_info=section_info,
            user_profile=section_generator.user_profile,
            fml_context=fml_context
        )
    
    @patch('app.tasks.generate_report_tasks.section_generator.create_ad_specific_prompt')
    def test_create_section_prompt_other_section_no_context(
        self, mock_create_prompt, section_generator
    ):
        """Test _create_section_prompt for non-belastbaarheid section without FML context"""
        # Setup
        section_id = "samenvatting"
        section_info = {"title": "Samenvatting", "description": "Test section"}
        expected_prompt = "Generated prompt"
        mock_create_prompt.return_value = expected_prompt
        
        # Execute
        result = section_generator._create_section_prompt(section_id, section_info)
        
        # Verify
        assert result == expected_prompt
        mock_create_prompt.assert_called_once_with(
            section_id=section_id,
            section_info=section_info,
            user_profile=section_generator.user_profile,
            fml_context=None
        )
    
    @patch('app.tasks.generate_report_tasks.section_generator.create_ad_specific_prompt')
    def test_create_section_prompt_without_user_profile(
        self, mock_create_prompt, section_generator_minimal
    ):
        """Test _create_section_prompt without user profile"""
        # Setup
        section_id = "conclusie"
        section_info = {"title": "Conclusie", "description": "Test section"}
        expected_prompt = "Generated prompt"
        mock_create_prompt.return_value = expected_prompt
        
        # Execute
        result = section_generator_minimal._create_section_prompt(section_id, section_info)
        
        # Verify
        assert result == expected_prompt
        mock_create_prompt.assert_called_once_with(
            section_id=section_id,
            section_info=section_info,
            user_profile=None,
            fml_context=None
        )
    
    @patch('app.tasks.generate_report_tasks.section_generator.create_ad_specific_prompt')
    def test_create_section_prompt_belastbaarheid_without_fml_context(
        self, mock_create_prompt, section_generator_minimal
    ):
        """Test _create_section_prompt for belastbaarheid section without FML context"""
        # Setup
        section_id = "belastbaarheid"
        section_info = {"title": "Belastbaarheid", "description": "Test section"}
        expected_prompt = "Generated prompt"
        mock_create_prompt.return_value = expected_prompt
        
        # Execute
        result = section_generator_minimal._create_section_prompt(section_id, section_info)
        
        # Verify
        assert result == expected_prompt
        mock_create_prompt.assert_called_once_with(
            section_id=section_id,
            section_info=section_info,
            user_profile=None,
            fml_context=None
        )
    
    @patch('app.tasks.generate_report_tasks.section_generator.create_ad_specific_prompt')
    def test_create_section_prompt_with_minimal_section_info(
        self, mock_create_prompt, section_generator
    ):
        """Test _create_section_prompt with minimal section info"""
        # Setup
        section_id = "visie_ad"
        section_info = {}  # Minimal section info
        expected_prompt = "Generated prompt"
        mock_create_prompt.return_value = expected_prompt
        
        # Execute
        result = section_generator._create_section_prompt(section_id, section_info)
        
        # Verify
        assert result == expected_prompt
        mock_create_prompt.assert_called_once_with(
            section_id=section_id,
            section_info=section_info,
            user_profile=section_generator.user_profile,
            fml_context=None
        )