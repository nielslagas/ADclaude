"""
Structured Output Generator for AI-Arbeidsdeskundige
Provides structured JSON output for flexible multi-format report generation
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import json
from pydantic import BaseModel, Field
from app.core.config import settings
from app.utils.llm_provider import create_llm_instance

class ContentType(str, Enum):
    """Types of content elements in structured output"""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    ASSESSMENT = "assessment"
    QUOTE = "quote"
    RECOMMENDATION = "recommendation"
    CONCLUSION = "conclusion"
    
class Priority(str, Enum):
    """Priority levels for recommendations and actions"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CRITICAL = "critical"

class ListStyle(str, Enum):
    """List formatting styles"""
    BULLET = "bullet"
    NUMBERED = "numbered"
    DASH = "dash"
    CHECKMARK = "checkmark"

# Pydantic models for structured output
class TextElement(BaseModel):
    """Basic text element with optional formatting"""
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    
class ListItem(BaseModel):
    """Structured list item with optional label-value pairs"""
    label: Optional[str] = None
    value: str
    detail: Optional[str] = None
    
class TableRow(BaseModel):
    """Table row structure"""
    cells: List[str]
    
class ContentElement(BaseModel):
    """Base content element structure"""
    type: ContentType
    content: Any  # Will be refined based on type
    metadata: Optional[Dict[str, Any]] = None

class FMLRubriekItem(BaseModel):
    """FML (Functionele Mogelijkhedenlijst) rubriek item"""
    rubriek_nummer: str  # I, II, III, IV, V, VI
    rubriek_naam: str  # Persoonlijk functioneren, etc.
    mate_van_beperking: Optional[str] = None  # Beperkt/Niet beperkt
    beschrijving: str  # Detailed description
    nummer: Optional[str] = None  # Sub-item number (e.g., "2.", "6.")
    specifieke_aspecten: Optional[List[str]] = None  # Specific aspects
    voorwaarden: Optional[List[str]] = None  # Conditions/requirements

class AssessmentItem(BaseModel):
    """Structured assessment item for belastbaarheid"""
    category: str  # fysiek, mentaal, sociaal
    aspect: str  # tillen, concentratie, etc.
    capacity: str  # wat kan de persoon
    frequency: Optional[str] = None  # hoe vaak
    limitation: Optional[str] = None  # beperkingen
    notes: Optional[str] = None  # extra notities
    fml_rubrieken: Optional[List[FMLRubriekItem]] = None  # FML structure
    
class Recommendation(BaseModel):
    """Structured recommendation"""
    priority: Priority
    action: str
    rationale: Optional[str] = None
    timeline: Optional[str] = None
    responsible_party: Optional[str] = None

class SectionContent(BaseModel):
    """Complete section with structured content"""
    section_id: str
    title: str
    summary: str
    main_content: List[ContentElement]
    conclusions: Optional[List[str]] = None
    recommendations: Optional[List[Recommendation]] = None
    metadata: Optional[Dict[str, Any]] = None

