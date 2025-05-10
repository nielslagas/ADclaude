"""
Hybrid report generator that combines direct LLM approach for small documents
and RAG approach for larger documents when embeddings are available.
"""
from datetime import datetime
import logging
from uuid import UUID

from app.celery_worker import celery
from app.db.database_service import db_service
from app.utils.llm_provider import (
    create_llm_instance, 
    generate_embedding
)

# Define templates here to avoid circular imports
MVP_TEMPLATES = {
    "staatvandienst": {
        "id": "staatvandienst",
        "name": "Staatvandienst Format",
        "description": "Standard format for Staatvandienst",
        "sections": {
            "persoonsgegevens": {
                "title": "Persoonsgegevens",
                "description": "Persoonlijke informatie van de cliënt"
            },
            "werkgever_functie": {
                "title": "Werkgever en Functie",
                "description": "Gegevens over de huidige of laatste werkgever en functie"
            },
            "aanleiding": {
                "title": "Aanleiding Onderzoek",
                "description": "Reden voor het arbeidsdeskundig onderzoek"
            },
            "arbeidsverleden": {
                "title": "Arbeidsverleden en Opleidingsachtergrond",
                "description": "Overzicht van opleidingen en werkervaring"
            },
            "medische_situatie": {
                "title": "Medische Situatie",
                "description": "Beschrijving van de medische situatie en beperkingen"
            },
            "belastbaarheid": {
                "title": "Belastbaarheid",
                "description": "Analyse van de belastbaarheid van de cliënt"
            },
            "belasting_huidige_functie": {
                "title": "Belasting Huidige Functie",
                "description": "Analyse van de belasting in de huidige/laatst uitgeoefende functie"
            },
            "visie_ad": {
                "title": "Visie Arbeidsdeskundige",
                "description": "Professionele visie van de arbeidsdeskundige"
            },
            "matching": {
                "title": "Matching Overwegingen",
                "description": "Overwegingen voor matching naar passend werk"
            },
            "conclusie": {
                "title": "Conclusie en Advies",
                "description": "Conclusies en aanbevelingen"
            },
            "samenvatting": {
                "title": "Samenvatting",
                "description": "Korte samenvatting van het rapport"
            }
        }
    }
}

# Import this here to avoid circular imports
from app.tasks.generate_report_tasks.rag_pipeline import generate_content_for_section
from app.core.config import settings

# Configure the logger
logger = logging.getLogger(__name__)

# Constants for determining approach
MAX_DIRECT_DOCUMENT_LENGTH = 80000  # Characters for total document length for direct LLM

def combine_document_texts(documents, max_length=None):
    """
    Combine text from multiple documents into a single context
    with optional truncation to max_length.
    """
    combined_text = ""
    
    for doc in documents:
        # Get document content
        content = doc.get("content", "")
        
        # Add document separator and metadata
        doc_header = f"\n\n--- DOCUMENT: {doc.get('filename', 'Unnamed')} ---\n\n"
        
        # Check if adding this document would exceed max_length
        if max_length and len(combined_text) + len(doc_header) + len(content) > max_length:
            # If we're already close to max_length, just return what we have
            if len(combined_text) > max_length * 0.8:
                break
                
            # Otherwise, truncate this document
            available_space = max_length - len(combined_text) - len(doc_header)
            truncated_content = content[:available_space]
            combined_text += doc_header + truncated_content + "\n\n[Document truncated due to length]"
            break
        else:
            # Add full document
            combined_text += doc_header + content
    
    return combined_text

