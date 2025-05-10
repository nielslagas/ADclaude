#!/usr/bin/env python3
"""
Test script to manually trigger and debug document processing
"""
import os
import sys
import logging
import uuid
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("doc_processing_test")

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

# Import required modules
from app.tasks.process_document_tasks.document_processor import process_document_mvp
from app.db.database_service import db_service
from app.utils.vector_store import init_vector_store

def create_test_document():
    """Create a test document for processing"""
    # Create a test case
    case_id = str(uuid.uuid4())
    logger.info(f"Creating test case with ID: {case_id}")
    
    case = db_service.create_case(
        user_id="test_user",
        title="Test Case for Document Processing",
        description="Created via test script"
    )
    
    if not case:
        logger.error("Failed to create test case")
        return None
        
    case_id = case["id"]
    logger.info(f"Test case created with ID: {case_id}")
    
    # Create test document content
    test_content = """
    Dit is een test document om de document verwerking te testen.
    
    De werknemer is een 45-jarige man die werkzaam is als magazijnmedewerker bij een groot logistiek bedrijf.
    Hij heeft last van rugklachten en kan niet lang staan of zware lasten tillen.
    
    De werknemer is beperkt inzetbaar en kan maximaal 4 uur per dag werken. Hij kan geen gewichten tillen
    van meer dan 5 kg en moet regelmatig kunnen wisselen tussen zitten en staan.
    
    De werkgever heeft aangegeven dat er mogelijkheden zijn voor aangepast werk, maar wil graag advies over
    welke aanpassingen nodig zijn en of er subsidies beschikbaar zijn.
    """
    
    # Save test content to a file
    filename = "test_document.txt"
    storage_path = db_service.get_document_storage_path("test_user", str(case_id), filename)
    
    os.makedirs(os.path.dirname(storage_path), exist_ok=True)
    with open(storage_path, "w") as f:
        f.write(test_content)
    
    # Create document record
    document = db_service.create_document(
        case_id=case_id,
        user_id="test_user",
        filename=filename,
        storage_path=storage_path,
        mimetype="text/plain",
        size=len(test_content),
    )
    
    if not document:
        logger.error("Failed to create document record")
        return None
        
    document_id = document["id"]
    logger.info(f"Test document created with ID: {document_id}")
    
    return document_id

def process_test_document(document_id):
    """Process the test document and track results"""
    logger.info(f"Processing document with ID: {document_id}")
    
    # Initialize vector store
    init_vector_store()
    
    # Instead of running the entire process, let's break it into steps
    # and see where it's getting stuck
    from app.db.database_service import db_service
    import docx2txt
    
    try:
        # Step 1: Get document info
        logger.info("Step 1: Getting document info...")
        document = db_service.get_row_by_id("document", document_id)
        
        if not document:
            logger.error(f"Document with ID {document_id} not found")
            return {"status": "failed", "error": "Document not found"}
        
        logger.info(f"Document found: {document}")
        storage_path = document["storage_path"]
        mimetype = document["mimetype"]
        
        # Step 2: Read file content
        logger.info("Step 2: Reading file content...")
        file_content = db_service.get_document_file(storage_path)
        
        if not file_content:
            logger.error(f"Could not read file from {storage_path}")
            return {"status": "failed", "error": "File not readable"}
        
        logger.info(f"Read file content, size: {len(file_content)} bytes")
        
        # Step 3: Parse document
        logger.info("Step 3: Parsing document...")
        if mimetype == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text_content = docx2txt.process(file_content)
        elif mimetype == "text/plain":
            text_content = file_content.decode("utf-8")
        else:
            text_content = file_content.decode("utf-8", errors="ignore")
            
        logger.info(f"Parsed document, text length: {len(text_content)}")
        
        # Step 4: Chunk document
        logger.info("Step 4: Chunking document...")
        from app.tasks.process_document_tasks.document_chunker import chunk_document
        from app.core.config import settings
        
        chunks = chunk_document(text_content, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
        logger.info(f"Document chunked into {len(chunks)} chunks")
        
        # Step 5: Process first chunk only to test embedding and storage
        logger.info("Step 5: Processing first chunk with embedding...")
        from app.utils.embeddings import generate_embedding
        from app.utils.vector_store import add_embedding
        
        chunk = chunks[0]
        chunk_embedding = generate_embedding(chunk)
        logger.info(f"Generated embedding with {len(chunk_embedding)} dimensions")
        
        # Step 6: Store embedding
        logger.info("Step 6: Storing embedding...")
        metadata = {
            "document_name": document["filename"],
            "chunk_index": 0,
            "total_chunks": len(chunks),
            "case_id": str(document["case_id"])
        }
        
        chunk_id = f"{document_id}_0"
        embedding_id = add_embedding(
            document_id=document_id,
            chunk_id=chunk_id,
            content=chunk,
            embedding=chunk_embedding,
            metadata=metadata
        )
        
        logger.info(f"Embedding stored with ID: {embedding_id}")
        
        # Step 7: Store chunk in document_chunk table
        logger.info("Step 7: Storing document chunk...")
        chunk_record = db_service.create_document_chunk(
            document_id=document_id,
            content=chunk,
            chunk_index=0,
            metadata=metadata
        )
        
        logger.info(f"Document chunk stored: {chunk_record is not None}")
        
        # Step 8: Update document status
        logger.info("Step 8: Updating document status...")
        updated = db_service.update_document_status(document_id, "processed")
        logger.info(f"Document status updated: {updated is not None}")
        
        return {"status": "success", "document_id": document_id, "chunks_processed": 1}
        
    except Exception as e:
        logger.error(f"Error in processing: {str(e)}", exc_info=True)
        try:
            db_service.update_document_status(document_id, "failed", str(e))
        except Exception as update_error:
            logger.error(f"Failed to update document status: {str(update_error)}")
            
        return {"status": "failed", "document_id": document_id, "error": str(e)}

def main():
    """Create and process a test document"""
    document_id = create_test_document()
    
    if not document_id:
        logger.error("Test setup failed - could not create test document")
        sys.exit(1)
        
    process_result = process_test_document(document_id)
    
    # Check document status after processing
    document = db_service.get_row_by_id("document", document_id)
    logger.info(f"Document status after processing: {document['status']}")
    
    # Check for stored embeddings
    if process_result and process_result.get("status") == "success":
        logger.info("Document successfully processed")
        chunks = db_service.get_document_chunks(document_id)
        logger.info(f"Created {len(chunks)} document chunks")
    else:
        logger.error("Document processing failed")
    
if __name__ == "__main__":
    main()