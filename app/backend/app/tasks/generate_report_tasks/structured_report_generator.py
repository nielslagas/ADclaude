"""
Structured report generator using Pydantic models for consistent JSON output.
This approach ensures professional formatting and table structure.
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.utils.llm_provider import create_llm_instance
from app.models.report_structure import (
    StructuredReport, 
    GegevensWerkgever, 
    GegevensWerknemer,
    Belastbaarheid,
    EigenFunctie,
    Conclusie
)
from app.utils.ad_report_template import get_ad_template_prompt

logger = logging.getLogger(__name__)

def generate_structured_section(section_type: str, context: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a structured section using LLM with Pydantic model constraints.
    
    Args:
        section_type: Type of section to generate (e.g., 'gegevens_werkgever')
        context: Document context for the LLM
        case_data: Additional case information
        
    Returns:
        Structured section data as dict
    """
    
    # Define structured prompts for each section
    prompts = {
        "samenvatting": get_samenvatting_prompt(),
        "vraagstelling": get_vraagstelling_prompt(),
        "ondernomen_activiteiten": get_activiteiten_prompt(),
        "voorgeschiedenis": get_voorgeschiedenis_prompt(),
        "gegevens_werkgever": get_werkgever_prompt(),
        "gegevens_werknemer": get_werknemer_prompt(),
        "belastbaarheid": get_belastbaarheid_prompt(),
        "eigen_functie": get_functie_prompt(),
        "geschiktheid_analyse": get_geschiktheid_prompt(),
        "conclusie": get_conclusie_prompt(),
        "trajectplan": get_trajectplan_prompt(),
        "vervolg": get_vervolg_prompt()
    }
    
    if section_type not in prompts:
        logger.error(f"Unknown section type: {section_type}")
        return {}
        
    # Get the section-specific prompt
    section_prompt = prompts[section_type]
    
    # Get Vector template instruction
    template_instruction = get_ad_template_prompt(section_type)
    
    # Create full prompt with Vector template format
    full_prompt = f"""
    ## VECTOR TEMPLATE INSTRUCTIES:
    {template_instruction}
    
    ## SECTIE SPECIFIEKE PROMPT:
    {section_prompt}
    
    ## Context Documenten:
    {context}
    
    ## Case Informatie:
    - Client: {case_data.get('client_name', 'Onbekend')}
    - Werkgever: {case_data.get('company_name', 'Onbekend')}
    - Datum: {datetime.now().strftime('%d-%m-%Y')}
    
    ## BELANGRIJKE INSTRUCTIES:
    - Gebruik EXACT het Vector format zoals gespecificeerd in het template
    - Gebruik de markdown formatting, tabel structures, en nummering van het voorbeeld
    - Genereer professionele Nederlandse AD rapport content
    - Baseer alle content op de aangeleverde documenten over Pieter Janssen
    - Gebruik de exacte structuur en format van het Vector voorbeeld
    - Bij ontbrekende informatie: gebruik "Informatie niet beschikbaar in documenten"
    
    Genereer de sectie in perfect Vector format!
    """
    
    try:
        # Create LLM instance with structured output settings
        model = create_llm_instance(
            temperature=0.1,  # Low temperature for consistency
            max_tokens=4000,
            response_format="json_object"  # Force JSON output
        )
        
        # Generate structured content
        response = model.generate_content([
            {
                "role": "system", 
                "parts": ["Je bent een professionele arbeidsdeskundige die gestructureerde JSON rapportages maakt. Je output moet altijd geldige JSON zijn."]
            },
            {
                "role": "user", 
                "parts": [full_prompt]
            }
        ])
        
        if not response.text:
            logger.error(f"Empty response for section {section_type}")
            return get_fallback_section(section_type)
            
        # Parse JSON response
        try:
            structured_data = json.loads(response.text)
            logger.info(f"Successfully generated structured section: {section_type}")
            return structured_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in response for section {section_type}: {e}")
            logger.error(f"Response text: {response.text[:500]}...")
            return get_fallback_section(section_type)
            
    except Exception as e:
        logger.error(f"Error generating structured section {section_type}: {str(e)}")
        return get_fallback_section(section_type)

def get_werkgever_prompt() -> str:
    """Prompt for structured employer information"""
    return """
    Genereer JSON voor de sectie "Gegevens werkgever" met exact deze structuur:
    
    {
        "aard_bedrijf": "Beschrijving van bedrijfsactiviteiten en sector",
        "omvang_bedrijf": "Aantal locaties, grootte bedrijf", 
        "aantal_werknemers": "Aantal werknemers in dienst",
        "functies_expertises": "Beschikbare functies en expertises binnen organisatie",
        "overige_informatie": "Website, contactgegevens, aanvullende informatie"
    }
    
    Vul elk veld in op basis van de documenten. Gebruik "Informatie niet beschikbaar" als gegevens ontbreken.
    """

