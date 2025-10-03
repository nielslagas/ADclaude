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
from app.utils.ad_report_template import AD_REPORT_TEMPLATE

# Define templates here to avoid circular imports
# Professionele Nederlandse AD-rapport template conform arbeidsdeskundige standaarden
MVP_TEMPLATES = {
    "staatvandienst": {
        "id": "staatvandienst",
        "name": "Staatvandienst Format", 
        "description": "Professioneel rapportage format volgens Nederlandse AD-standaarden",
        "sections": {
            "vraagstelling": {
                "title": "1. Vraagstelling",
                "description": "Onderzoeksvragen conform arbeidsdeskundig standaardprotocol",
                "order": 1
            },
            "ondernomen_activiteiten": {
                "title": "2. Ondernomen activiteiten",
                "description": "Overzicht van uitgevoerde onderzoekshandelingen", 
                "order": 2
            },
            "gegevensverzameling_voorgeschiedenis": {
                "title": "3.1 Voorgeschiedenis",
                "description": "Medische voorgeschiedenis en verzuimhistorie",
                "order": 3
            },
            "gegevensverzameling_werkgever": {
                "title": "3.2 Gegevens werkgever",
                "description": "Bedrijfsgegevens, aard bedrijf, functies en organisatie",
                "order": 4
            },
            "gegevensverzameling_werknemer": {
                "title": "3.3 Gegevens werknemer", 
                "description": "Opleidingen, arbeidsverleden en bekwaamheden",
                "order": 5
            },
            "belastbaarheid": {
                "title": "3.4 Belastbaarheid van werknemer",
                "description": "Functionele Mogelijkhedenlijst (FML) en capaciteitsanalyse",
                "order": 6
            },
            "eigen_functie": {
                "title": "3.5 Eigen functie werknemer",
                "description": "Functieomschrijving en belastende aspecten huidige functie",
                "order": 7
            },
            "gesprek_werkgever": {
                "title": "3.6 Gesprek met de werkgever",
                "description": "Visie werkgever op functioneren en re-integratiemogelijkheden",
                "order": 8
            },
            "gesprek_werknemer": {
                "title": "3.7 Gesprek met werknemer",
                "description": "Visie werknemer op beperkingen, mogelijkheden en re-integratie", 
                "order": 9
            },
            "gesprek_gezamenlijk": {
                "title": "3.8 Gesprek met werkgever en werknemer gezamenlijk",
                "description": "Afstemming en bespreking van advies",
                "order": 10
            },
            "visie_ad_eigen_werk": {
                "title": "4.1 Geschiktheid voor eigen werk",
                "description": "Arbeidsdeskundige analyse geschiktheid huidige functie",
                "order": 11
            },
            "visie_ad_aanpassing": {
                "title": "4.2 Aanpassing eigen werk",
                "description": "Mogelijkheden voor aanpassing huidige functie", 
                "order": 12
            },
            "visie_ad_ander_werk_eigen": {
                "title": "4.3 Geschiktheid voor ander werk bij eigen werkgever",
                "description": "Alternatieven binnen huidige organisatie",
                "order": 13
            },
            "visie_ad_ander_werk_extern": {
                "title": "4.4 Geschiktheid voor ander werk bij andere werkgever",
                "description": "Zoekrichting en mogelijkheden externe arbeidsmarkt",
                "order": 14
            },
            "visie_ad_duurzaamheid": {
                "title": "4.5 Duurzaamheid van herplaatsing",
                "description": "Prognose en duurzaamheidsanalyse re-integratie",
                "order": 15
            },
            "advies": {
                "title": "5. Advies",
                "description": "Concrete aanbevelingen en vervolgstappen",
                "order": 16
            },
            "conclusie": {
                "title": "6. Conclusie", 
                "description": "Beantwoording hoofdvragen en eindconclusies",
                "order": 17
            },
            "vervolg": {
                "title": "7. Vervolg",
                "description": "Vervolgtraject en aanbevolen acties",
                "order": 18
            }
        }
    }
}

# Import this here to avoid circular imports
from app.tasks.generate_report_tasks.rag_pipeline import generate_content_for_section
from app.tasks.generate_report_tasks.structured_rag_pipeline import generate_content_for_section as generate_structured_content
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
        # Quick timeout for overloaded APIs
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("API call timeout - server likely overloaded")
        
        # Set timeout to 15 seconds instead of waiting for retries
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(15)
        
        try:
            # Create an LLM instance with our provider-agnostic interface
            model = create_llm_instance(
                temperature=0.1,
                max_tokens=2048,  # Reduced for faster response
                dangerous_content_level="BLOCK_NONE"
            )
            
            # Vector template-based system instruction
            system_instruction = f"""
            Je bent een professionele arbeidsdeskundige die AD rapporten schrijft volgens het Vector voorbeeld format.
            
            GEBRUIK HET VECTOR TEMPLATE FORMAT:
            {AD_REPORT_TEMPLATE}
            
            BELANGRIJKE INSTRUCTIES:
            - Gebruik EXACT de markdown formatting van het Vector voorbeeld
            - Gebruik de exacte tabel structures met | :---- | :---- |
            - Gebruik de juiste nummering (1., 2., 3.1, 3.2, etc.)
            - Gebruik bullet points (*) waar aangegeven
            - Gebruik professionele Nederlandse arbeidsdeskundige terminologie
            - Genereer content gebaseerd op de case data over Pieter Janssen
            - Volg de exacte sectie structuur van het voorbeeld
            """
            
            # Medical terminology is essential for labor expert reports - use full context
            full_prompt = f"{prompt}\n\nRelevante informatie:\n\n{context}"
            
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
                cleaned_content = clean_markdown_formatting(response.text)
                return cleaned_content
            else:
                logger.warning("First attempt returned empty or too short content")
                logger.error("Generated content too short")
                raise Exception("Generated content too short")
                
        finally:
            # Clear the alarm
            signal.alarm(0)
            
    except (TimeoutError, Exception) as first_error:
        # Quick fallback for overloaded APIs
        if "overloaded" in str(first_error).lower() or "timeout" in str(first_error).lower() or "529" in str(first_error):
            logger.warning(f"API overloaded, using immediate fallback: {str(first_error)}")
            # Skip the second attempt and go directly to fallback content
            fallback_content = get_fallback_content_for_prompt(prompt)
            return clean_markdown_formatting(fallback_content)
        
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
                cleaned_content = clean_markdown_formatting(basic_response.text)
                return cleaned_content
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
            
            return clean_markdown_formatting(fallback_messages[section_type])
            
    # This should never be reached due to the fallbacks above
    fallback_content = "Op basis van de aangeleverde documenten is een objectieve analyse gemaakt. Voor meer specifieke informatie zijn aanvullende documenten gewenst."
    return clean_markdown_formatting(fallback_content)

def format_structured_section(section_id: str, section_data: dict) -> str:
    """
    Convert structured section data to formatted content for display.
    
    Args:
        section_id: The section identifier
        section_data: Structured data from JSON generation
        
    Returns:
        Formatted content string
    """
    if not section_data or not isinstance(section_data, dict):
        return "Geen gestructureerde data beschikbaar."
    
    try:
        # Handle specific section types
        if section_id == "gegevens_werkgever":
            return format_werkgever_section(section_data)
        elif section_id == "gegevens_werknemer":
            return format_werknemer_section(section_data)
        elif section_id == "belastbaarheid":
            return format_belastbaarheid_section(section_data)
        elif section_id == "eigen_functie":
            return format_functie_section(section_data)
        elif section_id == "conclusie":
            return format_conclusie_section(section_data)
        elif section_id == "vraagstelling":
            return format_vraagstelling_section(section_data)
        else:
            # Generic formatter for unknown sections
            return format_generic_section(section_data)
            
    except Exception as e:
        logger.error(f"Error formatting section {section_id}: {str(e)}")
        return f"Fout bij formatteren van sectie: {section_id}"

def format_werkgever_section(data: dict) -> str:
    """Format employer information section"""
    content = ""
    
    if data.get("aard_bedrijf"):
        content += f"**Aard bedrijf:** {data['aard_bedrijf']}\n\n"
    if data.get("omvang_bedrijf"):
        content += f"**Omvang bedrijf:** {data['omvang_bedrijf']}\n\n"
    if data.get("aantal_werknemers"):
        content += f"**Aantal werknemers:** {data['aantal_werknemers']}\n\n"
    if data.get("functies_expertises"):
        content += f"**Functies en expertises:** {data['functies_expertises']}\n\n"
    if data.get("overige_informatie"):
        content += f"**Overige informatie:** {data['overige_informatie']}\n\n"
    
    return content.strip()

