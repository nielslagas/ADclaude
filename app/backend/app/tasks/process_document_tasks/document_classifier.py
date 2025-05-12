"""
Document classification module for the hybrid RAG implementation.

This module provides functionality to classify documents based on their size and content,
allowing the system to choose the most appropriate processing strategy.
"""
import logging
from enum import Enum
from typing import Dict, Any, Tuple

from app.db.database_service import DatabaseService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentSize(str, Enum):
    """Enum for document size classification"""
    SMALL = "small"     # < 20,000 characters
    MEDIUM = "medium"   # < 60,000 characters
    LARGE = "large"     # >= 60,000 characters


class ProcessingStrategy(str, Enum):
    """Enum for document processing strategies"""
    DIRECT_LLM = "direct_llm"        # Direct processing with LLM (no embeddings)
    HYBRID = "hybrid"                # Hybrid approach (direct + async embeddings)
    FULL_RAG = "full_rag"            # Full RAG pipeline with embeddings


class DocumentClassifier:
    """
    Classifies documents and determines the optimal processing strategy
    based on document characteristics.
    """
    
    def __init__(self, db_service: DatabaseService):
        """
        Initialize the document classifier.
        
        Args:
            db_service: Database service for document operations
        """
        self.db_service = db_service
        
        # Size thresholds (in characters)
        self.small_threshold = 20000
        self.medium_threshold = 60000
    
    def classify_document(self, document_id: str) -> Tuple[DocumentSize, ProcessingStrategy, str]:
        """
        Classify a document and determine the optimal processing strategy.
        
        Args:
            document_id: The ID of the document to classify
            
        Returns:
            Tuple of (document_size, processing_strategy, priority)
        """
        document = self.db_service.get_document(document_id)
        
        if not document:
            logger.error(f"Document not found: {document_id}")
            raise ValueError(f"Document not found: {document_id}")
            
        # Extract content from document
        content = self._get_document_content(document)
        content_length = len(content)
        
        # Classify based on size
        if content_length < self.small_threshold:
            size = DocumentSize.SMALL
            strategy = ProcessingStrategy.DIRECT_LLM
            priority = "high"
        elif content_length < self.medium_threshold:
            size = DocumentSize.MEDIUM
            strategy = ProcessingStrategy.HYBRID
            priority = "medium"
        else:
            size = DocumentSize.LARGE
            strategy = ProcessingStrategy.FULL_RAG
            priority = "low"
            
        logger.info(f"Document {document_id} classified as {size} with strategy {strategy}")
        
        return size, strategy, priority
    
    def _get_document_content(self, document: Dict[str, Any]) -> str:
        """
        Extract the content from a document.
        
        Args:
            document: The document dictionary
            
        Returns:
            The document content as string
        """
        # Handle different document structures
        if "content" in document:
            return document["content"] or ""
        elif "chunks" in document and document["chunks"]:
            # Concatenate all chunk contents
            return "\n\n".join([chunk.get("content", "") for chunk in document["chunks"]])
        else:
            return ""