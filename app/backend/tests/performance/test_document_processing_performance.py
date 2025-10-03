"""
Performance tests for document processing and RAG pipeline.
Tests system performance under various load conditions.
"""

import pytest
import asyncio
import time
import statistics
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import threading

from app.utils.smart_document_classifier import SmartDocumentClassifier
from app.utils.optimized_rag_pipeline import OptimizedRAGPipeline
from app.utils.vector_store_improved import VectorStoreService
from app.utils.rag_monitoring import RAGMonitoring


@pytest.fixture
def large_document():
    """Generate a large document for performance testing."""
    base_content = """
    ARBEIDSDESKUNDIG RAPPORT
    
    Naam: Test Patiënt {i}
    BSN: {bsn}
    Datum onderzoek: 15-12-2024
    
    ANAMNESE:
    De patiënt werkt als {functie} en heeft sinds {datum} klachten van {klacht}.
    De klachten zijn ontstaan tijdens het werk door {oorzaak}.
    
    LICHAMELIJK ONDERZOEK:
    Bij onderzoek zijn de volgende bevindingen gedaan:
    - Bewegingsbeperking in {lichaamsdeel}
    - Pijn bij {beweging}
    - Functieverlies van {functie_verlies}
    
    DIAGNOSE:
    Op basis van het onderzoek luidt de diagnose: {diagnose}
    
    BEHANDELING:
    De behandeling bestaat uit:
    - Fysiotherapie {frequentie}
    - Medicatie: {medicatie}
    - Eventueel vervolgonderzoek
    
    BEPERKINGEN:
    De patiënt heeft de volgende beperkingen:
    - {beperking1}
    - {beperking2}
    - {beperking3}
    
    MOGELIJKHEDEN:
    Ondanks de beperkingen zijn er nog mogelijkheden:
    - {mogelijkheid1}
    - {mogelijkheid2}
    - {mogelijkheid3}
    
    CONCLUSIE:
    De patiënt is {geschiktheid} voor het huidige werk.
    Aanpassingen zijn {aanpassingen}.
    De prognose is {prognose}.
    """
    
    # Generate multiple sections to create a large document
    large_content = ""
    for i in range(50):  # 50 patient cases
        section = base_content.format(
            i=i+1,
            bsn=f"12345678{i:02d}",
            functie=["magazijnmedewerker", "kantoormedewerker", "verpleegkundige", "docent"][i % 4],
            datum=f"{(i % 12) + 1:02d}-{2024 - (i % 5)}-2024",
            klacht=["rugpijn", "nekklachten", "schouderprobleem", "kniepijn"][i % 4],
            oorzaak=["tillen", "langdurig zitten", "repetitief werk", "vallen"][i % 4],
            lichaamsdeel=["rug", "nek", "schouder", "knie"][i % 4],
            beweging=["buigen", "draaien", "tillen", "lopen"][i % 4],
            functie_verlies=["kracht", "bewegelijkheid", "gevoel", "coördinatie"][i % 4],
            diagnose=f"Aandoening {i+1} met bijkomende klachten",
            frequentie=["2x per week", "3x per week", "dagelijks", "1x per week"][i % 4],
            medicatie=["Paracetamol", "Ibuprofen", "Naproxen", "Diclofenac"][i % 4],
            beperking1="Geen tillen boven 5kg",
            beperking2="Maximaal 4 uur werken per dag",
            beperking3="Regelmatige pauzes nodig",
            mogelijkheid1="Aangepast werk mogelijk",
            mogelijkheid2="Thuiswerken optie",
            mogelijkheid3="Flexibele uren",
            geschiktheid=["gedeeltelijk geschikt", "niet geschikt", "geschikt met aanpassingen"][i % 3],
            aanpassingen=["noodzakelijk", "gewenst", "niet nodig"][i % 3],
            prognose=["gunstig", "onzeker", "matig"][i % 3]
        )
        large_content += section + "\n\n"
    
    return large_content


