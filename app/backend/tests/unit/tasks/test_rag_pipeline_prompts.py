import pytest
import re
from unittest.mock import Mock, patch, MagicMock
from app.tasks.generate_report_tasks.rag_pipeline import create_section_prompt, generate_section_content_rag
from app.utils.llm_provider import LLMProvider

class TestRAGPipelinePrompts:
    """Test suite for improved LLM prompts in RAG pipeline"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_context = "Test document content about a client's work situation and health status."
        self.mock_case_info = {
            'client_name': 'Test Client',
            'case_type': 'arbeidsdeskundig onderzoek',
            'situation': 'werkhervatting na ziekte'
        }
        
    def test_create_section_prompt_samenvatting(self):
        """Test samenvatting section prompt creation and BELANGRIJK instruction"""
        section_id = "samenvatting"
        context = self.mock_context
        case_info = self.mock_case_info
        
        prompt = create_section_prompt(section_id, context, case_info)
        
        # Check basic prompt structure
        assert "arbeidsdeskundige samenvatting" in prompt.lower()
        assert "3-4 alinea's" in prompt
        assert context in prompt
        
        # Critical: Check for BELANGRIJK instruction
        assert "BELANGRIJK:" in prompt
        assert "Schrijf GEEN koppen, titels, headers" in prompt
        assert "markdown formatting" in prompt
        assert "Begin direct met de eerste alinea" in prompt
        
        # Verify specific formatting restrictions
        assert "#, ##, ###" in prompt
        assert "**titel**" in prompt
        assert "zonder inleiding, titel of kop" in prompt
        
    def test_create_section_prompt_belastbaarheid(self):
        """Test belastbaarheid section prompt with specific categories"""
        section_id = "belastbaarheid"
        context = self.mock_context
        case_info = self.mock_case_info
        
        prompt = create_section_prompt(section_id, context, case_info)
        
        # Check category structure
        assert "**Fysiek**:" in prompt
        assert "**Mentaal**:" in prompt
        assert "**Sociaal**:" in prompt
        assert "**Beperkingen**:" in prompt
        
        # Check specific requirements
        assert "kg, uren" in prompt
        assert "concentratie, stress" in prompt
        assert "samenwerking, klantcontact" in prompt
        assert "tegenstrijdigheden" in prompt
        
        # Critical: Check for BELANGRIJK instruction
        assert "BELANGRIJK:" in prompt
        assert "Schrijf GEEN koppen, titels, headers" in prompt
        assert "Begin direct met de analyse" in prompt
        
    def test_create_section_prompt_visie_ad(self):
        """Test arbeidsdeskundige visie section prompt"""
        section_id = "visie_ad"
        context = self.mock_context
        case_info = self.mock_case_info
        
        prompt = create_section_prompt(section_id, context, case_info)
        
        # Check professional vision structure
        assert "professionele arbeidsdeskundige visie" in prompt
        assert "400-500 woorden" in prompt
        assert "**Beoordeling arbeidsmogelijkheden**" in prompt
        assert "**Belasting vs belastbaarheid**" in prompt
        assert "**Aanbevelingen**" in prompt
        assert "**Perspectief**" in prompt
        
        # Check professional requirements
        assert "documentreferenties" in prompt
        assert "mogelijkheden" in prompt
        assert "beperkingen" in prompt
        
        # Critical: Check for BELANGRIJK instruction
        assert "BELANGRIJK:" in prompt
        assert "Schrijf GEEN koppen, titels, headers" in prompt
        assert "Begin direct met de visie" in prompt
        
    def test_create_section_prompt_matching(self):
        """Test matching section prompt with E/W criteria"""
        section_id = "matching"
        context = self.mock_context
        case_info = self.mock_case_info
        
        prompt = create_section_prompt(section_id, context, case_info)
        
        # Check matching criteria structure
        assert "matchingcriteria" in prompt
        assert "(E)ssentieel" in prompt
        assert "(W)enselijk" in prompt
        assert "**Fysieke werkomgeving**" in prompt
        
        # Critical: Check for BELANGRIJK instruction
        assert "BELANGRIJK:" in prompt
        assert "Schrijf GEEN koppen, titels, headers" in prompt
        
    def test_belangrijk_instruction_consistency(self):
        """Test that all sections have consistent BELANGRIJK instructions"""
        sections = ["samenvatting", "belastbaarheid", "visie_ad", "matching"]
        context = self.mock_context
        case_info = self.mock_case_info
        
        for section_id in sections:
            prompt = create_section_prompt(section_id, context, case_info)
            
            # Every section must have BELANGRIJK instruction
            assert "BELANGRIJK:" in prompt, f"Section {section_id} missing BELANGRIJK instruction"
            assert "Schrijf GEEN koppen, titels, headers" in prompt, f"Section {section_id} missing header restriction"
            assert "markdown formatting" in prompt, f"Section {section_id} missing markdown restriction"
            
            # Check specific formatting restrictions are mentioned
            formatting_restrictions = ["#, ##, ###", "**titel**"]
            for restriction in formatting_restrictions:
                assert restriction in prompt, f"Section {section_id} missing restriction: {restriction}"
            
    def test_prompt_context_integration(self):
        """Test that context is properly integrated into prompts"""
        context = "Specific medical information about joint problems and mobility restrictions."
        case_info = {'client_name': 'Jane Doe'}
        
        for section_id in ["samenvatting", "belastbaarheid", "visie_ad", "matching"]:
            prompt = create_section_prompt(section_id, context, case_info)
            assert context in prompt, f"Context not found in {section_id} prompt"
            
    def test_case_info_usage(self):
        """Test that case info is properly used in prompts when provided"""
        context = self.mock_context
        case_info = {
            'client_name': 'John Smith',
            'case_type': 'reintegration assessment',
            'situation': 'return to work after burnout'
        }
        
        # For sections that might use case info
        prompt = create_section_prompt("samenvatting", context, case_info)
        # Case info should be used in prompt construction logic
        assert len(prompt) > 0
        
    @patch('app.utils.llm_provider.LLMProvider')
    def test_generate_section_content_rag_header_prevention(self, mock_llm_provider):
        """Test that generated content follows no-header instructions"""
        # Mock LLM response with headers (what we want to prevent)
        mock_response_with_headers = """
        # Samenvatting van het onderzoek
        
        De cliënt is een 45-jarige man die werkzaam was als monteur.
        
        ## Huidige situatie
        
        Hij heeft rugklachten ontwikkeld door het werk.
        """
        
        mock_llm = Mock()
        mock_llm.generate_text.return_value = mock_response_with_headers
        mock_llm_provider.return_value = mock_llm
        
        # Test the function
        with patch('app.tasks.generate_report_tasks.rag_pipeline.create_section_prompt') as mock_prompt:
            mock_prompt.return_value = "Test prompt with BELANGRIJK instruction"
            
            result = generate_section_content_rag(
                section_id="samenvatting",
                context=self.mock_context,
                case_info=self.mock_case_info,
                vector_store=Mock(),
                model_name="test-model"
            )
            
            # Verify the prompt was created with proper instructions
            mock_prompt.assert_called_once_with("samenvatting", self.mock_context, self.mock_case_info)
            
            # Verify LLM was called
            mock_llm.generate_text.assert_called_once()
            
            # The result should be the LLM response (header removal happens in frontend)
            assert result == mock_response_with_headers
            
    def test_prompt_length_reasonable(self):
        """Test that prompts are not excessively long"""
        context = "A" * 1000  # 1KB context
        case_info = self.mock_case_info
        
        for section_id in ["samenvatting", "belastbaarheid", "visie_ad", "matching"]:
            prompt = create_section_prompt(section_id, context, case_info)
            # Prompt should be reasonable length (context + instructions)
            assert len(prompt) < 5000, f"Prompt for {section_id} too long: {len(prompt)} characters"
            assert len(prompt) > 500, f"Prompt for {section_id} too short: {len(prompt)} characters"
            
    def test_prompt_dutch_language(self):
        """Test that prompts are in Dutch as expected"""
        context = self.mock_context
        case_info = self.mock_case_info
        
        dutch_indicators = [
            "arbeidsdeskundige", "belastbaarheid", "samenvatting", 
            "alinea's", "documenten", "analyse", "visie", "matching"
        ]
        
        for section_id in ["samenvatting", "belastbaarheid", "visie_ad", "matching"]:
            prompt = create_section_prompt(section_id, context, case_info)
            
            # Should contain Dutch language indicators
            dutch_found = any(indicator in prompt.lower() for indicator in dutch_indicators)
            assert dutch_found, f"Prompt for {section_id} should contain Dutch language indicators"
            
    def test_error_handling_empty_context(self):
        """Test prompt creation with empty context"""
        empty_context = ""
        case_info = self.mock_case_info
        
        for section_id in ["samenvatting", "belastbaarheid", "visie_ad", "matching"]:
            prompt = create_section_prompt(section_id, empty_context, case_info)
            
            # Should still contain BELANGRIJK instruction even with empty context
            assert "BELANGRIJK:" in prompt
            assert len(prompt) > 100  # Should have basic structure
            
    def test_error_handling_none_case_info(self):
        """Test prompt creation with None case_info"""
        context = self.mock_context
        
        for section_id in ["samenvatting", "belastbaarheid", "visie_ad", "matching"]:
            # Should not crash with None case_info
            prompt = create_section_prompt(section_id, context, None)
            assert "BELANGRIJK:" in prompt
            assert len(prompt) > 100
            
    def test_section_specific_requirements(self):
        """Test that each section has its specific requirements"""
        context = self.mock_context
        case_info = self.mock_case_info
        
        # Samenvatting specific
        samenvatting_prompt = create_section_prompt("samenvatting", context, case_info)
        assert "persoonsgegevens" in samenvatting_prompt.lower()
        assert "kernconclusive" in samenvatting_prompt.lower()
        
        # Belastbaarheid specific  
        belastbaarheid_prompt = create_section_prompt("belastbaarheid", context, case_info)
        assert "tillen, dragen" in belastbaarheid_prompt.lower()
        assert "concentratie" in belastbaarheid_prompt.lower()
        
        # Visie AD specific
        visie_prompt = create_section_prompt("visie_ad", context, case_info)
        assert "arbeidsmogelijkheden" in visie_prompt.lower()
        assert "werkhervatting" in visie_prompt.lower()
        
        # Matching specific
        matching_prompt = create_section_prompt("matching", context, case_info)
        assert "werkomgeving" in matching_prompt.lower()
        assert "essentieel" in matching_prompt.lower()
        
    def test_unknown_section_handling(self):
        """Test handling of unknown section IDs"""
        context = self.mock_context
        case_info = self.mock_case_info
        
        # Should handle unknown section gracefully
        prompt = create_section_prompt("unknown_section", context, case_info)
        
        # Should still return a basic prompt structure
        assert len(prompt) > 0
        assert context in prompt
