"""
Optimized RAG Pipeline voor Arbeidsdeskundige AI
Enhanced retrieval met document type awareness en slimme chunking
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
import asyncio
from dataclasses import dataclass
from enum import Enum

from anthropic import Anthropic
from app.utils.smart_document_classifier import DocumentType, ProcessingStrategy
from app.utils.vector_store_improved import HybridVectorStore
from app.db.database_service import DatabaseService


class RetrievalStrategy(Enum):
    """RAG retrieval strategies"""
    SEMANTIC_SEARCH = "semantic"
    HYBRID_SEARCH = "hybrid"
    KEYWORD_SEARCH = "keyword"
    SECTION_AWARE = "section_aware"


@dataclass
class ChunkConfig:
    """Configuration voor intelligent chunking"""
    target_size: int
    max_size: int
    overlap: int
    importance_boost: float
    section_aware: bool


@dataclass
class RetrievalConfig:
    """Configuration voor retrieval strategy"""
    strategy: RetrievalStrategy
    top_k: int
    confidence_threshold: float
    diversity_threshold: float
    metadata_filters: Dict[str, Any]


class OptimizedRAGPipeline:
    """
    Geoptimaliseerde RAG pipeline met document type awareness
    """
    
    def __init__(self, db_service: Optional[DatabaseService] = None):
        self.db_service = db_service
        from app.core.config import settings
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.vector_store = HybridVectorStore() if db_service else None
        self.logger = logging.getLogger(__name__)
        
        # Document type specific configurations
        self.chunk_configs = self._get_chunk_configurations()
        self.retrieval_configs = self._get_retrieval_configurations()
        
        # Performance metrics
        self.metrics = {
            "chunks_processed": 0,
            "retrievals_performed": 0,
            "average_retrieval_time": 0.0,
            "cache_hits": 0
        }
        
        # Simple cache for repeated queries
        self._query_cache = {}
        self._cache_max_size = 100
    
    def _get_chunk_configurations(self) -> Dict[str, ChunkConfig]:
        """Document type specific chunking configurations"""
        return {
            DocumentType.MEDICAL_REPORT.value: ChunkConfig(
                target_size=1000,
                max_size=1500,
                overlap=200,
                importance_boost=1.5,
                section_aware=True
            ),
            DocumentType.ASSESSMENT_REPORT.value: ChunkConfig(
                target_size=1200,
                max_size=1800,
                overlap=250,
                importance_boost=1.8,
                section_aware=True
            ),
            DocumentType.LEGAL_DOCUMENT.value: ChunkConfig(
                target_size=800,
                max_size=1200,
                overlap=150,
                importance_boost=2.0,
                section_aware=True
            ),
            DocumentType.INSURANCE_DOCUMENT.value: ChunkConfig(
                target_size=600,
                max_size=1000,
                overlap=100,
                importance_boost=1.3,
                section_aware=False
            ),
            DocumentType.PERSONAL_STATEMENT.value: ChunkConfig(
                target_size=500,
                max_size=800,
                overlap=100,
                importance_boost=1.0,
                section_aware=False
            ),
            DocumentType.CORRESPONDENCE.value: ChunkConfig(
                target_size=400,
                max_size=600,
                overlap=50,
                importance_boost=0.8,
                section_aware=False
            ),
            "default": ChunkConfig(
                target_size=800,
                max_size=1200,
                overlap=150,
                importance_boost=1.0,
                section_aware=False
            )
        }
    
    def _get_retrieval_configurations(self) -> Dict[str, RetrievalConfig]:
        """Document type specific retrieval configurations"""
        return {
            DocumentType.MEDICAL_REPORT.value: RetrievalConfig(
                strategy=RetrievalStrategy.SECTION_AWARE,
                top_k=8,
                confidence_threshold=0.3,
                diversity_threshold=0.7,
                metadata_filters={"importance": "high"}
            ),
            DocumentType.ASSESSMENT_REPORT.value: RetrievalConfig(
                strategy=RetrievalStrategy.HYBRID_SEARCH,
                top_k=10,
                confidence_threshold=0.25,
                diversity_threshold=0.8,
                metadata_filters={"section_type": ["belastbaarheid", "advies", "conclusie"]}
            ),
            DocumentType.LEGAL_DOCUMENT.value: RetrievalConfig(
                strategy=RetrievalStrategy.SECTION_AWARE,
                top_k=6,
                confidence_threshold=0.4,
                diversity_threshold=0.6,
                metadata_filters={"importance": "high"}
            ),
            "default": RetrievalConfig(
                strategy=RetrievalStrategy.SEMANTIC_SEARCH,
                top_k=5,
                confidence_threshold=0.3,
                diversity_threshold=0.7,
                metadata_filters={}
            )
        }
    
    async def create_optimized_chunks(self, document_id: str, content: str, 
                                    doc_type: str) -> List[Dict[str, Any]]:
        """
        Maak geoptimaliseerde chunks op basis van document type
        """
        try:
            start_time = datetime.utcnow()
            
            # Get chunking configuration for document type
            config = self.chunk_configs.get(doc_type, self.chunk_configs["default"])
            
            self.logger.info(f"Creating optimized chunks for {doc_type} with config: {config}")
            
            if config.section_aware and doc_type in [
                DocumentType.MEDICAL_REPORT.value,
                DocumentType.ASSESSMENT_REPORT.value,
                DocumentType.LEGAL_DOCUMENT.value
            ]:
                chunks = await self._create_section_aware_chunks(content, doc_type, config)
            else:
                chunks = await self._create_semantic_chunks(content, doc_type, config)
            
            # Add metadata and optimization info
            optimized_chunks = []
            for i, chunk in enumerate(chunks):
                optimized_chunk = {
                    "document_id": document_id,
                    "chunk_index": i,
                    "content": chunk["content"],
                    "metadata": {
                        **chunk.get("metadata", {}),
                        "chunk_config": {
                            "target_size": config.target_size,
                            "actual_size": len(chunk["content"]),
                            "importance_boost": config.importance_boost,
                            "section_aware": config.section_aware
                        },
                        "optimization_timestamp": datetime.utcnow().isoformat()
                    }
                }
                optimized_chunks.append(optimized_chunk)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self.metrics["chunks_processed"] += len(optimized_chunks)
            
            self.logger.info(
                f"Created {len(optimized_chunks)} optimized chunks for {doc_type} "
                f"in {processing_time:.2f}s"
            )
            
            return optimized_chunks
            
        except Exception as e:
            self.logger.error(f"Error creating optimized chunks: {e}")
            raise
    
    async def _create_section_aware_chunks(self, content: str, doc_type: str, 
                                         config: ChunkConfig) -> List[Dict[str, Any]]:
        """Maak section-aware chunks voor gestructureerde documenten"""
        
        chunks = []
        
        if doc_type == DocumentType.MEDICAL_REPORT.value:
            chunks = await self._chunk_medical_sections(content, config)
        elif doc_type == DocumentType.ASSESSMENT_REPORT.value:
            chunks = await self._chunk_assessment_sections(content, config)
        elif doc_type == DocumentType.LEGAL_DOCUMENT.value:
            chunks = await self._chunk_legal_sections(content, config)
        
        # Fallback to semantic chunking if no sections found
        if not chunks:
            chunks = await self._create_semantic_chunks(content, doc_type, config)
        
        return chunks
    
    async def _chunk_medical_sections(self, content: str, config: ChunkConfig) -> List[Dict[str, Any]]:
        """Chunk medische rapporten op basis van medische secties"""
        
        import re
        
        # Enhanced medical section patterns
        section_patterns = {
            "patient_info": {
                "pattern": r"(pati[eë]nt|naam|geboortedatum|bsn)",
                "importance": "medium"
            },
            "anamnese": {
                "pattern": r"(anamnese|voorgeschiedenis|hetero.anamnese|klachten)",
                "importance": "high"
            },
            "onderzoek": {
                "pattern": r"(lichamelijk onderzoek|bevindingen|inspectie|palpatie)",
                "importance": "high"
            },
            "diagnose": {
                "pattern": r"(diagnose|conclusie|bevindingen|differential)",
                "importance": "critical"
            },
            "behandeling": {
                "pattern": r"(behandeling|therapie|medicatie|behandelplan)",
                "importance": "high"
            },
            "prognose": {
                "pattern": r"(prognose|verwachting|herstel|vooruitzicht)",
                "importance": "high"
            },
            "beperkingen": {
                "pattern": r"(beperkingen|limitaties|contra.indicaties)",
                "importance": "critical"
            }
        }
        
        chunks = []
        processed_positions = set()
        
        for section_name, section_info in section_patterns.items():
            pattern = section_info["pattern"]
            importance = section_info["importance"]
            
            # Find all matches for this section
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            
            for match in matches:
                start_pos = match.start()
                
                # Skip if this position was already processed
                if any(abs(start_pos - pos) < 100 for pos in processed_positions):
                    continue
                
                # Extract section content
                section_content = self._extract_section_content(
                    content, start_pos, config.target_size, config.max_size
                )
                
                if len(section_content.strip()) > 50:  # Minimum content length
                    importance_boost = config.importance_boost
                    if importance == "critical":
                        importance_boost *= 1.5
                    elif importance == "high":
                        importance_boost *= 1.2
                    
                    chunks.append({
                        "content": section_content,
                        "metadata": {
                            "section_type": section_name,
                            "document_type": "medical_report",
                            "chunk_type": "medical_section",
                            "importance": importance,
                            "importance_boost": importance_boost,
                            "section_start": start_pos
                        }
                    })
                    
                    processed_positions.add(start_pos)
        
        return chunks
    
    async def _chunk_assessment_sections(self, content: str, config: ChunkConfig) -> List[Dict[str, Any]]:
        """Chunk arbeidsdeskundige rapporten op basis van assessment secties"""
        
        import re
        
        section_patterns = {
            "persoonsgegevens": {
                "pattern": r"(naam|bsn|geboortedatum|adres)",
                "importance": "low"
            },
            "belastbaarheid": {
                "pattern": r"(belastbaarheid|belastbaar|capaciteit|fysiek|mentaal)",
                "importance": "critical"
            },
            "beperkingen": {
                "pattern": r"(beperkingen|limitaties|problemen|niet.*mogelijk)",
                "importance": "critical"
            },
            "mogelijkheden": {
                "pattern": r"(mogelijkheden|kansen|wel.*mogelijk|geschikt)",
                "importance": "high"
            },
            "werkhervatting": {
                "pattern": r"(werkhervatting|re.integratie|terugkeer|hervat)",
                "importance": "high"
            },
            "advies": {
                "pattern": r"(advies|aanbeveling|voorstel|suggestie)",
                "importance": "critical"
            },
            "conclusie": {
                "pattern": r"(conclusie|samenvatting|eindoordeel)",
                "importance": "critical"
            }
        }
        
        return await self._extract_sections_by_patterns(
            content, section_patterns, config, "assessment_report"
        )
    
    async def _chunk_legal_sections(self, content: str, config: ChunkConfig) -> List[Dict[str, Any]]:
        """Chunk juridische documenten op basis van juridische structuur"""
        
        import re
        
        section_patterns = {
            "partijen": {
                "pattern": r"(tussen|eiser|verweerder|partijen)",
                "importance": "medium"
            },
            "feiten": {
                "pattern": r"(feiten|feitelijke.*omstandigheden|gebeurde)",
                "importance": "high"
            },
            "overwegingen": {
                "pattern": r"(overwegingen|beoordeling|analyse|rechtbank.*overweegt)",
                "importance": "critical"
            },
            "conclusie": {
                "pattern": r"(conclusie|uitspraak|beslissing|vonnis)",
                "importance": "critical"
            },
            "rechtsgevolgen": {
                "pattern": r"(rechtsgevolgen|gevolgen|consequenties|veroordeelt)",
                "importance": "high"
            },
            "artikelen": {
                "pattern": r"(artikel.*\d+|wet|wetboek|bw|sr)",
                "importance": "high"
            }
        }
        
        return await self._extract_sections_by_patterns(
            content, section_patterns, config, "legal_document"
        )
    
    async def _extract_sections_by_patterns(self, content: str, section_patterns: Dict[str, Dict],
                                          config: ChunkConfig, doc_type: str) -> List[Dict[str, Any]]:
        """Generic method voor pattern-based section extraction"""
        
        import re
        
        chunks = []
        processed_positions = set()
        
        for section_name, section_info in section_patterns.items():
            pattern = section_info["pattern"]
            importance = section_info["importance"]
            
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            
            for match in matches:
                start_pos = match.start()
                
                # Skip overlapping sections
                if any(abs(start_pos - pos) < 200 for pos in processed_positions):
                    continue
                
                section_content = self._extract_section_content(
                    content, start_pos, config.target_size, config.max_size
                )
                
                if len(section_content.strip()) > 100:
                    importance_boost = config.importance_boost
                    if importance == "critical":
                        importance_boost *= 1.8
                    elif importance == "high":
                        importance_boost *= 1.4
                    
                    chunks.append({
                        "content": section_content,
                        "metadata": {
                            "section_type": section_name,
                            "document_type": doc_type,
                            "chunk_type": "pattern_section",
                            "importance": importance,
                            "importance_boost": importance_boost,
                            "section_start": start_pos
                        }
                    })
                    
                    processed_positions.add(start_pos)
        
        return chunks
    
    def _extract_section_content(self, content: str, start_pos: int, 
                                target_size: int, max_size: int) -> str:
        """Extract section content with intelligent boundaries"""
        
        # Start extracting from a bit before the match for context
        extract_start = max(0, start_pos - 100)
        
        # Try to find natural boundary (paragraph end) near target size
        target_end = start_pos + target_size
        max_end = start_pos + max_size
        
        # Look for paragraph boundaries near target size
        search_text = content[extract_start:max_end]
        paragraphs = search_text.split('\n\n')
        
        extracted_content = ""
        current_length = 0
        
        for paragraph in paragraphs:
            if current_length + len(paragraph) > target_size and extracted_content:
                break
            extracted_content += paragraph + "\n\n"
            current_length += len(paragraph)
            
            if current_length >= target_size:
                break
        
        return extracted_content.strip()
    
    async def _create_semantic_chunks(self, content: str, doc_type: str, 
                                     config: ChunkConfig) -> List[Dict[str, Any]]:
        """Fallback semantic chunking voor ongestructureerde content"""
        
        # Intelligent paragraph-based chunking
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        chunks = []
        
        current_chunk = ""
        current_size = 0
        chunk_index = 0
        
        for paragraph in paragraphs:
            # Check if adding this paragraph would exceed max size
            if current_size + len(paragraph) > config.max_size and current_chunk:
                # Save current chunk
                chunks.append({
                    "content": current_chunk.strip(),
                    "metadata": {
                        "document_type": doc_type,
                        "chunk_type": "semantic_paragraph",
                        "importance": "medium",
                        "importance_boost": config.importance_boost,
                        "chunk_index": chunk_index
                    }
                })
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk, config.overlap)
                current_chunk = overlap_text + "\n\n" + paragraph
                current_size = len(current_chunk)
                chunk_index += 1
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
                current_size += len(paragraph)
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                "content": current_chunk.strip(),
                "metadata": {
                    "document_type": doc_type,
                    "chunk_type": "semantic_paragraph",
                    "importance": "medium",
                    "importance_boost": config.importance_boost,
                    "chunk_index": chunk_index
                }
            })
        
        return chunks
    
    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """Get overlap text from end of chunk for context continuity"""
        if len(text) <= overlap_size:
            return text
        
        # Try to find sentence boundary for natural overlap
        overlap_text = text[-overlap_size:]
        
        # Find last sentence end
        sentence_ends = ['.', '!', '?', '\n']
        last_sentence_end = -1
        
        for i, char in enumerate(overlap_text):
            if char in sentence_ends:
                last_sentence_end = i
        
        if last_sentence_end > overlap_size // 2:  # If we found a good break point
            return overlap_text[last_sentence_end + 1:].strip()
        
        return overlap_text
    
    async def enhanced_retrieval(self, query: str, case_id: str, 
                               document_types: Optional[List[str]] = None,
                               max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Enhanced retrieval met document type awareness en caching
        """
        try:
            start_time = datetime.utcnow()
            
            # Check cache first
            cache_key = self._generate_cache_key(query, case_id, document_types, max_results)
            if cache_key in self._query_cache:
                self.metrics["cache_hits"] += 1
                self.logger.debug(f"Cache hit for query: {query[:50]}...")
                return self._query_cache[cache_key]
            
            # Determine optimal retrieval strategy
            strategy = await self._determine_retrieval_strategy(query, document_types)
            
            self.logger.info(f"Using {strategy} retrieval strategy for query: {query[:50]}...")
            
            if strategy == RetrievalStrategy.SECTION_AWARE:
                results = await self._section_aware_retrieval(query, case_id, document_types, max_results)
            elif strategy == RetrievalStrategy.HYBRID_SEARCH:
                results = await self._hybrid_retrieval(query, case_id, document_types, max_results)
            elif strategy == RetrievalStrategy.KEYWORD_SEARCH:
                results = await self._keyword_retrieval(query, case_id, document_types, max_results)
            else:  # SEMANTIC_SEARCH
                results = await self._semantic_retrieval(query, case_id, document_types, max_results)
            
            # Apply post-processing optimizations
            optimized_results = await self._post_process_results(results, query, document_types)
            
            # Cache results
            self._update_cache(cache_key, optimized_results)
            
            # Update metrics
            retrieval_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_retrieval_metrics(retrieval_time)
            
            self.logger.info(
                f"Retrieved {len(optimized_results)} results using {strategy} "
                f"in {retrieval_time:.2f}s"
            )
            
            return optimized_results
            
        except Exception as e:
            self.logger.error(f"Error in enhanced retrieval: {e}")
            raise
    
    async def _determine_retrieval_strategy(self, query: str, 
                                          document_types: Optional[List[str]]) -> RetrievalStrategy:
        """Bepaal optimale retrieval strategy op basis van query en document types"""
        
        # Analyze query characteristics
        query_lower = query.lower()
        
        # Check for section-specific queries
        section_keywords = [
            "diagnose", "behandeling", "prognose", "anamnese",  # Medical
            "belastbaarheid", "beperkingen", "advies", "conclusie",  # Assessment
            "feiten", "overwegingen", "uitspraak", "artikel"  # Legal
        ]
        
        has_section_keywords = any(keyword in query_lower for keyword in section_keywords)
        
        # Check for specific document type focus
        priority_doc_types = [
            DocumentType.MEDICAL_REPORT.value,
            DocumentType.ASSESSMENT_REPORT.value,
            DocumentType.LEGAL_DOCUMENT.value
        ]
        
        has_priority_types = document_types and any(
            doc_type in priority_doc_types for doc_type in document_types
        )
        
        # Strategy selection logic
        if has_section_keywords and has_priority_types:
            return RetrievalStrategy.SECTION_AWARE
        elif len(query_lower.split()) > 8:  # Complex queries
            return RetrievalStrategy.HYBRID_SEARCH
        elif any(keyword in query_lower for keyword in ["zoek", "vind", "specifiek"]):
            return RetrievalStrategy.KEYWORD_SEARCH
        else:
            return RetrievalStrategy.SEMANTIC_SEARCH
    
    async def _section_aware_retrieval(self, query: str, case_id: str,
                                     document_types: Optional[List[str]], 
                                     max_results: int) -> List[Dict[str, Any]]:
        """Section-aware retrieval voor gestructureerde documenten"""
        
        # Extract section hints from query
        section_hints = self._extract_section_hints(query)
        
        # Build metadata filters
        metadata_filters = {"case_id": case_id}
        if document_types:
            metadata_filters["document_type"] = document_types
        if section_hints:
            metadata_filters["section_type"] = section_hints
        
        # Perform enhanced search with section boosting
        results = await self.vector_store.similarity_search_with_metadata(
            query=query,
            k=max_results * 2,  # Get more results for filtering
            metadata_filter=metadata_filters
        )
        
        # Boost results from relevant sections
        boosted_results = []
        for result in results:
            boost_factor = 1.0
            metadata = result.get("metadata", {})
            
            # Section relevance boost
            if section_hints and metadata.get("section_type") in section_hints:
                boost_factor *= 1.5
            
            # Importance boost
            importance = metadata.get("importance", "medium")
            if importance == "critical":
                boost_factor *= 1.8
            elif importance == "high":
                boost_factor *= 1.4
            
            # Document type priority boost
            if document_types and metadata.get("document_type") in document_types:
                boost_factor *= 1.2
            
            # Apply boost to similarity score
            original_score = result.get("similarity_score", 0.0)
            boosted_score = original_score * boost_factor
            
            boosted_results.append({
                **result,
                "similarity_score": boosted_score,
                "boost_factor": boost_factor,
                "retrieval_strategy": "section_aware"
            })
        
        # Sort by boosted score and return top results
        boosted_results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return boosted_results[:max_results]
    
    async def _hybrid_retrieval(self, query: str, case_id: str,
                              document_types: Optional[List[str]], 
                              max_results: int) -> List[Dict[str, Any]]:
        """Hybrid retrieval combinatie van semantic en keyword search"""
        
        # Perform both semantic and keyword searches
        semantic_task = self._semantic_retrieval(query, case_id, document_types, max_results // 2)
        keyword_task = self._keyword_retrieval(query, case_id, document_types, max_results // 2)
        
        semantic_results, keyword_results = await asyncio.gather(semantic_task, keyword_task)
        
        # Merge and deduplicate results
        all_results = {}
        
        # Add semantic results with weight
        for result in semantic_results:
            chunk_id = result.get("chunk_id")
            if chunk_id:
                all_results[chunk_id] = {
                    **result,
                    "semantic_score": result.get("similarity_score", 0.0),
                    "keyword_score": 0.0,
                    "retrieval_strategy": "hybrid"
                }
        
        # Add keyword results with weight
        for result in keyword_results:
            chunk_id = result.get("chunk_id")
            if chunk_id in all_results:
                # Combine scores
                all_results[chunk_id]["keyword_score"] = result.get("similarity_score", 0.0)
                hybrid_score = (
                    all_results[chunk_id]["semantic_score"] * 0.7 +
                    all_results[chunk_id]["keyword_score"] * 0.3
                )
                all_results[chunk_id]["similarity_score"] = hybrid_score
            else:
                all_results[chunk_id] = {
                    **result,
                    "semantic_score": 0.0,
                    "keyword_score": result.get("similarity_score", 0.0),
                    "similarity_score": result.get("similarity_score", 0.0) * 0.8,  # Lower weight for keyword-only
                    "retrieval_strategy": "hybrid"
                }
        
        # Sort by combined score
        combined_results = list(all_results.values())
        combined_results.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return combined_results[:max_results]
    
    async def _semantic_retrieval(self, query: str, case_id: str,
                                document_types: Optional[List[str]], 
                                max_results: int) -> List[Dict[str, Any]]:
        """Standard semantic similarity search"""
        
        metadata_filters = {"case_id": case_id}
        if document_types:
            metadata_filters["document_type"] = document_types
        
        results = await self.vector_store.similarity_search_with_metadata(
            query=query,
            k=max_results,
            metadata_filter=metadata_filters
        )
        
        for result in results:
            result["retrieval_strategy"] = "semantic"
        
        return results
    
    async def _keyword_retrieval(self, query: str, case_id: str,
                               document_types: Optional[List[str]], 
                               max_results: int) -> List[Dict[str, Any]]:
        """Keyword-based retrieval using database full-text search"""
        
        # Extract keywords from query
        keywords = self._extract_keywords(query)
        
        # Perform database keyword search
        search_criteria = {
            "case_id": case_id,
            "keywords": keywords
        }
        if document_types:
            search_criteria["document_types"] = document_types
        
        # Use database service for keyword search
        documents = self.db_service.search_documents_by_metadata(search_criteria)
        
        # Convert to result format
        results = []
        for doc in documents[:max_results]:
            results.append({
                "chunk_id": doc.get("id"),
                "content": doc.get("content", "")[:500] + "...",  # Preview
                "metadata": doc.get("metadata", {}),
                "similarity_score": 0.7,  # Fixed score for keyword matches
                "retrieval_strategy": "keyword"
            })
        
        return results
    
    def _extract_section_hints(self, query: str) -> List[str]:
        """Extract section hints from query"""
        query_lower = query.lower()
        
        section_mapping = {
            "medical": {
                "diagnose": ["diagnose", "bevinding", "conclusie"],
                "anamnese": ["anamnese", "voorgeschiedenis", "klacht"],
                "onderzoek": ["onderzoek", "bevinding", "test"],
                "behandeling": ["behandeling", "therapie", "medicatie"],
                "prognose": ["prognose", "verwachting", "herstel"],
                "beperkingen": ["beperking", "limitatie", "contra"]
            },
            "assessment": {
                "belastbaarheid": ["belastbaarheid", "capaciteit", "mogelijk"],
                "beperkingen": ["beperking", "limitatie", "niet"],
                "mogelijkheden": ["mogelijkheid", "kans", "wel"],
                "advies": ["advies", "aanbeveling", "voorstel"],
                "conclusie": ["conclusie", "samenvatting", "eindoordeel"]
            },
            "legal": {
                "feiten": ["feit", "gebeurtenis", "situatie"],
                "overwegingen": ["overweging", "beoordeling", "analyse"],
                "conclusie": ["conclusie", "uitspraak", "vonnis"],
                "rechtsgevolgen": ["gevolg", "consequentie", "effect"]
            }
        }
        
        hints = []
        for domain, sections in section_mapping.items():
            for section, keywords in sections.items():
                if any(keyword in query_lower for keyword in keywords):
                    hints.append(section)
        
        return hints
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords from query"""
        import re
        
        # Remove common Dutch stop words
        stop_words = {
            "de", "het", "een", "en", "van", "te", "dat", "die", "in", "op", 
            "voor", "met", "als", "zijn", "er", "aan", "bij", "om", "heeft"
        }
        
        # Extract words (letters only, minimum 3 characters)
        words = re.findall(r'\b[a-zA-ZáéíóúàèìòùâêîôûäëïöüÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÄËÏÖÜ]{3,}\b', query.lower())
        
        # Filter out stop words
        keywords = [word for word in words if word not in stop_words]
        
        return keywords[:10]  # Limit to top 10 keywords
    
    async def _post_process_results(self, results: List[Dict[str, Any]], 
                                  query: str, document_types: Optional[List[str]]) -> List[Dict[str, Any]]:
        """Post-process results voor diversity en relevance"""
        
        if not results:
            return results
        
        # Apply diversity filtering to avoid too many similar chunks
        diverse_results = self._apply_diversity_filter(results)
        
        # Add relevance scoring
        scored_results = await self._add_relevance_scores(diverse_results, query)
        
        # Final sorting by relevance
        scored_results.sort(key=lambda x: x.get("final_relevance_score", 0), reverse=True)
        
        return scored_results
    
    def _apply_diversity_filter(self, results: List[Dict[str, Any]], 
                               similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Filter out overly similar results"""
        
        if len(results) <= 3:
            return results
        
        diverse_results = [results[0]]  # Always include top result
        
        for result in results[1:]:
            # Check similarity with already selected results
            is_diverse = True
            current_content = result.get("content", "")
            
            for selected in diverse_results:
                selected_content = selected.get("content", "")
                
                # Simple similarity check based on common words
                if self._calculate_content_similarity(current_content, selected_content) > similarity_threshold:
                    is_diverse = False
                    break
            
            if is_diverse:
                diverse_results.append(result)
        
        return diverse_results
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Simple content similarity calculation"""
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    async def _add_relevance_scores(self, results: List[Dict[str, Any]], 
                                  query: str) -> List[Dict[str, Any]]:
        """Add final relevance scores combining multiple factors"""
        
        query_keywords = set(self._extract_keywords(query))
        
        for result in results:
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            similarity_score = result.get("similarity_score", 0.0)
            
            # Keyword overlap score
            content_keywords = set(self._extract_keywords(content))
            keyword_overlap = len(query_keywords.intersection(content_keywords)) / max(len(query_keywords), 1)
            
            # Metadata boost
            metadata_boost = 1.0
            if metadata.get("importance") == "critical":
                metadata_boost = 1.5
            elif metadata.get("importance") == "high":
                metadata_boost = 1.2
            
            # Length penalty for very short chunks
            length_factor = min(len(content) / 200, 1.0)  # Penalize chunks shorter than 200 chars
            
            # Calculate final score
            final_score = (
                similarity_score * 0.6 +
                keyword_overlap * 0.3 +
                length_factor * 0.1
            ) * metadata_boost
            
            result["final_relevance_score"] = final_score
            result["keyword_overlap"] = keyword_overlap
            result["metadata_boost"] = metadata_boost
        
        return results
    
    def _generate_cache_key(self, query: str, case_id: str, 
                           document_types: Optional[List[str]], max_results: int) -> str:
        """Generate cache key for query"""
        import hashlib
        
        cache_data = f"{query}|{case_id}|{document_types}|{max_results}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def _update_cache(self, cache_key: str, results: List[Dict[str, Any]]) -> None:
        """Update query cache with LRU eviction"""
        
        # Remove oldest entries if cache is full
        if len(self._query_cache) >= self._cache_max_size:
            # Simple FIFO eviction (could be improved to LRU)
            oldest_key = next(iter(self._query_cache))
            del self._query_cache[oldest_key]
        
        self._query_cache[cache_key] = results
    
    def _update_retrieval_metrics(self, retrieval_time: float) -> None:
        """Update retrieval performance metrics"""
        self.metrics["retrievals_performed"] += 1
        
        # Update moving average of retrieval time
        total_retrievals = self.metrics["retrievals_performed"]
        current_avg = self.metrics["average_retrieval_time"]
        
        self.metrics["average_retrieval_time"] = (
            (current_avg * (total_retrievals - 1) + retrieval_time) / total_retrievals
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get pipeline performance metrics"""
        return {
            **self.metrics,
            "cache_size": len(self._query_cache),
            "cache_hit_rate": (
                self.metrics["cache_hits"] / max(self.metrics["retrievals_performed"], 1)
            )
        }
    
    def clear_cache(self) -> None:
        """Clear query cache"""
        self._query_cache.clear()
        self.logger.info("Query cache cleared")