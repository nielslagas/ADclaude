from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging

from app.utils.context_aware_prompts import ContextAwarePromptGenerator, ReportSection, ComplexityLevel
from app.utils.smart_document_classifier import DocumentType
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class PromptRequest(BaseModel):
    section: str
    document_type: Optional[str] = None
    complexity_level: Optional[str] = "medium"
    context_chunks: List[str] = []
    additional_context: Optional[Dict[str, Any]] = None


class PromptResponse(BaseModel):
    section: str
    prompt: str
    context_analysis: Dict[str, Any]
    quality_criteria: List[str]
    estimated_tokens: int


class SectionInfo(BaseModel):
    section: str
    display_name: str
    description: str
    typical_length: str
    key_elements: List[str]


@router.post("/generate-prompt", response_model=PromptResponse)
async def generate_context_aware_prompt(
    request: PromptRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Genereer een context-aware prompt voor een specifieke rapport sectie.
    """
    try:
        generator = ContextAwarePromptGenerator()
        
        # Valideer section
        try:
            section = ReportSection(request.section)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Ongeldige sectie: {request.section}. Geldige secties: {[s.value for s in ReportSection]}"
            )
        
        # Valideer document type
        document_type = None
        if request.document_type:
            try:
                document_type = DocumentType(request.document_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ongeldig document type: {request.document_type}"
                )
        
        # Valideer complexity level
        try:
            complexity = ComplexityLevel(request.complexity_level)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Ongeldig complexiteitsniveau: {request.complexity_level}"
            )
        
        # Genereer prompt
        prompt = generator.generate_section_prompt(
            section=section,
            context_chunks=request.context_chunks,
            document_type=document_type,
            complexity_level=complexity,
            additional_context=request.additional_context or {}
        )
        
        # Analyseer context
        context_analysis = generator.analyze_context(
            request.context_chunks,
            section,
            document_type
        )
        
        # Krijg quality criteria
        quality_criteria = generator.get_quality_criteria(section, complexity)
        
        # Schat tokens (ruwe schatting: 1 token ≈ 4 karakters voor Nederlands)
        estimated_tokens = len(prompt) // 4
        
        return PromptResponse(
            section=request.section,
            prompt=prompt,
            context_analysis=context_analysis,
            quality_criteria=quality_criteria,
            estimated_tokens=estimated_tokens
        )
        
    except Exception as e:
        logger.error(f"Fout bij genereren prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij genereren prompt: {str(e)}")


@router.get("/sections", response_model=List[SectionInfo])
async def get_available_sections(
    current_user: dict = Depends(get_current_user)
):
    """
    Krijg informatie over alle beschikbare rapport secties.
    """
    try:
        generator = ContextAwarePromptGenerator()
        sections_info = []
        
        section_descriptions = {
            ReportSection.INTRODUCTIE: {
                "display_name": "Introductie",
                "description": "Inleiding en achtergrond van het rapport",
                "typical_length": "1-2 paragrafen",
                "key_elements": ["Doel rapport", "Aanleiding", "Scope", "Methodiek"]
            },
            ReportSection.MEDISCHE_SITUATIE: {
                "display_name": "Medische Situatie",
                "description": "Overzicht van medische conditie en behandeling",
                "typical_length": "2-3 paragrafen",
                "key_elements": ["Diagnose", "Behandeling", "Prognose", "Medicatie", "Specialisten"]
            },
            ReportSection.BELASTBAARHEID: {
                "display_name": "Belastbaarheid",
                "description": "Analyse van fysieke en mentale belastbaarheid",
                "typical_length": "2-4 paragrafen",
                "key_elements": ["Fysieke capaciteit", "Mentale capaciteit", "FCE resultaten", "Beperkingen"]
            },
            ReportSection.BEPERKINGEN: {
                "display_name": "Beperkingen",
                "description": "Specifieke beperkingen en limitaties",
                "typical_length": "1-2 paragrafen",
                "key_elements": ["Functionele beperkingen", "Tijdsduur", "Intensiteit", "Impact"]
            },
            ReportSection.MOGELIJKHEDEN: {
                "display_name": "Mogelijkheden",
                "description": "Resterende capaciteiten en mogelijkheden",
                "typical_length": "1-2 paragrafen",
                "key_elements": ["Restcapaciteit", "Geschiktheid", "Aanpassingen", "Alternatieven"]
            },
            ReportSection.WERKHERVATTING: {
                "display_name": "Werkhervatting",
                "description": "Advies over werkhervatting en re-integratie",
                "typical_length": "2-3 paragrafen",
                "key_elements": ["Timing", "Geleidelijkheid", "Aanpassingen", "Begeleiding"]
            },
            ReportSection.ADVIES: {
                "display_name": "Advies",
                "description": "Concrete aanbevelingen en interventies",
                "typical_length": "2-3 paragrafen",
                "key_elements": ["Concrete stappen", "Prioriteiten", "Verantwoordelijkheden", "Timeline"]
            },
            ReportSection.CONCLUSIE: {
                "display_name": "Conclusie",
                "description": "Samenvatting en eindconclusie",
                "typical_length": "1-2 paragrafen",
                "key_elements": ["Kernpunten", "Eindoordeel", "Vervolgstappen", "Prognose"]
            }
        }
        
        for section in ReportSection:
            info = section_descriptions.get(section, {})
            sections_info.append(SectionInfo(
                section=section.value,
                display_name=info.get("display_name", section.value.title()),
                description=info.get("description", ""),
                typical_length=info.get("typical_length", "Variabel"),
                key_elements=info.get("key_elements", [])
            ))
        
        return sections_info
        
    except Exception as e:
        logger.error(f"Fout bij ophalen secties: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij ophalen secties: {str(e)}")


@router.get("/complexity-levels")
async def get_complexity_levels(
    current_user: dict = Depends(get_current_user)
):
    """
    Krijg informatie over beschikbare complexiteitsniveaus.
    """
    return {
        "levels": [
            {
                "value": ComplexityLevel.BASIC.value,
                "display_name": "Basis",
                "description": "Eenvoudige gevallen met duidelijke situatie"
            },
            {
                "value": ComplexityLevel.MEDIUM.value,
                "display_name": "Gemiddeld",
                "description": "Standaard gevallen met normale complexiteit"
            },
            {
                "value": ComplexityLevel.COMPLEX.value,
                "display_name": "Complex",
                "description": "Complexe gevallen met meerdere factoren"
            }
        ]
    }


@router.post("/analyze-context")
async def analyze_document_context(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyseer document context voor betere prompt generatie.
    """
    try:
        generator = ContextAwarePromptGenerator()
        
        context_chunks = request.get("context_chunks", [])
        section = request.get("section")
        document_type = request.get("document_type")
        
        # Valideer section
        if section:
            try:
                section = ReportSection(section)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Ongeldige sectie: {section}")
        
        # Valideer document type
        if document_type:
            try:
                document_type = DocumentType(document_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Ongeldig document type: {document_type}")
        
        # Analyseer context
        analysis = generator.analyze_context(context_chunks, section, document_type)
        
        return {
            "analysis": analysis,
            "recommendations": generator._generate_section_guidelines(section, document_type) if section else {},
            "chunk_count": len(context_chunks),
            "total_content_length": sum(len(chunk) for chunk in context_chunks)
        }
        
    except Exception as e:
        logger.error(f"Fout bij context analyse: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij context analyse: {str(e)}")


@router.post("/batch-prompts")
async def generate_batch_prompts(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Genereer prompts voor meerdere secties tegelijk.
    """
    try:
        generator = ContextAwarePromptGenerator()
        
        sections = request.get("sections", [])
        context_chunks = request.get("context_chunks", [])
        document_type = request.get("document_type")
        complexity_level = request.get("complexity_level", "medium")
        additional_context = request.get("additional_context", {})
        
        if not sections:
            raise HTTPException(status_code=400, detail="Geen secties opgegeven")
        
        # Valideer inputs
        valid_sections = []
        for section in sections:
            try:
                valid_sections.append(ReportSection(section))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Ongeldige sectie: {section}")
        
        doc_type = None
        if document_type:
            try:
                doc_type = DocumentType(document_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Ongeldig document type: {document_type}")
        
        try:
            complexity = ComplexityLevel(complexity_level)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Ongeldig complexiteitsniveau: {complexity_level}")
        
        # Genereer prompts voor alle secties
        results = {}
        for section in valid_sections:
            prompt = generator.generate_section_prompt(
                section=section,
                context_chunks=context_chunks,
                document_type=doc_type,
                complexity_level=complexity,
                additional_context=additional_context
            )
            
            context_analysis = generator.analyze_context(context_chunks, section, doc_type)
            quality_criteria = generator.get_quality_criteria(section, complexity)
            
            results[section.value] = {
                "prompt": prompt,
                "context_analysis": context_analysis,
                "quality_criteria": quality_criteria,
                "estimated_tokens": len(prompt) // 4
            }
        
        return {
            "prompts": results,
            "total_sections": len(valid_sections),
            "total_estimated_tokens": sum(result["estimated_tokens"] for result in results.values())
        }
        
    except Exception as e:
        logger.error(f"Fout bij batch prompt generatie: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij batch prompt generatie: {str(e)}")