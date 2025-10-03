"""
Enhanced Arbeidsdeskundig Report Template
Based on comprehensive analysis of professional AD reports

This module defines the enhanced AD report structure incorporating findings from:
- AD rapportage format Staatvandienst
- AD rapportage mevrouw Jansen Provincie Gelderland  
- AD rapportage format Vector Advies
- AD rapportage mevrouw Wens-Smits Monta

Key structural elements identified:
1. Standardized 7-section framework
2. Consistent 4-question assessment approach
3. Detailed FML with 6 core rubrieken
4. Professional formatting requirements
5. Template/completed report variations
"""

from typing import Dict, Any, List
from datetime import datetime

# Enhanced AD Report Template based on analysis findings
ENHANCED_AD_TEMPLATE = {
    "id": "enhanced_ad_rapport",
    "name": "Arbeidsdeskundig Rapport - Enhanced",
    "description": "Uitgebreid AD rapport format gebaseerd op professionele standaarden",
    "version": "2.0",
    "based_on_analysis": "4 professional AD reports analyzed",
    "sections": {
        # Section 1: Voorblad en Inhoudsopgave
        "voorblad": {
            "title": "Voorblad",
            "description": "Professionele titelpagina met bedrijfsbranding en rapportidentificatie",
            "order": 1,
            "required_elements": [
                "titel_rapport",
                "werknemer_gegevens", 
                "opdrachtgever_gegevens",
                "adviseur_gegevens",
                "datum_rapport",
                "versie_nummer",
                "registratie_arbeidsdeskundige"
            ]
        },
        
        "inhoudsopgave": {
            "title": "Inhoudsopgave", 
            "description": "Gestructureerde inhoudsopgave met paginanummering",
            "order": 2,
            "auto_generated": True
        },

        # Section 2: Samenvatting (Critical addition from analysis)
        "samenvatting": {
            "title": "Samenvatting",
            "description": "Beknopte samenvatting vraagstelling en hoofdconclusies", 
            "order": 3,
            "key_elements": [
                "samenvatting_vraagstelling",
                "samenvatting_conclusies",
                "belangrijkste_aanbevelingen"
            ]
        },

        # Section 3: Vraagstelling (Standardized 4-question approach)
        "vraagstelling": {
            "title": "1. Vraagstelling", 
            "description": "Onderzoeksvragen volgens gestandaardiseerd 4-vragen protocol",
            "order": 4,
            "standard_questions": [
                {
                    "nummer": "1.1",
                    "vraag": "Is betrokkene geschikt voor zijn eigen functie bij eigen werkgever?"
                },
                {
                    "nummer": "1.2", 
                    "vraag": "Zo nee, is betrokkene geschikt voor zijn eigen functie bij eigen werkgever na aanpassing van zijn functie en/of werkplek?"
                },
                {
                    "nummer": "1.3",
                    "vraag": "Zo nee, is betrokkene geschikt voor andere functies bij eigen werkgever?"
                },
                {
                    "nummer": "1.4",
                    "vraag": "Zo nee, is betrokkene geschikt voor andere functies bij andere werkgever?"
                }
            ]
        },

        # Section 4: Ondernomen Activiteiten
        "ondernomen_activiteiten": {
            "title": "2. Ondernomen activiteiten",
            "description": "Overzicht van alle uitgevoerde onderzoekshandelingen", 
            "order": 5,
            "standard_activities": [
                "Bestudering van beschikbare stukken",
                "Gesprek met werknemer", 
                "Gesprek met werkgever",
                "Functieanalyse",
                "Belastbaarheidsonderzoek", 
                "Analyse arbeidsmarkt mogelijkheden"
            ]
        },

        # Section 5: Gegevensverzameling (Multi-part comprehensive section)
        "gegevensverzameling_voorgeschiedenis": {
            "title": "3.1 Voorgeschiedenis",
            "description": "Medische voorgeschiedenis, verzuimhistorie en relevante achtergrond",
            "order": 6,
            "subsections": [
                "medische_voorgeschiedenis",
                "verzuimhistorie", 
                "eerdere_behandelingen",
                "huidige_medische_status"
            ]
        },

        "gegevensverzameling_werkgever": {
            "title": "3.2 Gegevens werkgever",
            "description": "Uitgebreide bedrijfsgegevens en organisatiestructuur",
            "order": 7,
            "required_fields": [
                "naam_bedrijf",
                "contactgegevens",
                "aard_bedrijf", 
                "omvang_organisatie",
                "organisatiestructuur",
                "beschikbare_functies",
                "bedrijfscultuur",
                "re_integratie_ervaring"
            ]
        },

        "gegevensverzameling_werknemer": {
            "title": "3.3 Gegevens werknemer", 
            "description": "Opleidingen, arbeidsverleden en bekwaamheden werknemer",
            "order": 8,
            "subsections": [
                "opleidingen_gevolgd",
                "arbeidsverleden_detail",
                "computervaardigheden",
                "taalvaardigheden", 
                "rijbewijs_mobiliteit",
                "overige_bekwaamheden"
            ]
        },

        # Section 6: Belastbaarheid (Critical FML section)
        "belastbaarheid": {
            "title": "3.4 Belastbaarheid van werknemer",
            "description": "Functionele Mogelijkhedenlijst (FML) en capaciteitsanalyse",
            "order": 9,
            "fml_benadering": "selectief_relevant",
            "fml_instructie": "Selecteer alleen relevante FML-items op basis van medische diagnose en functie-eisen. Focus op daadwerkelijke beperkingen, niet op complete inventarisatie.",
            "fml_rubrieken": [
                {
                    "rubriek": "I",
                    "naam": "Persoonlijk functioneren",
                    "veel_voorkomende_items": [
                        "1. Concentreren van de aandacht",
                        "2. Verdelen van de aandacht", 
                        "3. Herinneren",
                        "6. Zelfstandig handelen",
                        "7. Handelingstempo"
                    ]
                },
                {
                    "rubriek": "II", 
                    "naam": "Sociaal en maatschappelijk functioneren",
                    "veel_voorkomende_items": [
                        "10. Omgaan met collega's",
                        "11. Omgaan met leidinggevenden",
                        "12. Omgaan met cliënten/klanten",
                        "14. Werken in groepsverband"
                    ]
                },
                {
                    "rubriek": "III",
                    "naam": "Waarneming en communicatie", 
                    "veel_voorkomende_items": [
                        "18. Zien",
                        "19. Horen",
                        "20. Spreken"
                    ]
                },
                {
                    "rubriek": "IV",
                    "naam": "Dynamische handelingen",
                    "veel_voorkomende_items": [
                        "23. Lopen op vlakke ondergrond",
                        "24. Traplopen", 
                        "25. Bukken",
                        "33. Duwen en trekken",
                        "34. Tillen of dragen"
                    ],
                    "classificatie_voorbeelden": {
                        "34": "normaal: kan meer dan 25kg tillen; beperkt: kan 10-25kg tillen; sterk beperkt: kan minder dan 10kg tillen",
                        "33": "normaal: kan normale krachten duwen/trekken; beperkt: kan max. 20kg; sterk beperkt: kan max. 5kg",
                        "23": "normaal: kan onbeperkt lopen; beperkt: kan max. 500m; sterk beperkt: kan max. 50m"
                    }
                },
                {
                    "rubriek": "V",
                    "naam": "Statische houdingen",
                    "veel_voorkomende_items": [
                        "37. Zitten",
                        "38. Staan", 
                        "39. Lopen"
                    ]
                },
                {
                    "rubriek": "VI",
                    "naam": "Handvaardigheid",
                    "veel_voorkomende_items": [
                        "42. Grijpen", 
                        "43. Vastpakken/vasthouden",
                        "44. Fijne handbewegingen"
                    ]
                }
            ],
            "beperkings_niveaus": ["Niet beperkt", "Beperkt", "Sterk beperkt"],
            "prognose_elementen": [
                "verwachte_ontwikkeling",
                "duurzaamheid_beperkingen", 
                "verbeterings_mogelijkheden"
            ]
        },

        "eigen_functie": {
            "title": "3.5 Eigen functie werknemer",
            "description": "Gedetailleerde functieomschrijving en analyse belastende aspecten", 
            "order": 10,
            "analysis_elements": [
                "functienaam_omschrijving",
                "arbeidspatroon_contractvorm",
                "taken_verantwoordelijkheden",
                "belastende_aspecten_analyse",
                "percentage_tijdsbesteding_per_taak",
                "fysieke_belasting_details",
                "mentale_belasting_details",
                "sociale_belasting_details"
            ]
        },

        # Section 7: Gesprekken (Three separate conversation sections)
        "gesprek_werkgever": {
            "title": "3.6 Gesprek met de werkgever",
            "description": "Visie werkgever op functioneren en re-integratiemogelijkheden",
            "order": 11,
            "conversation_topics": [
                "algemene_indruk_functioneren",
                "visie_op_huidige_beperkingen", 
                "visie_op_duurzaamheid_inzet",
                "mogelijkheden_aanpassingen",
                "mogelijkheden_andere_functies",
                "ervaring_re_integratie_processen",
                "bereidheid_medewerking"
            ]
        },

        "gesprek_werknemer": {
            "title": "3.7 Gesprek met werknemer",
            "description": "Visie werknemer op beperkingen, mogelijkheden en re-integratie",
            "order": 12, 
            "conversation_topics": [
                "ervaren_beperkingen_werk",
                "visie_op_eigen_mogelijkheden",
                "wensen_aanpassingen_functie",
                "visie_op_andere_werkzaamheden", 
                "motivatie_werkhervatting",
                "zorgen_verwachtingen",
                "re_integratie_doelstellingen"
            ]
        },

        "gesprek_gezamenlijk": {
            "title": "3.8 Gesprek met werkgever en werknemer gezamenlijk",
            "description": "Afstemming en bespreking van advies en vervolgstappen",
            "order": 13,
            "discussion_points": [
                "gezamenlijke_visie_situatie",
                "afstemming_over_mogelijkheden", 
                "bespreking_voorgesteld_advies",
                "afspraken_vervolgtraject",
                "verwachtingen_beide_partijen"
            ]
        },

        # Section 8: Visie Arbeidsdeskundige (Multi-part analysis)  
        "visie_ad_eigen_werk": {
            "title": "4.1 Geschiktheid voor eigen werk",
            "description": "Arbeidsdeskundige analyse geschiktheid huidige functie",
            "order": 14,
            "analysis_framework": [
                "confrontatie_belastbaarheid_belasting",
                "specifieke_knelpunten_identificatie",
                "geschiktheids_conclusie_per_aspect", 
                "overall_geschiktheidsoordeel"
            ]
        },

        "visie_ad_aanpassing": {
            "title": "4.2 Aanpassing eigen werk",
            "description": "Mogelijkheden voor aanpassing huidige functie",
            "order": 15,
            "aanpassing_categorien": [
                "werkplek_aanpassingen",
                "taak_aanpassingen",
                "werktijd_aanpassingen", 
                "begeleiding_ondersteuning",
                "opleidingen_training"
            ]
        },

        "visie_ad_ander_werk_eigen": {
            "title": "4.3 Geschiktheid voor ander werk bij eigen werkgever", 
            "description": "Alternatieven binnen huidige organisatie",
            "order": 16,
            "assessment_areas": [
                "beschikbare_functies_organisatie",
                "geschiktheid_per_functie_categorie",
                "benodigde_aanpassingen_opleiding",
                "duurzaamheids_prognose"
            ]
        },

        "visie_ad_ander_werk_extern": {
            "title": "4.4 Geschiktheid voor ander werk bij andere werkgever",
            "description": "Zoekrichting en mogelijkheden externe arbeidsmarkt", 
            "order": 17,
            "market_analysis": [
                "geschikte_functie_categorien",
                "arbeidsmarkt_kansen_beoordeling",
                "geografische_mobiliteit", 
                "opleiding_omscholing_behoeften",
                "competitieve_positie_arbeidsmarkt"
            ]
        },

        "visie_ad_duurzaamheid": {
            "title": "4.5 Duurzaamheid van herplaatsing",
            "description": "Prognose en duurzaamheidsanalyse re-integratie",
            "order": 18,
            "sustainability_factors": [
                "medische_prognose",
                "motivatie_werkcapaciteit", 
                "aanpassings_mogelijkheden",
                "ondersteunings_behoeften",
                "lange_termijn_verwachtingen"
            ]
        },

        # Section 9: Eindconclusies
        "advies": {
            "title": "5. Advies",
            "description": "Concrete aanbevelingen en vervolgstappen",
            "order": 19,
            "advice_structure": [
                "primaire_aanbeveling",
                "alternatieve_opties", 
                "concrete_vervolgstappen",
                "tijdsplanning",
                "verantwoordelijkheden_verdeling"
            ]
        },

        "conclusie": {
            "title": "6. Conclusie", 
            "description": "Beantwoording hoofdvragen en eindconclusies",
            "order": 20,
            "conclusion_format": [
                "antwoord_vraag_1_1",
                "antwoord_vraag_1_2",
                "antwoord_vraag_1_3", 
                "antwoord_vraag_1_4",
                "samenvattende_eindconclusie"
            ]
        },

        "vervolg": {
            "title": "7. Vervolg",
            "description": "Vervolgtraject en aanbevolen acties", 
            "order": 21,
            "follow_up_categories": [
                "korte_termijn_acties",
                "middellange_termijn_planning",
                "monitoring_evaluatie_momenten",
                "betrokken_partijen_rollen"
            ]
        },

        # Section 10: Bijlagen
        "bijlagen": {
            "title": "Bijlagen",
            "description": "Ondersteunende documenten en formulieren",
            "order": 22,
            "standard_attachments": [
                "fml_formulier_volledig",
                "functie_analyse_details", 
                "medische_rapportages",
                "arbeidscontract_functieomschrijving",
                "correspondentie_betrokkenen"
            ]
        }
    },
    
    # Professional formatting requirements
    "formatting_requirements": {
        "font": "Times New Roman, 11pt", 
        "line_spacing": "1.25",
        "margins": "2.5cm all sides",
        "header_styling": "Professional blue hierarchy (#1e40af, #2563eb, #3b82f6)",
        "page_numbering": "Bottom center",
        "section_numbering": "Hierarchical (1, 1.1, 1.1.1)",
        "table_formatting": "Professional borders, consistent spacing"
    },
    
    # Quality control checkpoints
    "quality_checkpoints": [
        "alle_4_standaard_vragen_beantwoord",
        "fml_volledig_ingevuld_6_rubrieken", 
        "confrontatie_belastbaarheid_belasting_uitgevoerd",
        "professionele_formatting_toegepast",
        "registratie_arbeidsdeskundige_vermeld",
        "conclusies_logisch_onderbouwd"
    ]
}

