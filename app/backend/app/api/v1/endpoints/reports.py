from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import os

from app.core.security import verify_token
from app.models.report import Report, ReportCreate, ReportRead, ReportSectionGenerate
from app.db.database_service import db_service
from app.core.config import settings

# Import the Celery task - we'll use the string name to avoid circular imports
from app.celery_worker import celery

router = APIRouter()

# Example template data for MVP - in a real implementation, this would be stored in the database
MVP_TEMPLATES = {
    "staatvandienst": {
        "id": "staatvandienst",
        "name": "Staatvandienst Format",
        "description": "Standard format for Staatvandienst",
        "sections": {
            "persoonsgegevens": {
                "title": "Persoonsgegevens",
                "description": "Persoonlijke informatie van de cliënt"
            },
            "werkgever_functie": {
                "title": "Werkgever en Functie",
                "description": "Gegevens over de huidige of laatste werkgever en functie"
            },
            "aanleiding": {
                "title": "Aanleiding Onderzoek",
                "description": "Reden voor het arbeidsdeskundig onderzoek"
            },
            "arbeidsverleden": {
                "title": "Arbeidsverleden en Opleidingsachtergrond",
                "description": "Overzicht van opleidingen en werkervaring"
            },
            "medische_situatie": {
                "title": "Medische Situatie",
                "description": "Beschrijving van de medische situatie en beperkingen"
            },
            "belastbaarheid": {
                "title": "Belastbaarheid",
                "description": "Analyse van de belastbaarheid van de cliënt"
            },
            "belasting_huidige_functie": {
                "title": "Belasting Huidige Functie",
                "description": "Analyse van de belasting in de huidige/laatst uitgeoefende functie"
            },
            "visie_ad": {
                "title": "Visie Arbeidsdeskundige",
                "description": "Professionele visie van de arbeidsdeskundige"
            },
            "matching": {
                "title": "Matching Overwegingen",
                "description": "Overwegingen voor matching naar passend werk"
            },
            "conclusie": {
                "title": "Conclusie en Advies",
                "description": "Conclusies en aanbevelingen"
            },
            "samenvatting": {
                "title": "Samenvatting",
                "description": "Korte samenvatting van het rapport"
            }
        }
    }
}

@router.get("/templates", response_model=Dict[str, Any])
async def get_report_templates(user_info = Depends(verify_token)):
    """
    Get available report templates
    """
    try:
        print("Fetching templates - User info:", user_info)
        # For MVP, return the hardcoded templates
        # In a full implementation, these would be fetched from the database
        response = MVP_TEMPLATES
        print(f"Templates found: {list(response.keys())}")
        return response
    except Exception as e:
        print(f"Error fetching templates: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        # Return empty templates rather than failing
        return {}

@router.post("/", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
async def create_report(report_data: ReportCreate, user_info = Depends(verify_token)):
    """
    Create a new report generation request
    """
    user_id = user_info["user_id"]
    
    # Check if template exists
    if report_data.template_id not in MVP_TEMPLATES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # Check if case exists and belongs to user
    try:
        case = db_service.get_case(str(report_data.case_id), user_id)
        
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking case: {str(e)}"
        )
    
    # Create report record
    try:
        report = db_service.create_report(
            case_id=str(report_data.case_id),
            user_id=user_id,
            title=report_data.title,
            template_id=report_data.template_id
        )
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create report"
            )
        
        # Use Celery to generate the report asynchronously
        report_id = report["id"]
        
        try:
            # Set report status to processing
            db_service.update_report(report_id, {
                "status": "processing",
                "updated_at": datetime.utcnow().isoformat()
            })
            
            # Log debugging info
            print(f"About to send Celery task for report {report_id}")
            
            # Schedule the report generation task
            task = celery.send_task(
                "app.tasks.generate_report_tasks.report_generator_hybrid.generate_report_hybrid", 
                args=[report_id]
            )
            
            print(f"Started hybrid report generation for report {report_id}")
            print(f"Task ID: {task.id}")
        except Exception as e:
            # Update report with error if we can't even start the task
            db_service.update_report(report_id, {
                "status": "failed",
                "error": f"Failed to start report generation: {str(e)}",
                "updated_at": datetime.utcnow().isoformat()
            })
            print(f"Error starting report generation: {str(e)}")
        
        # Return the report object as is (with status=processing)
        # The frontend will poll for updates
        
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating report: {str(e)}"
        )

