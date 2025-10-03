"""
Hybrid search implementation for the AI Arbeidsdeskundige system.

This module provides enhanced search capabilities by combining different 
search strategies based on document classification and processing approach.
"""
import logging
import time
from typing import List, Dict, Any, Optional

from app.utils.vector_store_improved import get_hybrid_vector_store
from app.utils.embeddings import generate_query_embedding
from app.db.database_service import get_database_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
db_service = get_database_service()
vector_store = get_hybrid_vector_store(db_service)


async def hybrid_search_documents(
    query: str, 
    case_id: Optional[str] = None,
    document_ids: Optional[List[str]] = None,
    limit: int = 10,
    similarity_threshold: float = 0.5,  # Added adaptive threshold parameter
    strategy_distribution: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Perform a hybrid search across documents using multiple RAG strategies.
    
    This search function automatically:
    1. Generates embeddings for the query
    2. Searches across all document processing strategies
    3. Combines and ranks results
    4. Returns formatted context for LLM consumption
    
    Args:
        query: The search query text
        case_id: Optional case ID to restrict search to
        document_ids: Optional specific document IDs to search in
        limit: Maximum total results to return (default 10)
        similarity_threshold: Adaptive similarity threshold (default 0.5)
        strategy_distribution: Optional distribution of results by strategy
            e.g. {"direct_llm": 0.4, "hybrid": 0.4, "full_rag": 0.2}
            
    Returns:
        Dictionary with search results and metadata
    """
    start_time = time.time()
    logger.info(f"Performing hybrid search for query: {query[:50]}... (threshold: {similarity_threshold})")
    
    # Generate query embedding
    try:
        # TODO: Cache embedding for this query
        query_embedding = generate_query_embedding(query)
    except Exception as e:
        logger.error(f"Error generating query embedding: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to generate query embedding: {str(e)}",
            "results": []
        }
    
    # Resolve document constraints
    if case_id and not document_ids:
        try:
            # TODO: Cache document list for case_id
            # Get all documents for this case
            case_documents = db_service.get_documents_for_case(case_id)
            document_ids = [doc["id"] for doc in case_documents if doc["status"] in ["processed", "enhanced"]]
            logger.info(f"Found {len(document_ids)} processed documents for case {case_id}")
        except Exception as e:
            logger.error(f"Error fetching documents for case {case_id}: {str(e)}")
            # Continue with no document restrictions if we can't fetch documents
            document_ids = None
    
    # Calculate strategy-specific limits
    direct_limit, hybrid_limit, full_rag_limit = calculate_strategy_limits(
        limit, strategy_distribution
    )
    
    # Perform the search
    try:
        # TODO: Cache vector search results for query_embedding + document_ids + similarity_threshold
        search_results = vector_store.hybrid_search(
            query=query,
            query_embedding=query_embedding,
            document_ids=document_ids,
            limit=limit,
            similarity_threshold=similarity_threshold,  # Pass adaptive threshold
            direct_limit=direct_limit,
            hybrid_limit=hybrid_limit,
            full_rag_limit=full_rag_limit
        )
        
        # Format results
        # TODO: Cache formatted results for search_results + query combination
        formatted_results = format_search_results(search_results, query)
        
        # Add timing information
        elapsed_time = time.time() - start_time
        formatted_results["timing"] = {
            "total_seconds": round(elapsed_time, 2),
            **(search_results.get("timing", {}))
        }
        
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error performing hybrid search: {str(e)}")
        return {
            "success": False,
            "error": f"Search failed: {str(e)}",
            "results": [],
            "timing": {"total_seconds": round(time.time() - start_time, 2)}
        }


def calculate_strategy_limits(
    total_limit: int, 
    distribution: Optional[Dict[str, float]] = None
) -> tuple:
    """
    Calculate result limits for each strategy based on distribution.
    
    Args:
        total_limit: Total maximum results to return
        distribution: Optional distribution dictionary
        
    Returns:
        Tuple of (direct_limit, hybrid_limit, full_rag_limit)
    """
    if not distribution:
        # Default distribution: balanced between direct and hybrid
        direct_limit = max(1, int(total_limit * 0.4))
        hybrid_limit = max(1, int(total_limit * 0.4))
        full_rag_limit = total_limit - direct_limit - hybrid_limit
    else:
        # Convert percentage distribution to absolute limits
        direct_pct = distribution.get("direct_llm", 0.0)
        hybrid_pct = distribution.get("hybrid", 0.0)
        full_rag_pct = distribution.get("full_rag", 0.0)
        
        # Normalize percentages to sum to 1.0
        total_pct = direct_pct + hybrid_pct + full_rag_pct
        if total_pct == 0:
            # Fallback to default if all are 0
            return calculate_strategy_limits(total_limit, None)
        
        # Calculate limits
        direct_limit = max(0, int(total_limit * (direct_pct / total_pct)))
        hybrid_limit = max(0, int(total_limit * (hybrid_pct / total_pct)))
        
        # Ensure we don't exceed total_limit due to rounding
        full_rag_limit = total_limit - direct_limit - hybrid_limit
        
    return direct_limit, hybrid_limit, full_rag_limit


def format_search_results(
    search_results: Dict[str, Any],
    query: str
) -> Dict[str, Any]:
    """
    Format search results for consumption by the LLM or API.
    
    Args:
        search_results: Raw search results from hybrid_search
        query: Original search query
        
    Returns:
        Dictionary with formatted results
    """
    formatted = {
        "success": True,
        "query": query,
        "total_results": search_results.get("total_results", 0),
        "strategy_counts": search_results.get("strategy_counts", {}),
        "results": []
    }
    
    # Process each result
    for result in search_results.get("results", []):
        # Extract document ID for lookup
        document_id = result.get("document_id")
        
        # Fetch document metadata if possible
        document_info = None
        try:
            # Note: This would need to be adjusted to handle the case where we don't know the user_id
            # Simplified approach for now
            document = db_service.get_row_by_id("document", document_id)
            if document:
                document_info = {
                    "filename": document.get("filename", "Unknown"),
                    "status": document.get("status", "Unknown"),
                    "created_at": document.get("created_at", "Unknown")
                }
        except Exception as e:
            logger.warning(f"Error fetching document info for {document_id}: {str(e)}")
        
        # Format the individual result
        formatted_result = {
            "content": result.get("content", ""),
            "similarity": round(result.get("similarity", 0), 4),
            "document_id": document_id,
            "chunk_id": result.get("chunk_id", ""),
            "strategy": result.get("metadata", {}).get("strategy", "unknown"),
            "document_info": document_info
        }
        
        formatted["results"].append(formatted_result)
    
    return formatted


def generate_context_from_results(search_results: Dict[str, Any], max_tokens: int = 4000) -> str:
    """
    Generate a context string from search results for LLM consumption.
    
    Args:
        search_results: Formatted search results from format_search_results
        max_tokens: Maximum approximate tokens to include
        
    Returns:
        String with formatted context for the LLM
    """
    if not search_results.get("success"):
        return f"ERROR: {search_results.get('error', 'Unknown search error')}"
    
    # Start building context
    context_parts = [
        f"Context voor de zoekvraag: \"{search_results.get('query')}\"\n",
        f"Totaal aantal resultaten: {search_results.get('total_results')}\n\n"
    ]
    
    # Add each result with its metadata
    for i, result in enumerate(search_results.get("results", []), 1):
        # Estimate current context length (rough approximation)
        current_length = sum(len(part) for part in context_parts)
        if current_length > max_tokens * 4:  # Approximate 4 chars per token
            context_parts.append(f"\n[Afgekapt vanwege maximale contextgrootte. {len(search_results['results']) - i + 1} resultaten weggelaten.]")
            break
        
        # Document info section
        doc_info = result.get("document_info", {})
        document_section = f"DOCUMENT {i}: "
        if doc_info:
            document_section += f"{doc_info.get('filename', 'Onbekend')}"
        else:
            document_section += f"ID: {result.get('document_id', 'Onbekend')}"
        
        # Add similarity score
        document_section += f" (relevantie: {result.get('similarity', 0):.2f})"
        
        # Add processing strategy
        strategy = result.get("strategy", "unknown")
        if strategy == "direct_llm":
            strategy_text = "directe verwerking"
        elif strategy == "hybrid":
            strategy_text = "hybride verwerking" 
        elif strategy == "full_rag":
            strategy_text = "volledige RAG verwerking"
        else:
            strategy_text = "onbekende verwerkingsstrategie"
        document_section += f" - {strategy_text}\n"
        
        # Add content
        content = result.get("content", "").strip()
        if content:
            context_parts.append(f"{document_section}---\n{content}\n---\n\n")
        else:
            context_parts.append(f"{document_section}[Geen inhoud beschikbaar]\n\n")
    
    return "".join(context_parts)