def get_werknemer_prompt() -> str:
    """Prompt for structured employee information"""
    return """
    Genereer JSON voor de sectie "Gegevens werknemer" met exact deze structuur:
    
    {
        "opleidingen": [
            {
                "opleiding": "Naam opleiding/cursus",
                "richting": "Studierichting", 
                "diploma": "Diploma/certificaat",
                "jaar": "Jaar afronding"
            }
        ],
        "arbeidsverleden": [
            {
                "periode": "Van/tot jaartal",
                "werkgever": "Naam werkgever",
                "functie": "Functietitel"
            }
        ],
        "bekwaamheden": {
            "computervaardigheden": "Niveau computervaardigheden",
            "taalvaardigheid": "Nederlandse/andere talen",
            "rijbewijs": "Rijbewijs categorie en beperkingen",
            "overige": "Andere relevante vaardigheden"
        }
    }
    """

def get_belastbaarheid_prompt() -> str:
    """Prompt for structured functional capacity assessment"""  
    return """
    Genereer JSON voor de sectie "Belastbaarheid van werknemer" met exact deze structuur:
    
    {
        "datum_beoordeling": "Datum van FML beoordeling",
        "beoordelaar": "Naam bedrijfsarts/beoordelaar",
        "beperkingen": [
            {
                "rubriek": "Rubriek I: Persoonlijk functioneren",
                "aspecten": [
                    "Specifieke beperking 1",
                    "Specifieke beperking 2"
                ],
                "mate_beperking": "Niet beperkt/Beperkt/Sterk beperkt"
            }
        ],
        "prognose": "Verwachting over ontwikkeling belastbaarheid"
    }
    
    Analyseer de FML informatie en vul de structuur systematisch in.
    """

def get_functie_prompt() -> str:
    """Prompt for structured job analysis"""
    return """
    Genereer JSON voor de sectie "Eigen functie werknemer" met exact deze structuur:
    
    {
        "functie_gegevens": {
            "naam_functie": "Functietitel",
            "arbeidspatroon": "Werkpatroon (dagvenster/wisselend)",
            "overeenkomst": "Type contract (vast/tijdelijk)",
            "aantal_uren": "Aantal uur per week",
            "salaris": "Salarisinformatie (indien beschikbaar)"
        },
        "functieomschrijving": "Uitgebreide beschrijving van functie-inhoud en verantwoordelijkheden",
        "functiebelasting": [
            {
                "taak": "Beschrijving van taak",
                "percentage": "Percentage tijd besteed",
                "belastende_aspecten": "Wat maakt deze taak belastend"
            }
        ]
    }
    """

def get_geschiktheid_prompt() -> str:
    """Prompt for suitability analysis"""
    return """
    Genereer JSON voor geschiktheidsanalyse met deze structuur:
    
    {
        "analyses": [
            {
                "belastend_aspect": "Wat maakt het werk belastend",
                "belastbaarheid_werknemer": "Wat kan de werknemer aan", 
                "match_niveau": "Voldoende/Onvoldoende/Gedeeltelijk"
            }
        ]
    }
    
    Vergelijk systematisch functie-eisen met belastbaarheid.
    """

def get_conclusie_prompt() -> str:
    """Prompt for structured conclusions"""
    return """
    Genereer JSON voor conclusies met exact deze structuur:
    
    {
        "eigen_werk": "Kan werknemer eigen werk nog uitvoeren? (Ja/Nee/Gedeeltelijk)",
        "eigen_werk_aanpassingen": "Is eigen werk met aanpassingen mogelijk? (Ja/Nee + toelichting)",
        "ander_werk_intern": "Mogelijk ander werk bij huidige werkgever? (Ja/Nee + toelichting)",
        "extern_werk": "Mogelijkheden externe re-integratie? (Ja/Nee + toelichting)"
    }
    
    Beantwoord elke vraag helder en onderbouwd.
    """

def get_samenvatting_prompt() -> str:
    """Prompt for executive summary"""
    return """
    Genereer JSON voor samenvatting met deze structuur:
    
    {
        "vraagstelling": "Kernvraag van het onderzoek",
        "conclusie": "Hoofdconclusie in 2-3 zinnen"
    }
    """

