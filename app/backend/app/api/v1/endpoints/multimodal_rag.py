from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
import logging
import base64

from app.utils.multimodal_rag import (
    MultiModalRAGPipeline, ModalInput, ModalityType, 
    ProcessingMode, MultiModalResult
)
from app.utils.context_aware_prompts import ReportSection, ComplexityLevel
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class MultiModalRequest(BaseModel):
    section: str
    complexity_level: Optional[str] = "medium"
    processing_mode: Optional[str] = "adaptive"
    text_inputs: Optional[List[Dict[str, Any]]] = []
    audio_metadata: Optional[List[Dict[str, Any]]] = []  # Metadata for uploaded audio files


class ModalInputResponse(BaseModel):
    modality: str
    content_length: int
    weight: float
    quality_score: Optional[float]
    metadata: Dict[str, Any]


class MultiModalResponse(BaseModel):
    generated_content: str
    source_modalities: List[str]
    quality_score: float
    processing_time: float
    recommendations: List[str]
    context_summary: Dict[str, Any]
    metadata: Dict[str, Any]


class ProcessingStatistics(BaseModel):
    available_modalities: List[str]
    processing_modes: List[str]
    quality_thresholds: Dict[str, float]
    default_weights: Dict[str, float]
    supported_strategies: List[str]


@router.post("/process", response_model=MultiModalResponse)
async def process_multimodal_content(
    section: str = Form(...),
    complexity_level: str = Form("medium"),
    processing_mode: str = Form("adaptive"),
    text_inputs: Optional[str] = Form("[]"),  # JSON string of text inputs
    audio_files: List[UploadFile] = File([]),
    current_user: dict = Depends(get_current_user)
):
    """
    Verwerk multi-modal content (tekst + audio) voor rapport generatie.
    """
    try:
        pipeline = MultiModalRAGPipeline()
        
        # Valideer section
        try:
            report_section = ReportSection(section)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Ongeldige sectie: {section}. Geldige secties: {[s.value for s in ReportSection]}"
            )
        
        # Valideer complexity level
        try:
            complexity = ComplexityLevel(complexity_level)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Ongeldig complexiteitsniveau: {complexity_level}"
            )
        
        # Valideer processing mode
        try:
            proc_mode = ProcessingMode(processing_mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Ongeldige processing mode: {processing_mode}"
            )
        
        # Parse text inputs
        import json
        try:
            text_data = json.loads(text_inputs) if text_inputs != "[]" else []
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Ongeldige JSON voor text_inputs")
        
        # Creëer modal inputs
        modal_inputs = []
        
        # Voeg tekst inputs toe
        for text_input in text_data:
            content = text_input.get("content", "")
            weight = text_input.get("weight", 1.0)
            metadata = text_input.get("metadata", {})
            
            if content.strip():
                modal_inputs.append(ModalInput(
                    modality=ModalityType.TEXT_DOCUMENT,
                    content=content,
                    metadata=metadata,
                    weight=weight
                ))
        
        # Voeg audio files toe
        for audio_file in audio_files:
            if audio_file.size > 10 * 1024 * 1024:  # 10MB limit
                raise HTTPException(status_code=400, detail=f"Audio bestand {audio_file.filename} te groot (max 10MB)")
            
            audio_content = await audio_file.read()
            
            modal_inputs.append(ModalInput(
                modality=ModalityType.AUDIO_RECORDING,
                content=audio_content,
                metadata={
                    "filename": audio_file.filename,
                    "content_type": audio_file.content_type,
                    "size": len(audio_content)
                },
                weight=1.0
            ))
        
        if not modal_inputs:
            raise HTTPException(status_code=400, detail="Geen geldige inputs verstrekt")
        
        # Verwerk multi-modal content
        result = await pipeline.process_multimodal_content(
            inputs=modal_inputs,
            section=report_section,
            complexity_level=complexity,
            processing_mode=proc_mode
        )
        
        return MultiModalResponse(
            generated_content=result.generated_content,
            source_modalities=[modality.value for modality in result.source_modalities],
            quality_score=result.quality_score,
            processing_time=result.processing_time,
            recommendations=result.recommendations,
            context_summary={
                "text_chunks_count": len(result.context_used.text_chunks),
                "audio_transcripts_count": len(result.context_used.audio_transcripts),
                "combined_insights_count": len(result.context_used.combined_insights),
                "modality_weights": {k.value: v for k, v in result.context_used.modality_weights.items()},
                "confidence_scores": {k.value: v for k, v in result.context_used.confidence_scores.items()}
            },
            metadata=result.metadata
        )
        
    except Exception as e:
        logger.error(f"Fout bij multi-modal verwerking: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij multi-modal verwerking: {str(e)}")


