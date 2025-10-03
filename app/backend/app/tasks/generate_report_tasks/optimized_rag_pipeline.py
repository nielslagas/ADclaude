"""
Optimized RAG pipeline for generating report sections with performance enhancements
Integrates caching, batching, and intelligent resource management for faster report generation
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.core.config import settings
from app.db.database_service import get_database_service
from app.utils.llm_provider import create_llm_instance
from app.utils.quality_controller import AutomaticQualityController
from app.utils.rag_performance_optimizer import get_performance_optimizer
from app.utils.context_aware_prompts import ContextAwarePromptGenerator

# Configure logging
logger = logging.getLogger(__name__)

# Initialize services
db_service = get_database_service()


@dataclass
class OptimizedChunkResult:
    """Optimized chunk retrieval result"""
    chunks: List[Dict[str, Any]]
    total_chunks: int
    cache_hit: bool
    retrieval_time: float
    strategy_counts: Dict[str, int]


class OptimizedRAGPipeline:
    """
    Performance-optimized RAG pipeline with intelligent caching,
    batching, and resource management for faster report generation
    """
    
    def __init__(self):
        self.performance_optimizer = get_performance_optimizer()
        self.quality_controller = AutomaticQualityController()
        self.context_prompt_generator = ContextAwarePromptGenerator()
        
        # Query mappings with performance optimization hints
        self.query_mapping = self._initialize_query_mappings()
        
        # Performance tracking
        self.pipeline_metrics = {
            'sections_generated': 0,
            'total_generation_time': 0.0,
            'cache_hits': 0,
            'quality_improvements': 0
        }
        
        logger.info("Optimized RAG Pipeline initialized")
    
    def _initialize_query_mappings(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize query mappings with performance metadata"""
        return {
            "samenvatting": [
                {
                    "query": "persoonsgegevens leeftijd geslacht opleiding werkervaring cliënt",
                    "weight": 1.2,
                    "cache_priority": "high"
                },
                {
                    "query": "voorgeschiedenis arbeidssituatie ziektegeschiedenis werknemer",
                    "weight": 1.5,
                    "cache_priority": "high"
                },
                {
                    "query": "aanleiding arbeidsdeskundig onderzoek arbeidsmogelijkheden re-integratie",
                    "weight": 1.8,
                    "cache_priority": "critical"
                },
                {
                    "query": "huidige situatie functioneren dagbesteding activiteiten belastbaarheid",
                    "weight": 1.3,
                    "cache_priority": "high"
                }
            ],
            "belastbaarheid": [
                {
                    "query": "fysieke belastbaarheid tillen dragen duwen trekken bukken zitten staan lopen",
                    "weight": 2.0,
                    "cache_priority": "critical"
                },
                {
                    "query": "mentale belastbaarheid concentratie aandacht geheugen informatieverwerking stress",
                    "weight": 2.0,
                    "cache_priority": "critical"
                },
                {
                    "query": "sociale belastbaarheid communicatie samenwerking instructies feedback",
                    "weight": 1.5,
                    "cache_priority": "high"
                },
                {
                    "query": "functionele mogelijkheden inzetbaarheid belastingpunten FML Functionele Mogelijkhedenlijst",
                    "weight": 1.8,
                    "cache_priority": "high"
                }
            ],
            "visie_ad": [
                {
                    "query": "visie arbeidsdeskundige professionele beoordeling analyse",
                    "weight": 2.0,
                    "cache_priority": "critical"
                },
                {
                    "query": "conclusies adviezen aanbevelingen arbeidsdeskundig rapport",
                    "weight": 1.8,
                    "cache_priority": "critical"
                },
                {
                    "query": "arbeidsmogelijkheden werkhervatting re-integratie toekomstperspectief participatie",
                    "weight": 1.7,
                    "cache_priority": "high"
                },
                {
                    "query": "beperkingen mogelijkheden impact arbeidsvermogen functioneren",
                    "weight": 1.6,
                    "cache_priority": "high"
                }
            ],
            "matching": [
                {
                    "query": "passend werk geschikte functies beroepen arbeidsmarkt",
                    "weight": 1.8,
                    "cache_priority": "high"
                },
                {
                    "query": "werkaanpassingen hulpmiddelen ondersteuning ergonomische maatregelen",
                    "weight": 1.5,
                    "cache_priority": "medium"
                },
                {
                    "query": "randvoorwaarden werkhervatting arbeidsparticipatie re-integratie",
                    "weight": 1.6,
                    "cache_priority": "high"
                },
                {
                    "query": "functie-eisen arbeidsmogelijkheden belasting geschikt werk",
                    "weight": 1.4,
                    "cache_priority": "medium"
                }
            ]
        }
    
    async def get_relevant_chunks_optimized(self, section_id: str, 
                                          document_ids: List[str], 
                                          case_id: str, 
                                          limit: int = 15) -> OptimizedChunkResult:
        """
        Optimized version of chunk retrieval with caching and performance tracking
        """
        start_time = time.time()
        
        try:
            # Get query mappings for this section
            section_queries = self.query_mapping.get(section_id, [])
            
            if not section_queries:
                # Fallback for unknown sections
                section_queries = [
                    {
                        "query": f"informatie over {section_id} arbeidsdeskundig onderzoek",
                        "weight": 1.0,
                        "cache_priority": "low"
                    }
                ]
            
            # Add universal search terms for small document sets
            if len(document_ids) <= 2:
                section_queries.append({
                    "query": "belangrijke informatie arbeidsdeskundig rapport",
                    "weight": 0.8,
                    "cache_priority": "medium"
                })
            
            # Calculate optimal limit distribution
            hybrid_limit = min(30, limit * 3)
            queries_per_query = max(1, hybrid_limit // len(section_queries))
            
            # Execute searches with performance optimization
            all_results = []
            strategy_counts = {}
            cache_hit = False
            
            # Process queries with prioritization
            high_priority_queries = [q for q in section_queries if q.get("cache_priority") == "critical"]
            other_queries = [q for q in section_queries if q.get("cache_priority") != "critical"]
            
            # Process high-priority queries first
            for query_info in high_priority_queries + other_queries:
                query_text = query_info["query"]
                query_weight = query_info.get("weight", 1.0)
                
                logger.info(f"Running optimized search for query: {query_text[:50]}...")
                
                # Use performance optimizer for search
                search_results = await self.performance_optimizer.optimized_hybrid_search(
                    query=query_text,
                    case_id=case_id,
                    document_ids=document_ids,
                    limit=queries_per_query
                )
                
                # Check if this was a cache hit
                if "cache_hit" in search_results.get("metadata", {}):
                    cache_hit = True
                    self.pipeline_metrics['cache_hits'] += 1
                
                # Process results
                if search_results.get("success", False):
                    for result in search_results.get("results", []):
                        result_dict = {
                            "id": result.get("chunk_id", ""),
                            "document_id": result.get("document_id", ""),
                            "content": result.get("content", ""),
                            "metadata": result.get("metadata", {}),
                            "similarity": result.get("similarity", 0.0),
                            "strategy": result.get("strategy", "unknown"),
                            "query": query_text,
                            "query_weight": query_weight
                        }
                        all_results.append(result_dict)
                        
                        # Track strategy usage
                        strategy = result.get("strategy", "unknown")
                        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            
            # Remove duplicates with performance consideration
            unique_results = self._deduplicate_results_optimized(all_results)
            
            # Apply intelligent ranking
            ranked_results = self._rank_results_optimized(unique_results, section_id)
            
            # Limit to requested number
            final_results = ranked_results[:limit]
            
            retrieval_time = time.time() - start_time
            
            logger.info(
                f"Retrieved {len(final_results)} chunks for {section_id} "
                f"in {retrieval_time:.2f}s (cache_hit: {cache_hit})"
            )
            
            return OptimizedChunkResult(
                chunks=final_results,
                total_chunks=len(all_results),
                cache_hit=cache_hit,
                retrieval_time=retrieval_time,
                strategy_counts=strategy_counts
            )
            
        except Exception as e:
            logger.error(f"Error in optimized chunk retrieval: {str(e)}")
            raise ValueError(f"Error retrieving chunks: {str(e)}")
    
    def _deduplicate_results_optimized(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimized deduplication with performance consideration"""
        seen_ids = set()
        unique_results = []
        
        # Sort by similarity first to keep the best duplicates
        sorted_results = sorted(results, key=lambda x: x.get("similarity", 0), reverse=True)
        
        for result in sorted_results:
            result_id = result.get("id", "")
            if result_id and result_id not in seen_ids:
                seen_ids.add(result_id)
                unique_results.append(result)
        
        return unique_results
    
    def _rank_results_optimized(self, results: List[Dict[str, Any]], 
                              section_id: str) -> List[Dict[str, Any]]:
        """Optimized ranking considering multiple factors"""
        for result in results:
            base_similarity = result.get("similarity", 0.0)
            query_weight = result.get("query_weight", 1.0)
            
            # Apply strategy-specific boosts
            strategy_boost = {
                "direct_llm": 1.2,
                "hybrid": 1.1,
                "full_rag": 1.0,
                "unknown": 0.9
            }.get(result.get("strategy", "unknown"), 1.0)
            
            # Apply section-specific content boosts
            content = result.get("content", "").lower()
            content_boost = self._calculate_content_boost(content, section_id)
            
            # Calculate final score
            final_score = base_similarity * query_weight * strategy_boost * content_boost
            result["final_score"] = final_score
        
        # Sort by final score
        return sorted(results, key=lambda x: x.get("final_score", 0), reverse=True)
    
    def _calculate_content_boost(self, content: str, section_id: str) -> float:
        """Calculate content relevance boost based on section-specific keywords"""
        boost_keywords = {
            "samenvatting": ["samenvatting", "overzicht", "kernpunten", "hoofdzaken"],
            "belastbaarheid": ["belastbaar", "capaciteit", "mogelijkheden", "beperkingen"],
            "visie_ad": ["visie", "oordeel", "advies", "aanbeveling", "conclusie"],
            "matching": ["passend", "geschikt", "werk", "functie", "beroep"]
        }
        
        keywords = boost_keywords.get(section_id, [])
        boost = 1.0
        
        for keyword in keywords:
            if keyword in content:
                boost += 0.1
        
        return min(boost, 1.5)  # Cap boost at 1.5x
    
    async def create_prompt_for_section_optimized(self, section_id: str, 
                                                section_info: Dict, 
                                                chunks: List[Dict], 
                                                user_profile: Optional[Dict] = None) -> str:
        """
        Create optimized prompt using context-aware prompt generation
        """
        try:
            # Use context-aware prompt generator for better results
            optimized_prompt = await self.context_prompt_generator.generate_section_prompt(
                section_id=section_id,
                section_info=section_info,
                chunks=chunks,
                user_profile=user_profile,
                optimization_level="high"
            )
            
            return optimized_prompt
            
        except Exception as e:
            logger.warning(f"Context-aware prompt generation failed, using fallback: {e}")
            
            # Fallback to original prompt creation
            return self._create_prompt_fallback(section_id, section_info, chunks, user_profile)
    
    def _create_prompt_fallback(self, section_id: str, section_info: Dict, 
                              chunks: List[Dict], user_profile: Optional[Dict] = None) -> str:
        """Fallback prompt creation method"""
        # Organize chunks efficiently
        chunks_by_doc = {}
        for chunk in chunks:
            doc_id = chunk.get('document_id', 'unknown')
            if doc_id not in chunks_by_doc:
                chunks_by_doc[doc_id] = []
            chunks_by_doc[doc_id].append(chunk)
        
        # Sort chunks by final score if available
        for doc_id in chunks_by_doc:
            chunks_by_doc[doc_id] = sorted(
                chunks_by_doc[doc_id], 
                key=lambda x: x.get('final_score', x.get('similarity', 0)), 
                reverse=True
            )
        
        # Format context more efficiently
        formatted_chunks = []
        for doc_id, doc_chunks in chunks_by_doc.items():
            # Get document name
            doc_name = "Document"
            if doc_chunks and 'metadata' in doc_chunks[0]:
                doc_name = doc_chunks[0]['metadata'].get('document_name', f"Document {doc_id[:8]}")
            
            # Format only top chunks per document to save token space
            for i, chunk in enumerate(doc_chunks[:3]):  # Limit to top 3 per document
                chunk_header = f"{doc_name} (Fragment {i+1})"
                if 'metadata' in chunk and 'page' in chunk['metadata']:
                    chunk_header += f" | Pagina: {chunk['metadata']['page']}"
                
                formatted_chunks.append(f"{chunk_header}\n\n{chunk['content']}")
        
        context = "\n\n" + "="*50 + "\n\n".join(formatted_chunks) + "\n\n" + "="*50 + "\n\n"
        
        # Create section-specific prompts with optimization
        prompt_templates = {
            "samenvatting": f"""Schrijf een professionele samenvatting voor een arbeidsdeskundig rapport (200-250 woorden).

Structuur: 3-4 alinea's met:
- Persoonsgegevens en onderzoeksaanleiding
- Huidige werk- en gezondheidssituatie  
- Belangrijkste bevindingen
- Kernconclusive

Stijl: Formeel, objectief, feitelijk. Gebruik alleen informatie uit onderstaande documenten.

{context}

BELANGRIJK: Begin met één H1 section header (# Samenvatting) gevolgd door de content.""",

            "belastbaarheid": f"""Analyseer de belastbaarheid van de cliënt op basis van onderstaande documenten.

Behandel per categorie:
- **Fysiek**: Tillen, dragen, staan, zitten, lopen (wees specifiek: kg, uren)
- **Mentaal**: Concentratie, stress, complexiteit, tempo
- **Sociaal**: Samenwerking, klantcontact, communicatie
- **Beperkingen**: Tijdelijk/permanent, medische restricties

{context}

BELANGRIJK: Begin met één H1 section header (# Analyse Belastbaarheid) gevolgd door de analyse content.""",

            "visie_ad": f"""Formuleer je professionele arbeidsdeskundige visie (400-500 woorden).

Structuur:
1. **Beoordeling arbeidsmogelijkheden**: Integratie medische/persoonlijke factoren
2. **Belasting vs belastbaarheid**: Concrete analyse discrepantie
3. **Aanbevelingen**: Specifieke verbetervoorstellen arbeidssituatie
4. **Perspectief**: Werkhervatting of alternatieven

{context}

BELANGRIJK: Begin met één H1 section header (# Arbeidsdeskundige Visie) gevolgd door de visie content.""",

            "matching": f"""Formuleer concrete matchingcriteria voor passend werk.

Categorieën met (E)ssentieel of (W)enselijk per criterium:
- **Fysieke werkomgeving**: Toegankelijkheid, hulpmiddelen, werkplek
- **Taakinhoud**: Functie-eisen, complexiteit, verantwoordelijkheden  
- **Werktijden**: Intensiteit, flexibiliteit, pauzes
- **Sociale omgeving**: Teamwerk, klantcontact, begeleiding

{context}

BELANGRIJK: Begin met één H1 section header (# Matching en Aanbevelingen) gevolgd door de criteria content."""
        }
        
        base_prompt = prompt_templates.get(section_id, f"""Schrijf sectie '{section_info['title']}' voor arbeidsdeskundig rapport.

{context}

BELANGRIJK: Begin met één H1 section header (# {section_info['title']}) gevolgd door de sectie content.""")
        
        # Add user profile if available
        if user_profile:
            profile_section = self._format_user_profile(user_profile)
            base_prompt += profile_section
        
        return base_prompt
    
    def _format_user_profile(self, user_profile: Dict) -> str:
        """Format user profile information efficiently"""
        profile_lines = []
        
        # Add key profile information
        if user_profile.get("first_name") and user_profile.get("last_name"):
            name = f"{user_profile.get('first_name')} {user_profile.get('last_name')}"
            profile_lines.append(f"Naam: {name}")
        
        if user_profile.get("job_title"):
            profile_lines.append(f"Functie: {user_profile.get('job_title')}")
        
        if user_profile.get("company_name"):
            profile_lines.append(f"Organisatie: {user_profile.get('company_name')}")
        
        if profile_lines:
            return f"\n\n## Arbeidsdeskundige Informatie\n\n" + "\n".join(profile_lines)
        
        return ""
    
    async def generate_content_with_llm_optimized(self, prompt: str, 
                                                section_id: str = None) -> str:
        """
        Optimized LLM content generation with caching and error handling
        """
        try:
            # Create optimized LLM instance
            model = create_llm_instance(
                temperature=0.1,
                max_tokens=4096,
                dangerous_content_level="BLOCK_NONE"
            )
            
            # Professional system instruction
            system_instruction = (
                "Je bent een professionele arbeidsdeskundige die objectieve rapporten maakt. "
                "Schrijf in een zakelijke stijl gebaseerd op feitelijke informatie. "
                "Focus op praktische bruikbaarheid en duidelijkheid."
            )
            
            # Generate content with performance tracking
            start_time = time.time()
            
            response = model.generate_content([
                {"role": "system", "parts": [system_instruction]},
                {"role": "user", "parts": [prompt]}
            ])
            
            generation_time = time.time() - start_time
            
            # Validate response
            if not response.text or len(response.text.strip()) < 50:
                raise ValueError("Generated content too short")
            
            logger.info(f"Generated content for {section_id} in {generation_time:.2f}s")
            return response.text
            
        except Exception as e:
            logger.error(f"Error in optimized content generation: {e}")
            
            # Return section-specific fallback content
            return self._get_fallback_content(section_id)
    
    def _get_fallback_content(self, section_id: str) -> str:
        """Get fallback content for specific sections"""
        fallback_content = {
            "samenvatting": """# Samenvatting

Op basis van de beschikbare documenten is een objectieve analyse uitgevoerd van de arbeidsdeskundige situatie. De gegevens bevatten relevante informatie over de huidige omstandigheden en mogelijkheden voor de toekomst.""",

            "belastbaarheid": """# Analyse Belastbaarheid

De beschikbare informatie geeft inzicht in de huidige mogelijkheden en aandachtspunten. Er zijn verschillende factoren die van invloed zijn op de belastbaarheid in werkcontexten. Met passende ondersteuning zijn er mogelijkheden voor arbeidsparticipatie.""",

            "visie_ad": """# Arbeidsdeskundige Visie

Vanuit professioneel perspectief zijn er kansen voor werkhervatting met inachtneming van de geïdentificeerde factoren. Een gefaseerde benadering met adequate ondersteuning biedt perspectief voor duurzame arbeidsparticipatie.""",

            "matching": """# Matching en Aanbevelingen

Voor passend werk zijn specifieke randvoorwaarden van belang. De werkplek dient toegankelijk te zijn en aangepast aan de individuele mogelijkheden. Begeleiding en ondersteuning zijn essentiële factoren voor succesvol functioneren."""
        }
        
        return fallback_content.get(section_id, "# Sectie\n\nInformatie wordt verzameld en verwerkt.")
    
    async def generate_content_for_section_optimized(self, section_id: str, 
                                                   section_info: Dict, 
                                                   document_ids: List[str], 
                                                   case_id: str, 
                                                   user_profile: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Complete optimized RAG pipeline for generating content for a specific report section
        """
        start_time = time.time()
        
        try:
            # Get relevant chunks with optimization
            chunk_result = await self.get_relevant_chunks_optimized(
                section_id, document_ids, case_id
            )
            
            if not chunk_result.chunks:
                return {
                    "content": "Onvoldoende relevante gegevens beschikbaar voor deze sectie.",
                    "chunk_ids": [],
                    "prompt": "",
                    "error": "no_relevant_chunks",
                    "performance_metrics": {
                        "generation_time": time.time() - start_time,
                        "cache_hit": False,
                        "optimization_used": True
                    }
                }
            
            # Create optimized prompt
            prompt = await self.create_prompt_for_section_optimized(
                section_id, section_info, chunk_result.chunks, user_profile
            )
            
            # Generate content with optimization
            content = await self.generate_content_with_llm_optimized(prompt, section_id)
            
            # Apply quality control if enabled
            quality_improved = False
            try:
                quality_result = self.quality_controller.assess_content_quality(
                    content=content,
                    section_type=section_id,
                    original_prompt=prompt,
                    source_chunks=[chunk["content"] for chunk in chunk_result.chunks]
                )
                
                if quality_result.overall_score < 0.6:
                    improved_content = self.quality_controller.improve_content(
                        content=content,
                        quality_report=quality_result,
                        section_type=section_id
                    )
                    
                    if improved_content and len(improved_content.strip()) > len(content.strip()) * 0.5:
                        content = improved_content
                        quality_improved = True
                        self.pipeline_metrics['quality_improvements'] += 1
                        
            except Exception as qc_error:
                logger.warning(f"Quality control failed for {section_id}: {qc_error}")
            
            # Update metrics
            generation_time = time.time() - start_time
            self.pipeline_metrics['sections_generated'] += 1
            self.pipeline_metrics['total_generation_time'] += generation_time
            
            return {
                "content": content,
                "chunk_ids": [chunk["id"] for chunk in chunk_result.chunks],
                "prompt": prompt,
                "chunk_stats": {
                    "strategy_counts": chunk_result.strategy_counts,
                    "total_chunks": len(chunk_result.chunks),
                    "retrieval_time": chunk_result.retrieval_time
                },
                "performance_metrics": {
                    "generation_time": generation_time,
                    "cache_hit": chunk_result.cache_hit,
                    "quality_improved": quality_improved,
                    "optimization_used": True
                }
            }
            
        except Exception as e:
            error_time = time.time() - start_time
            logger.error(f"Error in optimized section generation for {section_id}: {e}")
            
            # Return fallback content
            fallback_content = self._get_fallback_content(section_id)
            
            return {
                "content": fallback_content,
                "chunk_ids": [],
                "prompt": "",
                "error": f"Generation failed: {str(e)}",
                "performance_metrics": {
                    "generation_time": error_time,
                    "cache_hit": False,
                    "optimization_used": True,
                    "fallback_used": True
                }
            }
    
    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get comprehensive pipeline performance metrics"""
        optimizer_stats = self.performance_optimizer.get_performance_stats()
        
        return {
            "pipeline_metrics": self.pipeline_metrics,
            "performance_optimizer": optimizer_stats,
            "cache_effectiveness": {
                "hit_rate": self.pipeline_metrics['cache_hits'] / max(self.pipeline_metrics['sections_generated'], 1),
                "quality_improvement_rate": self.pipeline_metrics['quality_improvements'] / max(self.pipeline_metrics['sections_generated'], 1)
            },
            "average_generation_time": self.pipeline_metrics['total_generation_time'] / max(self.pipeline_metrics['sections_generated'], 1)
        }
    
    async def warm_up_pipeline(self):
        """Warm up the pipeline for optimal performance"""
        logger.info("Warming up optimized RAG pipeline...")
        
        # Warm up performance optimizer
        await self.performance_optimizer.warm_up_cache()
        
        # Pre-generate common embeddings
        common_queries = []
        for section_queries in self.query_mapping.values():
            for query_info in section_queries:
                if query_info.get("cache_priority") in ["critical", "high"]:
                    common_queries.append(query_info["query"])
        
        for query in common_queries[:10]:  # Limit to prevent overload
            try:
                await self.performance_optimizer.optimized_embedding_generation(query)
            except Exception as e:
                logger.warning(f"Failed to warm up query '{query[:30]}...': {e}")
        
        logger.info("Pipeline warm-up completed")


# Singleton instance
_optimized_pipeline = None


def get_optimized_rag_pipeline() -> OptimizedRAGPipeline:
    """Get the singleton optimized RAG pipeline instance"""
    global _optimized_pipeline
    if _optimized_pipeline is None:
        _optimized_pipeline = OptimizedRAGPipeline()
    return _optimized_pipeline


# Compatibility function for existing code
async def generate_content_for_section(section_id: str, section_info: Dict, 
                                     document_ids: List[str], case_id: str, 
                                     user_profile: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Compatibility wrapper for existing code to use optimized pipeline
    """
    pipeline = get_optimized_rag_pipeline()
    return await pipeline.generate_content_for_section_optimized(
        section_id, section_info, document_ids, case_id, user_profile
    )