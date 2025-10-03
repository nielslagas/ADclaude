"""
Document processor with hybrid approach:
1. Documents are immediately processed and available (direct approach)
2. Embeddings are generated asynchronously in the background (RAG approach)
3. Small documents use direct LLM, large documents use RAG when embeddings are ready
"""
import os
import logging
import time
import gc
from datetime import datetime
from uuid import UUID
import sys

from app.celery_worker import celery
from app.db.database_service import db_service
from app.core.config import settings
from app.utils.embeddings import generate_embedding

# Set up logging
logger = logging.getLogger(__name__)

# Constants for document size classification
SMALL_DOCUMENT_THRESHOLD = 20000  # Characters (roughly 10 pages)
MEDIUM_DOCUMENT_THRESHOLD = 60000  # Characters (roughly 30 pages)

def simple_chunking(text, chunk_size, chunk_overlap):
    """
    Simple chunking method for text documents with improved paragraph handling
    """
    if not text:
        return []
        
    # Split by paragraphs first
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # Skip empty paragraphs
        if not paragraph.strip():
            continue
            
        # If adding this paragraph would exceed the chunk size,
        # save the current chunk and start a new one
        if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
            chunks.append(current_chunk)
            
            # Start new chunk with overlap
            words = current_chunk.split()
            overlap_words = words[-min(len(words), chunk_overlap // 5):]  # ~5 chars per word
            current_chunk = ' '.join(overlap_words) + ' ' + paragraph
        else:
            # Add to current chunk
            if current_chunk:
                current_chunk += '\n\n' + paragraph
            else:
                current_chunk = paragraph
    
    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def get_document_size_category(text_length):
    """
    Categorize document size for determining processing approach
    """
    if text_length < SMALL_DOCUMENT_THRESHOLD:
        return "small"
    elif text_length < MEDIUM_DOCUMENT_THRESHOLD:
        return "medium"
    else:
        return "large"

@celery.task(name="app.tasks.process_document_tasks.document_processor_hybrid.process_document_hybrid")
def process_document_hybrid(document_id: str):
    logger.info(f"process_document_hybrid task called with ID: {document_id}")
    """
    Hybrid document processor that:
    1. Reads the document
    2. Splits it into chunks
    3. Stores the chunks in the database
    4. Marks the document as processed immediately
    5. Schedules asynchronous embedding generation
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting hybrid document processing for ID: {document_id}")
        
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
        elif mimetype == "application/pdf":
            # For .pdf files
            try:
                import pdfplumber
                import io

                logger.info(f"Processing PDF file: {document['filename']}")

                with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                    text_pages = []
                    total_pages = len(pdf.pages)
                    logger.info(f"PDF has {total_pages} pages")

                    for page_num, page in enumerate(pdf.pages, 1):
                        try:
                            text = page.extract_text()
                            if text:
                                text_pages.append(f"--- Pagina {page_num} van {total_pages} ---\n{text}")
                                logger.debug(f"Extracted {len(text)} characters from page {page_num}")
                        except Exception as page_error:
                            logger.error(f"Error extracting text from page {page_num}: {page_error}")
                            text_pages.append(f"--- Pagina {page_num} van {total_pages} ---\n[Fout bij extractie]")

                    text_content = "\n\n".join(text_pages)

                    # Detect if PDF is scanned (minimal extractable text) and attempt OCR
                    if len(text_content.strip()) < 100:
                        logger.warning(f"PDF {document['filename']} appears to be scanned - only {len(text_content.strip())} characters extracted")
                        logger.warning("Attempting OCR on scanned PDF")

                        from app.utils.ocr_processor import ocr_pdf, is_tesseract_available

                        if is_tesseract_available():
                            logger.info(f"Running OCR on scanned PDF: {document['filename']}")

                            # Run OCR with Dutch and English language support
                            ocr_text = ocr_pdf(file_content, language="nld+eng", dpi=300)

                            if ocr_text and len(ocr_text.strip()) > 100:
                                text_content = ocr_text
                                logger.info(f"OCR successful: {len(ocr_text)} characters extracted from scanned PDF")

                                # Update document metadata to reflect OCR success
                                db_service.update_row_by_id(
                                    "document",
                                    document_id,
                                    {
                                        "metadata": {
                                            "scanned_document": True,
                                            "ocr_processed": True,
                                            "text_extracted": len(ocr_text),
                                            "ocr_language": "nld+eng"
                                        }
                                    }
                                )
                            else:
                                logger.warning("OCR extracted minimal text from scanned PDF")

                                # Update metadata to flag OCR attempt with minimal results
                                db_service.update_row_by_id(
                                    "document",
                                    document_id,
                                    {
                                        "metadata": {
                                            "scanned_document": True,
                                            "ocr_processed": True,
                                            "ocr_successful": False,
                                            "text_extracted": len(text_content.strip()),
                                            "warning": "OCR extracted minimal text - document may be low quality"
                                        }
                                    }
                                )

                                if not text_content.strip():
                                    text_content = f"[Dit PDF-document is gescand. OCR verwerking uitgevoerd maar minimale tekst geëxtraheerd. Document mogelijk van lage kwaliteit. Bestand: {document['filename']}]"
                        else:
                            logger.error("Tesseract not available - cannot OCR scanned PDF")

                            # Update metadata to flag missing OCR capability
                            db_service.update_row_by_id(
                                "document",
                                document_id,
                                {
                                    "metadata": {
                                        "scanned_document": True,
                                        "text_extracted": len(text_content.strip()),
                                        "ocr_recommended": True,
                                        "ocr_available": False,
                                        "warning": "Minimal text extracted - OCR not available on this server"
                                    }
                                }
                            )

                            if not text_content.strip():
                                text_content = f"[Dit PDF-document lijkt gescand te zijn zonder tekst. OCR-verwerking is niet beschikbaar op deze server. Bestand: {document['filename']}]"
                    else:
                        logger.info(f"Successfully extracted {len(text_content)} characters from PDF")

            except ImportError:
                logger.error("pdfplumber not installed - cannot process PDF")
                text_content = "[PDF-verwerking mislukt: pdfplumber library niet geïnstalleerd]"
                db_service.update_document_status(document_id, "failed", "PDF library niet beschikbaar")
                return {"status": "failed", "document_id": document_id, "error": "PDF library niet beschikbaar"}
            except Exception as pdf_error:
                logger.error(f"PDF processing failed for {document['filename']}: {pdf_error}")
                text_content = f"[PDF-verwerking mislukt: {str(pdf_error)}]"
                db_service.update_document_status(document_id, "failed", f"PDF verwerking fout: {str(pdf_error)}")
                return {"status": "failed", "document_id": document_id, "error": str(pdf_error)}
        elif mimetype.startswith("image/"):
            # For image files (JPG, PNG, TIFF, etc.)
            logger.info(f"Processing image file: {document['filename']} with OCR")

            from app.utils.ocr_processor import extract_text_with_ocr, is_tesseract_available

            if is_tesseract_available():
                try:
                    # Extract text from image using OCR
                    text_content = extract_text_with_ocr(
                        file_content,
                        language="nld+eng",
                        dpi=300
                    )

                    if text_content and len(text_content.strip()) > 50:
                        logger.info(f"OCR successful: {len(text_content)} characters extracted from image")

                        # Update document metadata
                        db_service.update_row(
                            "document",
                            document_id,
                            {
                                "metadata": {
                                    "image_document": True,
                                    "ocr_processed": True,
                                    "text_extracted": len(text_content),
                                    "ocr_language": "nld+eng"
                                }
                            }
                        )
                    else:
                        logger.warning(f"OCR extracted minimal text from image {document['filename']}")
                        text_content = f"[Afbeelding verwerkt met OCR maar minimale tekst geëxtraheerd ({len(text_content.strip())} karakters). Mogelijk is de afbeelding van lage kwaliteit of bevat geen tekst. Bestand: {document['filename']}]"

                        # Update metadata with warning
                        db_service.update_row(
                            "document",
                            document_id,
                            {
                                "metadata": {
                                    "image_document": True,
                                    "ocr_processed": True,
                                    "ocr_successful": False,
                                    "text_extracted": len(text_content.strip()),
                                    "warning": "OCR extracted minimal text from image"
                                }
                            }
                        )

                except Exception as ocr_error:
                    logger.error(f"Image OCR failed for {document['filename']}: {ocr_error}")
                    text_content = f"[Afbeelding OCR-verwerking mislukt: {str(ocr_error)}]"
                    db_service.update_document_status(document_id, "failed", f"Image OCR fout: {str(ocr_error)}")
                    return {"status": "failed", "document_id": document_id, "error": str(ocr_error)}
            else:
                logger.error("Tesseract not available - cannot process image")
                text_content = "[OCR niet beschikbaar op deze server - kan afbeelding niet verwerken. Installeer Tesseract OCR voor afbeeldingsondersteuning.]"

                # Update metadata
                db_service.update_row(
                    "document",
                    document_id,
                    {
                        "metadata": {
                            "image_document": True,
                            "ocr_available": False,
                            "warning": "OCR not available - cannot process image"
                        }
                    }
                )
        else:
            # Fall back to treating as text for other types
            text_content = file_content.decode("utf-8", errors="ignore")
        
        # Clear file_content from memory
        del file_content
        gc.collect()
        
        # Determine document size category
        size_category = get_document_size_category(len(text_content))
        logger.info(f"Document categorized as '{size_category}' size")
        
        # Chunk the document using simple chunking
        chunks = simple_chunking(text_content, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
        logger.info(f"Document chunked into {len(chunks)} chunks")
        
        # Update metadata with document size info
        document_metadata = {
            "size_category": size_category,
            "chunks_count": len(chunks),
            "text_length": len(text_content),
            "processed_at": datetime.utcnow().isoformat()
        }
        
        # Skip updating document metadata if the column doesn't exist
        # We'll just log the metadata for debugging
        logger.info(f"Document metadata: {document_metadata}")
        
        # In a production environment, we would add the metadata column to the document table
        # For now, we'll just continue without updating metadata
        try:
            import json
            from app.utils.vector_store import UUIDEncoder
            db_service.update_row("document", document_id, {"metadata": json.dumps(document_metadata, cls=UUIDEncoder)})
        except Exception as e:
            # Log the error but continue processing
            logger.warning(f"Could not update document metadata: {str(e)}")
        
        # Store chunks in database
        chunks_processed = 0
        chunks_with_error = 0
        chunk_ids = []
        
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
                    "size_category": size_category
                }
                
                # Store document chunk using the original method signature
                chunk_record = db_service.create_document_chunk(
                    document_id=document_id,
                    content=chunk,
                    chunk_index=i,
                    metadata=metadata
                )
                
                if chunk_record:
                    chunks_processed += 1
                    # Get the ID from the chunk record
                    chunk_ids.append(chunk_record["id"])
                else:
                    chunks_with_error += 1
                    
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {str(e)}")
                chunks_with_error += 1
        
        # Clear text_content from memory
        del text_content
        gc.collect()
        
        # Update document status to processed IMMEDIATELY
        db_service.update_document_status(document_id, "processed")
        
        total_time = time.time() - start_time
        logger.info(f"Initial document processing completed in {total_time:.2f}s: {chunks_processed} chunks processed, {chunks_with_error} chunks with errors")
        
        # Schedule asynchronous embedding generation based on document size
        if size_category == "small":
            # For small documents, generate embeddings immediately with high priority
            priority = 5
            delay_seconds = 1
        elif size_category == "medium":
            # Medium priority for medium sized documents
            priority = 3
            delay_seconds = 5
        else:
            # Lowest priority for large documents
            priority = 1
            delay_seconds = 10
            
        # Queue the asynchronous embedding task
        if chunks_processed > 0:
            generate_document_embeddings.apply_async(
                args=[document_id, chunk_ids],
                countdown=delay_seconds,
                priority=priority
            )
            logger.info(f"Scheduled asynchronous embedding generation with priority {priority}")
        
        return {
            "status": "success", 
            "document_id": document_id, 
            "chunks_total": len(chunks),
            "chunks_processed": chunks_processed,
            "chunks_with_error": chunks_with_error,
            "size_category": size_category,
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

@celery.task(name="app.tasks.process_document_tasks.document_processor_hybrid.generate_document_embeddings", bind=True, max_retries=3)
def generate_document_embeddings(self, document_id, chunk_ids):
    """
    Asynchronous task to generate embeddings for document chunks.
    This runs in the background after the document is already marked as processed.
    """
    logger.info(f"Starting asynchronous embedding generation for document {document_id}")
    start_time = time.time()
    
    try:
        from app.utils.vector_store_improved import batch_add_embeddings
        
        # Get document info
        document = db_service.get_row_by_id("document", document_id)
        if not document:
            logger.error(f"Document {document_id} not found for embedding generation")
            return {"status": "failed", "error": "Document not found"}
            
        # Get document chunks
        chunks_data = []
        for chunk_id in chunk_ids:
            chunk = db_service.get_document_chunk(chunk_id)
            if chunk:
                chunks_data.append(chunk)
                
        logger.info(f"Retrieved {len(chunks_data)} chunks for embedding generation")
        
        # Prepare batch embeddings data
        embeddings_data = []
        total_chunks = len(chunks_data)
        chunks_processed = 0
        chunks_failed = 0
        
        # Process in mini-batches to avoid memory issues
        mini_batch_size = 3
        for i in range(0, total_chunks, mini_batch_size):
            mini_batch = chunks_data[i:i+mini_batch_size]
            logger.info(f"Processing embedding mini-batch {i//mini_batch_size + 1}/{(total_chunks-1)//mini_batch_size + 1}")
            
            for chunk in mini_batch:
                try:
                    # Force garbage collection
                    gc.collect()
                    
                    # Generate embedding
                    embedding = generate_embedding(chunk["content"])
                    
                    # Add to batch data
                    embeddings_data.append({
                        "document_id": document_id,
                        "chunk_id": chunk["id"],
                        "content": chunk["content"],
                        "embedding": embedding,
                        "metadata": chunk["metadata"]
                    })
                    
                    chunks_processed += 1
                    
                    # Log progress for large documents
                    if total_chunks > 10 and chunks_processed % 5 == 0:
                        logger.info(f"Embedding progress: {chunks_processed}/{total_chunks} chunks processed")
                        
                except Exception as e:
                    logger.error(f"Error generating embedding for chunk {chunk['id']}: {str(e)}")
                    chunks_failed += 1
                    
            # Add batch to vector store
            if embeddings_data:
                try:
                    batch_result = batch_add_embeddings(
                        embeddings_data=embeddings_data,
                        batch_size=10,  # Process in smaller sub-batches
                        timeout=60      # Longer timeout for batch operations
                    )
                    logger.info(f"Batch embedding result: {batch_result}")
                    
                    # Clear batch data after successful storage
                    embeddings_data = []
                except Exception as e:
                    logger.error(f"Error storing batch embeddings: {str(e)}")
        
        # Update document status to indicate embeddings are available
        logger.info(f"Embeddings generated: {chunks_processed} chunks, {chunks_failed} failures")
        
        # Update document status without metadata
        db_service.update_row("document", document_id, {
            "status": "enhanced"  # Mark as enhanced when embeddings are available
        })
        
        total_time = time.time() - start_time
        logger.info(f"Asynchronous embedding generation completed in {total_time:.2f}s: {chunks_processed} chunks processed, {chunks_failed} chunks failed")
        
        return {
            "status": "success",
            "document_id": document_id,
            "chunks_processed": chunks_processed,
            "chunks_failed": chunks_failed,
            "processing_time": total_time
        }
    except Exception as e:
        logger.error(f"Error in asynchronous embedding generation: {str(e)}")
        # Retry with exponential backoff
        retry_countdown = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
        self.retry(exc=e, countdown=retry_countdown)