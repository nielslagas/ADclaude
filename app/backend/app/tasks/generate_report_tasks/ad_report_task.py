"""
Enhanced AD Report Generation Task
Based on comprehensive analysis of professional AD reports

This module implements specialized report generation for Arbeidsdeskundig reports
incorporating the findings from professional report analysis.

Key features:
1. Uses enhanced AD template structure
2. Implements FML rubriek generation
3. Follows standardized 4-question approach
4. Ensures professional quality standards
"""

import logging
import time
from datetime import datetime
from uuid import UUID
from typing import Dict, Any, List
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from collections import OrderedDict

from app.celery_worker import celery
from app.db.database_service import get_database_service
from app.utils.ad_report_template import (
    get_enhanced_ad_template, 
    get_fml_rubrieken_detailed,
    get_standard_questions,
    validate_ad_report_completeness
)

# Configure logger for this module
logger = logging.getLogger(__name__)

def format_fml_context_for_prompt(fml_context: dict) -> str:
    """
    Format FML context dictionary into readable text for the LLM prompt
    
    Args:
        fml_context: Dictionary containing FML rubrieken data
        
    Returns:
        Formatted text with selective FML guidance
    """
    if not fml_context or "rubrieken" not in fml_context:
        return ""
    
    formatted_text = "\n\nSELECTIEVE FML-BENADERING (zoals in professionele praktijk):\n"
    
    for rubriek in fml_context["rubrieken"]:
        formatted_text += f"\nRUBRIEK {rubriek['rubriek']}: {rubriek['naam']}\n"
        
        # Show common relevant items if available
        if "veel_voorkomende_items" in rubriek:
            formatted_text += "  Veel voorkomende relevante items:\n"
            for item in rubriek["veel_voorkomende_items"]:
                formatted_text += f"  • {item}\n"
        
        # Add classification examples if available
        if "classificatie_voorbeelden" in rubriek:
            formatted_text += "  Classificatie voorbeelden:\n"
            for item_nr, description in rubriek["classificatie_voorbeelden"].items():
                formatted_text += f"    {item_nr}. {description}\n"
                
        formatted_text += "\n"
    
    formatted_text += """
INSTRUCTIE: Selecteer alleen items die RELEVANT zijn voor deze specifieke casus.
Analyseer niet alle items, maar focus op daadwerkelijke beperkingen.
Gebruik classificaties: normaal/beperkt/sterk beperkt met concrete onderbouwing.
"""
    
    return formatted_text
from app.core.config import settings

# Initialize services
db_service = get_database_service()

# Try to import RAG pipeline for content generation
try:
    from app.tasks.generate_report_tasks.rag_pipeline import generate_content_for_section
    HAS_RAG = True
except Exception as e:
    logger.warning(f"RAG pipeline import failed, will use fallback approach. Error: {str(e)}")
    HAS_RAG = False