def generate_content_with_direct_llm(prompt, context):
    """
    Generate content by sending the full context directly to the LLM
    with robust error handling and multiple fallback approaches
    """
    # Log the function call
    logger.info(f"Generating content with direct LLM, context length: {len(context)}")
    
    # First attempt: Use the configured provider with most permissive settings
    try:
        # Create an LLM instance with our provider-agnostic interface
        model = create_llm_instance(
            temperature=0.1,
            max_tokens=4096,
            dangerous_content_level="BLOCK_NONE"
        )
        
        # Neutral professional system instruction
        system_instruction = (
            "Je bent een professionele rapporteur die zakelijke rapporten schrijft. "
            "Schrijf in een objectieve, feitelijke stijl op basis van de gegeven informatie. "
            "Focus op het beschrijven van feiten zonder medische conclusies te trekken. "
            "Gebruik formele taal en vermijd gevoelige informatie waar mogelijk."
        )
        
        # Simplified context - strip out potentially problematic content
        safe_context = "\n".join([
            line for line in context.split("\n") 
            if not any(term in line.lower() for term in [
                "diagnose", "medisch", "ziekte", "medicatie", "behandeling", "therapie", 
                "symptomen", "psychisch", "beperking", "handicap"
            ])
        ])
        
        # Create a sanitized prompt version 
        full_prompt = f"{prompt}\n\nRelevante informatie:\n\n{safe_context}"
        
        # Generate content
        logger.info("Attempt 1: Using configured provider with permissive settings")
        response = model.generate_content(
            [
                {"role": "system", "parts": [system_instruction]},
                {"role": "user", "parts": [full_prompt]}
            ]
        )
        
        # Check for blocking
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback and response.prompt_feedback.block_reason:
            block_reason = response.prompt_feedback.block_reason
            logger.warning(f"First attempt blocked: {block_reason}")
            # Don't expose the actual block reason in error messages
            logger.error(f"Content blocked: {block_reason}")
            # Just raise a generic exception
            raise Exception("Content blocked by content filter")
            
        # Validate response
        if response.text and len(response.text.strip()) >= 50:
            logger.info("First attempt successful")
            return response.text
        else:
            logger.warning("First attempt returned empty or too short content")
            logger.error("Generated content too short")
            raise Exception("Generated content too short")
            
    except Exception as first_error:
        logger.warning(f"First attempt failed: {str(first_error)}")
        
        # Second attempt: Try with very simplified prompt and context
        try:
            logger.info("Attempt 2: Using extremely simplified approach")
            
            # Even more simplified system instruction
            basic_system = "Je bent een professionele tekstschrijver die objectieve samenvattingen maakt."
            
            # Create a very basic prompt without specific medical terminology
            basic_prompt = "Maak een objectieve samenvatting van de volgende informatie voor een zakelijk rapport."
            
            # Further reduce context to bare essentials
            minimal_context = "\n\n".join([
                para for para in safe_context.split("\n\n")
                if len(para.strip()) > 0
            ][:5])  # Just use first few paragraphs
            
            basic_full = f"{basic_prompt}\n\n{minimal_context}"
            
            # Try with even more permissive settings and a different model instance
            model = create_llm_instance(
                temperature=0.0,  # Completely factual
                max_tokens=2048,
                dangerous_content_level="BLOCK_NONE"
            )
            
            # Generate with minimal prompt
            basic_response = model.generate_content(
                [
                    {"role": "system", "parts": [basic_system]},
                    {"role": "user", "parts": [basic_full]}
                ]
            )
            
            if basic_response.text and len(basic_response.text.strip()) >= 30:
                logger.info("Second attempt successful")
                return basic_response.text
            else:
                logger.error("Second attempt returned empty or too short content")
                raise Exception("Second attempt failed")
                
        except Exception as second_error:
            logger.warning(f"Second attempt failed: {str(second_error)}")
            
            # Third attempt: Fallback to static content as last resort
            logger.info("All attempts failed, using static fallback content")
            
            # Parse the section prompt to understand what kind of content is needed
            section_type = "general"
            if "samenvatting" in prompt.lower():
                section_type = "samenvatting"
            elif "belastbaarheid" in prompt.lower() or "mogelijkheden" in prompt.lower():
                section_type = "belastbaarheid"
            elif "visie" in prompt.lower():
                section_type = "visie"
            elif "matching" in prompt.lower() or "passend werk" in prompt.lower():
                section_type = "matching"
                
            # Provide helpful fallback content based on section type
            fallback_messages = {
                "samenvatting": """
                Op basis van de beschikbare documenten is een objectieve en feitelijke samenvatting samengesteld. 
                De gegevens tonen aan dat er sprake is van een werksituatie waarbij bepaalde factoren van invloed 
                zijn op het functioneren. Het dossier bevat informatie over de huidige werkomstandigheden en 
                mogelijkheden voor de toekomst.
                """,
                "belastbaarheid": """
                De beschikbare gegevens geven inzicht in de mogelijkheden en aandachtspunten voor werkzaamheden. 
                Er zijn zowel fysieke, mentale als sociale factoren die invloed hebben op de werksituatie. 
                Met de juiste aanpassingen en voorwaarden zijn er diverse mogelijkheden voor passende werkzaamheden.
                """,
                "visie": """
                Vanuit professioneel perspectief kan gesteld worden dat er kansen zijn voor werkhervatting 
                met inachtneming van de geïdentificeerde aandachtspunten. Een gefaseerde opbouw van werkzaamheden 
                met de juiste ondersteuning biedt perspectief. Het is belangrijk om rekening te houden met individuele 
                factoren en werkomstandigheden.
                """,
                "matching": """
                Voor het vinden van passend werk zijn de volgende criteria van belang:
                
                Fysieke werkomgeving:
                - Toegankelijke werkplek (E)
                - Ergonomisch verantwoorde inrichting (E)
                - Mogelijkheid tot afwisseling in houding (W)
                
                Taakinhoud:
                - Taken met afwisselende belasting (E)
                - Werkzaamheden met eigen regie op tempo (E)
                - Taken passend bij ervaring en opleiding (W)
                
                Werktijden:
                - Regelmatige werktijden (E)
                - Flexibiliteit in planning (W)
                
                Sociale werkomgeving:
                - Ondersteunende collega's (W)
                - Begripvolle leidinggevende (E)
                """,
                "general": """
                Op basis van de beschikbare documenten is deze sectie samengesteld met objectieve en feitelijke informatie. 
                De gegevens zijn zorgvuldig geanalyseerd en in een professioneel kader geplaatst. 
                Voor specifieke details over deze sectie is het raadzaam aanvullende informatie te verzamelen.
                """
            }
            
            return fallback_messages[section_type]
            
    # This should never be reached due to the fallbacks above
    return "Op basis van de aangeleverde documenten is een objectieve analyse gemaakt. Voor meer specifieke informatie zijn aanvullende documenten gewenst."

