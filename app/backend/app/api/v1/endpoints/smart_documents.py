"""
Smart Documents API Endpoints
Enhanced document processing met AI-gedreven classificatie
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, List, Any, Optional
import logging

from app.db.database_service import get_database_service
from app.utils.llm_provider import GenerativeModel
from app.tasks.process_document_tasks.enhanced_document_processor import EnhancedDocumentProcessor
from app.utils.smart_document_classifier import DocumentType, ProcessingStrategy


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/documents/{document_id}/enhanced-processing")
async def process_document_enhanced(
    document_id: str,
    force_reprocess: bool = Query(False, description="Force reprocessing even if already processed")
):
    """
    Process document met enhanced AI classification en adaptive processing
    """
    try:
        db_service = get_database_service()
        llm_provider = GenerativeModel()
        
        # Check if document exists
        document = db_service.get_row_by_id("documents", document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document niet gevonden")
        
        # Check if already processed (unless force reprocess)
        if not force_reprocess and document.get("metadata", {}).get("classification_timestamp"):
            logger.info(f"Document {document_id} already processed, returning existing results")
            return {
                "document_id": document_id,
                "status": "already_processed",
                "classification": document.get("metadata", {}),
                "message": "Document was al verwerkt. Gebruik force_reprocess=true om opnieuw te verwerken."
            }
        
        # Initialize enhanced processor
        processor = EnhancedDocumentProcessor(db_service, llm_provider)
        
        # Process document
        logger.info(f"Starting enhanced processing for document {document_id}")
        result = await processor.process_document(document_id)
        
        if result.get("status") == "completed":
            return {
                "document_id": document_id,
                "status": "success",
                "classification": result.get("classification"),
                "processing_strategy": result.get("processing_strategy"),
                "processing_time": result.get("processing_time_seconds"),
                "timestamp": result.get("timestamp")
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Document verwerking gefaald: {result.get('error', 'Onbekende fout')}"
            )
    
    except Exception as e:
        logger.error(f"Error in enhanced document processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}/classification")
async def get_document_classification(document_id: str):
    """
    Haal document classificatie informatie op
    """
    try:
        db_service = get_database_service()
        
        document = db_service.get_row_by_id("documents", document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document niet gevonden")
        
        metadata = document.get("metadata", {})
        
        if not metadata.get("document_type"):
            return {
                "document_id": document_id,
                "status": "not_classified",
                "message": "Document is nog niet geclassificeerd"
            }
        
        return {
            "document_id": document_id,
            "status": "classified",
            "classification": {
                "type": metadata.get("document_type"),
                "confidence": metadata.get("classification_confidence"),
                "processing_strategy": metadata.get("processing_strategy"),
                "classification_timestamp": metadata.get("classification_timestamp"),
                "metadata": metadata.get("classification_metadata", {})
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting document classification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/by-type/{document_type}")
async def get_documents_by_type(
    document_type: str,
    confidence_threshold: float = Query(0.5, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=100)
):
    """
    Haal documenten op gefilterd op type en confidence threshold
    """
    try:
        # Validate document type
        valid_types = [dt.value for dt in DocumentType]
        if document_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Ongeldig document type. Geldige types: {valid_types}"
            )
        
        db_service = get_database_service()
        documents = db_service.get_document_by_classification(document_type, confidence_threshold)
        
        # Limit results
        limited_documents = documents[:limit]
        
        return {
            "document_type": document_type,
            "confidence_threshold": confidence_threshold,
            "total_found": len(documents),
            "returned": len(limited_documents),
            "documents": limited_documents
        }
    
    except Exception as e:
        logger.error(f"Error getting documents by type: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/processing/statistics")
async def get_processing_statistics():
    """
    Haal processing statistieken op
    """
    try:
        db_service = get_database_service()
        stats = db_service.get_processing_statistics()
        
        # Add additional computed statistics
        processing_stats = stats.get("processing_stats", [])
        
        # Calculate type distribution
        type_distribution = {}
        strategy_distribution = {}
        
        for stat in processing_stats:
            doc_type = stat.get("document_type", "unknown")
            strategy = stat.get("processing_strategy", "unknown")
            count = stat.get("count", 0)
            
            type_distribution[doc_type] = type_distribution.get(doc_type, 0) + count
            strategy_distribution[strategy] = strategy_distribution.get(strategy, 0) + count
        
        return {
            **stats,
            "distributions": {
                "by_type": type_distribution,
                "by_strategy": strategy_distribution
            },
            "available_types": [dt.value for dt in DocumentType],
            "available_strategies": [ps.value for ps in ProcessingStrategy]
        }
    
    except Exception as e:
        logger.error(f"Error getting processing statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/search")
async def search_documents_by_metadata(search_criteria: Dict[str, Any]):
    """
    Zoek documenten op basis van metadata criteria
    """
    try:
        db_service = get_database_service()
        
        # Validate search criteria
        allowed_criteria = ["document_types", "min_confidence", "processing_strategy", "has_metadata"]
        invalid_criteria = set(search_criteria.keys()) - set(allowed_criteria)
        if invalid_criteria:
            raise HTTPException(
                status_code=400,
                detail=f"Ongeldige zoek criteria: {invalid_criteria}. Toegestaan: {allowed_criteria}"
            )
        
        # Validate document types if provided
        if "document_types" in search_criteria:
            valid_types = [dt.value for dt in DocumentType]
            invalid_types = set(search_criteria["document_types"]) - set(valid_types)
            if invalid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ongeldige document types: {invalid_types}. Geldig: {valid_types}"
                )
        
        documents = db_service.search_documents_by_metadata(search_criteria)
        
        return {
            "search_criteria": search_criteria,
            "total_found": len(documents),
            "documents": documents
        }
    
    except Exception as e:
        logger.error(f"Error searching documents by metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    chunk_type: Optional[str] = Query(None, description="Filter chunks by type")
):
    """
    Haal document chunks op, optioneel gefilterd op type
    """
    try:
        db_service = get_database_service()
        
        # Check if document exists
        document = db_service.get_row_by_id("documents", document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document niet gevonden")
        
        chunks = db_service.get_document_chunks_by_type(document_id, chunk_type)
        
        return {
            "document_id": document_id,
            "chunk_type_filter": chunk_type,
            "total_chunks": len(chunks),
            "chunks": chunks
        }
    
    except Exception as e:
        logger.error(f"Error getting document chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{document_id}/reclassify")
async def reclassify_document(document_id: str):
    """
    Herclassificeer een document (force reprocessing van classificatie)
    """
    try:
        db_service = get_database_service()
        llm_provider = GenerativeModel()
        
        # Check if document exists
        document = db_service.get_row_by_id("documents", document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document niet gevonden")
        
        # Initialize classifier
        from app.utils.smart_document_classifier import SmartDocumentClassifier
        classifier = SmartDocumentClassifier(llm_provider)
        
        # Reclassify
        content = document.get("content", "")
        filename = document.get("filename", "")
        
        logger.info(f"Reclassifying document {document_id}")
        classification = await classifier.classify_document(content, filename)
        
        # Update document metadata
        metadata = {
            "document_type": classification.get("type"),
            "classification_confidence": classification.get("confidence"),
            "processing_strategy": classification.get("processing_strategy"),
            "classification_metadata": classification.get("metadata", {}),
            "classification_timestamp": classification.get("timestamp"),
            "reclassified": True
        }
        
        success = await db_service.update_document_metadata(document_id, metadata)
        
        if success:
            return {
                "document_id": document_id,
                "status": "reclassified",
                "new_classification": classification
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update document metadata")
    
    except Exception as e:
        logger.error(f"Error reclassifying document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/classification/types")
async def get_available_document_types():
    """
    Haal beschikbare document types op
    """
    try:
        return {
            "document_types": [
                {
                    "value": dt.value,
                    "name": dt.name,
                    "description": _get_type_description(dt)
                }
                for dt in DocumentType
            ],
            "processing_strategies": [
                {
                    "value": ps.value,
                    "name": ps.name,
                    "description": _get_strategy_description(ps)
                }
                for ps in ProcessingStrategy
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting document types: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_type_description(doc_type: DocumentType) -> str:
    """Helper om beschrijving te krijgen voor document type"""
    descriptions = {
        DocumentType.MEDICAL_REPORT: "Medische rapporten, specialistenverslagen, behandelplannen",
        DocumentType.INSURANCE_DOCUMENT: "UWV documenten, verzekeringsstukken, uitkeringsbeschikkingen",
        DocumentType.EMPLOYMENT_RECORD: "Arbeidscontracten, functieomschrijvingen, personeelsdossiers",
        DocumentType.ASSESSMENT_REPORT: "Arbeidsdeskundige rapporten, FML onderzoeken, belastbaarheidsanalyses",
        DocumentType.PERSONAL_STATEMENT: "Persoonlijke verhalen, eigen ervaringen, klachtenbeschrijvingen",
        DocumentType.EDUCATIONAL_RECORD: "Diploma's, certificaten, opleidingsgegevens",
        DocumentType.LEGAL_DOCUMENT: "Juridische documenten, rechtbankuitspraken, advocatenbrieven",
        DocumentType.CORRESPONDENCE: "Brieven, emails, algemene correspondentie",
        DocumentType.UNKNOWN: "Niet geclassificeerd of onbekend type document"
    }
    return descriptions.get(doc_type, "Geen beschrijving beschikbaar")


def _get_strategy_description(strategy: ProcessingStrategy) -> str:
    """Helper om beschrijving te krijgen voor processing strategy"""
    descriptions = {
        ProcessingStrategy.DIRECT_LLM: "Directe LLM verwerking voor kleine/eenvoudige documenten",
        ProcessingStrategy.HYBRID: "Hybride verwerking met chunking en directe analyse",
        ProcessingStrategy.FULL_RAG: "Volledige RAG pipeline voor complexe/grote documenten"
    }
    return descriptions.get(strategy, "Geen beschrijving beschikbaar")