def create_ad_specific_prompt(section_id: str, section_info: dict, user_profile: dict = None, fml_context: dict = None) -> str:
    """
    Create AD-specific prompts based on professional report analysis
    
    Args:
        section_id: The section being generated
        section_info: Section metadata from template
        user_profile: User profile information
        fml_context: FML rubrieken context if applicable
        
    Returns:
        Specialized prompt for AD report section
    """
    
    # Get report base date for reference
    current_date = datetime.utcnow().strftime("%d-%m-%Y")
    
    # Base professional prompt
    base_prompt = f"""Je bent een gecertificeerd arbeidsdeskundige (CRA - Certified Registered Occupational Expert) die een professioneel arbeidsdeskundig rapport opstelt volgens Nederlandse AD-standaarden en de richtlijnen van het Nederlands Register Arbeidsdeskundigen (NRA).

DATUM RICHTLIJNEN:
- Rapportdatum: {current_date}
- Gebruik REALISTISCHE, VERSCHILLENDE datums voor verschillende activiteiten
- Gesprek werknemer: bijvoorbeeld 2-3 dagen voor rapportdatum
- Gesprek werkgever: bijvoorbeeld 1 week voor rapportdatum  
- Documentonderzoek: enkele dagen eerder
- Zorg voor logische chronologie van activiteiten

Schrijf de sectie '{section_info.get('title', section_id)}' conform professionele arbeidsdeskundige rapportage eisen volgens de Wet Verbetering Poortwachter (WVP), WIA en UWV-procedures.

FUNDAMENTELE PROFESSIONELE EISEN:
- Gebruik uitsluitend objectieve, feitelijke en meetbare taal
- Volg de officiële Nederlandse arbeidsdeskundige terminologie en classificaties
- Onderbouw alle conclusies met concrete, verifieerbare gegevens
- Refereer naar relevante wetgeving: WVP, WIA, Wajong, en UWV-procedures
- Gebruik professionele beoordelingscriteria: "geschikt", "ongeschikt", "beperkt geschikt"
- Implementeer het matching-principe: confrontatie belastbaarheid vs. belasting
- Volg de gestandaardiseerde FML-classificaties en beperkingsniveaus
- Gebruik kwantitatieve parameters waar mogelijk (tijden, gewichten, frequenties)

PROFESSIONELE TAAL EN TERMINOLOGIE:
- "Betrokkene" of "werknemer" (niet "persoon" of "individu")  
- "Belastbaarheid" en "belasting" (niet "capaciteit" en "eisen")
- "Functionele mogelijkheden" (niet "vaardigheden")
- "Re-integratie" (niet "terugkeer naar werk")
- "Geschikt/ongeschikt" (niet "kan wel/kan niet")
- "Arbeidsdeskundig onderzoek" (niet "assessment" of "beoordeling")
- "Passende arbeid" (niet "geschikt werk")

VERPLICHTE REFERENTIES:
- Wet Verbetering Poortwachter (WVP) procedures
- Work and Income Act (WIA) criteria  
- Functionele Mogelijkheden Lijst (FML) klassificaties
- UWV re-integratie protocollen
- Nederlandse Register Arbeidsdeskundigen (NRA) standaarden
"""

    # Add section-specific instructions based on analysis findings
    if section_id == "vraagstelling":
        section_prompt = """
SPECIFIEKE INSTRUCTIES VOOR VRAAGSTELLING:
- Gebruik het gestandaardiseerde 4-vragen protocol:
  1.1 Geschiktheid voor eigen functie bij eigen werkgever
  1.2 Geschiktheid na aanpassing functie/werkplek  
  1.3 Geschiktheid voor andere functies bij eigen werkgever
  1.4 Geschiktheid voor andere functies bij andere werkgever
- Formuleer vragen helder en specifiek
- Verwijs naar de concrete situatie van betrokkene
"""
    
    elif section_id == "belastbaarheid":
        section_prompt = f"""
SPECIFIEKE INSTRUCTIES VOOR BELASTBAARHEID/FML:
- Analyseer SELECTIEF en DOELGERICHT alleen relevante FML-items op basis van:
  * Medische diagnose en gerapporteerde klachten
  * Functie-eisen van de eigen werkplek  
  * Daadwerkelijk beperkende factoren
- Focus op 5-15 specifieke items die RELEVANT zijn voor deze casus
- Vermijd volledige inventarisatie van alle FML-items (zoals in professionele praktijk)

SELECTIEVE RUBRIEK-ANALYSE (volg professionele AD-praktijk):
- Rubriek I (Persoonlijk): alleen bij cognitieve klachten (concentratie, geheugen, tempo)
- Rubriek II (Sociaal): alleen bij psychische/sociale problematiek
- Rubriek III (Communicatie): alleen bij sensorische beperkingen (zien, horen, spreken)
- Rubriek IV (Dynamisch): voor fysieke beperkingen (tillen, bukken, lopen, reiken)
- Rubriek V (Statisch): voor houdings-gerelateerde klachten (zitten, staan)  
- Rubriek VI (Handvaardigheid): voor hand/arm problematiek (grijpen, fijne motoriek)

- Gebruik professionele classificatie: "normaal", "beperkt", "sterk beperkt"
- Geef kwantitatieve parameters (tijden, gewichten, afstanden)
- Onderbouw met medische/functionele argumentatie

VOORBEELD PROFESSIONELE FORMULERING (VOLLEDIG UITGEWERKT):
"Op basis van de gerapporteerde lumbale hernia worden de volgende FML-beperkingen geconstateerd:

Rubriek IV: Dynamische handelingen
- 34. Tillen of dragen: BEPERKT tot maximaal 10 kg
  Toelichting: Vanwege lumbale problematiek is tillen beperkt. Regelmatige belasting boven 10 kg leidt tot pijntoename.
- 25. Bukken: STERK BEPERKT 
  Toelichting: Vooroverbuigende bewegingen maximaal 5 minuten per keer vanwege rugklachten.

Rubriek V: Statische houdingen  
- 37. Zitten: BEPERKT tot maximaal 60 minuten aaneengesloten
  Toelichting: Langdurig zitten verergert lumbale klachten. Regelmatige houding-wisselingen noodzakelijk."

VERBODEN: "Wordt beoordeeld", "Niet beperkt" zonder onderbouwing
VEREIST: Concrete FML-items met classificatie + medische onderbouwing

{format_fml_context_for_prompt(fml_context) if fml_context else ''}
"""
    
    elif "gesprek" in section_id:
        section_prompt = """
SPECIFIEKE INSTRUCTIES VOOR GESPREKVERSLAGEN:
- Datum gesprek: [Kies realistische datum binnen 2 weken voor rapportdatum]
- Locatie: [Specifieke, realistische locatie - werkplek, kantoor, etc.]
- Aanwezigen: [Concrete namen en functies van alle aanwezigen]
- Structureer volgens vaste onderwerpen
- Geef visie van betrokkene(n) weer
- Onderscheid feiten van meningen
- Gebruik indirecte rede voor weergegeven standpunten
- Vermeld relevante citaten waar passend
- Zorg voor professionele, gedetailleerde gespreksverslaglegging
"""
    
    elif "visie_ad" in section_id:
        section_prompt = """
SPECIFIEKE INSTRUCTIES VOOR ARBEIDSDESKUNDIGE VISIE:
- Voer systematische confrontatie uit tussen belastbaarheid en belasting (matching principe)
- Analyseer per FML rubriek de discrepanties tussen capaciteit en functie-eisen
- Identificeer concrete knelpunten met specifieke voorbeelden uit de functie
- Geef onderbouwde geschiktheidsconclusie per arbeidsdeskundig criterium
- Gebruik professionele terminologie: "geschikt", "ongeschikt", "beperkt geschikt", "tijdelijk geschikt"
- Onderbouw conclusies met:
  * Concrete FML bevindingen (verwijs naar specifieke rubrieken en items)
  * Medische informatie van behandelend arts/bedrijfsarts
  * Functionele observaties tijdens onderzoek
  * Werkplekanalyse bevindingen

VOORBEELD PROFESSIONELE ANALYSE:
"Uit de confrontatie van de belastbaarheid (FML rubriek IV.14: tillen beperkt tot 10 kg) met de belasting van de eigen functie (regelmatig tillen tot 20 kg vereist) blijkt een overschrijding van 100%. Deze overschrijding maakt duurzame inzet in de huidige functie zonder aanpassingen onmogelijk."

- Formuleer heldere, meetbare conclusies
- Vermijd vage termen zoals "mogelijk" of "waarschijnlijk"
- Geef concrete aanbevelingen voor aanpassingen waar mogelijk
"""
    
    elif section_id == "conclusie":
        section_prompt = """
SPECIFIEKE INSTRUCTIES VOOR CONCLUSIES:
Beantwoord systematisch alle 4 gestandaardiseerde arbeidsdeskundige hoofdvragen:

VRAAG 1.1: "Is betrokkene geschikt voor zijn eigen functie bij eigen werkgever?"
- Geef helder JA of NEE antwoord
- Onderbouw met specifieke FML bevindingen
- Verwijs naar concrete functie-eisen die wel/niet haalbaar zijn
- Bij NEE: specificeer welke aspecten van de functie niet uitvoerbaar zijn

VRAAG 1.2: "Zo nee, is betrokkene geschikt voor zijn eigen functie bij eigen werkgever na aanpassing van zijn functie en/of werkplek?"
- Geef helder JA of NEE antwoord
- Specificeer concrete, haalbare aanpassingen
- Onderbouw duurzaamheid van voorgestelde aanpassingen
- Beoordeel redelijkheid en proportionaliteit aanpassingen voor werkgever

VRAAG 1.3: "Zo nee, is betrokkene geschikt voor andere functies bij eigen werkgever?"
- Geef helder JA of NEE antwoord
- Specificeer welke alternatieve functies geschikt zijn
- Onderbouw met competentie- en capaciteitsanalyse
- Beoordeel beschikbaarheid en toegankelijkheid alternatieve functies

VRAAG 1.4: "Zo nee, is betrokkene geschikt voor andere functies bij andere werkgever?"
- Geef helder JA of NEE antwoord
- Specificeer zoekrichting externe arbeidsmarkt
- Onderbouw met arbeidsmarktanalyse
- Geef realistische prognose re-integratie kansen

AFSLUITING:
- Formuleer samenvattende eindconclusie
- Zorg voor logische samenhang tussen alle antwoorden
- Vermijd tegenstrijdigheden met eerdere bevindingen
- Gebruik objectieve, feitelijke taal zonder waardeoordelen
"""
    
    elif section_id == "vraagstelling":
        section_prompt = """
SPECIFIEKE INSTRUCTIES VOOR VRAAGSTELLING:
- Formuleer de exacte onderzoeksopdracht die opdrachtgever heeft gesteld
- Gebruik de gestandaardiseerde 4-vragen structuur:
  1.1: Geschikt voor eigen functie bij eigen werkgever?
  1.2: Geschikt na aanpassingen functie/werkplek?
  1.3: Geschikt voor andere functies bij eigen werkgever?
  1.4: Geschikt voor functies bij andere werkgever?
- Verwijs naar specifieke arbeidsrechtelijke context (WVP, WIA, UWV)
- Vermeld eventuele aanvullende vragen van opdrachtgever
"""
    
    elif section_id == "gegevensverzameling_werkgever":
        section_prompt = """
SPECIFIEKE INSTRUCTIES VOOR GEGEVENS WERKGEVER:
GENEREER REALISTISCHE BEDRIJFSGEGEVENS en plaats GESTRUCTUREERDE MARKERS:

VEREISTE STRUCTUUR (gebruik deze EXACTE format voor extractie):
werkgever_naam: [Bestaand Nederlands bedrijf]
contactpersoon_werkgever: [Volledige naam Nederlandse contactpersoon]
functie_contactpersoon: [Specifieke functietitel zoals HR Manager, Teamleider]
werkgever_adres: [Complete Nederlandse straatnaam + huisnummer]
werkgever_postcode: [Nederlandse postcode format 1234AB]
werkgever_plaats: [Nederlandse stad/plaats]
werkgever_telefoon: [Nederlands telefoonnummer 010-1234567]
werkgever_email: [professioneel@bedrijf.nl format]
bedrijfstak: [Specifieke sector: verzekeringen, zorg, industrie, etc.]
bedrijfsomvang: [Concreet aantal zoals "150 medewerkers"]

VOORBEELD FORMAT:
werkgever_naam: VerzekeringsMaatschappij Nederland BV
contactpersoon_werkgever: Sandra Jansen
functie_contactpersoon: HR Manager
werkgever_adres: Wilhelmina van Pruisenweg 35
werkgever_postcode: 2595AN
werkgever_plaats: Den Haag

VERBODEN: [Te bepalen], [Bedrijfsadres], placeholders
VEREIST: Complete Nederlandse gegevens met EXACTE field names voor extractie
"""
    
    elif section_id == "gegevensverzameling_werknemer":
        section_prompt = """
SPECIFIEKE INSTRUCTIES VOOR GEGEVENS WERKNEMER:
GENEREER COMPLETE GEGEVENS met GESTRUCTUREERDE MARKERS:

VEREISTE STRUCTUUR (gebruik deze EXACTE field names):
werknemer_naam: [Volledige Nederlandse naam]
geboortedatum: [DD-MM-YYYY format]
werknemer_adres: [Complete straatnaam + huisnummer]
werknemer_postcode: [Nederlandse postcode 1234AB]
werknemer_plaats: [Nederlandse stad]
werknemer_telefoon: [Nederlands telefoonnummer]
werknemer_email: [persoonlijk@email.nl]

OPLEIDINGEN EN ERVARING:
- Opleidingsachtergrond: [Concrete Nederlandse diploma's/certificaten]
- Arbeidsverleden: [10-20 jaar werkervaring met specifieke functies en werkgevers]
- Huidige functie: [Exacte functietitel en belangrijkste taken]
- Dienstverband: [Contracttype, jaren in dienst, uren per week]

VOORBEELD FORMAT:
werknemer_naam: Johannes van der Berg
geboortedatum: 15-03-1978
werknemer_adres: Hoofdstraat 123
werknemer_postcode: 2000AB
werknemer_plaats: Haarlem

VERBODEN: "wordt verzameld", [Woonadres], placeholders
VEREIST: Complete gegevens met EXACTE field names voor extractie
"""
    
    elif section_id == "samenvatting":
        section_prompt = """
SPECIFIEKE INSTRUCTIES VOOR SAMENVATTING:
- Geef beknopt overzicht van de kernvraagstelling
- Vat hoofdconclusies samen per onderzoeksvraag
- Noem belangrijkste beperkingen en mogelijkheden
- Vermeld hoofdlijnen van het advies
- Gebruik duidelijke, bondige formuleringen
- Maximum 1 pagina, focus op essentie
"""
    
    else:
        section_prompt = f"""
SPECIFIEKE INSTRUCTIES:
- {section_info.get('description', 'Standaard professionele rapportage')}
- Volg de professionele standaarden voor deze sectie
- Gebruik objectieve, feitelijke taal
- Onderbouw beweringen met concrete gegevens

GENEREER VOLLEDIGE CONTENT:
- VERBODEN: "wordt verzameld", "wordt geanalyseerd", "wordt bepaald", placeholders
- VEREIST: Concrete, realistische informatie relevant voor Nederlandse AD-praktijk
- Gebruik specifieke details, REALISTISCHE VERSCHILLENDE DATUMS, namen, cijfers waar nodig
- Voor activiteiten: gebruik logische chronologie (documentonderzoek → gesprekken → analyse → rapport)
- Zorg voor professionele, complete rapportage zonder lege velden
"""

    # Add user profile context if available
    if user_profile:
        profile_context = "\n\nARBEIDSDESKUNDIGE GEGEVENS:\n"
        
        if user_profile.get("display_name") or (user_profile.get("first_name") and user_profile.get("last_name")):
            name = user_profile.get("display_name") or f"{user_profile.get('first_name')} {user_profile.get('last_name')}"
            profile_context += f"Naam: {name}\n"
            
        if user_profile.get("certification"):
            profile_context += f"Certificering: {user_profile.get('certification')}\n"
            
        if user_profile.get("registration_number"):
            profile_context += f"Registratienummer: {user_profile.get('registration_number')}\n"
            
        if user_profile.get("company_name"):
            profile_context += f"Organisatie: {user_profile.get('company_name')}\n"
        
        base_prompt += profile_context

    return base_prompt + "\n" + section_prompt


