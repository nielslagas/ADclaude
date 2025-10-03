"""
Quality Control API Endpoints voor AI-Arbeidsdeskundige
Comprehensive API for content validation, improvement, and quality analytics
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Body
from pydantic import BaseModel, Field
import asyncio
import logging

from app.utils.quality_controller import (
    AutomaticQualityController, 
    QualityReport, 
    QualityIssue,
    QualityIssueType,
    QualitySeverity
)
from app.utils.context_aware_prompts import ReportSection, ComplexityLevel
from app.utils.rag_monitoring import ComponentType, MetricType
from app.core.security import get_current_user

# Initialize router and logger
router = APIRouter(prefix="/quality", tags=["Quality Control"])
logger = logging.getLogger(__name__)

# Initialize quality controller
quality_controller = AutomaticQualityController()


# Pydantic models for API
class ContentValidationRequest(BaseModel):
    """Request model for content validation"""
    content: str = Field(..., description="Content to validate", min_length=1, max_length=10000)
    section: ReportSection = Field(..., description="Report section type")
    context_chunks: Optional[List[str]] = Field(None, description="Related document chunks for context")
    complexity_level: ComplexityLevel = Field(ComplexityLevel.MEDIUM, description="Content complexity level")
    structured_data: Optional[Dict[str, Any]] = Field(None, description="Additional structured data to validate")
    record_metrics: bool = Field(True, description="Whether to record quality metrics")


class ContentImprovementRequest(BaseModel):
    """Request model for content improvement"""
    content: str = Field(..., description="Content to improve", min_length=1, max_length=10000)
    section: ReportSection = Field(..., description="Report section type")
    improvement_strategy: str = Field("comprehensive", description="Improvement strategy: comprehensive, focused, conservative")
    target_score: float = Field(0.8, description="Target quality score", ge=0.0, le=1.0)
    max_iterations: int = Field(3, description="Maximum improvement iterations", ge=1, le=5)
    context_chunks: Optional[List[str]] = Field(None, description="Related document chunks")


class BatchValidationRequest(BaseModel):
    """Request model for batch content validation"""
    items: List[ContentValidationRequest] = Field(..., description="List of content items to validate", max_items=20)


class BatchImprovementRequest(BaseModel):
    """Request model for batch content improvement"""
    items: List[Dict[str, Any]] = Field(..., description="Quality reports to improve", max_items=10)
    target_score: float = Field(0.8, description="Target quality score", ge=0.0, le=1.0)


class QualityIssueResponse(BaseModel):
    """Response model for quality issues"""
    type: str
    severity: str
    description: str
    location: str
    suggestion: str
    confidence: float


class QualityReportResponse(BaseModel):
    """Response model for quality reports"""
    overall_score: float
    issues: List[QualityIssueResponse]
    strengths: List[str]
    recommendations: List[str]
    section: str
    compliance_status: str
    improvement_potential: float
    processing_time_ms: float
    ai_confidence: float
    section_scores: Optional[Dict[str, float]] = None
    validation_timestamp: str


class ImprovementResultResponse(BaseModel):
    """Response model for improvement results"""
    improved_text: str
    original_score: float
    final_score: float
    improvement: float
    iterations_used: int
    strategy_used: str
    processing_time_ms: float
    improvement_log: List[Dict[str, Any]]


class QualityTrendsResponse(BaseModel):
    """Response model for quality trends"""
    section: str
    time_range_hours: int
    total_evaluations: int
    quality_summary: Dict[str, Any]
    issue_analysis: Dict[str, Any]
    compliance_analysis: Dict[str, Any]
    improvement_potential: Dict[str, Any]


class DashboardDataResponse(BaseModel):
    """Response model for dashboard data"""
    timestamp: str
    time_range_hours: int
    overview: Dict[str, Any]
    section_breakdown: Dict[str, Any]
    quality_distribution: Dict[str, Any]
    improvement_opportunities: Dict[str, Any]
    compliance_status: Dict[str, Any]


# Helper functions
def convert_quality_report_to_response(report: QualityReport) -> QualityReportResponse:
    """Convert QualityReport to API response model"""
    return QualityReportResponse(
        overall_score=report.overall_score,
        issues=[
            QualityIssueResponse(
                type=issue.type.value,
                severity=issue.severity.value,
                description=issue.description,
                location=issue.location,
                suggestion=issue.suggestion,
                confidence=issue.confidence
            )
            for issue in report.issues
        ],
        strengths=report.strengths,
        recommendations=report.recommendations,
        section=report.section.value,
        compliance_status=report.compliance_status or "unknown",
        improvement_potential=report.improvement_potential or 0.0,
        processing_time_ms=report.processing_time_ms or 0.0,
        ai_confidence=report.ai_confidence or 0.0,
        section_scores=report.section_scores,
        validation_timestamp=report.validation_timestamp or datetime.utcnow().isoformat()
    )


# API Endpoints
@router.post("/validate", response_model=QualityReportResponse)
async def validate_content(
    request: ContentValidationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Validate content quality with comprehensive analysis
    
    Performs extensive quality validation including:
    - Rule-based validation
    - AI-powered analysis  
    - Compliance checking
    - Context consistency
    - Domain-specific validation
    - Structured data validation
    """
    try:
        logger.info(f"Validating content for section: {request.section.value}")
        
        # Perform validation
        quality_report = await quality_controller.validate_and_record(
            content=request.content,
            section=request.section,
            context_chunks=request.context_chunks,
            complexity_level=request.complexity_level,
            structured_data=request.structured_data,
            record_metrics=request.record_metrics
        )
        
        return convert_quality_report_to_response(quality_report)
        
    except Exception as e:
        logger.error(f"Content validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quality validation failed: {str(e)}")