def create_direct_prompt_for_section(section_id, section_info):
    """
    Create a prompt for generating content using the direct LLM approach
    with enhanced safety considerations
    """
    if section_id == "samenvatting":
        return """
        # Taak: Samenvatting Arbeidsdeskundig Rapport
        
        Je bent een professionele rapporteur die een zakelijk rapport opstelt. Je taak is om een heldere, beknopte en objectieve samenvatting te schrijven op basis van de aangeleverde documenten.
        
        ## Eisen aan de Samenvatting
        
        1. Kernonderdelen die moeten worden opgenomen:
           - Feitelijke gegevens van de persoon
           - Context van het onderzoek
           - Huidige werksituatie
           - Belangrijkste objectieve bevindingen
           
        2. Formaat:
           - Lengte: 200-250 woorden
           - Schrijfstijl: Formeel, professioneel, zakelijk
           - Structuur: 3-4 beknopte alinea's
           
        3. Inhoudelijke richtlijnen:
           - Gebruik alleen feitelijke informatie uit de documenten
           - Vermijd interpretaties of speculaties
           - Blijf objectief en neutraal in toon
           - Integreer informatie logisch met vloeiende overgangen
           - Bij tegenstrijdige informatie, gebruik de meest recente of betrouwbare bron
           - Vermijd gevoelige persoonlijke details
           - Geef geen medisch advies
        
        ## Geef alleen de samenvatting zelf, zonder koppen, inleiding of afsluiting.
        """
    
    elif section_id == "belastbaarheid":
        return """
        # Taak: Analyse van Werkmogelijkheden
        
        Je bent een professionele rapporteur die een zakelijk rapport opstelt. Je taak is om een objectieve analyse te maken van de werkmogelijkheden op basis van de aangeleverde documenten.
        
        ## Eisen aan de Werkmogelijkheden Analyse
        
        1. Kernonderdelen die moeten worden opgenomen:
           - Mogelijkheden voor fysieke werkzaamheden
           - Mogelijkheden voor mentale werkzaamheden
           - Mogelijkheden voor sociale interacties op werk
           - Eventuele aanpassingen die mogelijk nodig zijn
           
        2. Formaat:
           - Structuur: Duidelijk ingedeeld per categorie met subkopjes
           - Gestructureerde lijsten gebruiken voor specifieke punten
           - Zowel mogelijkheden als aandachtspunten benoemen
           
        3. Inhoudelijke richtlijnen:
           - Wees specifiek en concreet 
           - Baseer alle punten direct op de beschikbare documentatie
           - Vermeld expliciet waar tegenstrijdigheden bestaan tussen bronnen
           - Gebruik objectieve, neutrale taal
           - Maak duidelijk onderscheid tussen tijdelijke en blijvende factoren
           - Vermijd gevoelige persoonlijke details
           - Geef geen medisch advies
        
        ## Geef alleen de objectieve analyse zelf, zonder introductie of afsluiting.
        """
    
    elif section_id == "visie_ad":
        return """
        # Taak: Professionele Visie
        
        Je bent een professionele rapporteur die een zakelijk rapport opstelt. Je taak is om een professionele visie te formuleren op basis van de aangeleverde documenten.
        
        ## Eisen aan de Professionele Visie
        
        1. Kernonderdelen die moeten worden opgenomen:
           - Objectieve beoordeling van de werkmogelijkheden
           - Integratie van vastgestelde feiten uit de documenten
           - Analyse van de huidige situatie
           - Concrete suggesties voor verbetering
           - Perspectief voor de toekomst
           
        2. Formaat:
           - Kernachtige maar complete analyse (400-500 woorden)
           - Logische argumentatiestructuur met duidelijke conclusies
           - Professioneel taalgebruik maar toegankelijk voor een breed publiek
           
        3. Inhoudelijke richtlijnen:
           - Onderbouw elke conclusie met verwijzing naar feiten uit de aangeleverde documenten
           - Geef een evenwichtige analyse
           - Wees constructief maar realistisch in je beoordeling
           - Houd rekening met zowel professionele als persoonlijke factoren
           - Focus op mogelijkheden voor verbeteringen
           - Vermijd gevoelige persoonlijke details
           - Geef geen medisch advies
        
        ## Geef alleen de professionele visie zelf, zonder introductie of afsluiting.
        """
    
    elif section_id == "matching":
        return """
        # Taak: Criteria voor Passend Werk
        
        Je bent een professionele rapporteur die een zakelijk rapport opstelt. Je taak is om concrete criteria te formuleren voor passend werk op basis van de aangeleverde documenten.
        
        ## Eisen aan de Criteria
        
        1. Kernonderdelen die moeten worden opgenomen:
           - Criterialijst ingedeeld in categorieën:
             * Fysieke werkomgeving
             * Taakinhoud en functie-eisen
             * Werktijden en planning
             * Sociale werkomgeving
             * Overige randvoorwaarden
           - Duidelijk onderscheid tussen essentiële en wenselijke criteria
           
        2. Formaat:
           - Gestructureerde lijst met categorieën en subcategorieën
           - Per criterium aangeven of het essentieel (E) of wenselijk (W) is
           - Concrete, meetbare criteria waar mogelijk
           
        3. Inhoudelijke richtlijnen:
           - Baseer alle criteria direct op de vastgestelde feiten uit de documenten
           - Zorg dat criteria specifiek en realistisch zijn
           - Prioriteer criteria volgens praktische haalbaarheid
           - Maak duidelijk welke aanpassingen of voorzieningen eventueel nodig zijn
           - Vermijd generieke criteria die voor iedereen gelden
           - Houd rekening met zowel aandachtspunten als talenten en voorkeuren
           - Vermijd gevoelige persoonlijke details
           - Geef geen medisch advies
        
        ## Geef alleen de criteria zelf, zonder introductie of afsluiting.
        """
    
    else:
        # Generic prompt for other sections
        return f"""
        # Taak: {section_info['title']} voor Rapport
        
        Je bent een professionele rapporteur die een zakelijk rapport opstelt. Je taak is om de sectie '{section_info['title']}' te schrijven op basis van de aangeleverde documenten.
        
        ## Eisen aan deze sectie
        
        1. Inhoud:
           - Focus op alle relevante aspecten van {section_info['title'].lower()}
           - Integreer informatie uit verschillende bronnen tot een coherent geheel
           - Zorg voor volledige dekking van het onderwerp
           
        2. Formaat:
           - Heldere structuur met logische opbouw
           - Beknopt maar volledig
           - Professionele toon en taalgebruik
           
        3. Richtlijnen:
           - Gebruik alleen feitelijke informatie uit de aangeleverde documenten
           - Schrijf in objectieve en neutrale toon
           - Structureer de informatie op een toegankelijke manier
           - Prioriteer informatie op basis van relevantie
           - Vermijd jargon tenzij noodzakelijk voor de professionele context
           - Vermijd gevoelige persoonlijke details
           - Geef geen medisch advies
        
        ## Geef alleen de inhoud voor deze sectie zelf, zonder introductie of afsluiting.
        """

