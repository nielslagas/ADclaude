# Troubleshooting Guide - AI-Arbeidsdeskundige

Comprehensive troubleshooting guide for common issues, diagnostic procedures, and resolution steps for the AI-Arbeidsdeskundige application.

## Table of Contents

1. [Quick Diagnostic Commands](#quick-diagnostic-commands)
2. [Application Issues](#application-issues)
3. [Infrastructure Problems](#infrastructure-problems)
4. [AI/RAG Pipeline Issues](#airag-pipeline-issues)
5. [Database Problems](#database-problems)
6. [Performance Issues](#performance-issues)
7. [Security and Access Issues](#security-and-access-issues)
8. [Monitoring and Alerting Issues](#monitoring-and-alerting-issues)
9. [User-Reported Issues](#user-reported-issues)
10. [Emergency Procedures](#emergency-procedures)

## Quick Diagnostic Commands

### System Health Check
```bash
#!/bin/bash
# Quick system health assessment

echo "=== AI-Arbeidsdeskundige Quick Diagnostics ==="

# Service status
echo "1. Container Status:"
docker-compose ps

# API health
echo "2. API Health:"
curl -f http://localhost:8000/api/health && echo "✅ API OK" || echo "❌ API Failed"

# Database
echo "3. Database:"
docker-compose exec -T db pg_isready -U postgres && echo "✅ DB OK" || echo "❌ DB Failed"

# Redis
echo "4. Redis:"
docker-compose exec -T redis redis-cli ping | grep -q "PONG" && echo "✅ Redis OK" || echo "❌ Redis Failed"

# Disk space
echo "5. Disk Usage:"
df -h | grep -E "(/$|/var/lib/docker)"

# Memory
echo "6. Memory Usage:"
free -h

echo "=== Quick Check Complete ==="
```

### Log Analysis Commands
```bash
# Recent errors across all services
docker-compose logs --since=1h | grep -i error

# API specific errors
docker-compose logs -f backend-api | grep -E "(ERROR|CRITICAL)"

# Worker task failures
docker-compose logs -f backend-worker | grep -E "(FAILED|ERROR)"

# Database connection issues
docker-compose logs -f backend-api | grep -i "database\|connection"
```

## Application Issues

### Frontend Not Loading

#### Symptoms
- White screen or loading spinner
- JavaScript console errors
- Components not rendering

#### Diagnostic Steps
```bash
# Check frontend container
docker-compose ps frontend

# Frontend logs
docker-compose logs -f frontend

# Build status
docker-compose exec frontend npm list --depth=0

# Network connectivity test
curl -I http://localhost:5173
```

#### Common Causes & Solutions

**1. Container Not Running**
```bash
# Solution: Restart frontend
docker-compose restart frontend

# If that fails, rebuild
docker-compose down
docker-compose up -d --build frontend
```

**2. Build Errors**
```bash
# Clear node_modules and rebuild
docker-compose exec frontend rm -rf node_modules package-lock.json
docker-compose exec frontend npm install
docker-compose restart frontend
```

**3. API Connection Issues**
```javascript
// Check API configuration in frontend
// File: app/frontend/src/services/api.ts
const API_BASE = process.env.VITE_API_URL || 'http://localhost:8000';
```

### Backend API Issues

#### Symptoms
- 500 Internal Server Error
- Connection timeouts
- Slow response times

#### Diagnostic Commands
```bash
# API health check
curl -v http://localhost:8000/api/health

# Check API logs
docker-compose logs -f backend-api | tail -100

# Test specific endpoints
curl -X GET http://localhost:8000/api/v1/cases/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check worker queue
docker-compose exec redis redis-cli llen default
```

#### Resolution Steps

**1. Service Restart**
```bash
# Graceful restart
docker-compose restart backend-api

# Force restart if unresponsive
docker-compose kill backend-api
docker-compose up -d backend-api
```

**2. Database Connection Issues**
```bash
# Check database connectivity
docker-compose exec backend-api python -c "
from app.db.database_service import db_service
print('DB Connection:', db_service.test_connection())
"

# Reset connection pool
docker-compose restart backend-api backend-worker
```

**3. Memory Issues**
```bash
# Check memory usage
docker stats backend-api

# If high memory usage, check for leaks
docker-compose exec backend-api python -c "
import psutil
process = psutil.Process()
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

### Celery Worker Issues

#### Symptoms
- Tasks stuck in pending state
- Background processing not working
- High task failure rate

#### Diagnostic Commands
```bash
# Worker status
docker-compose exec backend-worker celery -A app.celery_worker inspect active

# Queue status
docker-compose exec backend-worker celery -A app.celery_worker inspect stats

# Failed tasks
docker-compose exec redis redis-cli llen failed

# Worker logs
docker-compose logs -f backend-worker
```

#### Solutions

**1. Restart Workers**
```bash
# Graceful restart
docker-compose restart backend-worker

# Scale workers if needed
docker-compose up -d --scale backend-worker=3
```

**2. Clear Failed Tasks**
```bash
# Purge all tasks
docker-compose exec backend-worker celery -A app.celery_worker purge

# Clear specific queue
docker-compose exec redis redis-cli del default
```

**3. Memory/Resource Issues**
```bash
# Check worker resource usage
docker stats backend-worker

# Restart with resource limits
docker-compose down backend-worker
docker-compose up -d backend-worker
```

## Infrastructure Problems

### Docker Container Issues

#### Container Won't Start
```bash
# Check exit codes
docker ps -a

# Detailed logs
docker-compose logs [service-name]

# Resource constraints
docker system df
docker system prune -f

# Check for port conflicts
netstat -tulpn | grep :8000
```

#### Out of Disk Space
```bash
# Check disk usage
df -h
docker system df

# Clean up Docker resources
docker system prune -a -f
docker volume prune -f

# Remove old images
docker image prune -a -f
```

### Network Connectivity Issues

#### Services Can't Communicate
```bash
# Check Docker networks
docker network ls
docker network inspect ai-arbeidsdeskundige_default

# Test inter-service connectivity
docker-compose exec backend-api ping db
docker-compose exec backend-api ping redis

# DNS resolution test
docker-compose exec backend-api nslookup db
```

#### Port Binding Issues
```bash
# Check port usage
netstat -tulpn | grep -E "(8000|5432|6379|5173)"

# Kill processes using required ports
lsof -ti:8000 | xargs kill -9

# Restart with different ports if needed
docker-compose down
docker-compose up -d
```

## AI/RAG Pipeline Issues

### Document Processing Failures

#### Symptoms
- Documents stuck in "processing" state
- Classification errors
- Embedding generation failures

#### Diagnostic Commands
```bash
# Check processing status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/monitoring/components/document_processor/stats

# Test document classification
docker-compose exec backend-api python test_smart_classification.py

# Check vector store health
docker-compose exec backend-api python -c "
from app.utils.vector_store_improved import VectorStoreService
vs = VectorStoreService()
print('Vector store status:', vs.health_check())
"
```

#### Solutions

**1. Restart Processing Pipeline**
```bash
# Clear processing queue
docker-compose exec redis redis-cli flushdb

# Restart workers
docker-compose restart backend-worker

# Reprocess failed documents
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/documents/reprocess-failed
```

**2. LLM Provider Issues**
```bash
# Test LLM connectivity
docker-compose exec backend-api python -c "
from app.utils.llm_provider import get_llm_provider
llm = get_llm_provider()
print('LLM Status:', llm.test_connection())
"

# Switch to backup provider
export LLM_PROVIDER=openai  # or anthropic
docker-compose restart backend-api backend-worker
```

### Report Generation Issues

#### Symptoms
- Reports not generating
- Poor quality scores
- Generation timeouts

#### Diagnostic Steps
```bash
# Check report generation status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/monitoring/components/report_generator/stats

# Test RAG pipeline
docker-compose exec backend-api python test_hybrid_rag_report.py

# Check quality control
docker-compose exec backend-api python test_quality_control.py
```

#### Solutions

**1. Quality Issues**
```bash
# Adjust quality thresholds
export QUALITY_THRESHOLD=0.70
docker-compose restart backend-api backend-worker

# Regenerate with higher quality
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/reports/regenerate \
  -d '{"report_id": "uuid", "quality_level": "high"}'
```

**2. Performance Issues**
```bash
# Increase timeout settings
export API_TIMEOUT=60
export CHUNKING_TIMEOUT=60
docker-compose restart backend-api backend-worker

# Scale processing resources
docker-compose up -d --scale backend-worker=3
```

### Audio Processing Issues

#### Symptoms
- Audio transcription failures
- Poor transcription quality
- Processing timeouts

#### Diagnostic Commands
```bash
# Test Whisper integration
docker-compose exec backend-api python test_whisper.py

# Check audio processing logs
docker-compose logs -f backend-worker | grep -i audio

# Test direct Whisper API
docker-compose exec backend-api python test_whisper_direct.py
```

#### Solutions

**1. Transcription Quality Issues**
```bash
# Check audio file quality
docker-compose exec backend-api python -c "
import librosa
audio, sr = librosa.load('/path/to/audio.mp3')
print(f'Sample rate: {sr}, Duration: {len(audio)/sr:.2f}s')
"

# Adjust Whisper settings
export WHISPER_MODEL=large-v2
docker-compose restart backend-worker
```

**2. Processing Failures**
```bash
# Clear audio processing queue
docker-compose exec redis redis-cli del audio_processing

# Restart with more memory
docker-compose up -d --scale backend-worker=2
```

## Database Problems

### Connection Issues

#### Symptoms
- "Could not connect to database" errors
- Connection timeouts
- Max connections exceeded

#### Diagnostic Commands
```bash
# Database status
docker-compose exec db pg_isready -U postgres

# Connection count
docker-compose exec db psql -U postgres -c "
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';"

# Check connection settings
docker-compose exec db psql -U postgres -c "SHOW max_connections;"
```

#### Solutions

**1. Connection Pool Issues**
```bash
# Restart API to reset connections
docker-compose restart backend-api

# Increase connection limits
docker-compose exec db psql -U postgres -c "
ALTER SYSTEM SET max_connections = 200;
SELECT pg_reload_conf();"
```

**2. Database Locks**
```bash
# Check for locks
docker-compose exec db psql -U postgres -c "
SELECT pid, state, query_start, query 
FROM pg_stat_activity 
WHERE state = 'active' AND pid <> pg_backend_pid();"

# Kill problematic queries if needed
docker-compose exec db psql -U postgres -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE pid = [PROBLEMATIC_PID];"
```

### Performance Issues

#### Slow Queries
```bash
# Enable query logging
docker-compose exec db psql -U postgres -c "
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();"

# Check slow queries
docker-compose logs db | grep "duration:"

# Analyze query performance
docker-compose exec db psql -U postgres -c "
EXPLAIN ANALYZE SELECT * FROM documents WHERE case_id = 'uuid';"
```

#### Storage Issues
```bash
# Check database size
docker-compose exec db psql -U postgres -c "
SELECT pg_size_pretty(pg_database_size('postgres'));"

# Check table sizes
docker-compose exec db psql -U postgres -c "
SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# Vacuum and analyze
docker-compose exec db psql -U postgres -c "VACUUM ANALYZE;"
```

### Vector Search Issues

#### pgvector Extension Problems
```bash
# Check extension
docker-compose exec db psql -U postgres -c "
SELECT * FROM pg_extension WHERE extname = 'vector';"

# Reinstall if needed
docker-compose exec db psql -U postgres -c "
DROP EXTENSION IF EXISTS vector;
CREATE EXTENSION vector;"

# Test vector operations
docker-compose exec db psql -U postgres -c "
SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector as distance;"
```

## Performance Issues

### High Response Times

#### Diagnostic Commands
```bash
# API performance metrics
curl http://localhost:8000/api/v1/monitoring/metrics/snapshot | jq '.api_metrics'

# Database performance
docker stats db

# Application profiling
docker-compose exec backend-api python -c "
import cProfile
import pstats
# Profile critical functions
"
```

#### Optimization Steps

**1. Database Optimization**
```bash
# Create missing indexes
docker-compose exec db psql -U postgres -c "
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_case_id ON documents(case_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_document_id ON document_embeddings(document_id);
"

# Update statistics
docker-compose exec db psql -U postgres -c "ANALYZE;"
```

**2. Application Optimization**
```bash
# Enable caching
export REDIS_CACHE_ENABLED=true
export CACHE_TTL=3600
docker-compose restart backend-api

# Adjust worker concurrency
export CELERY_WORKER_CONCURRENCY=4
docker-compose restart backend-worker
```

### Memory Issues

#### High Memory Usage
```bash
# Check memory usage by service
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Python memory profiling
docker-compose exec backend-api python -c "
import tracemalloc
tracemalloc.start()
# Run your code
current, peak = tracemalloc.get_traced_memory()
print(f'Current: {current / 1024 / 1024:.2f} MB, Peak: {peak / 1024 / 1024:.2f} MB')
"
```

#### Memory Optimization
```bash
# Adjust Python garbage collection
export PYTHONHASHSEED=0
export PYTHONOPTIMIZE=1
docker-compose restart backend-api backend-worker

# Limit worker memory
docker-compose exec backend-worker celery -A app.celery_worker worker \
  --max-memory-per-child=500000  # 500MB limit
```

## Security and Access Issues

### Authentication Problems

#### Token Issues
```bash
# Test token validation
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/auth/verify

# Generate new token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

#### Permission Errors
```bash
# Check user permissions
docker-compose exec db psql -U postgres -c "
SELECT id, email, is_active FROM auth.users WHERE email = 'user@example.com';"

# Reset user permissions
docker-compose exec db psql -U postgres -c "
UPDATE auth.users SET is_active = true WHERE email = 'user@example.com';"
```

### File Permission Issues

#### Container Permission Problems
```bash
# Check file ownership
docker-compose exec backend-api ls -la /app/storage/

# Fix permissions
docker-compose exec backend-api chown -R app:app /app/storage/
docker-compose exec backend-api chmod -R 755 /app/storage/
```

## Monitoring and Alerting Issues

### Missing Metrics

#### Prometheus Issues
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Test metrics endpoint
curl http://localhost:8000/metrics

# Restart Prometheus
docker-compose restart prometheus
```

#### Grafana Dashboard Issues
```bash
# Check Grafana health
curl http://localhost:3000/api/health

# Reset admin password
docker-compose exec grafana grafana-cli admin reset-admin-password admin

# Import dashboards
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @monitoring/grafana/dashboards/system-overview.json
```

### Alert Issues

#### Alerts Not Firing
```bash
# Check alert rules
curl http://localhost:9090/api/v1/rules

# Test alert conditions
curl http://localhost:9090/api/v1/query?query=up==0

# Verify alert manager
curl http://localhost:9093/api/v1/alerts
```

## User-Reported Issues

### "My document won't upload"

#### Quick Checks
```bash
# File size check
ls -lh /path/to/document.pdf

# File type verification
file /path/to/document.pdf

# Upload endpoint test
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "case_id=uuid" \
  -F "file=@document.pdf"
```

#### Common Solutions
1. **File too large**: Check MAX_UPLOAD_SIZE setting
2. **Unsupported format**: Verify supported file types
3. **Corrupted file**: Have user re-export/save document
4. **Network timeout**: Increase upload timeout settings

### "Report generation is slow"

#### Diagnostic Steps
```bash
# Check current processing load
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/monitoring/components/report_generator/stats

# Review report complexity
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/reports/uuid/metadata
```

#### Optimization Actions
1. **Scale workers**: `docker-compose up -d --scale backend-worker=3`
2. **Optimize document set**: Remove non-essential documents
3. **Use faster LLM provider**: Switch to lower-latency provider
4. **Adjust quality settings**: Lower quality for faster generation

### "Report quality is poor"

#### Investigation Steps
```bash
# Check quality metrics
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/monitoring/quality/dashboard

# Analyze specific report
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/reports/uuid/quality-analysis
```

#### Improvement Actions
1. **Review source documents**: Ensure high-quality, relevant documents
2. **Update prompts**: Customize prompts for specific case types  
3. **Adjust settings**: Increase quality threshold
4. **Manual review**: Enable manual quality control steps

## Emergency Procedures

### System Down - Full Outage

#### Immediate Response
```bash
# 1. Quick health check
./scripts/health-check.sh

# 2. Check all services
docker-compose ps

# 3. Restart everything
docker-compose down
docker-compose up -d

# 4. Verify recovery
curl http://localhost:8000/api/health
```

#### Escalation Steps
1. **Check monitoring dashboards**: Identify root cause
2. **Review recent changes**: Check deployment history
3. **Contact on-call team**: Use escalation procedures
4. **Implement emergency fixes**: Apply hotfixes if needed

### Data Recovery

#### Database Recovery
```bash
# 1. Stop application services
docker-compose stop backend-api backend-worker

# 2. Create backup before recovery
docker-compose exec db pg_dump -U postgres postgres > emergency_backup.sql

# 3. Restore from latest backup
docker-compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS postgres_old;"
docker-compose exec db psql -U postgres -c "ALTER DATABASE postgres RENAME TO postgres_old;"
docker-compose exec db createdb -U postgres postgres
docker-compose exec db psql -U postgres postgres < /backups/latest_backup.sql

# 4. Verify data integrity
docker-compose exec db psql -U postgres -c "SELECT COUNT(*) FROM cases;"

# 5. Restart services
docker-compose start backend-api backend-worker
```

### Performance Emergency

#### High Load Response
```bash
# 1. Scale critical services immediately
docker-compose up -d --scale backend-api=3 --scale backend-worker=5

# 2. Enable emergency caching
export EMERGENCY_CACHE_ENABLED=true
docker-compose restart backend-api

# 3. Throttle non-critical operations
export RATE_LIMIT_ENABLED=true
export RATE_LIMIT_REQUESTS=10
docker-compose restart backend-api

# 4. Monitor recovery
watch "curl -s http://localhost:8000/api/v1/monitoring/metrics/snapshot | jq '.api_metrics.average_response_time_ms'"
```

## Contact Information

### Escalation Matrix

| Severity | Response Time | Contact |
|----------|---------------|---------|
| P1 - Critical | 15 minutes | +31 20 123 4567 |
| P2 - High | 2 hours | support@ai-arbeidsdeskundige.nl |
| P3 - Medium | 24 hours | support@ai-arbeidsdeskundige.nl |
| P4 - Low | 72 hours | support@ai-arbeidsdeskundige.nl |

### Support Channels
- **📞 Emergency Hotline**: +31 20 123 4567 (24/7 for P1 issues)
- **📧 Technical Support**: support@ai-arbeidsdeskundige.nl
- **💬 Slack**: #support-ai-arbeidsdeskundige
- **📋 Ticket System**: https://support.ai-arbeidsdeskundige.nl

---

**Last Updated**: January 29, 2025  
**Version**: 1.0.0  
**Next Review**: February 29, 2025