# Section-specific schemas
SECTION_SCHEMAS = {
    "persoonsgegevens": {
        "required_fields": ["naam", "geboortedatum", "adres", "telefoonnummer"],
        "optional_fields": ["email", "bsn", "verzekeraar"],
        "output_format": "structured_data"
    },
    "belastbaarheid": {
        "fml_rubrieken": {
            "I": {
                "naam": "Persoonlijk functioneren",
                "aspecten": [
                    "Verdelen van de aandacht",
                    "Concentratie",
                    "Werktempo",
                    "Plannen van werkzaamheden",
                    "Omgaan met stress"
                ]
            },
            "II": {
                "naam": "Sociaal functioneren", 
                "aspecten": [
                    "Emotionele problemen van anderen hanteren",
                    "Omgaan met conflicten",
                    "Leidinggeven",
                    "Instructies opvolgen",
                    "Samenwerken"
                ]
            },
            "III": {
                "naam": "Aanpassing aan fysieke omgevingseisen",
                "aspecten": [
                    "Geluid",
                    "Trillingen", 
                    "Temperatuur",
                    "Vochtigheid",
                    "Luchtverontreiniging"
                ]
            },
            "IV": {
                "naam": "Dynamische handelingen",
                "aspecten": [
                    "Tillen",
                    "Dragen",
                    "Duwen/trekken",
                    "Bukken/hurken",
                    "Reiken"
                ]
            },
            "V": {
                "naam": "Statische houdingen",
                "aspecten": [
                    "Zitten",
                    "Staan",
                    "Lopen",
                    "Knielen/hurken"
                ]
            },
            "VI": {
                "naam": "Werktijden",
                "aspecten": [
                    "Uren van de dag",
                    "Uren van de week",
                    "Energetische beperking",
                    "Nachtdiensten",
                    "Flexibiliteit werktijden"
                ]
            }
        },
        "output_format": "fml_assessment"
    },
    "visie_ad": {
        "structure": [
            "situatie_analyse",
            "arbeidsmogelijkheden",
            "beperkingen_impact",
            "re_integratie_perspectief",
            "advies"
        ],
        "output_format": "narrative_structured"
    },
    "matching": {
        "criteria_categories": [
            "fysieke_werkomgeving",
            "taakinhoud",
            "werktijden",
            "sociale_omgeving",
            "randvoorwaarden"
        ],
        "priority_marking": True,
        "output_format": "criteria_list"
    }
}

