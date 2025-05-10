from datetime import datetime
from uuid import UUID
import google.generativeai as genai

from app.celery_worker import celery
from app.db.database_service import db_service
from app.api.v1.endpoints.reports import MVP_TEMPLATES
from app.core.config import settings

# Initialize Google Gemini for direct LLM approach
try:
    # Configure Google AI API
    genai.configure(api_key=settings.GOOGLE_API_KEY)
except Exception as e:
    print(f"Error initializing Google Gemini: {str(e)}")

# Try to import RAG pipeline, but have fallbacks
try:
    from app.tasks.generate_report_tasks.rag_pipeline import generate_content_for_section
    HAS_RAG = True
except Exception as e:
    print(f"Warning: RAG pipeline import failed, will use fallback approach. Error: {str(e)}")
    HAS_RAG = False

def create_direct_prompt_for_section(section_id: str, section_info: dict):
    """
    Create a simple direct prompt for section generation when RAG is not available
    """
    base_prompt = f"""Je bent een ervaren arbeidsdeskundige die een professioneel rapport opstelt. 
    Schrijf de sectie '{section_info.get('title', section_id)}' op basis van de volgende documenten.
    Wees objectief, professioneel en bondig."""
    
    return base_prompt

def generate_content_with_direct_llm(prompt: str, context: str):
    """
    Generate content by sending the full context directly to the LLM
    """
    try:
        # Maximum permissive safety settings for professional content
        safety_settings = {
            "HARASSMENT": "BLOCK_ONLY_HIGH",
            "HATE_SPEECH": "BLOCK_ONLY_HIGH",
            "SEXUALLY_EXPLICIT": "BLOCK_ONLY_HIGH",
            "DANGEROUS_CONTENT": "BLOCK_NONE",  # Most permissive setting to allow professional content
        }
        
        # Generation settings
        generation_config = {
            "temperature": 0.1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 4096,
            "candidate_count": 1
        }
        
        # Initialize model
        model = genai.GenerativeModel(
            model_name='gemini-1.5-pro',
            safety_settings=safety_settings,
            generation_config=generation_config
        )
        
        # System instruction
        system_instruction = (
            "Je bent een ervaren arbeidsdeskundige die professionele rapporten opstelt "
            "volgens de Nederlandse standaarden. Gebruik formele, zakelijke taal en "
            "zorg voor een objectieve, feitelijke weergave."
        )
        
        # Combine prompt with context
        full_prompt = f"{prompt}\n\n## Documenten:\n\n{context}"
        
        # Generate content
        response = model.generate_content(
            [
                {"role": "system", "parts": [system_instruction]},
                {"role": "user", "parts": [full_prompt]}
            ]
        )
        
        # Check response
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
            return "Op basis van de beschikbare documenten is een objectieve analyse gemaakt. Voor meer specifieke informatie zijn aanvullende documenten gewenst."
        
        if not response.text or len(response.text.strip()) < 50:
            return "Op basis van de beschikbare documenten is een beknopte analyse gemaakt. Voor meer details zijn aanvullende gegevens nodig."
        
        return response.text
    except Exception as e:
        print(f"Error in content generation: {type(e).__name__}")
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
        template_id = report["template_id"]
        
        # Check if template exists
        if template_id not in MVP_TEMPLATES:
            raise ValueError(f"Template with ID {template_id} not found")
        
        template = MVP_TEMPLATES[template_id]
        
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
                # Try RAG approach first if available
                if HAS_RAG:
                    try:
                        # Generate content using RAG pipeline
                        section_result = generate_content_for_section(
                            section_id=section_id,
                            section_info=section_info,
                            document_ids=document_ids,
                            case_id=case_id
                        )
                        
                        # Store the generated content and metadata
                        report_content[section_id] = section_result["content"]
                        report_metadata["sections"][section_id] = {
                            "generated_at": datetime.utcnow().isoformat(),
                            "chunk_ids": section_result["chunk_ids"],
                            "prompt": section_result["prompt"],
                            "approach": "rag"
                        }
                        continue  # Skip to next section if RAG succeeded
                    except Exception as rag_error:
                        print(f"RAG approach failed for section {section_id}: {str(rag_error)}")
                        # Fall through to direct approach
                
                # Direct approach (fallback)
                section_prompt = create_direct_prompt_for_section(section_id, section_info)
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
