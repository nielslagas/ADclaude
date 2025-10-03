"""
Custom RAG Performance Metrics for AI-Arbeidsdeskundige
Advanced metrics for retrieval accuracy, generation quality, and pipeline optimization
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import json
import statistics
from collections import defaultdict, deque
import numpy as np

from app.utils.rag_monitoring import metrics_collector, ComponentType, MetricType
from app.utils.smart_document_classifier import DocumentType, ProcessingStrategy
from app.utils.context_aware_prompts import ReportSection


class RetrievalAccuracyMetric(Enum):
    """Types of retrieval accuracy measurements"""
    PRECISION_AT_K = "precision_at_k"
    RECALL_AT_K = "recall_at_k"
    MEAN_RECIPROCAL_RANK = "mrr"
    NORMALIZED_DCG = "ndcg"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    CONTEXT_RELEVANCE = "context_relevance"


class GenerationQualityMetric(Enum):
    """Types of generation quality measurements"""
    FACTUAL_ACCURACY = "factual_accuracy"
    COMPLETENESS = "completeness"
    COHERENCE = "coherence"
    RELEVANCE = "relevance"
    STYLE_CONSISTENCY = "style_consistency"
    TECHNICAL_ACCURACY = "technical_accuracy"
    LEGAL_COMPLIANCE = "legal_compliance"


@dataclass
class RetrievalMetrics:
    """Retrieval performance metrics"""
    query_id: str
    timestamp: datetime
    document_type: DocumentType
    query_text: str
    retrieved_chunks: List[str]
    relevant_chunks: List[str]  # Ground truth
    precision_at_k: float
    recall_at_k: float
    mrr_score: float
    ndcg_score: float
    avg_similarity_score: float
    retrieval_time: float
    chunk_count: int
    metadata: Dict[str, Any]


@dataclass
class GenerationMetrics:
    """Generation quality metrics"""
    generation_id: str
    timestamp: datetime
    report_section: ReportSection
    input_context: str
    generated_text: str
    reference_text: Optional[str]  # For comparison
    factual_accuracy: float
    completeness: float
    coherence: float
    relevance: float
    style_consistency: float
    technical_accuracy: float
    legal_compliance: float
    generation_time: float
    token_count: int
    metadata: Dict[str, Any]


@dataclass
class PipelinePerformanceMetrics:
    """End-to-end pipeline performance"""
    pipeline_id: str
    timestamp: datetime
    document_id: str
    document_type: DocumentType
    processing_strategy: ProcessingStrategy
    retrieval_metrics: RetrievalMetrics
    generation_metrics: List[GenerationMetrics]  # One per section
    overall_quality_score: float
    total_processing_time: float
    total_cost: float
    user_satisfaction: Optional[float]
    metadata: Dict[str, Any]


class RAGPerformanceTracker:
    """
    Advanced RAG performance tracking and analysis system
    """
    
    def __init__(self, max_history_size: int = 10000):
        self.logger = logging.getLogger(__name__)
        self.max_history_size = max_history_size
        
        # Storage
        self.retrieval_history = deque(maxlen=max_history_size)
        self.generation_history = deque(maxlen=max_history_size)
        self.pipeline_history = deque(maxlen=max_history_size)
        
        # Performance baselines
        self.performance_baselines = self._initialize_baselines()
        
        # Quality thresholds
        self.quality_thresholds = self._initialize_quality_thresholds()
        
        # Improvement tracking
        self.improvement_tracker = defaultdict(list)
    
    def _initialize_baselines(self) -> Dict[str, Dict[str, float]]:
        """Initialize performance baselines for different document types"""
        return {
            DocumentType.MEDICAL_REPORT.value: {
                "precision_at_k": 0.8,
                "recall_at_k": 0.75,
                "mrr_score": 0.85,
                "factual_accuracy": 0.9,
                "technical_accuracy": 0.85,
                "legal_compliance": 0.95
            },
            DocumentType.ASSESSMENT_REPORT.value: {
                "precision_at_k": 0.85,
                "recall_at_k": 0.8,
                "mrr_score": 0.88,
                "factual_accuracy": 0.88,
                "technical_accuracy": 0.9,
                "legal_compliance": 0.98
            },
            DocumentType.LEGAL_DOCUMENT.value: {
                "precision_at_k": 0.9,
                "recall_at_k": 0.85,
                "mrr_score": 0.9,
                "factual_accuracy": 0.95,
                "technical_accuracy": 0.88,
                "legal_compliance": 0.99
            }
        }
    
    def _initialize_quality_thresholds(self) -> Dict[str, float]:
        """Initialize quality thresholds for alerts"""
        return {
            "precision_at_k_min": 0.7,
            "recall_at_k_min": 0.65,
            "mrr_score_min": 0.75,
            "factual_accuracy_min": 0.8,
            "completeness_min": 0.75,
            "coherence_min": 0.8,
            "relevance_min": 0.8,
            "technical_accuracy_min": 0.8,
            "legal_compliance_min": 0.9
        }
    
    def record_retrieval_metrics(
        self,
        query_id: str,
        document_type: DocumentType,
        query_text: str,
        retrieved_chunks: List[str],
        relevant_chunks: List[str],
        retrieval_time: float,
        similarity_scores: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> RetrievalMetrics:
        """Record retrieval performance metrics"""
        
        # Calculate precision@k
        k = len(retrieved_chunks)
        relevant_retrieved = set(retrieved_chunks) & set(relevant_chunks)
        precision_at_k = len(relevant_retrieved) / k if k > 0 else 0.0
        
        # Calculate recall@k
        recall_at_k = len(relevant_retrieved) / len(relevant_chunks) if relevant_chunks else 0.0
        
        # Calculate MRR (Mean Reciprocal Rank)
        mrr_score = self._calculate_mrr(retrieved_chunks, relevant_chunks)
        
        # Calculate NDCG (Normalized Discounted Cumulative Gain)
        ndcg_score = self._calculate_ndcg(retrieved_chunks, relevant_chunks, similarity_scores)
        
        # Average similarity score
        avg_similarity = statistics.mean(similarity_scores) if similarity_scores else 0.0
        
        retrieval_metrics = RetrievalMetrics(
            query_id=query_id,
            timestamp=datetime.utcnow(),
            document_type=document_type,
            query_text=query_text,
            retrieved_chunks=retrieved_chunks,
            relevant_chunks=relevant_chunks,
            precision_at_k=precision_at_k,
            recall_at_k=recall_at_k,
            mrr_score=mrr_score,
            ndcg_score=ndcg_score,
            avg_similarity_score=avg_similarity,
            retrieval_time=retrieval_time,
            chunk_count=k,
            metadata=metadata or {}
        )
        
        self.retrieval_history.append(retrieval_metrics)
        
        # Record metrics for monitoring
        metrics_collector.record_metric(
            component=ComponentType.VECTOR_STORE,
            metric_type=MetricType.QUALITY_SCORE,
            value=precision_at_k,
            metadata={
                "metric_type": "precision_at_k",
                "document_type": document_type.value,
                "query_id": query_id,
                "recall": recall_at_k,
                "mrr": mrr_score,
                "ndcg": ndcg_score
            }
        )
        
        # Check quality thresholds
        self._check_retrieval_quality_thresholds(retrieval_metrics)
        
        self.logger.debug(
            f"Recorded retrieval metrics: P@{k}={precision_at_k:.3f}, "
            f"R@{k}={recall_at_k:.3f}, MRR={mrr_score:.3f}"
        )
        
        return retrieval_metrics
    
    def record_generation_metrics(
        self,
        generation_id: str,
        report_section: ReportSection,
        input_context: str,
        generated_text: str,
        generation_time: float,
        token_count: int,
        quality_scores: Dict[str, float],
        reference_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> GenerationMetrics:
        """Record generation quality metrics"""
        
        generation_metrics = GenerationMetrics(
            generation_id=generation_id,
            timestamp=datetime.utcnow(),
            report_section=report_section,
            input_context=input_context,
            generated_text=generated_text,
            reference_text=reference_text,
            factual_accuracy=quality_scores.get("factual_accuracy", 0.0),
            completeness=quality_scores.get("completeness", 0.0),
            coherence=quality_scores.get("coherence", 0.0),
            relevance=quality_scores.get("relevance", 0.0),
            style_consistency=quality_scores.get("style_consistency", 0.0),
            technical_accuracy=quality_scores.get("technical_accuracy", 0.0),
            legal_compliance=quality_scores.get("legal_compliance", 0.0),
            generation_time=generation_time,
            token_count=token_count,
            metadata=metadata or {}
        )
        
        self.generation_history.append(generation_metrics)
        
        # Record metrics for monitoring
        overall_score = statistics.mean([
            score for score in quality_scores.values() if score > 0
        ])
        
        metrics_collector.record_metric(
            component=ComponentType.LLM_PROVIDER,
            metric_type=MetricType.QUALITY_SCORE,
            value=overall_score,
            metadata={
                "section": report_section.value,
                "generation_id": generation_id,
                "token_count": token_count,
                "generation_time": generation_time,
                **quality_scores
            }
        )
        
        # Check quality thresholds
        self._check_generation_quality_thresholds(generation_metrics)
        
        self.logger.debug(
            f"Recorded generation metrics: Overall={overall_score:.3f}, "
            f"Section={report_section.value}, Tokens={token_count}"
        )
        
        return generation_metrics
    
    def record_pipeline_performance(
        self,
        pipeline_id: str,
        document_id: str,
        document_type: DocumentType,
        processing_strategy: ProcessingStrategy,
        retrieval_metrics: RetrievalMetrics,
        generation_metrics: List[GenerationMetrics],
        total_cost: float,
        user_satisfaction: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PipelinePerformanceMetrics:
        """Record end-to-end pipeline performance"""
        
        # Calculate overall quality score
        retrieval_score = (
            retrieval_metrics.precision_at_k * 0.3 +
            retrieval_metrics.recall_at_k * 0.3 +
            retrieval_metrics.mrr_score * 0.4
        )
        
        generation_scores = []
        for gen_metrics in generation_metrics:
            gen_score = statistics.mean([
                gen_metrics.factual_accuracy,
                gen_metrics.completeness,
                gen_metrics.coherence,
                gen_metrics.relevance,
                gen_metrics.technical_accuracy,
                gen_metrics.legal_compliance
            ])
            generation_scores.append(gen_score)
        
        avg_generation_score = statistics.mean(generation_scores) if generation_scores else 0.0
        overall_quality_score = (retrieval_score * 0.4 + avg_generation_score * 0.6)
        
        # Calculate total processing time
        total_processing_time = (
            retrieval_metrics.retrieval_time +
            sum(gen.generation_time for gen in generation_metrics)
        )
        
        pipeline_metrics = PipelinePerformanceMetrics(
            pipeline_id=pipeline_id,
            timestamp=datetime.utcnow(),
            document_id=document_id,
            document_type=document_type,
            processing_strategy=processing_strategy,
            retrieval_metrics=retrieval_metrics,
            generation_metrics=generation_metrics,
            overall_quality_score=overall_quality_score,
            total_processing_time=total_processing_time,
            total_cost=total_cost,
            user_satisfaction=user_satisfaction,
            metadata=metadata or {}
        )
        
        self.pipeline_history.append(pipeline_metrics)
        
        # Record comprehensive metrics for monitoring
        metrics_collector.record_metric(
            component=ComponentType.RAG_PIPELINE,
            metric_type=MetricType.PROCESSING_TIME,
            value=total_processing_time,
            metadata={
                "pipeline_id": pipeline_id,
                "document_type": document_type.value,
                "processing_strategy": processing_strategy.value,
                "overall_quality": overall_quality_score,
                "total_cost": total_cost,
                "user_satisfaction": user_satisfaction
            }
        )
        
        metrics_collector.record_metric(
            component=ComponentType.RAG_PIPELINE,
            metric_type=MetricType.QUALITY_SCORE,
            value=overall_quality_score,
            metadata={
                "pipeline_id": pipeline_id,
                "retrieval_score": retrieval_score,
                "generation_score": avg_generation_score,
                "sections_generated": len(generation_metrics)
            }
        )
        
        # Track improvement over time
        self._track_performance_improvement(pipeline_metrics)
        
        self.logger.info(
            f"Recorded pipeline performance: {pipeline_id} - "
            f"Quality={overall_quality_score:.3f}, Time={total_processing_time:.2f}s, "
            f"Cost=${total_cost:.4f}"
        )
        
        return pipeline_metrics
    
    def _calculate_mrr(self, retrieved: List[str], relevant: List[str]) -> float:
        """Calculate Mean Reciprocal Rank"""
        if not relevant:
            return 0.0
        
        for i, chunk in enumerate(retrieved):
            if chunk in relevant:
                return 1.0 / (i + 1)
        return 0.0
    
    def _calculate_ndcg(
        self, 
        retrieved: List[str], 
        relevant: List[str], 
        scores: List[float]
    ) -> float:
        """Calculate Normalized Discounted Cumulative Gain"""
        if not retrieved or not relevant or not scores:
            return 0.0
        
        # Create relevance judgments (1 if relevant, 0 otherwise)
        relevance_scores = [1.0 if chunk in relevant else 0.0 for chunk in retrieved]
        
        # Calculate DCG
        dcg = relevance_scores[0]
        for i in range(1, len(relevance_scores)):
            dcg += relevance_scores[i] / np.log2(i + 1)
        
        # Calculate IDCG (ideal DCG)
        ideal_relevance = sorted(relevance_scores, reverse=True)
        idcg = ideal_relevance[0]
        for i in range(1, len(ideal_relevance)):
            idcg += ideal_relevance[i] / np.log2(i + 1)
        
        return dcg / idcg if idcg > 0 else 0.0
    
    def _check_retrieval_quality_thresholds(self, metrics: RetrievalMetrics):
        """Check retrieval quality against thresholds and create alerts"""
        thresholds = self.quality_thresholds
        
        if metrics.precision_at_k < thresholds["precision_at_k_min"]:
            self.logger.warning(
                f"Low precision@k: {metrics.precision_at_k:.3f} < {thresholds['precision_at_k_min']}"
            )
        
        if metrics.recall_at_k < thresholds["recall_at_k_min"]:
            self.logger.warning(
                f"Low recall@k: {metrics.recall_at_k:.3f} < {thresholds['recall_at_k_min']}"
            )
        
        if metrics.mrr_score < thresholds["mrr_score_min"]:
            self.logger.warning(
                f"Low MRR score: {metrics.mrr_score:.3f} < {thresholds['mrr_score_min']}"
            )
    
    def _check_generation_quality_thresholds(self, metrics: GenerationMetrics):
        """Check generation quality against thresholds and create alerts"""
        thresholds = self.quality_thresholds
        
        quality_checks = [
            ("factual_accuracy", metrics.factual_accuracy, thresholds["factual_accuracy_min"]),
            ("completeness", metrics.completeness, thresholds["completeness_min"]),
            ("coherence", metrics.coherence, thresholds["coherence_min"]),
            ("relevance", metrics.relevance, thresholds["relevance_min"]),
            ("technical_accuracy", metrics.technical_accuracy, thresholds["technical_accuracy_min"]),
            ("legal_compliance", metrics.legal_compliance, thresholds["legal_compliance_min"])
        ]
        
        for metric_name, value, threshold in quality_checks:
            if value > 0 and value < threshold:  # Only check if value was actually measured
                self.logger.warning(
                    f"Low {metric_name}: {value:.3f} < {threshold} "
                    f"(Section: {metrics.report_section.value})"
                )
    
    def _track_performance_improvement(self, metrics: PipelinePerformanceMetrics):
        """Track performance improvement over time"""
        doc_type_key = metrics.document_type.value
        
        # Store recent performance for trend analysis
        self.improvement_tracker[doc_type_key].append({
            "timestamp": metrics.timestamp,
            "quality_score": metrics.overall_quality_score,
            "processing_time": metrics.total_processing_time,
            "cost": metrics.total_cost
        })
        
        # Keep only recent data (last 100 measurements)
        if len(self.improvement_tracker[doc_type_key]) > 100:
            self.improvement_tracker[doc_type_key] = self.improvement_tracker[doc_type_key][-100:]
    
    def get_performance_analysis(self, document_type: Optional[DocumentType] = None, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive performance analysis"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Filter data
        recent_pipelines = [
            p for p in self.pipeline_history
            if (p.timestamp > cutoff_time and 
                (document_type is None or p.document_type == document_type))
        ]
        
        if not recent_pipelines:
            return {"error": "No pipeline data available for analysis"}
        
        # Calculate summary statistics
        quality_scores = [p.overall_quality_score for p in recent_pipelines]
        processing_times = [p.total_processing_time for p in recent_pipelines]
        costs = [p.total_cost for p in recent_pipelines]
        
        # Retrieval analysis
        retrieval_precisions = [p.retrieval_metrics.precision_at_k for p in recent_pipelines]
        retrieval_recalls = [p.retrieval_metrics.recall_at_k for p in recent_pipelines]
        mrr_scores = [p.retrieval_metrics.mrr_score for p in recent_pipelines]
        
        # Generation analysis by section
        section_analysis = defaultdict(list)
        for pipeline in recent_pipelines:
            for gen_metrics in pipeline.generation_metrics:
                section_key = gen_metrics.report_section.value
                section_analysis[section_key].append({
                    "factual_accuracy": gen_metrics.factual_accuracy,
                    "completeness": gen_metrics.completeness,
                    "coherence": gen_metrics.coherence,
                    "relevance": gen_metrics.relevance,
                    "technical_accuracy": gen_metrics.technical_accuracy,
                    "legal_compliance": gen_metrics.legal_compliance
                })
        
        # Performance trends
        performance_trend = self._calculate_performance_trend(recent_pipelines)
        
        # Optimization recommendations
        recommendations = self._generate_optimization_recommendations(recent_pipelines)
        
        return {
            "analysis_period": f"Last {hours} hours",
            "total_pipelines": len(recent_pipelines),
            "document_type_filter": document_type.value if document_type else "all",
            
            "overall_performance": {
                "avg_quality_score": statistics.mean(quality_scores),
                "median_quality_score": statistics.median(quality_scores),
                "quality_std_dev": statistics.stdev(quality_scores) if len(quality_scores) > 1 else 0,
                "avg_processing_time": statistics.mean(processing_times),
                "median_processing_time": statistics.median(processing_times),
                "avg_cost": statistics.mean(costs),
                "total_cost": sum(costs)
            },
            
            "retrieval_performance": {
                "avg_precision_at_k": statistics.mean(retrieval_precisions),
                "avg_recall_at_k": statistics.mean(retrieval_recalls),
                "avg_mrr_score": statistics.mean(mrr_scores),
                "precision_trend": "improving" if len(retrieval_precisions) > 5 and 
                                  statistics.mean(retrieval_precisions[-5:]) > statistics.mean(retrieval_precisions[:5]) 
                                  else "stable"
            },
            
            "generation_performance": {
                section: {
                    "avg_factual_accuracy": statistics.mean([m["factual_accuracy"] for m in metrics if m["factual_accuracy"] > 0]),
                    "avg_completeness": statistics.mean([m["completeness"] for m in metrics if m["completeness"] > 0]),
                    "avg_coherence": statistics.mean([m["coherence"] for m in metrics if m["coherence"] > 0]),
                    "avg_relevance": statistics.mean([m["relevance"] for m in metrics if m["relevance"] > 0]),
                    "avg_technical_accuracy": statistics.mean([m["technical_accuracy"] for m in metrics if m["technical_accuracy"] > 0]),
                    "avg_legal_compliance": statistics.mean([m["legal_compliance"] for m in metrics if m["legal_compliance"] > 0]),
                    "sample_count": len(metrics)
                }
                for section, metrics in section_analysis.items()
            },
            
            "performance_trends": performance_trend,
            "optimization_recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _calculate_performance_trend(self, pipelines: List[PipelinePerformanceMetrics]) -> Dict[str, str]:
        """Calculate performance trends"""
        if len(pipelines) < 10:
            return {"trend": "insufficient_data"}
        
        # Split into two halves for comparison
        mid_point = len(pipelines) // 2
        first_half = pipelines[:mid_point]
        second_half = pipelines[mid_point:]
        
        first_avg_quality = statistics.mean([p.overall_quality_score for p in first_half])
        second_avg_quality = statistics.mean([p.overall_quality_score for p in second_half])
        
        first_avg_time = statistics.mean([p.total_processing_time for p in first_half])
        second_avg_time = statistics.mean([p.total_processing_time for p in second_half])
        
        quality_change = (second_avg_quality - first_avg_quality) / first_avg_quality
        time_change = (second_avg_time - first_avg_time) / first_avg_time
        
        quality_trend = "improving" if quality_change > 0.05 else "degrading" if quality_change < -0.05 else "stable"
        time_trend = "faster" if time_change < -0.1 else "slower" if time_change > 0.1 else "stable"
        
        return {
            "quality_trend": quality_trend,
            "performance_trend": time_trend,
            "quality_change_percent": round(quality_change * 100, 2),
            "time_change_percent": round(time_change * 100, 2)
        }
    
    def _generate_optimization_recommendations(self, pipelines: List[PipelinePerformanceMetrics]) -> List[str]:
        """Generate optimization recommendations based on performance data"""
        recommendations = []
        
        # Quality analysis
        avg_quality = statistics.mean([p.overall_quality_score for p in pipelines])
        if avg_quality < 0.75:
            recommendations.append("Overall quality score is below target (75%) - review prompt engineering and model selection")
        
        # Retrieval analysis
        avg_precision = statistics.mean([p.retrieval_metrics.precision_at_k for p in pipelines])
        if avg_precision < 0.8:
            recommendations.append("Retrieval precision is low - consider improving document chunking strategy or embedding model")
        
        avg_recall = statistics.mean([p.retrieval_metrics.recall_at_k for p in pipelines])
        if avg_recall < 0.75:
            recommendations.append("Retrieval recall is low - consider increasing chunk overlap or expanding search scope")
        
        # Performance analysis
        avg_time = statistics.mean([p.total_processing_time for p in pipelines])
        if avg_time > 30:
            recommendations.append("Processing time is high - consider optimizing vector search or using faster models for simple tasks")
        
        # Cost analysis
        avg_cost = statistics.mean([p.total_cost for p in pipelines])
        if avg_cost > 0.50:
            recommendations.append("Average cost per pipeline is high - review token usage and consider more cost-effective models")
        
        # Strategy-specific recommendations
        strategy_performance = defaultdict(list)
        for pipeline in pipelines:
            strategy_performance[pipeline.processing_strategy].append(pipeline.overall_quality_score)
        
        if len(strategy_performance) > 1:
            best_strategy = max(strategy_performance.keys(), 
                              key=lambda s: statistics.mean(strategy_performance[s]))
            recommendations.append(f"Best performing strategy: {best_strategy.value} - consider using more frequently")
        
        return recommendations


# Global RAG performance tracker instance
rag_performance_tracker = RAGPerformanceTracker()