class StructuredOutputGenerator:
    """Generate structured output from LLM responses"""
    
    def __init__(self):
        self.llm_provider = settings.LLM_PROVIDER
        
    async def generate_structured_section(
        self, 
        section_id: str, 
        prompt: str,
        context: str,
        user_profile: Optional[Dict] = None
    ) -> SectionContent:
        """
        Generate structured content for a specific section
        
        Args:
            section_id: ID of the section (e.g., 'belastbaarheid')
            prompt: Base prompt for the section
            context: Document context for generation
            user_profile: Optional user profile information
            
        Returns:
            Structured section content
        """
        
        # Get section-specific schema
        schema = SECTION_SCHEMAS.get(section_id, {})
        output_format = schema.get("output_format", "narrative")
        
        # Create structured prompt based on output format
        if output_format == "fml_assessment":
            return await self._generate_fml_section(section_id, prompt, context)
        elif output_format == "assessment_matrix":
            return await self._generate_assessment_section(section_id, prompt, context)
        elif output_format == "criteria_list":
            return await self._generate_criteria_section(section_id, prompt, context)
        elif output_format == "structured_data":
            return await self._generate_data_section(section_id, prompt, context)
        else:
            return await self._generate_narrative_section(section_id, prompt, context)
    
    async def _generate_fml_section(
        self, 
        section_id: str, 
        prompt: str, 
        context: str
    ) -> SectionContent:
        """Generate FML (Functionele Mogelijkhedenlijst) structured assessment"""
        
        schema = SECTION_SCHEMAS.get(section_id, {})
        fml_rubrieken = schema.get("fml_rubrieken", {})
        
        structured_prompt = f"""
        {prompt}
        
        BELANGRIJK: Genereer een FML (Functionele Mogelijkhedenlijst) analyse in markdown formaat.
        
        Gebruik de volgende structuur:
        
        **3.4 Belastbaarheid van werknemer**
        
        De belastbaarheid is door bedrijfsarts [naam bedrijfsarts] weergegeven in een functionelemogelijkhedenlijst (FML). 
        Uit de FML van werknemer blijkt dat de belastbaarheid in vergelijking met een gezond persoon tussen 16 en 65 jaar 
        beperkt is op de volgende aspecten:
        
        **Rubriek I: Persoonlijk functioneren**
        Mate van beperking: [Beperkt/Niet beperkt]
        [Nummer]. [Specifiek aspect]: [Beschrijving van beperking en voorwaarden]
        [Specifieke voorwaarden indien van toepassing]
        
        **Rubriek II: Sociaal functioneren**
        Mate van beperking: [Beperkt/Niet beperkt]
        [Nummer]. [Specifiek aspect]: [Beschrijving]
        
        **Rubriek III: Aanpassing aan fysieke omgevingseisen**
        [Niet beperkt / of beschrijving van beperkingen]
        
        **Rubriek IV: Dynamische handelingen**
        [Niet beperkt / of beschrijving van beperkingen]
        
        **Rubriek V: Statische houdingen**
        [Niet beperkt / of beschrijving van beperkingen]
        
        **Rubriek VI: Werktijden**
        [Beschrijving van beperkingen in werktijden, energetische beperking, nachtdiensten, etc.]
        
        [Optionele prognose paragraaf over belastbaarheid]
        
        Context documenten:
        {context}
        """
        
        try:
            response = await self._generate_with_structure(structured_prompt)
            return SectionContent(
                section_id=section_id,
                title="3.4 Belastbaarheid van werknemer",
                summary="FML belastbaarheidsanalyse",
                main_content=[ContentElement(
                    type=ContentType.PARAGRAPH,
                    content=response
                )],
                metadata={"format": "fml", "rubrieken": list(fml_rubrieken.keys())}
            )
        except Exception as e:
            return await self._generate_narrative_section(section_id, prompt, context)
    
    async def _generate_assessment_section(
        self, 
        section_id: str, 
        prompt: str, 
        context: str
    ) -> SectionContent:
        """Generate assessment matrix (for belastbaarheid)"""
        
        # Enhanced prompt for structured assessment output
        structured_prompt = f"""
        {prompt}
        
        BELANGRIJK: Genereer een gestructureerde belastbaarheidsanalyse in JSON formaat.
        
        Voor elke categorie (fysiek, mentaal, sociaal), geef per aspect:
        - capacity: wat kan de persoon (specifiek, met getallen waar mogelijk)
        - frequency: hoe vaak (dagelijks, wekelijks, incidenteel)
        - limitation: beperkingen of aandachtspunten
        - notes: aanvullende opmerkingen
        
        Gebruik het volgende JSON schema:
        {{
            "summary": "korte samenvatting van belastbaarheid",
            "fysiek": {{
                "tillen": {{"capacity": "max 10kg", "frequency": "incidenteel", "limitation": "rugklachten"}},
                "zitten": {{"capacity": "4 uur", "frequency": "dagelijks", "limitation": "met pauzes"}}
            }},
            "mentaal": {{
                "concentratie": {{"capacity": "goed", "frequency": "volledig", "limitation": "geen"}}
            }},
            "sociaal": {{
                "samenwerking": {{"capacity": "uitstekend", "frequency": "dagelijks", "limitation": "geen"}}
            }},
            "conclusions": ["conclusie 1", "conclusie 2"],
            "recommendations": [
                {{"priority": "high", "action": "ergonomische aanpassingen"}}
            ]
        }}
        
        Context documenten:
        {context}
        """
        
        # Use function calling if available, otherwise parse JSON response
        try:
            response = await self._generate_with_structure(structured_prompt)
            return self._parse_assessment_response(section_id, response)
        except Exception as e:
            # Fallback to narrative if structured generation fails
            return await self._generate_narrative_section(section_id, prompt, context)
    
    async def _generate_criteria_section(
        self, 
        section_id: str, 
        prompt: str, 
        context: str
    ) -> SectionContent:
        """Generate criteria list (for matching)"""
        
        structured_prompt = f"""
        {prompt}
        
        BELANGRIJK: Genereer matchingcriteria in gestructureerd JSON formaat.
        
        Voor elke categorie, geef criteria met prioriteit (critical/high/medium/low):
        
        {{
            "summary": "overzicht van matchingcriteria",
            "fysieke_werkomgeving": [
                {{"criterion": "toegankelijke werkplek", "priority": "critical", "details": "rolstoeltoegankelijk"}},
                {{"criterion": "ergonomische inrichting", "priority": "high", "details": "verstelbaar bureau"}}
            ],
            "taakinhoud": [
                {{"criterion": "geen zwaar tilwerk", "priority": "critical", "details": "max 5kg"}},
                {{"criterion": "afwisselende taken", "priority": "medium", "details": "variatie in werkzaamheden"}}
            ],
            "werktijden": [
                {{"criterion": "flexibele uren", "priority": "high", "details": "tussen 8-18 uur"}}
            ],
            "conclusions": ["conclusie over matching"],
            "suitable_functions": ["functie 1", "functie 2"]
        }}
        
        Context documenten:
        {context}
        """
        
        try:
            response = await self._generate_with_structure(structured_prompt)
            return self._parse_criteria_response(section_id, response)
        except Exception as e:
            return await self._generate_narrative_section(section_id, prompt, context)
    
    async def _generate_narrative_section(
        self, 
        section_id: str, 
        prompt: str, 
        context: str
    ) -> SectionContent:
        """Generate narrative section with light structure"""
        
        structured_prompt = f"""
        {prompt}
        
        Structureer je antwoord als volgt:
        
        1. SAMENVATTING (1-2 zinnen)
        2. HOOFDTEKST (gebruik paragr, afen, bullets waar nodig)
        3. CONCLUSIES (3-5 punten)
        4. AANBEVELINGEN (indien relevant)
        
        Markeer belangrijke onderdelen met **bold** en gebruik - voor bullets.
        
        Context documenten:
        {context}
        """
        
        response = await self._generate_text(structured_prompt)
        return self._parse_narrative_response(section_id, response)
    
    async def _generate_with_structure(self, prompt: str) -> Dict:
        """Generate response with structured output (JSON)"""
        
        # Try to use function calling for structured output
        if self.llm_provider in ["openai", "anthropic"]:
            return await self._generate_with_function_calling(prompt)
        else:
            # For other providers, parse JSON from text response
            response = await self._generate_text(prompt + "\n\nRETURN ONLY VALID JSON")
            return self._extract_json_from_text(response)
    
    async def _generate_with_function_calling(self, prompt: str) -> Dict:
        """Use function calling for guaranteed structured output"""
        
        # This would use provider-specific function calling
        # For now, fall back to JSON parsing
        response = await self._generate_text(prompt)
        return self._extract_json_from_text(response)
    
    async def _generate_text(self, prompt: str) -> str:
        """Generate text response from LLM"""
        
        llm = create_llm_instance(
            temperature=0.3,  # Lower temperature for more consistent structure
            max_tokens=3000
        )
        
        response = llm.generate_content([
            {"role": "system", "parts": ["Je bent een arbeidsdeskundige die gestructureerde rapporten maakt."]},
            {"role": "user", "parts": [prompt]}
        ])
        
        return response.text
    
    def _extract_json_from_text(self, text: str) -> Dict:
        """Extract JSON from text response"""
        
        # Try to find JSON in the text
        import re
        
        # Look for JSON blocks
        json_pattern = r'\{[^{}]*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except:
                continue
        
        # If no JSON found, create structured data from text
        return self._structure_text_fallback(text)
    
    def _structure_text_fallback(self, text: str) -> Dict:
        """Create structured data from unstructured text"""
        
        lines = text.split('\n')
        structured = {
            "summary": "",
            "content": [],
            "conclusions": [],
            "recommendations": []
        }
        
        current_section = "content"
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect sections
            if "samenvatting" in line.lower() or "summary" in line.lower():
                current_section = "summary"
            elif "conclusie" in line.lower():
                current_section = "conclusions"
            elif "aanbeveling" in line.lower() or "advies" in line.lower():
                current_section = "recommendations"
            else:
                # Add to current section
                if current_section == "summary" and not structured["summary"]:
                    structured["summary"] = line
                elif current_section == "conclusions":
                    structured["conclusions"].append(line)
                elif current_section == "recommendations":
                    structured["recommendations"].append(line)
                else:
                    structured["content"].append(line)
        
        return structured
    
    def _parse_assessment_response(self, section_id: str, data: Dict) -> SectionContent:
        """Parse assessment response into structured content"""
        
        content_elements = []
        
        # Add summary
        if "summary" in data:
            content_elements.append(ContentElement(
                type=ContentType.PARAGRAPH,
                content=data["summary"]
            ))
        
        # Process each category
        for category in ["fysiek", "mentaal", "sociaal"]:
            if category in data:
                # Create assessment table
                assessments = []
                for aspect, details in data[category].items():
                    assessments.append(AssessmentItem(
                        category=category,
                        aspect=aspect,
                        capacity=details.get("capacity", ""),
                        frequency=details.get("frequency", ""),
                        limitation=details.get("limitation", ""),
                        notes=details.get("notes", "")
                    ))
                
                content_elements.append(ContentElement(
                    type=ContentType.ASSESSMENT,
                    content=assessments,
                    metadata={"category": category}
                ))
        
        # Process recommendations
        recommendations = []
        if "recommendations" in data:
            for rec in data["recommendations"]:
                if isinstance(rec, dict):
                    recommendations.append(Recommendation(
                        priority=Priority(rec.get("priority", "medium")),
                        action=rec.get("action", ""),
                        rationale=rec.get("rationale", "")
                    ))
        
        return SectionContent(
            section_id=section_id,
            title=self._get_section_title(section_id),
            summary=data.get("summary", ""),
            main_content=content_elements,
            conclusions=data.get("conclusions", []),
            recommendations=recommendations
        )
    
    def _parse_criteria_response(self, section_id: str, data: Dict) -> SectionContent:
        """Parse criteria response into structured content"""
        
        content_elements = []
        
        # Add summary
        if "summary" in data:
            content_elements.append(ContentElement(
                type=ContentType.PARAGRAPH,
                content=data["summary"]
            ))
        
        # Process criteria categories
        for category in ["fysieke_werkomgeving", "taakinhoud", "werktijden", "sociale_omgeving", "randvoorwaarden"]:
            if category in data:
                criteria_list = []
                for criterion in data[category]:
                    if isinstance(criterion, dict):
                        criteria_list.append(ListItem(
                            label=f"[{criterion.get('priority', 'M').upper()[0]}]",
                            value=criterion.get("criterion", ""),
                            detail=criterion.get("details", "")
                        ))
                
                if criteria_list:
                    content_elements.append(ContentElement(
                        type=ContentType.LIST,
                        content=criteria_list,
                        metadata={"category": category, "style": ListStyle.BULLET}
                    ))
        
        # Add suitable functions if present
        if "suitable_functions" in data:
            content_elements.append(ContentElement(
                type=ContentType.LIST,
                content=[ListItem(value=func) for func in data["suitable_functions"]],
                metadata={"title": "Geschikte functies", "style": ListStyle.NUMBERED}
            ))
        
        return SectionContent(
            section_id=section_id,
            title=self._get_section_title(section_id),
            summary=data.get("summary", ""),
            main_content=content_elements,
            conclusions=data.get("conclusions", [])
        )
    
    def _parse_narrative_response(self, section_id: str, text: str) -> SectionContent:
        """Parse narrative text into light structure"""
        
        lines = text.split('\n')
        content_elements = []
        summary = ""
        conclusions = []
        recommendations = []
        
        current_mode = "content"
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            
            # Detect mode changes
            if "SAMENVATTING" in line or (not summary and len(line) < 200 and "samenvatting" in line.lower()):
                current_mode = "summary"
                continue
            elif "CONCLUSIE" in line or "Conclusie" in line:
                current_mode = "conclusions"
                continue
            elif "AANBEVELING" in line or "Aanbeveling" in line:
                current_mode = "recommendations"
                continue
            
            # Process based on mode
            if current_mode == "summary" and not summary:
                summary = line
            elif current_mode == "conclusions":
                if line.startswith('-') or line.startswith('•'):
                    conclusions.append(line[1:].strip())
                elif line:
                    conclusions.append(line)
            elif current_mode == "recommendations":
                if line.startswith('-') or line.startswith('•'):
                    recommendations.append(Recommendation(
                        priority=Priority.MEDIUM,
                        action=line[1:].strip()
                    ))
                elif line:
                    recommendations.append(Recommendation(
                        priority=Priority.MEDIUM,
                        action=line
                    ))
            else:
                # Regular content
                if not line:
                    # End of paragraph
                    if current_paragraph:
                        content_elements.append(ContentElement(
                            type=ContentType.PARAGRAPH,
                            content=' '.join(current_paragraph)
                        ))
                        current_paragraph = []
                elif line.startswith('-') or line.startswith('•'):
                    # List item
                    if current_paragraph:
                        content_elements.append(ContentElement(
                            type=ContentType.PARAGRAPH,
                            content=' '.join(current_paragraph)
                        ))
                        current_paragraph = []
                    
                    # Start collecting list items
                    list_items = [ListItem(value=line[1:].strip())]
                    # Check for more list items
                    # (would need to look ahead in lines)
                    content_elements.append(ContentElement(
                        type=ContentType.LIST,
                        content=list_items,
                        metadata={"style": ListStyle.BULLET}
                    ))
                else:
                    current_paragraph.append(line)
        
        # Add remaining paragraph
        if current_paragraph:
            content_elements.append(ContentElement(
                type=ContentType.PARAGRAPH,
                content=' '.join(current_paragraph)
            ))
        
        return SectionContent(
            section_id=section_id,
            title=self._get_section_title(section_id),
            summary=summary or "Geen samenvatting beschikbaar",
            main_content=content_elements,
            conclusions=conclusions,
            recommendations=recommendations if recommendations else None
        )
    
    def _get_section_title(self, section_id: str) -> str:
        """Get section title from ID"""
        
        titles = {
            "persoonsgegevens": "Persoonsgegevens",
            "werkgever_functie": "Werkgever en Functie",
            "aanleiding": "Aanleiding Onderzoek",
            "arbeidsverleden": "Arbeidsverleden en Opleidingsachtergrond",
            "medische_situatie": "Medische Situatie",
            "belastbaarheid": "Belastbaarheid",
            "belasting_huidige_functie": "Belasting Huidige Functie",
            "visie_ad": "Visie Arbeidsdeskundige",
            "matching": "Matching Overwegingen",
            "conclusie": "Conclusie en Advies",
            "samenvatting": "Samenvatting"
        }
        
        return titles.get(section_id, section_id.replace('_', ' ').title())