def define_execution_phases(sections_by_order):
    """
    Define 5-phase execution strategy based on dependencies

    Args:
        sections_by_order: List of (section_id, section_info) tuples sorted by order

    Returns:
        List of phase configurations with execution mode and section assignments
    """
    # Convert sections_by_order to a dict for easy lookup
    sections_dict = dict(sections_by_order)

    return [
        {
            'name': 'Setup & Introduction',
            'mode': 'sequential',
            'sections': [
                ('voorblad', sections_dict.get('voorblad')),
                ('inhoudsopgave', sections_dict.get('inhoudsopgave')),
                ('samenvatting', sections_dict.get('samenvatting')),
                ('vraagstelling', sections_dict.get('vraagstelling')),
                ('ondernomen_activiteiten', sections_dict.get('ondernomen_activiteiten'))
            ]
        },
        {
            'name': 'Data Collection',
            'mode': 'parallel',
            'max_workers': 6,
            'sections': [
                ('gegevensverzameling_voorgeschiedenis', sections_dict.get('gegevensverzameling_voorgeschiedenis')),
                ('gegevensverzameling_werkgever', sections_dict.get('gegevensverzameling_werkgever')),
                ('gegevensverzameling_werknemer', sections_dict.get('gegevensverzameling_werknemer')),
                ('gesprek_werkgever', sections_dict.get('gesprek_werkgever')),
                ('gesprek_werknemer', sections_dict.get('gesprek_werknemer')),
                ('gesprek_gezamenlijk', sections_dict.get('gesprek_gezamenlijk'))
            ]
        },
        {
            'name': 'Function Analysis',
            'mode': 'parallel',
            'max_workers': 2,
            'sections': [
                ('belastbaarheid', sections_dict.get('belastbaarheid')),
                ('eigen_functie', sections_dict.get('eigen_functie'))
            ]
        },
        {
            'name': 'AD Vision Analysis',
            'mode': 'parallel',
            'max_workers': 5,
            'sections': [
                ('visie_ad_eigen_werk', sections_dict.get('visie_ad_eigen_werk')),
                ('visie_ad_aanpassing', sections_dict.get('visie_ad_aanpassing')),
                ('visie_ad_ander_werk_eigen', sections_dict.get('visie_ad_ander_werk_eigen')),
                ('visie_ad_ander_werk_extern', sections_dict.get('visie_ad_ander_werk_extern')),
                ('visie_ad_duurzaamheid', sections_dict.get('visie_ad_duurzaamheid'))
            ]
        },
        {
            'name': 'Conclusions',
            'mode': 'sequential',
            'sections': [
                ('advies', sections_dict.get('advies')),
                ('conclusie', sections_dict.get('conclusie')),
                ('vervolg', sections_dict.get('vervolg')),
                ('bijlagen', sections_dict.get('bijlagen'))
            ]
        }
    ]


