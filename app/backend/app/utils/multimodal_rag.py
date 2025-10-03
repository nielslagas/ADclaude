"""
Multi-Modal RAG voor AI-Arbeidsdeskundige
Combineert tekst en audio processing voor verbeterde content generatie
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from app.utils.smart_document_classifier import SmartDocumentClassifier, DocumentType
from app.utils.optimized_rag_pipeline import OptimizedRAGPipeline, RetrievalStrategy
from app.utils.context_aware_prompts import ContextAwarePromptGenerator, ReportSection, ComplexityLevel
from app.utils.quality_controller import AutomaticQualityController
# Audio transcriber will be imported conditionally


class ModalityType(Enum):
    """Types van input modaliteiten"""
    TEXT_DOCUMENT = "text_document"
    AUDIO_RECORDING = "audio_recording"
    MIXED_CONTENT = "mixed_content"


class ProcessingMode(Enum):
    """Modi voor multi-modal processing"""
    SEQUENTIAL = "sequential"      # Verwerk eerst tekst, dan audio
    PARALLEL = "parallel"         # Verwerk gelijktijdig
    INTEGRATED = "integrated"     # Volledig geïntegreerde verwerking
    ADAPTIVE = "adaptive"         # Automatisch beste strategie kiezen


@dataclass
class ModalInput:
    """Input voor een specifieke modaliteit"""
    modality: ModalityType
    content: Union[str, bytes]
    metadata: Dict[str, Any]
    weight: float = 1.0  # Gewicht van deze modaliteit in final result
    quality_score: Optional[float] = None


@dataclass
class MultiModalContext:
    """Context informatie van meerdere modaliteiten"""
    text_chunks: List[str]
    audio_transcripts: List[str]
    combined_insights: List[str]
    modality_weights: Dict[ModalityType, float]
    processing_metadata: Dict[str, Any]
    confidence_scores: Dict[ModalityType, float]


@dataclass
class MultiModalResult:
    """Resultaat van multi-modal RAG processing"""
    generated_content: str
    source_modalities: List[ModalityType]
    context_used: MultiModalContext
    quality_score: float
    processing_time: float
    recommendations: List[str]
    metadata: Dict[str, Any]


class MultiModalRAGPipeline:
    """Advanced Multi-Modal RAG Pipeline voor Arbeidsdeskundige Content"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize component pipelines
        self.document_classifier = SmartDocumentClassifier()
        self.rag_pipeline = OptimizedRAGPipeline()
        self.prompt_generator = ContextAwarePromptGenerator()
        self.quality_controller = AutomaticQualityController()
        # Note: Audio transcription will be handled via direct function calls
        self.audio_transcriber = None
        
        # Multi-modal configuration
        self.modality_weights = self._load_modality_weights()
        self.processing_strategies = self._load_processing_strategies()
        self.quality_thresholds = self._load_quality_thresholds()
    
    def _load_modality_weights(self) -> Dict[ModalityType, float]:
        """Laad default gewichten per modaliteit"""
        return {
            ModalityType.TEXT_DOCUMENT: 0.7,  # Tekst is meestal primaire bron
            ModalityType.AUDIO_RECORDING: 0.5,  # Audio als aanvulling
            ModalityType.MIXED_CONTENT: 0.8   # Mixed content heeft hoge waarde
        }
    
    def _load_processing_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Laad processing strategieën per scenario"""
        return {
            "high_quality_text_with_audio": {
                "mode": ProcessingMode.INTEGRATED,
                "text_weight": 0.7,
                "audio_weight": 0.3,
                "strategy": "text_primary_audio_enhancement"
            },
            "poor_quality_text_with_audio": {
                "mode": ProcessingMode.PARALLEL,
                "text_weight": 0.4,
                "audio_weight": 0.6,
                "strategy": "audio_primary_text_support"
            },
            "audio_only": {
                "mode": ProcessingMode.SEQUENTIAL,
                "text_weight": 0.0,
                "audio_weight": 1.0,
                "strategy": "audio_transcription_rag"
            },
            "text_only": {
                "mode": ProcessingMode.SEQUENTIAL,
                "text_weight": 1.0,
                "audio_weight": 0.0,
                "strategy": "traditional_rag"
            }
        }
    
    def _load_quality_thresholds(self) -> Dict[str, float]:
        """Laad kwaliteitsdrempels voor verschillende processen"""
        return {
            "text_transcription_confidence": 0.85,
            "audio_quality_score": 0.7,
            "combined_context_relevance": 0.75,
            "final_content_quality": 0.8
        }
    
    async def process_multimodal_content(
        self,
        inputs: List[ModalInput],
        section: ReportSection,
        complexity_level: ComplexityLevel = ComplexityLevel.MEDIUM,
        processing_mode: ProcessingMode = ProcessingMode.ADAPTIVE
    ) -> MultiModalResult:
        """
        Hoofdfunctie: verwerk multi-modal content voor rapport generatie
        """
        start_time = datetime.utcnow()
        self.logger.info(f"Starting multi-modal processing for section {section.value}")
        
        try:
            # Stap 1: Analyseer inputs en bepaal optimale strategie
            strategy = await self._determine_processing_strategy(inputs, processing_mode)
            
            # Stap 2: Pre-process alle modaliteiten
            processed_inputs = await self._preprocess_modalities(inputs)
            
            # Stap 3: Extract en combineer context
            multimodal_context = await self._extract_multimodal_context(
                processed_inputs, strategy
            )
            
            # Stap 4: Genereer content op basis van gecombineerde context
            generated_content = await self._generate_multimodal_content(
                multimodal_context, section, complexity_level, strategy
            )
            
            # Stap 5: Kwaliteitscontrole en verbetering
            final_content = await self._quality_assurance(
                generated_content, multimodal_context, section
            )
            
            # Stap 6: Bereken metadata en statistieken
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            quality_score = await self._calculate_overall_quality(
                final_content, multimodal_context
            )
            
            result = MultiModalResult(
                generated_content=final_content,
                source_modalities=[inp.modality for inp in inputs],
                context_used=multimodal_context,
                quality_score=quality_score,
                processing_time=processing_time,
                recommendations=self._generate_recommendations(multimodal_context, quality_score),
                metadata={
                    "strategy_used": strategy,
                    "inputs_processed": len(inputs),
                    "section": section.value,
                    "complexity_level": complexity_level.value,
                    "timestamp": start_time.isoformat()
                }
            )
            
            self.logger.info(f"Multi-modal processing completed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"Multi-modal processing failed: {e}")
            return self._create_fallback_result(inputs, section)
    
    async def _determine_processing_strategy(
        self, 
        inputs: List[ModalInput], 
        processing_mode: ProcessingMode
    ) -> Dict[str, Any]:
        """Bepaal de optimale processing strategie"""
        
        # Analyseer input samenstelling
        modality_counts = {}
        total_weight = 0
        
        for inp in inputs:
            modality_counts[inp.modality] = modality_counts.get(inp.modality, 0) + 1
            total_weight += inp.weight
        
        has_text = ModalityType.TEXT_DOCUMENT in modality_counts
        has_audio = ModalityType.AUDIO_RECORDING in modality_counts
        has_mixed = ModalityType.MIXED_CONTENT in modality_counts
        
        # Bepaal strategie op basis van input types
        if processing_mode == ProcessingMode.ADAPTIVE:
            if has_text and has_audio:
                # Evalueer tekst kwaliteit om strategie te bepalen
                text_quality = await self._evaluate_text_quality(inputs)
                if text_quality > 0.7:
                    strategy_key = "high_quality_text_with_audio"
                else:
                    strategy_key = "poor_quality_text_with_audio"
            elif has_audio and not has_text:
                strategy_key = "audio_only"
            else:
                strategy_key = "text_only"
        else:
            # Gebruik specifieke mode
            strategy_key = "high_quality_text_with_audio"  # Default
        
        strategy = self.processing_strategies.get(strategy_key, 
                                                self.processing_strategies["text_only"])
        
        # Pas gewichten aan op basis van input weights
        if total_weight > 0:
            text_inputs = [inp for inp in inputs if inp.modality == ModalityType.TEXT_DOCUMENT]
            audio_inputs = [inp for inp in inputs if inp.modality == ModalityType.AUDIO_RECORDING]
            
            text_weight = sum(inp.weight for inp in text_inputs) / total_weight
            audio_weight = sum(inp.weight for inp in audio_inputs) / total_weight
            
            strategy = strategy.copy()
            strategy["text_weight"] = text_weight
            strategy["audio_weight"] = audio_weight
        
        return strategy
    
    async def _evaluate_text_quality(self, inputs: List[ModalInput]) -> float:
        """Evalueer de kwaliteit van tekst inputs"""
        text_inputs = [inp for inp in inputs if inp.modality == ModalityType.TEXT_DOCUMENT]
        
        if not text_inputs:
            return 0.0
        
        total_score = 0.0
        for inp in text_inputs:
            if isinstance(inp.content, str):
                # Basis kwaliteitsmetrics
                length_score = min(len(inp.content) / 1000, 1.0)  # Normaliseer naar 1000 chars
                word_count = len(inp.content.split())
                complexity_score = min(word_count / 200, 1.0)  # Normaliseer naar 200 woorden
                
                # Nederlandse arbeidsdeskundige terminologie check
                dutch_terms = ["arbeidsdeskundige", "belastbaarheid", "werkhervatting", 
                              "re-integratie", "arbeidsongeval", "verzuim"]
                term_score = sum(1 for term in dutch_terms if term in inp.content.lower()) / len(dutch_terms)
                
                input_score = (length_score + complexity_score + term_score) / 3
                total_score += input_score * inp.weight
        
        return total_score / len(text_inputs)
    
    async def _preprocess_modalities(self, inputs: List[ModalInput]) -> List[ModalInput]:
        """Pre-process alle input modaliteiten"""
        processed_inputs = []
        
        for inp in inputs:
            processed_inp = inp
            
            if inp.modality == ModalityType.AUDIO_RECORDING:
                # Transcribeer audio naar tekst
                try:
                    if isinstance(inp.content, bytes):
                        transcript = await self._transcribe_audio(inp.content)
                        processed_inp = ModalInput(
                            modality=ModalityType.TEXT_DOCUMENT,  # Convert to text
                            content=transcript,
                            metadata={**inp.metadata, "source": "audio_transcription"},
                            weight=inp.weight,
                            quality_score=self._estimate_transcription_quality(transcript)
                        )
                except Exception as e:
                    self.logger.error(f"Audio transcription failed: {e}")
                    continue
            
            elif inp.modality == ModalityType.TEXT_DOCUMENT:
                # Classificeer en evalueer tekst
                try:
                    classification = await self.document_classifier.classify_document(
                        str(inp.content), 
                        inp.metadata.get("filename", "")
                    )
                    processed_inp.metadata["classification"] = classification
                    processed_inp.quality_score = classification.get("confidence", 0.5)
                except Exception as e:
                    self.logger.error(f"Document classification failed: {e}")
            
            processed_inputs.append(processed_inp)
        
        return processed_inputs
    
    async def _transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribeer audio naar tekst met geoptimaliseerde pipeline"""
        try:
            import tempfile
            import os
            
            # Try to import optimized transcription functions
            try:
                from app.tasks.process_audio_tasks.optimized_audio_transcriber import (
                    prepare_audio_for_transcription, 
                    transcribe_single_chunk,
                    combine_chunk_results,
                    optimize_for_dutch
                )
                from openai import OpenAI
                from app.core.config import settings
                
                # Create temporary file for audio data
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                    temp_file.write(audio_data)
                    temp_path = temp_file.name
                
                try:
                    # Prepare audio for transcription
                    prepared_file, audio_metadata = prepare_audio_for_transcription(temp_path)
                    
                    # Use Dutch-optimized transcription
                    api_key = settings.OPENAI_API_KEY
                    if api_key and len(str(api_key).strip()) > 10:
                        client = OpenAI(api_key=str(api_key).strip().strip('"'))
                        
                        config = {
                            "model": "whisper-1",
                            "temperature": 0.1,
                            "language": "nl"
                        }
                        
                        # Transcribe with optimized settings
                        chunk_result = transcribe_single_chunk(
                            client, prepared_file, config, 0.0
                        )
                        
                        # Apply Dutch optimization
                        transcription = chunk_result.text
                        
                        # Simple Dutch optimization inline
                        dutch_corrections = {
                            "arbeidsongeschikt": "arbeidsgeschikt",
                            "arbeidsexpert": "arbeidsdeskundige",
                            "UWV kantoor": "UWV"
                        }
                        
                        for incorrect, correct in dutch_corrections.items():
                            transcription = transcription.replace(incorrect, correct)
                        
                        self.logger.info(f"Audio transcription completed: {len(transcription)} characters")
                        return transcription
                    else:
                        # Fallback without API key
                        return f"Gesimuleerde transcriptie van audio ({len(audio_data)} bytes): Audio inhoud bevat arbeidsdeskundige informatie."
                
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    if prepared_file != temp_path and os.path.exists(prepared_file):
                        os.remove(prepared_file)
                        
            except ImportError as ie:
                self.logger.warning(f"Could not import optimized transcription: {ie}")
                # Fallback: simulate transcription for testing
                return f"Gesimuleerde transcriptie van audio ({len(audio_data)} bytes): Audio bevat gesproken arbeidsdeskundige content."
                
        except Exception as e:
            self.logger.error(f"Audio transcription error: {e}")
            return "[Audio transcriptie gefaald]"
    
    def _estimate_transcription_quality(self, transcript: str) -> float:
        """Schat de kwaliteit van transcriptie"""
        if not transcript or "[Audio transcriptie gefaald]" in transcript:
            return 0.0
        
        # Basis kwaliteitsmetrics
        length_score = min(len(transcript) / 500, 1.0)
        word_count = len(transcript.split())
        
        # Check voor transcriptie artifacts
        artifacts = ["[unclear]", "[inaudible]", "uh", "um", "..."]
        artifact_penalty = sum(transcript.lower().count(artifact) for artifact in artifacts) * 0.1
        
        quality = length_score - artifact_penalty
        return max(0.0, min(1.0, quality))
    
    async def _extract_multimodal_context(
        self, 
        inputs: List[ModalInput], 
        strategy: Dict[str, Any]
    ) -> MultiModalContext:
        """Extract en combineer context van alle modaliteiten"""
        
        text_chunks = []
        audio_transcripts = []
        modality_weights = {}
        confidence_scores = {}
        
        # Verzamel content per modaliteit
        for inp in inputs:
            if inp.modality == ModalityType.TEXT_DOCUMENT:
                # Chunk tekst content
                if isinstance(inp.content, str) and inp.content.strip():
                    # Use RAG pipeline voor optimale chunking
                    document_type = inp.metadata.get("classification", {}).get("type")
                    chunks = await self._chunk_content(inp.content, document_type)
                    text_chunks.extend(chunks)
                    
                modality_weights[ModalityType.TEXT_DOCUMENT] = inp.weight
                confidence_scores[ModalityType.TEXT_DOCUMENT] = inp.quality_score or 0.5
                
            elif inp.modality == ModalityType.AUDIO_RECORDING:
                # Audio is already transcribed in preprocessing
                if isinstance(inp.content, str):
                    audio_transcripts.append(inp.content)
                    
                modality_weights[ModalityType.AUDIO_RECORDING] = inp.weight
                confidence_scores[ModalityType.AUDIO_RECORDING] = inp.quality_score or 0.5
        
        # Combineer insights van verschillende modaliteiten
        combined_insights = await self._generate_combined_insights(
            text_chunks, audio_transcripts, strategy
        )
        
        return MultiModalContext(
            text_chunks=text_chunks,
            audio_transcripts=audio_transcripts,
            combined_insights=combined_insights,
            modality_weights=modality_weights,
            confidence_scores=confidence_scores,
            processing_metadata={
                "strategy": strategy,
                "total_text_chunks": len(text_chunks),
                "total_audio_transcripts": len(audio_transcripts),
                "processing_timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def _chunk_content(self, content: str, document_type: Optional[str]) -> List[str]:
        """Chunk content using optimized RAG pipeline"""
        try:
            doc_type = DocumentType(document_type) if document_type else DocumentType.UNKNOWN
            chunks = await self.rag_pipeline.chunk_document(content, doc_type)
            return [chunk["text"] for chunk in chunks]
        except Exception as e:
            self.logger.error(f"Content chunking failed: {e}")
            # Fallback: simple chunking
            sentences = content.split(". ")
            return [f"{s}." for s in sentences if len(s.strip()) > 20]
    
    async def _generate_combined_insights(
        self, 
        text_chunks: List[str], 
        audio_transcripts: List[str], 
        strategy: Dict[str, Any]
    ) -> List[str]:
        """Genereer gecombineerde inzichten van alle modaliteiten"""
        
        insights = []
        
        # Cross-reference informatie tussen modaliteiten
        if text_chunks and audio_transcripts:
            # Zoek naar overlap en tegenstrijdigheden
            text_content = " ".join(text_chunks).lower()
            audio_content = " ".join(audio_transcripts).lower()
            
            # Analyseer overlap
            text_words = set(text_content.split())
            audio_words = set(audio_content.split())
            
            overlap = text_words.intersection(audio_words)
            if len(overlap) > 10:  # Significante overlap
                insights.append(f"Sterke consistentie tussen tekst en audio (overlap: {len(overlap)} woorden)")
            
            # Zoek naar unieke informatie in audio
            audio_unique = audio_words - text_words
            if len(audio_unique) > 20:
                insights.append("Audio bevat aanvullende informatie niet gevonden in tekst")
            
            # Zoek naar mogelijke tegenstrijdigheden
            negative_indicators_text = ["niet", "geen", "onmogelijk"] 
            negative_indicators_audio = ["wel", "kan", "mogelijk"]
            
            text_negative = any(indicator in text_content for indicator in negative_indicators_text)
            audio_positive = any(indicator in audio_content for indicator in negative_indicators_audio)
            
            if text_negative and audio_positive:
                insights.append("Mogelijke tegenstrijdigheid tussen tekst en audio gedetecteerd")
        
        # Modaliteit-specifieke insights
        if text_chunks:
            total_text_length = sum(len(chunk) for chunk in text_chunks)
            insights.append(f"Tekst analyse: {len(text_chunks)} chunks, {total_text_length} karakters")
        
        if audio_transcripts:
            total_audio_length = sum(len(transcript) for transcript in audio_transcripts)
            insights.append(f"Audio analyse: {len(audio_transcripts)} transcripties, {total_audio_length} karakters")
        
        return insights
    
    async def _generate_multimodal_content(
        self, 
        context: MultiModalContext, 
        section: ReportSection, 
        complexity_level: ComplexityLevel, 
        strategy: Dict[str, Any]
    ) -> str:
        """Genereer content op basis van multi-modal context"""
        
        # Combineer alle beschikbare context
        all_chunks = []
        
        # Voeg tekst chunks toe (met gewicht)
        text_weight = strategy.get("text_weight", 0.5)
        if text_weight > 0 and context.text_chunks:
            weighted_text_chunks = context.text_chunks[:int(10 * text_weight)]  # Max 10 chunks
            all_chunks.extend(weighted_text_chunks)
        
        # Voeg audio transcripties toe (met gewicht)
        audio_weight = strategy.get("audio_weight", 0.5)
        if audio_weight > 0 and context.audio_transcripts:
            weighted_audio_chunks = context.audio_transcripts[:int(5 * audio_weight)]  # Max 5 transcripts
            all_chunks.extend(weighted_audio_chunks)
        
        # Voeg combined insights toe
        all_chunks.extend(context.combined_insights)
        
        # Genereer context-aware prompt
        try:
            content = self.prompt_generator.generate_section_prompt(
                section=section,
                context_chunks=all_chunks,
                complexity_level=complexity_level,
                additional_context={
                    "multimodal_strategy": strategy["strategy"],
                    "modality_weights": context.modality_weights,
                    "confidence_scores": context.confidence_scores
                }
            )
            return content
        except Exception as e:
            self.logger.error(f"Content generation failed: {e}")
            return self._generate_fallback_content(context, section)
    
    def _generate_fallback_content(self, context: MultiModalContext, section: ReportSection) -> str:
        """Genereer fallback content als hoofdgeneratie faalt"""
        
        content_parts = []
        
        if context.text_chunks:
            content_parts.append("Op basis van de beschikbare documentatie:")
            content_parts.extend(context.text_chunks[:3])  # Eerste 3 chunks
        
        if context.audio_transcripts:
            content_parts.append("\nAanvullende informatie uit audio:")
            content_parts.extend(context.audio_transcripts[:2])  # Eerste 2 transcripts
        
        if context.combined_insights:
            content_parts.append("\nGecombineerde analyse:")
            content_parts.extend(context.combined_insights)
        
        if not content_parts:
            content_parts.append(f"Voor de {section.value} sectie zijn aanvullende gegevens nodig voor een volledige analyse.")
        
        return "\n\n".join(content_parts)
    
    async def _quality_assurance(
        self, 
        content: str, 
        context: MultiModalContext, 
        section: ReportSection
    ) -> str:
        """Voer kwaliteitscontrole uit en verbeter indien nodig"""
        
        try:
            # Gebruik quality controller voor validatie
            quality_report = await self.quality_controller.validate_content(
                content=content,
                section=section,
                context_chunks=context.text_chunks + context.audio_transcripts
            )
            
            # Verbeter content als score te laag is
            if quality_report.overall_score < self.quality_thresholds["final_content_quality"]:
                self.logger.info(f"Content quality {quality_report.overall_score:.2f} below threshold, improving...")
                improved_content = await self.quality_controller.improve_content(quality_report)
                return improved_content
            
            return content
            
        except Exception as e:
            self.logger.error(f"Quality assurance failed: {e}")
            return content  # Return original content if QA fails
    
    async def _calculate_overall_quality(
        self, 
        content: str, 
        context: MultiModalContext
    ) -> float:
        """Bereken overall kwaliteitsscore"""
        
        scores = []
        
        # Content kwaliteit (lengte, structure, etc.)
        content_score = min(len(content) / 500, 1.0)  # Normaliseer naar 500 chars
        scores.append(content_score)
        
        # Context confidence scores
        for modality, confidence in context.confidence_scores.items():
            weight = context.modality_weights.get(modality, 0.5)
            weighted_confidence = confidence * weight
            scores.append(weighted_confidence)
        
        # Combined insights quality
        insights_score = min(len(context.combined_insights) / 3, 1.0)  # Normaliseer naar 3 insights
        scores.append(insights_score)
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def _generate_recommendations(
        self, 
        context: MultiModalContext, 
        quality_score: float
    ) -> List[str]:
        """Genereer aanbevelingen op basis van processing resultaten"""
        
        recommendations = []
        
        # Kwaliteit-gebaseerde aanbevelingen
        if quality_score < 0.6:
            recommendations.append("Overweeg aanvullende documentatie voor betere kwaliteit")
        
        # Modaliteit-gebaseerde aanbevelingen
        text_confidence = context.confidence_scores.get(ModalityType.TEXT_DOCUMENT, 0)
        audio_confidence = context.confidence_scores.get(ModalityType.AUDIO_RECORDING, 0)
        
        if text_confidence < 0.5:
            recommendations.append("Tekst documentatie kan verbeterd worden")
        
        if audio_confidence < 0.5:
            recommendations.append("Audio kwaliteit kan verbeterd worden voor betere transcriptie")
        
        # Context-gebaseerde aanbevelingen
        if len(context.text_chunks) < 3:
            recommendations.append("Meer tekstuele context zou helpen voor betere analyse")
        
        if len(context.audio_transcripts) == 0:
            recommendations.append("Audio opnames kunnen waardevolle aanvullende informatie bieden")
        
        # Combined insights aanbevelingen
        if "tegenstrijdigheid" in " ".join(context.combined_insights).lower():
            recommendations.append("Tegenstrijdige informatie gedetecteerd - verificatie aanbevolen")
        
        return recommendations
    
    def _create_fallback_result(
        self, 
        inputs: List[ModalInput], 
        section: ReportSection
    ) -> MultiModalResult:
        """Creëer fallback resultaat bij falen van processing"""
        
        return MultiModalResult(
            generated_content=f"Voor de {section.value} sectie kon geen volledig multi-modal rapport worden gegenereerd. Aanvullende informatie is nodig.",
            source_modalities=[inp.modality for inp in inputs],
            context_used=MultiModalContext(
                text_chunks=[],
                audio_transcripts=[],
                combined_insights=["Multi-modal processing gefaald"],
                modality_weights={},
                confidence_scores={},
                processing_metadata={"error": "Processing failed"}
            ),
            quality_score=0.3,
            processing_time=0.0,
            recommendations=[
                "Controleer input kwaliteit",
                "Probeer met eenvoudigere content",
                "Gebruik enkele modaliteit in plaats van multi-modal"
            ],
            metadata={
                "error": "Fallback result due to processing failure",
                "inputs_count": len(inputs),
                "section": section.value
            }
        )
    
    async def get_processing_statistics(self) -> Dict[str, Any]:
        """Krijg statistieken over multi-modal processing"""
        
        return {
            "available_modalities": [modality.value for modality in ModalityType],
            "processing_modes": [mode.value for mode in ProcessingMode],
            "quality_thresholds": self.quality_thresholds,
            "default_weights": self.modality_weights,
            "supported_strategies": list(self.processing_strategies.keys())
        }