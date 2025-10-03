"""
AD Report Section Generator

This module provides a class-based approach to generating individual sections
of an Arbeidsdeskundig (AD) report with improved maintainability and testability.
"""

import asyncio
from typing import Dict, Any, List, Optional
from app.db.database_service import get_database_service


class ADReportSectionGenerator:
    """
    Handles generation of individual AD report sections with specialized
    prompts and content generation strategies.
    """
    
    def __init__(self, user_profile: Optional[Dict[str, Any]] = None, fml_context: Optional[Dict[str, Any]] = None, extracted_fields: Optional[Dict[str, str]] = None):
        """
        Initialize the section generator.

        Args:
            user_profile: User profile information
            fml_context: FML rubrieken context
            extracted_fields: Extracted structured fields from documents
        """
        self.user_profile = user_profile
        self.fml_context = fml_context
        self.extracted_fields = extracted_fields or {}
        self.db_service = get_database_service()
        self.has_rag = self._check_rag_availability()
    
    def _check_rag_availability(self) -> bool:
        """
        Check if RAG pipeline is available.
        
        Returns:
            True if RAG pipeline is available, False otherwise
        """
        try:
            from app.tasks.generate_report_tasks.rag_pipeline import generate_content_for_section
            return True
        except Exception:
            return False
    
    def generate_section(
        self, 
        section_id: str, 
        section_info: Dict[str, Any], 
        document_ids: List[str], 
        case_id: str
    ) -> Dict[str, Any]:
        """
        Generate content for a specific section.
        
        Args:
            section_id: ID of the section to generate
            section_info: Section metadata from template
            document_ids: List of document IDs to use
            case_id: ID of the case
            
        Returns:
            Dictionary with content, approach used, and metadata
        """
        # Create section prompt
        prompt = self._create_section_prompt(section_id, section_info)
        
        # Try RAG approach first
        result = self._try_rag_generation(
            section_id, section_info, document_ids, case_id
        )
        
        # Fallback to direct LLM if RAG fails
        if not result["content"]:
            result = self._try_direct_llm_generation(
                section_id, section_info, document_ids, prompt
            )
        
        # Add metadata
        result["section_id"] = section_id
        result["title"] = section_info.get("title", section_id)
        result["order"] = section_info.get("order", 999)
        
        return result
    
    def _create_section_prompt(self, section_id: str, section_info: Dict[str, Any]) -> str:
        """
        Create a specialized prompt for the section.
        
        Args:
            section_id: ID of the section
            section_info: Section metadata
            
        Returns:
            Specialized prompt for the section
        """
        # Import the prompt creation function
        from app.tasks.generate_report_tasks.ad_report_task import create_ad_specific_prompt
        
        # Create section-specific context
        section_context = None
        if section_id == "belastbaarheid":
            section_context = self.fml_context
        
        # Create specialized prompt
        return create_ad_specific_prompt(
            section_id=section_id,
            section_info=section_info,
            user_profile=self.user_profile,
            fml_context=section_context,
            extracted_fields=self.extracted_fields
        )
    
    def _try_rag_generation(
        self, 
        section_id: str, 
        section_info: Dict[str, Any], 
        document_ids: List[str], 
        case_id: str
    ) -> Dict[str, Any]:
        """
        Try to generate content using RAG approach.
        
        Args:
            section_id: ID of the section
            section_info: Section metadata
            document_ids: List of document IDs
            case_id: ID of the case
            
        Returns:
            Dictionary with content and approach used
        """
        if not self.has_rag:
            return {"content": None, "approach": "rag_unavailable"}
        
        try:
            # Use async RAG pipeline (lines 500-520 in ad_report_task.py)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Import RAG function (line 504)
                from app.tasks.generate_report_tasks.rag_pipeline import generate_content_for_section
                
                # Call RAG pipeline (lines 503-511)
                section_result = loop.run_until_complete(
                    generate_content_for_section(
                        section_id=section_id,
                        section_info=section_info,
                        document_ids=document_ids,
                        case_id=case_id,
                        user_profile=self.user_profile
                    )
                )
                
                # Return result (lines 512-517)
                return {
                    "content": section_result["content"],
                    "approach": "enhanced_rag",
                    "fml_generated": section_id == "belastbaarheid"
                }
            finally:
                loop.close()
                
        except Exception as rag_error:
            # Handle RAG error (lines 522-524)
            print(f"Enhanced RAG failed for {section_id}: {str(rag_error)}")
            return {"content": None, "approach": "rag_failed"}
    
    def _try_direct_llm_generation(
        self, 
        section_id: str, 
        section_info: Dict[str, Any], 
        document_ids: List[str], 
        prompt: str
    ) -> Dict[str, Any]:
        """
        Try to generate content using direct LLM approach.
        
        Args:
            section_id: ID of the section
            section_info: Section metadata
            document_ids: List of document IDs
            prompt: Section-specific prompt
            
        Returns:
            Dictionary with content and approach used
        """
        try:
            # Get document content (lines 529-543)
            document_content = self._get_document_content(document_ids)
            
            # Generate content directly with LLM (lines 545-561)
            from app.utils.llm_provider import create_llm_instance
            
            model = create_llm_instance(
                temperature=0.2,  # Increased for Haiku
                max_tokens=3072,  # Haiku can handle more tokens faster
                dangerous_content_level="BLOCK_NONE"
            )
            
            full_prompt = f"{prompt}\n\nDocumenten:\n{document_content}"
            response = model.generate_content([
                {"role": "system", "parts": ["Je bent een ervaren arbeidsdeskundige die professionele rapporten schrijft."]},
                {"role": "user", "parts": [full_prompt]}
            ])
            
            content = response.text if hasattr(response, 'text') else str(response)
            
            # Return result (lines 562-566)
            return {
                "content": content,
                "approach": "enhanced_direct",
                "fml_generated": section_id == "belastbaarheid"
            }
            
        except Exception as direct_error:
            # Handle direct LLM error (lines 568-571)
            print(f"Direct LLM approach failed for {section_id}: {str(direct_error)}")
            return {
                "content": f"Sectie '{section_info.get('title', section_id)}' kon niet gegenereerd worden. Handmatige invulling vereist.",
                "approach": "error_fallback"
            }
    
    def _get_document_content(self, document_ids: List[str]) -> str:
        """
        Get combined content from documents.
        
        Args:
            document_ids: List of document IDs
            
        Returns:
            Combined document content
        """
        # Get document content for context (lines 530-543)
        full_documents = []
        for doc_id in document_ids:
            chunks = self.db_service.get_document_chunks(doc_id)
            if chunks:
                content = "\n\n".join([chunk["content"] for chunk in chunks])
                document = self.db_service.get_row_by_id("document", doc_id)
                full_documents.append({
                    "filename": document.get("filename", "Unnamed"),
                    "content": content
                })
        
        # Combine documents with separator (lines 541-543)
        return "\n\n=== DOCUMENT SEPARATOR ===\n\n".join(
            [f"{doc['filename']}:\n{doc['content']}" for doc in full_documents]
        )