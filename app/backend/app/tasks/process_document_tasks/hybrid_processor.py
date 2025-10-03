"""
Hybrid document processor for RAG implementation.

This module implements the hybrid approach for document processing,
combining direct LLM access for small documents with asynchronous
vector embedding generation for larger documents.
"""
import gc
import time
import logging
from typing import Dict, Any, List, Optional

from celery import shared_task

from app.db.database_service import get_database_service
from app.tasks.process_document_tasks.document_classifier import (
    DocumentClassifier, DocumentSize, ProcessingStrategy
)
from app.utils.vector_store_improved import get_hybrid_vector_store
from app.utils.embeddings import generate_embedding

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
db_service = get_database_service()
vector_store = get_hybrid_vector_store(db_service)


async def process_document_by_strategy(
    document_id: str,
    strategy: ProcessingStrategy,
    chunks: List[str]
) -> Dict[str, Any]:
    """
    Process a document according to its specific strategy using the hybrid vector store.

    Args:
        document_id: The ID of the document to process
        strategy: Processing strategy to apply
        chunks: Document chunks already created

    Returns:
        Dictionary with processing results
    """
    try:
        # Prepare chunks in the format expected by the processor
        formatted_chunks = []
        for i, content in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{i}"
            formatted_chunks.append({
                "id": chunk_id,
                "content": content,
                "index": i
            })

        # Process using the appropriate strategy
        result = vector_store.process_document_vectors(
            document_id=document_id,
            chunks=formatted_chunks,
            strategy=strategy.value
        )

        # For direct or hybrid strategies, we mark as processed immediately
        if strategy in [ProcessingStrategy.DIRECT_LLM, ProcessingStrategy.HYBRID]:
            # These strategies provide immediate results, so update status
            db_service.update_document_status(document_id, "processed")

        if strategy == ProcessingStrategy.FULL_RAG:
            # For full RAG, mark as enhanced once processing is complete
            if result.get("embeddings_added", 0) > 0:
                db_service.update_document_status(document_id, "enhanced")

        return result

    except Exception as e:
        logger.error(f"Error in strategy-specific processing for document {document_id}: {str(e)}")
        return {"status": "error", "message": str(e)}


async def process_document_hybrid(document_id: str) -> Dict[str, Any]:
    """
    Process a document using the hybrid approach.

    This function serves as the main entry point for document processing:
    1. Immediately mark document as "processed" for quick user feedback
    2. Classify document to determine optimal strategy
    3. Process document according to its optimal strategy

    Args:
        document_id: The ID of the document to process

    Returns:
        Dictionary with processing status and info
    """
    start_time = time.time()
    logger.info(f"Starting hybrid processing for document {document_id}")
    
    try:
        # Get document from database
        document = db_service.get_document(document_id)
        if not document:
            logger.error(f"Document not found: {document_id}")
            return {"status": "error", "message": f"Document not found: {document_id}"}
        
        # Mark document as processed immediately for UI responsiveness
        db_service.update_document_status(document_id, "processed")
        
        # Classify document to determine strategy
        classifier = DocumentClassifier(db_service)
        size, strategy, priority = classifier.classify_document(document_id)
        
        # Create minimal chunks for the document
        simple_chunks = create_simple_chunks(document.get("content", ""))
        
        # Store chunks in database without embeddings
        for i, chunk in enumerate(simple_chunks):
            db_service.add_document_chunk(
                document_id=document_id,
                chunk_index=i,
                content=chunk,
                metadata={"strategy": strategy.value, "size": size.value}
            )
        
        # Get the strategy-specific processor
        result = await process_document_by_strategy(document_id, strategy, simple_chunks)
        logger.info(f"Document {document_id} initial processing with {strategy} strategy: {result}")
        
        processing_time = time.time() - start_time
        logger.info(f"Completed initial processing for document {document_id} in {processing_time:.2f}s")
        
        return {
            "status": "success",
            "document_id": document_id,
            "size": size.value,
            "strategy": strategy.value,
            "chunks": len(simple_chunks),
            "processing_time": processing_time
        }
    
    except Exception as e:
        logger.error(f"Error in hybrid document processing: {str(e)}")
        # Ensure document status is updated even on error
        db_service.update_document_status(document_id, "error")
        return {"status": "error", "message": str(e)}


