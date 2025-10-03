"""
Smart Document Classifier voor Arbeidsdeskundige AI
Intelligente classificatie van documenten voor arbeidsdeskundig onderzoek
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import json
import re
from datetime import datetime
from enum import Enum

from app.utils.llm_provider import GenerativeModel


class DocumentType(Enum):
    """Nederlandse arbeidsdeskundige document types"""
    MEDICAL_REPORT = "medical_report"
    INSURANCE_DOCUMENT = "insurance_document"
    EMPLOYMENT_RECORD = "employment_record"
    ASSESSMENT_REPORT = "assessment_report"
    PERSONAL_STATEMENT = "personal_statement"
    EDUCATIONAL_RECORD = "educational_record"
    LEGAL_DOCUMENT = "legal_document"
    CORRESPONDENCE = "correspondence"
    UNKNOWN = "unknown"


class ProcessingStrategy(Enum):
    """Document processing strategies"""
    DIRECT_LLM = "direct"
    HYBRID = "hybrid" 
    FULL_RAG = "full_rag"


class SmartDocumentClassifier:
    """Enhanced document classifier with AI-driven type detection"""
    
    def __init__(self):
        self.model = GenerativeModel("claude-3-5-sonnet-20241022")
        self.logger = logging.getLogger(__name__)
        
        # Nederlandse arbeidsdeskundige document types met keywords
        self.document_patterns = {
            DocumentType.MEDICAL_REPORT: {
                "keywords": [
                    "medisch rapport", "specialist", "arts", "diagnose", "anamnese",
                    "lichamelijk onderzoek", "bevindingen", "behandeling", "medicatie",
                    "therapie", "prognose", "herstel", "revalidatie", "specialist",
                    "ziekenhuis", "huisarts", "fysiotherapeut", "psycholoog"
                ],
                "patterns": [
                    r"medisch rapport",
                    r"diagnose[:\s]",
                    r"anamnese[:\s]",
                    r"lichamelijk onderzoek",
                    r"specialist.*rapport"
                ],
                "typical_sections": [
                    "diagnose", "anamnese", "onderzoek", "behandeling", "prognose"
                ]
            },
            DocumentType.INSURANCE_DOCUMENT: {
                "keywords": [
                    "UWV", "verzekeraar", "claim", "uitkering", "arbeidsongeschiktheid",
                    "WIA", "WAO", "WW", "verzekering", "schade", "premie",
                    "polis", "dekking", "eigen risico", "vergoeding"
                ],
                "patterns": [
                    r"UWV",
                    r"arbeidsongeschiktheid",
                    r"uitkering.*WIA|WIA.*uitkering",
                    r"verzekeraar",
                    r"claim.*nummer"
                ],
                "typical_sections": [
                    "claimgegevens", "uitkeringsbeschikking", "premie", "dekking"
                ]
            },
            DocumentType.EMPLOYMENT_RECORD: {
                "keywords": [
                    "arbeidscontract", "werkgever", "functieomschrijving", "salaris",
                    "arbeidsvoorwaarden", "CAO", "personeelsdossier", "baan",
                    "werknemer", "dienstverband", "proeftijd", "opzegging"
                ],
                "patterns": [
                    r"arbeidscontract",
                    r"functieomschrijving",
                    r"werkgever[:\s]",
                    r"dienstverband",
                    r"arbeidsvoorwaarden"
                ],
                "typical_sections": [
                    "functieomschrijving", "arbeidsvoorwaarden", "salaris", "secundaire voorwaarden"
                ]
            },
            DocumentType.ASSESSMENT_REPORT: {
                "keywords": [
                    "arbeidsdeskundig", "FML", "functioneel medisch onderzoek",
                    "belastbaarheid", "arbeidsbelasting", "re-integratie",
                    "werkhervatting", "beperkingen", "mogelijkheden",
                    "arbeidsdeskundige", "rapport", "conclusie"
                ],
                "patterns": [
                    r"arbeidsdeskundig.*rapport",
                    r"FML",
                    r"functioneel.*medisch",
                    r"belastbaarheid.*analyse",
                    r"re-integratie.*plan"
                ],
                "typical_sections": [
                    "belastbaarheid", "beperkingen", "mogelijkheden", "advies", "conclusie"
                ]
            },
            DocumentType.PERSONAL_STATEMENT: {
                "keywords": [
                    "eigen verhaal", "klacht", "ervaring", "persoonlijk",
                    "mijn situatie", "wat er gebeurd is", "problemen",
                    "gevolgen", "impact", "dagelijks leven"
                ],
                "patterns": [
                    r"eigen verhaal",
                    r"mijn.*ervaring",
                    r"wat.*gebeurd",
                    r"dagelijks.*leven",
                    r"persoonlijk.*verhaal"
                ],
                "typical_sections": [
                    "situatiebeschrijving", "klachten", "gevolgen", "dagelijks functioneren"
                ]
            },
            DocumentType.EDUCATIONAL_RECORD: {
                "keywords": [
                    "diploma", "certificaat", "opleiding", "cursus", "training",
                    "onderwijs", "school", "universiteit", "HBO", "MBO",
                    "getuigschrift", "studiebewijs", "kwalificatie"
                ],
                "patterns": [
                    r"diploma.*behaald",
                    r"certificaat.*uitgereikt",
                    r"opleiding.*gevolgd",
                    r"getuigschrift",
                    r"studiebewijs"
                ],
                "typical_sections": [
                    "opleidingsgegevens", "behaalde diploma's", "certificaten", "competenties"
                ]
            },
            DocumentType.LEGAL_DOCUMENT: {
                "keywords": [
                    "juridisch", "rechtbank", "advocaat", "procedure", "vonnis",
                    "uitspraak", "dagvaarding", "bezwaar", "beroep",
                    "wet", "artikel", "rechtszaak", "juridische stappen"
                ],
                "patterns": [
                    r"rechtbank.*uitspraak",
                    r"advocaat.*brief",
                    r"juridische.*procedure",
                    r"vonnis.*datum",
                    r"artikel.*wet"
                ],
                "typical_sections": [
                    "feiten", "overwegingen", "uitspraak", "rechtsgevolgen"
                ]
            },
            DocumentType.CORRESPONDENCE: {
                "keywords": [
                    "brief", "email", "correspondentie", "communicatie",
                    "antwoord", "reactie", "vraag", "informatie",
                    "mededeling", "kennisgeving"
                ],
                "patterns": [
                    r"geachte.*heer|mevrouw",
                    r"met vriendelijke groet",
                    r"in reactie op",
                    r"uw brief.*datum",
                    r"betreft[:\s]"
                ],
                "typical_sections": [
                    "onderwerp", "inhoud", "afsluiting", "bijlagen"
                ]
            }
        }
    
    async def classify_document(self, content: str, filename: str = "") -> Dict[str, Any]:
        """
        Classificeer document met AI-gedreven analyse
        
        Args:
            content: Document content
            filename: Original filename for context
            
        Returns:
            Dict met classification resultaten
        """
        try:
            # Stap 1: Regel-gebaseerde pre-classificatie
            rule_based_result = self._rule_based_classification(content, filename)
            
            # Stap 2: AI-versterkte classificatie
            ai_result = await self._ai_classification(content, rule_based_result)
            
            # Stap 3: Combineer resultaten
            final_result = self._combine_classifications(rule_based_result, ai_result, content)
            
            self.logger.info(f"Document classified as {final_result['type']} with confidence {final_result['confidence']}")
            return final_result
            
        except Exception as e:
            self.logger.error(f"Error classifying document: {e}")
            return self._default_classification()
    
    def _rule_based_classification(self, content: str, filename: str) -> Dict[str, Any]:
        """Regel-gebaseerde classificatie op basis van keywords en patterns"""
        
        content_lower = content.lower()
        filename_lower = filename.lower()
        
        scores = {}
        matches = {}
        
        for doc_type, patterns in self.document_patterns.items():
            score = 0
            type_matches = []
            
            # Keyword matching
            keyword_matches = 0
            for keyword in patterns["keywords"]:
                if keyword.lower() in content_lower:
                    keyword_matches += 1
                    type_matches.append(f"keyword: {keyword}")
            
            # Pattern matching  
            pattern_matches = 0
            for pattern in patterns["patterns"]:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    pattern_matches += 1
                    type_matches.append(f"pattern: {pattern}")
            
            # Filename hints
            filename_score = 0
            for keyword in patterns["keywords"][:5]:  # Top keywords only
                if keyword.lower() in filename_lower:
                    filename_score += 1
                    type_matches.append(f"filename: {keyword}")
            
            # Calculate weighted score
            score = (keyword_matches * 1.0) + (pattern_matches * 2.0) + (filename_score * 0.5)
            
            scores[doc_type] = score
            matches[doc_type] = type_matches
        
        # Find best match
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        
        # Calculate confidence (normalize by content length and number of patterns)
        content_length_factor = min(len(content) / 1000, 5.0)  # Cap influence
        confidence = min(best_score / (content_length_factor + 1), 1.0)
        
        return {
            "type": best_type.value,
            "confidence": confidence,
            "rule_based_score": best_score,
            "matches": matches[best_type],
            "all_scores": {t.value: s for t, s in scores.items()}
        }
    
    async def _ai_classification(self, content: str, rule_result: Dict[str, Any]) -> Dict[str, Any]:
        """AI-versterkte classificatie met LLM"""
        
        # Beperk content voor LLM (eerste 3000 karakters)
        content_preview = content[:3000]
        
        # Voeg regel-based context toe
        rule_type = rule_result.get("type", "unknown")
        rule_confidence = rule_result.get("confidence", 0.0)
        
        prompt = f"""
