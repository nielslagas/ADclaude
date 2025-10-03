"""
Improved document processor that stores document chunks AND generates embeddings
for RAG functionality.
"""
import os
import logging
import time
import gc
from datetime import datetime
from uuid import UUID

from app.celery_worker import celery
from app.db.database_service import db_service
from app.core.config import settings
from app.utils.embeddings import generate_embedding
from app.utils.vector_store_improved import add_embedding

# Set up logging
logger = logging.getLogger(__name__)

def simple_chunking(text, chunk_size, chunk_overlap):
    """
    Extremely simple chunking method for text documents
    """
    if not text:
        return []
        
    chunks = []
    start = 0
    
    while start < len(text):
        # Take a simple chunk
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]
        chunks.append(chunk)
        
        # Move start position
        start = end - chunk_overlap
        
        # Prevent getting stuck
        if start >= end - 1:
            start = end
    
    return chunks

@celery.task
def process_document_improved(document_id: str):
    """
    Improved document processor that:
    1. Reads the document
    2. Splits it into chunks
    3. Stores the chunks in the database
    4. Generates embeddings for each chunk
    5. Stores embeddings for RAG functionality
    6. Marks the document as processed
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting simplified document processing for ID: {document_id}")
        
        # Get document info from database
        document = db_service.get_row_by_id("document", document_id)
        
        if not document:
            logger.error(f"Document with ID {document_id} not found")
            return {"status": "failed", "document_id": document_id, "error": "Document not found"}
        
        logger.info(f"Document found: {document['filename']}")
        storage_path = document["storage_path"]
        mimetype = document["mimetype"]
        
        # Read file from local storage
        file_content = db_service.get_document_file(storage_path)
        
        if not file_content:
            logger.error(f"Could not read file from {storage_path}")
            db_service.update_document_status(document_id, "failed", f"Could not read file")
            return {"status": "failed", "document_id": document_id, "error": "Could not read file"}
        
        logger.info(f"Read file from {storage_path}, size: {len(file_content)} bytes")
        
        # Parse document based on mimetype
        if mimetype == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            # For .docx files
            import docx2txt
            text_content = docx2txt.process(file_content)
        elif mimetype == "text/plain":
            # For .txt files
            text_content = file_content.decode("utf-8")
        else:
            # Fall back to treating as text for other types
            text_content = file_content.decode("utf-8", errors="ignore")
        
        # Clear file_content from memory
        del file_content
        gc.collect()
        
        # Chunk the document using simple chunking
        chunks = simple_chunking(text_content, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
        logger.info(f"Document chunked into {len(chunks)} chunks")
        
        # Clear text_content from memory
        del text_content
        gc.collect()
        
        # Store chunks in database and generate embeddings
        chunks_processed = 0
        chunks_with_error = 0
        embeddings_processed = 0
        embeddings_with_error = 0
        
        for i, chunk in enumerate(chunks):
            # Force gc collection for every chunk to keep memory usage low
            gc.collect()
            
            try:
                # Create metadata for this chunk
                metadata = {
                    "document_name": document["filename"],
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "case_id": document["case_id"],
                    "strategy": "hybrid"  # Mark as hybrid strategy
                }
                
                # Store document chunk
                chunk_record = db_service.create_document_chunk(
                    document_id=document_id,
                    content=chunk,
                    chunk_index=i,
                    metadata=metadata
                )
                
                if chunk_record:
                    chunks_processed += 1
                    chunk_id = chunk_record["id"]
                    
                    # Generate embedding for this chunk
                    try:
                        logger.info(f"Generating embedding for chunk {i+1}/{len(chunks)}")
                        embedding = generate_embedding(chunk)
                        
                        if embedding:
                            # Store embedding in vector store
                            embedding_id = add_embedding(
                                document_id=document_id,
                                chunk_id=chunk_id,
                                content=chunk,
                                embedding=embedding,
                                metadata=metadata
                            )
                            
                            if embedding_id:
                                embeddings_processed += 1
                                logger.info(f"Embedding {i+1}/{len(chunks)} stored successfully")
                            else:
                                embeddings_with_error += 1
                                logger.warning(f"Failed to store embedding for chunk {i}")
                        else:
                            embeddings_with_error += 1
                            logger.warning(f"Failed to generate embedding for chunk {i}")
                            
                    except Exception as embedding_error:
                        embeddings_with_error += 1
                        logger.error(f"Error generating/storing embedding for chunk {i}: {str(embedding_error)}")
                        # Continue with other chunks even if embedding fails
                        
                else:
                    chunks_with_error += 1
                    
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {str(e)}")
                chunks_with_error += 1
        
        # Update document status to processed
        db_service.update_document_status(document_id, "processed")
        
        # Update document metadata to indicate embeddings are available
        document_metadata = {
            "embeddings_available": embeddings_processed > 0,
            "total_chunks": len(chunks),
            "chunks_processed": chunks_processed,
            "embeddings_processed": embeddings_processed,
            "processing_strategy": "hybrid",
            "processed_at": datetime.utcnow().isoformat()
        }
        db_service.update_document_metadata(document_id, document_metadata)
        
        total_time = time.time() - start_time
        logger.info(f"Document processing completed in {total_time:.2f}s: {chunks_processed} chunks processed, {embeddings_processed} embeddings generated")
        
        return {
            "status": "success", 
            "document_id": document_id, 
            "chunks_total": len(chunks),
            "chunks_processed": chunks_processed,
            "chunks_with_error": chunks_with_error,
            "embeddings_processed": embeddings_processed,
            "embeddings_with_error": embeddings_with_error,
            "processing_time": total_time
        }
    
    except Exception as e:
        logger.error(f"Critical error in document processing: {str(e)}")
        # Update document status to failed
        try:
            db_service.update_document_status(document_id, "failed", str(e))
        except Exception as update_error:
            logger.error(f"Failed to update document status: {str(update_error)}")
            
        return {"status": "failed", "document_id": document_id, "error": str(e)}