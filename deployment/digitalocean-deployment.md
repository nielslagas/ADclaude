# DigitalOcean Deployment Guide for AI-Arbeidsdeskundige

## Why DigitalOcean?

### Voordelen:
- **EU Data Centers** (Amsterdam) - GDPR compliant
- **Simpele pricing** - Voorspelbare kosten
- **Managed Kubernetes** - Makkelijk schalen
- **App Platform** - Zero-DevOps optie
- **Spaces** - S3-compatible object storage
- **Managed Database** - PostgreSQL met pgvector support

## Architecture Setup

### Option A: DigitalOcean App Platform (Recommended for Start)
**Kosten: ~€150-250/maand**

```yaml
# app.yaml for DigitalOcean App Platform
name: ai-arbeidsdeskundige
region: ams  # Amsterdam datacenter
domains:
  - domain: arbeidsdeskundige.nl
    type: PRIMARY

services:
  # Backend API
  - name: backend-api
    dockerfile_path: app/backend/Dockerfile.prod
    source_dir: /
    http_port: 8000
    instance_size: professional-xs  # 1 vCPU, 2GB RAM
    instance_count: 2
    health_check:
      http_path: /health
    envs:
      - key: DATABASE_URL
        scope: RUN_TIME
        type: SECRET
      - key: REDIS_URL
        scope: RUN_TIME
        value: ${redis.REDIS_URL}
      - key: ANTHROPIC_API_KEY
        scope: RUN_TIME
        type: SECRET
      - key: OPENAI_API_KEY
        scope: RUN_TIME
        type: SECRET

  # Worker Service
  - name: backend-worker
    dockerfile_path: app/backend/Dockerfile.worker.prod
    source_dir: /
    instance_size: professional-s  # 2 vCPU, 4GB RAM
    instance_count: 2
    envs:
      - key: DATABASE_URL
        scope: RUN_TIME
        type: SECRET
      - key: REDIS_URL
        scope: RUN_TIME
        value: ${redis.REDIS_URL}

  # Frontend
  - name: frontend
    dockerfile_path: app/frontend/Dockerfile.prod
    source_dir: /
    http_port: 80
    instance_size: basic-xxs  # 0.5 vCPU, 512MB RAM
    instance_count: 2
    routes:
      - path: /

databases:
  # PostgreSQL with pgvector
  - name: db
    engine: PG
    version: "15"
    size: db-s-2vcpu-4gb
    num_nodes: 1

  # Redis for caching/queue
  - name: redis
    engine: REDIS
    version: "7"
    size: db-s-1vcpu-1gb
    num_nodes: 1

# Object Storage for documents
jobs:
  - name: setup-spaces
    kind: PRE_DEPLOY
    source_dir: /
    run_command: |
      doctl spaces create arbeidsdeskundige-documents --region ams3
```

### Option B: Kubernetes Cluster (For Scale)
**Kosten: ~€300-500/maand**

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-arbeidsdeskundige
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-arbeidsdeskundige
  template:
    metadata:
      labels:
        app: ai-arbeidsdeskundige
    spec:
      containers:
      - name: backend-api
        image: registry.digitalocean.com/arbeidsdeskundige/backend:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
---
apiVersion: v1
kind: Service
metadata:
  name: ai-arbeidsdeskundige-service
spec:
  selector:
    app: ai-arbeidsdeskundige
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-arbeidsdeskundige-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-arbeidsdeskundige
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Deployment Steps

### 1. Initial Setup
```bash
# Install doctl CLI
brew install doctl  # macOS
# or
snap install doctl  # Linux

# Authenticate
doctl auth init

# Create project
doctl projects create --name ai-arbeidsdeskundige \
  --purpose "Arbeidsdeskundige rapport generatie platform" \
  --environment production
```

### 2. Database Setup
```bash
# Create PostgreSQL database with pgvector
doctl databases create arbeidsdeskundige-db \
  --engine pg \
  --version 15 \
  --size db-s-2vcpu-4gb \
  --region ams3 \
  --num-nodes 1

# Get connection string
doctl databases connection arbeidsdeskundige-db --format json

# Enable pgvector extension
doctl databases sql arbeidsdeskundige-db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 3. Setup Secrets
```bash
# Add secrets to App Platform
doctl apps create-secret arbeidsdeskundige \
  ANTHROPIC_API_KEY="your-key" \
  OPENAI_API_KEY="your-key" \
  JWT_SECRET="your-secret" \
  DATABASE_URL="postgresql://..."