Je bent een expert in Nederlandse arbeidsdeskundige documenten. Analyseer dit document en classificeer het type.

Document preview:
{content_preview}

Regel-gebaseerde classificatie suggestie: {rule_type} (confidence: {rule_confidence:.2f})

Mogelijke document types:
- medical_report: Medische rapporten, specialistenverslagen, behandelplannen
- insurance_document: UWV documenten, verzekeringsstukken, uitkeringsbeschikkingen  
- employment_record: Arbeidscontracten, functieomschrijvingen, personeelsdossiers
- assessment_report: Arbeidsdeskundige rapporten, FML onderzoeken, belastbaarheidsanalyses
- personal_statement: Persoonlijke verhalen, eigen ervaringen, klachtenbeschrijvingen
- educational_record: Diploma's, certificaten, opleidingsgegevens
- legal_document: Juridische documenten, rechtbankuitspraken, advocatenbrieven
- correspondence: Brieven, emails, algemene correspondentie
- unknown: Kan niet geclassificeerd worden

Analyseer de inhoud, structuur, taalgebruik en context. Geef je antwoord in JSON formaat:

{{
    "type": "document_type",
    "confidence": 0.0-1.0,
    "reasoning": "Korte uitleg waarom dit type gekozen is",
    "key_indicators": ["lijst", "van", "belangrijke", "indicatoren"],
    "alternative_types": ["mogelijk", "alternatief"] 
}}