def execute_sequential(sections, generator, content_dict, metadata_dict, document_ids, case_id):
    """
    Execute sections sequentially

    Args:
        sections: List of (section_id, section_info) tuples
        generator: ADReportSectionGenerator instance
        content_dict: OrderedDict to store results
        metadata_dict: Dict to store metadata
        document_ids: List of document IDs to use
        case_id: ID of the case
    """
    for section_id, section_info in sections:
        if section_info is None:
            continue

        try:
            logger.info(f"Generating section: {section_id}")

            result = generator.generate_section(
                section_id=section_id,
                section_info=section_info,
                document_ids=document_ids,
                case_id=case_id
            )

            # Store results (thread-safe for sequential)
            content_dict[section_id] = result['content']
            metadata_dict['sections'][section_id] = {
                'generated_at': datetime.utcnow().isoformat(),
                'approach': result['approach'],
                'title': result['title'],
                'order': result['order']
            }

            # Track FML generation
            if section_id == "belastbaarheid" and result.get('fml_generated'):
                metadata_dict['fml_rubrieken_generated'] = True

            logger.info(f"✓ Section {section_id} generated using {result['approach']}")

        except Exception as section_error:
            logger.error(f"Error generating section {section_id}: {str(section_error)}")
            content_dict[section_id] = f"Fout bij genereren van sectie '{section_info.get('title', section_id)}'. Handmatige aanvulling nodig."
            metadata_dict['sections'][section_id] = {
                'generated_at': datetime.utcnow().isoformat(),
                'approach': 'failed',
                'error': str(section_error),
                'title': section_info.get('title', section_id)
            }


