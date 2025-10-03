# 🆓 Gratis Deployment Guide - AI-Arbeidsdeskundige

## 🎯 Beste Gratis Opties (2025)

### 1. 🚂 **Railway.app (AANBEVOLEN)**
**Waarom Railway:**
- €5 gratis credit per maand
- PostgreSQL database included
- Automatic HTTPS & custom domains
- Git-based deployments
- Docker support

#### Setup Railway:
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Clone en deploy
git clone <your-repo>
cd ai-arbeidsdeskundige

# Deploy backend
railway new
railway add --service postgresql
railway deploy

# Deploy frontend
railway new frontend
railway deploy
```

**Railway Configuration:**
```toml
# railway.toml
[build]
builder = "dockerfile"
dockerfilePath = "app/backend/Dockerfile.railway"

[deploy]
startCommand = "python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "on_failure"

[[services]]
name = "backend"

[[services]]
name = "postgresql"
```

### 2. 🌐 **Vercel (Frontend) + Supabase (Backend)**

#### Vercel Frontend:
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy frontend
cd app/frontend
vercel --prod
```

#### Supabase Backend:
1. Go to supabase.com
2. Create new project (gratis tot 500MB database)
3. Enable Row Level Security
4. Create API routes in Vercel

**Vercel API Route Example:**
```typescript
// pages/api/reports/generate.ts
import { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!
);

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { case_id, template_id } = req.body;
    
    // Generate report logic here
    const report = await generateReport(case_id, template_id);
    
    res.status(200).json(report);
  } catch (error) {
    res.status(500).json({ error: 'Report generation failed' });
  }
}
```

### 3. 🐙 **GitHub Pages + GitHub Actions**

```yaml
# .github/workflows/deploy-free.yml
name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout
      uses: actions/checkout@v2

    - name: Setup Node.js
      uses: actions/setup-node@v2
      with:
        node-version: '18'

    - name: Install and Build Frontend
      run: |
        cd app/frontend
        npm ci
        npm run build

    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./app/frontend/dist
```

### 4. 🔥 **Firebase (Google)**

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login
firebase login

# Initialize
firebase init

# Deploy
firebase deploy
```

**Firebase Configuration:**
```json
// firebase.json
{
  "hosting": {
    "public": "app/frontend/dist",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      {
        "source": "/api/**",
        "function": "api"
      },
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  },
  "functions": {
    "source": "functions",
    "runtime": "nodejs18"
  }
}
```

## 🏗️ **Free Tier Architecture**

### Option A: Railway (All-in-One)
```
Railway App ($5/month credit):
├── Backend API (Python/FastAPI)
├── PostgreSQL Database  
├── Redis Cache (limited)
├── Worker Process
└── Static Frontend
```

### Option B: Multi-Platform
```
Frontend: Vercel (Free)
Database: Supabase (Free 500MB)
Backend API: Railway/Render (Free tier)
File Storage: GitHub/Cloudinary
```

### Option C: Serverless
```
Frontend: Netlify (Free)
API: Vercel Functions (Free 100GB/month)
Database: PlanetScale (Free 10GB)
Auth: Supabase Auth (Free)
```

## 🚀 **Quick Start: Railway Deployment**

### 1. Prepare Code for Railway

**Create Railway Dockerfile:**
```dockerfile
# app/backend/Dockerfile.railway
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

RUN apt-get update && apt-get install -y \
    gcc postgresql-client curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

CMD python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Update Environment Variables:**
```python
# app/backend/app/core/config.py
import os

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://...")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://...")
    PORT: int = int(os.getenv("PORT", 8000))
    
    # Railway provides these automatically
    RAILWAY_ENVIRONMENT: str = os.getenv("RAILWAY_ENVIRONMENT", "development")
    
settings = Settings()
```

### 2. Deploy Commands

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login to Railway
railway login

# 3. Create new project
railway new ai-arbeidsdeskundige

# 4. Add database
railway add postgresql

# 5. Deploy backend
cd app/backend
railway up

# 6. Deploy frontend (separate service)
railway new ai-arbeidsdeskundige-frontend
cd ../frontend
railway up
```

### 3. Environment Configuration

Via Railway Dashboard of CLI:
```bash
railway variables set ANTHROPIC_API_KEY="your-key"
railway variables set OPENAI_API_KEY="your-key" 
railway variables set JWT_SECRET="your-secret"
```

## 💡 **Free Tier Limitations & Solutions**

### Railway Free Tier:
- **$5 credit/maand** (ongeveer 140 hours uptime)
- **512MB RAM** per service
- **1GB disk space**
- **100GB bandwidth**

**Solutions:**
- Sleep inactive apps (Railway auto-sleeps)
- Optimize images en dependencies
- Use external storage (GitHub, Cloudinary)

### Database Limitations:
- **Railway PostgreSQL**: 1GB storage
- **Supabase**: 500MB, 2 concurrent connections
- **PlanetScale**: 10GB, 1 database

**Solutions:**
- Regular cleanup old data
- Use document compression
- Implement data archiving

### API Rate Limits:
- **Vercel**: 100GB bandwidth/month
- **Netlify**: 100GB bandwidth/month
- **Railway**: Included in $5 credit

## 🔧 **Optimization for Free Tiers**

### 1. Reduce Docker Image Size

```dockerfile
# Multi-stage build
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
CMD python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### 2. Database Optimization

```python
# Use connection pooling
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

engine = create_engine(
    DATABASE_URL,
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False,
    },
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections hourly
    max_overflow=0,     # No overflow for free tiers
    pool_size=2         # Small pool size
)
```

### 3. Caching Strategy

```python
# Simple in-memory cache instead of Redis
from functools import lru_cache
import time

@lru_cache(maxsize=100)
def get_cached_result(key: str):
    # Cache results for 5 minutes
    return expensive_operation(key)
```

## 📊 **Cost Comparison**

| Platform | Monthly Cost | Limitations |
|----------|-------------|-------------|
| **Railway** | $0 ($5 credit) | 140h uptime, 512MB RAM |
| **Vercel + Supabase** | $0 | 100GB bandwidth, 500MB DB |
| **Render Free** | $0 | Sleeps after 15min, 512MB |
| **Heroku** | $0 (discontinued) | - |
| **Firebase** | $0 | 125K reads/day, 20K writes/day |

## 🎯 **Recommended Free Setup**

### For MVP/Testing:
```
✅ Railway.app
- Fullstack deployment
- PostgreSQL included  
- $5/month credit covers development
- Easy scaling to paid plans
```

### For Production Demo:
```
✅ Vercel (Frontend) + Railway (Backend)
- Frontend: Unlimited bandwidth on Vercel
- Backend: Stable with Railway's $5 credit
- Database: Railway PostgreSQL
- Total: ~140 hours uptime/month
```

## 🚀 **Deploy Now (5 Minutes)**

```bash
# Quick Railway deployment
git clone <your-repo>
cd ai-arbeidsdeskundige

# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway new
railway add postgresql  
railway up

# Your app is live! 🎉
```

**Railway will provide URLs like:**
- Backend: `https://ai-arbeidsdeskundige-backend.up.railway.app`
- Frontend: `https://ai-arbeidsdeskundige-frontend.up.railway.app`

## 💰 **Upgrade Path**

Wanneer je uit de gratis tier groeit:

1. **Railway Pro**: $20/maand onbeperkt
2. **Vercel Pro**: $20/maand team features  
3. **Supabase Pro**: $25/maand meer database
4. **Migrate to DigitalOcean**: $150/maand productie-ready

**De gratis opties zijn perfect voor development, testing, en kleine demos!** 🎉