# Export formatter for different output formats
class OutputFormatter:
    """Convert structured content to different output formats"""
    
    @staticmethod
    def to_html(section: SectionContent) -> str:
        """Convert to HTML"""
        html = f"<h1>{section.title}</h1>\n"
        html += f"<p class='summary'>{section.summary}</p>\n"
        
        for element in section.main_content:
            if element.type == ContentType.PARAGRAPH:
                html += f"<p>{element.content}</p>\n"
            elif element.type == ContentType.LIST:
                list_tag = "ol" if element.metadata.get("style") == ListStyle.NUMBERED else "ul"
                html += f"<{list_tag}>\n"
                for item in element.content:
                    if isinstance(item, ListItem):
                        html += f"  <li>{item.label}: {item.value}"
                        if item.detail:
                            html += f" <span class='detail'>({item.detail})</span>"
                        html += "</li>\n"
                html += f"</{list_tag}>\n"
            elif element.type == ContentType.ASSESSMENT:
                html += "<table class='assessment'>\n"
                html += "  <thead><tr><th>Aspect</th><th>Capaciteit</th><th>Frequentie</th><th>Beperking</th></tr></thead>\n"
                html += "  <tbody>\n"
                for item in element.content:
                    if isinstance(item, AssessmentItem):
                        html += f"    <tr><td>{item.aspect}</td><td>{item.capacity}</td><td>{item.frequency or '-'}</td><td>{item.limitation or '-'}</td></tr>\n"
                html += "  </tbody>\n</table>\n"
        
        if section.conclusions:
            html += "<h2>Conclusies</h2>\n<ul>\n"
            for conclusion in section.conclusions:
                html += f"  <li>{conclusion}</li>\n"
            html += "</ul>\n"
        
        if section.recommendations:
            html += "<h2>Aanbevelingen</h2>\n<ul>\n"
            for rec in section.recommendations:
                priority_class = f"priority-{rec.priority.value}"
                html += f"  <li class='{priority_class}'>{rec.action}</li>\n"
            html += "</ul>\n"
        
        return html
    
    @staticmethod
    def to_markdown(section: SectionContent) -> str:
        """Convert to Markdown"""
        md = f"# {section.title}\n\n"
        md += f"**Samenvatting:** {section.summary}\n\n"
        
        for element in section.main_content:
            if element.type == ContentType.PARAGRAPH:
                md += f"{element.content}\n\n"
            elif element.type == ContentType.LIST:
                prefix = "1." if element.metadata.get("style") == ListStyle.NUMBERED else "-"
                for i, item in enumerate(element.content):
                    if isinstance(item, ListItem):
                        list_prefix = f"{i+1}." if prefix == "1." else "-"
                        md += f"{list_prefix} {item.value}"
                        if item.detail:
                            md += f" _{item.detail}_"
                        md += "\n"
                md += "\n"
            elif element.type == ContentType.ASSESSMENT:
                md += "| Aspect | Capaciteit | Frequentie | Beperking |\n"
                md += "|--------|------------|------------|------------|\n"
                for item in element.content:
                    if isinstance(item, AssessmentItem):
                        md += f"| {item.aspect} | {item.capacity} | {item.frequency or '-'} | {item.limitation or '-'} |\n"
                md += "\n"
        
        if section.conclusions:
            md += "## Conclusies\n\n"
            for conclusion in section.conclusions:
                md += f"- {conclusion}\n"
            md += "\n"
        
        if section.recommendations:
            md += "## Aanbevelingen\n\n"
            for rec in section.recommendations:
                priority_marker = "🔴" if rec.priority == Priority.HIGH else "🟡" if rec.priority == Priority.MEDIUM else "🟢"
                md += f"- {priority_marker} {rec.action}\n"
            md += "\n"
        
        return md
    
    @staticmethod
    def to_json(section: SectionContent) -> Dict:
        """Convert to JSON/Dict format"""
        return section.dict()
    
    @staticmethod
    def to_plain_text(section: SectionContent) -> str:
        """Convert to plain text (current format)"""
        text = f"# {section.title}\n\n"
        text += f"{section.summary}\n\n"
        
        for element in section.main_content:
            if element.type == ContentType.PARAGRAPH:
                text += f"{element.content}\n\n"
            elif element.type == ContentType.LIST:
                for item in element.content:
                    if isinstance(item, ListItem):
                        text += f"- {item.value}"
                        if item.detail:
                            text += f" ({item.detail})"
                        text += "\n"
                text += "\n"
            elif element.type == ContentType.ASSESSMENT:
                for item in element.content:
                    if isinstance(item, AssessmentItem):
                        text += f"{item.aspect}: {item.capacity}"
                        if item.limitation:
                            text += f" (beperking: {item.limitation})"
                        text += "\n"
                text += "\n"
        
        if section.conclusions:
            text += "Conclusies:\n"
            for conclusion in section.conclusions:
                text += f"- {conclusion}\n"
            text += "\n"
        
        if section.recommendations:
            text += "Aanbevelingen:\n"
            for rec in section.recommendations:
                text += f"- [{rec.priority.value.upper()}] {rec.action}\n"
        
        return text