#!/usr/bin/env python3
"""
Improved test script to debug document processing with enhanced monitoring and timeouts
"""
import os
import sys
import logging
import uuid
import time
import signal
import gc
import tracemalloc
import threading
from datetime import datetime
import psutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("improved_doc_processing_test")

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), "app/backend"))

# Import required modules
try:
    from app.db.database_service import db_service
    from app.utils.vector_store import init_vector_store
    from app.utils.embeddings import generate_embedding
    from app.tasks.process_document_tasks.document_chunker import chunk_document
    from app.core.config import settings
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

# Initialize memory tracking and process monitoring
tracemalloc.start()
process = psutil.Process(os.getpid())

# Track specific operations for timing analysis
timings = {}
current_operation = None
operation_start_time = None

def start_operation(name):
    """Start timing for an operation"""
    global current_operation, operation_start_time
    current_operation = name
    operation_start_time = time.time()
    logger.info(f"Starting operation: {name}")

def end_operation():
    """End timing for current operation"""
    global current_operation, operation_start_time, timings
    if current_operation:
        duration = time.time() - operation_start_time
        timings[current_operation] = duration
        logger.info(f"Completed operation: {current_operation} in {duration:.2f} seconds")
        current_operation = None
        operation_start_time = None

def log_memory_usage(label):
    """Log current memory usage"""
    memory_info = process.memory_info()
    current, peak = tracemalloc.get_traced_memory()
    logger.info(f"Memory usage at {label}: RSS={memory_info.rss/1024/1024:.2f}MB, "
                f"Traced={current/1024/1024:.2f}MB, Peak={peak/1024/1024:.2f}MB")

class TimeoutError(Exception):
    """Custom exception for operation timeouts"""
    pass

def timeout_handler(signum, frame):
    """Handle operation timeouts"""
    global current_operation
    raise TimeoutError(f"Operation timed out: {current_operation}")

def with_timeout(func, timeout_sec, *args, **kwargs):
    """Run a function with a timeout"""
    # Set the timeout handler
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_sec)
    
    try:
        result = func(*args, **kwargs)
        # Cancel the alarm if the function completes
        signal.alarm(0)
        return result
    except TimeoutError as e:
        logger.error(f"{e}")
        # Reset the function name but keep the alarm active to terminate
        raise
    finally:
        # Always cancel the alarm to be safe
        signal.alarm(0)

def create_test_document():
    """Create a test document for processing"""
    start_operation("create_test_document")
    log_memory_usage("before creating test document")
    
    try:
        # Create a test case
        case_id = str(uuid.uuid4())
        logger.info(f"Creating test case with ID: {case_id}")
        
        case = db_service.create_case(
            user_id="test_user",
            title="Test Case for Document Processing Debug",
            description="Created via improved test script"
        )
        
        if not case:
            logger.error("Failed to create test case")
            end_operation()
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
            end_operation()
            return None
            
        document_id = document["id"]
        logger.info(f"Test document created with ID: {document_id}")
        
        log_memory_usage("after creating test document")
        end_operation()
        return document_id
    except Exception as e:
        logger.error(f"Error in create_test_document: {str(e)}")
        end_operation()
        return None