def get_vraagstelling_prompt() -> str:
    """Prompt for research questions"""
    return """
    Genereer JSON voor vraagstelling:
    
    {
        "hoofdvraag": "Centrale onderzoeksvraag",
        "deelvragen": [
            "Kan werknemer het eigen werk nog uitvoeren?",
            "Is het eigen werk met aanpassingen passend te maken?", 
            "Kan werknemer ander werk bij eigen werkgever uitvoeren?",
            "Zijn er mogelijkheden voor externe re-integratie?"
        ]
    }
    """

def get_activiteiten_prompt() -> str:
    """Prompt for undertaken activities"""
    return """
    Genereer JSON voor ondernomen activiteiten:
    
    {
        "activiteiten": [
            "Dossieronderzoek en documentenanalyse",
            "Gesprek met werknemer", 
            "Gesprek met werkgever",
            "Werkplekonderzoek (indien van toepassing)",
            "Overleg met behandelaars (indien van toepassing)"
        ]
    }
    
    Vermeld alleen activiteiten die daadwerkelijk zijn ondernomen op basis van de documenten.
    """

def get_voorgeschiedenis_prompt() -> str:
    """Prompt for background information"""
    return """
    Genereer JSON voor voorgeschiedenis:
    
    {
        "dienstverband": "Informatie over huidige dienstverband",
        "verzuim_historie": "Overzicht verzuimperiode en oorzaken", 
        "medische_behandeling": "Huidige behandeling en begeleiding",
        "eerdere_interventies": "Eerdere re-integratiepogingen"
    }
    """

def get_trajectplan_prompt() -> str:
    """Prompt for action plan"""
    return """
    Genereer JSON voor trajectplan:
    
    {
        "spoor_1": [
            {
                "actie": "Te ondernemen actie",
                "verantwoordelijke": "Wie is verantwoordelijk", 
                "termijn": "Binnen welke termijn"
            }
        ],
        "spoor_2": [
            {
                "actie": "Re-integratie externe markt actie",
                "verantwoordelijke": "Verantwoordelijke partij",
                "termijn": "Tijdsframe"
            }
        ]
    }
    """

def get_vervolg_prompt() -> str:
    """Prompt for follow-up steps"""
    return """
    Genereer JSON voor vervolgstappen:
    
    {
        "acties": [
            "Rapport bespreken met betrokkenen",
            "Implementeren aanbevelingen", 
            "Planning evaluatiemoment",
            "Monitoring voortgang"
        ]
    }
    """

def get_fallback_section(section_type: str) -> Dict[str, Any]:
    """Provide fallback structured data when generation fails"""
    fallbacks = {
        "gegevens_werkgever": {
            "aard_bedrijf": "Informatie niet beschikbaar in documenten",
            "omvang_bedrijf": "Informatie niet beschikbaar in documenten",
            "aantal_werknemers": "Informatie niet beschikbaar in documenten", 
            "functies_expertises": "Informatie niet beschikbaar in documenten",
            "overige_informatie": "Informatie niet beschikbaar in documenten"
        },
        "conclusie": {
            "eigen_werk": "Beoordeling volgt na analyse documenten",
            "eigen_werk_aanpassingen": "Te onderzoeken",
            "ander_werk_intern": "Te onderzoeken", 
            "extern_werk": "Te onderzoeken"
        }
    }
    
    return fallbacks.get(section_type, {"error": "Sectie kon niet worden gegenereerd"})

def generate_full_structured_report(context: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate complete structured report using all sections.
    
    Returns:
        Complete report as structured dictionary
    """
    logger.info("Starting structured report generation")
    
    report_data = {
        "titel": "Arbeidsdeskundig rapport",
        "werknemer_naam": case_data.get('client_name', 'Onbekend'),
        "werkgever_naam": case_data.get('company_name', 'Onbekend'),
        "datum_onderzoek": datetime.now().strftime('%d-%m-%Y'),
        "datum_rapportage": datetime.now().strftime('%d-%m-%Y')
    }
    
    # Generate each section
    sections = [
        "samenvatting", "vraagstelling", "ondernomen_activiteiten", 
        "voorgeschiedenis", "gegevens_werkgever", "gegevens_werknemer",
        "belastbaarheid", "eigen_functie", "geschiktheid_analyse", 
        "conclusie", "trajectplan", "vervolg"
    ]
    
    for section in sections:
        try:
            logger.info(f"Generating section: {section}")
            section_data = generate_structured_section(section, context, case_data)
            report_data[section] = section_data
            
        except Exception as e:
            logger.error(f"Failed to generate section {section}: {str(e)}")
            report_data[section] = get_fallback_section(section)
    
    logger.info("Structured report generation completed")
    return report_data