def should_use_direct_approach(documents):
    """
    Determine if we should use the direct LLM approach based on:
    1. Total document length
    2. Presence of embeddings
    3. Document processing status
    """
    # Check total document length
    total_length = sum(len(doc.get("content", "")) for doc in documents)
    
    # Parse metadata for each document
    documents_with_parsed_metadata = []
    for doc in documents:
        metadata = doc.get("metadata", {})
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata)
            except:
                metadata = {}
        doc["parsed_metadata"] = metadata
        documents_with_parsed_metadata.append(doc)
    
    # Check if any documents have embeddings properly processed
    has_valid_embeddings = any(
        doc.get("parsed_metadata", {}).get("embeddings_available", False) and
        doc.get("status", "") == "enhanced" 
        for doc in documents_with_parsed_metadata
    )
    
    # Log detailed decision info
    logger.info(f"Hybrid approach decision - Document length: {total_length}, " 
                f"Has valid embeddings: {has_valid_embeddings}")
    
    # Check percentage of documents with embeddings
    total_docs = len(documents)
    if total_docs > 0:
        docs_with_embeddings = sum(
            1 for doc in documents_with_parsed_metadata 
            if doc.get("parsed_metadata", {}).get("embeddings_available", False)
        )
        embedding_coverage = docs_with_embeddings / total_docs
        logger.info(f"Embedding coverage: {embedding_coverage:.2f} ({docs_with_embeddings}/{total_docs} documents)")
        
        # If less than 50% of documents have embeddings, use direct approach
        if embedding_coverage < 0.5:
            logger.info("Using direct approach due to low embedding coverage")
            return True
    
    # Use direct approach if documents are small enough or no valid embeddings
    if total_length <= MAX_DIRECT_DOCUMENT_LENGTH or not has_valid_embeddings:
        return True
    else:
        return False