def execute_parallel(sections, generator, content_dict, metadata_dict, max_workers, document_ids, case_id):
    """
    Execute sections in parallel using ThreadPoolExecutor

    Args:
        sections: List of (section_id, section_info) tuples
        generator: ADReportSectionGenerator instance
        content_dict: OrderedDict to store results (thread-safe writes)
        metadata_dict: Dict to store metadata (thread-safe writes)
        max_workers: Number of concurrent threads
        document_ids: List of document IDs to use
        case_id: ID of the case
    """
    write_lock = Lock()  # Protect shared dict writes

    def generate_with_timeout(section_id, section_info):
        """
        Wrapper to generate a section with timeout handling
        """
        try:
            result = generator.generate_section(
                section_id=section_id,
                section_info=section_info,
                document_ids=document_ids,
                case_id=case_id
            )

            return (section_id, section_info, result, None)

        except Exception as e:
            logger.error(f"Error in section {section_id}: {str(e)}")
            return (section_id, section_info, None, str(e))

    # Filter out None sections
    valid_sections = [(sid, sinfo) for sid, sinfo in sections if sinfo is not None]

    # Submit all tasks to thread pool
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all sections
        future_to_section = {
            executor.submit(generate_with_timeout, section_id, section_info): section_id
            for section_id, section_info in valid_sections
        }

        # Collect results as they complete
        for future in as_completed(future_to_section, timeout=120):
            section_id = future_to_section[future]

            try:
                section_id, section_info, result, error = future.result(timeout=120)

                # Thread-safe write to shared dicts
                with write_lock:
                    if error:
                        # Store error placeholder
                        content_dict[section_id] = f"Fout: {error}"
                        metadata_dict['sections'][section_id] = {
                            'generated_at': datetime.utcnow().isoformat(),
                            'approach': 'failed',
                            'error': error,
                            'title': section_info.get('title', section_id)
                        }
                    else:
                        # Store successful result
                        content_dict[section_id] = result['content']
                        metadata_dict['sections'][section_id] = {
                            'generated_at': datetime.utcnow().isoformat(),
                            'approach': result['approach'],
                            'title': result['title'],
                            'order': result['order']
                        }

                        # Track FML generation
                        if section_id == "belastbaarheid" and result.get('fml_generated'):
                            metadata_dict['fml_rubrieken_generated'] = True

                logger.info(f"✓ Section {section_id} completed")

            except TimeoutError:
                logger.error(f"✗ Section {section_id} timed out")
                with write_lock:
                    content_dict[section_id] = "Timeout tijdens generatie"
                    metadata_dict['sections'][section_id] = {
                        'generated_at': datetime.utcnow().isoformat(),
                        'approach': 'timeout',
                        'error': 'Section generation timed out'
                    }