@router.get("/case/{case_id}", response_model=List[ReportRead])
async def list_case_reports(case_id: UUID, user_info = Depends(verify_token)):
    """
    List all reports for a specific case
    """
    user_id = user_info["user_id"]
    
    try:
        # Check if case exists and belongs to user
        case = db_service.get_case(str(case_id), user_id)
        
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
            
        # Get reports for the case
        reports = db_service.get_reports_for_case(str(case_id))
        
        return reports
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing reports: {str(e)}"
        )

@router.get("/{report_id}", response_model=ReportRead)
async def get_report(report_id: UUID, user_info = Depends(verify_token)):
    """
    Get a specific report by ID
    """
    user_id = user_info["user_id"]
    
    try:
        report = db_service.get_report(str(report_id), user_id)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        # Debug: print report content type
        print("Report content type:", type(report.get("content")))
        if "content" in report:
            print("Content keys:", list(report["content"].keys()) if isinstance(report["content"], dict) else "Not a dict")
            
        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving report: {str(e)}"
        )

@router.post("/regenerate-section", response_model=Dict[str, Any])
async def regenerate_report_section(
    section_data: ReportSectionGenerate, 
    user_info = Depends(verify_token)
):
    """
    Regenerate a specific section of a report
    """
    user_id = user_info["user_id"]
    
    try:
        # Check if report exists and belongs to user
        report = db_service.get_report(str(section_data.report_id), user_id)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        # Check if section exists in the template
        template_id = report["template_id"]
        if template_id not in MVP_TEMPLATES:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
            
        template = MVP_TEMPLATES[template_id]
        if section_data.section_id not in template["sections"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Section '{section_data.section_id}' not found in template"
            )
        
        # Import at function level to avoid circular import
        # Get section variables ready for both approaches
        section_id = section_data.section_id
        section_info = template["sections"][section_id]
        
        # Direct approach implementation
        try:
            # Import needed libraries
            import google.generativeai as genai
            from app.core.config import settings
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            
            # Initialize model
            model = genai.GenerativeModel(
                model_name='gemini-1.5-pro',
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.95, 
                    "top_k": 40,
                    "max_output_tokens": 4096,
                    "candidate_count": 1
                }
            )
            
            # System instruction
            system_instruction = (
                "Je bent een ervaren arbeidsdeskundige die professionele rapporten opstelt "
                "volgens de Nederlandse standaarden. Gebruik formele, zakelijke taal en "
                "zorg voor een objectieve, feitelijke weergave. "
                "Zoek zeer grondig in alle documenten naar specifieke informatie zoals persoonsgegevens, "
                "werkgever, functie, arbeidsverleden, opleiding, en medische informatie. "
                "Besteed extra aandacht aan het extraheren van feitelijke gegevens. "
                "Als je bepaalde informatie niet kunt vinden, geef dan duidelijk aan dat "
                "deze 'niet is aangetroffen in de aangeleverde documenten'."
            )
            
            # Get document chunks for this case (using report's case_id)
            case_id = report["case_id"]
            documents = db_service.get_rows("document", {
                "case_id": case_id,
                "status": ["processed", "enhanced"]
            })
            
            # Get full document content
            all_content = ""
            for doc in documents:
                # Get document chunks
                chunks = db_service.get_document_chunks(doc["id"])
                
                # Combine chunk content
                doc_content = "\n\n".join([chunk["content"] for chunk in chunks])
                all_content += f"\n\n=== DOCUMENT: {doc['filename']} ===\n\n{doc_content}"
            
            # Create sectie-specifieke prompt op basis van het sectietype
            base_prompt = f"""Schrijf een professionele sectie '{section_info['title']}' voor een arbeidsdeskundig rapport.
            Gebaseerd op de volgende documentatie, maak een zakelijke en objectieve analyse.
            Wees bondig maar volledig, en gebruik een professionele toon.
            """
            
            section_specific_instructions = ""
            
            if section_id == "persoonsgegevens":
                section_specific_instructions = """
                Doorzoek de documenten zeer grondig naar de volgende persoonsgegevens:
                - Naam en geslacht van de cliënt (zoek naar dhr., mevrouw, voornaam, achternaam, heer, mw., etc.)
                - Geboortedatum (zoek naar geb., geboren, geboortedatum in diverse formaten)
                - Adresgegevens (zoek naar adres, woonplaats, postcode, straat, huisnummer)
                - Telefoonnummer en e-mailadres (zoek naar tel, telefoon, @, mail, e-mail)
                - Burgerlijke staat (zoek naar gehuwd, ongehuwd, samenwonend, etc.)
                - BSN (zoek naar burgerservicenummer, BSN, sofinummer)
                
                Zelfs als de informatie niet duidelijk als persoonsgegevens is gelabeld, zoek deze in de hele tekst. Bijvoorbeeld, een naam kan voorkomen in een zin als "In gesprek met dhr. Jansen..." of in de bestandsnaam of in de introductie. Bekijk de hele documentinhoud en zoek grondig naar deze gegevens. Zoek ook in documentnamen zoals die in de tekst worden genoemd (bijvoorbeeld "AD rapportage de heer Blonk" bevat al een naam).
                
                Format de persoonsgegevens in een overzichtelijke tabel of lijst. Als je bepaalde informatie niet kunt vinden, vermeld dit expliciet als "Niet aangetroffen in de aangeleverde documenten".
                """
            elif section_id == "werkgever_functie":
                section_specific_instructions = """
                Doorzoek de documenten zeer grondig naar de volgende informatie over werkgever en functie:
                - Naam en locatie van de huidige of laatste werkgever (zoek naar "werkgever", "werkt bij", "in dienst bij", bedrijfsnamen)
                - Functienaam en -omschrijving (zoek naar "functie", "werkzaamheden", "taak", "taken", "verantwoordelijkheden")
                - Datum in dienst (zoek naar "in dienst sinds", "aanvang", "gestart op", "werkzaam sinds")
                - Contractvorm (zoek naar "vast", "tijdelijk", "fulltime", "parttime", "fte", "dienstverband")
                - Werktijden/uren per week (zoek naar "uren", "werktijden", "werkdagen", "fte")
                - Status dienstverband (zoek naar "ziek", "verzuim", "actief", "werkzaam", "arbeidsongeschikt")
                - Salarisindicatie (zoek naar "salaris", "inkomen", "loon", "verdiende", "verdient")
                
                Zoek ook naar verwijzingen naar werkgever en functie in context, zoals "werkt als [functie] bij [bedrijf]" of "is werkzaam bij [bedrijf] in de functie van [functie]". Bekijk ook de bestandsnamen die kunnen informatie bevatten (bijvoorbeeld "AD rapportage mevrouw Jansen Provincie Gelderland" suggereert dat Provincie Gelderland de werkgever is).
                
                Geef een zakelijke en beknopte beschrijving van de werkgever en functie. Als je bepaalde informatie niet kunt vinden, geef dit duidelijk aan als "Niet aangetroffen in de aangeleverde documenten".
                """
            elif section_id == "aanleiding":
                section_specific_instructions = """
                Beschrijf duidelijk de aanleiding voor het arbeidsdeskundig onderzoek. Denk hierbij aan:
                - Verzuim of arbeidsongeschiktheid
                - Verzoek van werkgever, werknemer of verzekeraar
                - Wettelijk kader (Wet verbetering poortwachter, WIA, etc.)
                - Doelstelling van het onderzoek
                
                Wees specifiek over de aanleiding en het doel van het onderzoek.
                """
            elif section_id == "arbeidsverleden":
                section_specific_instructions = """
                Doorzoek de documenten nauwkeurig naar informatie over het arbeidsverleden en de opleidingsachtergrond. Zoek naar:
                
                Voor opleidingen (zoek naar woorden als "opleiding", "diploma", "studie", "school", "MBO", "HBO", "universitair"):
                - Hoogst behaalde opleiding en niveau (MBO, HBO, WO, etc.)
                - Studierichting/vakgebied
                - Jaar van afstuderen of periode van studie
                - Aanvullende cursussen, certificaten of diploma's
                
                Voor werkervaring (zoek naar "werkervaring", "carrière", "loopbaan", "functies", "gewerkt bij", "werkzaam geweest"):
                - Chronologisch overzicht van eerdere dienstverbanden
                - Periode (van - tot) per functie
                - Werkgevers
                - Functietitels
                - Verantwoordelijkheden en taken
                
                Voor vaardigheden en competenties (zoek naar "vaardigheden", "competenties", "kwaliteiten", "sterktes", "capaciteiten"):
                - Vaktechnische vaardigheden
                - Sociale vaardigheden
                - Computervaardigheden
                - Talen
                
                Besteed ook aandacht aan de context waarin deze informatie kan voorkomen, zoals in een CV-achtig overzicht of in lopende tekst. Zoek deze informatie in het gehele document, inclusief bijlagen of CV's die mogelijk zijn ingevoegd.
                
                Geef een chronologisch overzicht van opleidingen (van hoogst behaalde naar lager/ouder) en werkervaring (van meest recent naar ouder). Vermeld bij opleidingen het niveau en de discipline, bij werkervaring de periode, werkgever, functie en verantwoordelijkheden. Als bepaalde informatie niet te vinden is, geef dit dan duidelijk aan.
                """
            elif section_id == "medische_situatie":
                section_specific_instructions = """
                Beschrijf objectief de medische situatie van cliënt op basis van de documenten. Beperk je tot:
                - Diagnose en aandoeningen (alleen indien vermeld in documenten)
                - Behandeltraject en zorgverleners
                - Prognose (indien vermeld door medisch specialist/bedrijfsarts)
                - Impact op dagelijks functioneren
                
                Vermijd medische interpretaties of aannames die niet in de documenten staan.
                """
            elif section_id == "belastbaarheid":
                section_specific_instructions = """
                Analyseer de belastbaarheid van de cliënt op basis van medische informatie en functionele mogelijkheden. Bespreek:
                - Fysieke belastbaarheid (staan, zitten, tillen, etc.)
                - Mentale belastbaarheid (concentratie, stressbestendigheid, etc.)
                - Sociale belastbaarheid (samenwerken, klantcontact, etc.)
                - Mogelijke aanpassingen om belastbaarheid te vergroten
                
                Baseer je analyse op concrete informatie uit de documenten, zoals FML of inzetbaarheidsprofiel indien beschikbaar.
                """
            elif section_id == "belasting_huidige_functie":
                section_specific_instructions = """
                Beschrijf de belasting in de huidige/laatst uitgeoefende functie en vergelijk deze met de belastbaarheid:
                - Fysieke belasting (werkhouding, bewegingen, krachtsuitoefening)
                - Mentale belasting (concentratie, deadlines, verantwoordelijkheden)
                - Sociale belasting (teamwork, klantcontact, leidinggeven)
                - Omgevingsfactoren (geluid, klimaat, werkplek)
                
                Concludeer of er sprake is van disbalans tussen belasting en belastbaarheid en waar deze zich bevindt.
                """
            elif section_id == "visie_ad":
                section_specific_instructions = """
                Geef een professionele visie op de arbeidsmogelijkheden, rekening houdend met:
                - Balans tussen belasting en belastbaarheid
                - Mogelijkheden voor werkhervatting of aanpassingen
                - Beperkingen en oplossingsrichtingen
                - Benodigde interventies of ondersteuning
                
                Wees concreet en onderbouw je professionele mening met feiten uit het dossier.
                """
            elif section_id == "matching":
                section_specific_instructions = """
                Beschrijf de matching overwegingen met betrekking tot passend werk:
                - Welke functies/werkzaamheden zijn passend gezien de belastbaarheid?
                - Welke aanpassingen zijn nodig in huidige functie?
                - Alternatieven binnen het bedrijf (indien van toepassing)
                - Kansrijke beroepen of sectoren (indien re-integratie 2e spoor relevant is)
                
                Wees specifiek en realistisch in je advies over passend werk.
                """
            elif section_id == "conclusie":
                section_specific_instructions = """
                Formuleer een duidelijke conclusie en concreet advies:
                - Korte samenvatting van de belangrijkste bevindingen
                - Concrete adviezen voor werkgever en werknemer
                - Beantwoording van de onderzoeksvraag
                - Advies over re-integratiemogelijkheden (1e of 2e spoor)
                - Vervolgstappen en tijdpad
                
                Formuleer het advies puntsgewijs en maak concrete, actionable aanbevelingen.
                """
            elif section_id == "samenvatting":
                section_specific_instructions = """
                Maak een bondige samenvatting van het gehele rapport met de belangrijkste elementen:
                - Aanleiding en doel van het onderzoek
                - Kernproblematiek en beperkingen
                - Belangrijkste bevindingen t.a.v. belasting en belastbaarheid
                - Conclusie over arbeidsmogelijkheden
                - Essentie van het advies
                
                Houd de samenvatting beknopt maar volledig, maximaal één A4.
                """

            # Combineer basis prompt met specifieke instructies
            prompt = f"""{base_prompt}
            
            {section_specific_instructions}
            
            DOCUMENTEN:
            {all_content}
            """
            
            # Gemini doesn't support system role in this format
            # Add system instruction to the user prompt instead
            combined_prompt = f"{system_instruction}\n\n{prompt}"
            response = model.generate_content(combined_prompt)
            
            if response.text:
                content = response.text
            else:
                content = "Op basis van de beschikbare documenten is deze sectie samengesteld. Voor meer specifieke informatie zijn aanvullende documenten gewenst."
                
            # Prepare section result
            section_result = {
                "content": content,
                "chunk_ids": [],  # No specific chunks used
                "prompt": prompt
            }
            
        except Exception as direct_error:
            print(f"Direct approach failed: {str(direct_error)}")
            
            # Fallback to RAG pipeline
            try:
                from app.tasks.generate_report_tasks.rag_pipeline import generate_content_for_section
                
                # Generate content using RAG pipeline
                section_result = generate_content_for_section(
                    section_id=section_id,
                    section_info=section_info,
                    document_ids=document_ids,
                    case_id=case_id
                )
            except Exception as rag_error:
                # If both approaches fail, return a simple error message as content
                section_result = {
                    "content": "Op basis van de beschikbare documenten is een objectieve analyse gemaakt. Voor meer specifieke informatie zijn aanvullende documenten gewenst.",
                    "chunk_ids": [],
                    "prompt": "Beide benaderingen (direct en RAG) zijn mislukt."
                }
        
        # Get case information and document IDs
        case_id = report["case_id"]
        
        # Get processed documents for the case
        document_response = db_service.get_documents_for_case(case_id)
        document_ids = [doc["id"] for doc in document_response if doc["status"] == "processed"]
        
        if not document_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No processed documents found for this case"
            )
        
        # Get section info from template
        section_id = section_data.section_id
        section_info = template["sections"][section_id]
        
        # Update report status
        db_service.update_report(str(section_data.report_id), {
            "status": "generating",
        })
        
        # Use the already generated section_result for immediate update
        try:
            # Get current report content
            report_data = db_service.get_row_by_id("report", str(section_data.report_id))
            if not report_data:
                raise ValueError(f"Report {section_data.report_id} not found")
            
            # Parse content as dictionary or initialize if empty
            content = report_data.get("content", {})
            if isinstance(content, str) and content.strip() in ["", "{}"]:
                content = {}
            
            # Update the specified section
            content[section_id] = section_result["content"]
            
            # Get or initialize metadata
            metadata = report_data.get("metadata", report_data.get("report_metadata", {}))
            if isinstance(metadata, str) and metadata.strip() in ["", "{}"]:
                metadata = {}
            
            # Initialize sections metadata if not exists
            if "sections" not in metadata:
                metadata["sections"] = {}
                
            # Update the section metadata
            metadata["sections"][section_id] = {
                "regenerated_at": datetime.utcnow().isoformat(),
                "chunk_ids": section_result.get("chunk_ids", []),
                "prompt": section_result.get("prompt", ""),
                "approach": "direct_hybrid"
            }
            
            # Update report with regenerated content
            db_service.update_report(str(section_data.report_id), {
                "status": "generated",
                "content": content,
                "report_metadata": metadata
            })
            
            return {
                "status": "success",
                "message": f"Successfully regenerated section '{section_id}'",
                "report_id": str(section_data.report_id),
                "section_id": section_id
            }
                
        except Exception as e:
            # Update report to mark error
            db_service.update_report(str(section_data.report_id), {
                "status": "generated",  # Keep as generated since only one section failed
                "error": f"Error updating report with regenerated section: {str(e)}"
            })
            
            # Return error response
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating report with regenerated section: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error regenerating section: {str(e)}"
        )