def get_enhanced_ad_template() -> Dict[str, Any]:
    """
    Get the enhanced AD report template based on professional analysis
    
    Returns:
        Dict containing complete enhanced AD report template structure
    """
    return ENHANCED_AD_TEMPLATE

def get_fml_rubrieken_detailed() -> List[Dict[str, Any]]:
    """
    Get detailed FML rubrieken structure for report generation
    
    Returns:
        List of detailed FML rubrieken with all standard items
    """
    return ENHANCED_AD_TEMPLATE["sections"]["belastbaarheid"]["fml_rubrieken"]

def get_standard_questions() -> List[Dict[str, str]]:
    """
    Get the standardized 4-question framework
    
    Returns:
        List of standard arbeidsdeskundig questions
    """
    return ENHANCED_AD_TEMPLATE["sections"]["vraagstelling"]["standard_questions"]

# Backward compatibility alias for existing imports
AD_REPORT_TEMPLATE = ENHANCED_AD_TEMPLATE

def validate_ad_report_completeness(report_content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that an AD report meets professional completeness standards
    
    Args:
        report_content: Generated report content to validate
        
    Returns:
        Dict containing validation results and missing elements
    """
    required_sections = [section_id for section_id in ENHANCED_AD_TEMPLATE["sections"].keys()]
    quality_checkpoints = ENHANCED_AD_TEMPLATE["quality_checkpoints"]
    
    validation_results = {
        "is_complete": True,
        "missing_sections": [],
        "failed_checkpoints": [],
        "completeness_score": 0.0
    }
    
    # Check section completeness
    for section_id in required_sections:
        if section_id not in report_content or not report_content[section_id]:
            validation_results["missing_sections"].append(section_id)
            validation_results["is_complete"] = False
    
    # Calculate completeness score
    completed_sections = len(required_sections) - len(validation_results["missing_sections"])
    validation_results["completeness_score"] = (completed_sections / len(required_sections)) * 100
    
    return validation_results