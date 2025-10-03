"""
AD Pipeline Adapter - Integrates new AD report structure with existing pipeline
Bridges the gap between old sectioned approach and new structured approach
"""
import json
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

from app.models.ad_report_structure import (
    ADReport,
    ADReportGenerator,
    Contactgegevens,
    Bedrijfsgegevens,
    OnderzoekGegevens,
    BeperkingMate,
    FMLRubriek,
    FMLRubriekItem,
    Belastbaarheid,
    FunctieGegevens,
    FunctieBelasting,
    Opleiding,
    Arbeidsverleden,
    Bekwaamheden,
    GeschiktheidAnalyse,
    VraagstellingItem,
    ConclusieItem,
    TrajectplanItem
)
from app.utils.ad_content_generator import ADContentGenerator
from app.utils.ad_report_renderer import ADReportRenderer
from app.models.report import Report, ReportRead

logger = logging.getLogger(__name__)

class ADPipelineAdapter:
    """Adapts the new AD report system to work with existing pipeline"""
    
    def __init__(self):
        self.content_generator = ADContentGenerator()
        self.renderer = ADReportRenderer()
        
    # Legacy section mapping to new AD structure
    SECTION_MAPPING = {
        # Old section -> New AD section method
        "vraagstelling": "generate_questions",
        "ondernomen_activiteiten": "generate_activities", 
        "gegevensverzameling_voorgeschiedenis": "generate_history",
        "gegevensverzameling_werkgever": "generate_basic_data",
        "gegevensverzameling_werknemer": "generate_employee_data",
        "belastbaarheid": "generate_belastbaarheid",
        "eigen_functie": "generate_job_analysis",
        "gesprek_werkgever": "generate_conversations",
        "gesprek_werknemer": "generate_conversations",
        "gesprek_gezamenlijk": "generate_conversations",
        "visie_ad_eigen_werk": "generate_suitability_analysis",
        "visie_ad_aanpassing": "generate_adjustments",
        "visie_ad_ander_werk_eigen": "generate_alternatives",
        "visie_ad_ander_werk_extern": "generate_alternatives",
        "visie_ad_duurzaamheid": "generate_alternatives",
        "advies": "generate_trajectory_plan",
        "conclusie": "generate_conclusions",
        "vervolg": "generate_follow_up"
    }
    
    async def generate_ad_report_from_legacy_sections(
        self, 
        context: str,
        sections: Dict[str, str],
        case_data: Optional[Dict[str, Any]] = None,
        template_id: str = "staatvandienst"
    ) -> ADReport:
        """
        Generate AD report using legacy section content but new structure
        
        Args:
            context: Document context
            sections: Legacy sections dict {section_id: content}
            case_data: Case metadata
            template_id: Template identifier
            
        Returns:
            Structured ADReport
        """
        logger.info("Generating AD report from legacy sections")
        
        # Start with empty report
        report = ADReportGenerator.create_empty_report()
        
        # Fill basic data from case_data if available
        if case_data:
            if 'client_name' in case_data:
                report.werknemer.naam = case_data['client_name']
            if 'company_name' in case_data:
                report.opdrachtgever.naam_bedrijf = case_data['company_name']
        
        # Process legacy sections and convert to structured data
        await self._process_legacy_sections(report, sections, context)
        
        # Fill any missing sections using content generator
        report = await self._fill_missing_sections(report, context)
        
        return report
    
    async def _process_legacy_sections(
        self, 
        report: ADReport, 
        sections: Dict[str, str], 
        context: str
    ):
        """Process legacy sections and map to new structure"""
        
        for section_id, content in sections.items():
            if not content or content.strip() == "":
                continue
                
            try:
                # Map to appropriate part of AD structure
                if section_id == "gegevensverzameling_voorgeschiedenis":
                    report.voorgeschiedenis = content
                    
                elif section_id == "gegevensverzameling_werkgever":
                    # Try to extract structured data from text
                    await self._extract_werkgever_data(report, content)
                    
                elif section_id == "gegevensverzameling_werknemer":
                    # Try to extract employee data
                    await self._extract_werknemer_data(report, content)
                    
                elif section_id == "belastbaarheid":
                    # Try to extract FML data
                    await self._extract_belastbaarheid_data(report, content)
                    
                elif section_id == "eigen_functie":
                    # Extract function data
                    await self._extract_functie_data(report, content)
                    
                elif section_id in ["gesprek_werkgever", "gesprek_werknemer", "gesprek_gezamenlijk"]:
                    # Store conversation data
                    if section_id == "gesprek_werkgever":
                        report.gesprek_werkgever = {"algemeen": content}
                    elif section_id == "gesprek_werknemer":
                        report.gesprek_werknemer = {"visie_beperkingen": content}
                    else:
                        report.gesprek_gezamenlijk = content
                        
                elif section_id.startswith("visie_ad_"):
                    # Map AD vision sections
                    if section_id == "visie_ad_eigen_werk":
                        report.conclusie_eigen_werk = content
                    elif section_id == "visie_ad_aanpassing":
                        report.aanpassing_eigen_werk = content
                    elif section_id == "visie_ad_ander_werk_eigen":
                        report.geschiktheid_ander_werk_intern = content
                    elif section_id == "visie_ad_ander_werk_extern":
                        report.geschiktheid_ander_werk_extern = content
                    elif section_id == "visie_ad_duurzaamheid":
                        report.visie_duurzaamheid = content
                        
                elif section_id == "vraagstelling":
                    # Parse questions
                    questions = self._parse_questions(content)
                    report.vraagstelling = questions
                    report.samenvatting_vraagstelling = [q.vraag for q in questions[:4]]
                    
                elif section_id == "ondernomen_activiteiten":
                    # Parse activities 
                    activities = self._parse_list_items(content)
                    report.ondernomen_activiteiten = activities
                    
                elif section_id == "conclusie":
                    # Parse conclusions
                    conclusions = self._parse_list_items(content)
                    report.samenvatting_conclusie = conclusions[:4]
                    report.conclusies = [ConclusieItem(conclusie=c) for c in conclusions]
                    
                elif section_id == "vervolg":
                    # Parse follow-up steps
                    vervolg_items = self._parse_list_items(content)
                    report.vervolg = vervolg_items
                    
            except Exception as e:
                logger.error(f"Error processing section {section_id}: {str(e)}")
                continue
    
    async def _extract_werkgever_data(self, report: ADReport, content: str):
        """Extract employer data from legacy content"""
        # Try to use content generator to structure the data
        try:
            generator = self.content_generator
            temp_report = ADReportGenerator.create_empty_report()
            temp_report = await generator._generate_basic_data(temp_report, content)
            
            # Copy over the extracted data
            if temp_report.opdrachtgever.naam_bedrijf and temp_report.opdrachtgever.naam_bedrijf != "[Te vullen]":
                report.opdrachtgever = temp_report.opdrachtgever
                
        except Exception as e:
            logger.error(f"Error extracting employer data: {str(e)}")
            # Fallback - just store as description
            report.opdrachtgever.aard_bedrijf = content
    
    async def _extract_werknemer_data(self, report: ADReport, content: str):
        """Extract employee data from legacy content"""
        try:
            generator = self.content_generator
            temp_report = ADReportGenerator.create_empty_report()
            temp_report = await generator._generate_employee_data(temp_report, content)
            
            # Copy extracted data
            if temp_report.opleidingen:
                report.opleidingen = temp_report.opleidingen
            if temp_report.arbeidsverleden_lijst:
                report.arbeidsverleden_lijst = temp_report.arbeidsverleden_lijst
            if temp_report.bekwaamheden:
                report.bekwaamheden = temp_report.bekwaamheden
                
        except Exception as e:
            logger.error(f"Error extracting employee data: {str(e)}")
    
    async def _extract_belastbaarheid_data(self, report: ADReport, content: str):
        """Extract FML data from legacy content"""
        try:
            generator = self.content_generator
            temp_report = ADReportGenerator.create_empty_report()
            temp_report = await generator._generate_belastbaarheid(temp_report, content)
            
            # Copy FML data
            if temp_report.belastbaarheid and temp_report.belastbaarheid.fml_rubrieken:
                report.belastbaarheid = temp_report.belastbaarheid
                
        except Exception as e:
            logger.error(f"Error extracting belastbaarheid data: {str(e)}")
            # Fallback - create basic structure
            report.belastbaarheid = Belastbaarheid(
                datum_beoordeling=datetime.now().strftime("%d-%m-%Y"),
                beoordelaar="[Te bepalen]",
                fml_rubrieken=ADReportGenerator.get_fml_rubrieken_template()
            )
    
    async def _extract_functie_data(self, report: ADReport, content: str):
        """Extract job function data from legacy content"""
        try:
            generator = self.content_generator
            temp_report = ADReportGenerator.create_empty_report()
            temp_report = await generator._generate_job_analysis(temp_report, content)
            
            if temp_report.eigen_functie:
                report.eigen_functie = temp_report.eigen_functie
            if temp_report.functiebelasting:
                report.functiebelasting = temp_report.functiebelasting
                
        except Exception as e:
            logger.error(f"Error extracting function data: {str(e)}")
    
    def _parse_questions(self, content: str) -> List[VraagstellingItem]:
        """Parse questions from content"""
        questions = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line.startswith('*') or line.endswith('?')):
                # Remove bullet points
                question = line.lstrip('-•* ').strip()
                if question:
                    questions.append(VraagstellingItem(vraag=question))
        
        # If no questions found, use defaults
        if not questions:
            questions = [
                VraagstellingItem(vraag="Kan werknemer het eigen werk nog uitvoeren?"),
                VraagstellingItem(vraag="Is het eigen werk met aanpassingen mogelijk?"),
                VraagstellingItem(vraag="Kan werknemer ander werk bij eigen werkgever uitvoeren?"),
                VraagstellingItem(vraag="Zijn er mogelijkheden voor externe re-integratie?")
            ]
        
        return questions
    
    def _parse_list_items(self, content: str) -> List[str]:
        """Parse list items from content"""
        items = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                item = line.lstrip('-•* ').strip()
                if item:
                    items.append(item)
            elif line and not items:  # If no bullet points, treat each line as an item
                items.append(line)
        
        return items
    
    async def _fill_missing_sections(self, report: ADReport, context: str) -> ADReport:
        """Fill any missing sections using content generator"""
        try:
            # Check and fill basic data if missing
            if not report.werknemer.naam or report.werknemer.naam == "[Te vullen]":
                report = await self.content_generator._generate_basic_data(report, context)
            
            # Check and fill summary if missing
            if not report.samenvatting_vraagstelling:
                report = await self.content_generator._generate_summary(report, context)
            
            # Check and fill belastbaarheid if missing
            if not report.belastbaarheid.fml_rubrieken:
                report = await self.content_generator._generate_belastbaarheid(report, context)
            
        except Exception as e:
            logger.error(f"Error filling missing sections: {str(e)}")
        
        return report
    
    def convert_to_legacy_format(self, ad_report: ADReport, template_id: str = "staatvandienst") -> Dict[str, str]:
        """
        Convert AD report back to legacy section format for backward compatibility
        
        Args:
            ad_report: Structured AD report
            template_id: Template to use for section mapping
            
        Returns:
            Dictionary with legacy section format
        """
        legacy_sections = {}
        
        # Map structured data back to legacy sections
        try:
            # 1. Vraagstelling
            if ad_report.vraagstelling:
                questions_text = "\n".join([f"• {q.vraag}" for q in ad_report.vraagstelling])
                legacy_sections["vraagstelling"] = questions_text
            
            # 2. Ondernomen activiteiten  
            if ad_report.ondernomen_activiteiten:
                activities_text = "\n".join([f"• {act}" for act in ad_report.ondernomen_activiteiten])
                legacy_sections["ondernomen_activiteiten"] = activities_text
            
            # 3.1 Voorgeschiedenis
            if ad_report.voorgeschiedenis:
                legacy_sections["gegevensverzameling_voorgeschiedenis"] = ad_report.voorgeschiedenis
            
            # 3.2 Gegevens werkgever
            if ad_report.opdrachtgever:
                werkgever_text = self._format_werkgever_text(ad_report.opdrachtgever)
                legacy_sections["gegevensverzameling_werkgever"] = werkgever_text
            
            # 3.3 Gegevens werknemer
            werknemer_text = self._format_werknemer_text(ad_report)
            if werknemer_text:
                legacy_sections["gegevensverzameling_werknemer"] = werknemer_text
            
            # 3.4 Belastbaarheid
            if ad_report.belastbaarheid:
                belastbaarheid_text = self._format_belastbaarheid_text(ad_report.belastbaarheid)
                legacy_sections["belastbaarheid"] = belastbaarheid_text
            
            # 3.5 Eigen functie
            if ad_report.eigen_functie:
                functie_text = self._format_functie_text(ad_report.eigen_functie, ad_report.functiebelasting)
                legacy_sections["eigen_functie"] = functie_text
            
            # Gesprekken
            if ad_report.gesprek_werkgever:
                legacy_sections["gesprek_werkgever"] = "\n".join(ad_report.gesprek_werkgever.values())
            
            if ad_report.gesprek_werknemer:
                legacy_sections["gesprek_werknemer"] = "\n".join(ad_report.gesprek_werknemer.values())
            
            if ad_report.gesprek_gezamenlijk:
                legacy_sections["gesprek_gezamenlijk"] = ad_report.gesprek_gezamenlijk
            
            # Visie AD secties
            if ad_report.conclusie_eigen_werk:
                legacy_sections["visie_ad_eigen_werk"] = ad_report.conclusie_eigen_werk
                
            if ad_report.aanpassing_eigen_werk:
                legacy_sections["visie_ad_aanpassing"] = ad_report.aanpassing_eigen_werk
                
            if ad_report.geschiktheid_ander_werk_intern:
                legacy_sections["visie_ad_ander_werk_eigen"] = ad_report.geschiktheid_ander_werk_intern
                
            if ad_report.geschiktheid_ander_werk_extern:
                legacy_sections["visie_ad_ander_werk_extern"] = ad_report.geschiktheid_ander_werk_extern
                
            if ad_report.visie_duurzaamheid:
                legacy_sections["visie_ad_duurzaamheid"] = ad_report.visie_duurzaamheid
            
            # Trajectplan -> Advies
            if ad_report.trajectplan:
                advies_text = "\n".join([f"• {item.actie}" for item in ad_report.trajectplan])
                legacy_sections["advies"] = advies_text
            
            # Conclusies
            if ad_report.conclusies:
                conclusie_text = "\n".join([f"• {c.conclusie}" for c in ad_report.conclusies])
                legacy_sections["conclusie"] = conclusie_text
            elif ad_report.samenvatting_conclusie:
                conclusie_text = "\n".join([f"• {c}" for c in ad_report.samenvatting_conclusie])
                legacy_sections["conclusie"] = conclusie_text
            
            # Vervolg
            if ad_report.vervolg:
                vervolg_text = "\n".join([f"• {item}" for item in ad_report.vervolg])
                legacy_sections["vervolg"] = vervolg_text
                
        except Exception as e:
            logger.error(f"Error converting to legacy format: {str(e)}")
        
        return legacy_sections
    
    def _format_werkgever_text(self, werkgever: Bedrijfsgegevens) -> str:
        """Format employer data as text"""
        lines = []
        if werkgever.naam_bedrijf:
            lines.append(f"Bedrijf: {werkgever.naam_bedrijf}")
        if werkgever.aard_bedrijf:
            lines.append(f"Aard bedrijf: {werkgever.aard_bedrijf}")
        if werkgever.omvang_bedrijf:
            lines.append(f"Omvang: {werkgever.omvang_bedrijf}")
        if werkgever.aantal_werknemers:
            lines.append(f"Aantal werknemers: {werkgever.aantal_werknemers}")
        return "\n".join(lines)
    
    def _format_werknemer_text(self, report: ADReport) -> str:
        """Format employee data as text"""
        lines = []
        
        # Basic info
        if report.werknemer.naam:
            lines.append(f"Naam: {report.werknemer.naam}")
        if report.werknemer.geboortedatum:
            lines.append(f"Geboortedatum: {report.werknemer.geboortedatum}")
        
        # Education
        if report.opleidingen:
            lines.append("\nOpleidingen:")
            for opl in report.opleidingen:
                lines.append(f"- {opl.naam} ({opl.jaar or 'onbekend'})")
        
        # Work history
        if report.arbeidsverleden_lijst:
            lines.append("\nArbeidsverleden:")
            for werk in report.arbeidsverleden_lijst:
                lines.append(f"- {werk.periode}: {werk.functie} bij {werk.werkgever}")
        
        return "\n".join(lines)
    
    def _format_belastbaarheid_text(self, belastbaarheid: Belastbaarheid) -> str:
        """Format FML data as text"""
        lines = []
        
        if belastbaarheid.datum_beoordeling and belastbaarheid.beoordelaar:
            lines.append(f"FML van {belastbaarheid.datum_beoordeling} door {belastbaarheid.beoordelaar}")
        
        for rubriek in belastbaarheid.fml_rubrieken:
            lines.append(f"\nRubriek {rubriek.rubriek_nummer}: {rubriek.rubriek_naam} - {rubriek.mate_beperking.value}")
            
            for item in rubriek.items:
                lines.append(f"  {item.nummer or ''} {item.beschrijving}")
        
        if belastbaarheid.prognose:
            lines.append(f"\nPrognose: {belastbaarheid.prognose}")
        
        return "\n".join(lines)
    
    def _format_functie_text(self, functie: FunctieGegevens, belasting: List[FunctieBelasting]) -> str:
        """Format function data as text"""
        lines = []
        
        lines.append(f"Functie: {functie.naam_functie}")
        lines.append(f"Arbeidspatroon: {functie.arbeidspatroon}")
        lines.append(f"Overeenkomst: {functie.overeenkomst}")
        lines.append(f"Aantal uren: {functie.aantal_uren}")
        
        if functie.functieomschrijving:
            lines.append(f"\nFunctieomschrijving:\n{functie.functieomschrijving}")
        
        if belasting:
            lines.append("\nFunctiebelasting:")
            for item in belasting:
                lines.append(f"- {item.taak} ({item.percentage}): {item.belastende_aspecten}")
        
        return "\n".join(lines)
    
    async def render_ad_report(
        self, 
        ad_report: ADReport, 
        format: str = "markdown",
        template: str = "standaard"
    ) -> str:
        """
        Render AD report to specified format
        
        Args:
            ad_report: Structured AD report
            format: Output format (markdown, html, json)
            template: Template style
            
        Returns:
            Rendered report string
        """
        try:
            renderer = ADReportRenderer(template)
            
            if format == "markdown":
                return renderer.render_markdown(ad_report)
            elif format == "html":
                return renderer.render_html(ad_report)
            elif format == "json":
                return renderer.render_json(ad_report)
            else:
                # Default to markdown
                return renderer.render_markdown(ad_report)
                
        except Exception as e:
            logger.error(f"Error rendering AD report: {str(e)}")
            return f"Error rendering report: {str(e)}"