@router.post("/process-json", response_model=MultiModalResponse)
async def process_multimodal_json(
    request: MultiModalRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Verwerk multi-modal content via JSON (alleen tekst, geen file uploads).
    """
    try:
        pipeline = MultiModalRAGPipeline()
        
        # Valideer section
        try:
            report_section = ReportSection(request.section)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Ongeldige sectie: {request.section}"
            )
        
        # Valideer complexity level
        try:
            complexity = ComplexityLevel(request.complexity_level)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Ongeldig complexiteitsniveau: {request.complexity_level}"
            )
        
        # Valideer processing mode
        try:
            proc_mode = ProcessingMode(request.processing_mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Ongeldige processing mode: {request.processing_mode}"
            )
        
        # Creëer modal inputs van JSON
        modal_inputs = []
        
        # Voeg tekst inputs toe
        for text_input in request.text_inputs:
            content = text_input.get("content", "")
            weight = text_input.get("weight", 1.0)
            metadata = text_input.get("metadata", {})
            
            if content.strip():
                modal_inputs.append(ModalInput(
                    modality=ModalityType.TEXT_DOCUMENT,
                    content=content,
                    metadata=metadata,
                    weight=weight
                ))
        
        # Verwerk base64-encoded audio (indien aanwezig)
        for audio_meta in (request.audio_metadata or []):
            if "base64_content" in audio_meta:
                try:
                    audio_content = base64.b64decode(audio_meta["base64_content"])
                    
                    modal_inputs.append(ModalInput(
                        modality=ModalityType.AUDIO_RECORDING,
                        content=audio_content,
                        metadata={
                            "filename": audio_meta.get("filename", "audio.wav"),
                            "content_type": audio_meta.get("content_type", "audio/wav"),
                            "size": len(audio_content)
                        },
                        weight=audio_meta.get("weight", 1.0)
                    ))
                except Exception as e:
                    logger.warning(f"Could not decode base64 audio: {e}")
        
        if not modal_inputs:
            raise HTTPException(status_code=400, detail="Geen geldige inputs verstrekt")
        
        # Verwerk multi-modal content
        result = await pipeline.process_multimodal_content(
            inputs=modal_inputs,
            section=report_section,
            complexity_level=complexity,
            processing_mode=proc_mode
        )
        
        return MultiModalResponse(
            generated_content=result.generated_content,
            source_modalities=[modality.value for modality in result.source_modalities],
            quality_score=result.quality_score,
            processing_time=result.processing_time,
            recommendations=result.recommendations,
            context_summary={
                "text_chunks_count": len(result.context_used.text_chunks),
                "audio_transcripts_count": len(result.context_used.audio_transcripts),
                "combined_insights_count": len(result.context_used.combined_insights),
                "modality_weights": {k.value: v for k, v in result.context_used.modality_weights.items()},
                "confidence_scores": {k.value: v for k, v in result.context_used.confidence_scores.items()}
            },
            metadata=result.metadata
        )
        
    except Exception as e:
        logger.error(f"Fout bij multi-modal JSON verwerking: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij multi-modal JSON verwerking: {str(e)}")


@router.get("/statistics", response_model=ProcessingStatistics)
async def get_processing_statistics(
    current_user: dict = Depends(get_current_user)
):
    """
    Krijg statistieken en configuratie informatie over multi-modal processing.
    """
    try:
        pipeline = MultiModalRAGPipeline()
        stats = await pipeline.get_processing_statistics()
        
        return ProcessingStatistics(**stats)
        
    except Exception as e:
        logger.error(f"Fout bij ophalen statistieken: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij ophalen statistieken: {str(e)}")


@router.get("/modalities")
async def get_available_modalities(
    current_user: dict = Depends(get_current_user)
):
    """
    Krijg informatie over beschikbare modaliteiten.
    """
    return {
        "modalities": [
            {
                "value": ModalityType.TEXT_DOCUMENT.value,
                "display_name": "Tekst Document",
                "description": "Tekstuele documenten en content",
                "supported_formats": ["txt", "pdf", "docx", "plain text"]
            },
            {
                "value": ModalityType.AUDIO_RECORDING.value,
                "display_name": "Audio Opname",
                "description": "Audio opnames die getranscribeerd worden",
                "supported_formats": ["wav", "mp3", "m4a", "webm"]
            },
            {
                "value": ModalityType.MIXED_CONTENT.value,
                "display_name": "Gemixte Content",
                "description": "Combinatie van tekst en audio in één input",
                "supported_formats": ["mixed"]
            }
        ],
        "processing_modes": [
            {
                "value": ProcessingMode.SEQUENTIAL.value,
                "display_name": "Sequentieel",
                "description": "Verwerk modaliteiten één voor één"
            },
            {
                "value": ProcessingMode.PARALLEL.value,
                "display_name": "Parallel",
                "description": "Verwerk modaliteiten gelijktijdig"
            },
            {
                "value": ProcessingMode.INTEGRATED.value,
                "display_name": "Geïntegreerd",
                "description": "Volledig geïntegreerde verwerking"
            },
            {
                "value": ProcessingMode.ADAPTIVE.value,
                "display_name": "Adaptief",
                "description": "Automatisch beste strategie kiezen"
            }
        ]
    }


@router.post("/analyze-inputs")
async def analyze_multimodal_inputs(
    text_content: Optional[str] = Form(None),
    audio_files: List[UploadFile] = File([]),
    current_user: dict = Depends(get_current_user)
):
    """
    Analyseer multi-modal inputs voordat ze worden verwerkt.
    """
    try:
        analysis = {
            "input_summary": {
                "text_provided": bool(text_content and text_content.strip()),
                "audio_files_count": len(audio_files),
                "total_audio_size": 0
            },
            "recommendations": [],
            "estimated_processing_time": 0.0,
            "suggested_mode": ProcessingMode.ADAPTIVE.value
        }
        
        # Analyseer tekst input
        if text_content and text_content.strip():
            text_length = len(text_content)
            word_count = len(text_content.split())
            
            analysis["text_analysis"] = {
                "character_count": text_length,
                "word_count": word_count,
                "estimated_quality": min(text_length / 1000, 1.0),
                "language_detected": "dutch" if any(word in text_content.lower() 
                                                  for word in ["de", "het", "en", "van", "een"]) else "unknown"
            }
            
            analysis["estimated_processing_time"] += text_length / 5000  # ~5000 chars per second
            
            if text_length < 100:
                analysis["recommendations"].append("Tekst is erg kort - overweeg meer context")
            elif text_length > 5000:
                analysis["recommendations"].append("Lange tekst - processing kan even duren")
        
        # Analyseer audio inputs
        total_audio_size = 0
        audio_analysis = []
        
        for audio_file in audio_files:
            file_size = 0
            if hasattr(audio_file, 'size'):
                file_size = audio_file.size
            else:
                # Read file to get size (and reset position)
                content = await audio_file.read()
                file_size = len(content)
                await audio_file.seek(0)
            
            total_audio_size += file_size
            
            audio_info = {
                "filename": audio_file.filename,
                "content_type": audio_file.content_type,
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "estimated_transcription_time": file_size / (1024 * 100)  # Rough estimate
            }
            
            audio_analysis.append(audio_info)
            
            if file_size > 10 * 1024 * 1024:  # 10MB
                analysis["recommendations"].append(f"Audio bestand {audio_file.filename} is groot (>{audio_info['size_mb']}MB)")
        
        analysis["input_summary"]["total_audio_size"] = total_audio_size
        analysis["audio_analysis"] = audio_analysis
        analysis["estimated_processing_time"] += total_audio_size / (1024 * 200)  # Audio processing estimate
        
        # Bepaal suggested mode
        if text_content and audio_files:
            if len(text_content) > 2000:  # Lange tekst
                analysis["suggested_mode"] = ProcessingMode.INTEGRATED.value
            else:
                analysis["suggested_mode"] = ProcessingMode.PARALLEL.value
        elif audio_files and not text_content:
            analysis["suggested_mode"] = ProcessingMode.SEQUENTIAL.value
        
        # Algemene aanbevelingen
        if not text_content and not audio_files:
            analysis["recommendations"].append("Geen inputs verstrekt - voeg tekst of audio toe")
        elif len(analysis["recommendations"]) == 0:
            analysis["recommendations"].append("Inputs zien er goed uit voor verwerking")
        
        return analysis
        
    except Exception as e:
        logger.error(f"Fout bij input analyse: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij input analyse: {str(e)}")


@router.post("/batch-process")
async def batch_process_multimodal(
    requests: List[MultiModalRequest],
    current_user: dict = Depends(get_current_user)
):
    """
    Verwerk meerdere multi-modal requests in batch.
    """
    try:
        if len(requests) > 5:  # Limit batch size
            raise HTTPException(status_code=400, detail="Maximaal 5 requests per batch")
        
        pipeline = MultiModalRAGPipeline()
        results = []
        
        for i, request in enumerate(requests):
            try:
                # Converteer request naar modal inputs
                modal_inputs = []
                
                for text_input in request.text_inputs:
                    content = text_input.get("content", "")
                    if content.strip():
                        modal_inputs.append(ModalInput(
                            modality=ModalityType.TEXT_DOCUMENT,
                            content=content,
                            metadata=text_input.get("metadata", {}),
                            weight=text_input.get("weight", 1.0)
                        ))
                
                if modal_inputs:
                    result = await pipeline.process_multimodal_content(
                        inputs=modal_inputs,
                        section=ReportSection(request.section),
                        complexity_level=ComplexityLevel(request.complexity_level),
                        processing_mode=ProcessingMode(request.processing_mode)
                    )
                    
                    results.append({
                        "index": i,
                        "status": "success",
                        "result": {
                            "generated_content": result.generated_content,
                            "quality_score": result.quality_score,
                            "processing_time": result.processing_time,
                            "source_modalities": [m.value for m in result.source_modalities]
                        }
                    })
                else:
                    results.append({
                        "index": i,
                        "status": "error",
                        "error": "Geen geldige inputs"
                    })
                    
            except Exception as e:
                results.append({
                    "index": i,
                    "status": "error", 
                    "error": str(e)
                })
        
        # Bereken batch statistieken
        successful_results = [r for r in results if r["status"] == "success"]
        
        batch_stats = {
            "total_requests": len(requests),
            "successful": len(successful_results),
            "failed": len(requests) - len(successful_results),
            "average_quality_score": 0.0,
            "total_processing_time": 0.0
        }
        
        if successful_results:
            batch_stats["average_quality_score"] = sum(
                r["result"]["quality_score"] for r in successful_results
            ) / len(successful_results)
            
            batch_stats["total_processing_time"] = sum(
                r["result"]["processing_time"] for r in successful_results
            )
        
        return {
            "results": results,
            "batch_statistics": batch_stats
        }
        
    except Exception as e:
        logger.error(f"Fout bij batch verwerking: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij batch verwerking: {str(e)}")