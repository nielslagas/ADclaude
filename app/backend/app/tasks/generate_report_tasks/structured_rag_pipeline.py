"""
Enhanced RAG pipeline with structured output generation
"""

from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.db.database_service import get_database_service
from app.utils.structured_output_generator import (
    StructuredOutputGenerator, 
    OutputFormatter,
    SectionContent
)
from app.utils.hybrid_search import hybrid_search_documents
from app.utils.quality_controller import AutomaticQualityController
import logging
import asyncio

logger = logging.getLogger(__name__)
db_service = get_database_service()

async def generate_structured_content_for_section(
    section_id: str,
    section_info: Dict,
    document_ids: List[str],
    case_id: str,
    user_profile: Optional[Dict] = None,
    output_format: str = "structured"
) -> Dict[str, Any]:
    """
    Generate structured content for a specific report section
    
    Args:
        section_id: ID of the section to generate
        section_info: Information about the section
        document_ids: List of document IDs to use
        case_id: Case ID for context
        user_profile: Optional user profile information
        output_format: Output format (structured, html, markdown, plain)
    
    Returns:
        Dictionary with structured content and metadata
    """
    
    try:
        # Initialize structured output generator
        generator = StructuredOutputGenerator()
        formatter = OutputFormatter()
        
        # Get relevant chunks using existing hybrid search
        chunks = await get_relevant_chunks_for_section(
            section_id, 
            document_ids, 
            case_id
        )
        
        if not chunks:
            logger.warning(f"No relevant chunks found for section {section_id}")
            return {
                "content": f"Geen relevante informatie gevonden voor {section_info.get('title', section_id)}",
                "structured_content": None,
                "chunk_ids": [],
                "format": "plain",
                "error": "no_chunks_found"
            }
        
        # Create context from chunks
        context = format_chunks_for_context(chunks)
        
        # Create base prompt
        prompt = create_structured_prompt(section_id, section_info, user_profile)
        
        # Generate structured content
        structured_section = await generator.generate_structured_section(
            section_id=section_id,
            prompt=prompt,
            context=context,
            user_profile=user_profile
        )
        
        # Quality control check
        quality_controller = AutomaticQualityController()
        validation_result = quality_controller.validate_section(
            section_id=section_id,
            content=structured_section.summary + " " + 
                    " ".join([str(el.content) for el in structured_section.main_content])
        )
        
        if not validation_result["is_valid"]:
            logger.warning(f"Quality control failed for {section_id}: {validation_result['issues']}")
            # Try to improve content
            structured_section = await improve_section_content(
                structured_section, 
                validation_result["issues"],
                generator,
                prompt,
                context
            )
        
        # Format output based on requested format
        formatted_content = format_structured_output(
            structured_section, 
            formatter, 
            output_format
        )
        
        # Return comprehensive result
        return {
            "content": formatted_content,
            "structured_content": structured_section.dict(),
            "chunk_ids": [chunk["id"] for chunk in chunks],
            "format": output_format,
            "metadata": {
                "section_id": section_id,
                "quality_score": validation_result.get("score", 0),
                "chunk_count": len(chunks),
                "has_conclusions": bool(structured_section.conclusions),
                "has_recommendations": bool(structured_section.recommendations)
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating structured content for {section_id}: {str(e)}")
        
        # Fallback to simple text generation
        return {
            "content": generate_fallback_content(section_id, section_info),
            "structured_content": None,
            "chunk_ids": [],
            "format": "plain",
            "error": str(e)
        }

async def get_relevant_chunks_for_section(
    section_id: str,
    document_ids: List[str],
    case_id: str,
    limit: int = 15
) -> List[Dict]:
    """Get relevant chunks for a section using hybrid search"""
    
    # Section-specific queries
    query_mapping = {
        "samenvatting": [
            "persoonsgegevens cliënt werknemer",
            "aanleiding onderzoek arbeidssituatie",
            "huidige situatie functioneren"
        ],
        "belastbaarheid": [
            "fysieke belastbaarheid tillen dragen zitten staan",
            "mentale belastbaarheid concentratie stress",
            "sociale belastbaarheid communicatie samenwerking",
            "functionele mogelijkheden beperkingen"
        ],
        "visie_ad": [
            "arbeidsdeskundige visie beoordeling",
            "conclusies advies aanbevelingen",
            "arbeidsmogelijkheden re-integratie perspectief"
        ],
        "matching": [
            "passend werk geschikte functies",
            "werkaanpassingen hulpmiddelen",
            "randvoorwaarden werkhervatting"
        ]
    }
    
    queries = query_mapping.get(section_id, [f"informatie {section_id}"])
    all_chunks = []
    
    for query in queries:
        try:
            results = await hybrid_search_documents(
                query=query,
                document_ids=document_ids,
                limit=limit // len(queries)  # Distribute limit across queries
            )
            all_chunks.extend(results)
        except Exception as e:
            logger.error(f"Search error for query '{query}': {str(e)}")
    
    # Remove duplicates and sort by relevance
    seen_ids = set()
    unique_chunks = []
    for chunk in all_chunks:
        if chunk["id"] not in seen_ids:
            seen_ids.add(chunk["id"])
            unique_chunks.append(chunk)
    
    # Sort by similarity score
    unique_chunks.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    
    return unique_chunks[:limit]

def format_chunks_for_context(chunks: List[Dict]) -> str:
    """Format chunks into context string"""
    
    formatted_parts = []
    
    # Group chunks by document
    chunks_by_doc = {}
    for chunk in chunks:
        doc_id = chunk.get("document_id", "unknown")
        if doc_id not in chunks_by_doc:
            chunks_by_doc[doc_id] = []
        chunks_by_doc[doc_id].append(chunk)
    
    # Format each document's chunks
    for doc_id, doc_chunks in chunks_by_doc.items():
        doc_name = doc_chunks[0].get("metadata", {}).get("document_name", f"Document {doc_id[:8]}")
        
        formatted_parts.append(f"=== {doc_name} ===")
        
        for i, chunk in enumerate(doc_chunks, 1):
            page = chunk.get("metadata", {}).get("page", "")
            page_info = f" (Pagina {page})" if page else ""
            
            formatted_parts.append(f"\nFragment {i}{page_info}:")
            formatted_parts.append(chunk.get("content", ""))
        
        formatted_parts.append("\n" + "="*50 + "\n")
    
    return "\n".join(formatted_parts)

def create_structured_prompt(
    section_id: str,
    section_info: Dict,
    user_profile: Optional[Dict] = None
) -> str:
    """Create section-specific structured prompt"""
    
    base_prompts = {
        "samenvatting": """
        Schrijf een professionele samenvatting voor een arbeidsdeskundig rapport.
        Focus op: persoonsgegevens, aanleiding onderzoek, huidige situatie, belangrijkste bevindingen.
        Maximaal 250 woorden, objectief en feitelijk.
        """,
        
        "belastbaarheid": """
        Analyseer de belastbaarheid van de cliënt uitgebreid.
        Behandel fysieke, mentale en sociale belastbaarheid.
        Wees specifiek met getallen en frequenties waar mogelijk.
        """,
        
        "visie_ad": """
        Formuleer je professionele arbeidsdeskundige visie.
        Integreer medische en persoonlijke factoren.
        Geef concrete aanbevelingen voor arbeidssituatie.
        Focus op mogelijkheden met erkenning van beperkingen.
        """,
        
        "matching": """
        Formuleer concrete matchingcriteria voor passend werk.
        Categoriseer naar fysieke omgeving, taakinhoud, werktijden, sociale omgeving.
        Markeer prioriteit (essentieel/wenselijk) per criterium.
        Wees SMART en meetbaar.
        """
    }
    
    prompt = base_prompts.get(section_id, f"Schrijf sectie '{section_info.get('title', section_id)}' voor arbeidsdeskundig rapport.")
    
    # Add user profile context if available
    if user_profile:
        profile_info = format_user_profile(user_profile)
        prompt += f"\n\nArbeidsdeskundige informatie:\n{profile_info}"
    
    return prompt

def format_user_profile(user_profile: Dict) -> str:
    """Format user profile for prompt context"""
    
    parts = []
    
    if user_profile.get("first_name") and user_profile.get("last_name"):
        parts.append(f"Naam: {user_profile['first_name']} {user_profile['last_name']}")
    
    if user_profile.get("job_title"):
        parts.append(f"Functie: {user_profile['job_title']}")
    
    if user_profile.get("certification"):
        parts.append(f"Certificering: {user_profile['certification']}")
    
    if user_profile.get("company_name"):
        parts.append(f"Organisatie: {user_profile['company_name']}")
    
    return "\n".join(parts)

def format_structured_output(
    section: SectionContent,
    formatter: OutputFormatter,
    output_format: str
) -> str:
    """Format structured content based on requested format"""
    
    if output_format == "html":
        return formatter.to_html(section)
    elif output_format == "markdown":
        return formatter.to_markdown(section)
    elif output_format == "json":
        return formatter.to_json(section)
    else:  # plain or default
        return formatter.to_plain_text(section)

async def improve_section_content(
    section: SectionContent,
    issues: List[str],
    generator: StructuredOutputGenerator,
    original_prompt: str,
    context: str
) -> SectionContent:
    """Try to improve section content based on quality issues"""
    
    improvement_prompt = f"""
    {original_prompt}
    
    De volgende kwaliteitsproblemen zijn gedetecteerd:
    {' '.join(issues)}
    
    Verbeter de content en zorg voor:
    - Meer specifieke informatie
    - Concrete getallen waar mogelijk
    - Duidelijke conclusies
    - Praktische aanbevelingen
    
    Context:
    {context}
    """
    
    try:
        improved_section = await generator.generate_structured_section(
            section_id=section.section_id,
            prompt=improvement_prompt,
            context=context
        )
        return improved_section
    except Exception as e:
        logger.error(f"Failed to improve section: {str(e)}")
        return section  # Return original if improvement fails

def generate_fallback_content(section_id: str, section_info: Dict) -> str:
    """Generate fallback content when structured generation fails"""
    
    fallbacks = {
        "samenvatting": """
        Op basis van de beschikbare documenten is een analyse gemaakt van de arbeidssituatie.
        De gegevens tonen een complexe situatie met verschillende factoren die van invloed zijn 
        op het dagelijks functioneren en arbeidsmogelijkheden.
        """,
        
        "belastbaarheid": """
        De belastbaarheid wordt beoordeeld op fysiek, mentaal en sociaal vlak.
        Er zijn zowel mogelijkheden als beperkingen geconstateerd die relevant zijn voor 
        passende arbeid. Met de juiste aanpassingen zijn er perspectiven voor werkhervatting.
        """,
        
        "visie_ad": """
        Vanuit arbeidsdeskundig perspectief zijn er mogelijkheden voor re-integratie
        met inachtneming van de geïdentificeerde beperkingen. Een gefaseerde aanpak
        met adequate ondersteuning biedt de beste kansen op duurzame werkhervatting.
        """,
        
        "matching": """
        Voor passend werk gelden criteria op het gebied van fysieke belasting,
        werkomgeving, werktijden en sociale context. Essentieel zijn ergonomische
        aanpassingen en flexibiliteit in taken en werktijden.
        """
    }
    
    return fallbacks.get(
        section_id, 
        f"Informatie voor {section_info.get('title', section_id)} wordt momenteel verwerkt."
    )

# Integration function for backwards compatibility
async def generate_content_for_section(
    section_id: str,
    section_info: Dict,
    document_ids: List[str],
    case_id: str,
    user_profile: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Backwards compatible wrapper for structured content generation
    
    Returns content in the original format but with structured data available
    """
    
    result = await generate_structured_content_for_section(
        section_id=section_id,
        section_info=section_info,
        document_ids=document_ids,
        case_id=case_id,
        user_profile=user_profile,
        output_format="plain"  # Default to plain text for compatibility
    )
    
    # Return in original format with structured data as metadata
    return {
        "content": result["content"],
        "chunk_ids": result["chunk_ids"],
        "prompt": create_structured_prompt(section_id, section_info, user_profile),
        "structured_content": result.get("structured_content"),  # NEW: structured data
        "metadata": result.get("metadata", {})  # NEW: additional metadata
    }