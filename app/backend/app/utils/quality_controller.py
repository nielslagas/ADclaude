"""
Automatische Kwaliteitscontrole voor Gegenereerde Arbeidsdeskundige Content
Valideert en verbetert de kwaliteit van AI-gegenereerde rapportsecties
"""

import logging
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from anthropic import Anthropic
from app.utils.context_aware_prompts import ReportSection, ComplexityLevel


class QualityIssueType(Enum):
    """Types van kwaliteitsproblemen"""
    FACTUAL_INCONSISTENCY = "factual_inconsistency"
    INSUFFICIENT_DETAIL = "insufficient_detail"
    UNPROFESSIONAL_TONE = "unprofessional_tone"
    MISSING_STRUCTURE = "missing_structure"
    INCORRECT_TERMINOLOGY = "incorrect_terminology"
    INCOMPLETE_SECTION = "incomplete_section"
    LOGICAL_FLOW = "logical_flow"
    COMPLIANCE_ISSUE = "compliance_issue"
    HALLUCINATION = "hallucination"
    REPETITION = "repetition"
    INCONSISTENT_FACTS = "inconsistent_facts"
    LANGUAGE_QUALITY = "language_quality"
    FORMATTING_ISSUE = "formatting_issue"
    MISSING_CONTEXT = "missing_context"
    OUTDATED_INFORMATION = "outdated_information"
    BIAS_DETECTED = "bias_detected"
    LEGAL_ACCURACY = "legal_accuracy"
    MEDICAL_ACCURACY = "medical_accuracy"


class QualitySeverity(Enum):
    """Ernst van kwaliteitsproblemen"""
    CRITICAL = "critical"      # Moet gefixed worden
    MAJOR = "major"           # Sterk aanbevolen om te fixen
    MINOR = "minor"           # Optionele verbetering
    SUGGESTION = "suggestion" # Stylistische suggestie


@dataclass
class QualityIssue:
    """Een geïdentificeerd kwaliteitsprobleem"""
    type: QualityIssueType
    severity: QualitySeverity
    description: str
    location: str  # Waar in de tekst
    suggestion: str
    confidence: float


@dataclass
class QualityReport:
    """Volledige kwaliteitsrapportage"""
    overall_score: float  # 0.0 - 1.0
    issues: List[QualityIssue]
    strengths: List[str]
    recommendations: List[str]
    section: ReportSection
    original_text: str
    improved_text: Optional[str] = None
    validation_timestamp: str = None
    # Enhanced metrics
    section_scores: Dict[str, float] = None
    quality_metrics: Dict[str, Any] = None
    compliance_status: str = "unknown"
    improvement_potential: float = 0.0
    processing_time_ms: float = 0.0
    ai_confidence: float = 0.0


