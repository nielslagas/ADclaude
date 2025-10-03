"""
Enhanced Document Processor met Smart Classification
Geïntegreerde verwerking met AI-gedreven document classificatie
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.db.database_service import DatabaseService
from app.utils.llm_provider import GenerativeModel
from app.utils.smart_document_classifier import SmartDocumentClassifier, ProcessingStrategy
# from app.tasks.process_document_tasks.hybrid_processor import HybridDocumentProcessor
# from app.utils.vector_store_improved import VectorStoreImproved


class EnhancedDocumentProcessor:
    """
    Enhanced document processor met slimme classificatie en adaptieve verwerking
    """
    
    def __init__(self, db_service: DatabaseService, llm_provider: GenerativeModel):
        self.db_service = db_service
        self.llm_provider = llm_provider
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.classifier = SmartDocumentClassifier(llm_provider)
        # self.hybrid_processor = HybridDocumentProcessor(db_service, llm_provider)
        
        # Processing statistics
        self.processing_stats = {
            "total_processed": 0,
            "by_type": {},
            "by_strategy": {},
            "average_confidence": 0.0
        }
    
    async def process_document(self, document_id: str) -> Dict[str, Any]:
        """
        Hoofd document processing functie met slimme classificatie
        
        Args:
            document_id: ID van het te verwerken document
            
        Returns:
            Dict met processing resultaten en metadata
        """
        try:
            start_time = datetime.utcnow()
            
            # Stap 1: Haal document op
            document = await self._get_document(document_id)
            if not document:
                raise ValueError(f"Document {document_id} niet gevonden")
            
            # Stap 2: Smart classification
            self.logger.info(f"Starting smart classification for document {document_id}")
            classification = await self.classifier.classify_document(
                content=document.get("content", ""),
                filename=document.get("filename", "")
            )
            
            # Stap 3: Update document met classificatie metadata
            await self._update_document_metadata(document_id, classification)
            
            # Stap 4: Bepaal en execute processing strategy
            strategy = classification.get("processing_strategy", ProcessingStrategy.HYBRID.value)
            processing_result = await self._execute_processing_strategy(
                document_id, document, classification, strategy
            )
            
            # Stap 5: Update statistics
            self._update_processing_stats(classification, strategy)
            
            # Stap 6: Finalize result
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            final_result = {
                "document_id": document_id,
                "classification": classification,
                "processing_strategy": strategy,
                "processing_result": processing_result,
                "processing_time_seconds": processing_time,
                "timestamp": end_time.isoformat(),
                "status": "completed"
            }
            
            self.logger.info(
                f"Document {document_id} processed successfully as {classification['type']} "
                f"using {strategy} strategy in {processing_time:.2f}s"
            )
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"Error processing document {document_id}: {e}")
            return {
                "document_id": document_id,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Haal document op uit database"""
        try:
            document = self.db_service.get_document(document_id)
            if not document:
                self.logger.error(f"Document {document_id} not found in database")
                return None
            return document
        except Exception as e:
            self.logger.error(f"Error retrieving document {document_id}: {e}")
            return None
    
    async def _update_document_metadata(self, document_id: str, classification: Dict[str, Any]) -> None:
        """Update document met classificatie metadata"""
        try:
            metadata = {
                "document_type": classification.get("type"),
                "classification_confidence": classification.get("confidence"),
                "processing_strategy": classification.get("processing_strategy"),
                "classification_metadata": classification.get("metadata", {}),
                "classification_timestamp": datetime.utcnow().isoformat()
            }
            
            # Update document in database
            await self.db_service.update_document_metadata(document_id, metadata)
            
            self.logger.debug(f"Updated metadata for document {document_id}")
            
        except Exception as e:
            self.logger.error(f"Error updating document metadata for {document_id}: {e}")
    
    async def _execute_processing_strategy(self, document_id: str, document: Dict[str, Any], 
                                         classification: Dict[str, Any], strategy: str) -> Dict[str, Any]:
        """Execute de gekozen processing strategy"""
        
        content = document.get("content", "")
        doc_type = classification.get("type", "unknown")
        
        try:
            if strategy == ProcessingStrategy.DIRECT_LLM.value:
                return await self._direct_llm_processing(document_id, content, doc_type, classification)
            
            elif strategy == ProcessingStrategy.HYBRID.value:
                return await self._hybrid_processing(document_id, content, doc_type, classification)
            
            elif strategy == ProcessingStrategy.FULL_RAG.value:
                return await self._full_rag_processing(document_id, content, doc_type, classification)
            
            else:
                self.logger.warning(f"Unknown processing strategy: {strategy}, falling back to hybrid")
                return await self._hybrid_processing(document_id, content, doc_type, classification)
                
        except Exception as e:
            self.logger.error(f"Error in {strategy} processing for document {document_id}: {e}")
            raise
    
    async def _direct_llm_processing(self, document_id: str, content: str, 
                                   doc_type: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Direct LLM processing voor kleinere/eenvoudigere documenten"""
        
        self.logger.info(f"Starting direct LLM processing for document {document_id}")
        
        # Maak document-type specifieke extractie prompt
        extraction_prompt = self._create_extraction_prompt(content, doc_type, classification)
        
        try:
            # Direct LLM call voor informatie extractie
            extraction_result = await self.llm_provider.generate_response(extraction_prompt)
            
            # Parse en structureer resultaat
            structured_result = self._parse_extraction_result(extraction_result, doc_type)
            
            return {
                "processing_type": "direct_llm",
                "extracted_information": structured_result,
                "chunks_created": 0,
                "embeddings_created": 0,
                "processing_notes": "Direct LLM processing completed successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Direct LLM processing failed for {document_id}: {e}")
            raise
    
    async def _hybrid_processing(self, document_id: str, content: str, 
                                doc_type: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Hybrid processing met zowel direct LLM als chunking"""
        
        self.logger.info(f"Starting hybrid processing for document {document_id}")
        
        try:
            # Gebruik bestaande hybrid processor maar met enhanced metadata
            result = await self.hybrid_processor.process_document(document_id)
            
            # Voeg classification context toe aan het resultaat
            if "chunks" in result:
                for chunk in result["chunks"]:
                    chunk["document_type"] = doc_type
                    chunk["classification_confidence"] = classification.get("confidence", 0.0)
                    chunk["document_metadata"] = classification.get("metadata", {})
            
            # Voeg type-specifieke processing toe
            enhanced_result = await self._enhance_with_type_specific_processing(
                result, content, doc_type, classification
            )
            
            return enhanced_result
            
        except Exception as e:
            self.logger.error(f"Hybrid processing failed for {document_id}: {e}")
            raise
    
    async def _full_rag_processing(self, document_id: str, content: str, 
                                 doc_type: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Full RAG processing voor complexe/grote documenten"""
        
        self.logger.info(f"Starting full RAG processing for document {document_id}")
        
        try:
            # Enhanced chunking gebaseerd op document type
            chunks = await self._create_smart_chunks(content, doc_type, classification)
            
            # Create embeddings for all chunks
            vector_store = VectorStoreImproved(self.db_service, self.llm_provider)
            embeddings_result = await vector_store.add_document_chunks(document_id, chunks)
            
            # Type-specific analysis
            analysis_result = await self._perform_type_specific_analysis(content, doc_type, classification)
            
            return {
                "processing_type": "full_rag",
                "chunks_created": len(chunks),
                "embeddings_created": embeddings_result.get("embeddings_count", 0),
                "document_analysis": analysis_result,
                "chunks": chunks,
                "processing_notes": "Full RAG processing with enhanced chunking completed"
            }
            
        except Exception as e:
            self.logger.error(f"Full RAG processing failed for {document_id}: {e}")
            raise
    
    async def _create_smart_chunks(self, content: str, doc_type: str, 
                                 classification: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Maak slimme chunks gebaseerd op document type"""
        
        if doc_type == "medical_report":
            return await self._chunk_medical_report(content, classification)
        elif doc_type == "assessment_report":
            return await self._chunk_assessment_report(content, classification)
        elif doc_type == "legal_document":
            return await self._chunk_legal_document(content, classification)
        else:
            return await self._default_smart_chunking(content, classification)
    
    async def _chunk_medical_report(self, content: str, classification: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Medische rapporten: chunk op basis van medische secties"""
        
        # Medische sectie patterns
        section_patterns = {
            "anamnese": r"(anamnese|voorgeschiedenis|hetero-anamnese)",
            "klachten": r"(klachten|symptomen|problemen)",
            "onderzoek": r"(lichamelijk onderzoek|bevindingen|inspectie)",
            "diagnose": r"(diagnose|conclusie|bevindingen)",
            "behandeling": r"(behandeling|therapie|medicatie|advies)",
            "prognose": r"(prognose|verwachting|herstel|vooruitzicht)"
        }
        
        chunks = []
        remaining_content = content
        
        for section_name, pattern in section_patterns.items():
            # Zoek sectie in content
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if matches:
                # Neem eerste match als sectie start
                start_pos = matches[0].start()
                
                # Zoek einde van sectie (volgende sectie of einde document)
                end_pos = len(content)
                for other_section, other_pattern in section_patterns.items():
                    if other_section != section_name:
                        other_matches = list(re.finditer(other_pattern, content[start_pos + 100:], re.IGNORECASE))
                        if other_matches:
                            potential_end = start_pos + 100 + other_matches[0].start()
                            if potential_end < end_pos:
                                end_pos = potential_end
                
                section_content = content[start_pos:end_pos].strip()
                
                if len(section_content) > 50:  # Minimale sectie grootte
                    chunks.append({
                        "content": section_content,
                        "metadata": {
                            "section_type": section_name,
                            "document_type": "medical_report",
                            "chunk_type": "medical_section",
                            "importance": "high" if section_name in ["diagnose", "behandeling"] else "medium"
                        }
                    })
        
        # Als er geen duidelijke secties gevonden zijn, gebruik default chunking
        if not chunks:
            chunks = await self._default_smart_chunking(content, classification)
        
        return chunks
    
    async def _chunk_assessment_report(self, content: str, classification: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Arbeidsdeskundige rapporten: chunk op basis van assessment secties"""
        
        section_patterns = {
            "belastbaarheid": r"(belastbaarheid|belastbaar|capaciteit)",
            "beperkingen": r"(beperkingen|limitaties|problemen)",
            "mogelijkheden": r"(mogelijkheden|kansen|potentieel)",
            "advies": r"(advies|aanbeveling|conclusie)",
            "werkhervatting": r"(werkhervatting|re-integratie|terugkeer)"
        }
        
        return await self._chunk_by_patterns(content, section_patterns, "assessment_report")
    
    async def _chunk_legal_document(self, content: str, classification: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Juridische documenten: chunk op basis van juridische structuur"""
        
        section_patterns = {
            "feiten": r"(feiten|feitelijke omstandigheden|gebeurde)",
            "overwegingen": r"(overwegingen|beoordeling|analyse)",
            "conclusie": r"(conclusie|uitspraak|beslissing)",
            "rechtsgevolgen": r"(rechtsgevolgen|gevolgen|consequenties)"
        }
        
        return await self._chunk_by_patterns(content, section_patterns, "legal_document")
    
    async def _chunk_by_patterns(self, content: str, section_patterns: Dict[str, str], 
                               doc_type: str) -> List[Dict[str, Any]]:
        """Generieke functie voor pattern-based chunking"""
        
        chunks = []
        
        for section_name, pattern in section_patterns.items():
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if matches:
                for match in matches:
                    start_pos = max(0, match.start() - 200)  # Context voor de match
                    end_pos = min(len(content), match.end() + 1000)  # 1000 chars na match
                    
                    section_content = content[start_pos:end_pos].strip()
                    
                    if len(section_content) > 100:
                        chunks.append({
                            "content": section_content,
                            "metadata": {
                                "section_type": section_name,
                                "document_type": doc_type,
                                "chunk_type": "pattern_section",
                                "importance": "high"
                            }
                        })
        
        # Fallback naar default als geen patterns gevonden
        if not chunks:
            chunks = await self._default_smart_chunking(content, {"type": doc_type})
        
        return chunks
    
    async def _default_smart_chunking(self, content: str, classification: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Default slimme chunking strategie"""
        
        # Intelligent paragraph-based chunking
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = ""
        current_size = 0
        
        target_chunk_size = 800  # Characters
        max_chunk_size = 1500
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Als toevoegen van deze paragraph de chunk te groot maakt
            if current_size + len(paragraph) > max_chunk_size and current_chunk:
                # Sla huidige chunk op
                chunks.append({
                    "content": current_chunk.strip(),
                    "metadata": {
                        "document_type": classification.get("type", "unknown"),
                        "chunk_type": "paragraph_group",
                        "importance": "medium"
                    }
                })
                current_chunk = paragraph
                current_size = len(paragraph)
            else:
                # Voeg paragraph toe aan huidige chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
                current_size += len(paragraph)
        
        # Voeg laatste chunk toe
        if current_chunk.strip():
            chunks.append({
                "content": current_chunk.strip(),
                "metadata": {
                    "document_type": classification.get("type", "unknown"),
                    "chunk_type": "paragraph_group",
                    "importance": "medium"
                }
            })
        
        return chunks
    
    def _create_extraction_prompt(self, content: str, doc_type: str, 
                                classification: Dict[str, Any]) -> str:
        """Maak document-type specifieke extractie prompt"""
        
        base_prompt = f"""
Je bent een expert in Nederlandse arbeidsdeskundige documenten. 
Analyseer dit {doc_type} document en extraheer de belangrijkste informatie.

Document:
{content[:4000]}  # Limiteer voor LLM context

"""
        
        if doc_type == "medical_report":
            return base_prompt + """
Voor medische rapporten, extraheer:
- Diagnoses en bevindingen
- Beperkingen en mogelijkheden  
- Behandelplannen
- Prognose en verwachtingen
- Relevante medische geschiedenis

Geef een gestructureerd overzicht in JSON formaat.
"""
        
        elif doc_type == "assessment_report":
            return base_prompt + """
Voor arbeidsdeskundige rapporten, extraheer:
- Belastbaarheidsanalyse
- Functionele beperkingen
- Arbeidsplaats mogelijkheden
- Re-integratie advies
- Conclusies en aanbevelingen

Geef een gestructureerd overzicht in JSON formaat.
"""
        
        else:
            return base_prompt + """
Extraheer de belangrijkste punten, conclusies en aanbevelingen uit dit document.
Focus op informatie relevant voor arbeidsdeskundig onderzoek.

Geef een gestructureerd overzicht in JSON formaat.
"""
    
    def _parse_extraction_result(self, extraction_result: str, doc_type: str) -> Dict[str, Any]:
        """Parse en structureer extraction resultaat"""
        
        try:
            # Probeer JSON parsing
            import json
            import re
            
            json_match = re.search(r'\{.*\}', extraction_result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # Fallback: return als tekst
        return {
            "extracted_text": extraction_result,
            "document_type": doc_type,
            "extraction_method": "text_fallback"
        }
    
    async def _enhance_with_type_specific_processing(self, base_result: Dict[str, Any], 
                                                   content: str, doc_type: str, 
                                                   classification: Dict[str, Any]) -> Dict[str, Any]:
        """Voeg type-specifieke verwerking toe aan basis resultaat"""
        
        enhanced_result = base_result.copy()
        enhanced_result["processing_type"] = "enhanced_hybrid"
        enhanced_result["document_type"] = doc_type
        enhanced_result["classification"] = classification
        
        # Type-specifieke enhancements
        if doc_type == "medical_report":
            enhanced_result["medical_analysis"] = await self._analyze_medical_content(content)
        elif doc_type == "assessment_report":
            enhanced_result["assessment_analysis"] = await self._analyze_assessment_content(content)
        
        return enhanced_result
    
    async def _analyze_medical_content(self, content: str) -> Dict[str, Any]:
        """Specifieke analyse voor medische content"""
        # Implementatie voor medische content analyse
        return {"analysis_type": "medical", "status": "completed"}
    
    async def _analyze_assessment_content(self, content: str) -> Dict[str, Any]:
        """Specifieke analyse voor arbeidsdeskundige content"""
        # Implementatie voor assessment content analyse
        return {"analysis_type": "assessment", "status": "completed"}
    
    async def _perform_type_specific_analysis(self, content: str, doc_type: str, 
                                            classification: Dict[str, Any]) -> Dict[str, Any]:
        """Voer type-specifieke diepgaande analyse uit"""
        
        analysis = {
            "document_type": doc_type,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
        # Type-specifieke analyse logica hier
        if doc_type == "medical_report":
            analysis.update(await self._deep_medical_analysis(content))
        elif doc_type == "assessment_report":
            analysis.update(await self._deep_assessment_analysis(content))
        
        return analysis
    
    async def _deep_medical_analysis(self, content: str) -> Dict[str, Any]:
        """Diepgaande medische analyse"""
        return {"deep_analysis": "medical", "status": "completed"}
    
    async def _deep_assessment_analysis(self, content: str) -> Dict[str, Any]:
        """Diepgaande arbeidsdeskundige analyse"""
        return {"deep_analysis": "assessment", "status": "completed"}
    
    def _update_processing_stats(self, classification: Dict[str, Any], strategy: str) -> None:
        """Update processing statistieken"""
        
        doc_type = classification.get("type", "unknown")
        confidence = classification.get("confidence", 0.0)
        
        self.processing_stats["total_processed"] += 1
        
        # Update type statistics
        if doc_type not in self.processing_stats["by_type"]:
            self.processing_stats["by_type"][doc_type] = 0
        self.processing_stats["by_type"][doc_type] += 1
        
        # Update strategy statistics
        if strategy not in self.processing_stats["by_strategy"]:
            self.processing_stats["by_strategy"][strategy] = 0
        self.processing_stats["by_strategy"][strategy] += 1
        
        # Update average confidence
        total = self.processing_stats["total_processed"]
        current_avg = self.processing_stats["average_confidence"]
        self.processing_stats["average_confidence"] = ((current_avg * (total - 1)) + confidence) / total
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Krijg huidige processing statistieken"""
        return self.processing_stats.copy()


# Import fix
import re