from datetime import datetime
from uuid import UUID
import asyncio

from app.celery_worker import celery
from app.db.database_service import get_database_service
from app.api.v1.endpoints.reports import MVP_TEMPLATES
from app.core.config import settings
from app.utils.llm_provider import create_llm_instance, get_safety_settings, get_generation_config

# Initialize database service
db_service = get_database_service()

# Try to import RAG pipeline, but have fallbacks
try:
    from app.tasks.generate_report_tasks.rag_pipeline import generate_content_for_section
    HAS_RAG = True
except Exception as e:
    print(f"Warning: RAG pipeline import failed, will use fallback approach. Error: {str(e)}")
    HAS_RAG = False

# Helper to run async code in sync context for Celery compatibility
def run_async(coroutine):
    """Run an async coroutine in a synchronous context."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()

def create_direct_prompt_for_section(section_id: str, section_info: dict, user_profile=None):
    """
    Create a simple direct prompt for section generation when RAG is not available
    """
    base_prompt = f"""Je bent een ervaren arbeidsdeskundige die een professioneel rapport opstelt.
    Schrijf de sectie '{section_info.get('title', section_id)}' op basis van de volgende documenten.
    Wees objectief, professioneel en bondig."""

    # Add profile information if available
    if user_profile:
        profile_prompt = "Gebruik onderstaande informatie voor je referentie als arbeidsdeskundige:\n"

        # Add name and title
        if user_profile.get("first_name") and user_profile.get("last_name"):
            name = f"{user_profile.get('first_name')} {user_profile.get('last_name')}"
            profile_prompt += f"Naam: {name}\n"
        elif user_profile.get("display_name"):
            profile_prompt += f"Naam: {user_profile.get('display_name')}\n"

        # Add job title
        if user_profile.get("job_title"):
            profile_prompt += f"Functie: {user_profile.get('job_title')}\n"

        # Add certification and registration
        if user_profile.get("certification"):
            profile_prompt += f"Certificering: {user_profile.get('certification')}\n"
        if user_profile.get("registration_number"):
            profile_prompt += f"Registratienummer: {user_profile.get('registration_number')}\n"

        # Add company information
        if user_profile.get("company_name"):
            profile_prompt += f"Bedrijf: {user_profile.get('company_name')}\n"

            # Add company address if available
            address_parts = []
            if user_profile.get("company_address"):
                address_parts.append(user_profile.get("company_address"))
            if user_profile.get("company_postal_code") and user_profile.get("company_city"):
                address_parts.append(f"{user_profile.get('company_postal_code')} {user_profile.get('company_city')}")
            elif user_profile.get("company_city"):
                address_parts.append(user_profile.get("company_city"))
            if user_profile.get("company_country"):
                address_parts.append(user_profile.get("company_country"))

            if address_parts:
                profile_prompt += f"Adres: {', '.join(address_parts)}\n"

            # Add contact information
            contact_parts = []
            if user_profile.get("company_phone"):
                contact_parts.append(f"Tel: {user_profile.get('company_phone')}")
            if user_profile.get("company_email"):
                contact_parts.append(f"Email: {user_profile.get('company_email')}")
            if user_profile.get("company_website"):
                contact_parts.append(f"Website: {user_profile.get('company_website')}")

            if contact_parts:
                profile_prompt += f"Contact: {' | '.join(contact_parts)}\n"

        # Add specializations
        if user_profile.get("specializations") and isinstance(user_profile.get("specializations"), list):
            profile_prompt += f"Specialisaties: {', '.join(user_profile.get('specializations'))}\n"

        base_prompt = base_prompt + "\n\n" + profile_prompt

    return base_prompt

def generate_content_with_direct_llm(prompt: str, context: str):
    """
    Generate content by sending the full context directly to the configured LLM provider
    """
    try:
        # Create LLM instance using the provider abstraction
        model = create_llm_instance(
            temperature=0.1,
            max_tokens=4096,
            dangerous_content_level="BLOCK_NONE"
        )
        
        # System instruction
        system_instruction = (
            "Je bent een ervaren arbeidsdeskundige die professionele rapporten opstelt "
            "volgens de Nederlandse standaarden. Gebruik formele, zakelijke taal en "
            "zorg voor een objectieve, feitelijke weergave."
        )
        
        # Combine prompt with context
        full_prompt = f"{prompt}\n\n## Documenten:\n\n{context}"
        
        # Generate content using the standardized interface
        response = model.generate_content(
            [
                {"role": "system", "parts": [system_instruction]},
                {"role": "user", "parts": [full_prompt]}
            ]
        )
        
        # Check response
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback and hasattr(response.prompt_feedback, 'block_reason') and response.prompt_feedback.block_reason:
            return "Op basis van de beschikbare documenten is een objectieve analyse gemaakt. Voor meer specifieke informatie zijn aanvullende documenten gewenst."
        
        if not response.text or len(response.text.strip()) < 50:
            return "Op basis van de beschikbare documenten is een beknopte analyse gemaakt. Voor meer details zijn aanvullende gegevens nodig."
        
        return response.text
    except Exception as e:
        print(f"Error in content generation: {type(e).__name__}: {str(e)}")
        print(f"Full error details: {repr(e)}")
        return "Op basis van de beschikbare documenten is een objectieve analyse gemaakt. Voor meer specifieke informatie is aanvullende documentatie gewenst."

@celery.task
def generate_report_mvp(report_id: str):
    """
    Generate a report based on document chunks using RAG or direct approach:
    1. Get report info and case documents
    2. For each section in the template, try:
       a. RAG approach if available: Get relevant chunks from pgvector & generate with LLM
       b. Direct approach if RAG fails: Send all text directly to LLM
    3. Update report with generated content
    """
    try:
        # Get report info from database
        report = db_service.get_row_by_id("report", report_id)

        if not report:
            raise ValueError(f"Report with ID {report_id} not found")

        case_id = report["case_id"]
        user_id = report["user_id"]
        template_id = report["template_id"]

        # Check if template exists
        if template_id not in MVP_TEMPLATES:
            raise ValueError(f"Template with ID {template_id} not found")

        template = MVP_TEMPLATES[template_id]

        # Get user profile for including in report
        user_profile = db_service.get_user_profile(user_id)

        # Get list of processed documents for this case
        documents = db_service.get_rows("document", {
            "case_id": case_id,
            "status": "processed"
        })

        document_ids = [doc["id"] for doc in documents]

        if not document_ids:
            raise ValueError(f"No processed documents found for case {case_id}")

        # Initialize content dictionary for the report
        report_content = {}
        report_metadata = {
            "generation_started": datetime.utcnow().isoformat(),
            "document_ids": document_ids,
            "user_profile": user_profile,
            "sections": {}
        }
        
        # Get full document texts for direct approach
        full_documents = []
        for doc_id in document_ids:
            # Get document info
            document = db_service.get_row_by_id("document", doc_id)
            if not document:
                continue
                
            # Get document chunks
            chunks = db_service.get_document_chunks(doc_id)
            if not chunks:
                continue
                
            # Combine chunk content
            content = "\n\n".join([chunk["content"] for chunk in chunks])
            
            # Add to document info
            document["content"] = content
            full_documents.append(document)
        
        # Combined text from all documents
        combined_text = "\n\n=== DOCUMENT SEPARATOR ===\n\n".join(
            [f"{doc.get('filename', 'Unnamed')}:\n{doc.get('content', '')}" for doc in full_documents]
        )
        
        # Generate content for each section in the template
        for section_id, section_info in template["sections"].items():
            try:
                # Try hybrid RAG approach first if available
                if HAS_RAG:
                    try:
                        # Generate content using RAG pipeline (run async in sync context)
                        section_result = run_async(generate_content_for_section(
                            section_id=section_id,
                            section_info=section_info,
                            document_ids=document_ids,
                            case_id=case_id
                        ))

                        # Store the generated content and metadata
                        report_content[section_id] = section_result["content"]

                        # Extract strategy statistics if available
                        strategy_stats = {}
                        if "chunk_stats" in section_result:
                            strategy_stats = section_result["chunk_stats"]

                        report_metadata["sections"][section_id] = {
                            "generated_at": datetime.utcnow().isoformat(),
                            "chunk_ids": section_result["chunk_ids"],
                            "prompt": section_result["prompt"],
                            "approach": "hybrid_rag",
                            "strategy_stats": strategy_stats
                        }
                        continue  # Skip to next section if RAG succeeded
                    except Exception as rag_error:
                        print(f"Hybrid RAG approach failed for section {section_id}: {str(rag_error)}")
                        # Fall through to direct approach
                
                # Direct approach (fallback)
                section_prompt = create_direct_prompt_for_section(section_id, section_info, user_profile)
                content = generate_content_with_direct_llm(section_prompt, combined_text)
                
                # Store the generated content and metadata
                report_content[section_id] = content
                report_metadata["sections"][section_id] = {
                    "generated_at": datetime.utcnow().isoformat(),
                    "chunk_ids": [],  # No specific chunks used
                    "prompt": section_prompt,
                    "approach": "direct"
                }
            except Exception as section_error:
                # If both approaches fail, store error message
                # Generic error message without exposing dangerous_content
                error_msg = f"Generatie heeft onvoldoende specifieke informatie beschikbaar voor sectie {section_info.get('title', section_id)}"
                report_content[section_id] = error_msg
                report_metadata["sections"][section_id] = {
                    "generated_at": datetime.utcnow().isoformat(),
                    "error": "Content generation failed",  # Generic error message
                    "approach": "failed"
                }
        
        # Complete the metadata
        report_metadata["generation_completed"] = datetime.utcnow().isoformat()
        
        # Update report with generated content
        db_service.update_report(report_id, {
            "status": "generated",
            "content": report_content,
            "report_metadata": report_metadata,  # Use report_metadata field name
            "updated_at": datetime.utcnow().isoformat()
        })
            
        return {
            "status": "success", 
            "report_id": report_id, 
            "sections": list(report_content.keys())
        }
    
    except Exception as e:
        # Update report status to failed
        db_service.update_report(report_id, {
            "status": "failed",
            "error": "Rapportgeneratie kon niet worden voltooid",  # Generic error message
            "updated_at": datetime.utcnow().isoformat()
        })
        
        # Log the error for debugging
        print(f"Error generating report {report_id}: {str(e)}")
        
        # Re-raise the exception to mark the Celery task as failed
        raise
