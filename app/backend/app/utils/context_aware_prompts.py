"""
Context-Aware Prompts voor Arbeidsdeskundige AI
Intelligente prompt generatie per rapport sectie en document type
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from app.utils.smart_document_classifier import DocumentType


class ReportSection(Enum):
    """Arbeidsdeskundige rapport secties"""
    INTRODUCTIE = "introductie"
    PERSOONSGEGEVENS = "persoonsgegevens"
    MEDISCHE_SITUATIE = "medische_situatie"
    ARBEIDSANAMNESE = "arbeidsanamnese"
    BELASTBAARHEID = "belastbaarheid"
    BEPERKINGEN = "beperkingen"
    MOGELIJKHEDEN = "mogelijkheden"
    WERKHERVATTING = "werkhervatting"
    ADVIES = "advies"
    CONCLUSIE = "conclusie"


class ComplexityLevel(Enum):
    """Prompt complexiteit niveaus"""
    BASIC = "basic"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class PromptContext:
    """Context informatie voor prompt generatie"""
    section: ReportSection
    document_types: List[str]
    available_chunks: List[Dict[str, Any]]
    case_metadata: Dict[str, Any]
    user_profile: Optional[Dict[str, Any]]
    complexity_level: ComplexityLevel


@dataclass
class GeneratedPrompt:
    """Gegenereerde prompt met metadata"""
    prompt_text: str
    section: ReportSection
    context_sources: List[str]
    complexity_level: ComplexityLevel
    quality_indicators: Dict[str, Any]
    generation_timestamp: str


class ContextAwarePromptGenerator:
    """
    Generator voor context-aware prompts per rapport sectie
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Section-specific prompt templates
        self.section_templates = self._load_section_templates()
        
        # Document type specific guidelines
        self.document_guidelines = self._load_document_guidelines()
        
        # Dutch professional terminology
        self.terminology = self._load_professional_terminology()
        
        # Quality criteria per section
        self.quality_criteria = self._load_quality_criteria()
    
    def generate_section_prompt(
        self, 
        section: ReportSection,
        context_chunks: List[str] = None,
        document_type: Optional['DocumentType'] = None,
        complexity_level: ComplexityLevel = ComplexityLevel.MEDIUM,
        additional_context: Dict[str, Any] = None
    ) -> str:
        """
        Convenience method voor eenvoudige prompt generatie
        """
        # Create PromptContext from parameters
        context = PromptContext(
            section=section,
            document_types=[document_type.value] if document_type else [],
            available_chunks=[{"text": chunk} for chunk in (context_chunks or [])],
            case_metadata=additional_context or {},
            user_profile=None,
            complexity_level=complexity_level
        )
        
        # Generate using full method
        result = self.generate_full_section_prompt(context)
        return result.prompt_text
    
    def generate_full_section_prompt(self, context: PromptContext) -> GeneratedPrompt:
        """
        Genereer een context-aware prompt voor een specifieke rapport sectie
        """
        try:
            start_time = datetime.utcnow()
            
            self.logger.info(f"Generating prompt for section {context.section.value}")
            
            # Get base template for section
            base_template = self.section_templates.get(
                context.section, 
                self.section_templates[ReportSection.CONCLUSIE]
            )
            
            # Adapt template based on available document types
            adapted_template = self._adapt_for_document_types(base_template, context.document_types)
            
            # Add context-specific instructions
            contextualized_prompt = self._add_context_instructions(adapted_template, context)
            
            # Apply complexity adjustments
            final_prompt = self._adjust_for_complexity(contextualized_prompt, context.complexity_level)
            
            # Generate quality indicators
            quality_indicators = self._generate_quality_indicators(context)
            
            generated_prompt = GeneratedPrompt(
                prompt_text=final_prompt,
                section=context.section,
                context_sources=[chunk.get("document_type", "unknown") for chunk in context.available_chunks],
                complexity_level=context.complexity_level,
                quality_indicators=quality_indicators,
                generation_timestamp=datetime.utcnow().isoformat()
            )
            
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            self.logger.info(f"Generated prompt for {context.section.value} in {generation_time:.2f}s")
            
            return generated_prompt
            
        except Exception as e:
            self.logger.error(f"Error generating prompt for {context.section}: {e}")
            return self._generate_fallback_prompt(context)
    
    def _load_section_templates(self) -> Dict[ReportSection, str]:
        """Laad section-specifieke prompt templates"""
        
        return {
            ReportSection.INTRODUCTIE: """
Je bent een expert arbeidsdeskundige die een professioneel rapport schrijft. 
Schrijf een beknopte introductie voor dit arbeidsdeskundig rapport.

CONTEXT: {context_description}
BESCHIKBARE INFORMATIE: {available_sources}

INSTRUCTIES:
- Beschrijf kort het doel van het onderzoek
- Vermeld de datum en methode van onderzoek
- Geef een overzicht van de gebruikte bronnen
- Houd het professioneel en objectief
- Gebruik Nederlandse arbeidsdeskundige terminologie

VERWACHTE LENGTE: 150-300 woorden

INTRODUCTIE:
""",
            
            ReportSection.MEDISCHE_SITUATIE: """
Je bent een arbeidsdeskundige die medische informatie vertaalt naar arbeidsdeskundige conclusies.
Analyseer de medische informatie en beschrijf de relevante medische situatie voor arbeidsdeskundig onderzoek.

MEDISCHE BRONNEN:
{medical_sources}

ANDERE RELEVANTE INFORMATIE:
{additional_context}

INSTRUCTIES:
- Focus op arbeidsrelevante medische aspecten
- Vermijd medische details die niet relevant zijn voor arbeid
- Gebruik begrijpelijke taal (geen medisch jargon)
- Beschrijf de impact op het functioneren
- Geef een objectieve samenvatting
- Respecteer privacy en beperk je tot relevante informatie

KWALITEITSCRITERIA:
- Arbeidsrelevantie: Is de informatie relevant voor arbeidsgeschiktheid?
- Objectiviteit: Wordt de informatie neutraal en feitelijk gepresenteerd?
- Volledigheid: Zijn alle relevante medische aspecten genoemd?
- Begrijpelijkheid: Is de tekst toegankelijk voor niet-medici?

MEDISCHE SITUATIE:
""",
            
            ReportSection.BELASTBAARHEID: """
Je bent een ervaren arbeidsdeskundige die een belastbaarheidsanalyse uitvoert.
Analyseer de beschikbare informatie en geef een gedetailleerde belastbaarheidsanalyse.

BESCHIKBARE INFORMATIE:
{context_information}

DOCUMENT TYPES BESCHIKBAAR: {document_types}

INSTRUCTIES:
- Analyseer fysieke belastbaarheid (tillen, lopen, staan, zitten)
- Analyseer mentale belastbaarheid (concentratie, stress, complexiteit)
- Analyseer sociale belastbaarheid (teamwerk, klantcontact)
- Geef concrete beperkingen en mogelijkheden
- Gebruik de FCE (Functionele Capaciteit Evaluatie) methodiek
- Baseer conclusies op objectieve informatie
- Vermeld onzekerheden en aanbevelingen voor aanvullend onderzoek

STRUCTUUR:
1. Fysieke belastbaarheid
2. Mentale/cognitieve belastbaarheid  
3. Sociale belastbaarheid
4. Samenvatting belastbaarheidsprofiel

BELASTBAARHEIDSANALYSE:
""",
            
            ReportSection.BEPERKINGEN: """
Je bent een arbeidsdeskundige die functionele beperkingen in kaart brengt.
Analyseer de informatie en beschrijf de concrete beperkingen voor arbeidsparticipatie.

RELEVANTE INFORMATIE:
{limitation_sources}

INSTRUCTIES:
- Beschrijf specifieke functionele beperkingen
- Maak onderscheid tussen tijdelijke en permanente beperkingen
- Geef concrete voorbeelden van wat niet/beperkt mogelijk is
- Gebruik de ICF (International Classification of Functioning) methodiek
- Focus op impact voor arbeidsuitvoering
- Vermijd vage formuleringen, wees specifiek en meetbaar
- Onderbouw beperkingen met beschikbare informatie

CATEGORIEËN:
- Fysieke beperkingen (beweging, kracht, houding)
- Cognitieve beperkingen (geheugen, concentratie, planning)
- Psychosociale beperkingen (stress, communicatie, teamwerk)
- Sensorische beperkingen (zien, horen, voelen)

FUNCTIONELE BEPERKINGEN:
""",
            
            ReportSection.MOGELIJKHEDEN: """
Je bent een arbeidsdeskundige die zich richt op mogelijkheden en potentieel.
Analyseer de informatie en beschrijf welke arbeidsmogelijkheden er zijn.

BESCHIKBARE INFORMATIE:
{opportunity_sources}

INSTRUCTIES:
- Focus op wat WEL mogelijk is (strength-based approach)
- Beschrijf concrete arbeidsmogelijkheden
- Geef voorbeelden van geschikte werkzaamheden
- Analyseer aanpassingsmogelijkheden van de huidige functie
- Overweeg alternatieve functities binnen of buiten het huidige bedrijf
- Baseer mogelijkheden op objectieve capaciteiten
- Geef realistische en haalbare perspectieven

STRUCTUUR:
1. Huidige functie - aanpassingsmogelijkheden
2. Alternatieve functies binnen huidig werkdomein
3. Andere geschikte werkdomeinen
4. Bijzondere talenten en sterke punten

ARBEIDSMOGELIJKHEDEN:
""",
            
            ReportSection.WERKHERVATTING: """
Je bent een arbeidsdeskundige gespecialiseerd in re-integratie en werkhervatting.
Ontwikkel een concreet plan voor werkhervatting op basis van de beschikbare informatie.

RELEVANTE INFORMATIE:
{reintegration_context}

INSTRUCTIES:
- Maak een stapsgewijs plan voor werkhervatting
- Geef concrete tijdslijnen en mijlpalen
- Beschrijf noodzakelijke aanpassingen (werkplek, taken, uren)
- Overweeg gefaseerde opbouw van werkzaamheden
- Betrek alle stakeholders (werkgever, behandelaars, betrokkene)
- Geef voorwaarden voor succesvolle werkhervatting
- Beschrijf follow-up en evaluatiemomenten

ELEMENTEN VAN HET PLAN:
1. Voorbereidingsfase
2. Opstartfase (eerste weken)
3. Opbouwfase (maanden 1-3)
4. Stabilisatiefase (maanden 3-6)
5. Evaluatie en toekomstperspectief

WERKHERVATTING PLAN:
""",
            
            ReportSection.ADVIES: """
Je bent een senior arbeidsdeskundige die concrete, actionable adviezen geeft.
Formuleer heldere adviezen gebaseerd op alle beschikbare informatie.

ALLE BESCHIKBARE INFORMATIE:
{comprehensive_context}

INSTRUCTIES:
- Geef concrete, uitvoerbare adviezen
- Richt adviezen aan relevante stakeholders (werkgever, werknemer, behandelaars)
- Prioriteer adviezen naar urgentie en impact
- Geef tijdslijnen voor implementatie
- Beschrijf verwachte resultaten
- Baseer adviezen op evidence-based practices
- Zorg voor realistische en haalbare aanbevelingen

STAKEHOLDERS:
- Voor de werknemer/betrokkene
- Voor de werkgever/leidinggevende  
- Voor behandelaars/begeleiders
- Voor UWV/verzekeraar (indien relevant)

ADVIEZEN EN AANBEVELINGEN:
""",
            
            ReportSection.CONCLUSIE: """
Je bent een ervaren arbeidsdeskundige die een gedegen conclusie formuleert.
Schrijf een heldere, onderbouwde conclusie gebaseerd op alle beschikbare informatie.

ALLE INFORMATIE EN ANALYSES:
{full_context}

INSTRUCTIES:
- Geef een duidelijk antwoord op de onderzoeksvraag
- Vat de belangrijkste bevindingen samen
- Geef een eindoordeel over arbeidsgeschiktheid
- Beschrijf de mate van arbeidsgeschiktheid (percentage indien relevant)
- Vermeld belangrijkste aanbevelingen kort
- Gebruik professionele, objectieve toon
- Zorg voor een logische afsluiting van het rapport

STRUCTUUR:
1. Eindoordeel arbeidsgeschiktheid
2. Belangrijkste bevindingen samenvatting
3. Kernpunten advies
4. Perspectief en prognose

CONCLUSIE:
"""
        }
    
    def _load_document_guidelines(self) -> Dict[str, Dict[str, str]]:
        """Laad document type specifieke guidelines"""
        
        return {
            DocumentType.MEDICAL_REPORT.value: {
                "focus": "Vertaal medische bevindingen naar arbeidsrelevante impact",
                "terminology": "Gebruik functionele terminologie, vermijd medisch jargon",
                "critical_elements": "Diagnose, prognose, functionele beperkingen, behandelplan",
                "quality_check": "Is de medische informatie correct geïnterpreteerd voor arbeidscontext?"
            },
            
            DocumentType.ASSESSMENT_REPORT.value: {
                "focus": "Bouw voort op bestaande arbeidsdeskundige analyses",
                "terminology": "Gebruik consistente arbeidsdeskundige terminologie",
                "critical_elements": "Belastbaarheid, beperkingen, mogelijkheden, advies",
                "quality_check": "Zijn de arbeidsdeskundige conclusies logisch en onderbouwd?"
            },
            
            DocumentType.INSURANCE_DOCUMENT.value: {
                "focus": "Integreer verzekeringsrechtelijke aspecten",
                "terminology": "Respecteer juridische en verzekeringstechnische termen",
                "critical_elements": "Uitkeringsstatus, mate arbeidsgeschiktheid, verplichtingen",
                "quality_check": "Zijn de juridische aspecten correct meegenomen?"
            },
            
            DocumentType.PERSONAL_STATEMENT.value: {
                "focus": "Integreer subjectieve beleving met objectieve analyse",
                "terminology": "Balanceer empathie met professionele objectiviteit",
                "critical_elements": "Subjectieve klachten, functionele impact, belevingswereld",
                "quality_check": "Is er balans tussen empathie en objectiviteit?"
            },
            
            DocumentType.LEGAL_DOCUMENT.value: {
                "focus": "Respecteer juridische context en uitspraken",
                "terminology": "Gebruik correcte juridische terminologie",
                "critical_elements": "Juridische verplichtingen, uitspraken, rechtsgevolgen",
                "quality_check": "Zijn juridische aspecten correct geïnterpreteerd?"
            },
            
            "default": {
                "focus": "Gebruik algemene arbeidsdeskundige methodiek",
                "terminology": "Standaard arbeidsdeskundige terminologie",
                "critical_elements": "Arbeidsgeschiktheid, functioneren, perspectief",
                "quality_check": "Is de analyse compleet en onderbouwd?"
            }
        }
    
    def _load_professional_terminology(self) -> Dict[str, Dict[str, List[str]]]:
        """Laad Nederlandse arbeidsdeskundige terminologie"""
        
        return {
            "belastbaarheid": {
                "fysiek": [
                    "fysieke belastbaarheid", "tilcapaciteit", "loopcapaciteit", 
                    "statische houding", "dynamische bewegingen", "uithoudingsvermogen"
                ],
                "mentaal": [
                    "cognitieve belastbaarheid", "concentratievermogen", "geheugen",
                    "planning en organisatie", "probleemoplossend vermogen", "werksnelheid"
                ],
                "sociaal": [
                    "sociale vaardigheden", "communicatieve vaardigheden", "teamwerk",
                    "klantgerichtheid", "conflicthantering", "leiderschap"
                ]
            },
            
            "beperkingen": {
                "functioneel": [
                    "functionele beperkingen", "participatiebelemmeringen", "activiteitenbeperkingen",
                    "stoornissen in het functioneren", "verminderde capaciteit"
                ],
                "tijdelijk": [
                    "tijdelijke beperking", "herstelperiode", "revalidatiefase",
                    "geleidelijk herstel", "progressieve verbetering"
                ],
                "permanent": [
                    "blijvende beperking", "chronische aandoening", "permanente impact",
                    "langdurige gevolgen", "structurele aanpassingen nodig"
                ]
            },
            
            "arbeidsgeschiktheid": {
                "volledig": [
                    "volledig arbeidsgeschikt", "zonder beperkingen inzetbaar",
                    "geschikt voor alle werkzaamheden", "volledige participatie mogelijk"
                ],
                "gedeeltelijk": [
                    "gedeeltelijk arbeidsgeschikt", "met aanpassingen inzetbaar",
                    "beperkt geschikt", "aangepast werk mogelijk"
                ],
                "ongeschikt": [
                    "niet arbeidsgeschikt", "tijdelijk niet inzetbaar",
                    "volledig uitgevallen", "geen arbeidsparticipatie mogelijk"
                ]
            },
            
            "werkhervatting": {
                "gefaseerd": [
                    "gefaseerde werkhervatting", "stapsgewijze opbouw", "geleidelijke toename",
                    "therapeutische werkhervatting", "proefplaatsing"
                ],
                "aangepast": [
                    "aangepast werk", "alternatieve functie", "werkaanpassingen",
                    "functiemodificatie", "taakverlichting"
                ]
            }
        }
    
    def _load_quality_criteria(self) -> Dict[ReportSection, Dict[str, Any]]:
        """Laad kwaliteitscriteria per sectie"""
        
        return {
            ReportSection.MEDISCHE_SITUATIE: {
                "completeness": "Zijn alle relevante medische aspecten behandeld?",
                "relevance": "Is de informatie relevant voor arbeidsgeschiktheid?",
                "accuracy": "Is de medische informatie correct geïnterpreteerd?",
                "clarity": "Is de tekst begrijpelijk voor niet-medici?",
                "min_words": 100,
                "max_words": 400
            },
            
            ReportSection.BELASTBAARHEID: {
                "comprehensiveness": "Zijn alle aspecten van belastbaarheid behandeld?",
                "specificity": "Zijn de bevindingen concreet en meetbaar?",
                "evidence_based": "Zijn conclusies gebaseerd op objectieve informatie?",
                "practical": "Zijn de bevindingen praktisch toepasbaar?",
                "min_words": 200,
                "max_words": 500
            },
            
            ReportSection.ADVIES: {
                "actionability": "Zijn de adviezen concreet uitvoerbaar?",
                "prioritization": "Zijn adviezen geprioriteerd naar urgentie?",
                "stakeholder_clarity": "Is duidelijk wie wat moet doen?",
                "realistic": "Zijn de adviezen realistisch en haalbaar?",
                "min_words": 150,
                "max_words": 400
            },
            
            ReportSection.CONCLUSIE: {
                "clarity": "Is de conclusie helder en ondubbelzinnig?",
                "completeness": "Worden alle hoofdpunten samengevat?",
                "logic": "Volgt de conclusie logisch uit de analyses?",
                "professional": "Is de toon professioneel en objectief?",
                "min_words": 100,
                "max_words": 300
            }
        }
    
    def _adapt_for_document_types(self, template: str, document_types: List[str]) -> str:
        """Pas template aan op basis van beschikbare document types"""
        
        adaptations = []
        
        for doc_type in document_types:
            if doc_type in self.document_guidelines:
                guidelines = self.document_guidelines[doc_type]
                
                adaptation = f"""
SPECIFIEKE AANDACHTSPUNTEN VOOR {doc_type.upper()}:
- Focus: {guidelines['focus']}
- Terminologie: {guidelines['terminology']}
- Kritieke elementen: {guidelines['critical_elements']}
- Kwaliteitscheck: {guidelines['quality_check']}
"""
                adaptations.append(adaptation)
        
        if adaptations:
            adapted_template = template + "\n" + "\n".join(adaptations)
        else:
            adapted_template = template
        
        return adapted_template
    
    def _add_context_instructions(self, template: str, context: PromptContext) -> str:
        """Voeg context-specifieke instructies toe"""
        
        # Analyze available chunks for context
        chunk_summary = self._analyze_chunks(context.available_chunks)
        
        # Add case metadata context
        case_context = self._format_case_metadata(context.case_metadata)
        
        # Add user profile context if available
        profile_context = ""
        if context.user_profile:
            profile_context = self._format_user_profile(context.user_profile)
        
        # Create context variables for template
        context_variables = {
            "context_description": chunk_summary["description"],
            "available_sources": chunk_summary["sources"],
            "medical_sources": chunk_summary["medical_content"],
            "additional_context": chunk_summary["additional_context"],
            "context_information": chunk_summary["full_context"],
            "document_types": ", ".join(context.document_types),
            "limitation_sources": chunk_summary["limitation_content"],
            "opportunity_sources": chunk_summary["opportunity_content"],
            "reintegration_context": chunk_summary["reintegration_content"],
            "comprehensive_context": chunk_summary["comprehensive_summary"],
            "full_context": chunk_summary["complete_analysis"],
            "case_metadata": case_context,
            "user_profile": profile_context
        }
        
        # Replace placeholders in template
        contextualized = template
        for key, value in context_variables.items():
            placeholder = "{" + key + "}"
            if placeholder in contextualized:
                contextualized = contextualized.replace(placeholder, value)
        
        return contextualized
    
    def _analyze_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, str]:
        """Analyseer beschikbare chunks voor context"""
        
        if not chunks:
            return {
                "description": "Geen specifieke documenten beschikbaar voor analyse",
                "sources": "Algemene arbeidsdeskundige kennis",
                "medical_content": "Geen medische informatie beschikbaar",
                "additional_context": "Beperkte contextinformatie beschikbaar",
                "full_context": "Basis arbeidsdeskundige analyse",
                "limitation_content": "Algemene functionele analyse",
                "opportunity_content": "Standaard mogelijkheden analyse",
                "reintegration_content": "Algemene werkhervatting principes",
                "comprehensive_summary": "Beperkte informatie beschikbaar",
                "complete_analysis": "Basis analyse op beschikbare informatie"
            }
        
        # Categorize chunks by type and content
        medical_chunks = []
        assessment_chunks = []
        personal_chunks = []
        other_chunks = []
        
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            doc_type = metadata.get("document_type", "unknown")
            content = chunk.get("content", "")[:500]  # Limit for analysis
            
            if doc_type == "medical_report":
                medical_chunks.append(content)
            elif doc_type == "assessment_report":
                assessment_chunks.append(content)
            elif doc_type == "personal_statement":
                personal_chunks.append(content)
            else:
                other_chunks.append(content)
        
        # Generate summaries
        summary = {
            "description": f"Analyse gebaseerd op {len(chunks)} documenten",
            "sources": self._format_sources_summary(chunks),
            "medical_content": self._format_medical_summary(medical_chunks),
            "additional_context": self._format_additional_context(assessment_chunks, personal_chunks, other_chunks),
            "full_context": self._format_full_context(chunks),
            "limitation_content": self._extract_limitation_content(chunks),
            "opportunity_content": self._extract_opportunity_content(chunks),
            "reintegration_content": self._extract_reintegration_content(chunks),
            "comprehensive_summary": self._create_comprehensive_summary(chunks),
            "complete_analysis": self._create_complete_analysis(chunks)
        }
        
        return summary
    
    def _format_sources_summary(self, chunks: List[Dict[str, Any]]) -> str:
        """Format een samenvatting van beschikbare bronnen"""
        
        source_types = {}
        for chunk in chunks:
            doc_type = chunk.get("metadata", {}).get("document_type", "unknown")
            source_types[doc_type] = source_types.get(doc_type, 0) + 1
        
        source_list = []
        for doc_type, count in source_types.items():
            if doc_type == "medical_report":
                source_list.append(f"Medische rapporten ({count})")
            elif doc_type == "assessment_report":
                source_list.append(f"Arbeidsdeskundige rapporten ({count})")
            elif doc_type == "personal_statement":
                source_list.append(f"Persoonlijke verhalen ({count})")
            elif doc_type == "insurance_document":
                source_list.append(f"Verzekeringsdocumenten ({count})")
            else:
                source_list.append(f"Overige documenten ({count})")
        
        return ", ".join(source_list) if source_list else "Geen specifieke bronnen"
    
    def _format_medical_summary(self, medical_chunks: List[str]) -> str:
        """Format medische informatie samenvatting"""
        
        if not medical_chunks:
            return "Geen medische rapporten beschikbaar voor analyse"
        
        # Extract key medical terms from chunks
        medical_terms = []
        for chunk in medical_chunks:
            chunk_lower = chunk.lower()
            if "diagnose" in chunk_lower:
                medical_terms.append("diagnose informatie")
            if "behandeling" in chunk_lower:
                medical_terms.append("behandeling gegevens")
            if "prognose" in chunk_lower:
                medical_terms.append("prognose informatie")
            if "beperking" in chunk_lower:
                medical_terms.append("functionele beperkingen")
        
        medical_summary = f"Medische informatie uit {len(medical_chunks)} rapport(en)"
        if medical_terms:
            medical_summary += f" bevat: {', '.join(set(medical_terms))}"
        
        # Add sample content (first 200 chars of first chunk)
        if medical_chunks[0]:
            sample = medical_chunks[0][:200] + "..." if len(medical_chunks[0]) > 200 else medical_chunks[0]
            medical_summary += f"\n\nVoorbeeld content:\n{sample}"
        
        return medical_summary
    
    def _format_additional_context(self, assessment_chunks: List[str], 
                                 personal_chunks: List[str], other_chunks: List[str]) -> str:
        """Format aanvullende context informatie"""
        
        context_parts = []
        
        if assessment_chunks:
            context_parts.append(f"Arbeidsdeskundige analyse uit {len(assessment_chunks)} rapport(en)")
        
        if personal_chunks:
            context_parts.append(f"Persoonlijke ervaringen uit {len(personal_chunks)} verhaal/verhalen")
        
        if other_chunks:
            context_parts.append(f"Aanvullende informatie uit {len(other_chunks)} document(en)")
        
        return "; ".join(context_parts) if context_parts else "Beperkte aanvullende context beschikbaar"
    
    def _format_full_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format volledige context voor analyse"""
        
        context_summary = f"Totaal {len(chunks)} documenten beschikbaar voor analyse.\n\n"
        
        # Group by importance
        critical_chunks = [c for c in chunks if c.get("metadata", {}).get("importance") == "critical"]
        high_chunks = [c for c in chunks if c.get("metadata", {}).get("importance") == "high"]
        
        if critical_chunks:
            context_summary += f"Kritieke informatie ({len(critical_chunks)} chunks):\n"
            for chunk in critical_chunks[:3]:  # Max 3 examples
                content_preview = chunk.get("content", "")[:150]
                section_type = chunk.get("metadata", {}).get("section_type", "algemeen")
                context_summary += f"- {section_type}: {content_preview}...\n"
        
        if high_chunks:
            context_summary += f"\nBelangrijke informatie ({len(high_chunks)} chunks):\n"
            for chunk in high_chunks[:2]:  # Max 2 examples
                content_preview = chunk.get("content", "")[:100]
                section_type = chunk.get("metadata", {}).get("section_type", "algemeen")
                context_summary += f"- {section_type}: {content_preview}...\n"
        
        return context_summary
    
    def _extract_limitation_content(self, chunks: List[Dict[str, Any]]) -> str:
        """Extraheer content relevant voor beperkingen"""
        
        limitation_keywords = ["beperking", "limitatie", "niet mogelijk", "probleem", "klacht"]
        relevant_chunks = []
        
        for chunk in chunks:
            content = chunk.get("content", "").lower()
            if any(keyword in content for keyword in limitation_keywords):
                relevant_chunks.append(chunk.get("content", "")[:200])
        
        if relevant_chunks:
            return f"Relevante informatie over beperkingen uit {len(relevant_chunks)} bron(nen):\n\n" + "\n\n".join(relevant_chunks)
        else:
            return "Geen specifieke informatie over beperkingen gevonden in de beschikbare documenten"
    
    def _extract_opportunity_content(self, chunks: List[Dict[str, Any]]) -> str:
        """Extraheer content relevant voor mogelijkheden"""
        
        opportunity_keywords = ["mogelijk", "geschikt", "kan", "in staat", "capaciteit", "kans"]
        relevant_chunks = []
        
        for chunk in chunks:
            content = chunk.get("content", "").lower()
            if any(keyword in content for keyword in opportunity_keywords):
                relevant_chunks.append(chunk.get("content", "")[:200])
        
        if relevant_chunks:
            return f"Relevante informatie over mogelijkheden uit {len(relevant_chunks)} bron(nen):\n\n" + "\n\n".join(relevant_chunks)
        else:
            return "Geen specifieke informatie over mogelijkheden gevonden in de beschikbare documenten"
    
    def _extract_reintegration_content(self, chunks: List[Dict[str, Any]]) -> str:
        """Extraheer content relevant voor werkhervatting"""
        
        reintegration_keywords = ["werkhervatting", "werk", "functie", "re-integratie", "herstel", "terugkeer"]
        relevant_chunks = []
        
        for chunk in chunks:
            content = chunk.get("content", "").lower()
            if any(keyword in content for keyword in reintegration_keywords):
                relevant_chunks.append(chunk.get("content", "")[:200])
        
        if relevant_chunks:
            return f"Relevante informatie over werkhervatting uit {len(relevant_chunks)} bron(nen):\n\n" + "\n\n".join(relevant_chunks)
        else:
            return "Geen specifieke informatie over werkhervatting gevonden in de beschikbare documenten"
    
    def _create_comprehensive_summary(self, chunks: List[Dict[str, Any]]) -> str:
        """Maak een uitgebreide samenvatting van alle beschikbare informatie"""
        
        summary = f"UITGEBREIDE ANALYSE van {len(chunks)} documenten:\n\n"
        
        # Group by document type
        doc_groups = {}
        for chunk in chunks:
            doc_type = chunk.get("metadata", {}).get("document_type", "unknown")
            if doc_type not in doc_groups:
                doc_groups[doc_type] = []
            doc_groups[doc_type].append(chunk)
        
        for doc_type, type_chunks in doc_groups.items():
            summary += f"{doc_type.upper()} ({len(type_chunks)} chunks):\n"
            
            # Get most important content
            for chunk in type_chunks[:2]:  # Max 2 per type
                content_preview = chunk.get("content", "")[:250]
                importance = chunk.get("metadata", {}).get("importance", "medium")
                summary += f"- [{importance}] {content_preview}...\n"
            
            summary += "\n"
        
        return summary
    
    def _create_complete_analysis(self, chunks: List[Dict[str, Any]]) -> str:
        """Maak een complete analyse van alle beschikbare informatie"""
        
        analysis = "COMPLETE ANALYSE:\n\n"
        
        # Statistical overview
        total_chunks = len(chunks)
        doc_types = set(chunk.get("metadata", {}).get("document_type", "unknown") for chunk in chunks)
        importance_levels = [chunk.get("metadata", {}).get("importance", "medium") for chunk in chunks]
        
        analysis += f"OVERZICHT:\n"
        analysis += f"- Totaal chunks: {total_chunks}\n"
        analysis += f"- Document types: {', '.join(doc_types)}\n"
        analysis += f"- Kritieke chunks: {importance_levels.count('critical')}\n"
        analysis += f"- Belangrijke chunks: {importance_levels.count('high')}\n\n"
        
        # Key content areas
        analysis += "INHOUDELIJKE GEBIEDEN:\n"
        
        content_areas = {
            "Medisch": ["diagnose", "behandeling", "prognose", "medisch"],
            "Functioneel": ["beperking", "mogelijk", "capaciteit", "functioneren"],
            "Arbeidskundig": ["werk", "functie", "belastbaar", "geschikt"],
            "Persoonlijk": ["ervaring", "gevoel", "impact", "dagelijks"]
        }
        
        for area, keywords in content_areas.items():
            relevant_count = 0
            for chunk in chunks:
                content = chunk.get("content", "").lower()
                if any(keyword in content for keyword in keywords):
                    relevant_count += 1
            
            if relevant_count > 0:
                analysis += f"- {area}: {relevant_count} relevante chunks\n"
        
        analysis += "\nDeze informatie vormt de basis voor de arbeidsdeskundige analyse."
        
        return analysis
    
    def _format_case_metadata(self, case_metadata: Dict[str, Any]) -> str:
        """Format case metadata voor context"""
        
        if not case_metadata:
            return "Geen case metadata beschikbaar"
        
        context = "CASE INFORMATIE:\n"
        
        if "title" in case_metadata:
            context += f"Case: {case_metadata['title']}\n"
        
        if "description" in case_metadata:
            context += f"Beschrijving: {case_metadata['description']}\n"
        
        if "created_at" in case_metadata:
            context += f"Aangemaakt: {case_metadata['created_at']}\n"
        
        return context
    
    def _format_user_profile(self, user_profile: Dict[str, Any]) -> str:
        """Format user profile voor context"""
        
        if not user_profile:
            return ""
        
        profile_context = "GEBRUIKERSPROFIEL:\n"
        
        if "display_name" in user_profile:
            profile_context += f"Arbeidsdeskundige: {user_profile['display_name']}\n"
        
        if "company_name" in user_profile:
            profile_context += f"Organisatie: {user_profile['company_name']}\n"
        
        if "specializations" in user_profile and user_profile["specializations"]:
            profile_context += f"Specialisaties: {', '.join(user_profile['specializations'])}\n"
        
        return profile_context
    
    def _adjust_for_complexity(self, prompt: str, complexity: ComplexityLevel) -> str:
        """Pas prompt aan voor complexiteitsniveau"""
        
        complexity_adjustments = {
            ComplexityLevel.BASIC: {
                "instruction": "\nGEBRUIK EEN EENVOUDIGE, TOEGANKELIJKE SCHRIJFSTIJL:\n- Korte zinnen\n- Duidelijke taal\n- Vermijd jargon\n- Concrete voorbeelden\n",
                "length_modifier": "Houd het beknopt (150-250 woorden)."
            },
            
            ComplexityLevel.MEDIUM: {
                "instruction": "\nGEBRUIK EEN PROFESSIONELE MAAR TOEGANKELIJKE SCHRIJFSTIJL:\n- Heldere structuur\n- Passende terminologie\n- Balans tussen detail en overzicht\n",
                "length_modifier": "Streef naar 200-400 woorden."
            },
            
            ComplexityLevel.COMPLEX: {
                "instruction": "\nGEBRUIK EEN GEDETAILLEERDE, PROFESSIONELE SCHRIJFSTIJL:\n- Uitgebreide analyse\n- Vakterminologie waar passend\n- Nuancering en context\n- Onderbouwing van conclusies\n",
                "length_modifier": "Uitgebreide analyse (300-600 woorden)."
            },
            
        }
        
        if complexity in complexity_adjustments:
            adjustment = complexity_adjustments[complexity]
            adjusted_prompt = prompt + adjustment["instruction"] + adjustment["length_modifier"]
        else:
            adjusted_prompt = prompt
        
        return adjusted_prompt
    
    def _generate_quality_indicators(self, context: PromptContext) -> Dict[str, Any]:
        """Genereer kwaliteitsindicatoren voor de prompt"""
        
        section_criteria = self.quality_criteria.get(context.section, {})
        
        return {
            "section": context.section.value,
            "document_types_count": len(context.document_types),
            "chunks_available": len(context.available_chunks),
            "complexity_level": context.complexity_level.value,
            "expected_criteria": section_criteria,
            "context_richness": "high" if len(context.available_chunks) > 5 else "medium" if len(context.available_chunks) > 2 else "low",
            "domain_coverage": self._assess_domain_coverage(context.available_chunks)
        }
    
    def _assess_domain_coverage(self, chunks: List[Dict[str, Any]]) -> Dict[str, int]:
        """Assess welke domeinen gedekt zijn door de chunks"""
        
        domains = {
            "medical": 0,
            "functional": 0,
            "personal": 0,
            "legal": 0,
            "work_related": 0
        }
        
        for chunk in chunks:
            content = chunk.get("content", "").lower()
            doc_type = chunk.get("metadata", {}).get("document_type", "")
            
            if doc_type == "medical_report" or any(word in content for word in ["medisch", "diagnose", "behandeling"]):
                domains["medical"] += 1
            
            if any(word in content for word in ["functioneel", "beperking", "mogelijkheid", "capaciteit"]):
                domains["functional"] += 1
            
            if doc_type == "personal_statement" or any(word in content for word in ["ervaring", "gevoel", "beleving"]):
                domains["personal"] += 1
            
            if doc_type == "legal_document" or any(word in content for word in ["juridisch", "rechtbank", "wet"]):
                domains["legal"] += 1
            
            if any(word in content for word in ["werk", "functie", "arbeidsdeskundig", "belastbaar"]):
                domains["work_related"] += 1
        
        return domains
    
    def _generate_fallback_prompt(self, context: PromptContext) -> GeneratedPrompt:
        """Genereer een fallback prompt bij fouten"""
        
        fallback_prompt = f"""