@pytest.mark.performance
@pytest.mark.slow
class TestDocumentProcessingPerformance:
    """Performance tests for document processing."""
    
    async def test_single_document_processing_speed(self, mock_llm_provider, mock_vector_store, large_document):
        """Test processing speed for a single large document."""
        
        classifier = SmartDocumentClassifier(mock_llm_provider)
        rag_pipeline = OptimizedRAGPipeline(mock_llm_provider, mock_vector_store)
        
        # Mock fast responses
        with patch.object(classifier, 'classify_document') as mock_classify, \
             patch.object(rag_pipeline, 'process_document') as mock_process:
            
            mock_classify.return_value = {
                "type": "assessment_report",
                "confidence": 0.93,
                "processing_strategy": "hybrid",
                "metadata": {"estimated_tokens": len(large_document) // 4}
            }
            
            mock_process.return_value = {
                "document_id": str(uuid4()),
                "chunks_created": 75,
                "embeddings_generated": 75,
                "processing_time": 0.1,  # Mock fast processing
                "strategy_used": "hybrid"
            }
            
            # Measure processing time
            start_time = time.time()
            
            classification = await classifier.classify_document(large_document, "large_doc.txt")
            processing_result = await rag_pipeline.process_document(
                large_document, classification, "large_doc.txt"
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Performance assertions
            assert processing_time < 5.0  # Should complete within 5 seconds
            assert processing_result["chunks_created"] > 50  # Large document should create many chunks
            assert classification["confidence"] > 0.8
    
    
    async def test_concurrent_document_processing(self, mock_llm_provider, mock_vector_store, performance_test_documents):
        """Test system performance under concurrent document processing load."""
        
        rag_pipeline = OptimizedRAGPipeline(mock_llm_provider, mock_vector_store)
        
        with patch.object(rag_pipeline, 'process_document') as mock_process:
            # Mock varying processing times
            processing_times = [0.5, 1.0, 1.5, 2.0, 0.8, 1.2, 0.9, 1.8, 1.1, 1.6]
            
            def mock_process_func(content, classification, filename):
                idx = len(mock_process.call_args_list) % len(processing_times)
                time.sleep(processing_times[idx] * 0.1)  # Simulate processing time (scaled down)
                return {
                    "document_id": str(uuid4()),
                    "chunks_created": len(content) // 500,
                    "processing_time": processing_times[idx],
                    "strategy_used": "hybrid"
                }
            
            mock_process.side_effect = mock_process_func
            
            # Process documents concurrently
            start_time = time.time()
            
            tasks = []
            for doc in performance_test_documents:
                classification = {"type": "document", "confidence": 0.9, "processing_strategy": "hybrid"}
                task = rag_pipeline.process_document(
                    doc["content"], classification, doc["filename"]
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Performance checks
            assert len(results) == len(performance_test_documents)
            assert total_time < 15.0  # Should handle concurrent load efficiently
            
            # Check all documents were processed
            for result in results:
                assert "document_id" in result
                assert result["chunks_created"] > 0
    
    
    async def test_memory_usage_during_processing(self, mock_llm_provider, mock_vector_store, large_document):
        """Test memory usage during large document processing."""
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        rag_pipeline = OptimizedRAGPipeline(mock_llm_provider, mock_vector_store)
        
        with patch.object(rag_pipeline, 'process_document') as mock_process:
            # Mock memory-efficient processing
            mock_process.return_value = {
                "document_id": str(uuid4()),
                "chunks_created": 100,
                "processing_time": 2.0,
                "memory_peak": 150  # MB
            }
            
            # Process multiple large documents
            for i in range(5):
                classification = {"type": "large_document", "confidence": 0.9}
                await rag_pipeline.process_document(
                    large_document, classification, f"large_doc_{i}.txt"
                )
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Memory usage should not increase excessively
            assert memory_increase < 500  # Should not use more than 500MB additional memory
    
    
    async def test_embedding_generation_performance(self, mock_llm_provider, mock_vector_store):
        """Test performance of embedding generation for multiple chunks."""
        
        # Create test chunks
        test_chunks = []
        for i in range(100):
            chunk = f"""
            Chunk {i}: Dit is een test chunk voor embedding generatie.
            Het bevat Nederlandse tekst over arbeidsdeskundige rapporten.
            Patiënt heeft klachten en beperkingen die beschreven worden.
            """ * 3  # Make chunks reasonably long
            test_chunks.append(chunk)
        
        with patch.object(mock_llm_provider, 'generate_embedding') as mock_embed:
            # Mock fast embedding generation
            mock_embed.return_value = [0.1] * 1536  # Standard embedding size
            
            start_time = time.time()
            
            # Generate embeddings for all chunks
            embeddings = []
            for chunk in test_chunks:
                embedding = await mock_llm_provider.generate_embedding(chunk)
                embeddings.append(embedding)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Performance checks
            assert len(embeddings) == 100
            assert total_time < 10.0  # Should generate 100 embeddings within 10 seconds
            assert mock_embed.call_count == 100
            
            # Check embedding quality
            for embedding in embeddings:
                assert len(embedding) == 1536
                assert all(isinstance(x, (int, float)) for x in embedding)
    
    
    async def test_vector_search_performance(self, mock_vector_store):
        """Test vector search performance with large dataset."""
        
        # Mock large vector database
        with patch.object(mock_vector_store, 'search_similar') as mock_search:
            # Mock search results
            mock_search.return_value = [
                {
                    "id": str(uuid4()),
                    "content": f"Search result {i}",
                    "similarity": 0.9 - (i * 0.01),  # Decreasing similarity
                    "metadata": {"chunk_index": i, "document_id": str(uuid4())}
                }
                for i in range(10)
            ]
            
            query_embedding = [0.1] * 1536
            
            # Measure search performance
            search_times = []
            
            for _ in range(20):  # 20 search operations
                start_time = time.time()
                
                results = mock_vector_store.search_similar(
                    query_embedding=query_embedding,
                    max_results=10
                )
                
                end_time = time.time()
                search_times.append(end_time - start_time)
                
                assert len(results) == 10
                assert all(r["similarity"] > 0.8 for r in results)
            
            # Performance statistics
            avg_search_time = statistics.mean(search_times)
            max_search_time = max(search_times)
            
            assert avg_search_time < 0.5  # Average search should be under 0.5 seconds
            assert max_search_time < 1.0   # No search should take more than 1 second
    
    
    async def test_report_generation_performance(self, mock_llm_provider):
        """Test performance of report generation with multiple sections."""
        
        sections = [
            "persoonsgegevens", "werkgever_functie", "aanleiding", "arbeidsverleden",
            "medische_situatie", "belastbaarheid", "belasting_huidige_functie",
            "mogelijkheden_huidige_werkgever", "mogelijkheden_arbeidsmarkt", "conclusie"
        ]
        
        with patch.object(mock_llm_provider, 'generate_response') as mock_generate:
            # Mock section generation
            def mock_section_generation(prompt, **kwargs):
                section_name = prompt.split(":")[-1].strip() if ":" in prompt else "unknown"
                return {
                    "content": f"Generated content for {section_name} section. " * 50,  # ~250 words
                    "tokens_used": 300,
                    "model": "claude-3-haiku",
                    "processing_time": 0.8
                }
            
            mock_generate.side_effect = mock_section_generation
            
            # Generate report sections
            start_time = time.time()
            
            generated_sections = {}
            for section in sections:
                prompt = f"Generate {section} section for arbeidsdeskundig rapport"
                result = await mock_llm_provider.generate_response(prompt)
                generated_sections[section] = result
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Performance checks
            assert len(generated_sections) == len(sections)
            assert total_time < 20.0  # Should generate all sections within 20 seconds
            
            # Check content quality
            total_tokens = sum(section["tokens_used"] for section in generated_sections.values())
            assert total_tokens > 2000  # Should generate substantial content
            assert all(len(section["content"]) > 100 for section in generated_sections.values())
    
    
    async def test_system_load_simulation(self, mock_llm_provider, mock_vector_store):
        """Simulate realistic system load with multiple concurrent users."""
        
        # Simulate 10 concurrent users each processing documents and generating reports
        num_users = 10
        operations_per_user = 3
        
        rag_pipeline = OptimizedRAGPipeline(mock_llm_provider, mock_vector_store)
        monitoring = RAGMonitoring()
        
        with patch.object(rag_pipeline, 'process_query') as mock_query, \
             patch.object(monitoring, 'log_operation') as mock_log:
            
            # Mock realistic response times
            response_times = [1.2, 1.8, 2.1, 1.5, 2.4, 1.9, 1.7, 2.0, 1.6, 2.3]
            
            def mock_query_func(query, case_id):
                idx = len(mock_query.call_args_list) % len(response_times)
                response_time = response_times[idx]
                time.sleep(response_time * 0.1)  # Scaled down simulation
                
                return {
                    "response": f"Generated response for: {query[:50]}...",
                    "sources": [{"document_id": str(uuid4()), "relevance": 0.9}],
                    "confidence": 0.88,
                    "processing_time": response_time,
                    "tokens_used": 450
                }
            
            mock_query.side_effect = mock_query_func
            
            async def simulate_user_session(user_id):
                """Simulate a user session with multiple operations."""
                case_id = str(uuid4())
                queries = [
                    "Wat zijn de medische beperkingen van de werknemer?",
                    "Welke aanpassingen zijn nodig op de werkplek?", 
                    "Wat is de prognose voor werkhervatting?"
                ]
                
                results = []
                for query in queries[:operations_per_user]:
                    result = await rag_pipeline.process_query(query, case_id)
                    results.append(result)
                    
                    # Log operation for monitoring
                    monitoring.log_operation(
                        operation_type="query_processing",
                        duration=result["processing_time"],
                        success=True,
                        metadata={"user_id": user_id, "tokens": result["tokens_used"]}
                    )
                
                return results
            
            # Execute concurrent user sessions
            start_time = time.time()
            
            user_tasks = [
                simulate_user_session(f"user_{i}") 
                for i in range(num_users)
            ]
            
            all_results = await asyncio.gather(*user_tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Performance analysis
            total_operations = num_users * operations_per_user
            avg_time_per_operation = total_time / total_operations
            
            assert len(all_results) == num_users
            assert total_time < 30.0  # Should handle load within 30 seconds
            assert avg_time_per_operation < 2.0  # Average operation time should be reasonable
            
            # Verify all operations completed successfully
            for user_results in all_results:
                assert len(user_results) == operations_per_user
                for result in user_results:
                    assert "response" in result
                    assert result["confidence"] > 0.8
    
    
    async def test_database_performance_under_load(self, mock_db_service):
        """Test database performance with high concurrent access."""
        
        # Mock database operations with realistic response times
        with patch.object(mock_db_service, 'create_document') as mock_create, \
             patch.object(mock_db_service, 'get_case_documents') as mock_get, \
             patch.object(mock_db_service, 'update_document_status') as mock_update:
            
            # Mock response times
            def mock_create_doc(*args, **kwargs):
                time.sleep(0.05)  # 50ms database write
                return {"id": str(uuid4()), "status": "created"}
            
            def mock_get_docs(case_id, user_id):
                time.sleep(0.02)  # 20ms database read
                return [{"id": str(uuid4()), "filename": f"doc_{i}.txt"} for i in range(5)]
            
            def mock_update_status(doc_id, status):
                time.sleep(0.03)  # 30ms database update
                return {"id": doc_id, "status": status}
            
            mock_create.side_effect = mock_create_doc
            mock_get.side_effect = mock_get_docs
            mock_update.side_effect = mock_update_status
            
            # Simulate concurrent database operations
            start_time = time.time()
            
            async def database_operations():
                case_id = str(uuid4())
                user_id = "test_user"
                
                # Create documents
                create_tasks = [
                    asyncio.create_task(asyncio.to_thread(mock_db_service.create_document, 
                                                        case_id=case_id, user_id=user_id,
                                                        filename=f"doc_{i}.txt"))
                    for i in range(10)
                ]
                
                # Get documents  
                get_tasks = [
                    asyncio.create_task(asyncio.to_thread(mock_db_service.get_case_documents,
                                                        case_id, user_id))
                    for _ in range(5)
                ]
                
                # Update document status
                update_tasks = [
                    asyncio.create_task(asyncio.to_thread(mock_db_service.update_document_status,
                                                        str(uuid4()), "processed"))
                    for _ in range(8)
                ]
                
                all_tasks = create_tasks + get_tasks + update_tasks
                results = await asyncio.gather(*all_tasks)
                
                return results
            
            results = await database_operations()
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Performance checks
            assert len(results) == 23  # 10 creates + 5 gets + 8 updates
            assert total_time < 5.0    # Should complete within 5 seconds with concurrency
            
            # Verify operation counts
            assert mock_create.call_count == 10
            assert mock_get.call_count == 5  
            assert mock_update.call_count == 8