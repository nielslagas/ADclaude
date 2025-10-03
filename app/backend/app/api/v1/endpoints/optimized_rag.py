"""
Optimized RAG API Endpoints
Enhanced retrieval en chunking voor arbeidsdeskundige rapporten
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, List, Any, Optional
import logging
from pydantic import BaseModel

from app.db.database_service import get_database_service
from app.utils.llm_provider import GenerativeModel
from app.utils.optimized_rag_pipeline import OptimizedRAGPipeline, RetrievalStrategy


router = APIRouter()
logger = logging.getLogger(__name__)


class OptimizedChunkRequest(BaseModel):
    """Request voor optimized chunking"""
    document_id: str
    force_rechunk: bool = False


class EnhancedRetrievalRequest(BaseModel):
    """Request voor enhanced retrieval"""
    query: str
    case_id: str
    document_types: Optional[List[str]] = None
    max_results: int = 10
    strategy: Optional[str] = None


@router.post("/chunks/optimized")
async def create_optimized_chunks(request: OptimizedChunkRequest):
    """
    Maak geoptimaliseerde chunks voor een document
    """
    try:
        db_service = get_database_service()
        llm_provider = GenerativeModel()
        
        # Check if document exists
        document = db_service.get_row_by_id("documents", request.document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document niet gevonden")
        
        # Check if already chunked (unless force rechunk)
        existing_chunks = db_service.get_document_chunks_by_type(request.document_id)
        if existing_chunks and not request.force_rechunk:
            logger.info(f"Document {request.document_id} already has {len(existing_chunks)} chunks")
            return {
                "document_id": request.document_id,
                "status": "already_chunked",
                "existing_chunks": len(existing_chunks),
                "message": "Document heeft al chunks. Gebruik force_rechunk=true om opnieuw te chunken."
            }
        
        # Get document metadata for type information
        metadata = document.get("metadata", {})
        doc_type = metadata.get("document_type", "unknown")
        
        if doc_type == "unknown":
            raise HTTPException(
                status_code=400, 
                detail="Document moet eerst geclassificeerd worden voordat optimized chunking mogelijk is"
            )
        
        # Initialize optimized RAG pipeline
        pipeline = OptimizedRAGPipeline(db_service, llm_provider)
        
        # Create optimized chunks
        logger.info(f"Creating optimized chunks for document {request.document_id} of type {doc_type}")
        content = document.get("content", "")
        chunks = await pipeline.create_optimized_chunks(request.document_id, content, doc_type)
        
        # Store chunks in database
        stored_chunks = []
        for chunk in chunks:
            chunk_id = db_service.create_document_chunk(request.document_id, chunk)
            if chunk_id:
                stored_chunks.append(chunk_id)
        
        return {
            "document_id": request.document_id,
            "document_type": doc_type,
            "status": "success",
            "chunks_created": len(stored_chunks),
            "chunks": chunks[:3],  # Return first 3 chunks as preview
            "chunk_statistics": {
                "total_chunks": len(chunks),
                "average_size": sum(len(c["content"]) for c in chunks) // len(chunks) if chunks else 0,
                "size_range": {
                    "min": min(len(c["content"]) for c in chunks) if chunks else 0,
                    "max": max(len(c["content"]) for c in chunks) if chunks else 0
                }
            }
        }
    
    except Exception as e:
        logger.error(f"Error creating optimized chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieval/enhanced")
async def enhanced_retrieval(request: EnhancedRetrievalRequest):
    """
    Voer enhanced retrieval uit met document type awareness
    """
    try:
        db_service = get_database_service()
        llm_provider = GenerativeModel()
        
        # Validate case exists
        case = db_service.get_row_by_id("cases", request.case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case niet gevonden")
        
        # Validate document types if provided
        if request.document_types:
            valid_types = ["medical_report", "assessment_report", "legal_document", 
                          "insurance_document", "personal_statement", "correspondence", 
                          "educational_record"]
            invalid_types = [dt for dt in request.document_types if dt not in valid_types]
            if invalid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ongeldige document types: {invalid_types}"
                )
        
        # Initialize optimized RAG pipeline
        pipeline = OptimizedRAGPipeline(db_service, llm_provider)
        
        # Perform enhanced retrieval
        logger.info(f"Performing enhanced retrieval for query: {request.query[:50]}...")
        results = await pipeline.enhanced_retrieval(
            query=request.query,
            case_id=request.case_id,
            document_types=request.document_types,
            max_results=request.max_results
        )
        
        # Get pipeline metrics
        metrics = pipeline.get_metrics()
        
        return {
            "query": request.query,
            "case_id": request.case_id,
            "document_types": request.document_types,
            "results_found": len(results),
            "results": results,
            "retrieval_metrics": {
                "retrieval_time": metrics.get("average_retrieval_time"),
                "cache_hit_rate": metrics.get("cache_hit_rate"),
                "total_retrievals": metrics.get("retrievals_performed")
            },
            "query_analysis": {
                "strategy_used": results[0].get("retrieval_strategy") if results else "none",
                "boost_factors_applied": [r.get("boost_factor", 1.0) for r in results]
            }
        }
    
    except Exception as e:
        logger.error(f"Error in enhanced retrieval: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chunks/{document_id}/optimized")
async def get_optimized_chunks(
    document_id: str,
    chunk_type: Optional[str] = Query(None, description="Filter op chunk type"),
    include_metadata: bool = Query(True, description="Include chunk metadata")
):
    """
    Haal geoptimaliseerde chunks op voor een document
    """
    try:
        db_service = get_database_service()
        
        # Check if document exists
        document = db_service.get_row_by_id("documents", document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document niet gevonden")
        
        # Get chunks
        chunks = db_service.get_document_chunks_by_type(document_id, chunk_type)
        
        # Process chunks based on include_metadata flag
        processed_chunks = []
        for chunk in chunks:
            processed_chunk = {
                "chunk_id": chunk.get("id"),
                "content": chunk.get("content"),
                "chunk_index": chunk.get("chunk_index")
            }
            
            if include_metadata:
                processed_chunk["metadata"] = chunk.get("metadata", {})
            
            processed_chunks.append(processed_chunk)
        
        # Generate chunk statistics
        chunk_stats = {}
        if chunks:
            chunk_stats = {
                "total_chunks": len(chunks),
                "chunk_types": list(set(
                    c.get("metadata", {}).get("chunk_type", "unknown") for c in chunks
                )),
                "section_types": list(set(
                    c.get("metadata", {}).get("section_type", "unknown") for c in chunks
                    if c.get("metadata", {}).get("section_type")
                )),
                "average_length": sum(len(c.get("content", "")) for c in chunks) // len(chunks),
                "importance_distribution": {
                    importance: sum(1 for c in chunks 
                                  if c.get("metadata", {}).get("importance") == importance)
                    for importance in ["critical", "high", "medium", "low"]
                }
            }
        
        return {
            "document_id": document_id,
            "chunk_type_filter": chunk_type,
            "chunks": processed_chunks,
            "statistics": chunk_stats
        }
    
    except Exception as e:
        logger.error(f"Error getting optimized chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retrieval/strategies")
async def get_retrieval_strategies():
    """
    Haal beschikbare retrieval strategies op
    """
    try:
        strategies = [
            {
                "value": RetrievalStrategy.SEMANTIC_SEARCH.value,
                "name": "Semantic Search",
                "description": "Zoekt op basis van betekenis en context van de query"
            },
            {
                "value": RetrievalStrategy.HYBRID_SEARCH.value,
                "name": "Hybrid Search", 
                "description": "Combineert semantic en keyword search voor betere resultaten"
            },
            {
                "value": RetrievalStrategy.KEYWORD_SEARCH.value,
                "name": "Keyword Search",
                "description": "Zoekt op basis van exacte woord matches"
            },
            {
                "value": RetrievalStrategy.SECTION_AWARE.value,
                "name": "Section Aware",
                "description": "Intelligente zoektocht met document sectie awareness"
            }
        ]
        
        return {
            "strategies": strategies,
            "default_strategy": "auto_select",
            "strategy_selection_logic": {
                "section_aware": "Voor queries met sectie-specifieke keywords en prioriteitsdocumenten",
                "hybrid": "Voor complexe queries met meer dan 8 woorden",
                "keyword": "Voor specifieke zoektermen en exacte matches",
                "semantic": "Voor algemene vragen en context-gebaseerde zoekopdrachten"
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting retrieval strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline/metrics")
async def get_pipeline_metrics():
    """
    Haal RAG pipeline performance metrics op
    """
    try:
        db_service = get_database_service()
        llm_provider = GenerativeModel()
        
        # Initialize pipeline to get current metrics
        pipeline = OptimizedRAGPipeline(db_service, llm_provider)
        metrics = pipeline.get_metrics()
        
        # Get additional database statistics
        doc_stats = db_service.get_processing_statistics()
        
        return {
            "pipeline_metrics": metrics,
            "document_statistics": doc_stats,
            "performance_indicators": {
                "average_retrieval_time": f"{metrics.get('average_retrieval_time', 0):.3f}s",
                "cache_effectiveness": f"{metrics.get('cache_hit_rate', 0) * 100:.1f}%",
                "total_chunks_processed": metrics.get('chunks_processed', 0),
                "total_retrievals": metrics.get('retrievals_performed', 0)
            },
            "optimization_status": {
                "cache_size": metrics.get('cache_size', 0),
                "cache_utilization": f"{(metrics.get('cache_size', 0) / 100) * 100:.1f}%",
                "ready_for_production": metrics.get('retrievals_performed', 0) > 10
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting pipeline metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline/clear-cache")
async def clear_pipeline_cache():
    """
    Clear RAG pipeline cache
    """
    try:
        db_service = get_database_service()
        llm_provider = GenerativeModel()
        
        pipeline = OptimizedRAGPipeline(db_service, llm_provider)
        pipeline.clear_cache()
        
        return {
            "status": "success",
            "message": "Pipeline cache cleared successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error clearing pipeline cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{document_id}/analyze-chunks")
async def analyze_document_chunks(document_id: str):
    """
    Analyseer de chunk kwaliteit van een document
    """
    try:
        db_service = get_database_service()
        
        # Get document and chunks
        document = db_service.get_row_by_id("documents", document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document niet gevonden")
        
        chunks = db_service.get_document_chunks_by_type(document_id)
        
        if not chunks:
            return {
                "document_id": document_id,
                "status": "no_chunks",
                "message": "Document heeft geen chunks. Voer eerst optimized chunking uit."
            }
        
        # Analyze chunk quality
        analysis = {
            "total_chunks": len(chunks),
            "size_analysis": {
                "sizes": [len(c.get("content", "")) for c in chunks],
                "average_size": sum(len(c.get("content", "")) for c in chunks) // len(chunks),
                "size_variance": "calculated",
                "optimal_size_range": "600-1500 characters"
            },
            "content_analysis": {
                "section_types": {},
                "importance_levels": {},
                "chunk_types": {}
            },
            "quality_indicators": {
                "has_overlaps": False,
                "section_coverage": "good",
                "metadata_completeness": 0.0
            }
        }
        
        # Analyze chunk metadata
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            
            # Section types
            section_type = metadata.get("section_type", "unknown")
            analysis["content_analysis"]["section_types"][section_type] = \
                analysis["content_analysis"]["section_types"].get(section_type, 0) + 1
            
            # Importance levels
            importance = metadata.get("importance", "unknown")
            analysis["content_analysis"]["importance_levels"][importance] = \
                analysis["content_analysis"]["importance_levels"].get(importance, 0) + 1
            
            # Chunk types
            chunk_type = metadata.get("chunk_type", "unknown")
            analysis["content_analysis"]["chunk_types"][chunk_type] = \
                analysis["content_analysis"]["chunk_types"].get(chunk_type, 0) + 1
        
        # Calculate metadata completeness
        metadata_fields = ["section_type", "importance", "chunk_type", "document_type"]
        total_completeness = 0
        
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            chunk_completeness = sum(1 for field in metadata_fields if metadata.get(field))
            total_completeness += chunk_completeness / len(metadata_fields)
        
        analysis["quality_indicators"]["metadata_completeness"] = total_completeness / len(chunks)
        
        # Quality recommendations
        recommendations = []
        
        avg_size = analysis["size_analysis"]["average_size"]
        if avg_size < 400:
            recommendations.append("Chunks zijn erg klein, overweeg grotere target size")
        elif avg_size > 1800:
            recommendations.append("Chunks zijn erg groot, overweeg kleinere target size")
        
        if analysis["quality_indicators"]["metadata_completeness"] < 0.8:
            recommendations.append("Metadata completeness kan verbeterd worden")
        
        section_types = analysis["content_analysis"]["section_types"]
        if len(section_types) == 1 and "unknown" in section_types:
            recommendations.append("Geen sectie-informatie gevonden, overweeg section-aware chunking")
        
        return {
            "document_id": document_id,
            "analysis": analysis,
            "recommendations": recommendations,
            "overall_quality": "good" if len(recommendations) <= 1 else "needs_improvement"
        }
    
    except Exception as e:
        logger.error(f"Error analyzing document chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Import datetime voor clear cache endpoint
from datetime import datetime