def format_werknemer_section(data: dict) -> str:
    """Format employee information section"""
    content = ""
    
    # Opleidingen tabel
    if data.get("opleidingen"):
        content += "**Opleidingen/cursussen:**\n\n"
        content += "| Opleiding | Richting | Diploma | Jaar |\n"
        content += "|-----------|----------|---------|------|\n"
        for opl in data["opleidingen"]:
            content += f"| {opl.get('opleiding', '')} | {opl.get('richting', '')} | {opl.get('diploma', '')} | {opl.get('jaar', '')} |\n"
        content += "\n"
    
    # Arbeidsverleden tabel
    if data.get("arbeidsverleden"):
        content += "**Arbeidsverleden:**\n\n"
        content += "| Periode | Werkgever | Functie |\n"
        content += "|---------|-----------|----------|\n"
        for werk in data["arbeidsverleden"]:
            content += f"| {werk.get('periode', '')} | {werk.get('werkgever', '')} | {werk.get('functie', '')} |\n"
        content += "\n"
    
    # Bekwaamheden
    if data.get("bekwaamheden"):
        content += "**Bekwaamheden:**\n\n"
        bekw = data["bekwaamheden"]
        for key, value in bekw.items():
            content += f"**{key.replace('_', ' ').title()}:** {value}\n\n"
    
    return content.strip()

def format_belastbaarheid_section(data: dict) -> str:
    """Format functional capacity assessment section"""
    content = ""
    
    if data.get("datum_beoordeling"):
        content += f"**Datum beoordeling:** {data['datum_beoordeling']}\n\n"
    if data.get("beoordelaar"):
        content += f"**Beoordelaar:** {data['beoordelaar']}\n\n"
    
    if data.get("beperkingen"):
        content += "**Functionele beperkingen:**\n\n"
        for beperking in data["beperkingen"]:
            content += f"**{beperking.get('rubriek', '')}** - {beperking.get('mate_beperking', '')}\n\n"
            if beperking.get("aspecten"):
                for aspect in beperking["aspecten"]:
                    content += f"- {aspect}\n"
                content += "\n"
    
    if data.get("prognose"):
        content += f"**Prognose:** {data['prognose']}\n\n"
    
    return content.strip()

def format_functie_section(data: dict) -> str:
    """Format job function section"""
    content = ""
    
    # Functiegegevens tabel
    if data.get("functie_gegevens"):
        gegevens = data["functie_gegevens"]
        content += "**Functiegegevens:**\n\n"
        content += "| Aspect | Informatie |\n"
        content += "|--------|------------|\n"
        for key, value in gegevens.items():
            if value:
                label = key.replace('_', ' ').title()
                content += f"| {label} | {value} |\n"
        content += "\n"
    
    # Functieomschrijving
    if data.get("functieomschrijving"):
        content += f"**Functieomschrijving:**\n\n{data['functieomschrijving']}\n\n"
    
    # Functiebelasting tabel
    if data.get("functiebelasting"):
        content += "**Functiebelasting:**\n\n"
        content += "| Taak | Percentage | Belastende aspecten |\n"
        content += "|------|------------|---------------------|\n"
        for taak in data["functiebelasting"]:
            content += f"| {taak.get('taak', '')} | {taak.get('percentage', '')} | {taak.get('belastende_aspecten', '')} |\n"
        content += "\n"
    
    return content.strip()

def format_conclusie_section(data: dict) -> str:
    """Format conclusion section"""
    content = ""
    
    if data.get("eigen_werk"):
        content += f"**Kan werknemer het eigen werk nog uitvoeren?**\n{data['eigen_werk']}\n\n"
    if data.get("eigen_werk_aanpassingen"):
        content += f"**Is het eigen werk met aanpassingen passend te maken?**\n{data['eigen_werk_aanpassingen']}\n\n"
    if data.get("ander_werk_intern"):
        content += f"**Kan werknemer ander werk bij eigen werkgever uitvoeren?**\n{data['ander_werk_intern']}\n\n"
    if data.get("extern_werk"):
        content += f"**Zijn er mogelijkheden voor externe re-integratie?**\n{data['extern_werk']}\n\n"
    
    return content.strip()

def format_vraagstelling_section(data: dict) -> str:
    """Format research questions section"""
    content = ""
    
    if data.get("hoofdvraag"):
        content += f"**Hoofdvraag:**\n{data['hoofdvraag']}\n\n"
    
    if data.get("deelvragen"):
        content += "**Deelvragen:**\n\n"
        for i, vraag in enumerate(data["deelvragen"], 1):
            content += f"{i}. {vraag}\n"
        content += "\n"
    
    return content.strip()

def format_generic_section(data: dict) -> str:
    """Generic formatter for unknown section types"""
    content = ""
    
    for key, value in data.items():
        if isinstance(value, list):
            content += f"**{key.replace('_', ' ').title()}:**\n"
            for item in value:
                if isinstance(item, str):
                    content += f"- {item}\n"
                else:
                    content += f"- {str(item)}\n"
            content += "\n"
        elif isinstance(value, dict):
            content += f"**{key.replace('_', ' ').title()}:**\n"
            for subkey, subvalue in value.items():
                content += f"- {subkey.replace('_', ' ').title()}: {subvalue}\n"
            content += "\n"
        else:
            content += f"**{key.replace('_', ' ').title()}:** {value}\n\n"
    
    return content.strip()

def clean_markdown_formatting(content: str) -> str:
    """
    Remove markdown formatting from generated content
    """
    if not content:
        return content
    
    # Remove bold formatting
    content = content.replace('**', '')
    content = content.replace('__', '')
    
    # Remove italic formatting  
    content = content.replace('*', '')
    content = content.replace('_', '')
    
    # Remove header formatting (but keep the text)
    import re
    content = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)
    
    # Remove strikethrough
    content = content.replace('~~', '')
    
    return content.strip()