class AutomaticQualityController:
    """Automatische kwaliteitscontrole voor arbeidsdeskundige content"""
    
    def __init__(self):
        from app.core.config import settings
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.logger = logging.getLogger(__name__)
        
        # Nederlandse arbeidsdeskundige terminologie database
        self.professional_terms = self._load_professional_terminology()
        self.compliance_rules = self._load_compliance_rules()
        self.quality_patterns = self._load_quality_patterns()
    
    def _load_professional_terminology(self) -> Dict[str, List[str]]:
        """Laad Nederlandse arbeidsdeskundige vakterminologie"""
        return {
            "medical": [
                "diagnose", "anamnese", "bevindingen", "prognose", "behandeling",
                "medicatie", "therapie", "revalidatie", "specialist", "huisarts",
                "fysiotherapeut", "ergotherapeut", "psycholoog", "psychiater",
                "symptomen", "klachten", "onderzoek", "MRI", "röntgen", "echo",
                "bloedonderzoek", "laboratorium", "radiologie", "pathologie",
                "chronisch", "acuut", "symptomatisch", "asymptomatisch",
                "contraïndicatie", "indicatie", "dosering", "bijwerking"
            ],
            "assessment": [
                "FCE", "functionele capaciteit evaluatie", "belastbaarheid",
                "arbeidsbelasting", "beperkingen", "mogelijkheden", "capaciteit",
                "werkhervatting", "re-integratie", "arbeidsgeschiktheid",
                "functie-eisen", "taakanalyse", "werkplekonderzoek",
                "ergonomische beoordeling", "risico-inventarisatie",
                "WUBO", "proefplaatsing", "therapeutische werkhervatting",
                "geleidelijke opbouw", "werknemersonderzoek", "second opinion"
            ],
            "legal": [
                "WIA", "WAO", "WW", "Ziektewet", "arbeidscontract", "ontslag",
                "verzuim", "arbeidsrecht", "UWV", "verzekeraar", "claim",
                "arbodienst", "bedrijfsarts", "loondoorbetalingsverplichting",
                "re-integratieverslag", "plan van aanpak", "arbeidsgeschiktheid",
                "WGA", "IVA", "Wajong", "participatiewet", "poortwachter",
                "geschillencommissie", "bezwaar", "beroep", "deskundigenoordeel"
            ],
            "workplace": [
                "werkplek", "functie-eisen", "arbeidsomstandigheden", "ergonomie",
                "werkbelasting", "werkdruk", "werkritme", "werktijden",
                "arbocatalogus", "RI&E", "PVA", "preventie", "ARBO",
                "werkplekonderzoek", "aanpassingen", "hulpmiddelen",
                "taakroulatie", "flexibiliteit", "thuiswerken", "deeltijd"
            ],
            "functional": [
                "ADL", "mobiliteit", "cognitie", "concentratie", "geheugen",
                "uithouding", "kracht", "flexibiliteit", "balans", "coördinatie",
                "fijnmotoriek", "grofmotoriek", "zitwerk", "stawerk", "loopwerk",
                "tillen", "dragen", "duwen", "trekken", "reiken", "bukken"
            ],
            "psychological": [
                "stressbestendigheid", "coping", "motivatie", "burn-out",
                "depressie", "angst", "PTSS", "aanpassingsstoornis",
                "psychosociaal", "werkdruk", "time management", "assertiviteit",
                "sociale vaardigheden", "communicatie", "zelfredzaamheid"
            ]
        }
    
    def _load_compliance_rules(self) -> Dict[str, List[str]]:
        """Laad compliance regels voor arbeidsdeskundige rapporten"""
        return {
            "privacy": [
                "Geen volledige namen van derden",
                "Geen BSN nummers", 
                "Geen directe identificeerbare informatie",
                "Professionele distantie bewaren",
                "Geen adressen of contactgegevens van derden",
                "Anonymisering van werkgevers waar mogelijk",
                "GDPR compliance voor persoonsgegevens"
            ],
            "objectivity": [
                "Feitelijke toon gebruiken",
                "Geen persoonlijke meningen",
                "Onderbouwde conclusies",
                "Neutrale formulering",
                "Vermijd subjectieve bewoordingen",
                "Gebruik van 'ik' of 'wij' alleen waar professioneel gepast",
                "Balans tussen verschillende perspectieven"
            ],
            "completeness": [
                "Alle relevante aspecten behandelen",
                "Bronvermelding waar nodig",
                "Heldere conclusies",
                "Praktische aanbevelingen",
                "Voldoende onderbouwing van stellingen",
                "Consistentie door het gehele rapport",
                "Actuele informatie en richtlijnen"
            ],
            "professional_standards": [
                "Nederlandse arbeidsdeskundige richtlijnen",
                "NVAB standaarden waar van toepassing",
                "Wetgeving correct toegepast",
                "Medische terminologie juist gebruikt",
                "Evidenced-based conclusies",
                "Transparantie over methodologie"
            ],
            "language_quality": [
                "Correcte Nederlandse spelling en grammatica",
                "Professionele schrijfstijl",
                "Heldere en toegankelijke taal",
                "Consistente terminologie",
                "Logische paragraafopbouw",
                "Adequate zinsbouw en interpunctie"
            ]
        }
    
    def _load_quality_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Laad kwaliteitspatronen per rapport sectie"""
        return {
            ReportSection.MEDISCHE_SITUATIE.value: {
                "required_elements": ["diagnose", "behandeling", "prognose", "anamnese"],
                "structure_indicators": ["hoofddiagnose", "bijkomende", "behandeling", "medicatie", "specialist", "onderzoek"],
                "tone_words": ["objectief", "feitelijk", "medisch", "klinisch", "behandelend", "gespecialiseerd"],
                "avoid_words": ["misschien", "waarschijnlijk", "denk", "voel", "lijkt me", "volgens mij"],
                "min_word_count": 150,
                "max_word_count": 800,
                "quality_indicators": ["chronologie", "onderbouwing", "volledigheid"]
            },
            ReportSection.BELASTBAARHEID.value: {
                "required_elements": ["fysiek", "mentaal", "capaciteit", "beperkingen", "mogelijkheden"],
                "structure_indicators": ["fysieke belastbaarheid", "mentale belastbaarheid", "FCE", "werknemersonderzoek"],
                "tone_words": ["capaciteit", "belastbaar", "geschikt", "mogelijk", "haalbaar", "realistisch"],
                "avoid_words": ["onmogelijk", "nooit", "altijd", "absoluut niet", "zeker niet"],
                "min_word_count": 200,
                "max_word_count": 1000,
                "quality_indicators": ["concrete beoordeling", "onderbouwing", "nuancering"]
            },
            ReportSection.ADVIES.value: {
                "required_elements": ["concrete stappen", "tijdslijn", "verantwoordelijkheden", "monitoring"],
                "structure_indicators": ["aanbeveling", "advies", "stappen", "planning", "evaluatie"],
                "tone_words": ["aanbevolen", "geadviseerd", "zinvol", "passend", "haalbaar", "realistisch"],
                "avoid_words": ["moet", "verplicht", "absoluut", "noodzakelijk", "dwingend"],
                "min_word_count": 100,
                "max_word_count": 600,
                "quality_indicators": ["uitvoerbaarheid", "specificiteit", "meetbaarheid"]
            },
            ReportSection.CONCLUSIE.value: {
                "required_elements": ["samenvatting", "hoofdpunten", "eindoordeel"],
                "structure_indicators": ["concluderend", "samenvattend", "kernpunten", "eindoordeel"],
                "tone_words": ["concluderend", "samenvattend", "overzichtelijk", "helder"],
                "avoid_words": ["misschien", "mogelijk", "waarschijnlijk", "denk"],
                "min_word_count": 80,
                "max_word_count": 400,
                "quality_indicators": ["synthese", "helderheid", "logische afsluiting"]
            },
            ReportSection.ADVIES.value: {
                "required_elements": ["professioneel oordeel", "ervaring", "methode"],
                "structure_indicators": ["arbeidsdeskundige visie", "professioneel oordeel", "expertise"],
                "tone_words": ["professioneel", "deskundig", "gebaseerd op", "vanuit expertise"],
                "avoid_words": ["persoonlijk", "naar mijn idee", "ik vind"],
                "min_word_count": 120,
                "max_word_count": 500,
                "quality_indicators": ["expertise", "onderbouwing", "professionaliteit"]
            },
            ReportSection.MOGELIJKHEDEN.value: {
                "required_elements": ["functie-eisen", "capaciteiten", "match analyse"],
                "structure_indicators": ["matching", "aansluiting", "geschiktheid", "functie-eisen"],
                "tone_words": ["geschikt", "passend", "aansluitend", "haalbaar"],
                "avoid_words": ["perfect", "ideaal", "ongeschikt", "hopeloos"],
                "min_word_count": 150,
                "max_word_count": 700,
                "quality_indicators": ["analyse", "vergelijking", "realistische beoordeling"]
            }
        }
    
    async def validate_content(
        self, 
        content: str, 
        section: ReportSection,
        context_chunks: List[str] = None,
        complexity_level: ComplexityLevel = ComplexityLevel.MEDIUM,
        structured_data: Dict[str, Any] = None
    ) -> QualityReport:
        """
        Hoofdfunctie: valideer content kwaliteit met uitgebreide checks
        """
        start_time = datetime.utcnow()
        self.logger.info(f"Starting enhanced quality validation for section {section.value}")
        
        try:
            # Stap 1: Pre-processing checks
            preprocessing_issues = self._preprocessing_validation(content, section)
            
            # Stap 2: Basis regel-gebaseerde validaties
            rule_based_issues = self._rule_based_validation(content, section)
            
            # Stap 3: Geavanceerde linguïstische analyse
            linguistic_issues = self._linguistic_analysis(content, section)
            
            # Stap 4: AI-gedreven kwaliteitsanalyse
            ai_analysis = await self._ai_quality_analysis(content, section, context_chunks)
            
            # Stap 5: Compliance en privacy checks
            compliance_issues = self._compliance_check(content, section)
            
            # Stap 6: Gestructureerde data validatie (indien beschikbaar)
            structured_issues = self._validate_structured_data(structured_data, section) if structured_data else []
            
            # Stap 7: Context consistentie check
            context_issues = self._context_consistency_check(content, context_chunks) if context_chunks else []
            
            # Stap 8: Medische/juridische accuraatheid (indien relevant)
            domain_issues = self._domain_specific_validation(content, section)
            
            # Combineer alle issues
            all_issues = (
                preprocessing_issues + rule_based_issues + linguistic_issues + 
                ai_analysis["issues"] + compliance_issues + structured_issues + 
                context_issues + domain_issues
            )
            
            # Filter en prioriteer issues
            filtered_issues = self._filter_and_prioritize_issues(all_issues)
            
            # Bereken uitgebreide kwaliteitsscores
            quality_metrics = self._calculate_comprehensive_quality_metrics(
                filtered_issues, content, section, ai_analysis
            )
            
            # Genereer verbeterde aanbevelingen
            recommendations = self._generate_enhanced_recommendations(filtered_issues, section, quality_metrics)
            
            # Identificeer sterke punten
            strengths = self._identify_comprehensive_strengths(content, section, ai_analysis, quality_metrics)
            
            # Bereken processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            report = QualityReport(
                overall_score=quality_metrics["overall_score"],
                issues=filtered_issues,
                strengths=strengths,
                recommendations=recommendations,
                section=section,
                original_text=content,
                validation_timestamp=start_time.isoformat(),
                section_scores=quality_metrics["section_scores"],
                quality_metrics=quality_metrics,
                compliance_status=self._determine_compliance_status(compliance_issues),
                improvement_potential=quality_metrics["improvement_potential"],
                processing_time_ms=processing_time,
                ai_confidence=ai_analysis.get("confidence", 0.7)
            )
            
            self.logger.info(
                f"Enhanced quality validation completed. Score: {quality_metrics['overall_score']:.2f}, "
                f"Issues: {len(filtered_issues)}, Time: {processing_time:.1f}ms"
            )
            return report
            
        except Exception as e:
            self.logger.error(f"Quality validation failed: {e}")
            return self._create_fallback_report(content, section)
    
    def _preprocessing_validation(self, content: str, section: ReportSection) -> List[QualityIssue]:
        """Pre-processing validatie checks"""
        issues = []
        
        # Check voor lege of zeer korte content
        if not content or len(content.strip()) == 0:
            issues.append(QualityIssue(
                type=QualityIssueType.INSUFFICIENT_DETAIL,
                severity=QualitySeverity.CRITICAL,
                description="Content is leeg",
                location="gehele tekst",
                suggestion="Voeg inhoudelijke tekst toe",
                confidence=1.0
            ))
            return issues
        
        # Check voor encoding problemen
        try:
            content.encode('utf-8')
        except UnicodeEncodeError:
            issues.append(QualityIssue(
                type=QualityIssueType.FORMATTING_ISSUE,
                severity=QualitySeverity.MAJOR,
                description="Encoding problemen gedetecteerd",
                location="tekst formatting",
                suggestion="Controleer karakterset en speciale tekens",
                confidence=0.9
            ))
        
        # Check voor ongewone karakters
        unusual_chars = set(char for char in content if ord(char) > 127 and char not in 'äöüßéèêëïî')
        if len(unusual_chars) > 5:
            issues.append(QualityIssue(
                type=QualityIssueType.FORMATTING_ISSUE,
                severity=QualitySeverity.MINOR,
                description=f"Ongewone karakters gevonden: {', '.join(list(unusual_chars)[:5])}",
                location="tekst formatting",
                suggestion="Controleer op correcte karakters en formatting",
                confidence=0.6
            ))
        
        # Check voor verdachte patronen (mogelijk gegenereerde tekst markers)
        suspicious_patterns = [
            r'```[a-z]*\n',  # Code blocks
            r'\[PLACEHOLDER\]', r'\[TODO\]', r'\[INSERT\]',  # Placeholders
            r'lorem ipsum', r'test test test'  # Test content
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, content.lower()):
                issues.append(QualityIssue(
                    type=QualityIssueType.INCOMPLETE_SECTION,
                    severity=QualitySeverity.MAJOR,
                    description="Verdachte placeholder of test content gedetecteerd",
                    location="content structuur",
                    suggestion="Vervang placeholders met daadwerkelijke inhoud",
                    confidence=0.8
                ))
        
        return issues
    
    def _linguistic_analysis(self, content: str, section: ReportSection) -> List[QualityIssue]:
        """Geavanceerde linguïstische analyse"""
        issues = []
        sentences = re.split(r'[.!?]+', content)
        words = content.split()
        
        # Check gemiddelde zinslengte
        avg_sentence_length = sum(len(s.split()) for s in sentences if s.strip()) / max(len([s for s in sentences if s.strip()]), 1)
        if avg_sentence_length > 30:
            issues.append(QualityIssue(
                type=QualityIssueType.LANGUAGE_QUALITY,
                severity=QualitySeverity.MINOR,
                description=f"Zinnen zijn gemiddeld lang ({avg_sentence_length:.1f} woorden)",
                location="zinsstructuur",
                suggestion="Overweeg kortere, helderdere zinnen voor betere leesbaarheid",
                confidence=0.7
            ))
        
        # Check voor repetitie van woorden
        word_freq = {}
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if len(clean_word) > 4:  # Alleen langere woorden
                word_freq[clean_word] = word_freq.get(clean_word, 0) + 1
        
        repeated_words = [(word, count) for word, count in word_freq.items() if count > 3]
        if repeated_words:
            top_repeated = sorted(repeated_words, key=lambda x: x[1], reverse=True)[:3]
            issues.append(QualityIssue(
                type=QualityIssueType.REPETITION,
                severity=QualitySeverity.MINOR,
                description=f"Veel herhaalde woorden: {', '.join([f'{word} ({count}x)' for word, count in top_repeated])}",
                location="woordgebruik",
                suggestion="Varieer woordkeuze voor betere leesbaarheid",
                confidence=0.6
            ))
        
        # Check voor passieve constructies
        passive_indicators = ['wordt', 'worden', 'werd', 'werden', 'is gemaakt', 'zijn genomen']
        passive_count = sum(1 for indicator in passive_indicators if indicator in content.lower())
        total_sentences = len([s for s in sentences if s.strip()])
        
        if passive_count > total_sentences * 0.3:  # Meer dan 30% passief
            issues.append(QualityIssue(
                type=QualityIssueType.LANGUAGE_QUALITY,
                severity=QualitySeverity.MINOR,
                description="Veel passieve constructies gedetecteerd",
                location="schrijfstijl",
                suggestion="Gebruik meer actieve constructies voor directere communicatie",
                confidence=0.5
            ))
        
        # Check voor Nederlandse spelling patronen
        common_errors = {
            r'\bword\b': 'wordt',
            r'\bzie\b(?!\s+je)': 'zij',  # 'zie' vs 'zij' (behalve 'zie je')
            r'\bhun\b(?=\s+[a-z]+en)': 'hen',  # 'hun' vs 'hen'
            r'\bals\s+hun\b': 'als hen',
        }
        
        for error_pattern, suggestion in common_errors.items():
            if re.search(error_pattern, content, re.IGNORECASE):
                issues.append(QualityIssue(
                    type=QualityIssueType.LANGUAGE_QUALITY,
                    severity=QualitySeverity.MINOR,
                    description=f"Mogelijk taalkundige fout gedetecteerd",
                    location="spelling/grammatica",
                    suggestion=f"Controleer gebruik van woorden zoals '{suggestion}'",
                    confidence=0.4
                ))
        
        return issues
    
    def _context_consistency_check(self, content: str, context_chunks: List[str]) -> List[QualityIssue]:
        """Check consistentie met beschikbare context"""
        issues = []
        
        if not context_chunks:
            return issues
        
        # Combineer context
        context_text = ' '.join(context_chunks).lower()
        content_lower = content.lower()
        
        # Extract belangrijke entiteiten (eenvoudige implementatie)
        # In productie zou dit een NER model gebruiken
        date_pattern = r'\\b\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4}\\b'
        content_dates = set(re.findall(date_pattern, content))
        context_dates = set(re.findall(date_pattern, context_text))
        
        # Check voor inconsistente datums
        if content_dates and context_dates:
            inconsistent_dates = content_dates - context_dates
            if inconsistent_dates:
                issues.append(QualityIssue(
                    type=QualityIssueType.INCONSISTENT_FACTS,
                    severity=QualitySeverity.MAJOR,
                    description=f"Datums in content komen niet voor in brondocumenten: {', '.join(list(inconsistent_dates)[:3])}",
                    location="feitelijke consistentie",
                    suggestion="Controleer of alle datums correct zijn overgenomen uit brondocumenten",
                    confidence=0.7
                ))
        
        # Check voor claims die niet onderbouwd zijn door context
        strong_claims = [
            'diagnose', 'behandeling', 'prognose', 'medicatie',
            'conclusie', 'aanbeveling', 'geschikt', 'ongeschikt'
        ]
        
        unsupported_claims = []
        for claim in strong_claims:
            if claim in content_lower and claim not in context_text:
                unsupported_claims.append(claim)
        
        if len(unsupported_claims) > 2:
            issues.append(QualityIssue(
                type=QualityIssueType.MISSING_CONTEXT,
                severity=QualitySeverity.MAJOR,
                description=f"Stellingen mogelijk niet onderbouwd door brondocumenten: {', '.join(unsupported_claims[:3])}",
                location="onderbouwing",
                suggestion="Zorg ervoor dat alle stellingen gebaseerd zijn op beschikbare documentatie",
                confidence=0.6
            ))
        
        return issues
    
    def _validate_structured_data(self, structured_data: Dict[str, Any], section: ReportSection) -> List[QualityIssue]:
        """Valideer gestructureerde data elementen"""
        issues = []
        
        if not structured_data:
            return issues
        
        # Check voor vereiste velden per sectie
        required_fields = {
            ReportSection.MEDISCHE_SITUATIE: ['diagnoses', 'treatments'],
            ReportSection.BELASTBAARHEID: ['physical_capacity', 'mental_capacity'],
            ReportSection.ADVIES: ['recommendations', 'timeline'],
            ReportSection.CONCLUSIE: ['summary', 'final_assessment']
        }
        
        section_requirements = required_fields.get(section, [])
        for required_field in section_requirements:
            if required_field not in structured_data or not structured_data[required_field]:
                issues.append(QualityIssue(
                    type=QualityIssueType.INCOMPLETE_SECTION,
                    severity=QualitySeverity.MAJOR,
                    description=f"Vereist gestructureerd veld ontbreekt: {required_field}",
                    location="gestructureerde data",
                    suggestion=f"Voeg {required_field} toe aan de gestructureerde output",
                    confidence=0.9
                ))
        
        # Valideer data types en formats
        for key, value in structured_data.items():
            if key.endswith('_date') and isinstance(value, str):
                try:
                    datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    issues.append(QualityIssue(
                        type=QualityIssueType.FORMATTING_ISSUE,
                        severity=QualitySeverity.MINOR,
                        description=f"Ongeldige datum format in {key}: {value}",
                        location="data formatting",
                        suggestion="Gebruik YYYY-MM-DD format voor datums",
                        confidence=0.8
                    ))
            
            elif key.endswith('_score') and isinstance(value, (int, float)):
                if not 0 <= value <= 10:
                    issues.append(QualityIssue(
                        type=QualityIssueType.FACTUAL_INCONSISTENCY,
                        severity=QualitySeverity.MINOR,
                        description=f"Score buiten verwachte range (0-10) in {key}: {value}",
                        location="score validatie",
                        suggestion="Controleer score bereiken en corrigeer indien nodig",
                        confidence=0.7
                    ))
        
        return issues
    
    def _domain_specific_validation(self, content: str, section: ReportSection) -> List[QualityIssue]:
        """Domein-specifieke validatie voor medische en juridische content"""
        issues = []
        content_lower = content.lower()
        
        # Medische validatie
        if section in [ReportSection.MEDISCHE_SITUATIE, ReportSection.BELASTBAARHEID]:
            # Check voor verouderde terminologie
            outdated_terms = {
                'tics stoornissen': 'ticsstoornissen',
                'asperger': 'autismespectrumstoornis',
                'manic-depressief': 'bipolaire stoornis',
                'multiple sclerose': 'multiple sclerose (MS)'
            }
            
            for old_term, new_term in outdated_terms.items():
                if old_term in content_lower:
                    issues.append(QualityIssue(
                        type=QualityIssueType.OUTDATED_INFORMATION,
                        severity=QualitySeverity.MINOR,
                        description=f"Mogelijk verouderde terminologie: '{old_term}'",
                        location="medische terminologie",
                        suggestion=f"Overweeg modernere terminologie zoals '{new_term}'",
                        confidence=0.6
                    ))
            
            # Check voor onduidelijke medische claims
            vague_medical_terms = ['ernstig', 'licht', 'veel', 'weinig', 'soms', 'vaak']
            found_vague = [term for term in vague_medical_terms if term in content_lower]
            if len(found_vague) > 3:
                issues.append(QualityIssue(
                    type=QualityIssueType.INSUFFICIENT_DETAIL,
                    severity=QualitySeverity.MINOR,
                    description=f"Veel vage medische bewoordingen: {', '.join(found_vague[:3])}",
                    location="medische precisie",
                    suggestion="Gebruik meer specifieke en meetbare beschrijvingen",
                    confidence=0.5
                ))
        
        # Juridische validatie
        if section in [ReportSection.ADVIES, ReportSection.CONCLUSIE]:
            # Check voor verouderde wetgeving referenties
            outdated_laws = {
                'wao': 'WIA (WAO is vervangen)',
                'ziektewet art': 'controleer actualiteit Ziektewet artikelen'
            }
            
            for old_ref, suggestion in outdated_laws.items():
                if old_ref in content_lower:
                    issues.append(QualityIssue(
                        type=QualityIssueType.LEGAL_ACCURACY,
                        severity=QualitySeverity.MAJOR,
                        description=f"Mogelijk verouderde wetgeving referentie: '{old_ref}'",
                        location="juridische accuratesse",
                        suggestion=suggestion,
                        confidence=0.8
                    ))
            
            # Check voor te stellige juridische uitspraken
            absolute_legal_terms = ['zeker', 'absoluut', 'onmogelijk', 'altijd', 'nooit']
            found_absolute = [term for term in absolute_legal_terms if term in content_lower]
            if found_absolute:
                issues.append(QualityIssue(
                    type=QualityIssueType.UNPROFESSIONAL_TONE,
                    severity=QualitySeverity.MINOR,
                    description=f"Absolute uitspraken in juridische context: {', '.join(found_absolute)}",
                    location="juridische nuancering",
                    suggestion="Gebruik meer genuanceerde bewoordingen in juridische adviezen",
                    confidence=0.6
                ))
        
        return issues

    def _rule_based_validation(self, content: str, section: ReportSection) -> List[QualityIssue]:
        """Regel-gebaseerde kwaliteitsvalidatie"""
        issues = []
        content_lower = content.lower()
        
        # Check lengte
        if len(content) < 100:
            issues.append(QualityIssue(
                type=QualityIssueType.INSUFFICIENT_DETAIL,
                severity=QualitySeverity.MAJOR,
                description="Content is te kort voor een professionele rapport sectie",
                location="gehele tekst",
                suggestion="Voeg meer detail en uitleg toe",
                confidence=0.9
            ))
        
        # Check professionele terminologie
        section_patterns = self.quality_patterns.get(section.value, {})
        required_elements = section_patterns.get("required_elements", [])
        
        missing_elements = []
        for element in required_elements:
            if element.lower() not in content_lower:
                missing_elements.append(element)
        
        if missing_elements:
            issues.append(QualityIssue(
                type=QualityIssueType.INCOMPLETE_SECTION,
                severity=QualitySeverity.MAJOR,
                description=f"Ontbrekende elementen: {', '.join(missing_elements)}",
                location="structuur",
                suggestion=f"Voeg informatie toe over: {', '.join(missing_elements)}",
                confidence=0.8
            ))
        
        # Check vermijd woorden
        avoid_words = section_patterns.get("avoid_words", [])
        found_avoid_words = []
        for word in avoid_words:
            if word.lower() in content_lower:
                found_avoid_words.append(word)
        
        if found_avoid_words:
            issues.append(QualityIssue(
                type=QualityIssueType.UNPROFESSIONAL_TONE,
                severity=QualitySeverity.MINOR,
                description=f"Ongewenste woorden gevonden: {', '.join(found_avoid_words)}",
                location="toon",
                suggestion="Gebruik meer objectieve en professionele formulering",
                confidence=0.7
            ))
        
        # Check structuur indicatoren
        structure_indicators = section_patterns.get("structure_indicators", [])
        found_indicators = sum(1 for indicator in structure_indicators if indicator.lower() in content_lower)
        
        if found_indicators < len(structure_indicators) * 0.5:  # Minder dan 50% van verwachte structuur
            issues.append(QualityIssue(
                type=QualityIssueType.MISSING_STRUCTURE,
                severity=QualitySeverity.MAJOR,
                description="Ontbrekende structuur elementen",
                location="organisatie",
                suggestion="Verbeter de structuur met duidelijke kopjes en logische volgorde",
                confidence=0.6
            ))
        
        return issues
    
    async def _ai_quality_analysis(
        self, 
        content: str, 
        section: ReportSection,
        context_chunks: List[str] = None
    ) -> Dict[str, Any]:
        """AI-gedreven kwaliteitsanalyse"""
        
        context_info = ""
        if context_chunks:
            context_info = f"\n\nBeschikbare context:\n{' '.join(context_chunks[:3])}"
        
        prompt = f"""