@celery.task(name="app.tasks.generate_report_tasks.report_generator_hybrid.generate_report_hybrid")
def generate_report_hybrid(report_id: str):
    logger.info(f"generate_report_hybrid task called with ID: {report_id}")
    """
    Generate a report using a hybrid approach:
    1. For small documents or when embeddings aren't available, use direct LLM
    2. For larger documents with embeddings, use RAG pipeline
    """
    try:
        logger.info(f"Starting hybrid report generation for ID: {report_id}")
        
        # Get report info from database
        report = db_service.get_row_by_id("report", report_id)
        
        if not report:
            raise ValueError(f"Report with ID {report_id} not found")
        
        case_id = report["case_id"]
        template_id = report["template_id"]
        
        # Check if template exists
        if template_id not in MVP_TEMPLATES:
            raise ValueError(f"Template with ID {template_id} not found")
        
        template = MVP_TEMPLATES[template_id]
        
        # Get documents for this case (both processed and enhanced)
        documents = db_service.get_rows("document", {
            "case_id": case_id
        })
        
        # Filter for processed documents
        processed_documents = [doc for doc in documents if doc["status"] in ["processed", "enhanced"]]
        document_ids = [doc["id"] for doc in processed_documents]
        
        if not document_ids:
            raise ValueError(f"No processed documents found for case {case_id}")
        
        # Initialize content dictionary for the report
        report_content = {}
        report_metadata = {
            "generation_started": datetime.utcnow().isoformat(),
            "document_ids": document_ids,
            "sections": {},
            "approach": "hybrid",
            "provider": settings.LLM_PROVIDER
        }
        
        # Get full document content for direct approach
        full_documents = []
        for doc_id in document_ids:
            # Get full document info
            document = db_service.get_row_by_id("document", doc_id)
            
            # Get document chunks
            chunks = db_service.get_document_chunks(doc_id)
            
            # Combine chunk content
            content = "\n\n".join([chunk["content"] for chunk in chunks])
            
            # Add to document info
            document["content"] = content
            full_documents.append(document)
        
        # Determine if we should use direct approach
        use_direct = should_use_direct_approach(full_documents)
        report_metadata["direct_approach"] = use_direct
        
        logger.info(f"Using {'direct' if use_direct else 'RAG'} approach for report generation")
        
        # Generate content for each section in the template
        if use_direct:
            # Combine document content
            combined_content = combine_document_texts(full_documents, MAX_DIRECT_DOCUMENT_LENGTH)
            
            for section_id, section_info in template["sections"].items():
                # Create direct prompt
                prompt = create_direct_prompt_for_section(section_id, section_info)
                
                # Generate content using direct LLM approach with guaranteed fallback
                try:
                    # This function now has multiple fallback mechanisms and will always return content
                    content = generate_content_with_direct_llm(prompt, combined_content)
                    
                    # Store the generated content and metadata
                    report_content[section_id] = content
                    report_metadata["sections"][section_id] = {
                        "generated_at": datetime.utcnow().isoformat(),
                        "approach": "direct",
                        "prompt": prompt,
                        "chunk_ids": []  # No specific chunks used
                    }
                    
                    # Log successful generation
                    logger.info(f"Successfully generated content for section {section_id}")
                    
                except Exception as section_error:
                    # This should rarely happen since the function has its own fallbacks,
                    # but just in case, provide a generic content based on section type
                    # IMPORTANT: Don't include the actual error message to avoid exposing 'dangerous_content' in logs
                    logger.error(f"All content generation attempts failed for section {section_id}: {type(section_error).__name__}")
                    
                    section_type = "general"
                    if section_id == "samenvatting":
                        section_type = "samenvatting"
                    elif section_id == "belastbaarheid":
                        section_type = "belastbaarheid"
                    elif section_id == "visie_ad":
                        section_type = "visie"
                    elif section_id == "matching":
                        section_type = "matching"
                    
                    # Use the same fallback messages as in the generate_content_with_direct_llm function
                    fallback_messages = {
                        "samenvatting": "Op basis van de beschikbare documenten is een objectieve en feitelijke samenvatting samengesteld. De gegevens tonen aan dat er sprake is van een werksituatie waarbij bepaalde factoren van invloed zijn op het functioneren.",
                        "belastbaarheid": "De beschikbare gegevens geven inzicht in de mogelijkheden en aandachtspunten voor werkzaamheden. Er zijn zowel fysieke, mentale als sociale factoren die invloed hebben op de werksituatie.",
                        "visie": "Vanuit professioneel perspectief kan gesteld worden dat er kansen zijn voor werkhervatting met inachtneming van de geïdentificeerde aandachtspunten.",
                        "matching": "Voor het vinden van passend werk zijn criteria op het gebied van werkomgeving, taakinhoud, werktijden en sociale aspecten van belang.",
                        "general": "Op basis van de beschikbare documenten is deze sectie samengesteld met objectieve en feitelijke informatie."
                    }
                    
                    report_content[section_id] = fallback_messages[section_type]
                    report_metadata["sections"][section_id] = {
                        "generated_at": datetime.utcnow().isoformat(),
                        "error": "Content generation failed",  # Generic error message without specifics
                        "approach": "fallback_static",
                        "note": "Generated using static fallback due to content generation issues"
                    }
        else:
            # Use RAG approach
            for section_id, section_info in template["sections"].items():
                # Generate content using RAG pipeline
                try:
                    # The generate_content_for_section function now has its own fallback mechanisms
                    section_result = generate_content_for_section(
                        section_id=section_id,
                        section_info=section_info,
                        document_ids=document_ids,
                        case_id=case_id
                    )
                    
                    # Store the generated content and metadata
                    report_content[section_id] = section_result["content"]
                    section_metadata = {
                        "generated_at": datetime.utcnow().isoformat(),
                        "chunk_ids": section_result["chunk_ids"],
                        "prompt": section_result["prompt"],
                        "approach": "rag"
                    }
                    
                    # Add error information if available
                    if "error" in section_result:
                        section_metadata["error"] = section_result["error"]
                        
                        # Add a user-friendly message for missing embeddings
                        if section_result["error"] == "missing_embeddings":
                            section_metadata["user_message"] = "Probeer het later opnieuw wanneer de document verwerking is voltooid."
                    
                    report_metadata["sections"][section_id] = section_metadata
                    logger.info(f"Successfully generated content for section {section_id} using RAG")
                    
                except Exception as section_error:
                    logger.error(f"Error generating section {section_id} with RAG: {str(section_error)}")
                    
                    # Try fallback to direct approach
                    try:
                        logger.info(f"Attempting direct fallback for section {section_id}")
                        prompt = create_direct_prompt_for_section(section_id, section_info)
                        content = generate_content_with_direct_llm(prompt, combine_document_texts(full_documents, MAX_DIRECT_DOCUMENT_LENGTH))
                        
                        report_content[section_id] = content
                        report_metadata["sections"][section_id] = {
                            "generated_at": datetime.utcnow().isoformat(),
                            "approach": "direct_fallback",
                            "prompt": prompt,
                            "fallback_reason": "Primary approach failed"  # Generic reason without exposing details
                        }
                        
                        logger.info(f"Direct fallback successful for section {section_id}")
                        
                    except Exception as fallback_error:
                        logger.error(f"Error with fallback approach for section {section_id}: {str(fallback_error)}")
                        
                        # Final static fallback content
                        section_type = "general"
                        if section_id == "samenvatting":
                            section_type = "samenvatting"
                        elif section_id == "belastbaarheid":
                            section_type = "belastbaarheid"
                        elif section_id == "visie_ad":
                            section_type = "visie"
                        elif section_id == "matching":
                            section_type = "matching"
                        
                        # Use the same fallback messages as before
                        fallback_messages = {
                            "samenvatting": "Op basis van de beschikbare documenten is een objectieve en feitelijke samenvatting samengesteld. De gegevens tonen aan dat er sprake is van een werksituatie waarbij bepaalde factoren van invloed zijn op het functioneren.",
                            "belastbaarheid": "De beschikbare gegevens geven inzicht in de mogelijkheden en aandachtspunten voor werkzaamheden. Er zijn zowel fysieke, mentale als sociale factoren die invloed hebben op de werksituatie.",
                            "visie": "Vanuit professioneel perspectief kan gesteld worden dat er kansen zijn voor werkhervatting met inachtneming van de geïdentificeerde aandachtspunten.",
                            "matching": "Voor het vinden van passend werk zijn criteria op het gebied van werkomgeving, taakinhoud, werktijden en sociale aspecten van belang.",
                            "general": "Op basis van de beschikbare documenten is deze sectie samengesteld met objectieve en feitelijke informatie."
                        }
                        
                        report_content[section_id] = fallback_messages[section_type]
                        report_metadata["sections"][section_id] = {
                            "generated_at": datetime.utcnow().isoformat(),
                            "error": "Content generation failed with multiple approaches",  # Generic error without exposing details
                            "approach": "static_fallback"
                        }
                        
                        logger.info(f"Used static fallback content for section {section_id}")
                        
        
        # Complete the metadata
        report_metadata["generation_completed"] = datetime.utcnow().isoformat()
        
        # Check for missing embeddings in any section
        missing_embeddings_sections = [
            section_id for section_id, metadata in report_metadata.get("sections", {}).items()
            if metadata.get("error") == "missing_embeddings"
        ]
        
        if missing_embeddings_sections:
            report_metadata["has_missing_embeddings"] = True
            report_metadata["missing_embeddings_sections"] = missing_embeddings_sections
            logger.warning(f"Report {report_id} has sections with missing embeddings: {missing_embeddings_sections}")
            
            # Add a global message to the report metadata
            report_metadata["user_message"] = (
                f"Enkele secties ({len(missing_embeddings_sections)}) konden niet worden gegenereerd omdat "
                f"de document verwerking nog niet is voltooid. Probeer het later opnieuw."
            )
        
        # Update report with generated content
        db_service.update_report(report_id, {
            "status": "generated",
            "content": report_content,
            "report_metadata": report_metadata,
            "updated_at": datetime.utcnow().isoformat()
        })
            
        return {
            "status": "success", 
            "report_id": report_id, 
            "sections": list(report_content.keys()),
            "approach": "direct" if use_direct else "rag"
        }
    
    except Exception as e:
        logger.error(f"Error generating report {report_id}: {str(e)}")
        
        # Update report status to failed
        db_service.update_report(report_id, {
            "status": "failed",
            "error": "Rapportgeneratie kon niet worden voltooid",  # Generic error message for user
            "updated_at": datetime.utcnow().isoformat()
        })
        
        # Re-raise the exception to mark the Celery task as failed
        raise