Je bent een ervaren arbeidsdeskundige die een {context.section.value} sectie schrijft voor een arbeidsdeskundig rapport.

Gebruik je professionele kennis en ervaring om een kwalitatief goede {context.section.value} te schrijven, 
ook al is er beperkte specifieke informatie beschikbaar.

Zorg voor:
- Professionele toon en terminologie
- Heldere structuur en argumentatie
- Praktische en uitvoerbare adviezen
- Objectieve en onderbouwde conclusies

Schrijf de {context.section.value}:
"""
        
        return GeneratedPrompt(
            prompt_text=fallback_prompt,
            section=context.section,
            context_sources=["fallback"],
            complexity_level=context.complexity_level,
            quality_indicators={"status": "fallback_generated"},
            generation_timestamp=datetime.utcnow().isoformat()
        )
    
    def analyze_context(
        self, 
        context_chunks: List[str], 
        section: ReportSection = None,
        document_type: Optional['DocumentType'] = None
    ) -> Dict[str, Any]:
        """
        Analyseer context chunks voor betere prompt generatie
        """
        if not context_chunks:
            return {
                "total_chunks": 0,
                "total_length": 0,
                "key_terms": [],
                "section_relevance": "unknown",
                "recommendations": []
            }
        
        total_length = sum(len(chunk) for chunk in context_chunks)
        combined_text = " ".join(context_chunks).lower()
        
        # Extract key medical/legal terms
        key_terms = []
        medical_terms = ["diagnose", "behandeling", "medicatie", "arts", "specialist", "onderzoek"]
        legal_terms = ["arbeidscontract", "ontslag", "verzuim", "re-integratie", "arbeidsrecht"]
        capacity_terms = ["belastbaarheid", "beperkingen", "capaciteit", "mogelijkheden"]
        
        for term in medical_terms + legal_terms + capacity_terms:
            if term in combined_text:
                key_terms.append(term)
        
        # Section relevance
        section_relevance = "medium"
        if section:
            section_keywords = {
                ReportSection.MEDISCHE_SITUATIE: medical_terms,
                ReportSection.BELASTBAARHEID: capacity_terms,
                ReportSection.BEPERKINGEN: capacity_terms + ["beperking", "limitatie"],
                ReportSection.ADVIES: ["advies", "aanbeveling", "conclusie"]
            }
            
            relevant_terms = section_keywords.get(section, [])
            matches = sum(1 for term in relevant_terms if term in combined_text)
            
            if matches >= 3:
                section_relevance = "high"
            elif matches >= 1:
                section_relevance = "medium"
            else:
                section_relevance = "low"
        
        return {
            "total_chunks": len(context_chunks),
            "total_length": total_length,
            "key_terms": key_terms,
            "section_relevance": section_relevance,
            "recommendations": [
                f"Focus op {', '.join(key_terms[:3])}" if key_terms else "Gebruik algemene arbeidsdeskundige terminologie",
                f"Context relevantie voor sectie: {section_relevance}"
            ]
        }
    
    def get_quality_criteria(
        self, 
        section: ReportSection, 
        complexity_level: ComplexityLevel
    ) -> List[str]:
        """
        Krijg kwaliteitscriteria voor een specifieke sectie en complexiteit
        """
        base_criteria = {
            ReportSection.INTRODUCTIE: [
                "Duidelijke probleemstelling",
                "Relevante achtergrond informatie",
                "Scope en methodiek vermeld"
            ],
            ReportSection.MEDISCHE_SITUATIE: [
                "Objectieve medische feiten",
                "Chronologische volgorde",
                "Relevante diagnoses en behandelingen",
                "Prognose indien beschikbaar"
            ],
            ReportSection.BELASTBAARHEID: [
                "Fysieke en mentale aspecten",
                "Concrete capaciteiten genoemd",
                "FCE resultaten indien beschikbaar",
                "Onderbouwing met medische informatie"
            ],
            ReportSection.BEPERKINGEN: [
                "Specifieke functionele beperkingen",
                "Tijdsduur en intensiteit",
                "Impact op werkzaamheden",
                "Onderbouwing vanuit medische situatie"
            ],
            ReportSection.ADVIES: [
                "Concrete en uitvoerbare stappen",
                "Prioritering van interventies",
                "Tijdslijn en verwachtingen",
                "Verantwoordelijkheden benoemd"
            ],
            ReportSection.CONCLUSIE: [
                "Samenvatting kernpunten",
                "Helder eindoordeel",
                "Vervolgstappen gedefinieerd",
                "Realistische prognose"
            ]
        }
        
        section_criteria = base_criteria.get(section, [
            "Professionele toon",
            "Feitelijke informatie",
            "Heldere structuur"
        ])
        
        # Add complexity-specific criteria
        if complexity_level == ComplexityLevel.COMPLEX:
            section_criteria.extend([
                "Uitgebreide analyse en onderbouwing",
                "Vakterminologie correct gebruikt",
                "Nuancering waar nodig"
            ])
        elif complexity_level == ComplexityLevel.BASIC:
            section_criteria.extend([
                "Eenvoudige en heldere taal",
                "Kernpunten prioriteren",
                "Praktische focus"
            ])
        
        return section_criteria