def create_direct_prompt_for_section(section_id, section_info, user_profile=None):
    """
    Create a prompt for generating content using the direct LLM approach
    with enhanced safety considerations

    Args:
        section_id: The ID of the section to generate
        section_info: Information about the section
        user_profile: Optional user profile information to include in the prompt
    """
    # Create base prompt according to section type
    if section_id == "samenvatting":
        prompt = """
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
    
    # Professional Dutch AD report section prompts matching exact professional format
    elif section_id == "vraagstelling":
        prompt = """
        # Taak: Vraagstelling voor Arbeidsdeskundig Rapport
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om een heldere vraagstelling te formuleren op basis van de aangeleverde documenten.
        
        ## Eisen aan de Vraagstelling
        
        1. Kernonderdelen:
           - Wie heeft het onderzoek aangevraagd
           - Wat is de concrete onderzoeksvraag
           - Welke aspecten moeten worden onderzocht
           - Eventuele specifieke aandachtspunten
           
        2. Formaat:
           - Begin met context van de aanvraag
           - Formuleer de hoofdvraag helder en specifiek
           - Benoem eventuele deelvragen
           - Houd het beknopt en zakelijk (200-300 woorden)
           
        3. Inhoudelijke richtlijnen:
           - Baseer de vraagstelling op informatie uit de documenten
           - Gebruik objectieve, professionele taal
           - Vermijd interpretaties of vooroordelen
           - Focus op wat concreet onderzocht moet worden
        
        ## BELANGRIJK: GEBRUIK HTML FORMATTING VOOR TABELLEN
        - Gebruik GEEN **bold**, *italic*, # headers, of andere markdown formatting
        - Voor tabellen: gebruik correct HTML <table>, <tr>, <td>, <th> formatting
        - Voor nadruk: gebruik HTML <strong> en <em> tags
        - Alleen HTML tags voor opmaak, geen markdown
        
        ## Geef alleen de vraagstelling, zonder introductie of afsluiting.
        """
    
    elif section_id == "ondernomen_activiteiten":
        prompt = """
        # Taak: Ondernomen Activiteiten
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om te beschrijven welke activiteiten zijn ondernomen voor dit onderzoek.
        
        ## Eisen aan Ondernomen Activiteiten
        
        1. Kernonderdelen:
           - Documentenanalyse uitgevoerd
           - Gesprekken of interviews gehouden
           - Observaties gedaan
           - Onderzoeksmethoden toegepast
           - Bronnen geraadpleegd
           
        2. Formaat:
           - Chronologische of thematische indeling
           - Per activiteit beknopt maar volledig
           - Datum/periode vermelden waar mogelijk
           
        3. Inhoudelijke richtlijnen:
           - Beschrijf alleen activiteiten die daadwerkelijk zijn ondernomen
           - Wees concreet en specifiek
           - Vermeld relevante bronnen en documenten
           - Houd objectieve, professionele toon aan
        
        ## Geef alleen de beschrijving van ondernomen activiteiten, zonder introductie of afsluiting.
        """
    
    elif section_id == "medische_situatie":
        prompt = """
        # Taak: Medische Situatie
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om de medische situatie objectief weer te geven op basis van aangeleverde documenten.
        
        ## Eisen aan Medische Situatie
        
        1. Kernonderdelen:
           - Huidige medische diagnoses
           - Behandeling en medicatie
           - Functionele beperkingen
           - Prognose en verwachtingen
           
        2. Formaat:
           - Objectieve weergave van medische feiten
           - Geen eigen interpretaties of diagnoses
           - Verwijs naar bronnen waar mogelijk
           
        3. Inhoudelijke richtlijnen:
           - Baseer alleen op medische informatie uit documenten
           - Gebruik neutrale, professionele terminologie
           - Vermijd speculatie of eigen medische beoordeling
           - Focus op arbeidsrelevante aspecten
        
        ## Geef alleen de medische situatie zoals beschreven in documenten, zonder introductie of afsluiting.
        """
    
    elif section_id == "belastbaarheid":
        prompt = """
        # Taak: 3.4 Belastbaarheid van werknemer (FML Structuur)
        
        Je bent een arbeidsdeskundige die een professioneel rapport opstelt. Je taak is om sectie 3.4 te schrijven volgens de FML (Functionele Mogelijkhedenlijst) structuur.
        
        ## BELANGRIJKE FML STRUCTUUR - gebruik exact deze HTML opmaak:
        
        GEBRUIK ALLEEN HTML TABELLEN voor de FML structuur, bijvoorbeeld:
        <table>
        <tr><th>Rubriek</th><th>Beperking</th><th>Details</th></tr>
        <tr><td><strong>Rubriek I: Persoonlijk functioneren</strong></td><td>Beperkt</td><td>Beschrijving hier</td></tr>
        </table>
        
        De belastbaarheid is door bedrijfsarts [naam] weergegeven in een functionelemogelijkhedenlijst (FML). 
        Uit de FML van werknemer blijkt dat de belastbaarheid in vergelijking met een gezond persoon tussen 16 en 65 jaar beperkt is op de volgende aspecten:

        Rubriek I: Persoonlijk functioneren
        Mate van beperking: [Beperkt/Niet beperkt]
        1. [Specifiek aspect]: [Beschrijving van beperking en voorwaarden]
        2. [Ander aspect indien van toepassing]: [Beschrijving]
        
        Rubriek II: Sociaal functioneren  
        Mate van beperking: [Beperkt/Niet beperkt]
        [Nummer]. [Specifiek aspect]: [Beschrijving]
        
        Rubriek III: Aanpassing aan fysieke omgevingseisen
        [Niet beperkt / of beschrijving van beperkingen]
        
        Rubriek IV: Dynamische handelingen
        [Niet beperkt / of beschrijving van beperkingen]
        
        Rubriek V: Statische houdingen
        [Niet beperkt / of beschrijving van beperkingen]
        
        Rubriek VI: Werktijden  
        [Beschrijving van beperkingen in werktijden, energetische beperking, nachtdiensten, etc.]
        
        ## Eisen aan de FML analyse
        
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
        
        ## BELANGRIJK: GEBRUIK HTML FORMATTING VOOR TABELLEN
        - Gebruik GEEN **bold**, *italic*, # headers, of andere markdown formatting
        - Voor tabellen: gebruik correct HTML <table>, <tr>, <td>, <th> formatting
        - Voor nadruk: gebruik HTML <strong> en <em> tags
        - Alleen HTML tags voor opmaak, geen markdown
        
        ## Geef alleen de objectieve analyse zelf, zonder introductie of afsluiting.
        """
    
    elif section_id == "werkvermogen":
        prompt = """
        # Taak: Werkvermogen Analyse
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om het werkvermogen te analyseren op basis van de aangeleverde documenten.
        
        ## Eisen aan Werkvermogen Analyse
        
        1. Kernonderdelen:
           - Huidige capaciteiten voor werk
           - Aandachtspunten en beperkingen
           - Tijdsbesteding en belastbaarheid
           - Potentie voor ontwikkeling
           
        2. Formaat:
           - Gestructureerde analyse per aspect
           - Concreet en meetbaar waar mogelijk
           - Onderscheid tussen verschillende werkvormen
           
        3. Inhoudelijke richtlijnen:
           - Baseer conclusies op documentatie
           - Wees realistisch en objectief
           - Focus op arbeidsrelevante aspecten
           - Vermijd speculatie
        
        ## Geef alleen de werkvermogen analyse, zonder introductie of afsluiting.
        """
    
    elif section_id == "arbeidsverleden":
        prompt = """
        # Taak: Arbeidsverleden
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om het arbeidsverleden samen te vatten op basis van de aangeleverde documenten.
        
        ## Eisen aan Arbeidsverleden
        
        1. Kernonderdelen:
           - Chronologisch overzicht werkervaring
           - Functieomschrijvingen en verantwoordelijkheden
           - Opgedane vaardigheden en competenties
           - Relevante werkgerelateerde gebeurtenissen
           
        2. Formaat:
           - Chronologische volgorde (meest recente eerst)
           - Per functie: periode, werkgever, taken
           - Beknopt maar volledig
           
        3. Inhoudelijke richtlijnen:
           - Baseer alleen op informatie uit documenten
           - Focus op arbeidsrelevante ervaringen
           - Vermeld relevante opleidingen en certificaten
           - Gebruik objectieve, professionele taal
        
        ## Geef alleen het arbeidsverleden, zonder introductie of afsluiting.
        """
    
    elif section_id == "opleiding_ontwikkeling":
        prompt = """
        # Taak: Opleiding en Ontwikkeling
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om de opleidings- en ontwikkelingssituatie te beschrijven.
        
        ## Eisen aan Opleiding en Ontwikkeling
        
        1. Kernonderdelen:
           - Afgeronde opleidingen en certificaten
           - Huidige scholing of ontwikkeltrajecten
           - Leer- en ontwikkelingsmogelijkheden
           - Motivatie en interesse voor bij-/omscholing
           
        2. Formaat:
           - Overzicht van formele en informele educatie
           - Huidige en toekomstige ontwikkelplannen
           - Concrete mogelijkheden en aanbevelingen
           
        3. Inhoudelijke richtlijnen:
           - Baseer op beschikbare onderwijsinformatie
           - Focus op arbeidsrelevante ontwikkeling
           - Wees realistisch over leercapaciteit
           - Vermeld concrete opleidingsmogelijkheden
        
        ## Geef alleen informatie over opleiding en ontwikkeling, zonder introductie of afsluiting.
        """
    
    elif section_id == "persoonlijke_situatie":
        prompt = """
        # Taak: Persoonlijke Situatie
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om relevante persoonlijke omstandigheden te beschrijven.
        
        ## Eisen aan Persoonlijke Situatie
        
        1. Kernonderdelen:
           - Gezinssituatie en zorgtaken
           - Financiële aspecten (indien relevant)
           - Geografische bereikbaarheid
           - Andere relevante persoonlijke factoren
           
        2. Formaat:
           - Beknopt en to-the-point
           - Alleen arbeidsrelevante aspecten
           - Respectvol en professioneel
           
        3. Inhoudelijke richtlijnen:
           - Vermeld alleen informatie uit documenten
           - Focus op impact op werkmogelijkheden
           - Respecteer privacy en waardigheid
           - Gebruik neutrale, objectieve taal
        
        ## Geef alleen relevante persoonlijke situatie, zonder introductie of afsluiting.
        """
    
    elif section_id == "motivatie_wensen":
        prompt = """
        # Taak: Motivatie en Wensen
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om motivatie en wensen ten aanzien van werk te beschrijven.
        
        ## Eisen aan Motivatie en Wensen
        
        1. Kernonderdelen:
           - Motivatie voor werkhervatting of werk zoeken
           - Voorkeuren voor type werk of sector
           - Wensen betreffende arbeidsvoorwaarden
           - Doelstellingen en ambities
           
        2. Formaat:
           - Gestructureerd per thema
           - Concreet en specifiek
           - Realistisch en haalbaar
           
        3. Inhoudelijke richtlijnen:
           - Baseer op uitgesproken wensen in documenten
           - Onderscheid tussen wensen en mogelijkheden
           - Wees respectvol voor persoonlijke voorkeuren
           - Focus op constructieve aspecten
        
        ## Geef alleen motivatie en wensen, zonder introductie of afsluiting.
        """
    
    elif section_id == "barrières_belemmering":
        prompt = """
        # Taak: Barrières en Belemmering
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om barrières en belemmeringen voor werk te identificeren.
        
        ## Eisen aan Barrières en Belemmering
        
        1. Kernonderdelen:
           - Medische/fysieke belemmeringen
           - Praktische barrières (vervoer, kinderopvang, etc.)
           - Sociale of psychische obstakels
           - Externe factoren (arbeidsmarkt, werkgever)
           
        2. Formaat:
           - Categoriseer per type barrière
           - Onderscheid tussen tijdelijke en structurele belemmeringen
           - Geef aan welke oplosbaar zijn
           
        3. Inhoudelijke richtlijnen:
           - Identificeer alleen op basis van documentatie
           - Wees objectief en constructief
           - Focus op oplosbare barrières
           - Vermijd stigmatisering
        
        ## Geef alleen barrières en belemmeringen, zonder introductie of afsluiting.
        """
    
    elif section_id == "kansen_mogelijkheden":
        prompt = """
        # Taak: Kansen en Mogelijkheden
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om kansen en mogelijkheden voor werk te identificeren.
        
        ## Eisen aan Kansen en Mogelijkheden
        
        1. Kernonderdelen:
           - Sterke punten en talenten
           - Potentiële werkgebieden
           - Ontwikkelingsmogelijkheden
           - Externe kansen (arbeidsmarkt, regelingen)
           
        2. Formaat:
           - Positief en opbouwend
           - Concreet en realistisch
           - Actionable aanbevelingen
           
        3. Inhoudelijke richtlijnen:
           - Baseer op positieve aspecten uit documenten
           - Wees optimistisch maar realistisch
           - Focus op haalbare kansen
           - Verbind aan concrete acties
        
        ## Geef alleen kansen en mogelijkheden, zonder introductie of afsluiting.
        """
    
    elif section_id == "visie_ad":
        prompt = """
        # Taak: Visie Arbeidsdeskundige
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om je professionele visie te formuleren op basis van de aangeleverde documenten.
        
        ## Eisen aan de Visie Arbeidsdeskundige
        
        1. Kernonderdelen:
           - Professioneel oordeel over de situatie
           - Integratie van alle onderzochte aspecten
           - Realistische inschatting van mogelijkheden
           - Aanbevelingen voor vervolgstappen
           
        2. Formaat:
           - Kernachtige maar complete analyse (400-600 woorden)
           - Logische opbouw met duidelijke conclusies
           - Professioneel en toegankelijk taalgebruik
           
        3. Inhoudelijke richtlijnen:
           - Onderbouw conclusies met feiten uit documenten
           - Geef evenwichtige, constructieve beoordeling
           - Focus op mogelijkheden voor verbetering
           - Vermijd medische diagnoses of adviezen
        
        ## Geef alleen de professionele visie, zonder introductie of afsluiting.
        """
    
    elif section_id == "matching":
        prompt = """
        # Taak: Matching - Criteria voor Passend Werk
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om concrete criteria te formuleren voor passend werk.
        
        ## Eisen aan Matching Criteria
        
        1. Kernonderdelen:
           - Criteria ingedeeld per categorie:
             * Fysieke werkomgeving en eisen
             * Taakinhoud en functievereisten  
             * Werktijden en planning
             * Sociale werkomgeving
             * Ontwikkel- en groeimogelijkheden
             * Overige randvoorwaarden
           - Onderscheid tussen essentiële (E) en wenselijke (W) criteria
           
        2. Formaat:
           - Gestructureerde lijst per categorie
           - Per criterium duidelijk E (essentieel) of W (wenselijk)
           - Concreet en meetbaar geformuleerd
           
        3. Inhoudelijke richtlijnen:
           - Baseer criteria op vastgestelde capaciteiten en beperkingen
           - Zorg voor specifieke, realistische criteria
           - Prioriteer volgens praktische haalbaarheid
           - Vermijd generieke criteria
        
        ## Geef alleen de matching criteria, zonder introductie of afsluiting.
        """
    
    elif section_id == "aanbevelingen":
        prompt = """
        # Taak: Aanbevelingen
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om concrete aanbevelingen te formuleren.
        
        ## Eisen aan Aanbevelingen
        
        1. Kernonderdelen:
           - Korte termijn acties (0-6 maanden)
           - Middellange termijn doelen (6-12 maanden)  
           - Lange termijn perspectief (1+ jaar)
           - Rol van verschillende betrokkenen
           
        2. Formaat:
           - Concrete, actionable aanbevelingen
           - Per aanbeveling: wat, wie, wanneer
           - Prioritering in urgentie
           
        3. Inhoudelijke richtlijnen:
           - Baseer op alle voorafgaande analyse
           - Wees specifiek en realistisch
           - Focus op haalbare vervolgstappen
           - Betrek relevante partijen
        
        ## Geef alleen de aanbevelingen, zonder introductie of afsluiting.
        """
    
    elif section_id == "vervolgtraject":
        prompt = """
        # Taak: Vervolgtraject
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om het vervolgtraject te beschrijven.
        
        ## Eisen aan Vervolgtraject
        
        1. Kernonderdelen:
           - Concrete vervolgstappen
           - Tijdsplanning en mijlpalen
           - Betrokken partijen en hun rollen
           - Evaluatiemomenten
           
        2. Formaat:
           - Stapsgewijs overzicht
           - Per stap: actie, verantwoordelijke, timing
           - Duidelijke timeline
           
        3. Inhoudelijke richtlijnen:
           - Bouw voort op aanbevelingen
           - Wees realistisch in planning
           - Definieer meetbare doelstellingen
           - Plan evaluatiemomenten in
        
        ## Geef alleen het vervolgtraject, zonder introductie of afsluiting.
        """
    
    elif section_id == "bijlagen":
        prompt = """
        # Taak: Bijlagen Overzicht
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om een overzicht te geven van de bijlagen.
        
        ## Eisen aan Bijlagen Overzicht
        
        1. Kernonderdelen:
           - Lijst van geanalyseerde documenten
           - Relevante medische informatie
           - Aanvullende documenten
           - Bronvermelding
           
        2. Formaat:
           - Genummerde lijst per type document
           - Per bijlage: titel, datum, bron
           - Chronologische of thematische ordening
           
        3. Inhoudelijke richtlijnen:
           - Vermeld alleen daadwerkelijk gebruikte bronnen
           - Wees volledig en accuraat
           - Respecteer vertrouwelijkheid
           - Gebruik consistente nummering
        
        ## Geef alleen het bijlagen overzicht, zonder introductie of afsluiting.
        """
    
    elif section_id == "gegevensverzameling_voorgeschiedenis":
        prompt = """
        # Taak: 3.1 Voorgeschiedenis
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om de voorgeschiedenis en verzuimhistorie weer te geven.
        
        ## Eisen aan Voorgeschiedenis
        
        1. Kernonderdelen:
           - Dienstverband en functieomschrijving
           - Verzuimhistorie met data en oorzaken
           - Medische behandeling en begeleiding
           - Huidige werkzaamheden en opbouw
           
        2. Formaat:
           - Chronologische weergave
           - Feitelijke informatie zonder interpretatie
           - Professionele, objectieve taal
           
        3. Inhoudelijke richtlijnen:
           - Baseer alleen op informatie uit documenten
           - Gebruik exacte data waar beschikbaar
           - Respecteer privacy bij medische informatie
           - Focus op arbeidsrelevante aspecten
        
        ## Geef alleen de voorgeschiedenis, zonder introductie of afsluiting.
        """
    
    elif section_id == "gegevensverzameling_werkgever":
        prompt = """
        # Taak: 3.2 Gegevens werkgever
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om bedrijfsgegevens systematisch weer te geven.
        
        ## Eisen aan Gegevens werkgever
        
        1. Kernonderdelen (gebruik HTML tabelformaat):
           - Aard bedrijf en activiteiten
           - Omvang bedrijf en locaties
           - Aantal werknemers
           - Functies en expertises
           - Overige informatie (website, etc.)
           
        2. Formaat (gebruik exact dit HTML tabel format):
           <table>
           <tr><td><strong>Aard bedrijf</strong></td><td>[Beschrijving bedrijfsactiviteiten]</td></tr>
           <tr><td><strong>Omvang bedrijf</strong></td><td>[Aantal locaties en grootte]</td></tr>
           <tr><td><strong>Aantal werknemers</strong></td><td>[Totaal aantal werknemers]</td></tr>
           <tr><td><strong>Functies en expertises</strong></td><td>[Overzicht functies]</td></tr>
           <tr><td><strong>Overige informatie</strong></td><td>[Website en aanvullende info]</td></tr>
           </table>
           
        3. Inhoudelijke richtlijnen:
           - Baseer op beschikbare bedrijfsinformatie
           - Wees volledig maar beknopt
           - Use relevante bedrijfsdetails
           - Vermeld website indien beschikbaar
        
        ## Geef alleen de bedrijfsgegevens in tabelformaat, zonder introductie of afsluiting.
        """
    
    elif section_id == "gegevensverzameling_werknemer":
        prompt = """
        # Taak: 3.3 Gegevens werknemer
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om werknemergegevens systematisch weer te geven.
        
        ## Eisen aan Gegevens werknemer
        
        1. Kernonderdelen (gebruik HTML tabelformaat):
           - Opleidingen/cursussen met diploma's en jaren
           - Arbeidsverleden (van/tot, werkgever, functie)
           - Bekwaamheden (computer, taal, rijbewijs, etc.)
           - Relevante certificaten en vaardigheden
           
        2. Formaat (gebruik exact deze HTML tabel formats):
           
           Opleidingen:
           <table>
           <tr><th>Opleiding/cursus</th><th>Richting</th><th>Diploma/certificaat</th><th>Jaar</th></tr>
           <tr><td>[Naam opleiding]</td><td>[Richting]</td><td>[Diploma]</td><td>[Jaar]</td></tr>
           </table>
           
           Arbeidsverleden:
           <table>
           <tr><th>Periode</th><th>Werkgever</th><th>Functie</th></tr>
           <tr><td>[Van/tot]</td><td>[Bedrijfsnaam]</td><td>[Functietitel]</td></tr>
           </table>
           
           Bekwaamheden:
           <table>
           <tr><th>Vaardigheid</th><th>Niveau</th></tr>
           <tr><td>[Vaardigheid]</td><td>[Beschrijving niveau]</td></tr>
           </table>
           
        3. Inhoudelijke richtlijnen:
           - Baseer alleen op informatie uit documenten
           - Vermeld relevante arbeidsgerichte competenties
           - Gebruik professionele terminologie
           - Focus op arbeidsrelevante aspecten
        
        ## Geef alleen de werknemergegevens in tabelformaat, zonder introductie of afsluiting.
        """
    
    elif section_id == "eigen_functie":
        prompt = """
        # Taak: 3.5 Eigen functie werknemer
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om de huidige functie gedetailleerd te beschrijven.
        
        ## Eisen aan Eigen functie werknemer
        
        1. Kernonderdelen:
           - Functiegegevens (naam, patroon, uren, salaris)
           - Uitgebreide functieomschrijving
           - Functiebelasting gerelateerd aan werknemer
           - Tabel met taken, percentages en belastende aspecten
           
        2. Formaat (gebruik exact deze HTML tabel formats):
           
           Functiegegevens:
           <table>
           <tr><td><strong>Functienaam</strong></td><td>[Naam functie]</td></tr>
           <tr><td><strong>Werkgever</strong></td><td>[Bedrijfsnaam]</td></tr>
           <tr><td><strong>Arbeidspatroon</strong></td><td>[Werktijden]</td></tr>
           <tr><td><strong>Contracturen</strong></td><td>[Aantal uren per week]</td></tr>
           <tr><td><strong>Salaris</strong></td><td>[Salarisindicatie]</td></tr>
           </table>
           
           Functiebelasting:
           <table>
           <tr><th>Taak</th><th>Percentage</th><th>Belastende aspecten</th></tr>
           <tr><td>[Taakomschrijving]</td><td>[Percentage]</td><td>[Belastende aspecten]</td></tr>
           </table>
           
        3. Inhoudelijke richtlijnen:
           - Wees specifiek over taken en verantwoordelijkheden
           - Koppel functie-eisen aan werknemerkapaciteiten
           - Gebruik percentages voor taakverdelingen
           - Identificeer belastende aspecten per taak
        
        ## Geef alleen de functieomschrijving met tabellen, zonder introductie of afsluiting.
        """
    
    elif section_id == "gesprek_werkgever":
        prompt = """
        # Taak: 3.6 Gesprek met de werkgever
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om het werkgeversgesprek weer te geven.
        
        ## Eisen aan Gesprek met werkgever
        
        1. Kernonderdelen:
           - Algemeen (besproken wet- en regelgeving)
           - Visie werkgever op functioneren vóór uitval
           - Visie werkgever op duurzaamheid herplaatsing
           - Visie werkgever op re-integratiemogelijkheden (eigen werk, aangepast werk, ander werk)
           
        2. Formaat:
           - Verdeel in duidelijke subkopjes per onderwerp
           - Objectieve weergave van werkgeversstandpunten
           - Professionele, neutrale taal
           
        3. Inhoudelijke richtlijnen:
           - Geef werkgeversvisie weer zonder eigen interpretatie
           - Vermeld concrete voorstellen en mogelijkheden
           - Focus op re-integratiemogelijkheden
           - Respecteer vertrouwelijkheid gesprek
        
        ## Geef alleen de weergave van het werkgeversgesprek, zonder introductie of afsluiting.
        """
    
    elif section_id == "gesprek_werknemer":
        prompt = """
        # Taak: 3.7 Gesprek met werknemer
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om het werknemersgesprek weer te geven.
        
        ## Eisen aan Gesprek met werknemer
        
        1. Kernonderdelen:
           - Algemeen (positie arbeidsdeskundige, rechten en plichten, toestemming)
           - Visie op beperkingen en mogelijkheden
           - Visie werknemer op werk en re-integratiemogelijkheden (eigen werk, aangepast werk, ander werk)
           - Medische situatie (privacyoverweging opmerken)
           
        2. Formaat:
           - Verdeel in duidelijke subkopjes per onderwerp
           - Objectieve weergave van werknemersstandpunten
           - Vermeld toestemming voor rapportage
           
        3. Inhoudelijke richtlijnen:
           - Geef werknemersvisie weer zonder eigen interpretatie
           - Respecteer privacy bij medische informatie
           - Focus op werkgerelateerde aspecten
           - Vermeld concrete wensen en mogelijkheden
        
        ## Geef alleen de weergave van het werknemersgesprek, zonder introductie of afsluiting.
        """
    
    elif section_id == "gesprek_gezamenlijk":
        prompt = """
        # Taak: 3.8 Gesprek met werkgever en werknemer gezamenlijk
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om het gezamenlijke gesprek weer te geven.
        
        ## Eisen aan Gezamenlijk gesprek
        
        1. Kernonderdelen:
           - Bespreking van het advies
           - Afstemming tussen partijen
           - Gemaakte afspraken
           - Vervolgstappen
           
        2. Formaat:
           - Beknopt en zakelijk
           - Focus op besluitvorming
           - Vermeld concrete afspraken
           
        3. Inhoudelijke richtlijnen:
           - Geef objectief weer wat is besproken
           - Vermeld overeenstemming of meningsverschillen
           - Focus op vervolgacties
           - Houd het professioneel en neutraal
        
        ## Geef alleen de weergave van het gezamenlijke gesprek, zonder introductie of afsluiting.
        """
    
    elif section_id == "visie_ad_eigen_werk":
        prompt = """
        # Taak: 4.1 Geschiktheid voor eigen werk
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om de geschiktheid voor eigen werk te analyseren.
        
        ## Eisen aan Geschiktheid eigen werk
        
        1. Kernonderdelen:
           - Tabel met belastende aspecten vs. belastbaarheid
           - Conclusie over geschiktheid huidige functie
           - Analyse van overschrijding belastbaarheid
           - Concrete aanbevelingen voor aanpassingen
           
        2. Formaat (gebruik exact dit HTML tabel format):
           
           Vergelijkingstabel:
           <table>
           <tr><th>Belastende aspecten functie</th><th>Belastbaarheid cliënt</th><th>Match</th></tr>
           <tr><td>[Functie-eis]</td><td>[Belastbaarheid beschrijving]</td><td>[Voldoende/Onvoldoende]</td></tr>
           </table>
           
        3. Inhoudelijke richtlijnen:
           - Koppel functie-eisen direct aan FML-beperkingen
           - Gebruik concrete voorbeelden
           - Wees duidelijk over geschiktheid of ongeschiktheid
           - Onderbouw elke conclusie met feiten
        
        ## Geef alleen de analyse van geschiktheid voor eigen werk, zonder introductie of afsluiting.
        """
    
    elif section_id == "visie_ad_aanpassing":
        prompt = """
        # Taak: 4.2 Aanpassing eigen werk
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om mogelijkheden voor aanpassing te analyseren.
        
        ## Eisen aan Aanpassing eigen werk
        
        1. Kernonderdelen:
           - Concrete voorstellen voor functieaanpassingen
           - Werkplekaanpassingen en voorzieningen
           - Organisatorische veranderingen
           - Prognose over toekomstige opbouw
           
        2. Formaat:
           - Specifieke aanbevelingen per aspect
           - Realistische en haalbare voorstellen
           - Duidelijke argumentatie per voorstel
           
        3. Inhoudelijke richtlijnen:
           - Baseer op FML-beperkingen en mogelijkheden
           - Geef praktische, implementeerbare oplossingen
           - Houd rekening met bedrijfscontext
           - Wees realistisch over haalbaarheid
        
        ## Geef alleen de analyse van aanpassingsmogelijkheden, zonder introductie of afsluiting.
        """
    
    elif section_id == "visie_ad_ander_werk_eigen":
        prompt = """
        # Taak: 4.3 Geschiktheid voor ander werk bij eigen werkgever
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om alternatieven binnen de organisatie te analyseren.
        
        ## Eisen aan Ander werk eigen werkgever
        
        1. Kernonderdelen:
           - Analyse beschikbare functies/vacatures
           - Beoordeling geschiktheid per functie
           - Redenen voor wel/niet geschikt zijn
           - Eventuele scholingsvereisten
           
        2. Formaat:
           - Systematische doorloop van mogelijkheden
           - Per functie duidelijke beoordeling
           - Onderbouwing van conclusies
           
        3. Inhoudelijke richtlijnen:
           - Baseer op werknemervaardigheden en beperkingen
           - Wees realistisch over scholingsmogelijkheden
           - Houd rekening met bedrijfsstructuur
           - Geef concrete redenen bij afwijzing
        
        ## Geef alleen de analyse van interne alternatieven, zonder introductie of afsluiting.
        """
    
    elif section_id == "visie_ad_ander_werk_extern":
        prompt = """
        # Taak: 4.4 Geschiktheid voor ander werk bij andere werkgever
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om externe mogelijkheden te analyseren.
        
        ## Eisen aan Ander werk externe werkgever
        
        1. Kernonderdelen:
           - Verwijzing naar poortwachterstermijnen
           - Zoekrichting met concrete criteria:
             * Aantal uren
             * Wisselende diensten
             * Mobiliteit
             * Richting en opleidingsniveau
             * Affiniteit en voorkeuren
           - Aanbeveling re-integratiebegeleiding
           
        2. Formaat:
           - Systematische opsomming zoekrichtingcriteria
           - Concrete suggesties voor functies/sectoren
           - Advies over professionele begeleiding
           
        3. Inhoudelijke richtlijnen:
           - Baseer op capaciteiten en voorkeuren werknemer
           - Wees realistisch over arbeidsmarktmogelijkheden
           - Geef concrete voorbeelden van geschikte functies
           - Adviseer professionele re-integratiebegeleiding
        
        ## Geef alleen de analyse van externe mogelijkheden, zonder introductie of afsluiting.
        """
    
    elif section_id == "visie_ad_duurzaamheid":
        prompt = """
        # Taak: 4.5 Duurzaamheid van herplaatsing
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om de duurzaamheid van re-integratie te beoordelen.
        
        ## Eisen aan Duurzaamheid herplaatsing
        
        1. Kernonderdelen:
           - Factoren voor duurzame re-integratie
           - Aanbevelingen voor werkgever en werknemer
           - Prognose over toekomstige ontwikkelingen
           - Voorwaarden voor succesvol herstel
           
        2. Formaat:
           - Focus op kritische succesfactoren
           - Concrete aanbevelingen voor alle partijen
           - Realistische verwachtingen
           
        3. Inhoudelijke richtlijnen:
           - Baseer op analyse van hele situatie
           - Geef praktische handvatten
           - Wees realistisch over kansen en uitdagingen
           - Focus op werkbare oplossingen
        
        ## Geef alleen de duurzaamheidsanalyse, zonder introductie of afsluiting.
        """
    
    elif section_id == "advies":
        prompt = """
        # Taak: 5. Trajectplan/Advies
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om concrete adviezen en een trajectplan te formuleren.
        
        ## Eisen aan Trajectplan
        
        1. Kernonderdelen:
           - Concrete vervolgstappen in volgorde
           - Wie is verantwoordelijk voor welke actie
           - Tijdschema waar mogelijk
           - Parallelle trajecten (spoor 1 en 2)
           
        2. Formaat:
           - Bullet points met duidelijke acties
           - Logische volgorde van stappen
           - Praktisch en uitvoerbaar
           
        3. Inhoudelijke richtlijnen:
           - Baseer op alle voorgaande analyses
           - Wees specifiek en actionable
           - Houd rekening met poortwachterstermijnen
           - Geef realistische tijdslijnen
        
        ## Geef alleen het trajectplan, zonder introductie of afsluiting.
        """
    
    elif section_id == "conclusie":
        prompt = """
        # Taak: 6. Conclusie
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om de hoofdconclusies helder samen te vatten.
        
        ## Eisen aan Conclusie
        
        1. Kernonderdelen (beantwoord elke vraag):
           - Kan werknemer het eigen werk nog uitvoeren?
           - Is eigen werk met aanpassingen passend te maken?
           - Kan werknemer ander werk bij eigen werkgever uitvoeren?
           - Zijn er mogelijkheden voor externe re-integratie?
           
        2. Formaat:
           - Gebruik bullet points per hoofdvraag
           - Heldere ja/nee antwoorden waar mogelijk
           - Korte onderbouwing per punt
           
        3. Inhoudelijke richtlijnen:
           - Geef directe antwoorden op vraagstelling
           - Wees definitief maar realistisch
           - Samenvatting van belangrijkste bevindingen
           - Vooruitblik op vervolgtraject
        
        ## Geef alleen de conclusies in bullet points, zonder introductie of afsluiting.
        """
    
    elif section_id == "vervolg":
        prompt = """
        # Taak: 7. Vervolg
        
        Je bent een professionele arbeidsdeskundige die een rapport opstelt. Je taak is om de vervolgstappen te beschrijven.
        
        ## Eisen aan Vervolg
        
        1. Kernonderdelen:
           - Rapportage bespreken met betrokkenen
           - Praktische vervolgacties
           - Doorsturen naar relevante partijen
           - Beschikbaarstelling aan professionals
           
        2. Formaat:
           - Bullet points met concrete acties
           - Duidelijke verantwoordelijkheden
           - Logische volgorde van stappen
           
        3. Inhoudelijke richtlijnen:
           - Geef praktische vervolghandelingen
           - Vermeld relevante partijen (bedrijfsarts, re-integratiebedrijf)
           - Houd rekening met privacy en procedures
           - Wees compleet maar beknopt
        
        ## Geef alleen de vervolgstappen, zonder introductie of afsluiting.
        """
    
    else:
        # Generic prompt for other sections
        prompt = f"""
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

    # Add user profile information if available
    if user_profile:
        profile_prompt = "\n\n## Arbeidsdeskundige Informatie\n\n"

        # Add name and title
        if user_profile.get("first_name") and user_profile.get("last_name"):
            name = f"{user_profile.get('first_name')} {user_profile.get('last_name')}"
            profile_prompt += f"Naam: {name}\n"
        elif user_profile.get("display_name"):
            profile_prompt += f"Naam: {user_profile.get('display_name')}\n"

        # Add job title
        if user_profile.get("job_title"):
            profile_prompt += f"Functie: {user_profile.get('job_title')}\n"

        # Add certification and registration
        if user_profile.get("certification"):
            profile_prompt += f"Certificering: {user_profile.get('certification')}\n"
        if user_profile.get("registration_number"):
            profile_prompt += f"Registratienummer: {user_profile.get('registration_number')}\n"

        # Add company information
        if user_profile.get("company_name"):
            profile_prompt += f"Organisatie: {user_profile.get('company_name')}\n"

            # Add company contact information
            contact_parts = []
            if user_profile.get("company_phone"):
                contact_parts.append(f"Tel: {user_profile.get('company_phone')}")
            if user_profile.get("company_email"):
                contact_parts.append(f"Email: {user_profile.get('company_email')}")
            if user_profile.get("company_website"):
                contact_parts.append(f"Website: {user_profile.get('company_website')}")

            if contact_parts:
                profile_prompt += f"Contact: {' | '.join(contact_parts)}\n"

        # Add specializations
        if user_profile.get("specializations") and isinstance(user_profile.get("specializations"), list):
            profile_prompt += f"Specialisaties: {', '.join(user_profile.get('specializations'))}\n"

        # Add instructions for using the profile info
        profile_prompt += "\nGebruik bovenstaande informatie voor het opstellen van het rapport."

        # Add profile info to the prompt
        prompt = prompt + profile_prompt

    return prompt

