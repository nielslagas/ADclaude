"""
Debug script for document processing to help identify where it's getting stuck.
"""
import docx2txt
import os
import gc  # For garbage collection
from datetime import datetime
import time
from uuid import UUID
import json

from app.db.database_service import db_service
from app.tasks.process_document_tasks.document_chunker import chunk_document
from app.utils.embeddings import generate_embedding


def debug_document_processing(document_id: str):
    """
    Debug version of document processing to find where it hangs.
    """
    # Create debug log file
    debug_log_path = "/app/debug_processing.log"
    
    def log_debug(message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(debug_log_path, "a") as f:
            f.write(f"{timestamp} - {message}\n")
    
    try:
        log_debug(f"Starting debug document processing for ID: {document_id}")
        
        # Get document info from database
        log_debug("Getting document from database")
        document = db_service.get_row_by_id("document", document_id)
        
        if not document:
            log_debug(f"Document with ID {document_id} not found")
            return
        
        log_debug(f"Document found: {document}")
        storage_path = document["storage_path"]
        mimetype = document["mimetype"]
        
        # Read file from local storage
        log_debug(f"Reading file from {storage_path}")
        file_content = db_service.get_document_file(storage_path)
        
        if not file_content:
            log_debug(f"Could not read file from {storage_path}")
            return
        
        log_debug(f"Read file, size: {len(file_content)} bytes")
        
        # Parse document based on mimetype
        log_debug(f"Parsing document with mimetype: {mimetype}")
        try:
            if mimetype == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                # For .docx files, use docx2txt
                text_content = docx2txt.process(file_content)
                log_debug(f"Parsed DOCX file, text length: {len(text_content)}")
            elif mimetype == "text/plain":
                # For .txt files
                text_content = file_content.decode("utf-8")
                log_debug(f"Parsed TXT file, text length: {len(text_content)}")
            else:
                # Fall back to treating as text for other types
                log_debug(f"Unsupported mimetype: {mimetype}, trying as text")
                text_content = file_content.decode("utf-8", errors="ignore")
        except Exception as e:
            log_debug(f"Error parsing document: {str(e)}")
            return
        
        # Chunk the document
        try:
            log_debug("Starting document chunking")
            chunks = chunk_document(text_content, 1000, 200)
            log_debug(f"Document chunked into {len(chunks)} chunks")
            
            for i, chunk in enumerate(chunks):
                log_debug(f"Processing chunk {i+1}/{len(chunks)}, length: {len(chunk)}")
        except Exception as e:
            log_debug(f"Error chunking document: {str(e)}")
            return
        
        # Process each chunk
        chunks_processed = 0
        chunks_with_error = 0
        
        for i, chunk in enumerate(chunks):
            try:
                log_debug(f"Starting processing of chunk {i+1}/{len(chunks)}")
                
                # Create chunk metadata
                metadata = {
                    "document_name": document["filename"],
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "case_id": document["case_id"]
                }
                
                # Generate embedding for the chunk
                try:
                    log_debug(f"Generating embedding for chunk {i+1}")
                    start_time = time.time()
                    chunk_embedding = generate_embedding(chunk)
                    log_debug(f"Generated embedding in {time.time() - start_time:.2f} seconds, vector length: {len(chunk_embedding)}")
                    
                    # Store the chunk with embeddings in vector store
                    log_debug(f"Storing chunk {i+1} in vector store")
                    chunk_id = f"{document_id}_{i}"
                    from app.utils.vector_store import add_embedding
                    
                    # Check if document_embeddings table exists
                    log_debug("Checking if document_embeddings table exists")
                    with db_service.engine.connect() as conn:
                        result = conn.execute("""
                            SELECT EXISTS (
                                SELECT FROM pg_tables 
                                WHERE schemaname = 'public' 
                                AND tablename = 'document_embeddings'
                            );
                        """)
                        table_exists = result.scalar()
                        log_debug(f"document_embeddings table exists: {table_exists}")
                    
                    # Add embedding to vector store
                    log_debug(f"Adding embedding to vector store, vector length: {len(chunk_embedding)}")
                    embedding_id = add_embedding(
                        document_id=document_id,
                        chunk_id=chunk_id,
                        content=chunk,
                        embedding=chunk_embedding,
                        metadata=metadata
                    )
                    log_debug(f"Added embedding with ID: {embedding_id}")
                    
                    # Also store in regular document_chunk table
                    log_debug(f"Storing chunk {i+1} in document_chunk table")
                    chunk_record = db_service.create_document_chunk(
                        document_id=document_id,
                        content=chunk,
                        chunk_index=i,
                        metadata=metadata
                    )
                    log_debug(f"Created document chunk record: {chunk_record['id'] if chunk_record else None}")
                    
                    if chunk_record and embedding_id:
                        chunks_processed += 1
                    else:
                        chunks_with_error += 1
                        
                except Exception as chunk_error:
                    log_debug(f"Error processing chunk {i}: {str(chunk_error)}")
                    chunks_with_error += 1
                    
            except Exception as e:
                log_debug(f"Error processing chunk {i}: {str(e)}")
                chunks_with_error += 1
        
        log_debug(f"Document processing completed: {chunks_processed} chunks processed, {chunks_with_error} chunks with errors")
        
        # Update document status to processed even if some chunks failed
        log_debug("Updating document status to processed")
        db_service.update_document_status(document_id, "processed")
        
        log_debug("Document processing debug complete")
        
    except Exception as e:
        log_debug(f"Critical error in document processing: {str(e)}")
            
    return


if __name__ == "__main__":
    # For manual execution
    pass