@router.post("/improve", response_model=ImprovementResultResponse)
async def improve_content(
    request: ContentImprovementRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Improve content quality using AI-powered enhancement
    
    Features:
    - Multiple improvement strategies
    - Iterative enhancement
    - Target score achievement
    - Detailed improvement tracking
    """
    try:
        logger.info(f"Improving content for section: {request.section.value} with strategy: {request.improvement_strategy}")
        
        # First validate to get quality report
        quality_report = await quality_controller.validate_content(
            content=request.content,
            section=request.section,
            context_chunks=request.context_chunks
        )
        
        # Improve content
        improvement_result = await quality_controller.improve_content(
            quality_report=quality_report,
            improvement_strategy=request.improvement_strategy,
            target_score=request.target_score,
            max_iterations=request.max_iterations
        )
        
        return ImprovementResultResponse(**improvement_result)
        
    except Exception as e:
        logger.error(f"Content improvement failed: {e}")
        raise HTTPException(status_code=500, detail=f"Content improvement failed: {str(e)}")


@router.post("/validate-batch", response_model=List[QualityReportResponse])
async def validate_batch_content(
    request: BatchValidationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Validate multiple content pieces in batch
    
    Efficient batch processing for multiple content validation
    """
    try:
        logger.info(f"Batch validating {len(request.items)} content items")
        
        results = []
        for item in request.items:
            try:
                quality_report = await quality_controller.validate_and_record(
                    content=item.content,
                    section=item.section,
                    context_chunks=item.context_chunks,
                    complexity_level=item.complexity_level,
                    structured_data=item.structured_data,
                    record_metrics=item.record_metrics
                )
                results.append(convert_quality_report_to_response(quality_report))
                
            except Exception as e:
                logger.warning(f"Individual validation failed: {e}")
                # Create fallback response for failed items
                fallback_report = QualityReportResponse(
                    overall_score=0.0,
                    issues=[],
                    strengths=[],
                    recommendations=[f"Validation failed: {str(e)}"],
                    section=item.section.value,
                    compliance_status="error",
                    improvement_potential=1.0,
                    processing_time_ms=0.0,
                    ai_confidence=0.0,
                    validation_timestamp=datetime.utcnow().isoformat()
                )
                results.append(fallback_report)
        
        return results
        
    except Exception as e:
        logger.error(f"Batch validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch validation failed: {str(e)}")


@router.post("/improve-batch", response_model=List[ImprovementResultResponse])
async def improve_batch_content(
    request: BatchImprovementRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Improve multiple content pieces in batch
    
    Batch processing for content improvement with statistics
    """
    try:
        logger.info(f"Batch improving {len(request.items)} content items")
        
        # Convert items to QualityReport objects (simplified for this example)
        quality_reports = []
        for item in request.items:
            # This would normally come from previous validation
            # For now, we'll validate each item first
            if "content" in item and "section" in item:
                report = await quality_controller.validate_content(
                    content=item["content"],
                    section=ReportSection(item["section"])
                )
                quality_reports.append(report)
        
        # Batch improve
        improvement_results = await quality_controller.batch_improve_content(
            quality_reports=quality_reports,
            target_score=request.target_score
        )
        
        return [ImprovementResultResponse(**result) for result in improvement_results]
        
    except Exception as e:
        logger.error(f"Batch improvement failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch improvement failed: {str(e)}")


@router.get("/trends", response_model=QualityTrendsResponse)
async def get_quality_trends(
    section: Optional[ReportSection] = Query(None, description="Specific section to analyze"),
    hours: int = Query(24, description="Time range in hours", ge=1, le=168),
    current_user: dict = Depends(get_current_user)
):
    """
    Get quality trends and analytics
    
    Provides insights into quality patterns and trends over time
    """
    try:
        logger.info(f"Getting quality trends for {hours} hours, section: {section.value if section else 'all'}")
        
        trends = quality_controller.get_quality_trends(section=section, hours=hours)
        
        if "error" in trends:
            raise HTTPException(status_code=404, detail=trends["error"])
        
        return QualityTrendsResponse(**trends)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get quality trends: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get quality trends: {str(e)}")


@router.get("/dashboard", response_model=DashboardDataResponse)
async def get_quality_dashboard(
    hours: int = Query(24, description="Time range in hours", ge=1, le=168),
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive quality dashboard data
    
    Provides complete overview for quality monitoring dashboard
    """
    try:
        logger.info(f"Getting quality dashboard data for {hours} hours")
        
        dashboard_data = quality_controller.create_quality_dashboard_data(hours=hours)
        
        if "error" in dashboard_data:
            raise HTTPException(status_code=500, detail=dashboard_data["error"])
        
        return DashboardDataResponse(**dashboard_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")


@router.get("/sections/{section}/analysis")
async def get_section_analysis(
    section: ReportSection,
    hours: int = Query(24, description="Time range in hours", ge=1, le=168),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed analysis for a specific section
    
    Provides section-specific quality insights and recommendations
    """
    try:
        logger.info(f"Getting section analysis for {section.value}")
        
        trends = quality_controller.get_quality_trends(section=section, hours=hours)
        
        if "error" in trends:
            return {
                "section": section.value,
                "status": "no_data",
                "message": trends["error"],
                "recommendations": [
                    f"No quality data available for {section.value} in the last {hours} hours",
                    "Process some content for this section to generate analytics"
                ]
            }
        
        # Add section-specific recommendations
        section_recommendations = []
        
        avg_score = trends["quality_summary"]["current_average"]
        if avg_score < 0.6:
            section_recommendations.append(f"{section.value} content consistently scores below 60% - review content generation prompts")
        elif avg_score < 0.8:
            section_recommendations.append(f"{section.value} content has room for improvement - consider additional training data")
        else:
            section_recommendations.append(f"{section.value} content quality is good - maintain current standards")
        
        critical_issues = trends["issue_analysis"]["critical_issues"]
        if critical_issues > 0:
            section_recommendations.append(f"Address {critical_issues} critical issues in {section.value} content")
        
        return {
            "section": section.value,
            "status": "success",
            "trends": trends,
            "recommendations": section_recommendations,
            "insights": {
                "performance_level": "excellent" if avg_score >= 0.9 else "good" if avg_score >= 0.8 else "needs_improvement",
                "primary_focus": "compliance" if trends["compliance_analysis"]["compliance_rate"] < 0.8 else "quality_enhancement"
            }
        }
        
    except Exception as e:
        logger.error(f"Section analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Section analysis failed: {str(e)}")


@router.get("/health")
async def quality_system_health():
    """
    Get quality control system health status
    
    Provides system health metrics and status
    """
    try:
        # Try to create a small test validation
        test_content = "Test content voor systeemstatus controle."
        test_report = await quality_controller.validate_content(
            content=test_content,
            section=ReportSection.INTRODUCTIE
        )
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "quality_controller": "operational",
                "ai_analysis": "operational" if test_report.ai_confidence > 0 else "degraded",
                "rule_validation": "operational",
                "monitoring_integration": "operational"
            },
            "metrics": {
                "test_validation_score": test_report.overall_score,
                "test_processing_time_ms": test_report.processing_time_ms,
                "issues_detected": len(test_report.issues)
            },
            "version": "2.0.0"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "components": {
                "quality_controller": "error",
                "ai_analysis": "unknown",
                "rule_validation": "unknown",
                "monitoring_integration": "unknown"
            }
        }


@router.get("/statistics")
async def get_quality_statistics(
    current_user: dict = Depends(get_current_user)
):
    """
    Get overall quality control system statistics
    
    Provides comprehensive statistics about quality control usage
    """
    try:
        # Get statistics from monitoring system
        from app.utils.rag_monitoring import metrics_collector, ComponentType, MetricType
        
        quality_metrics = [
            m for m in metrics_collector.metrics_history
            if m.component == ComponentType.QUALITY_CONTROLLER
        ]
        
        if not quality_metrics:
            return {
                "status": "no_data",
                "message": "No quality control statistics available yet",
                "total_validations": 0
            }
        
        # Calculate statistics
        total_validations = len([m for m in quality_metrics if m.metric_type == MetricType.QUALITY_SCORE])
        
        scores = [m.value for m in quality_metrics if m.metric_type == MetricType.QUALITY_SCORE]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        processing_times = [m.value for m in quality_metrics if m.metric_type == MetricType.PROCESSING_TIME]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # Section breakdown
        section_stats = {}
        for metric in quality_metrics:
            section = metric.metadata.get("section", "unknown")
            if section not in section_stats:
                section_stats[section] = {"count": 0, "scores": []}
            section_stats[section]["count"] += 1
            if metric.metric_type == MetricType.QUALITY_SCORE:
                section_stats[section]["scores"].append(metric.value)
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "overall_statistics": {
                "total_validations": total_validations,
                "average_quality_score": round(avg_score, 3),
                "average_processing_time_seconds": round(avg_processing_time, 3)
            },
            "section_breakdown": {
                section: {
                    "validations": stats["count"],
                    "average_score": round(sum(stats["scores"]) / len(stats["scores"]), 3) if stats["scores"] else 0
                }
                for section, stats in section_stats.items()
            },
            "quality_distribution": {
                "excellent_0.9+": len([s for s in scores if s >= 0.9]),
                "good_0.8-0.9": len([s for s in scores if 0.8 <= s < 0.9]),
                "fair_0.6-0.8": len([s for s in scores if 0.6 <= s < 0.8]),
                "poor_<0.6": len([s for s in scores if s < 0.6])
            }
        }
        
    except Exception as e:
        logger.error(f"Statistics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Statistics retrieval failed: {str(e)}")


@router.get("/quality-standards")
async def get_quality_standards(
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive quality standards and validation criteria
    
    Returns detailed information about all quality validation rules and standards
    """
    return {
        "issue_types": [
            {
                "value": "factual_inconsistency",
                "display_name": "Feitelijke Inconsistentie",
                "description": "Tegenstrijdige of onjuiste feitelijke informatie"
            },
            {
                "value": "insufficient_detail", 
                "display_name": "Onvoldoende Detail",
                "description": "Te weinig specifieke informatie of uitleg"
            },
            {
                "value": "unprofessional_tone",
                "display_name": "Onprofessionele Toon", 
                "description": "Niet-objectieve of informele formulering"
            },
            {
                "value": "missing_structure",
                "display_name": "Ontbrekende Structuur",
                "description": "Onduidelijke opbouw of logische volgorde"
            },
            {
                "value": "incorrect_terminology",
                "display_name": "Onjuiste Terminologie",
                "description": "Verkeerd gebruik van vakterminologie"
            },
            {
                "value": "incomplete_section",
                "display_name": "Onvolledige Sectie",
                "description": "Ontbrekende verplichte elementen"
            },
            {
                "value": "compliance_issue",
                "display_name": "Compliance Probleem",
                "description": "Privacy- of objectiviteitsschending"
            },
            {
                "value": "hallucination",
                "display_name": "Hallucinatie",
                "description": "Verzonnen of onjuiste informatie"
            },
            {
                "value": "repetition",
                "display_name": "Herhaling",
                "description": "Onnodige herhalingen in de tekst"
            },
            {
                "value": "language_quality",
                "display_name": "Taalkwaliteit",
                "description": "Grammatica, spelling of schrijfstijl problemen"
            },
            {
                "value": "legal_accuracy",
                "display_name": "Juridische Accuratesse",
                "description": "Onjuiste of verouderde juridische informatie"
            },
            {
                "value": "medical_accuracy",
                "display_name": "Medische Accuratesse",
                "description": "Onjuiste of verouderde medische informatie"
            }
        ],
        "severity_levels": [
            {
                "value": "critical",
                "display_name": "Kritiek",
                "description": "Moet worden opgelost voor publicatie",
                "weight": 0.4
            },
            {
                "value": "major",
                "display_name": "Belangrijk", 
                "description": "Sterk aanbevolen om op te lossen",
                "weight": 0.25
            },
            {
                "value": "minor",
                "display_name": "Klein",
                "description": "Optionele verbetering",
                "weight": 0.1
            },
            {
                "value": "suggestion",
                "display_name": "Suggestie",
                "description": "Stylistische verbetering",
                "weight": 0.05
            }
        ],
        "quality_thresholds": {
            "excellent": 0.9,
            "good": 0.8,
            "acceptable": 0.7,
            "needs_improvement": 0.6,
            "poor": 0.0
        },
        "compliance_rules": {
            "privacy": [
                "Geen volledige namen van derden",
                "Geen BSN nummers",
                "Geen directe identificeerbare informatie",
                "GDPR compliance voor persoonsgegevens"
            ],
            "objectivity": [
                "Feitelijke toon gebruiken",
                "Geen persoonlijke meningen",
                "Onderbouwde conclusies",
                "Neutrale formulering"
            ],
            "professional_standards": [
                "Nederlandse arbeidsdeskundige richtlijnen",
                "NVAB standaarden waar van toepassing",
                "Wetgeving correct toegepast",
                "Evidence-based conclusies"
            ]
        },
        "improvement_strategies": {
            "comprehensive": "Uitgebreide verbeteringen aan de gehele tekst",
            "focused": "Focus specifiek op de meest kritieke problemen", 
            "conservative": "Minimale, zeer betrouwbare aanpassingen"
        }
    }


# Export router for main application
__all__ = ["router"]