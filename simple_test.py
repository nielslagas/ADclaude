#!/usr/bin/env python3
"""
Simplified test for the RAG pipeline
"""
import os
import sys
import logging
import uuid
import time
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("rag_pipeline_test")

# Import required modules
from app.db.database_service import db_service
from app.utils.vector_store_improved import similarity_search, add_embedding
from app.utils.embeddings import generate_embedding, generate_query_embedding
from app.tasks.generate_report_tasks.rag_pipeline import get_relevant_chunks

def test_rag_pipeline():
    """Test the RAG pipeline with a simple query"""
    logger.info("Testing RAG pipeline with vector_store_improved")
    
    # Generate a test embedding
    test_text = "Dit is een test voor de verbeterde RAG pipeline"
    logger.info(f"Generating embedding for: '{test_text}'")
    
    try:
        embedding = generate_embedding(test_text)
        logger.info(f"Successfully generated embedding with {len(embedding)} dimensions")
        
        # Test query embedding
        query = "Hoe werkt de RAG pipeline?"
        query_embedding = generate_query_embedding(query)
        logger.info(f"Successfully generated query embedding")
        
        logger.info("RAG pipeline test passed!")
        return True
    except Exception as e:
        logger.error(f"Error in RAG pipeline test: {str(e)}")
        return False

if __name__ == "__main__":
    test_rag_pipeline()