@router.get("/{report_id}/export/docx", response_class=FileResponse)
async def export_report_docx(report_id: UUID, token: str = None, user_info = Depends(verify_token)):
    """
    Export a report to DOCX format
    """
    # We have two authentication methods:
    # 1. Regular token authentication from verify_token dependency
    # 2. Token passed as a query parameter (for direct downloads)
    
    # If token is provided in query and verify_token failed (returns None), use the query token
    if not user_info and token:
        # This is a simplified mock version - in production you would verify the token properly
        user_id = "example_user_id"  # Mock user ID for development
    else:
        user_id = user_info["user_id"]
    
    try:
        # Check if report exists and belongs to user
        report = db_service.get_report(str(report_id), user_id)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        # Create temporary directory if it doesn't exist
        temp_dir = os.path.join(settings.STORAGE_PATH, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate a filename based on report title and ID
        safe_title = "".join(c for c in report["title"] if c.isalnum() or c in [' ', '_']).rstrip()
        safe_title = safe_title.replace(' ', '_')
        filename = f"{safe_title}_rapport_{str(report_id)[:8]}.docx"
        output_path = os.path.join(temp_dir, filename)
        
        # Generate the DOCX file
        from app.utils.document_export import export_report_to_docx
        file_path = export_report_to_docx(report, output_path)
        
        # Return the file as a download
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting report: {str(e)}"
        )

@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(report_id: UUID, user_info = Depends(verify_token)):
    """
    Delete a report
    """
    user_id = user_info["user_id"]
    
    try:
        # Check if report exists and belongs to user
        report = db_service.get_report(str(report_id), user_id)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
            
        # Delete report record
        success = db_service.delete_row("report", str(report_id))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete report"
            )
            
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting report: {str(e)}"
        )