@celery.task
def generate_enhanced_ad_report(report_id: str):
    """
    Generate an enhanced AD report using professional analysis-based template
    
    This task implements the comprehensive AD report structure identified through
    analysis of 4 professional AD reports.
    
    Args:
        report_id: UUID of the report to generate
        
    Returns:
        Dict with generation results
    """
    try:
        logger.info(f"Starting enhanced AD report generation for report {report_id}")
        
        # Get report info
        report = db_service.get_row_by_id("report", report_id)
        if not report:
            raise ValueError(f"Report with ID {report_id} not found")

        case_id = report["case_id"]
        user_id = report["user_id"]
        template_id = report.get("template_id", "enhanced_ad_rapport")

        # Get enhanced template
        enhanced_template = get_enhanced_ad_template()
        
        # Override template_id if using enhanced template
        if template_id == "enhanced_ad_rapport":
            template = enhanced_template
        else:
            # Fallback to original logic for other templates
            from app.api.v1.endpoints.reports import MVP_TEMPLATES
            if template_id not in MVP_TEMPLATES:
                raise ValueError(f"Template with ID {template_id} not found")
            template = MVP_TEMPLATES[template_id]

        logger.info(f"Using template: {template.get('name', template_id)} with {len(template['sections'])} sections")

        # Get user profile
        user_profile = db_service.get_user_profile(user_id)
        
        # Get processed documents (both "processed" and "enhanced" status)
        processed_docs = db_service.get_rows("document", {
            "case_id": case_id,
            "status": "processed"
        })
        enhanced_docs = db_service.get_rows("document", {
            "case_id": case_id,
            "status": "enhanced"
        })
        documents = processed_docs + enhanced_docs
        
        if not documents:
            raise ValueError(f"No processed documents found for case {case_id}")
            
        document_ids = [doc["id"] for doc in documents]
        logger.info(f"Found {len(document_ids)} processed documents")

        # Initialize report content and metadata
        report_content = OrderedDict()  # Use OrderedDict for proper section ordering
        report_metadata = {
            "generation_started": datetime.utcnow().isoformat(),
            "template_used": template_id,
            "template_version": template.get("version", "1.0"),
            "document_ids": document_ids,
            "user_profile": user_profile,
            "sections": {},
            "quality_checkpoints": template.get("quality_checkpoints", []),
            "fml_rubrieken_generated": False
        }

        # Get FML context for belastbaarheid section
        fml_rubrieken = get_fml_rubrieken_detailed()
        fml_context = {
            "rubrieken": fml_rubrieken,
            "standard_items": [item for rubriek in fml_rubrieken for item in rubriek.get("veel_voorkomende_items", rubriek.get("items", []))]
        }

        # Generate content for each section in order
        sections_by_order = sorted(
            template["sections"].items(),
            key=lambda x: x[1].get("order", 999)
        )

        total_sections = len(sections_by_order)
        logger.info(f"Generating {total_sections} sections using parallel processing")

        # Initialize section generator
        from app.tasks.generate_report_tasks.section_generator import ADReportSectionGenerator

        section_generator = ADReportSectionGenerator(
            user_profile=user_profile,
            fml_context=fml_context
        )

        # Record total report generation start time
        report_start_time = time.time()

        # PARALLEL IMPLEMENTATION: Execute sections in 5 phases
        phases = define_execution_phases(sections_by_order)

        for phase_num, phase in enumerate(phases, 1):
            phase_start = time.time()
            logger.info(f"\n=== Phase {phase_num}/{len(phases)}: {phase['name']} ===")

            if phase['mode'] == 'sequential':
                execute_sequential(
                    phase['sections'],
                    section_generator,
                    report_content,
                    report_metadata,
                    document_ids,
                    case_id
                )
            else:
                execute_parallel(
                    phase['sections'],
                    section_generator,
                    report_content,
                    report_metadata,
                    phase['max_workers'],
                    document_ids,
                    case_id
                )

            phase_duration = time.time() - phase_start
            logger.info(f"Phase {phase_num} completed in {phase_duration:.2f}s")

        # OLD SEQUENTIAL IMPLEMENTATION - Kept for reference
        """
        # Generate each section
        for section_id, section_info in sections_by_order:
            try:
                print(f"Generating section: {section_id}")

                result = section_generator.generate_section(
                    section_id=section_id,
                    section_info=section_info,
                    document_ids=document_ids,
                    case_id=case_id
                )

                # Store results
                report_content[section_id] = result["content"]
                report_metadata["sections"][section_id] = {
                    "generated_at": datetime.utcnow().isoformat(),
                    "approach": result["approach"],
                    "title": result["title"],
                    "order": result["order"]
                }

                # Track FML generation
                if section_id == "belastbaarheid" and result.get("fml_generated"):
                    report_metadata["fml_rubrieken_generated"] = True

                print(f"Section {section_id} generated using {result['approach']}")

            except Exception as section_error:
                print(f"Error generating section {section_id}: {str(section_error)}")
                report_content[section_id] = f"Fout bij genereren van sectie '{section_info.get('title', section_id)}'. Handmatige aanvulling nodig."
                report_metadata["sections"][section_id] = {
                    "generated_at": datetime.utcnow().isoformat(),
                    "approach": "failed",
                    "error": str(section_error),
                    "title": section_info.get("title", section_id)
                }
        """

        # OLD IMPLEMENTATION - Kept for reference
        """
        for i, (section_id, section_info) in enumerate(sections_by_order, 1):
            try:
                print(f"Generating section {i}/{total_sections}: {section_info.get('title', section_id)}")
                
                # Create section-specific context
                section_context = None
                if section_id == "belastbaarheid":
                    section_context = fml_context
                
                # Create specialized prompt
                section_prompt = create_ad_specific_prompt(
                    section_id=section_id,
                    section_info=section_info,
                    user_profile=user_profile,
                    fml_context=section_context
                )

                # Try RAG approach first
                section_content = None
                approach_used = "failed"
                
                # Try RAG approach with faster Haiku model
                if HAS_RAG:
                    try:
                        # Use async RAG pipeline
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            section_result = loop.run_until_complete(
                                generate_content_for_section(
                                    section_id=section_id,
                                    section_info=section_info,
                                    document_ids=document_ids,
                                    case_id=case_id,
                                    user_profile=user_profile
                                )
                            )
                            section_content = section_result["content"]
                            approach_used = "enhanced_rag"
                            
                            # Track FML generation
                            if section_id == "belastbaarheid":
                                report_metadata["fml_rubrieken_generated"] = True
                                
                        finally:
                            loop.close()
                            
                    except Exception as rag_error:
                        print(f"Enhanced RAG failed for {section_id}: {str(rag_error)}")
                        section_content = None
                
                # Fallback to direct LLM approach (same as standard report generator)
                if not section_content:
                    try:
                        # Get document content for context
                        full_documents = []
                        for doc_id in document_ids:
                            chunks = db_service.get_document_chunks(doc_id)
                            if chunks:
                                content = "\n\n".join([chunk["content"] for chunk in chunks])
                                document = db_service.get_row_by_id("document", doc_id)
                                full_documents.append({
                                    "filename": document.get("filename", "Unnamed"),
                                    "content": content
                                })
                        
                        combined_text = "\n\n=== DOCUMENT SEPARATOR ===\n\n".join(
                            [f"{doc['filename']}:\n{doc['content']}" for doc in full_documents]
                        )
                        
                        # Generate content directly with LLM
                        from app.utils.llm_provider import create_llm_instance
                        
                        model = create_llm_instance(
                            temperature=0.2,  # Increased for Haiku
                            max_tokens=3072,  # Haiku can handle more tokens faster
                            dangerous_content_level="BLOCK_NONE"
                        )
                        
                        full_prompt = f"{section_prompt}\n\nDocumenten:\n{combined_text}"
                        response = model.generate_content([
                            {"role": "system", "parts": ["Je bent een ervaren arbeidsdeskundige die professionele rapporten schrijft."]},
                            {"role": "user", "parts": [full_prompt]}
                        ])
                        
                        section_content = response.text if hasattr(response, 'text') else str(response)
                        
                        approach_used = "enhanced_direct"
                        
                        # Track FML generation
                        if section_id == "belastbaarheid":
                            report_metadata["fml_rubrieken_generated"] = True
                            
                    except Exception as direct_error:
                        print(f"Direct LLM approach failed for {section_id}: {str(direct_error)}")
                        section_content = f"Sectie '{section_info.get('title', section_id)}' kon niet gegenereerd worden. Handmatige invulling vereist."
                        approach_used = "error_fallback"

                # Store generated content
                report_content[section_id] = section_content
                report_metadata["sections"][section_id] = {
                    "generated_at": datetime.utcnow().isoformat(),
                    "approach": approach_used,
                    "title": section_info.get("title", section_id),
                    "order": section_info.get("order", 999)
                }
                
                print(f"✓ Section {section_id} generated using {approach_used}")
                
            except Exception as section_error:
                print(f"Error generating section {section_id}: {str(section_error)}")
                report_content[section_id] = f"Fout bij genereren van sectie '{section_info.get('title', section_id)}'. Handmatige aanvulling nodig."
                report_metadata["sections"][section_id] = {
                    "generated_at": datetime.utcnow().isoformat(),
                    "approach": "failed",
                    "error": str(section_error),
                    "title": section_info.get("title", section_id)
                }
        """

        # Complete metadata
        report_metadata["generation_completed"] = datetime.utcnow().isoformat()
        
        # Validate report completeness
        validation_results = validate_ad_report_completeness(report_content)
        report_metadata["validation"] = validation_results
        
        logger.info(f"Report completeness: {validation_results['completeness_score']:.1f}%")
        
        # Update report in database
        update_data = {
            "status": "generated",
            "content": report_content,
            "report_metadata": report_metadata,
            "generation_method": "enhanced_ad",
            "format_version": "2.0",
            "has_structured_data": True,
            "fml_rubrieken_count": len(fml_rubrieken) if report_metadata["fml_rubrieken_generated"] else 0,
            "quality_metrics": {
                "completeness_score": validation_results["completeness_score"],
                "sections_generated": len([s for s in report_metadata["sections"].values() if s["approach"] != "failed"]),
                "total_sections": len(template["sections"]),
                "fml_generated": report_metadata["fml_rubrieken_generated"]
            },
            "updated_at": datetime.utcnow().isoformat()
        }
        
        db_service.update_report(report_id, update_data)
        
        # Calculate total report generation time
        total_duration = time.time() - report_start_time
        logger.info(f"Total report generation: {total_duration:.2f}s")
        logger.info(f"✓ Enhanced AD report {report_id} generated successfully")
        
        return {
            "status": "success",
            "report_id": report_id,
            "template_used": template_id,
            "sections_generated": len(report_content),
            "completeness_score": validation_results["completeness_score"],
            "approach_summary": {
                approach: len([s for s in report_metadata["sections"].values() if s["approach"] == approach])
                for approach in set(s["approach"] for s in report_metadata["sections"].values())
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating enhanced AD report {report_id}: {str(e)}")
        
        # Update report status to failed
        db_service.update_report(report_id, {
            "status": "failed",
            "error": "Enhanced AD report generation failed",
            "updated_at": datetime.utcnow().isoformat()
        })
        
        # Re-raise for Celery task failure
        raise

# Helper function to get available AD templates
def get_available_ad_templates() -> List[Dict[str, Any]]:
    """
    Get list of available AD report templates
    
    Returns:
        List of template metadata
    """
    templates = []
    
    # Enhanced template
    enhanced = get_enhanced_ad_template()
    templates.append({
        "id": enhanced["id"],
        "name": enhanced["name"],
        "description": enhanced["description"],
        "version": enhanced["version"],
        "sections_count": len(enhanced["sections"]),
        "based_on_analysis": enhanced["based_on_analysis"],
        "quality_checkpoints": len(enhanced["quality_checkpoints"])
    })
    
    return templates