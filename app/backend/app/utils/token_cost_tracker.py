"""
Advanced Token Cost Tracking for Multi-Provider LLM Usage
Comprehensive cost analysis and optimization for AI-Arbeidsdeskundige
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import json
from collections import defaultdict, deque

from app.utils.rag_monitoring import metrics_collector, ComponentType, MetricType


class LLMProvider(Enum):
    """Supported LLM providers"""
    ANTHROPIC_CLAUDE = "anthropic"
    OPENAI_GPT = "openai"
    GOOGLE_GEMINI = "google"


class ModelTier(Enum):
    """Model performance tiers"""
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    FLAGSHIP = "flagship"


@dataclass
class TokenPricing:
    """Token pricing structure for different models"""
    provider: LLMProvider
    model_name: str
    tier: ModelTier
    input_price_per_1k: float  # USD per 1000 input tokens
    output_price_per_1k: float  # USD per 1000 output tokens
    context_window: int
    last_updated: datetime


@dataclass
class TokenUsageRecord:
    """Individual token usage record"""
    timestamp: datetime
    provider: LLMProvider
    model_name: str
    component: ComponentType
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    request_id: str
    metadata: Dict[str, Any]


@dataclass
class CostAnalysis:
    """Cost analysis summary"""
    time_period: str
    total_cost: float
    total_tokens: int
    cost_by_provider: Dict[str, float]
    cost_by_component: Dict[str, float]
    cost_by_model: Dict[str, float]
    tokens_by_provider: Dict[str, int]
    average_cost_per_request: float
    cost_trend: str  # "increasing", "decreasing", "stable"
    optimization_suggestions: List[str]


class TokenCostTracker:
    """
    Advanced token cost tracking and optimization system
    """
    
    def __init__(self, max_history_size: int = 50000):
        self.logger = logging.getLogger(__name__)
        self.max_history_size = max_history_size
        
        # Storage
        self.usage_history = deque(maxlen=max_history_size)
        self.pricing_data = self._initialize_pricing_data()
        
        # Optimization tracking
        self.cost_budgets = {}
        self.efficiency_targets = {}
        
        # Performance counters
        self.provider_performance = defaultdict(lambda: {
            "total_requests": 0,
            "total_cost": 0.0,
            "average_quality": 0.0,
            "average_response_time": 0.0,
            "cost_per_quality_point": 0.0
        })
        
    def _initialize_pricing_data(self) -> Dict[str, TokenPricing]:
        """Initialize current token pricing data"""
        now = datetime.utcnow()
        
        pricing_data = {
            # Anthropic Claude Models
            "claude-3-5-sonnet-20241022": TokenPricing(
                provider=LLMProvider.ANTHROPIC_CLAUDE,
                model_name="claude-3-5-sonnet-20241022",
                tier=ModelTier.FLAGSHIP,
                input_price_per_1k=3.00,
                output_price_per_1k=15.00,
                context_window=200000,
                last_updated=now
            ),
            "claude-3-haiku-20240307": TokenPricing(
                provider=LLMProvider.ANTHROPIC_CLAUDE,
                model_name="claude-3-haiku-20240307",
                tier=ModelTier.BASIC,
                input_price_per_1k=0.25,
                output_price_per_1k=1.25,
                context_window=200000,
                last_updated=now
            ),
            
            # OpenAI GPT Models
            "gpt-4-turbo": TokenPricing(
                provider=LLMProvider.OPENAI_GPT,
                model_name="gpt-4-turbo",
                tier=ModelTier.PREMIUM,
                input_price_per_1k=10.00,
                output_price_per_1k=30.00,
                context_window=128000,
                last_updated=now
            ),
            "gpt-4o": TokenPricing(
                provider=LLMProvider.OPENAI_GPT,
                model_name="gpt-4o",
                tier=ModelTier.FLAGSHIP,
                input_price_per_1k=5.00,
                output_price_per_1k=15.00,
                context_window=128000,
                last_updated=now
            ),
            "gpt-3.5-turbo": TokenPricing(
                provider=LLMProvider.OPENAI_GPT,
                model_name="gpt-3.5-turbo",
                tier=ModelTier.STANDARD,
                input_price_per_1k=0.50,
                output_price_per_1k=1.50,
                context_window=16384,
                last_updated=now
            ),
            
            # Google Gemini Models
            "gemini-1.5-pro": TokenPricing(
                provider=LLMProvider.GOOGLE_GEMINI,
                model_name="gemini-1.5-pro",
                tier=ModelTier.PREMIUM,
                input_price_per_1k=3.50,
                output_price_per_1k=10.50,
                context_window=2000000,
                last_updated=now
            ),
            "gemini-1.5-flash": TokenPricing(
                provider=LLMProvider.GOOGLE_GEMINI,
                model_name="gemini-1.5-flash",
                tier=ModelTier.STANDARD,
                input_price_per_1k=0.075,
                output_price_per_1k=0.30,
                context_window=1000000,
                last_updated=now
            )
        }
        
        return pricing_data
    
    def record_token_usage(
        self,
        provider: str,
        model_name: str,
        component: ComponentType,
        input_tokens: int,
        output_tokens: int,
        request_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TokenUsageRecord:
        """Record token usage and calculate costs"""
        
        try:
            provider_enum = LLMProvider(provider)
        except ValueError:
            self.logger.warning(f"Unknown provider: {provider}")
            provider_enum = LLMProvider.OPENAI_GPT  # Default fallback
        
        total_tokens = input_tokens + output_tokens
        
        # Get pricing data
        pricing = self.pricing_data.get(model_name)
        if not pricing:
            self.logger.warning(f"No pricing data for model: {model_name}")
            # Use default pricing based on provider
            pricing = self._get_default_pricing(provider_enum)
        
        # Calculate costs
        input_cost = (input_tokens / 1000) * pricing.input_price_per_1k
        output_cost = (output_tokens / 1000) * pricing.output_price_per_1k
        total_cost = input_cost + output_cost
        
        # Create usage record
        usage_record = TokenUsageRecord(
            timestamp=datetime.utcnow(),
            provider=provider_enum,
            model_name=model_name,
            component=component,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            request_id=request_id,
            metadata=metadata or {}
        )
        
        # Store usage record
        self.usage_history.append(usage_record)
        
        # Update performance tracking
        self._update_provider_performance(usage_record)
        
        # Record metrics for monitoring
        metrics_collector.record_metric(
            component=component,
            metric_type=MetricType.TOKEN_USAGE,
            value=total_tokens,
            metadata={
                "provider": provider,
                "model": model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": total_cost,
                "request_id": request_id
            }
        )
        
        # Check cost budgets and alerts
        self._check_cost_budgets(usage_record)
        
        self.logger.debug(
            f"Recorded token usage: {model_name} - {total_tokens} tokens, ${total_cost:.4f}"
        )
        
        return usage_record
    
    def _get_default_pricing(self, provider: LLMProvider) -> TokenPricing:
        """Get default pricing for unknown models"""
        defaults = {
            LLMProvider.ANTHROPIC_CLAUDE: TokenPricing(
                provider=provider,
                model_name="claude-default",
                tier=ModelTier.STANDARD,
                input_price_per_1k=1.00,
                output_price_per_1k=3.00,
                context_window=100000,
                last_updated=datetime.utcnow()
            ),
            LLMProvider.OPENAI_GPT: TokenPricing(
                provider=provider,
                model_name="gpt-default",
                tier=ModelTier.STANDARD,
                input_price_per_1k=1.00,
                output_price_per_1k=2.00,
                context_window=8192,
                last_updated=datetime.utcnow()
            ),
            LLMProvider.GOOGLE_GEMINI: TokenPricing(
                provider=provider,
                model_name="gemini-default",
                tier=ModelTier.STANDARD,
                input_price_per_1k=0.50,
                output_price_per_1k=1.50,
                context_window=32000,
                last_updated=datetime.utcnow()
            )
        }
        return defaults.get(provider, defaults[LLMProvider.OPENAI_GPT])
    
    def _update_provider_performance(self, usage_record: TokenUsageRecord):
        """Update provider performance metrics"""
        provider_key = usage_record.provider.value
        perf = self.provider_performance[provider_key]
        
        perf["total_requests"] += 1
        perf["total_cost"] += usage_record.total_cost
        
        # Update averages (simplified)
        quality_score = usage_record.metadata.get("quality_score", 0.8)
        response_time = usage_record.metadata.get("response_time", 5.0)
        
        current_avg_quality = perf["average_quality"]
        current_avg_time = perf["average_response_time"]
        total_requests = perf["total_requests"]
        
        perf["average_quality"] = (
            (current_avg_quality * (total_requests - 1) + quality_score) / total_requests
        )
        perf["average_response_time"] = (
            (current_avg_time * (total_requests - 1) + response_time) / total_requests
        )
        
        # Calculate cost efficiency
        if perf["average_quality"] > 0:
            perf["cost_per_quality_point"] = perf["total_cost"] / (perf["average_quality"] * total_requests)
    
    def _check_cost_budgets(self, usage_record: TokenUsageRecord):
        """Check if usage exceeds cost budgets"""
        # Implementation for budget monitoring
        # This would integrate with the alerting system
        pass
    
    def get_cost_analysis(self, hours: int = 24) -> CostAnalysis:
        """Generate comprehensive cost analysis"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_usage = [
            record for record in self.usage_history
            if record.timestamp > cutoff_time
        ]
        
        if not recent_usage:
            return CostAnalysis(
                time_period=f"Last {hours} hours",
                total_cost=0.0,
                total_tokens=0,
                cost_by_provider={},
                cost_by_component={},
                cost_by_model={},
                tokens_by_provider={},
                average_cost_per_request=0.0,
                cost_trend="stable",
                optimization_suggestions=[]
            )
        
        # Calculate totals
        total_cost = sum(record.total_cost for record in recent_usage)
        total_tokens = sum(record.total_tokens for record in recent_usage)
        
        # Group by different dimensions
        cost_by_provider = defaultdict(float)
        cost_by_component = defaultdict(float)
        cost_by_model = defaultdict(float)
        tokens_by_provider = defaultdict(int)
        
        for record in recent_usage:
            provider_key = record.provider.value
            component_key = record.component.value
            model_key = record.model_name
            
            cost_by_provider[provider_key] += record.total_cost
            cost_by_component[component_key] += record.total_cost
            cost_by_model[model_key] += record.total_cost
            tokens_by_provider[provider_key] += record.total_tokens
        
        # Calculate average cost per request
        average_cost_per_request = total_cost / len(recent_usage) if recent_usage else 0.0
        
        # Determine cost trend
        cost_trend = self._calculate_cost_trend(hours)
        
        # Generate optimization suggestions
        optimization_suggestions = self._generate_optimization_suggestions(
            recent_usage, cost_by_provider, cost_by_model
        )
        
        return CostAnalysis(
            time_period=f"Last {hours} hours",
            total_cost=total_cost,
            total_tokens=total_tokens,
            cost_by_provider=dict(cost_by_provider),
            cost_by_component=dict(cost_by_component),
            cost_by_model=dict(cost_by_model),
            tokens_by_provider=dict(tokens_by_provider),
            average_cost_per_request=average_cost_per_request,
            cost_trend=cost_trend,
            optimization_suggestions=optimization_suggestions
        )
    
    def _calculate_cost_trend(self, hours: int) -> str:
        """Calculate whether costs are increasing, decreasing, or stable"""
        
        now = datetime.utcnow()
        half_period = timedelta(hours=hours//2)
        
        # Split period in half
        middle_time = now - half_period
        start_time = now - timedelta(hours=hours)
        
        first_half = [
            record for record in self.usage_history
            if start_time <= record.timestamp < middle_time
        ]
        second_half = [
            record for record in self.usage_history
            if middle_time <= record.timestamp <= now
        ]
        
        if not first_half or not second_half:
            return "stable"
        
        first_half_cost = sum(record.total_cost for record in first_half)
        second_half_cost = sum(record.total_cost for record in second_half)
        
        # Calculate percentage change
        if first_half_cost == 0:
            return "increasing" if second_half_cost > 0 else "stable"
        
        change_percent = (second_half_cost - first_half_cost) / first_half_cost
        
        if change_percent > 0.2:  # 20% increase
            return "increasing"
        elif change_percent < -0.2:  # 20% decrease
            return "decreasing"
        else:
            return "stable"
    
    def _generate_optimization_suggestions(
        self, 
        recent_usage: List[TokenUsageRecord],
        cost_by_provider: Dict[str, float],
        cost_by_model: Dict[str, float]
    ) -> List[str]:
        """Generate cost optimization suggestions"""
        
        suggestions = []
        
        # Find most expensive provider
        if cost_by_provider:
            most_expensive_provider = max(cost_by_provider, key=cost_by_provider.get)
            if cost_by_provider[most_expensive_provider] > sum(cost_by_provider.values()) * 0.7:
                suggestions.append(
                    f"Consider diversifying from {most_expensive_provider} - "
                    f"accounts for {cost_by_provider[most_expensive_provider]/sum(cost_by_provider.values())*100:.1f}% of costs"
                )
        
        # Find expensive models
        if cost_by_model:
            sorted_models = sorted(cost_by_model.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_models) > 1:
                top_model_cost = sorted_models[0][1]
                total_cost = sum(cost_by_model.values())
                if top_model_cost > total_cost * 0.5:
                    suggestions.append(
                        f"Model {sorted_models[0][0]} accounts for "
                        f"{top_model_cost/total_cost*100:.1f}% of costs - consider alternatives"
                    )
        
        # Check for high output token ratios
        total_input = sum(record.input_tokens for record in recent_usage)
        total_output = sum(record.output_tokens for record in recent_usage)
        
        if total_input > 0:
            output_ratio = total_output / total_input
            if output_ratio > 2.0:
                suggestions.append(
                    f"High output/input ratio ({output_ratio:.1f}) - "
                    "consider more concise prompts or output formatting"
                )
        
        # Performance-based suggestions
        for provider_key, perf in self.provider_performance.items():
            if perf["total_requests"] > 10:  # Minimum sample size
                cost_per_quality = perf.get("cost_per_quality_point", 0)
                if cost_per_quality > 0.10:  # $0.10 per quality point
                    suggestions.append(
                        f"Provider {provider_key} has high cost per quality point "
                        f"(${cost_per_quality:.3f}) - review model selection"
                    )
        
        return suggestions
    
    def get_provider_comparison(self) -> Dict[str, Any]:
        """Get comprehensive provider performance comparison"""
        
        comparison = {}
        
        for provider_key, perf in self.provider_performance.items():
            if perf["total_requests"] > 0:
                comparison[provider_key] = {
                    "total_requests": perf["total_requests"],
                    "total_cost": round(perf["total_cost"], 4),
                    "average_cost_per_request": round(
                        perf["total_cost"] / perf["total_requests"], 4
                    ),
                    "average_quality": round(perf["average_quality"], 3),
                    "average_response_time": round(perf["average_response_time"], 2),
                    "cost_per_quality_point": round(perf["cost_per_quality_point"], 4),
                    "efficiency_score": self._calculate_efficiency_score(perf)
                }
        
        return comparison
    
    def _calculate_efficiency_score(self, performance: Dict[str, Any]) -> float:
        """Calculate overall efficiency score for a provider"""
        
        # Normalize metrics (higher is better for quality, lower is better for cost and time)
        quality_score = performance["average_quality"]  # 0-1, higher is better
        
        # Normalize cost (assume $0.01 per request is excellent, $0.10 is poor)
        cost_per_request = performance["total_cost"] / performance["total_requests"]
        cost_score = max(0, min(1, (0.10 - cost_per_request) / 0.09))
        
        # Normalize response time (assume 2s is excellent, 20s is poor)
        time_score = max(0, min(1, (20 - performance["average_response_time"]) / 18))
        
        # Weighted efficiency score
        efficiency_score = (
            quality_score * 0.4 +     # 40% weight on quality
            cost_score * 0.35 +       # 35% weight on cost
            time_score * 0.25         # 25% weight on speed
        )
        
        return round(efficiency_score, 3)
    
    def export_cost_data(self, hours: int = 24, format: str = "json") -> str:
        """Export cost data for external analysis"""
        
        analysis = self.get_cost_analysis(hours)
        provider_comparison = self.get_provider_comparison()
        
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "time_range_hours": hours,
            "cost_analysis": asdict(analysis),
            "provider_comparison": provider_comparison,
            "pricing_data": {
                model: asdict(pricing) for model, pricing in self.pricing_data.items()
            }
        }
        
        if format == "json":
            return json.dumps(export_data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Global token cost tracker instance
token_cost_tracker = TokenCostTracker()