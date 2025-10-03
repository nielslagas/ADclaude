"""
Integration tests for the Hybrid RAG Pipeline.
Tests the complete RAG workflow including document classification, processing, and retrieval.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime
import asyncio

from app.utils.smart_document_classifier import SmartDocumentClassifier
from app.utils.optimized_rag_pipeline import OptimizedRAGPipeline
from app.utils.hybrid_search import HybridSearchService
from app.utils.quality_controller import QualityController
from app.utils.multimodal_rag import MultiModalRAG
from app.utils.rag_monitoring import RAGMonitoring


@pytest.fixture
def sample_medical_document():
    """Sample medical document for testing."""
    return """
    MEDISCH RAPPORT

    Patiënt: Jan de Vries
    BSN: 123456789
    Geboortedatum: 15-03-1980
    Datum onderzoek: 10-12-2024

    ANAMNESE:
    De patiënt meldt chronische pijn in de lumbale wervelkolom sinds een arbeidsongeval 
    6 maanden geleden. Hij werkte als magazijnmedewerker en tilde regelmatig zware dozen.
    
    De pijn straalt uit naar beide benen en gaat gepaard met tintelingen in de voeten.
    Zittend werk is mogelijk tot maximaal 2 uur aaneengesloten.

    LICHAMELIJK ONDERZOEK:
    - Beperkte flexie van de lumbale wervelkolom (45 graden)
    - Lasègue test positief bilateraal bij 60 graden
    - Kracht verminderd in beide benen (4/5)
    - Sensibiliteitsstoornissen in L5 en S1 dermatomen

    DIAGNOSE:
    Multiple lumbale herniae L4-L5 en L5-S1 met bilaterale radiculopathie

    BEHANDELING:
    - Fysiotherapie gestart
    - Medicatie: Pregabaline 75mg 2x daags
    - Epidurale injecties overwogen

    PROGNOSE:
    Herstel onzeker. Huidige klachten bestaan reeds 6 maanden zonder verbetering.
    Werkhervatting in oorspronkelijke functie niet waarschijnlijk.
    Aangepast werk tot maximaal 4 uur per dag mogelijk.
    """


@pytest.fixture
def sample_assessment_document():
    """Sample arbeidsdeskundig assessment document."""
    return """
    ARBEIDSDESKUNDIGE BEOORDELING

    Naam: Jan de Vries
    Datum beoordeling: 15-12-2024

    BELASTBAARHEIDSANALYSE:
    Op basis van het medisch rapport en eigen onderzoek kan worden geconcludeerd:

    FYSIEKE BELASTBAARHEID:
    - Zittend werk: maximaal 4 uur per dag met pauzes
    - Staand werk: maximaal 1 uur aaneengesloten
    - Lopen: tot 500 meter zonder rust
    - Tillen: maximaal 5 kg vanaf tafelblad hoogte
    - Geen tillen vanaf de grond
    - Geen werkzaamheden boven schouderhoogte

    BEPERKINGEN:
    - Langdurig zitten niet mogelijk (max 30 minuten aaneengesloten)
    - Bukken en hurken niet mogelijk
    - Autorijden beperkt tot 1 uur
    - Concentratieproblemen door pijn

    MOGELIJKHEDEN:
    - Administratief werk met ergonomische aanpassingen
    - Licht fysiek werk in wisselhouding
    - Telewerken 2-3 dagen per week
    - Flexibele werktijden noodzakelijk

    CONCLUSIE:
    Geschikt voor aangepast werk binnen beperkingen.
    Werkgever dient werkplekaanpassingen te realiseren.
    Begeleiding door arbeidsdeskundige geadviseerd.
    """


@pytest.mark.integration
@pytest.mark.rag
class TestHybridRAGPipeline:
    """Integration tests for the complete RAG pipeline."""
    
    async def test_end_to_end_document_processing(self, mock_llm_provider, mock_vector_store, 
                                                  sample_medical_document, sample_assessment_document):
        """Test complete document processing pipeline."""
        
        # Setup components
        classifier = SmartDocumentClassifier(mock_llm_provider)
        rag_pipeline = OptimizedRAGPipeline(mock_llm_provider, mock_vector_store)
        quality_controller = QualityController(mock_llm_provider)
        monitoring = RAGMonitoring()
        
        # Mock classification results
        with patch.object(classifier, 'classify_document') as mock_classify:
            mock_classify_results = [
                {
                    "type": "medical_report",
                    "confidence": 0.95,
                    "processing_strategy": "hybrid",
                    "metadata": {
                        "sections": ["anamnese", "diagnose", "behandeling"],
                        "language": "dutch",
                        "estimated_tokens": 500
                    }
                },
                {
                    "type": "assessment_report", 
                    "confidence": 0.92,
                    "processing_strategy": "semantic",
                    "metadata": {
                        "sections": ["belastbaarheid", "beperkingen", "conclusie"],
                        "language": "dutch",
                        "estimated_tokens": 400
                    }
                }
            ]
            mock_classify.side_effect = mock_classify_results
            
            # Mock RAG pipeline processing
            with patch.object(rag_pipeline, 'process_document') as mock_process:
                mock_process_results = [
                    {
                        "document_id": str(uuid4()),
                        "chunks_created": 8,
                        "embeddings_generated": 8,
                        "processing_time": 2.5,
                        "strategy_used": "hybrid",
                        "quality_score": 0.88
                    },
                    {
                        "document_id": str(uuid4()),
                        "chunks_created": 6,
                        "embeddings_generated": 6,
                        "processing_time": 1.8,
                        "strategy_used": "semantic",
                        "quality_score": 0.91
                    }
                ]
                mock_process.side_effect = mock_process_results
                
                # Process documents
                documents = [
                    {"content": sample_medical_document, "filename": "medical_report.txt"},
                    {"content": sample_assessment_document, "filename": "assessment.txt"}
                ]
                
                results = []
                for doc in documents:
                    # Step 1: Classify document
                    classification = await classifier.classify_document(doc["content"], doc["filename"])
                    
                    # Step 2: Process with RAG pipeline
                    processing_result = await rag_pipeline.process_document(
                        doc["content"], 
                        classification,
                        doc["filename"]
                    )
                    
                    results.append({
                        "classification": classification,
                        "processing": processing_result
                    })
                
                # Verify results
                assert len(results) == 2
                
                # Check medical report processing
                medical_result = results[0]
                assert medical_result["classification"]["type"] == "medical_report"
                assert medical_result["classification"]["confidence"] > 0.9
                assert medical_result["processing"]["chunks_created"] > 0
                
                # Check assessment report processing
                assessment_result = results[1]
                assert assessment_result["classification"]["type"] == "assessment_report"
                assert assessment_result["processing"]["strategy_used"] == "semantic"
    
    
    async def test_hybrid_search_integration(self, mock_llm_provider, mock_vector_store):
        """Test hybrid search functionality across different document types."""
        
        search_service = HybridSearchService(mock_vector_store, mock_llm_provider)
        
        # Mock search results
        with patch.object(search_service, 'hybrid_search') as mock_search:
            mock_search.return_value = {
                "semantic_results": [
                    {
                        "content": "Patient heeft chronische rugpijn met uitstraling naar beide benen",
                        "similarity": 0.92,
                        "document_id": str(uuid4()),
                        "chunk_index": 2,
                        "metadata": {"section_type": "anamnese", "document_type": "medical_report"}
                    }
                ],
                "keyword_results": [
                    {
                        "content": "Lumbale hernia L4-L5 en L5-S1 bilateraal",
                        "score": 0.88,
                        "document_id": str(uuid4()),
                        "chunk_index": 5,
                        "metadata": {"section_type": "diagnose", "document_type": "medical_report"}
                    }
                ],
                "combined_results": [
                    {
                        "content": "Patient heeft chronische rugpijn met uitstraling naar beide benen",
                        "relevance_score": 0.95,
                        "source": "semantic",
                        "metadata": {"confidence": 0.92}
                    },
                    {
                        "content": "Lumbale hernia L4-L5 en L5-S1 bilateraal", 
                        "relevance_score": 0.89,
                        "source": "keyword",
                        "metadata": {"confidence": 0.88}
                    }
                ],
                "strategy_used": "hybrid",
                "search_time": 0.45
            }
            
            # Test different query types
            queries = [
                "Wat zijn de medische klachten van de patiënt?",
                "Welke beperkingen heeft de werknemer?",
                "Wat is de prognose voor werkhervatting?"
            ]
            
            for query in queries:
                result = await search_service.hybrid_search(
                    query=query,
                    case_id=str(uuid4()),
                    max_results=10
                )
                
                assert "combined_results" in result
                assert "strategy_used" in result
                assert len(result["combined_results"]) > 0
                assert result["search_time"] < 1.0  # Performance check
    
    
    async def test_multimodal_rag_integration(self, mock_llm_provider, mock_vector_store):
        """Test multimodal RAG with text and audio integration."""
        
        multimodal_rag = MultiModalRAG(mock_llm_provider, mock_vector_store)
        
        # Mock multimodal processing
        with patch.object(multimodal_rag, 'process_multimodal_query') as mock_multimodal:
            mock_multimodal.return_value = {
                "response": "Op basis van het medische rapport en het gesprek met de patiënt blijkt dat...",
                "sources": [
                    {
                        "type": "document",
                        "document_id": str(uuid4()),
                        "content": "Medisch rapport fragment",
                        "relevance": 0.92
                    },
                    {
                        "type": "audio_transcript",
                        "audio_id": str(uuid4()),
                        "content": "Patiënt: Ik heb vooral pijn als ik lang zit",
                        "timestamp": "00:02:15",
                        "relevance": 0.87
                    }
                ],
                "confidence": 0.89,
                "modalities_used": ["text", "audio"],
                "processing_time": 3.2
            }
            
            query = "Beschrijf de volledige situatie van de patiënt op basis van alle beschikbare informatie"
            case_id = str(uuid4())
            
            result = await multimodal_rag.process_multimodal_query(
                query=query,
                case_id=case_id,
                include_audio=True
            )
            
            assert result["confidence"] > 0.8
            assert len(result["sources"]) >= 2
            assert "text" in result["modalities_used"]
            assert "audio" in result["modalities_used"]
    
    
    async def test_quality_control_integration(self, mock_llm_provider):
        """Test quality control validation across the pipeline."""
        
        quality_controller = QualityController(mock_llm_provider)
        
        # Mock quality validation
        with patch.object(quality_controller, 'validate_generated_content') as mock_validate:
            mock_validate.return_value = {
                "is_valid": True,
                "quality_score": 0.91,
                "issues": [],
                "suggestions": [
                    "Consider adding more specific timeline information",
                    "Include reference to relevant legislation"
                ],
                "factual_accuracy": 0.95,
                "completeness": 0.87,
                "coherence": 0.93,
                "dutch_language_quality": 0.96
            }
            
            generated_content = """
            Op basis van de medische rapportage kan worden geconcludeerd dat de werknemer 
            beperkt inzetbaar is vanwege chronische lumbale klachten. De prognose voor 
            volledig herstel is ongunstig.
            """
            
            validation_result = await quality_controller.validate_generated_content(
                content=generated_content,
                section_type="conclusie",
                context="arbeidsdeskundig rapport"
            )
            
            assert validation_result["is_valid"] is True
            assert validation_result["quality_score"] > 0.8
            assert validation_result["dutch_language_quality"] > 0.9
    
    
    async def test_rag_monitoring_integration(self, mock_llm_provider, mock_vector_store):
        """Test RAG monitoring and metrics collection."""
        
        monitoring = RAGMonitoring()
        rag_pipeline = OptimizedRAGPipeline(mock_llm_provider, mock_vector_store)
        
        # Mock monitoring data collection
        with patch.object(monitoring, 'log_operation') as mock_log, \
             patch.object(monitoring, 'get_performance_metrics') as mock_metrics:
            
            mock_metrics.return_value = {
                "total_operations": 150,
                "success_rate": 0.96,
                "avg_response_time": 2.1,
                "avg_quality_score": 0.89,
                "token_usage": {
                    "total_tokens": 75000,
                    "avg_per_operation": 500,
                    "cost_estimate": 15.30
                },
                "error_rate": 0.04,
                "most_common_errors": ["timeout", "rate_limit"],
                "performance_trends": {
                    "response_time_trend": "stable",
                    "quality_trend": "improving"
                }
            }
            
            # Simulate RAG operations
            operations = [
                {"type": "document_processing", "duration": 2.5, "success": True},
                {"type": "query_processing", "duration": 1.8, "success": True},
                {"type": "report_generation", "duration": 4.2, "success": False}
            ]
            
            for op in operations:
                monitoring.log_operation(
                    operation_type=op["type"],
                    duration=op["duration"],
                    success=op["success"],
                    metadata={"tokens_used": 450}
                )
            
            # Get performance metrics
            metrics = monitoring.get_performance_metrics(time_period="24h")
            
            assert metrics["success_rate"] > 0.9
            assert metrics["avg_response_time"] < 5.0
            assert "token_usage" in metrics
            assert "performance_trends" in metrics
    
    
    async def test_error_handling_and_fallbacks(self, mock_llm_provider, mock_vector_store):
        """Test error handling and fallback mechanisms in the RAG pipeline."""
        
        rag_pipeline = OptimizedRAGPipeline(mock_llm_provider, mock_vector_store)
        
        # Test LLM provider failure with fallback
        with patch.object(mock_llm_provider, 'generate_response') as mock_generate:
            # First call fails, second succeeds (fallback provider)
            mock_generate.side_effect = [
                Exception("OpenAI API rate limit exceeded"),
                {
                    "content": "Fallback response using Anthropic Claude",
                    "tokens_used": 200,
                    "model": "claude-3-haiku",
                    "provider": "anthropic"
                }
            ]
            
            with patch.object(rag_pipeline, '_handle_llm_fallback') as mock_fallback:
                mock_fallback.return_value = {
                    "content": "Fallback response using Anthropic Claude",
                    "tokens_used": 200,
                    "model": "claude-3-haiku", 
                    "provider": "anthropic"
                }
                
                result = await rag_pipeline.process_query(
                    query="Test query for fallback",
                    case_id=str(uuid4())
                )
                
                assert "content" in result
                assert result["provider"] == "anthropic"  # Fallback provider used
                mock_fallback.assert_called_once()
    
    
    async def test_concurrent_pipeline_operations(self, mock_llm_provider, mock_vector_store):
        """Test pipeline performance under concurrent load."""
        
        rag_pipeline = OptimizedRAGPipeline(mock_llm_provider, mock_vector_store)
        
        # Mock successful operations
        with patch.object(rag_pipeline, 'process_query') as mock_process:
            mock_process.return_value = {
                "response": "Generated response",
                "sources": [],
                "confidence": 0.85,
                "processing_time": 1.5
            }
            
            # Simulate concurrent queries
            queries = [
                "Wat zijn de medische beperkingen?",
                "Welke aanpassingen zijn nodig?",
                "Wat is de prognose?",
                "Kan de werknemer zijn werk hervatten?",
                "Welke behandeling wordt geadviseerd?"
            ]
            
            case_id = str(uuid4())
            
            import time
            start_time = time.time()
            
            # Execute concurrent queries
            tasks = [
                rag_pipeline.process_query(query, case_id) 
                for query in queries
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Verify all operations succeeded
            assert len(results) == 5
            for result in results:
                assert not isinstance(result, Exception)
                assert "response" in result
            
            # Performance check - should handle concurrent load efficiently
            assert total_time < 10.0  # Should complete within 10 seconds
    
    
    async def test_document_chunking_strategies(self, mock_llm_provider, mock_vector_store, 
                                              sample_medical_document):
        """Test different document chunking strategies based on document type."""
        
        classifier = SmartDocumentClassifier(mock_llm_provider)
        rag_pipeline = OptimizedRAGPipeline(mock_llm_provider, mock_vector_store)
        
        with patch.object(classifier, 'classify_document') as mock_classify, \
             patch.object(rag_pipeline, '_create_smart_chunks') as mock_chunk:
            
            # Mock classification for medical document
            mock_classify.return_value = {
                "type": "medical_report",
                "confidence": 0.94,
                "processing_strategy": "section_aware",
                "metadata": {
                    "sections": ["anamnese", "onderzoek", "diagnose", "behandeling"],
                    "language": "dutch"
                }
            }
            
            # Mock intelligent chunking
            mock_chunk.return_value = [
                {
                    "content": "ANAMNESE: De patiënt meldt chronische pijn...",
                    "metadata": {
                        "section_type": "anamnese",
                        "chunk_index": 0,
                        "importance": "high"
                    }
                },
                {
                    "content": "DIAGNOSE: Multiple lumbale herniae...",
                    "metadata": {
                        "section_type": "diagnose", 
                        "chunk_index": 1,
                        "importance": "critical"
                    }
                },
                {
                    "content": "PROGNOSE: Herstel onzeker...",
                    "metadata": {
                        "section_type": "prognose",
                        "chunk_index": 2,
                        "importance": "high"
                    }
                }
            ]
            
            classification = await classifier.classify_document(
                sample_medical_document, 
                "medical_report.txt"
            )
            
            chunks = await rag_pipeline._create_smart_chunks(
                sample_medical_document,
                classification["type"],
                classification
            )
            
            assert len(chunks) == 3
            
            # Verify section-aware chunking
            section_types = [chunk["metadata"]["section_type"] for chunk in chunks]
            assert "anamnese" in section_types
            assert "diagnose" in section_types
            assert "prognose" in section_types
            
            # Verify importance tagging
            importance_levels = [chunk["metadata"]["importance"] for chunk in chunks]
            assert "critical" in importance_levels  # Diagnose should be critical
            assert "high" in importance_levels     # Other sections should be high importance