Je bent een senior arbeidsdeskundige die de kwaliteit van rapport secties beoordeelt.
Analyseer deze {section.value} sectie op kwaliteit, professionaliteit en volledigheid.

Te analyseren tekst:
{content}
{context_info}

Beoordeel op de volgende aspecten:
1. FEITELIJKE JUISTHEID: Zijn de feiten correct en consistent?
2. PROFESSIONALITEIT: Is de toon professioneel en objectief?
3. VOLLEDIGHEID: Bevat de sectie alle verwachte elementen?
4. STRUCTUUR: Is de tekst logisch opgebouwd?
5. TERMINOLOGIE: Wordt correcte vakterminologie gebruikt?
6. COMPLIANCE: Voldoet het aan privacy en objectiviteitsregels?

Geef je beoordeling in dit JSON formaat:

{{
    "quality_score": 0.0-1.0,
    "issues": [
        {{
            "type": "issue_type",
            "severity": "critical|major|minor|suggestion", 
            "description": "beschrijving van het probleem",
            "location": "waar in de tekst",
            "suggestion": "concrete verbetering",
            "confidence": 0.0-1.0
        }}
    ],
    "strengths": ["lijst van sterke punten"],
    "specific_feedback": "gedetailleerde feedback"
}}

Wees specifiek en constructief in je feedback.
"""
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            )
            response_text = response.content[0].text
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # Convert to QualityIssue objects
                issues = []
                for issue_data in result.get("issues", []):
                    try:
                        issues.append(QualityIssue(
                            type=QualityIssueType(issue_data.get("type", "logical_flow")),
                            severity=QualitySeverity(issue_data.get("severity", "minor")),
                            description=issue_data.get("description", ""),
                            location=issue_data.get("location", "onbekend"),
                            suggestion=issue_data.get("suggestion", ""),
                            confidence=float(issue_data.get("confidence", 0.5))
                        ))
                    except (ValueError, TypeError):
                        # Skip invalid issues
                        continue
                
                return {
                    "quality_score": float(result.get("quality_score", 0.5)),
                    "issues": issues,
                    "strengths": result.get("strengths", []),
                    "feedback": result.get("specific_feedback", "")
                }
            
            # Fallback parsing
            return {
                "quality_score": 0.6,
                "issues": [],
                "strengths": ["AI analyse voltooid"],
                "feedback": "Basis AI analyse uitgevoerd"
            }
            
        except Exception as e:
            self.logger.error(f"AI quality analysis failed: {e}")
            return {
                "quality_score": 0.5,
                "issues": [],
                "strengths": [],
                "feedback": "AI analyse gefaald"
            }
    
    def _compliance_check(self, content: str, section: ReportSection) -> List[QualityIssue]:
        """Check compliance met arbeidsdeskundige standaarden"""
        issues = []
        content_lower = content.lower()
        
        # Privacy check
        privacy_patterns = [
            r'\b\d{9}\b',  # BSN-achtige nummers
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Volledige namen pattern
            r'meneer [A-Z][a-z]+|mevrouw [A-Z][a-z]+'  # Formele namen
        ]
        
        for pattern in privacy_patterns:
            if re.search(pattern, content):
                issues.append(QualityIssue(
                    type=QualityIssueType.COMPLIANCE_ISSUE,
                    severity=QualitySeverity.CRITICAL,
                    description="Mogelijk privacy-gevoelige informatie gedetecteerd",
                    location="privacy",
                    suggestion="Verwijder of anonymiseer persoonlijke gegevens",
                    confidence=0.8
                ))
        
        # Objectiviteit check
        subjective_phrases = [
            "ik denk", "mijn mening", "volgens mij", "ik vind",
            "het lijkt", "waarschijnlijk", "misschien wel"
        ]
        
        found_subjective = []
        for phrase in subjective_phrases:
            if phrase in content_lower:
                found_subjective.append(phrase)
        
        if found_subjective:
            issues.append(QualityIssue(
                type=QualityIssueType.UNPROFESSIONAL_TONE,
                severity=QualitySeverity.MAJOR,
                description=f"Subjectieve formuleringen: {', '.join(found_subjective)}",
                location="objectiviteit",
                suggestion="Gebruik objectieve, feitelijke formuleringen",
                confidence=0.9
            ))
        
        return issues
    
    def _filter_and_prioritize_issues(self, issues: List[QualityIssue]) -> List[QualityIssue]:
        """Filter en prioriteer issues om noise te verminderen"""
        if not issues:
            return issues
        
        # Groepeer gelijkaardige issues
        issue_groups = {}
        for issue in issues:
            key = (issue.type, issue.location)
            if key not in issue_groups:
                issue_groups[key] = []
            issue_groups[key].append(issue)
        
        # Selecteer beste issue per groep
        filtered_issues = []
        for group in issue_groups.values():
            # Sorteer op confidence en selecteer beste
            best_issue = max(group, key=lambda x: x.confidence)
            
            # Combine descriptions if multiple similar issues
            if len(group) > 1:
                descriptions = [i.description for i in group]
                best_issue.description = f"{best_issue.description} (+{len(group)-1} gelijkaardige issues)"
            
            filtered_issues.append(best_issue)
        
        # Sorteer op severity en confidence
        severity_order = {
            QualitySeverity.CRITICAL: 4,
            QualitySeverity.MAJOR: 3,
            QualitySeverity.MINOR: 2,
            QualitySeverity.SUGGESTION: 1
        }
        
        filtered_issues.sort(key=lambda x: (severity_order[x.severity], x.confidence), reverse=True)
        
        # Limiteer aantal issues om overwhelm te voorkomen
        return filtered_issues[:15]
    
    def _calculate_comprehensive_quality_metrics(
        self, 
        issues: List[QualityIssue], 
        content: str, 
        section: ReportSection,
        ai_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Bereken uitgebreide kwaliteitsmetrics"""
        
        # Basis overall score
        base_score = 1.0
        
        # Trek punten af op basis van issues (gewogen)
        severity_weights = {
            QualitySeverity.CRITICAL: 0.4,
            QualitySeverity.MAJOR: 0.25,
            QualitySeverity.MINOR: 0.1,
            QualitySeverity.SUGGESTION: 0.05
        }
        
        for issue in issues:
            weight = severity_weights.get(issue.severity, 0.1)
            base_score -= weight * issue.confidence
        
        # Bonus voor lengte (optimaal tussen min en max voor sectie)
        section_patterns = self.quality_patterns.get(section.value, {})
        min_words = section_patterns.get("min_word_count", 50)
        max_words = section_patterns.get("max_word_count", 500)
        
        word_count = len(content.split())
        length_bonus = 0.0
        
        if min_words <= word_count <= max_words:
            length_bonus = 0.1
        elif word_count >= min_words * 0.8:  # 80% van minimum
            length_bonus = 0.05
        
        # Terminologie bonus
        professional_term_count = 0
        content_lower = content.lower()
        for category, terms in self.professional_terms.items():
            for term in terms:
                if term.lower() in content_lower:
                    professional_term_count += 1
        
        terminology_bonus = min(0.15, professional_term_count * 0.02)
        
        # AI quality bonus
        ai_score = ai_analysis.get("quality_score", 0.5)
        ai_bonus = (ai_score - 0.5) * 0.2  # Max 0.1 bonus
        
        # Bereken section-specific scores
        section_scores = {
            "content_length": max(0, min(1, word_count / max_words)),
            "terminology_usage": min(1, professional_term_count / 5),  # Normaliseer op 5 termen
            "language_quality": 1 - len([i for i in issues if i.type == QualityIssueType.LANGUAGE_QUALITY]) * 0.2,
            "compliance": 1 - len([i for i in issues if i.type == QualityIssueType.COMPLIANCE_ISSUE]) * 0.3,
            "structure": 1 - len([i for i in issues if i.type == QualityIssueType.MISSING_STRUCTURE]) * 0.25
        }
        
        # Normalize section scores
        for key in section_scores:
            section_scores[key] = max(0, min(1, section_scores[key]))
        
        # Calculate improvement potential
        critical_issues = len([i for i in issues if i.severity == QualitySeverity.CRITICAL])
        major_issues = len([i for i in issues if i.severity == QualitySeverity.MAJOR])
        improvement_potential = min(1.0, (critical_issues * 0.3 + major_issues * 0.2))
        
        final_score = max(0.0, min(1.0, base_score + length_bonus + terminology_bonus + ai_bonus))
        
        return {
            "overall_score": final_score,
            "section_scores": section_scores,
            "components": {
                "base_score": base_score,
                "length_bonus": length_bonus,
                "terminology_bonus": terminology_bonus,
                "ai_bonus": ai_bonus
            },
            "metrics": {
                "word_count": word_count,
                "professional_terms": professional_term_count,
                "critical_issues": critical_issues,
                "major_issues": major_issues,
                "total_issues": len(issues)
            },
            "improvement_potential": improvement_potential
        }
    
    def _generate_enhanced_recommendations(
        self, 
        issues: List[QualityIssue], 
        section: ReportSection,
        quality_metrics: Dict[str, Any]
    ) -> List[str]:
        """Genereer verbeterde, prioritized aanbevelingen"""
        recommendations = []
        
        # Prioriteitscategorieën
        high_priority_issues = [i for i in issues if i.severity in [QualitySeverity.CRITICAL, QualitySeverity.MAJOR]]
        medium_priority_issues = [i for i in issues if i.severity == QualitySeverity.MINOR]
        
        # High priority recommendations eerst
        if high_priority_issues:
            recommendations.append("🔥 PRIORITEIT - Direct aandacht vereist:")
            for issue in high_priority_issues[:3]:  # Top 3 critical issues
                recommendations.append(f"   • {issue.suggestion}")
        
        # Section-specific recommendations
        section_patterns = self.quality_patterns.get(section.value, {})
        word_count = quality_metrics["metrics"]["word_count"]
        min_words = section_patterns.get("min_word_count", 50)
        
        if word_count < min_words:
            recommendations.append(f"📝 Uitbreiding: Voeg meer detail toe (huidige lengte: {word_count} woorden, minimum: {min_words})")
        
        # Quality indicators recommendations
        quality_indicators = section_patterns.get("quality_indicators", [])
        content_lower = self.quality_patterns.get(section.value, {}).get("tone_words", [])
        
        missing_indicators = []
        for indicator in quality_indicators:
            # Simple check - in productie zou dit sophisticater zijn
            if not any(word in indicator.lower() for word in content_lower):
                missing_indicators.append(indicator)
        
        if missing_indicators:
            recommendations.append(f"⭐ Kwaliteitsverbetering: Focus op {', '.join(missing_indicators)}")
        
        # Terminology recommendations
        professional_term_count = quality_metrics["metrics"]["professional_terms"]
        if professional_term_count < 3:
            recommendations.append("📚 Terminologie: Gebruik meer specifieke arbeidsdeskundige vakterminologie")
        
        # Medium priority recommendations
        if medium_priority_issues and len(recommendations) < 8:
            recommendations.append("✨ Verdere verbetering:")
            for issue in medium_priority_issues[:2]:
                recommendations.append(f"   • {issue.suggestion}")
        
        # AI-driven recommendations
        if quality_metrics["improvement_potential"] > 0.3:
            recommendations.append("🎯 Strategische verbetering: Overweeg grondige herziening van deze sectie")
        elif quality_metrics["improvement_potential"] > 0.1:
            recommendations.append("📈 Incrementele verbetering: Enkele aanpassingen kunnen de kwaliteit significant verbeteren")
        
        return recommendations
    
    def _identify_comprehensive_strengths(
        self, 
        content: str, 
        section: ReportSection,
        ai_analysis: Dict[str, Any],
        quality_metrics: Dict[str, Any]
    ) -> List[str]:
        """Identificeer uitgebreide sterke punten"""
        strengths = list(ai_analysis.get("strengths", []))
        
        # Kwantitatieve sterkte analyse
        metrics = quality_metrics["metrics"]
        section_scores = quality_metrics["section_scores"]
        
        # Length appropriateness
        section_patterns = self.quality_patterns.get(section.value, {})
        min_words = section_patterns.get("min_word_count", 50)
        max_words = section_patterns.get("max_word_count", 500)
        word_count = metrics["word_count"]
        
        if min_words <= word_count <= max_words:
            strengths.append(f"✅ Optimale lengte ({word_count} woorden)")
        elif word_count >= min_words:
            strengths.append("✅ Voldoende detail")
        
        # Professional terminology usage
        if metrics["professional_terms"] >= 5:
            strengths.append(f"📚 Excellent terminologie gebruik ({metrics['professional_terms']} vaktermen)")
        elif metrics["professional_terms"] >= 3:
            strengths.append("📚 Goede terminologie gebruik")
        
        # Section-specific strengths
        if section_scores["compliance"] >= 0.9:
            strengths.append("⚖️ Uitstekende compliance met professionele standaarden")
        elif section_scores["compliance"] >= 0.7:
            strengths.append("⚖️ Goede compliance met professionele standaarden")
        
        if section_scores["structure"] >= 0.8:
            strengths.append("🏗️ Heldere en logische structuur")
        
        if section_scores["language_quality"] >= 0.8:
            strengths.append("✍️ Professionele schrijfstijl en taalgebruik")
        
        # Issue-based strengths (absence of problems is a strength)
        if metrics["critical_issues"] == 0:
            strengths.append("🎯 Geen kritieke kwaliteitsproblemen")
        
        if metrics["total_issues"] <= 2:
            strengths.append("⭐ Hoge overall kwaliteit met minimale issues")
        
        # AI confidence strength
        ai_confidence = quality_metrics.get("ai_confidence", 0.5)
        if ai_confidence >= 0.8:
            strengths.append("🤖 AI analyse toont hoge content betrouwbaarheid")
        
        return strengths[:8]  # Limiteer tot 8 sterke punten
    
    def _determine_compliance_status(self, compliance_issues: List[QualityIssue]) -> str:
        """Bepaal compliance status"""
        critical_compliance = [i for i in compliance_issues if i.severity == QualitySeverity.CRITICAL]
        major_compliance = [i for i in compliance_issues if i.severity == QualitySeverity.MAJOR]
        
        if critical_compliance:
            return "non_compliant"
        elif major_compliance:
            return "partially_compliant"
        elif compliance_issues:
            return "mostly_compliant"
        else:
            return "fully_compliant"
    
    def _calculate_quality_score(
        self, 
        issues: List[QualityIssue], 
        content: str, 
        section: ReportSection
    ) -> float:
        """Bereken overall kwaliteitsscore"""
        
        # Start met basis score
        base_score = 1.0
        
        # Trek punten af op basis van issues
        for issue in issues:
            if issue.severity == QualitySeverity.CRITICAL:
                base_score -= 0.3 * issue.confidence
            elif issue.severity == QualitySeverity.MAJOR:
                base_score -= 0.2 * issue.confidence
            elif issue.severity == QualitySeverity.MINOR:
                base_score -= 0.1 * issue.confidence
            elif issue.severity == QualitySeverity.SUGGESTION:
                base_score -= 0.05 * issue.confidence
        
        # Bonus voor lengte (binnen redelijke grenzen)
        length_bonus = 0.0
        if 200 <= len(content) <= 800:
            length_bonus = 0.05
        elif 100 <= len(content) < 200:
            length_bonus = 0.02
        
        # Bonus voor professionele terminologie
        professional_term_count = 0
        content_lower = content.lower()
        for category, terms in self.professional_terms.items():
            for term in terms:
                if term.lower() in content_lower:
                    professional_term_count += 1
        
        terminology_bonus = min(0.1, professional_term_count * 0.02)
        
        final_score = max(0.0, min(1.0, base_score + length_bonus + terminology_bonus))
        return final_score
    
    def _generate_recommendations(
        self, 
        issues: List[QualityIssue], 
        section: ReportSection
    ) -> List[str]:
        """Genereer concrete aanbevelingen"""
        recommendations = []
        
        # Groepeer issues per type
        issue_groups = {}
        for issue in issues:
            if issue.type not in issue_groups:
                issue_groups[issue.type] = []
            issue_groups[issue.type].append(issue)
        
        # Genereer aanbevelingen per groep
        for issue_type, type_issues in issue_groups.items():
            if issue_type == QualityIssueType.INSUFFICIENT_DETAIL:
                recommendations.append("Voeg meer specifieke details en uitleg toe aan de sectie")
            elif issue_type == QualityIssueType.MISSING_STRUCTURE:
                recommendations.append("Verbeter de structuur met duidelijke alinea's en logische volgorde")
            elif issue_type == QualityIssueType.UNPROFESSIONAL_TONE:
                recommendations.append("Gebruik meer professionele en objectieve formulering")
            elif issue_type == QualityIssueType.COMPLIANCE_ISSUE:
                recommendations.append("Controleer en verwijder privacy-gevoelige informatie")
            elif issue_type == QualityIssueType.INCORRECT_TERMINOLOGY:
                recommendations.append("Gebruik correcte arbeidsdeskundige vakterminologie")
        
        # Sectie-specifieke aanbevelingen
        section_recommendations = {
            ReportSection.MEDISCHE_SITUATIE: [
                "Zorg voor chronologische volgorde van medische informatie",
                "Vermeld relevante diagnoses en behandelingen"
            ],
            ReportSection.BELASTBAARHEID: [
                "Beschrijf zowel fysieke als mentale aspecten",
                "Verwijs naar FCE resultaten indien beschikbaar"
            ],
            ReportSection.ADVIES: [
                "Geef concrete en uitvoerbare aanbevelingen",
                "Vermeld tijdslijn en verantwoordelijkheden"
            ]
        }
        
        if section in section_recommendations:
            recommendations.extend(section_recommendations[section])
        
        return list(set(recommendations))  # Remove duplicates
    
    def _identify_strengths(
        self, 
        content: str, 
        section: ReportSection, 
        ai_analysis: Dict[str, Any]
    ) -> List[str]:
        """Identificeer sterke punten in de content"""
        strengths = ai_analysis.get("strengths", [])
        
        # Voeg automatisch gedetecteerde sterke punten toe
        content_lower = content.lower()
        
        # Check voor professionele structuur
        if any(indicator in content_lower for indicator in ["ten eerste", "ten tweede", "daarnaast", "concluderend"]):
            strengths.append("Goede structuur met duidelijke opbouw")
        
        # Check voor specifieke terminologie
        terminology_count = sum(
            1 for terms in self.professional_terms.values() 
            for term in terms if term.lower() in content_lower
        )
        
        if terminology_count >= 3:
            strengths.append("Goede gebruik van vakterminologie")
        
        # Check voor objectieve toon
        if not any(subjective in content_lower for subjective in ["ik denk", "mijn mening", "volgens mij"]):
            strengths.append("Objectieve en professionele toon")
        
        # Check voor voldoende detail
        if len(content) >= 300:
            strengths.append("Voldoende detail en uitgebreide beschrijving")
        
        return strengths
    
    def _create_fallback_report(self, content: str, section: ReportSection) -> QualityReport:
        """Creëer fallback rapport bij falen van analyse"""
        return QualityReport(
            overall_score=0.5,
            issues=[
                QualityIssue(
                    type=QualityIssueType.LOGICAL_FLOW,
                    severity=QualitySeverity.MINOR,
                    description="Kwaliteitsanalyse kon niet volledig worden uitgevoerd",
                    location="systeem",
                    suggestion="Handmatige review aanbevolen",
                    confidence=1.0
                )
            ],
            strengths=["Content gegenereerd"],
            recommendations=["Voer handmatige kwaliteitscontrole uit"],
            section=section,
            original_text=content,
            validation_timestamp=datetime.utcnow().isoformat()
        )
    
    async def improve_content(
        self, 
        quality_report: QualityReport,
        max_iterations: int = 3,
        improvement_strategy: str = "comprehensive",
        target_score: float = 0.8
    ) -> Dict[str, Any]:
        """Enhanced content improvement met multiple strategieën"""
        
        start_time = datetime.utcnow()
        original_score = quality_report.overall_score
        
        if original_score >= target_score:
            self.logger.info(f"Content quality already meets target ({original_score:.2f} >= {target_score})")
            return {
                "improved_text": quality_report.original_text,
                "original_score": original_score,
                "final_score": original_score,
                "improvement": 0.0,
                "iterations_used": 0,
                "strategy_used": "none",
                "processing_time_ms": 0
            }
        
        current_text = quality_report.original_text
        current_report = quality_report
        iterations_used = 0
        
        improvement_log = []
        
        for iteration in range(max_iterations):
            self.logger.info(f"Improvement iteration {iteration + 1} using {improvement_strategy} strategy")
            iterations_used += 1
            
            # Selecteer issues op basis van strategie
            target_issues = self._select_improvement_targets(
                current_report.issues, 
                improvement_strategy, 
                iteration
            )
            
            if not target_issues:
                self.logger.info("No more improvement targets found")
                break
            
            # Genereer verbeteringsaanwijzingen
            improvement_prompt = self._create_enhanced_improvement_prompt(
                current_text, 
                target_issues, 
                current_report.section,
                improvement_strategy,
                iteration
            )
            
            try:
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,  # Verhoogd voor betere output
                    messages=[
                        {
                            "role": "user", 
                            "content": improvement_prompt
                        }
                    ]
                )
                improved_text = response.content[0].text.strip()
                
                # Valideer de verbetering
                new_report = await self.validate_content(
                    improved_text, 
                    current_report.section
                )
                
                score_improvement = new_report.overall_score - current_report.overall_score
                
                improvement_log.append({
                    "iteration": iteration + 1,
                    "original_score": current_report.overall_score,
                    "new_score": new_report.overall_score,
                    "improvement": score_improvement,
                    "issues_addressed": len(target_issues),
                    "remaining_issues": len(new_report.issues)
                })
                
                if score_improvement > 0.05:  # Minimum meaningful improvement
                    current_text = improved_text
                    current_report = new_report
                    self.logger.info(
                        f"Iteration {iteration + 1} successful: "
                        f"score improved by {score_improvement:.3f} to {new_report.overall_score:.2f}"
                    )
                    
                    # Check if target reached
                    if new_report.overall_score >= target_score:
                        self.logger.info(f"Target score {target_score} reached")
                        break
                else:
                    self.logger.info(
                        f"Iteration {iteration + 1} minimal improvement: {score_improvement:.3f}"
                    )
                    # Try different strategy on next iteration
                    if improvement_strategy == "comprehensive":
                        improvement_strategy = "focused"
                    elif improvement_strategy == "focused":
                        improvement_strategy = "conservative"
                    else:
                        break  # No more strategies to try
                        
            except Exception as e:
                self.logger.error(f"Content improvement iteration {iteration + 1} failed: {e}")
                improvement_log.append({
                    "iteration": iteration + 1,
                    "error": str(e),
                    "original_score": current_report.overall_score
                })
                break
        
        final_improvement = current_report.overall_score - original_score
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        self.logger.info(
            f"Content improvement completed: {original_score:.2f} -> {current_report.overall_score:.2f} "
            f"(+{final_improvement:.3f}) in {iterations_used} iterations"
        )
        
        return {
            "improved_text": current_text,
            "original_score": original_score,
            "final_score": current_report.overall_score,
            "improvement": final_improvement,
            "iterations_used": iterations_used,
            "strategy_used": improvement_strategy,
            "processing_time_ms": processing_time,
            "improvement_log": improvement_log,
            "final_report": current_report
        }
    
    def _select_improvement_targets(
        self, 
        issues: List[QualityIssue], 
        strategy: str, 
        iteration: int
    ) -> List[QualityIssue]:
        """Selecteer issues om te verbeteren op basis van strategie"""
        
        if not issues:
            return []
        
        if strategy == "comprehensive":
            # Focus op alle major en critical issues
            return [i for i in issues if i.severity in [QualitySeverity.CRITICAL, QualitySeverity.MAJOR]][:5]
        
        elif strategy == "focused":
            # Focus op hoogste prioriteit issues
            critical_issues = [i for i in issues if i.severity == QualitySeverity.CRITICAL]
            if critical_issues:
                return critical_issues[:2]
            else:
                major_issues = [i for i in issues if i.severity == QualitySeverity.MAJOR]
                return major_issues[:3]
        
        elif strategy == "conservative":
            # Focus op 1-2 meest betrouwbare fixes
            high_confidence_issues = [i for i in issues if i.confidence >= 0.8]
            if high_confidence_issues:
                return sorted(high_confidence_issues, 
                             key=lambda x: (x.severity.value, x.confidence), 
                             reverse=True)[:2]
            else:
                return issues[:1]  # Just one issue
        
        else:
            return issues[:3]  # Default fallback
    
    def _create_enhanced_improvement_prompt(
        self, 
        content: str, 
        issues: List[QualityIssue], 
        section: ReportSection,
        strategy: str,
        iteration: int
    ) -> str:
        """Creëer geavanceerde improvement prompt"""
        
        issues_text = "\n".join([
            f"- {issue.severity.value.upper()}: {issue.description}\n  Oplossing: {issue.suggestion}\n  Locatie: {issue.location}"
            for issue in issues
        ])
        
        strategy_instructions = {
            "comprehensive": "Maak uitgebreide verbeteringen aan de gehele tekst.",
            "focused": "Focus specifiek op de meest kritieke problemen.",
            "conservative": "Maak minimale, zeer betrouwbare aanpassingen."
        }
        
        section_guidance = {
            ReportSection.MEDISCHE_SITUATIE: "Focus op medische accuratesse, chronologie en objectieve beschrijving.",
            ReportSection.BELASTBAARHEID: "Emphasis op concrete capaciteiten, beperkingen en onderbouwing.",
            ReportSection.ADVIES: "Zorg voor haalbare, specifieke aanbevelingen met duidelijke stappen.",
            ReportSection.CONCLUSIE: "Maak een heldere synthese en logische afsluiting.",
            # Removed duplicate VISIE_AD - using ADVIES instead
            ReportSection.MOGELIJKHEDEN: "Analyseer functie-eisen versus capaciteiten grondig."
        }
        
        return f"""
Je bent een senior arbeidsdeskundige editor die content verbetert voor hoge kwaliteit rapporten.

STRATEGIE: {strategy_instructions.get(strategy, "Standaard verbetering")}
ITERATIE: {iteration + 1}
SECTIE: {section.value}

SPECIFIEKE RICHTLIJNEN VOOR DEZE SECTIE:
{section_guidance.get(section, "Algemene arbeidsdeskundige richtlijnen")}

HUIDIGE TEKST:
{content}

GEÏDENTIFICEERDE PROBLEMEN:
{issues_text}

VERBETERINGSINSTRUCTIES:
1. Los de geïdentificeerde problemen systematisch op
2. Behoud alle feitelijke informatie en kernboodschap
3. Verbeter professionaliteit, structuur en leesbaarheid
4. Gebruik correcte Nederlandse arbeidsdeskundige terminologie
5. Zorg voor objectieve, evidence-based bewoordingen
6. Respecteer privacy en compliance regels
7. Maak de tekst geschikt voor professioneel gebruik

{"BELANGRIJK: Maak alleen minimale aanpassingen die nodig zijn." if strategy == "conservative" else "BELANGRIJK: Zorg voor substantiële kwaliteitsverbetering."}

SCHRIJF DE VERBETERDE VERSIE (alleen de tekst, geen uitleg):
"""
    
    async def batch_improve_content(
        self, 
        quality_reports: List[QualityReport],
        target_score: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Verbeter meerdere content stukken in batch"""
        
        self.logger.info(f"Starting batch improvement for {len(quality_reports)} content pieces")
        
        results = []
        for i, report in enumerate(quality_reports):
            self.logger.info(f"Processing batch item {i+1}/{len(quality_reports)}")
            
            try:
                improvement_result = await self.improve_content(
                    report, 
                    max_iterations=2,  # Lower for batch processing
                    target_score=target_score
                )
                results.append(improvement_result)
                
            except Exception as e:
                self.logger.error(f"Batch improvement failed for item {i+1}: {e}")
                results.append({
                    "improved_text": report.original_text,
                    "original_score": report.overall_score,
                    "final_score": report.overall_score,
                    "improvement": 0.0,
                    "error": str(e)
                })
        
        # Calculate batch statistics
        successful_improvements = [r for r in results if r.get("improvement", 0) > 0]
        avg_improvement = sum(r.get("improvement", 0) for r in results) / len(results)
        
        self.logger.info(
            f"Batch improvement completed: {len(successful_improvements)}/{len(results)} improved, "
            f"average improvement: {avg_improvement:.3f}"
        )
        
        return results
    
    def record_quality_metrics(self, quality_report: QualityReport, processing_time_ms: float = None):
        """Record quality metrics to the monitoring system"""
        try:
            from app.utils.rag_monitoring import metrics_collector, ComponentType, MetricType
            
            # Record overall quality score
            metrics_collector.record_metric(
                component=ComponentType.QUALITY_CONTROLLER,
                metric_type=MetricType.QUALITY_SCORE,
                value=quality_report.overall_score,
                metadata={
                    "section": quality_report.section.value,
                    "total_issues": len(quality_report.issues),
                    "critical_issues": len([i for i in quality_report.issues if i.severity == QualitySeverity.CRITICAL]),
                    "major_issues": len([i for i in quality_report.issues if i.severity == QualitySeverity.MAJOR]),
                    "compliance_status": quality_report.compliance_status,
                    "improvement_potential": quality_report.improvement_potential
                }
            )
            
            # Record processing time if provided
            if processing_time_ms:
                metrics_collector.record_metric(
                    component=ComponentType.QUALITY_CONTROLLER,
                    metric_type=MetricType.PROCESSING_TIME,
                    value=processing_time_ms / 1000,  # Convert to seconds
                    metadata={"section": quality_report.section.value}
                )
            
            # Record section-specific quality scores
            if quality_report.section_scores:
                for metric_name, score in quality_report.section_scores.items():
                    metrics_collector.record_metric(
                        component=ComponentType.QUALITY_CONTROLLER,
                        metric_type=MetricType.QUALITY_SCORE,
                        value=score,
                        metadata={
                            "section": quality_report.section.value,
                            "metric_type": metric_name
                        },
                        tags={"quality_metric": metric_name}
                    )
            
        except ImportError:
            self.logger.warning("Monitoring system not available for quality metrics recording")
        except Exception as e:
            self.logger.error(f"Failed to record quality metrics: {e}")
    
    def get_quality_trends(self, section: ReportSection = None, hours: int = 24) -> Dict[str, Any]:
        """Get quality trends and analytics"""
        try:
            from app.utils.rag_monitoring import metrics_collector, ComponentType, MetricType
            from datetime import datetime, timedelta
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Get quality metrics from monitoring system
            quality_metrics = []
            for metric in metrics_collector.metrics_history:
                if (metric.component == ComponentType.QUALITY_CONTROLLER and 
                    metric.metric_type == MetricType.QUALITY_SCORE and
                    metric.timestamp > cutoff_time):
                    
                    # Filter by section if specified
                    if section is None or metric.metadata.get("section") == section.value:
                        quality_metrics.append(metric)
            
            if not quality_metrics:
                return {
                    "error": "No quality data available for specified parameters",
                    "section": section.value if section else "all",
                    "hours": hours
                }
            
            # Calculate trends
            scores = [m.value for m in quality_metrics]
            recent_scores = scores[-10:] if len(scores) > 10 else scores
            older_scores = scores[:-10] if len(scores) > 10 else []
            
            trend_direction = "stable"
            if older_scores and recent_scores:
                recent_avg = sum(recent_scores) / len(recent_scores)
                older_avg = sum(older_scores) / len(older_scores)
                
                if recent_avg > older_avg + 0.05:
                    trend_direction = "improving"
                elif recent_avg < older_avg - 0.05:
                    trend_direction = "declining"
            
            # Issue analysis
            total_issues = sum(m.metadata.get("total_issues", 0) for m in quality_metrics)
            critical_issues = sum(m.metadata.get("critical_issues", 0) for m in quality_metrics)
            major_issues = sum(m.metadata.get("major_issues", 0) for m in quality_metrics)
            
            # Compliance analysis
            compliance_statuses = [m.metadata.get("compliance_status", "unknown") for m in quality_metrics]
            fully_compliant = compliance_statuses.count("fully_compliant")
            compliance_rate = fully_compliant / len(compliance_statuses) if compliance_statuses else 0
            
            return {
                "section": section.value if section else "all",
                "time_range_hours": hours,
                "total_evaluations": len(quality_metrics),
                "quality_summary": {
                    "current_average": sum(recent_scores) / len(recent_scores) if recent_scores else 0,
                    "overall_average": sum(scores) / len(scores),
                    "min_score": min(scores),
                    "max_score": max(scores),
                    "trend_direction": trend_direction
                },
                "issue_analysis": {
                    "total_issues": total_issues,
                    "critical_issues": critical_issues,
                    "major_issues": major_issues,
                    "avg_issues_per_evaluation": total_issues / len(quality_metrics) if quality_metrics else 0
                },
                "compliance_analysis": {
                    "compliance_rate": compliance_rate,
                    "fully_compliant_count": fully_compliant,
                    "total_evaluations": len(compliance_statuses)
                },
                "improvement_potential": {
                    "avg_potential": sum(m.metadata.get("improvement_potential", 0) for m in quality_metrics) / len(quality_metrics),
                    "high_potential_count": len([m for m in quality_metrics if m.metadata.get("improvement_potential", 0) > 0.3])
                }
            }
            
        except ImportError:
            return {"error": "Monitoring system not available"}
        except Exception as e:
            self.logger.error(f"Failed to get quality trends: {e}")
            return {"error": str(e)}
    
    async def validate_and_record(
        self,
        content: str,
        section: ReportSection,
        context_chunks: List[str] = None,
        complexity_level: ComplexityLevel = ComplexityLevel.MEDIUM,
        structured_data: Dict[str, Any] = None,
        record_metrics: bool = True
    ) -> QualityReport:
        """Validate content and automatically record metrics"""
        
        # Perform validation
        quality_report = await self.validate_content(
            content=content,
            section=section,
            context_chunks=context_chunks,
            complexity_level=complexity_level,
            structured_data=structured_data
        )
        
        # Record metrics to monitoring system
        if record_metrics:
            self.record_quality_metrics(quality_report, quality_report.processing_time_ms)
        
        return quality_report
    
    def create_quality_dashboard_data(self, hours: int = 24) -> Dict[str, Any]:
        """Create comprehensive quality dashboard data"""
        
        dashboard_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "time_range_hours": hours,
            "overview": {},
            "section_breakdown": {},
            "quality_distribution": {},
            "improvement_opportunities": {},
            "compliance_status": {}
        }
        
        try:
            # Overall quality trends
            overall_trends = self.get_quality_trends(hours=hours)
            dashboard_data["overview"] = overall_trends.get("quality_summary", {})
            dashboard_data["compliance_status"] = overall_trends.get("compliance_analysis", {})
            
            # Section-specific breakdown
            for section in ReportSection:
                section_trends = self.get_quality_trends(section=section, hours=hours)
                if "error" not in section_trends:
                    dashboard_data["section_breakdown"][section.value] = {
                        "average_score": section_trends["quality_summary"]["current_average"],
                        "evaluations": section_trends["total_evaluations"],
                        "trend": section_trends["quality_summary"]["trend_direction"],
                        "issues": section_trends["issue_analysis"]
                    }
            
            # Quality score distribution
            try:
                from app.utils.rag_monitoring import metrics_collector, ComponentType, MetricType
                
                recent_scores = []
                for metric in metrics_collector.metrics_history:
                    if (metric.component == ComponentType.QUALITY_CONTROLLER and 
                        metric.metric_type == MetricType.QUALITY_SCORE):
                        recent_scores.append(metric.value)
                
                if recent_scores:
                    dashboard_data["quality_distribution"] = {
                        "excellent": len([s for s in recent_scores if s >= 0.9]),
                        "good": len([s for s in recent_scores if 0.8 <= s < 0.9]),
                        "fair": len([s for s in recent_scores if 0.6 <= s < 0.8]),
                        "poor": len([s for s in recent_scores if s < 0.6]),
                        "total": len(recent_scores)
                    }
                
            except ImportError:
                pass
            
            # Improvement opportunities
            dashboard_data["improvement_opportunities"] = {
                "high_potential_sections": [],
                "common_issues": [],
                "recommendations": []
            }
            
            # Add recommendations based on trends
            if overall_trends.get("quality_summary", {}).get("trend_direction") == "declining":
                dashboard_data["improvement_opportunities"]["recommendations"].append(
                    "Quality trend is declining - consider reviewing validation rules and improvement strategies"
                )
            
            if overall_trends.get("issue_analysis", {}).get("critical_issues", 0) > 0:
                dashboard_data["improvement_opportunities"]["recommendations"].append(
                    "Critical issues detected - prioritize addressing high-severity quality problems"
                )
            
            compliance_rate = overall_trends.get("compliance_analysis", {}).get("compliance_rate", 0)
            if compliance_rate < 0.8:
                dashboard_data["improvement_opportunities"]["recommendations"].append(
                    f"Compliance rate is {compliance_rate:.1%} - review compliance rules and training"
                )
                
        except Exception as e:
            self.logger.error(f"Error creating quality dashboard data: {e}")
            dashboard_data["error"] = str(e)
        
        return dashboard_data
    
    def _create_improvement_prompt(
        self, 
        content: str, 
        issues: List[QualityIssue], 
        section: ReportSection
    ) -> str:
        """Creëer prompt voor content verbetering"""
        
        issues_text = "\n".join([
            f"- {issue.description}: {issue.suggestion}" 
            for issue in issues[:5]  # Top 5 issues
        ])
        
        return f"""
Je bent een senior arbeidsdeskundige die teksten verbetert.
Verbeter deze {section.value} sectie door de volgende kwaliteitsproblemen op te lossen:

HUIDIGE TEKST:
{content}

GEÏDENTIFICEERDE PROBLEMEN:
{issues_text}

VERBETERINGSINSTRUCTIES:
1. Behoud de kernboodschap en feitelijke inhoud
2. Verbeter de professionele toon en structuur  
3. Los de specifieke problemen op
4. Gebruik correcte arbeidsdeskundige terminologie
5. Zorg voor objectieve en feitelijke formulering

Schrijf de verbeterde versie:
"""