def create_simple_chunks(text: str, chunk_size: int = 1000, chunk_overlap: int = 100) -> List[str]:
    """
    Create simple text chunks from document content.
    
    Args:
        text: The document text to chunk
        chunk_size: Target size of each chunk in characters
        chunk_overlap: Overlap between chunks in characters
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
        
    chunks = []
    start = 0
    
    while start < len(text):
        # Take a chunk of text
        end = min(start + chunk_size, len(text))
        
        # If we're not at the end, try to break at a paragraph or sentence
        if end < len(text):
            # Look for paragraph break
            paragraph_break = text.rfind("\n\n", start, end)
            if paragraph_break != -1 and paragraph_break > start + chunk_size / 2:
                end = paragraph_break + 2
            else:
                # Look for sentence break (period followed by space)
                sentence_break = text.rfind(". ", start, end)
                if sentence_break != -1 and sentence_break > start + chunk_size / 2:
                    end = sentence_break + 2
        
        chunk = text[start:end]
        chunks.append(chunk)
        
        # Move start position with overlap
        start = end - chunk_overlap
        
        # Prevent getting stuck
        if start >= end - 1:
            start = end
    
    return chunks


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_document_embeddings(self, document_id: str, batch_size: int = 5) -> Dict[str, Any]:
    """
    Generate embeddings for document chunks in batches.
    
    Args:
        document_id: The ID of the document to generate embeddings for
        batch_size: Number of chunks to process in each batch
        
    Returns:
        Dictionary with status and processing information
    """
    start_time = time.time()
    logger.info(f"Starting embedding generation for document {document_id}")
    
    try:
        # Get document chunks from database
        chunks = db_service.get_document_chunks(document_id)
        if not chunks:
            logger.warning(f"No chunks found for document {document_id}")
            return {"status": "warning", "message": f"No chunks found for document {document_id}"}
        
        total_chunks = len(chunks)
        processed_chunks = 0
        successful_embeddings = 0
        
        # Process chunks in batches
        for i in range(0, total_chunks, batch_size):
            batch = chunks[i:i+batch_size]
            
            for chunk in batch:
                chunk_id = chunk.get("id")
                content = chunk.get("content", "")
                
                if not content or not chunk_id:
                    logger.warning(f"Empty content or missing ID for chunk in document {document_id}")
                    continue
                
                try:
                    # Generate embedding for the chunk
                    embedding = generate_embedding(content)
                    
                    # Store embedding in vector store with improved metadata
                    vector_store.add_embedding(
                        document_id=document_id,
                        chunk_id=chunk_id,
                        embedding=embedding,
                        content=content,
                        metadata={
                            **(chunk.get("metadata", {})),
                            "strategy": chunk.get("metadata", {}).get("strategy", ProcessingStrategy.HYBRID.value)
                        }
                    )
                    
                    successful_embeddings += 1
                except Exception as chunk_error:
                    logger.error(f"Error generating embedding for chunk {chunk_id}: {str(chunk_error)}")
                
                processed_chunks += 1
            
            # Log progress
            progress = (processed_chunks / total_chunks) * 100
            logger.info(f"Document {document_id} embedding progress: {progress:.1f}% ({processed_chunks}/{total_chunks})")
            
            # Force garbage collection after each batch
            gc.collect()
        
        # Update document status to enhanced if any embeddings were successful
        if successful_embeddings > 0:
            db_service.update_document_status(document_id, "enhanced")
            
        processing_time = time.time() - start_time
        logger.info(f"Completed embedding generation for document {document_id} in {processing_time:.2f}s")
        
        return {
            "status": "success",
            "document_id": document_id,
            "total_chunks": total_chunks,
            "successful_embeddings": successful_embeddings,
            "processing_time": processing_time
        }
    
    except Exception as e:
        logger.error(f"Error generating embeddings: {str(e)}")
        
        # Retry the task if within retry limits
        try:
            self.retry(exc=e)
        except Exception as retry_error:
            logger.error(f"Retry failed: {str(retry_error)}")
            return {"status": "error", "message": str(e)}