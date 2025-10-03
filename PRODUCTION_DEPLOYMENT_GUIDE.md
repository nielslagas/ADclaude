# AI-Arbeidsdeskundige Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the AI-Arbeidsdeskundige application to production. The deployment setup includes:

- **Production-optimized Docker containers** with multi-stage builds
- **SSL/TLS termination** with automatic certificate management
- **Security hardening** and monitoring
- **Automated backups** and disaster recovery
- **Load balancing** and high availability
- **Comprehensive monitoring** and alerting

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04 LTS or newer
- **Memory**: Minimum 16GB RAM (32GB recommended)
- **Storage**: Minimum 100GB SSD
- **CPU**: Minimum 4 cores (8 cores recommended)
- **Network**: Static IP address with ports 80, 443, 22 accessible

### Required Software

```bash
# Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Git
sudo apt update && sudo apt install -y git curl jq

# Additional security tools
sudo apt install -y fail2ban ufw
```

### Domain and DNS Setup

1. **Domain Registration**: Register your domain (e.g., `arbeidsdeskundige.nl`)
2. **DNS Configuration**:
   ```
   A    @                    -> YOUR_SERVER_IP
   A    www                  -> YOUR_SERVER_IP
   A    api                  -> YOUR_SERVER_IP
   A    grafana             -> YOUR_SERVER_IP
   A    prometheus          -> YOUR_SERVER_IP
   ```

## Deployment Steps

### 1. Server Preparation

```bash
# Create application directory
sudo mkdir -p /opt/ai-arbeidsdeskundige
sudo chown $USER:$USER /opt/ai-arbeidsdeskundige
cd /opt/ai-arbeidsdeskundige

# Clone repository
git clone https://github.com/your-org/ai-arbeidsdeskundige.git .

# Set up firewall
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

### 2. Environment Configuration

```bash
# Copy production environment template
cp .env.production.template .env.production

# Edit with your configuration
nano .env.production
```

**Required Environment Variables:**

```bash
# Domain Configuration
DOMAIN=your-domain.com
FRONTEND_URL=https://your-domain.com
BACKEND_URL=https://api.your-domain.com

# Database Credentials (Generate secure passwords)
POSTGRES_USER=your_secure_user
POSTGRES_PASSWORD=your_very_secure_password_32_chars_min
POSTGRES_DB=ai_arbeidsdeskundige_prod

# Redis Configuration
REDIS_PASSWORD=your_secure_redis_password

# LLM API Keys (At least one required)
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
OPENAI_API_KEY=sk-proj-your-key-here

# Security Configuration
JWT_SECRET_KEY=your_jwt_secret_64_characters_minimum
SSL_ENABLED=true
LETSENCRYPT_EMAIL=your-email@your-domain.com

# Backup Configuration
BACKUP_ENABLED=true
DB_BACKUP_ENCRYPTION_KEY=your_backup_encryption_key_32_chars
```

### 3. SSL Certificate Setup

The deployment uses Traefik with automatic Let's Encrypt certificates:

```bash
# Create certificate storage directory
mkdir -p /opt/ai-arbeidsdeskundige/traefik-certificates
chmod 600 /opt/ai-arbeidsdeskundige/traefik-certificates
```

### 4. Deploy the Application

```bash
# Make deployment script executable
chmod +x deployment/scripts/deploy.sh

# Run production deployment
./deployment/scripts/deploy.sh production
```

The deployment script will:
1. Validate environment configuration
2. Run security scans
3. Build optimized Docker images
4. Deploy services with zero-downtime
5. Verify deployment health
6. Set up monitoring and backups

### 5. Verify Deployment

```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# Verify health endpoints
curl -f https://your-domain.com/health
curl -f https://api.your-domain.com/api/health

# Check SSL certificates
curl -I https://your-domain.com
```

## Service Architecture

### Production Services

| Service | Purpose | Port | Health Check |
|---------|---------|------|--------------|
| **traefik** | Reverse proxy & SSL termination | 80, 443 | `/ping` |
| **frontend** | Vue.js application | Internal | `/health` |
| **backend-api** | FastAPI REST API | Internal | `/api/health` |
| **backend-worker** | Celery task processor | N/A | Celery inspect |
| **db** | PostgreSQL with pgvector | Internal | `pg_isready` |
| **redis** | Cache & message broker | Internal | `PING` |
| **prometheus** | Metrics collection | Internal | `/metrics` |
| **grafana** | Monitoring dashboards | Internal | `/api/health` |
| **backup** | Automated backup service | N/A | Custom script |

### Network Architecture

```
Internet
    ↓
Traefik (SSL Termination)
    ↓
┌─────────────────────────────────────┐
│ ai-arbeidsdeskundige-network        │
│                                     │
│ Frontend ←→ Backend API ←→ Worker   │
│     ↓           ↓           ↓       │
│ Database ←→ Redis ←→ Monitoring     │
└─────────────────────────────────────┘
```

## Security Configuration

### Container Security

- **Non-root users** in all containers
- **Read-only filesystems** where possible
- **Minimal base images** (Alpine, distroless)
- **Security scanning** with Trivy
- **Runtime monitoring** with Falco

### Network Security

- **Internal Docker network** with no external access
- **Traefik as single entry point** with rate limiting
- **Security headers** (HSTS, CSP, XSS protection)
- **IP allowlisting** for admin interfaces

### Data Security

- **Encrypted backups** with configurable keys
- **Secret management** with Docker secrets
- **Database connection encryption**
- **API key rotation** capabilities

## Monitoring and Alerting

### Metrics Collection

- **Application metrics**: FastAPI, Celery, AI/RAG pipeline
- **Infrastructure metrics**: Docker, system resources
- **Database metrics**: PostgreSQL performance
- **Security metrics**: Failed authentications, anomalies

### Grafana Dashboards

Access Grafana at `https://grafana.your-domain.com`:

1. **Application Dashboard**: API performance, response times
2. **Infrastructure Dashboard**: CPU, memory, disk usage
3. **AI/RAG Dashboard**: Document processing, model performance
4. **Security Dashboard**: Security events, anomalies

### Alerting Rules

- **High error rates** (>5% 5xx responses)
- **Resource exhaustion** (>90% CPU/memory)
- **Database issues** (connection failures, slow queries)
- **Security incidents** (multiple failed logins, suspicious activity)
- **Backup failures** (missed or failed backups)

## Backup and Recovery

### Automated Backups

The backup service runs automated backups:

- **PostgreSQL**: Daily full dumps with compression
- **Redis**: Daily RDB backups
- **Storage**: Incremental file backups
- **Retention**: 30 days (configurable)

### Backup Locations

```bash
/opt/ai-arbeidsdeskundige/volumes/postgres-backups/
/opt/ai-arbeidsdeskundige/volumes/redis-backups/
/opt/ai-arbeidsdeskundige/volumes/backup-logs/
```

### Disaster Recovery

1. **Database Recovery**:
   ```bash
   # Stop services
   docker-compose -f docker-compose.prod.yml stop backend-api backend-worker
   
   # Restore from backup
   docker-compose -f docker-compose.prod.yml exec db psql -U postgres -c "DROP DATABASE IF EXISTS ai_arbeidsdeskundige_prod;"
   docker-compose -f docker-compose.prod.yml exec db pg_restore -U postgres -d postgres /backups/latest_backup.sql
   
   # Restart services
   docker-compose -f docker-compose.prod.yml start backend-api backend-worker
   ```

2. **Full System Recovery**:
   ```bash
   # Reinstall application
   git clone https://github.com/your-org/ai-arbeidsdeskundige.git /opt/ai-arbeidsdeskundige-new
   
   # Restore configuration
   cp /opt/ai-arbeidsdeskundige/.env.production /opt/ai-arbeidsdeskundige-new/
   
   # Restore data volumes
   docker volume create postgres-data
   docker run --rm -v postgres-data:/data -v /backups:/backup alpine tar xzf /backup/postgres-data.tar.gz -C /data
   
   # Deploy
   cd /opt/ai-arbeidsdeskundige-new
   ./deployment/scripts/deploy.sh production
   ```

## Scaling and Performance

### Horizontal Scaling

Scale individual services:

```bash
# Scale backend API
docker-compose -f docker-compose.prod.yml up -d --scale backend-api=3

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale backend-worker=4
```

### Performance Tuning

1. **Database Optimization**:
   - Connection pooling (configured)
   - Index optimization for vector searches
   - Regular VACUUM and ANALYZE

2. **Application Optimization**:
   - Redis caching for frequent queries
   - Celery task prioritization
   - AI model response caching

3. **Infrastructure Optimization**:
   - SSD storage for database
   - Sufficient RAM for Redis
   - Load balancing across multiple nodes

## Maintenance

### Regular Tasks

```bash
# Weekly maintenance script
#!/bin/bash

# Update system packages
sudo apt update && sudo apt upgrade -y

# Clean Docker images
docker system prune -f

# Rotate logs
docker-compose -f docker-compose.prod.yml exec traefik logrotate /etc/logrotate.conf

# Check backup integrity
./deployment/scripts/verify-backups.sh

# Security scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image --severity HIGH,CRITICAL ai-arbeidsdeskundige-backend:latest
```

### Updates and Rollbacks

```bash
# Update to latest version
git pull origin main
./deployment/scripts/deploy.sh production

# Rollback if needed
git checkout previous-stable-tag
./deployment/scripts/deploy.sh production --force
```

## Troubleshooting

### Common Issues

1. **SSL Certificate Issues**:
   ```bash
   # Check certificate status
   docker-compose -f docker-compose.prod.yml logs traefik
   
   # Force certificate renewal
   docker-compose -f docker-compose.prod.yml restart traefik
   ```

2. **Database Connection Issues**:
   ```bash
   # Check database health
   docker-compose -f docker-compose.prod.yml exec db pg_isready -U postgres
   
   # Check connection limits
   docker-compose -f docker-compose.prod.yml exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
   ```

3. **High Memory Usage**:
   ```bash
   # Check memory usage by service
   docker stats
   
   # Restart memory-intensive services
   docker-compose -f docker-compose.prod.yml restart backend-worker
   ```

### Log Locations

```bash
# Application logs
docker-compose -f docker-compose.prod.yml logs -f backend-api
docker-compose -f docker-compose.prod.yml logs -f backend-worker

# System logs
sudo journalctl -u docker.service -f

# Backup logs
tail -f /opt/ai-arbeidsdeskundige/volumes/backup-logs/backup.log
```

## Support and Maintenance Contacts

- **Technical Support**: tech-support@your-company.com
- **Security Issues**: security@your-company.com
- **Emergency Contact**: +31-XX-XXX-XXXX

## License and Compliance

This deployment configuration ensures compliance with:
- **GDPR** (EU data protection)
- **AVG** (Dutch data protection law)
- **SOC 2** (Security controls)
- **ISO 27001** (Information security management)

---

**Last Updated**: January 29, 2025
**Version**: 1.0.0