def debug_document_processing(document_id):
    """Process the document in debug mode with detailed monitoring"""
    try:
        logger.info(f"Starting debug processing for document: {document_id}")
        log_memory_usage("before processing")
        
        # Initialize vector store
        start_operation("init_vector_store")
        with_timeout(init_vector_store, 10)
        end_operation()
        
        # Break down the process into smaller steps to identify the bottleneck
        
        # Step 1: Get document info
        start_operation("get_document_info")
        document = with_timeout(db_service.get_row_by_id, 5, "document", document_id)
        end_operation()
        
        if not document:
            logger.error(f"Document with ID {document_id} not found")
            return {"status": "failed", "error": "Document not found"}
        
        logger.info(f"Document found: {document}")
        storage_path = document["storage_path"]
        mimetype = document["mimetype"]
        
        # Step 2: Read file content
        start_operation("read_file_content")
        file_content = with_timeout(db_service.get_document_file, 5, storage_path)
        end_operation()
        
        if not file_content:
            logger.error(f"Could not read file from {storage_path}")
            return {"status": "failed", "error": "File not readable"}
        
        logger.info(f"Read file content, size: {len(file_content)} bytes")
        
        # Step 3: Parse document
        start_operation("parse_document")
        if mimetype == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            import docx2txt
            text_content = with_timeout(docx2txt.process, 10, file_content)
        elif mimetype == "text/plain":
            text_content = file_content.decode("utf-8")
        else:
            text_content = file_content.decode("utf-8", errors="ignore")
        end_operation()
            
        logger.info(f"Parsed document, text length: {len(text_content)}")
        
        # Step 4: Chunk document
        start_operation("chunk_document")
        chunks = with_timeout(
            chunk_document, 
            15, 
            text_content, 
            settings.CHUNK_SIZE, 
            settings.CHUNK_OVERLAP
        )
        end_operation()
        
        logger.info(f"Document chunked into {len(chunks)} chunks")
        log_memory_usage("after chunking")
        
        # Step 5: Process chunks with embedding - this is where we expect the issue
        chunks_processed = 0
        chunks_with_error = 0
        
        # Process each chunk individually to identify which one might be causing the issue
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1} of {len(chunks)}")
            log_memory_usage(f"before processing chunk {i+1}")
            
            try:
                # Force garbage collection before each chunk
                gc.collect()
                
                # Create metadata for this chunk
                metadata = {
                    "document_name": document["filename"],
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "case_id": document["case_id"]
                }
                
                # Step 5a: Generate embedding with timeout
                logger.info(f"Generating embedding for chunk {i+1}")
                start_operation(f"generate_embedding_chunk_{i+1}")
                try:
                    chunk_embedding = with_timeout(generate_embedding, 15, chunk)
                    logger.info(f"Generated embedding with {len(chunk_embedding)} dimensions")
                except TimeoutError:
                    logger.error(f"Timeout generating embedding for chunk {i+1}")
                    chunks_with_error += 1
                    end_operation()
                    continue
                end_operation()
                
                # Step 5b: Store embedding
                logger.info(f"Storing embedding for chunk {i+1}")
                start_operation(f"store_embedding_chunk_{i+1}")
                try:
                    from app.utils.vector_store import add_embedding
                    
                    chunk_id = f"{document_id}_{i}"
                    embedding_id = with_timeout(
                        add_embedding,
                        10,
                        document_id=document_id,
                        chunk_id=chunk_id,
                        content=chunk,
                        embedding=chunk_embedding,
                        metadata=metadata
                    )
                    
                    if embedding_id:
                        logger.info(f"Successfully stored embedding with ID: {embedding_id}")
                    else:
                        logger.error(f"Failed to store embedding for chunk {i+1}")
                        chunks_with_error += 1
                except TimeoutError:
                    logger.error(f"Timeout storing embedding for chunk {i+1}")
                    chunks_with_error += 1
                except Exception as e:
                    logger.error(f"Error storing embedding: {str(e)}")
                    chunks_with_error += 1
                end_operation()
                
                # Step 5c: Store document chunk
                logger.info(f"Storing document chunk {i+1}")
                start_operation(f"store_document_chunk_{i+1}")
                try:
                    chunk_record = with_timeout(
                        db_service.create_document_chunk,
                        10,
                        document_id=document_id,
                        content=chunk,
                        chunk_index=i,
                        metadata=metadata
                    )
                    
                    if chunk_record:
                        logger.info(f"Successfully stored document chunk")
                        chunks_processed += 1
                    else:
                        logger.error(f"Failed to store document chunk {i+1}")
                        chunks_with_error += 1
                except TimeoutError:
                    logger.error(f"Timeout storing document chunk {i+1}")
                    chunks_with_error += 1
                except Exception as e:
                    logger.error(f"Error storing document chunk: {str(e)}")
                    chunks_with_error += 1
                end_operation()
                
                log_memory_usage(f"after processing chunk {i+1}")
                
            except Exception as chunk_error:
                logger.error(f"Error processing chunk {i+1}: {str(chunk_error)}")
                chunks_with_error += 1
        
        # Step 6: Update document status
        start_operation("update_document_status")
        with_timeout(
            db_service.update_document_status,
            5,
            document_id,
            "processed"
        )
        end_operation()
        
        logger.info(f"Processing completed: {chunks_processed} chunks processed, {chunks_with_error} chunks with errors")
        log_memory_usage("after processing all chunks")
        
        # Print timing summary
        logger.info("--- Timing Summary ---")
        for operation, duration in timings.items():
            logger.info(f"{operation}: {duration:.2f} seconds")
            
        return {
            "status": "success",
            "document_id": document_id,
            "chunks_total": len(chunks),
            "chunks_processed": chunks_processed,
            "chunks_with_error": chunks_with_error,
            "timings": timings
        }
        
    except Exception as e:
        logger.error(f"Critical error in debug processing: {str(e)}")
        try:
            db_service.update_document_status(document_id, "failed", str(e))
        except Exception as update_error:
            logger.error(f"Failed to update document status: {str(update_error)}")
            
        return {"status": "failed", "document_id": document_id, "error": str(e)}

def search_documents(case_id, query_text):
    """
    Test vector search functionality to ensure the entire pipeline is working
    """
    logger.info(f"Testing vector search with query: '{query_text}'")
    start_operation("search_documents")
    
    try:
        from app.utils.embeddings import generate_query_embedding
        
        # Generate embedding for the query
        query_embedding = with_timeout(generate_query_embedding, 10, query_text)
        
        # Search for similar chunks
        similar_chunks = with_timeout(
            db_service.similarity_search,
            10,
            query_embedding=query_embedding,
            case_id=case_id,
            match_threshold=0.5,
            match_count=5
        )
        
        if similar_chunks:
            logger.info(f"Found {len(similar_chunks)} similar chunks")
            # Print the top results
            for i, chunk in enumerate(similar_chunks[:3]):
                logger.info(f"Result {i+1}: Similarity={chunk['similarity']:.4f}")
                logger.info(f"Content: {chunk['content'][:100]}...")
        else:
            logger.warning("No similar chunks found")
            
        end_operation()
        return similar_chunks
    except Exception as e:
        logger.error(f"Error in search_documents: {str(e)}")
        end_operation()
        return []

def main():
    """Main function to run the improved test"""
    logger.info("=== IMPROVED DOCUMENT PROCESSING DEBUG TEST ===")
    
    # Create and process a test document
    document_id = create_test_document()
    
    if not document_id:
        logger.error("Test setup failed - could not create test document")
        sys.exit(1)
    
    # Process the document with detailed monitoring
    process_result = debug_document_processing(document_id)
    
    if process_result and process_result.get("status") == "success":
        logger.info("Document successfully processed in debug mode")
        
        # Test the search functionality
        document = db_service.get_row_by_id("document", document_id)
        if document:
            case_id = document["case_id"]
            search_result = search_documents(case_id, "Welke beperkingen heeft de werknemer?")
            logger.info(f"Search test {'passed' if search_result else 'failed'}")
    else:
        logger.error("Document processing failed in debug mode")
    
    # Final memory usage report
    log_memory_usage("end of test")
    
    # Print timing summary again
    logger.info("=== Final Timing Summary ===")
    for operation, duration in sorted(timings.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"{operation}: {duration:.2f} seconds")

if __name__ == "__main__":
    main()