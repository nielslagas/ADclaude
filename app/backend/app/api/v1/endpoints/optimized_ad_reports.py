"""
Optimized AD Reports API endpoint
Uses the new optimized AD report generator with fewer LLM calls
"""
import logging
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from app.db.database_service import get_database_service
from app.models.report import Report
from app.models.user_profile import UserProfile
from app.core.security import verify_token as get_current_user
from app.db.postgres import get_db
from app.utils.optimized_ad_generator import OptimizedADGenerator
from app.utils.ad_html_renderer import ADHtmlRenderer
from app.utils.vector_store_improved import HybridVectorStore
from app.celery_worker import celery

logger = logging.getLogger(__name__)

router = APIRouter()
db_service = get_database_service()

@router.post("/generate-optimized")
async def generate_optimized_ad_report(
    case_id: str = Body(..., description="Case ID to generate report for"),
    template: str = Body(default="standaard", description="Report template to use"),
    use_async: bool = Body(default=True, description="Use async generation via Celery"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate optimized AD report with fewer LLM calls
    
    This endpoint uses the new optimized generator that combines multiple
    sections per LLM call, reducing from 18 calls to approximately 5-6 calls.
    
    Returns:
        Report ID and generation status
    """
    try:
        user_id = current_user["id"]
        
        # Verify case exists and belongs to user
        case = db_service.get_case(case_id, user_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Get case documents
        documents = db_service.get_case_documents(case_id)
        if not documents:
            raise HTTPException(
                status_code=400,
                detail="No documents found for this case. Please upload documents first."
            )
        
        # Create report record
        report_id = str(uuid4())
        report = Report(
            id=UUID(report_id),
            case_id=UUID(case_id),
            user_id=user_id,
            template_id=template,
            status="generating",
            created_at=datetime.utcnow()
        )
        
        # Save report to database
        db_service.create_report(report)
        
        if use_async:
            # Queue async task
            task = generate_optimized_ad_report_task.delay(
                report_id=report_id,
                case_id=case_id,
                user_id=user_id,
                template=template
            )
            
            return {
                "report_id": report_id,
                "status": "generating",
                "task_id": task.id,
                "message": "Optimized AD report generation started",
                "estimated_time": "30-60 seconds"
            }
        else:
            # Generate synchronously
            result = _generate_report_sync(
                report_id=report_id,
                case_id=case_id,
                user_id=user_id,
                template=template
            )
            
            return {
                "report_id": report_id,
                "status": "completed",
                "sections": result.get("sections_count", 0),
                "message": "Optimized AD report generated successfully"
            }
            
    except Exception as e:
        logger.error(f"Error generating optimized AD report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{report_id}/structured")
async def get_structured_ad_report(
    report_id: str,
    format: str = Query(default="html", description="Output format: html, json, or markdown"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get structured AD report in specified format
    
    Formats:
    - html: Professional HTML rendering
    - json: Structured JSON data
    - markdown: Markdown formatted text
    
    Returns:
        Report content in requested format
    """
    try:
        user_id = current_user["id"]
        
        # Get report from database
        report = db_service.get_report(report_id)
        if not report or report.user_id != user_id:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Check if report is generated
        if report.status != "generated":
            return {
                "status": report.status,
                "message": f"Report is {report.status}"
            }
        
        # Get structured content
        content = report.content
        if not content:
            raise HTTPException(status_code=404, detail="Report content not found")
        
        # Format based on request
        if format == "html":
            # Check if we have structured ADReport data
            if "structured_data" in content:
                from app.models.ad_report_structure import ADReport
                
                # Recreate ADReport from dict
                ad_report = ADReport(**content["structured_data"])
                
                # Render to HTML
                renderer = ADHtmlRenderer()
                html_content = renderer.render_complete_report(ad_report)
                
                return {
                    "format": "html",
                    "content": html_content,
                    "sections_count": len(content.get("sections", {})),
                    "generated_at": content.get("generated_at")
                }
            else:
                # Fallback to section-based HTML
                return {
                    "format": "html",
                    "content": content,
                    "message": "Legacy format - use new generator for structured HTML"
                }
                
        elif format == "json":
            return {
                "format": "json",
                "content": content,
                "sections_count": len(content.get("sections", {}))
            }
            
        elif format == "markdown":
            # Convert to markdown if structured data exists
            if "structured_data" in content:
                md_content = _convert_to_markdown(content["structured_data"])
                return {
                    "format": "markdown",
                    "content": md_content
                }
            else:
                return {
                    "format": "markdown",
                    "content": content,
                    "message": "Legacy format"
                }
        else:
            raise HTTPException(status_code=400, detail="Invalid format specified")
            
    except Exception as e:
        logger.error(f"Error retrieving structured report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{report_id}/status")
async def get_report_generation_status(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the status of report generation
    
    Returns:
        Current status and progress information
    """
    try:
        user_id = current_user["id"]
        
        # Get report from database
        report = db_service.get_report(report_id)
        if not report or report.user_id != user_id:
            raise HTTPException(status_code=404, detail="Report not found")
        
        response = {
            "report_id": report_id,
            "status": report.status,
            "created_at": report.created_at.isoformat() if report.created_at else None
        }
        
        # Add metadata if available
        if report.metadata:
            response["progress"] = report.metadata.get("progress", {})
            response["sections_completed"] = report.metadata.get("sections_completed", 0)
            response["total_sections"] = report.metadata.get("total_sections", 12)
            response["approach"] = report.metadata.get("approach", "optimized")
        
        # Add completion time if generated
        if report.status == "generated" and report.updated_at:
            response["completed_at"] = report.updated_at.isoformat()
            
            # Calculate generation time
            if report.created_at:
                duration = (report.updated_at - report.created_at).total_seconds()
                response["generation_time_seconds"] = duration
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting report status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Celery task
@celery.task(bind=True, name='generate_optimized_ad_report')
def generate_optimized_ad_report_task(
    self,
    report_id: str,
    case_id: str,
    user_id: str,
    template: str = "standaard"
) -> Dict[str, Any]:
    """
    Celery task for async optimized AD report generation
    """
    return _generate_report_sync(report_id, case_id, user_id, template)

def _generate_report_sync(
    report_id: str,
    case_id: str,
    user_id: str,
    template: str
) -> Dict[str, Any]:
    """
    Synchronous report generation logic
    """
    try:
        logger.info(f"Starting optimized AD report generation for report {report_id}")
        
        # Update status
        db_service.update_report(report_id, {
            "status": "processing",
            "metadata": {
                "approach": "optimized",
                "started_at": datetime.utcnow().isoformat()
            }
        })
        
        # Get case data
        case = db_service.get_case(case_id, user_id)
        case_data = {
            "case_id": case_id,
            "client_name": case.client_name,
            "company_name": case.company_name,
            "description": case.description
        }
        
        # Get document context
        documents = db_service.get_case_documents(case_id)
        context = _prepare_document_context(documents)
        
        # Generate with optimized generator
        generator = OptimizedADGenerator()
        ad_report = generator.generate_complete_report(context, case_data)
        
        # Convert structured data to sections format for compatibility
        sections_content = _convert_structured_to_sections(ad_report)
        
        # Prepare content for storage
        content = {
            "sections": sections_content,
            "structured_data": ad_report.dict(),
            "generated_at": datetime.utcnow().isoformat(),
            "generator": "optimized_v1",
            "template": template,
            "approach": "optimized_sections"
        }
        
        # Update report in database
        db_service.update_report(report_id, {
            "content": content,
            "status": "generated",
            "metadata": {
                "approach": "optimized",
                "completed_at": datetime.utcnow().isoformat(),
                "sections_count": len(content["sections"]),
                "llm_calls": 5  # Approximate number with optimized approach
            }
        })
        
        logger.info(f"Completed optimized AD report generation for report {report_id}")
        
        return {
            "status": "success",
            "report_id": report_id,
            "sections_count": len(content["sections"])
        }
        
    except Exception as e:
        logger.error(f"Error in sync report generation: {str(e)}")
        
        # Update report status to failed
        db_service.update_report(report_id, {
            "status": "failed",
            "metadata": {
                "error": str(e),
                "failed_at": datetime.utcnow().isoformat()
            }
        })
        
        raise

def _prepare_document_context(documents: list) -> str:
    """
    Prepare document context for LLM
    """
    context_parts = []
    
    for doc in documents:
        # Get document chunks
        chunks = db_service.get_document_chunks(doc["id"])
        if chunks:
            # Combine chunks
            content = "\n".join([chunk["content"] for chunk in chunks[:20]])  # Limit chunks
            context_parts.append(f"=== {doc.get('filename', 'Document')} ===\n{content}")
    
    return "\n\n".join(context_parts)

def _extract_sections_from_report(ad_report) -> Dict[str, str]:
    """
    Extract sections from ADReport for compatibility with existing frontend
    """
    sections = {}
    
    # Map ADReport fields to section IDs
    mapping = {
        "samenvatting": f"Vraagstelling: {', '.join(ad_report.samenvatting_vraagstelling[:2])}",
        "vraagstelling": "1. Vraagstelling",
        "ondernomen_activiteiten": "2. Ondernomen activiteiten",
        "voorgeschiedenis": "3.1 Voorgeschiedenis",
        "gegevens_werkgever": "3.2 Gegevens werkgever",
        "gegevens_werknemer": "3.3 Gegevens werknemer",
        "belastbaarheid": "3.4 Belastbaarheid van werknemer",
        "eigen_functie": "3.5 Eigen functie werknemer",
        "gesprek_werkgever": "3.6 Gesprek met de werkgever",
        "gesprek_werknemer": "3.7 Gesprek met werknemer",
        "geschiktheid_eigen_werk": "4.1 Geschiktheid voor eigen werk",
        "aanpassing_eigen_werk": "4.2 Aanpassing eigen werk",
        "geschiktheid_ander_werk": "4.3 Geschiktheid voor ander werk",
        "visie_duurzaamheid": "4.5 Visie op duurzaamheid",
        "trajectplan": "5. Trajectplan",
        "conclusie": "6. Conclusie",
        "vervolg": "7. Vervolg"
    }
    
    # Convert to section format
    for field, title in mapping.items():
        sections[field] = title
    
    return sections

def _convert_structured_to_sections(ad_report) -> Dict[str, str]:
    """
    Convert ADReport structured data to sections format compatible with existing frontend
    This avoids duplicate headers by generating clean content for each section
    """
    sections = {}
    
    # 1. Samenvatting
    samenvatting_content = "**Vraagstelling:**\n"
    for vraag in ad_report.samenvatting_vraagstelling:
        samenvatting_content += f"• {vraag}\n"
    samenvatting_content += "\n**Conclusie:**\n"
    for conclusie in ad_report.samenvatting_conclusie:
        samenvatting_content += f"• {conclusie}\n"
    sections["samenvatting"] = samenvatting_content
    
    # 2. Vraagstelling
    vraagstelling_content = ""
    for i, item in enumerate(ad_report.vraagstelling, 1):
        vraagstelling_content += f"• {item.vraag}\n"
    sections["vraagstelling"] = vraagstelling_content
    
    # 3. Ondernomen activiteiten
    activiteiten_content = ""
    for activiteit in ad_report.ondernomen_activiteiten:
        activiteiten_content += f"• {activiteit}\n"
    sections["ondernomen_activiteiten"] = activiteiten_content
    
    # 4. Voorgeschiedenis
    voorgeschiedenis_content = f"{ad_report.voorgeschiedenis}\n\n**Verzuimhistorie:**\n{ad_report.verzuimhistorie}"
    sections["voorgeschiedenis"] = voorgeschiedenis_content
    
    # 5. Gegevens werkgever
    werkgever = ad_report.opdrachtgever
    werkgever_content = f"""
| **Aspect** | **Informatie** |
|------------|----------------|
| Naam bedrijf | {werkgever.naam_bedrijf} |
| Contactpersoon | {werkgever.contactpersoon or 'Niet beschikbaar'} |
| Functie | {werkgever.functie_contactpersoon or 'Niet beschikbaar'} |
| Adres | {werkgever.adres or 'Niet beschikbaar'} |
| PC/Woonplaats | {werkgever.postcode or ''} {werkgever.woonplaats or 'Niet beschikbaar'} |
| Telefoonnummer | {werkgever.telefoonnummer or 'Niet beschikbaar'} |
| E-mail | {werkgever.email or 'Niet beschikbaar'} |
| Aard bedrijf | {werkgever.aard_bedrijf or 'Niet beschikbaar'} |
| Omvang bedrijf | {werkgever.omvang_bedrijf or 'Niet beschikbaar'} |
| Aantal werknemers | {werkgever.aantal_werknemers or 'Niet beschikbaar'} |
| Website | {werkgever.website or 'Niet beschikbaar'} |
"""
    sections["gegevens_werkgever"] = werkgever_content
    
    # 6. Gegevens werknemer
    werknemer = ad_report.werknemer
    werknemer_content = f"""
| **Aspect** | **Informatie** |
|------------|----------------|
| Naam | {werknemer.naam} |
| Geboortedatum | {werknemer.geboortedatum or 'Niet beschikbaar'} |
| Adres | {werknemer.adres or 'Niet beschikbaar'} |
| PC/Woonplaats | {werknemer.postcode or ''} {werknemer.woonplaats or 'Niet beschikbaar'} |
| Telefoonnummer | {werknemer.telefoonnummer or 'Niet beschikbaar'} |
| E-mail | {werknemer.email or 'Niet beschikbaar'} |

**Opleidingen:**
"""
    for opl in ad_report.opleidingen:
        werknemer_content += f"• {opl.naam} ({opl.richting or 'Onbekende richting'}) - {opl.jaar or 'Jaar onbekend'}\n"
    
    werknemer_content += "\n**Arbeidsverleden:**\n"
    for av in ad_report.arbeidsverleden_lijst:
        werknemer_content += f"• {av.periode}: {av.functie} bij {av.werkgever}\n"
    
    if ad_report.bekwaamheden:
        bek = ad_report.bekwaamheden
        werknemer_content += f"""
**Bekwaamheden:**
• Computervaardigheden: {bek.computervaardigheden or 'Niet beschikbaar'}
• Taalvaardigheid: {bek.taalvaardigheid or 'Niet beschikbaar'}
• Rijbewijs: {bek.rijbewijs or 'Niet beschikbaar'}
• Overige: {bek.overige or 'Niet beschikbaar'}
"""
    
    sections["gegevens_werknemer"] = werknemer_content
    
    # 7. Belastbaarheid
    bel = ad_report.belastbaarheid
    belastbaarheid_content = f"""
De belastbaarheid is op {bel.datum_beoordeling} door {bel.beoordelaar} beoordeeld.

**FML Beperkingen:**

| **Rubriek** | **Mate van beperking** | **Details** |
|-------------|-------------------------|-------------|
"""
    
    for rubriek in bel.fml_rubrieken:
        items_text = "; ".join([item.beschrijving for item in rubriek.items])
        belastbaarheid_content += f"| {rubriek.rubriek_naam} | {rubriek.mate_beperking.value} | {items_text} |\n"
    
    if bel.prognose:
        belastbaarheid_content += f"\n**Prognose:** {bel.prognose}"
        
    sections["belastbaarheid"] = belastbaarheid_content
    
    # 8. Eigen functie
    ef = ad_report.eigen_functie
    eigen_functie_content = f"""
| **Aspect** | **Details** |
|------------|-------------|
| Functietitel | {ef.naam_functie} |
| Arbeidspatroon | {ef.arbeidspatroon} |
| Contract | {ef.overeenkomst} |
| Aantal uren | {ef.aantal_uren} |
| Salaris | {ef.salaris or 'Niet beschikbaar'} |

**Functieomschrijving:**
{ef.functieomschrijving}

**Functiebelasting:**

| **Taak** | **Percentage** | **Belastende aspecten** |
|----------|----------------|-------------------------|
"""
    
    for fb in ad_report.functiebelasting:
        eigen_functie_content += f"| {fb.taak} | {fb.percentage} | {fb.belastende_aspecten} |\n"
    
    sections["eigen_functie"] = eigen_functie_content
    
    # 9. Geschiktheidsanalyse
    geschiktheid_content = "**Analyse geschiktheid eigen werk:**\n\n"
    geschiktheid_content += "| **Belastend aspect** | **Belastbaarheid werknemer** | **Conclusie** |\n"
    geschiktheid_content += "|---------------------|------------------------------|---------------|\n"
    
    for ga in ad_report.geschiktheid_eigen_werk:
        geschiktheid_content += f"| {ga.belastend_aspect} | {ga.belastbaarheid_werknemer} | {ga.conclusie} |\n"
    
    geschiktheid_content += f"\n**Conclusie eigen werk:** {ad_report.conclusie_eigen_werk}\n"
    geschiktheid_content += f"\n**Aanpassingen eigen werk:** {ad_report.aanpassing_eigen_werk}\n"
    geschiktheid_content += f"\n**Ander werk intern:** {ad_report.geschiktheid_ander_werk_intern}\n"
    geschiktheid_content += f"\n**Ander werk extern:** {ad_report.geschiktheid_ander_werk_extern}\n"
    
    sections["geschiktheid_analyse"] = geschiktheid_content
    
    # 10. Trajectplan
    trajectplan_content = "**Actiepunten:**\n\n"
    trajectplan_content += "| **Actie** | **Verantwoordelijke** | **Termijn** | **Spoor** |\n"
    trajectplan_content += "|-----------|----------------------|-------------|----------|\n"
    
    for tp in ad_report.trajectplan:
        trajectplan_content += f"| {tp.actie} | {tp.verantwoordelijke or 'Niet gespecificeerd'} | {tp.termijn or 'Niet gespecificeerd'} | {tp.spoor or '-'} |\n"
    
    sections["trajectplan"] = trajectplan_content
    
    # 11. Conclusie
    conclusie_content = "**Hoofdconclusies:**\n\n"
    for i, conclusie in enumerate(ad_report.conclusies, 1):
        conclusie_content += f"{i}. **{conclusie.conclusie}**\n"
        if conclusie.toelichting:
            conclusie_content += f"   {conclusie.toelichting}\n"
        conclusie_content += "\n"
    
    sections["conclusie"] = conclusie_content
    
    # 12. Vervolg
    vervolg_content = "**Vervolgstappen:**\n\n"
    for i, stap in enumerate(ad_report.vervolg, 1):
        vervolg_content += f"{i}. {stap}\n"
    
    sections["vervolg"] = vervolg_content
    
    return sections

def _convert_to_markdown(structured_data: Dict[str, Any]) -> str:
    """
    Convert structured data to markdown format
    """
    # Implementation would convert the structured data to markdown
    # For now, return a placeholder
    return "# Arbeidsdeskundig Rapport\n\nMarkdown conversion not yet implemented"