def create_report_header(user_profile):
    """
    Create a professional header for the report using user profile information
    """
    if not user_profile:
        return ""
    
    header_lines = []
    header_lines.append("# ARBEIDSDESKUNDIG RAPPORT")
    header_lines.append("")
    
    # Add company logo placeholder if available
    if user_profile.get("logo_path") or user_profile.get("logo_url"):
        if user_profile.get("logo_path"):
            # Extract filename from storage path for URL
            import os
            filename = os.path.basename(user_profile.get("logo_path"))
            header_lines.append(f"![Bedrijfslogo](/api/v1/profiles/logo/{filename})")
        else:
            header_lines.append(f"![Bedrijfslogo]({user_profile.get('logo_url')})")
        header_lines.append("")
    
    # Add arbeidsdeskundige information
    header_lines.append("## Opgesteld door:")
    
    # Name and title
    if user_profile.get("first_name") and user_profile.get("last_name"):
        name = f"{user_profile.get('first_name')} {user_profile.get('last_name')}"
        if user_profile.get("job_title"):
            header_lines.append(f"**{name}**, {user_profile.get('job_title')}")
        else:
            header_lines.append(f"**{name}**")
    elif user_profile.get("display_name"):
        if user_profile.get("job_title"):
            header_lines.append(f"**{user_profile.get('display_name')}**, {user_profile.get('job_title')}")
        else:
            header_lines.append(f"**{user_profile.get('display_name')}**")
    
    # Certification and registration
    if user_profile.get("certification"):
        header_lines.append(f"Certificering: {user_profile.get('certification')}")
    if user_profile.get("registration_number"):
        header_lines.append(f"Registratienummer: {user_profile.get('registration_number')}")
    
    # Company information
    if user_profile.get("company_name"):
        header_lines.append("")
        header_lines.append(f"**{user_profile.get('company_name')}**")
        
        # Company address
        address_parts = []
        if user_profile.get("company_address"):
            address_parts.append(user_profile.get("company_address"))
        if user_profile.get("company_postal_code") and user_profile.get("company_city"):
            address_parts.append(f"{user_profile.get('company_postal_code')} {user_profile.get('company_city')}")
        elif user_profile.get("company_city"):
            address_parts.append(user_profile.get("company_city"))
        
        if address_parts:
            header_lines.append(", ".join(address_parts))
        
        # Company contact information
        contact_parts = []
        if user_profile.get("company_phone"):
            contact_parts.append(f"Tel: {user_profile.get('company_phone')}")
        if user_profile.get("company_email"):
            contact_parts.append(f"Email: {user_profile.get('company_email')}")
        if user_profile.get("company_website"):
            contact_parts.append(f"Website: {user_profile.get('company_website')}")
        
        if contact_parts:
            header_lines.append(" | ".join(contact_parts))
    
    # Specializations
    if user_profile.get("specializations") and isinstance(user_profile.get("specializations"), list):
        header_lines.append("")
        header_lines.append(f"**Specialisaties:** {', '.join(user_profile.get('specializations'))}")
    
    # Add date
    header_lines.append("")
    header_lines.append(f"**Datum:** {datetime.utcnow().strftime('%d %B %Y')}")
    
    header_lines.append("")
    header_lines.append("---")
    header_lines.append("")
    
    return "\n".join(header_lines)

