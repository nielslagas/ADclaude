# Monitoring and Observability Guide

Complete guide for monitoring the AI-Arbeidsdeskundige application, including metrics, alerts, dashboards, and troubleshooting procedures.

## Table of Contents

1. [Overview](#overview)
2. [Monitoring Architecture](#monitoring-architecture)
3. [Metrics Collection](#metrics-collection)
4. [Performance Monitoring](#performance-monitoring)
5. [Quality Control Monitoring](#quality-control-monitoring)
6. [Alert Management](#alert-management)
7. [Dashboard Configuration](#dashboard-configuration)
8. [Log Management](#log-management)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

## Overview

The AI-Arbeidsdeskundige monitoring system provides comprehensive observability across all components:

- **📊 Real-time Metrics**: Performance, quality, and usage metrics
- **🚨 Intelligent Alerting**: Proactive issue detection and notification
- **📈 Trend Analysis**: Historical performance and quality tracking
- **🔍 Deep Diagnostics**: Component-level troubleshooting tools
- **📋 Custom Dashboards**: Tailored views for different stakeholders

### Key Monitoring Areas

```
🏗️ Infrastructure          📊 Application Performance    🤖 AI/RAG Components
├── Docker containers      ├── API response times        ├── Document classification
├── Database performance   ├── Request throughput        ├── RAG pipeline metrics
├── Redis cache           ├── Error rates              ├── Quality scores
├── Storage usage         ├── User sessions             ├── LLM provider health
└── Network connectivity  └── Background jobs           └── Token usage tracking
```

## Monitoring Architecture

### Component Stack

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Grafana       │    │   Prometheus    │    │   Loki          │
│   (Dashboards)  │◄──►│   (Metrics)     │    │   (Logs)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                     AI-Arbeidsdeskundige                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Frontend   │  │  Backend    │  │  Workers    │             │
│  │             │  │   API       │  │  (Celery)   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                           │                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 RAG Monitoring                          │   │
│  │  - Document Classification   - Quality Control         │   │
│  │  - Vector Search            - Token Usage              │   │
│  │  - LLM Providers            - Performance Metrics     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Metrics Collection**: Application components emit metrics
2. **Metrics Storage**: Prometheus scrapes and stores time-series data
3. **Log Aggregation**: Loki collects structured logs from all services
4. **Visualization**: Grafana creates dashboards from metrics and logs
5. **Alerting**: Prometheus/Grafana trigger alerts based on rules

## Metrics Collection

### Application Metrics

#### API Performance Metrics
```python
# Available via /api/v1/monitoring/metrics/snapshot
{
  "api_metrics": {
    "requests_per_minute": 45,
    "average_response_time_ms": 234,
    "error_rate": 0.02,
    "active_connections": 12,
    "endpoints": {
      "/api/v1/documents/upload": {
        "requests": 156,
        "avg_response_time": 1245,
        "error_rate": 0.01
      },
      "/api/v1/reports/generate": {
        "requests": 34,
        "avg_response_time": 5670,
        "error_rate": 0.03
      }
    }
  }
}
```

#### RAG Pipeline Metrics
```python
# Available via /api/v1/monitoring/components/rag_pipeline/stats
{
  "rag_pipeline": {
    "documents_processed_today": 156,
    "reports_generated_today": 34,
    "average_processing_time_seconds": 23,
    "quality_score": 0.87,
    "classification_accuracy": 0.94,
    "chunks_generated": 1245,
    "embeddings_created": 1245,
    "vector_searches": 567
  }
}
```

#### LLM Provider Metrics
```python
{
  "llm_providers": {
    "anthropic": {
      "status": "healthy",
      "requests_today": 234,
      "average_response_time_ms": 1245,
      "tokens_used_today": 145623,
      "cost_estimate_today": 12.45,
      "error_rate": 0.01
    },
    "openai": {
      "status": "healthy", 
      "requests_today": 89,
      "average_response_time_ms": 987,
      "tokens_used_today": 67432,
      "cost_estimate_today": 8.90,
      "error_rate": 0.02
    }
  }
}
```

### System Metrics

#### Infrastructure Health
```python
{
  "system_health": {
    "status": "healthy",
    "uptime_seconds": 86400,
    "memory_usage_mb": 512,
    "cpu_usage_percent": 23,
    "disk_usage_percent": 45,
    "containers": {
      "backend-api": "healthy",
      "backend-worker": "healthy", 
      "db": "healthy",
      "redis": "healthy",
      "frontend": "healthy"
    }
  }
}
```

#### Database Performance
```python
{
  "database": {
    "active_connections": 12,
    "max_connections": 100,
    "query_time_avg_ms": 45,
    "slow_queries_count": 2,
    "cache_hit_ratio": 0.95,
    "index_usage": 0.98,
    "storage_usage_gb": 2.3
  }
}
```

## Performance Monitoring

### Key Performance Indicators (KPIs)

#### Document Processing KPIs
| Metric | Target | Critical Threshold | Alert Level |
|--------|--------|-------------------|-------------|
| Processing Time | < 30s | > 60s | Warning |
| Classification Accuracy | > 90% | < 80% | Critical |
| Quality Score | > 85% | < 75% | Warning |
| Error Rate | < 2% | > 5% | Critical |

#### Report Generation KPIs
| Metric | Target | Critical Threshold | Alert Level |
|--------|--------|-------------------|-------------|
| Generation Time | < 10 min | > 20 min | Warning |
| Quality Score | > 87% | < 75% | Critical |
| Success Rate | > 98% | < 95% | Critical |
| User Satisfaction | > 4.0/5 | < 3.5/5 | Warning |

#### System KPIs
| Metric | Target | Critical Threshold | Alert Level |
|--------|--------|-------------------|-------------|
| API Response Time | < 500ms | > 2000ms | Critical |
| CPU Usage | < 70% | > 90% | Critical |
| Memory Usage | < 80% | > 95% | Critical |
| Database Query Time | < 100ms | > 1000ms | Warning |

### Performance Monitoring Commands

#### Real-time Monitoring
```bash
# Get current performance snapshot
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/monitoring/metrics/snapshot

# Monitor specific component
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/monitoring/components/document_processor/stats

# Check system health
curl http://localhost:8000/api/health
```

#### Historical Analysis
```bash
# Get component statistics for last 24 hours
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/monitoring/components/rag_pipeline/stats?time_range=24h"

# Export metrics for analysis
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/monitoring/metrics/export > metrics_$(date +%Y%m%d).json
```

## Quality Control Monitoring

### Quality Metrics Dashboard

#### Section Quality Tracking
```python
# Available via /api/v1/monitoring/quality/dashboard
{
  "section_quality": {
    "persoonsgegevens": {
      "average_score": 0.94,
      "total_sections": 156,
      "low_quality_count": 2,
      "trend": "stable"
    },
    "medische_situatie": {
      "average_score": 0.85,
      "total_sections": 134,
      "low_quality_count": 8,
      "trend": "improving"
    },
    "conclusie": {
      "average_score": 0.89,
      "total_sections": 156,
      "low_quality_count": 5,
      "trend": "declining"
    }
  }
}
```

#### Quality Improvement Tracking
```python
{
  "quality_improvements": {
    "automatic_improvements_today": 23,
    "manual_reviews_requested": 5,
    "quality_score_improvement": "+2.3%",
    "most_improved_section": "medische_situatie",
    "areas_needing_attention": [
      {
        "section": "conclusie",
        "issue": "Consistency with medical findings",
        "suggestion": "Enhance context integration"
      }
    ]
  }
}
```

### Quality Alerts

#### Automatic Quality Alerts
```bash
# Quality score below threshold
{
  "alert_type": "quality_degradation",
  "section": "medische_situatie", 
  "current_score": 0.72,
  "threshold": 0.75,
  "case_id": "uuid",
  "timestamp": "2025-01-29T10:30:00Z",
  "suggested_action": "Review medical document integration"
}

# Consistency issues detected
{
  "alert_type": "consistency_issue",
  "sections": ["medische_situatie", "belastbaarheid"],
  "issue": "Conflicting statements about mobility limitations",
  "case_id": "uuid",
  "severity": "medium"
}
```

## Alert Management

### Alert Configuration

#### Alert Rules Configuration
```yaml
# monitoring/prometheus/rules/rag-pipeline-alerts.yml
groups:
  - name: rag_pipeline
    rules:
      - alert: HighDocumentProcessingTime
        expr: document_processing_time_seconds > 60
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Document processing taking too long"
          description: "Processing time {{ $value }}s exceeds threshold"

      - alert: LowQualityScore
        expr: report_quality_score < 0.75
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Report quality below acceptable threshold"
          description: "Quality score {{ $value }} is below 0.75"

      - alert: LLMProviderDown
        expr: llm_provider_health == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "LLM Provider unavailable"
          description: "{{ $labels.provider }} is not responding"
```

#### Alert Channels
```yaml
# Alert routing configuration
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'
  routes:
  - match:
      severity: critical
    receiver: 'critical-alerts'
  - match:
      severity: warning
    receiver: 'warning-alerts'

receivers:
- name: 'critical-alerts'
  slack_configs:
  - api_url: 'YOUR_SLACK_WEBHOOK'
    channel: '#critical-alerts'
    title: 'AI-Arbeidsdeskundige Critical Alert'
    text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

- name: 'warning-alerts'
  email_configs:
  - to: 'admin@your-domain.com'
    subject: 'AI-Arbeidsdeskundige Warning'
    body: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

### Alert Management API

#### Active Alerts
```bash
# Get current active alerts
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/monitoring/alerts

# Acknowledge alert
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/monitoring/alerts/acknowledge \
  -d '{"alert_id": "alert-uuid", "acknowledged_by": "admin"}'
```

#### Alert History
```bash
# Get alert history
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/monitoring/alerts/history?days=7"
```

## Dashboard Configuration

### Grafana Dashboards

#### 1. System Overview Dashboard
```json
{
  "dashboard": {
    "title": "AI-Arbeidsdeskundige Overview",
    "panels": [
      {
        "title": "API Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Document Processing",
        "type": "stat",
        "targets": [
          {
            "expr": "documents_processed_total",
            "legendFormat": "Total Processed"
          }
        ]
      },
      {
        "title": "Quality Scores",
        "type": "gauge",
        "targets": [
          {
            "expr": "avg(report_quality_score)",
            "legendFormat": "Average Quality"
          }
        ]
      }
    ]
  }
}
```

#### 2. RAG Pipeline Dashboard
Key metrics panels:
- Document classification accuracy over time
- Processing time by document type
- Quality scores by report section
- LLM provider performance comparison
- Token usage and cost tracking
- Error rates by component

#### 3. Infrastructure Dashboard
System health panels:
- CPU and memory usage
- Database performance metrics
- Container health status
- Network latency
- Storage usage trends

### Custom Dashboard Creation

#### Dashboard Templates
Pre-configured dashboard templates are available in:
```
monitoring/grafana/dashboards/
├── system-overview.json
├── rag-pipeline.json
├── quality-control.json
├── infrastructure.json
└── custom-template.json
```

#### Creating Custom Dashboards
1. **Access Grafana**: http://localhost:3000 (admin/admin)
2. **Import Template**: Use provided JSON templates
3. **Customize Panels**: Add specific metrics for your use case
4. **Save Dashboard**: Export configuration for version control

## Log Management

### Log Structure

#### Application Logs
```json
{
  "timestamp": "2025-01-29T10:30:15.123Z",
  "level": "INFO",
  "service": "backend-api",
  "component": "document_processor",
  "message": "Document processing completed",
  "metadata": {
    "document_id": "uuid",
    "processing_time_ms": 2340,
    "document_type": "medical_report",
    "quality_score": 0.87
  },
  "trace_id": "trace-uuid"
}
```

#### RAG Component Logs
```json
{
  "timestamp": "2025-01-29T10:30:16.456Z",
  "level": "DEBUG", 
  "service": "backend-worker",
  "component": "rag_pipeline",
  "message": "Vector search completed",
  "metadata": {
    "query": "medical conditions",
    "results_count": 8,
    "search_time_ms": 125,
    "similarity_threshold": 0.8
  },
  "trace_id": "trace-uuid"
}
```

### Log Aggregation

#### Loki Configuration
```yaml
# monitoring/loki/loki-config.yml
server:
  http_listen_port: 3100

ingester:
  lifecycler:
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1

schema_config:
  configs:
  - from: 2020-10-24
    store: boltdb-shipper
    object_store: filesystem
    schema: v11
    index:
      prefix: index_
      period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
  filesystem:
    directory: /loki/chunks
```

#### Log Queries
```bash
# View application logs
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={service="backend-api"}' \
  --data-urlencode 'start=2025-01-29T00:00:00Z' \
  --data-urlencode 'end=2025-01-29T23:59:59Z'

# Search for errors
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={level="ERROR"}' \
  --data-urlencode 'start=1h'

# RAG pipeline specific logs
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={component="rag_pipeline"}' \
  --data-urlencode 'start=1h'
```

## Troubleshooting

### Common Monitoring Issues

#### 1. Missing Metrics Data

**Symptoms:**
- Empty graphs in Grafana
- No data in Prometheus targets
- API endpoints not responding

**Diagnostic Steps:**
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify metrics endpoint
curl http://localhost:8000/metrics

# Check service health
docker-compose ps
docker-compose logs -f prometheus
```

**Solutions:**
- Restart monitoring services: `docker-compose restart prometheus grafana`
- Check network connectivity between services
- Verify metric endpoint configuration

#### 2. High Memory Usage Alerts

**Symptoms:**
- Memory usage alerts firing
- Slow application performance
- Container restarts

**Diagnostic Steps:**
```bash
# Check container memory usage
docker stats

# Analyze memory-intensive processes
docker-compose exec backend-api top

# Check for memory leaks
curl http://localhost:8000/api/v1/monitoring/metrics/snapshot | jq '.system_health.memory_usage_mb'
```

**Solutions:**
- Scale up memory allocation
- Optimize document processing batch sizes
- Enable garbage collection tuning
- Implement memory-efficient caching

#### 3. Quality Score Degradation

**Symptoms:**
- Declining quality scores over time
- User complaints about report quality
- Quality alerts firing

**Diagnostic Steps:**
```bash
# Analyze quality trends
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/monitoring/quality/dashboard

# Check recent quality issues
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/monitoring/quality/trends?days=7

# Review failing cases
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/monitoring/cases/low-quality?threshold=0.75"
```

**Solutions:**
- Review and update prompt templates
- Retrain document classification model
- Adjust quality control thresholds
- Improve source document quality

### Monitoring Troubleshooting Checklist

#### System Health Check
```bash
#!/bin/bash
# monitoring-health-check.sh

echo "=== AI-Arbeidsdeskundige Health Check ==="

# 1. Service Status
echo "1. Checking service status..."
docker-compose ps

# 2. API Health
echo "2. Checking API health..."
curl -f http://localhost:8000/api/health || echo "API health check failed"

# 3. Metrics Availability
echo "3. Checking metrics..."
curl -f http://localhost:8000/metrics > /dev/null || echo "Metrics endpoint failed"

# 4. Database Connectivity
echo "4. Checking database..."
docker-compose exec -T db pg_isready -U postgres || echo "Database check failed"

# 5. Redis Status
echo "5. Checking Redis..."
docker-compose exec -T redis redis-cli ping || echo "Redis check failed"

# 6. Monitoring Stack
echo "6. Checking monitoring stack..."
curl -f http://localhost:9090/-/healthy > /dev/null || echo "Prometheus unhealthy"
curl -f http://localhost:3000/api/health > /dev/null || echo "Grafana unhealthy"

echo "=== Health Check Complete ==="
```

#### Performance Diagnostic Script
```bash
#!/bin/bash
# performance-diagnostic.sh

echo "=== Performance Diagnostics ==="

# System resources
echo "System Resources:"
docker stats --no-stream

# API performance
echo "API Performance (last 5 minutes):"
curl -s http://localhost:8000/api/v1/monitoring/metrics/snapshot | jq '.api_metrics'

# Database performance
echo "Database Performance:"
curl -s http://localhost:8000/api/v1/monitoring/components/database/stats | jq '.statistics'

# RAG pipeline performance
echo "RAG Pipeline Performance:"
curl -s http://localhost:8000/api/v1/monitoring/components/rag_pipeline/stats | jq '.statistics'

echo "=== Diagnostics Complete ==="
```

## Best Practices

### Monitoring Setup Best Practices

1. **Comprehensive Coverage**
   - Monitor all system layers (infrastructure, application, business metrics)
   - Include both technical and user experience metrics
   - Set up monitoring before production deployment

2. **Alert Management**
   - Use tiered alerting (info, warning, critical)
   - Avoid alert fatigue with proper thresholds
   - Include remediation steps in alert descriptions
   - Regularly review and tune alert rules

3. **Dashboard Design**
   - Create role-specific dashboards (ops, dev, business)
   - Use clear, actionable visualizations
   - Include trend analysis and comparisons
   - Ensure mobile-friendly layouts

4. **Data Retention**
   - Configure appropriate retention policies
   - Archive historical data for compliance
   - Balance storage costs with analysis needs
   - Implement data lifecycle management

### Performance Optimization

1. **Proactive Monitoring**
   ```bash
   # Daily performance check
   curl -s http://localhost:8000/api/v1/monitoring/metrics/snapshot | \
     jq '.performance_summary' > daily_performance_$(date +%Y%m%d).json
   ```

2. **Capacity Planning**
   - Monitor resource utilization trends
   - Plan for traffic spikes and growth
   - Set up predictive alerting
   - Regular capacity reviews

3. **Quality Monitoring**
   ```bash
   # Weekly quality report
   curl -s -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/monitoring/quality/dashboard | \
     jq '.quality_overview' > weekly_quality_$(date +%Y%m%d).json
   ```

### Security Monitoring

1. **Access Monitoring**
   - Track authentication failures
   - Monitor unusual access patterns
   - Log administrative actions
   - Alert on security policy violations

2. **Data Protection**
   - Monitor data access and modifications
   - Track document processing activities
   - Alert on suspicious activities
   - Regular security audits

### Operational Excellence

1. **Documentation**
   - Maintain runbooks for common issues
   - Document escalation procedures
   - Keep monitoring configuration in version control
   - Regular documentation reviews

2. **Team Processes**
   - Establish on-call procedures
   - Regular monitoring reviews
   - Post-incident analysis
   - Continuous improvement cycles

---

**📞 Support Contacts**

- **Technical Support**: monitoring@ai-arbeidsdeskundige.nl
- **Emergency**: +31 20 123 4567 (24/7 critical issues)
- **Documentation**: docs@ai-arbeidsdeskundige.nl

---

**Last Updated**: January 29, 2025  
**Version**: 1.0.0