```

### 4. Deploy Application
```bash
# Using App Platform
doctl apps create --spec app.yaml

# Or using Kubernetes
doctl kubernetes cluster create arbeidsdeskundige-cluster \
  --region ams3 \
  --node-pool "name=worker-pool;size=s-2vcpu-4gb;count=3"

kubectl apply -f k8s-deployment.yaml
```

### 5. Setup CDN & SSL
```bash
# Configure Cloudflare for CDN
doctl compute cdn create \
  --origin arbeidsdeskundige.ams3.digitaloceanspaces.com \
  --domain cdn.arbeidsdeskundige.nl

# SSL is automatic with App Platform
```

## Monitoring Setup

### 1. Enable Monitoring
```bash
doctl monitoring alert-policy create \
  --name "High CPU Usage" \
  --type "cpu" \
  --threshold 80 \
  --window 5m \
  --emails "admin@arbeidsdeskundige.nl"
```

### 2. Setup Logging
```yaml
# Add to app.yaml
logs:
  - name: backend-logs
    source_dir: /var/log
    retention_days: 30
```

### 3. Application Insights
```bash
# Install monitoring stack
kubectl apply -f https://github.com/digitalocean/marketplace-kubernetes/raw/master/stacks/prometheus-grafana/yaml/prometheus-grafana.yaml
```

## Security Configuration

### 1. Firewall Rules
```bash
doctl compute firewall create \
  --name arbeidsdeskundige-firewall \
  --inbound-rules "protocol:tcp,ports:443,sources:0.0.0.0/0" \
  --inbound-rules "protocol:tcp,ports:80,sources:0.0.0.0/0" \
  --outbound-rules "protocol:tcp,ports:all,destinations:0.0.0.0/0"
```

### 2. Database Security
```bash
# Restrict database access
doctl databases firewalls append arbeidsdeskundige-db \
  --rule ip_addr:APP_PLATFORM_IP
```

### 3. Backup Configuration
```bash
# Automated backups
doctl databases backups list arbeidsdeskundige-db

# Manual backup
doctl databases backups create arbeidsdeskundige-db
```

## Cost Optimization

### Recommended Setup for Production:
- **App Platform Professional**: €150/month
- **Managed PostgreSQL**: €60/month
- **Redis Cache**: €15/month
- **Spaces (100GB)**: €5/month
- **Bandwidth (1TB)**: €10/month
- **Total**: ~€240/month

### Scaling Options:
- Auto-scaling based on load
- Read replicas for database
- CDN for static assets
- Reserved instances for cost savings

## CI/CD Pipeline

### GitHub Actions Integration
```yaml
# .github/workflows/deploy.yml
name: Deploy to DigitalOcean
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Install doctl
        uses: digitalocean/action-doctl@v2
        with:
          token: ${{ secrets.DIGITALOCEAN_ACCESS_TOKEN }}
      
      - name: Build and push Docker images
        run: |
          docker build -t registry.digitalocean.com/arbeidsdeskundige/backend:${{ github.sha }} ./app/backend
          docker push registry.digitalocean.com/arbeidsdeskundige/backend:${{ github.sha }}
      
      - name: Deploy to App Platform
        run: |
          doctl apps update ${{ secrets.APP_ID }} --spec app.yaml
```

## Maintenance & Support

### Regular Tasks:
1. **Weekly**: Review logs and metrics
2. **Monthly**: Update dependencies
3. **Quarterly**: Security audit
4. **Yearly**: Disaster recovery test

### Support Channels:
- DigitalOcean Support (24/7)
- Community forums
- Managed services available

## Migration from Development

### 1. Export local data
```bash
docker-compose exec db pg_dump -U postgres arbeidsdeskundige > backup.sql
```

### 2. Import to production
```bash
doctl databases sql arbeidsdeskundige-db < backup.sql
```

### 3. Update environment variables
```bash
doctl apps update-env arbeidsdeskundige \
  NODE_ENV=production \
  API_URL=https://api.arbeidsdeskundige.nl
```

## Rollback Strategy

```bash
# List deployments
doctl apps list-deployments arbeidsdeskundige

# Rollback to previous version
doctl apps create-deployment arbeidsdeskundige \
  --rollback deployment-id
```