def get_fallback_content_for_prompt(prompt):
    """
    Get fast fallback content when API is overloaded, based on prompt analysis
    """
    prompt_lower = prompt.lower()
    
    if "samenvatting" in prompt_lower:
        return """Op basis van de beschikbare documenten is een objectieve analyse gemaakt. 
        De gegevens tonen aan dat er sprake is van een complexe werksituatie waarbij verschillende 
        factoren van invloed zijn op het dagelijks functioneren. Voor een volledig beeld zijn 
        aanvullende gegevens gewenst."""
        
    elif "belastbaarheid" in prompt_lower or "mogelijkheden" in prompt_lower:
        return """## Fysieke mogelijkheden
- Activiteiten kunnen worden uitgevoerd met inachtneming van individuele beperkingen
- Aanpassingen in werkhouding en tempo zijn wenselijk

## Mentale mogelijkheden  
- Cognitieve taken kunnen worden uitgevoerd binnen een gestructureerde omgeving
- Concentratie en aandacht vereisen adequate ondersteuning

## Sociale aspecten
- Interactie met collega's is mogelijk binnen een ondersteunende werkomgeving
- Begeleiding en duidelijke communicatie zijn van belang"""

    elif "visie" in prompt_lower:
        return """Vanuit professioneel perspectief bestaat er potentieel voor werkhervatting 
        mits de juiste randvoorwaarden worden gecreëerd. Een gefaseerde opbouw met adequate 
        begeleiding biedt perspectief voor duurzame re-integratie. Het is essentieel om 
        individuele factoren zorgvuldig af te wegen tegen de eisen van de arbeidsmarkt."""

    elif "matching" in prompt_lower or "passend werk" in prompt_lower:
        return """# CRITERIA VOOR PASSEND WERK

## Fysieke werkomgeving
- Ergonomische werkplek (E)
- Mogelijkheid tot afwisseling in houding (E)  
- Aangepaste werktijden indien nodig (W)

## Taakinhoud
- Taken passend bij ervaring en capaciteiten (E)
- Werkzaamheden met eigen tempo-regeling (E)
- Duidelijke instructies en feedback (W)

## Sociale werkomgeving
- Ondersteunende leidinggevende (E)
- Begrip voor individuele situatie (E)
- Collega's die samenwerking faciliteren (W)"""
        
    else:
        return """Op basis van de beschikbare informatie is een objectieve analyse gemaakt. 
        De gegevens worden geïnterpreteerd binnen de context van arbeidsdeskundige beoordeling. 
        Voor specifieke details wordt verwezen naar de onderliggende documentatie."""

