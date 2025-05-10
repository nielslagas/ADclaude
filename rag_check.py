#!/usr/bin/env python3
"""
Test script to verify the RAG pipeline fixes
"""
import os
import sys
import logging
import uuid
import json
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("rag_check")

# Import required modules
from app.db.database_service import db_service
from app.utils.vector_store_improved import similarity_search
from app.utils.embeddings import generate_embedding, generate_query_embedding
from app.tasks.generate_report_tasks.rag_pipeline import get_relevant_chunks
from app.tasks.process_document_tasks.document_processor_hybrid import get_document_size_category

def test_embedding_availability_check():
    """Test if the embedding availability check works"""
    logger.info("Testing embedding availability check in get_relevant_chunks")
    
    try:
        # Create a dummy document without embeddings
        case_id = str(uuid.uuid4())
        document_id = str(uuid.uuid4())
        
        # Mock document without embeddings_available flag
        metadata = {
            "size_category": "small",
            "chunks_count": 5,
            "text_length": 1000,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        # Create a document record
        db_service.create_row("document", {
            "id": document_id,
            "case_id": case_id,
            "filename": "test_document.txt",
            "storage_path": "/tmp/test_document.txt",
            "mimetype": "text/plain",
            "size": 1000,
            "status": "processed",
            "user_id": "test_user",
            "metadata": json.dumps(metadata)
        })
        
        # Test get_relevant_chunks
        section_id = "samenvatting"
        chunks = get_relevant_chunks(section_id, [document_id], case_id)
        
        # Should return an empty list since document doesn't have embeddings
        if chunks == []:
            logger.info("✅ Embedding availability check works - returned empty list for document without embeddings")
        else:
            logger.error("❌ Embedding availability check failed - returned chunks for document without embeddings")
        
        # Cleanup
        db_service.delete_row("document", document_id)
        
        return len(chunks) == 0
    except Exception as e:
        logger.error(f"Error testing embedding availability check: {str(e)}")
        return False

def test_hybrid_decision_logic():
    """Test if the hybrid decision logic works correctly"""
    logger.info("Testing hybrid decision logic based on embedding availability")
    
    try:
        # Import the function
        from app.tasks.generate_report_tasks.report_generator_hybrid import should_use_direct_approach
        
        # Test case 1: Document without embeddings
        doc1 = {
            "content": "Short document content",
            "metadata": json.dumps({"processed_at": datetime.utcnow().isoformat()}),
            "status": "processed"
        }
        
        # Test case 2: Document with embeddings
        doc2 = {
            "content": "Document with embeddings",
            "metadata": json.dumps({
                "processed_at": datetime.utcnow().isoformat(),
                "embeddings_available": True
            }),
            "status": "enhanced"
        }
        
        # Test case 1: Should use direct approach
        result1 = should_use_direct_approach([doc1])
        
        # Test case 2: Should use RAG approach unless document is too small
        result2 = should_use_direct_approach([doc2])
        
        logger.info(f"Decision for document without embeddings: use_direct={result1}")
        logger.info(f"Decision for document with embeddings: use_direct={result2}")
        
        # We should always use direct approach when no embeddings available
        return result1 == True
    except Exception as e:
        logger.error(f"Error testing hybrid decision logic: {str(e)}")
        return False

def test_error_reporting():
    """Test if the error reporting for missing embeddings works"""
    logger.info("Testing error reporting for missing embeddings")
    
    try:
        from app.tasks.generate_report_tasks.rag_pipeline import generate_content_for_section
        
        # Create a dummy document without embeddings
        case_id = str(uuid.uuid4())
        document_id = str(uuid.uuid4())
        
        # Mock document without embeddings_available flag
        metadata = {
            "size_category": "small",
            "chunks_count": 5,
            "text_length": 1000,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        # Create a document record
        db_service.create_row("document", {
            "id": document_id,
            "case_id": case_id,
            "filename": "test_document.txt",
            "storage_path": "/tmp/test_document.txt",
            "mimetype": "text/plain",
            "size": 1000,
            "status": "processed",
            "user_id": "test_user",
            "metadata": json.dumps(metadata)
        })
        
        # Test generate_content_for_section
        section_info = {"title": "Samenvatting"}
        section_id = "samenvatting"
        result = generate_content_for_section(section_id, section_info, [document_id], case_id)
        
        # Check if the result contains an error for missing embeddings
        has_error = "error" in result
        contains_missing_embeddings_error = has_error and result.get("error") == "missing_embeddings"
        
        if contains_missing_embeddings_error:
            logger.info("✅ Error reporting works - correctly identified missing embeddings")
        else:
            logger.info("❌ Error reporting failed - didn't report missing embeddings correctly")
            logger.info(f"Result: {result}")
        
        # Check if the content contains an error message
        error_in_content = "Kan deze sectie niet genereren" in result.get("content", "")
        
        if error_in_content:
            logger.info("✅ Content includes error message for missing embeddings")
        else:
            logger.info("❌ Content doesn't include error message for missing embeddings")
        
        # Cleanup
        db_service.delete_row("document", document_id)
        
        return contains_missing_embeddings_error and error_in_content
    except Exception as e:
        logger.error(f"Error testing error reporting: {str(e)}")
        return False

def main():
    """Run all tests for the RAG pipeline fixes"""
    logger.info("=== TESTING RAG PIPELINE FIXES ===")
    
    tests = [
        ("Embedding Availability Check", test_embedding_availability_check),
        ("Hybrid Decision Logic", test_hybrid_decision_logic),
        ("Error Reporting", test_error_reporting)
    ]
    
    results = []
    for name, test_func in tests:
        logger.info(f"\n--- Testing: {name} ---")
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"Unexpected error in test {name}: {str(e)}")
            results.append((name, False))
    
    # Print summary
    logger.info("\n=== TEST RESULTS ===")
    success_count = 0
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{name}: {status}")
        if result:
            success_count += 1
    
    overall = success_count == len(tests)
    logger.info(f"\nOverall result: {'✅ ALL PASSED' if overall else '❌ SOME TESTS FAILED'}")
    logger.info(f"{success_count}/{len(tests)} tests passed")
    
if __name__ == "__main__":
    main()