Zorg ervoor dat je antwoord geldig JSON is.
"""

        try:
            response = await self.model.generate_content_async(prompt)
            response_text = response.text if hasattr(response, 'text') else str(response)
            ai_result = self._parse_ai_response(response_text)
            
            self.logger.debug(f"AI classification result: {ai_result}")
            return ai_result
            
        except Exception as e:
            self.logger.error(f"AI classification failed: {e}")
            return {
                "type": rule_result.get("type", "unknown"),
                "confidence": 0.5,
                "reasoning": "AI classification failed, using rule-based result",
                "key_indicators": [],
                "alternative_types": []
            }
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response naar gestructureerd resultaat"""
        try:
            # Probeer JSON te extraheren uit de response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                # Valideer required fields
                if "type" in result and "confidence" in result:
                    # Zorg ervoor dat confidence een float is tussen 0 en 1
                    result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
                    return result
            
            # Fallback parsing
            self.logger.warning(f"Could not parse AI response as JSON: {response}")
            return self._extract_fallback_classification(response)
            
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Error parsing AI response: {e}")
            return self._extract_fallback_classification(response)
    
    def _extract_fallback_classification(self, response: str) -> Dict[str, Any]:
        """Fallback parsing als JSON parsing faalt"""
        
        # Zoek naar type mentions
        doc_types = [dt.value for dt in DocumentType]
        found_type = "unknown"
        
        for doc_type in doc_types:
            if doc_type in response.lower():
                found_type = doc_type
                break
        
        # Zoek naar confidence indicaties
        confidence = 0.5
        conf_patterns = [
            r"confidence[:\s]+([0-9]\.[0-9]+)",
            r"zekerheid[:\s]+([0-9]+)%",
            r"waarschijnlijk[:\s]+([0-9]+)%"
        ]
        
        for pattern in conf_patterns:
            match = re.search(pattern, response.lower())
            if match:
                try:
                    conf_val = float(match.group(1))
                    confidence = conf_val if conf_val <= 1.0 else conf_val / 100.0
                    break
                except ValueError:
                    continue
        
        return {
            "type": found_type,
            "confidence": confidence,
            "reasoning": "Fallback parsing gebruikt",
            "key_indicators": [],
            "alternative_types": []
        }
    
    def _combine_classifications(self, rule_result: Dict[str, Any], 
                                ai_result: Dict[str, Any], content: str) -> Dict[str, Any]:
        """Combineer regel-based en AI resultaten tot finale classificatie"""
        
        rule_type = rule_result.get("type", "unknown")
        rule_confidence = rule_result.get("confidence", 0.0)
        
        ai_type = ai_result.get("type", "unknown")
        ai_confidence = ai_result.get("confidence", 0.0)
        
        # Als beide methoden hetzelfde type voorstellen, verhoog confidence
        if rule_type == ai_type:
            final_type = rule_type
            # Gewogen gemiddelde met bonus voor consensus
            consensus_bonus = 0.2
            final_confidence = min(1.0, (rule_confidence + ai_confidence) / 2 + consensus_bonus)
        else:
            # Bij conflict, kies de methode met hoogste confidence
            if ai_confidence > rule_confidence:
                final_type = ai_type
                final_confidence = ai_confidence * 0.9  # Kleine penalty voor conflict
            else:
                final_type = rule_type  
                final_confidence = rule_confidence * 0.9
        
        # Extraheer metadata
        metadata = self._extract_metadata(content, final_type)
        
        return {
            "type": final_type,
            "confidence": final_confidence,
            "processing_strategy": self._determine_processing_strategy(final_type, len(content), final_confidence),
            "metadata": metadata,
            "classification_details": {
                "rule_based": rule_result,
                "ai_based": ai_result,
                "consensus": rule_type == ai_type
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _determine_processing_strategy(self, doc_type: str, content_length: int, confidence: float) -> str:
        """Bepaal optimale processing strategy op basis van document type en eigenschappen"""
        
        # Prioriteitsdocumenten krijgen altijd enhanced processing
        priority_types = [
            DocumentType.MEDICAL_REPORT.value,
            DocumentType.ASSESSMENT_REPORT.value,
            DocumentType.LEGAL_DOCUMENT.value
        ]
        
        if doc_type in priority_types and confidence > 0.7:
            return ProcessingStrategy.FULL_RAG.value
        
        # Legal documents hebben altijd zorgvuldige processing nodig
        if doc_type == DocumentType.LEGAL_DOCUMENT.value:
            return ProcessingStrategy.HYBRID.value if content_length < 30000 else ProcessingStrategy.FULL_RAG.value
        
        # Persoonlijke verhalen kunnen vaak direct verwerkt worden
        if doc_type == DocumentType.PERSONAL_STATEMENT.value and content_length < 40000:
            return ProcessingStrategy.DIRECT_LLM.value
        
        # Correspondentie is meestal simpel
        if doc_type == DocumentType.CORRESPONDENCE.value and content_length < 20000:
            return ProcessingStrategy.DIRECT_LLM.value
        
        # Fallback naar size-based strategy
        if content_length < 20000:
            return ProcessingStrategy.DIRECT_LLM.value
        elif content_length < 60000:
            return ProcessingStrategy.HYBRID.value
        else:
            return ProcessingStrategy.FULL_RAG.value
    
    def _extract_metadata(self, content: str, doc_type: str) -> Dict[str, Any]:
        """Extraheer document-specifieke metadata"""
        
        metadata = {
            "content_length": len(content),
            "language": "nl",
            "domain": "arbeidsdeskundig",
            "extraction_date": datetime.utcnow().isoformat()
        }
        
        # Type-specifieke metadata extractie
        if doc_type == DocumentType.MEDICAL_REPORT.value:
            metadata.update(self._extract_medical_metadata(content))
        elif doc_type == DocumentType.ASSESSMENT_REPORT.value:
            metadata.update(self._extract_assessment_metadata(content))
        elif doc_type == DocumentType.LEGAL_DOCUMENT.value:
            metadata.update(self._extract_legal_metadata(content))
        
        return metadata
    
    def _extract_medical_metadata(self, content: str) -> Dict[str, Any]:
        """Extraheer medische metadata"""
        metadata = {}
        
        # Zoek naar specialisme
        specialisms = ["cardioloog", "neuroloog", "orthopeed", "psychiater", "huisarts", "fysiotherapeut"]
        found_specialisms = [s for s in specialisms if s in content.lower()]
        if found_specialisms:
            metadata["specialisme"] = found_specialisms
        
        # Zoek naar datum patronen
        date_patterns = [
            r"(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
            r"(\d{1,2}\s+\w+\s+\d{4})"
        ]
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, content))
        if dates:
            metadata["gevonden_datums"] = dates[:5]  # Limiteer tot 5
        
        # Zoek naar diagnose keywords
        diagnosis_keywords = ["diagnose", "bevinding", "conclusie", "aandoening"]
        found_diagnoses = [kw for kw in diagnosis_keywords if kw in content.lower()]
        if found_diagnoses:
            metadata["diagnose_secties"] = found_diagnoses
        
        return metadata
    
    def _extract_assessment_metadata(self, content: str) -> Dict[str, Any]:
        """Extraheer arbeidsdeskundige metadata"""
        metadata = {}
        
        # Zoek naar belastbaarheid termen
        belastbaarheid_terms = ["belastbaarheid", "beperking", "mogelijkheid", "functie-eisen"]
        found_terms = [term for term in belastbaarheid_terms if term in content.lower()]
        if found_terms:
            metadata["belastbaarheid_aspecten"] = found_terms
        
        # Zoek naar re-integratie termen
        reintegration_terms = ["re-integratie", "werkhervatting", "aangepast werk", "arbeidstherapie"]
        found_reintegration = [term for term in reintegration_terms if term in content.lower()]
        if found_reintegration:
            metadata["reintegratie_aspecten"] = found_reintegration
        
        return metadata
    
    def _extract_legal_metadata(self, content: str) -> Dict[str, Any]:
        """Extraheer juridische metadata"""
        metadata = {}
        
        # Zoek naar rechtbank informatie
        rechtbank_pattern = r"rechtbank\s+(\w+)"
        rechtbank_matches = re.findall(rechtbank_pattern, content.lower())
        if rechtbank_matches:
            metadata["rechtbank"] = rechtbank_matches[0]
        
        # Zoek naar zaaknummers
        zaaknummer_pattern = r"zaaknummer[:\s]+([A-Z0-9\-/]+)"
        zaaknummer_matches = re.findall(zaaknummer_pattern, content, re.IGNORECASE)
        if zaaknummer_matches:
            metadata["zaaknummer"] = zaaknummer_matches[0]
        
        return metadata
    
    def _default_classification(self) -> Dict[str, Any]:
        """Default classificatie bij falen van andere methoden"""
        return {
            "type": DocumentType.UNKNOWN.value,
            "confidence": 0.1,
            "processing_strategy": ProcessingStrategy.HYBRID.value,
            "metadata": {
                "content_length": 0,
                "language": "nl",
                "domain": "arbeidsdeskundig",
                "extraction_date": datetime.utcnow().isoformat(),
                "classification_failed": True
            },
            "classification_details": {
                "error": "Classification failed"
            },
            "timestamp": datetime.utcnow().isoformat()
        }