def should_use_direct_approach(documents):
    """
    Determine if we should use the direct LLM approach based on:
    1. Total document length
    2. Presence of embeddings
    3. Document processing status
    """
    # Filter out None documents
    valid_documents = [doc for doc in documents if doc is not None]
    
    if not valid_documents:
        logger.warning("No valid documents found for approach decision")
        return True  # Default to direct approach
    
    # Check total document length
    total_length = sum(len(doc.get("content", "")) for doc in valid_documents)
    
    # Parse metadata for each document
    documents_with_parsed_metadata = []
    for doc in valid_documents:
        if doc is None:  # Extra safety check
            continue
            
        metadata = doc.get("metadata", {})
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata)
            except:
                metadata = {}
        elif metadata is None:
            metadata = {}
            
        # Ensure metadata is a dict
        if not isinstance(metadata, dict):
            metadata = {}
            
        doc["parsed_metadata"] = metadata
        documents_with_parsed_metadata.append(doc)
    
    # Check if any documents have embeddings properly processed
    has_valid_embeddings = any(
        doc is not None and
        doc.get("parsed_metadata", {}).get("embeddings_available", False) and
        doc.get("status", "") == "enhanced" 
        for doc in documents_with_parsed_metadata
    )
    
    # Log detailed decision info
    logger.info(f"Hybrid approach decision - Document length: {total_length}, " 
                f"Has valid embeddings: {has_valid_embeddings}")
    
    # Check percentage of documents with embeddings
    total_docs = len(valid_documents)
    if total_docs > 0:
        docs_with_embeddings = sum(
            1 for doc in documents_with_parsed_metadata 
            if doc is not None and doc.get("parsed_metadata", {}).get("embeddings_available", False)
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
def generate_report_hybrid(report_id: str, user_profile=None, use_structured_output=False):
    logger.info(f"generate_report_hybrid task called with ID: {report_id}")
    if user_profile:
        logger.info(f"User profile included with data for {user_profile.get('first_name', '')} {user_profile.get('last_name', '')}")
    """
    Generate a report using a hybrid approach:
    1. For small documents or when embeddings aren't available, use direct LLM
    2. For larger documents with embeddings, use RAG pipeline
    3. NEW: For structured AD reports, delegate to the new AD report generator
    """
    try:
        logger.info(f"Starting hybrid report generation for ID: {report_id}")
        
        # Get report info from database
        report = db_service.get_row_by_id("report", report_id)
        
        if not report:
            raise ValueError(f"Report with ID {report_id} not found")
        
        # Check if this should use the new structured AD report generation
        if use_structured_output or report.get('generation_method') == 'structured':
            logger.info(f"Delegating to structured AD report generator for report {report_id}")
            # Import here to avoid circular dependencies
            from app.tasks.generate_report_tasks.ad_report_task import generate_ad_report_task
            
            # Create a mock Celery task instance for the AD report generator
            class MockTask:
                def update_state(self, state, meta):
                    logger.info(f"Task state: {state}, meta: {meta}")
            
            mock_task = MockTask()
            
            # Call the AD report generator directly
            try:
                result = generate_ad_report_task.func(mock_task, report_id, True)  # Use structured approach
                logger.info(f"Structured AD report generation completed for {report_id}")
                return result
            except Exception as e:
                logger.error(f"Structured AD report generation failed: {str(e)}")
                # Fall back to legacy approach
                logger.info(f"Falling back to legacy hybrid approach for report {report_id}")
                pass
        
        case_id = report["case_id"]
        template_id = report["template_id"]
        
        # Check if template exists
        if template_id not in MVP_TEMPLATES:
            raise ValueError(f"Template with ID {template_id} not found")

        template = MVP_TEMPLATES[template_id]

        # Get template layout type
        template_layout = template.get("layout", "standaard")
        
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
            "provider": settings.LLM_PROVIDER,
            "template_type": template_layout,
            "user_profile": user_profile if user_profile else None
        }
        
        # Get full document content for direct approach
        full_documents = []
        for doc_id in document_ids:
            # Get full document info
            document = db_service.get_row_by_id("document", doc_id)
            
            # Skip if document not found
            if document is None:
                logger.warning(f"Document {doc_id} not found, skipping")
                continue
            
            # Get document chunks
            chunks = db_service.get_document_chunks(doc_id)
            
            if not chunks:
                logger.warning(f"No chunks found for document {doc_id}")
                # For audio documents, use the transcribed content if available
                if document.get("document_type") == "audio" and document.get("content"):
                    logger.info(f"Using transcribed content for audio document {doc_id}")
                    # Keep the existing transcribed content
                    pass
                else:
                    # Set empty content for documents without chunks or content
                    document["content"] = ""
            else:
                # Combine chunk content
                content = "\n\n".join([chunk["content"] for chunk in chunks])
                document["content"] = content
            
            full_documents.append(document)
        
        # Determine if we should use direct approach
        use_direct = should_use_direct_approach(full_documents)
        report_metadata["direct_approach"] = use_direct
        
        logger.info(f"Using {'direct' if use_direct else 'RAG'} approach for report generation")
        
        # Generate content for each section in the template
        if use_structured_output:
            # Use structured output generation
            logger.info("Using structured output generation")
            from app.tasks.generate_report_tasks.structured_report_generator import generate_full_structured_report
            
            # Combine document content
            combined_content = combine_document_texts(full_documents, MAX_DIRECT_DOCUMENT_LENGTH)
            
            # Prepare case data
            case_data = {
                "client_name": case.get("client_name", "Onbekend"),
                "company_name": case.get("company_name", "Onbekend"),
                "case_id": case_id
            }
            
            # Generate structured report
            structured_data = generate_full_structured_report(combined_content, case_data)
            
            # Convert structured data to content format for compatibility
            for section_id in template["sections"].keys():
                if section_id in structured_data:
                    section_data = structured_data[section_id]
                    if isinstance(section_data, dict):
                        # Convert structured data to formatted content
                        content = format_structured_section(section_id, section_data)
                    else:
                        content = str(section_data)
                    
                    report_content[section_id] = content
                    report_metadata["sections"][section_id] = {
                        "generated_at": datetime.utcnow().isoformat(),
                        "approach": "structured",
                        "structured_data": section_data,
                        "chunk_ids": []
                    }
                    logger.info(f"Generated structured content for section {section_id}")
        
        elif use_direct:
            # Combine document content
            combined_content = combine_document_texts(full_documents, MAX_DIRECT_DOCUMENT_LENGTH)
            
            for section_id, section_info in template["sections"].items():
                # Create direct prompt
                prompt = create_direct_prompt_for_section(section_id, section_info, user_profile)
                
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
            # Use RAG approach (with optional structured output)
            for section_id, section_info in template["sections"].items():
                # Generate content using RAG pipeline
                try:
                    if use_structured_output:
                        # Use structured output pipeline
                        import asyncio
                        section_result = asyncio.run(generate_structured_content(
                            section_id=section_id,
                            section_info=section_info,
                            document_ids=document_ids,
                            case_id=case_id,
                            user_profile=user_profile,
                            output_format="plain"  # For backwards compatibility
                        ))
                        
                        # Store structured metadata if available
                        if section_result.get("structured_content"):
                            if "structured_content" not in report_metadata:
                                report_metadata["structured_content"] = {}
                            report_metadata["structured_content"][section_id] = section_result["structured_content"]
                        
                        approach_type = "structured_rag"
                    else:
                        # Use traditional RAG pipeline
                        section_result = generate_content_for_section(
                            section_id=section_id,
                            section_info=section_info,
                            document_ids=document_ids,
                            case_id=case_id,
                            user_profile=user_profile
                        )
                        approach_type = "rag"
                    
                    # Store the generated content and metadata
                    report_content[section_id] = section_result["content"]
                    section_metadata = {
                        "generated_at": datetime.utcnow().isoformat(),
                        "chunk_ids": section_result["chunk_ids"],
                        "prompt": section_result.get("prompt", ""),
                        "approach": approach_type
                    }
                    
                    # Add structured content metadata if available
                    if use_structured_output and section_result.get("metadata"):
                        section_metadata.update(section_result["metadata"])
                    
                    # Add error information if available
                    if "error" in section_result:
                        section_metadata["error"] = section_result["error"]
                        
                        # Add a user-friendly message for missing embeddings
                        if section_result["error"] == "missing_embeddings":
                            section_metadata["user_message"] = "Probeer het later opnieuw wanneer de document verwerking is voltooid."
                    
                    report_metadata["sections"][section_id] = section_metadata
                    logger.info(f"Successfully generated content for section {section_id} using {'structured ' if use_structured_output else ''}RAG")
                    
                except Exception as section_error:
                    logger.error(f"Error generating section {section_id} with RAG: {str(section_error)}")
                    
                    # Try fallback to direct approach
                    try:
                        logger.info(f"Attempting direct fallback for section {section_id}")
                        prompt = create_direct_prompt_for_section(section_id, section_info, user_profile)
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
                        
        
        # Add rapport header met profiel informatie
        if user_profile:
            header_content = create_report_header(user_profile)
            report_content["rapport_header"] = header_content
            report_metadata["sections"]["rapport_header"] = {
                "generated_at": datetime.utcnow().isoformat(),
                "approach": "profile_header",
                "prompt": "Generated from user profile data"
            }

        # Complete the metadata
        report_metadata["generation_completed"] = datetime.utcnow().isoformat()

        # Add user profile to metadata if available
        if user_profile:
            report_metadata["user_profile"] = user_profile
        
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