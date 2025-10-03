# Developer Guide - AI-Arbeidsdeskundige

Comprehensive guide for developers working on the AI-Arbeidsdeskundige application, including architecture, development workflows, and contribution guidelines.

## Table of Contents

1. [Development Setup](#development-setup)
2. [Architecture Overview](#architecture-overview)
3. [Code Structure](#code-structure)
4. [Development Workflow](#development-workflow)
5. [API Development](#api-development)
6. [Frontend Development](#frontend-development)
7. [AI/RAG Components](#airag-components)
8. [Testing Guidelines](#testing-guidelines)
9. [Performance Optimization](#performance-optimization)
10. [Contribution Guidelines](#contribution-guidelines)
11. [Code Standards](#code-standards)
12. [Release Process](#release-process)

## Development Setup

### Prerequisites

- **Docker & Docker Compose**: Container orchestration
- **Node.js 18+**: Frontend development
- **Python 3.11+**: Backend development (for local dev without containers)
- **Git**: Version control
- **VS Code** (recommended): Code editor with extensions

### Recommended VS Code Extensions

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "ms-python.isort",
    "bradlc.vscode-tailwindcss",
    "vue.volar",
    "ms-vscode.vscode-typescript-next",
    "ms-vscode-remote.remote-containers",
    "redhat.vscode-yaml",
    "ms-azuretools.vscode-docker"
  ]
}
```

### Environment Setup

#### 1. Clone and Configure
```bash
# Clone repository
git clone https://github.com/your-org/ai-arbeidsdeskundige.git
cd ai-arbeidsdeskundige

# Create development environment
cp docker-compose.example.env .env

# Configure API keys (see SECURITY.md for best practices)
nano .env
```

#### 2. Development Environment Variables
```bash
# .env for development
NODE_ENV=development
ENVIRONMENT=development

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=postgres
POSTGRES_SERVER=db
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# LLM Providers (at least one required)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-your-development-key
OPENAI_API_KEY=sk-proj-your-development-key
GOOGLE_API_KEY=your-google-development-key

# Development features
DEBUG=true
LOG_LEVEL=DEBUG
ENABLE_CORS=true
RELOAD_ON_CHANGE=true

# Monitoring (optional for development)
METRICS_ENABLED=true
MONITORING_RETENTION_HOURS=1
```

#### 3. Start Development Environment
```bash
# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps

# Check logs
docker-compose logs -f backend-api
```

#### 4. Frontend Development Setup
```bash
# Install dependencies
cd app/frontend
npm install

# Start development server
npm run dev
```

### Development URLs

- **🌐 Frontend**: http://localhost:5173
- **📡 Backend API**: http://localhost:8000
- **📚 API Documentation**: http://localhost:8000/docs
- **🗄️ Database**: localhost:5432
- **🔴 Redis**: localhost:6379
- **📊 Grafana** (if enabled): http://localhost:3000
- **🎯 Prometheus** (if enabled): http://localhost:9090

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Client Applications                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Web Browser   │  │   Mobile App    │  │   API Clients   │  │
│  │   (Vue.js)      │  │   (Future)      │  │   (SDKs)        │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Gateway / Load Balancer                  │
│                          (Traefik)                             │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Application Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Frontend      │  │   Backend API   │  │   Worker Pool   │  │
│  │   (Vue.js 3)    │  │   (FastAPI)     │  │   (Celery)      │  │
│  │                 │  │                 │  │                 │  │
│  │ • Components    │  │ • REST API      │  │ • Document      │  │
│  │ • State (Pinia) │  │ • Authentication│  │   Processing    │  │
│  │ • Routing       │  │ • Validation    │  │ • Report Gen    │  │
│  │ • Services      │  │ • Business Logic│  │ • Audio Trans   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AI/RAG Layer                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Smart Document  │  │ Optimized RAG   │  │ Context-Aware   │  │
│  │ Classification  │  │ Pipeline        │  │ Prompts         │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Quality Control │  │ Multi-modal RAG │  │ Pipeline        │  │
│  │ System          │  │ Processing      │  │ Monitoring      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Data Layer                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   PostgreSQL    │  │     Redis       │  │   File Storage  │  │
│  │                 │  │                 │  │                 │  │
│  │ • Business Data │  │ • Sessions      │  │ • Documents     │  │
│  │ • Vector Store  │  │ • Cache         │  │ • Audio Files   │  │
│  │ • User Data     │  │ • Task Queue    │  │ • Generated     │  │
│  │ • Embeddings    │  │ • Pub/Sub       │  │   Reports       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                 External Services                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Anthropic Claude│  │   OpenAI GPT    │  │ Google Gemini   │  │
│  │                 │  │                 │  │                 │  │
│  │ • Text Gen      │  │ • Text Gen      │  │ • Text Gen      │  │
│  │ • Analysis      │  │ • Embeddings    │  │ • Analysis      │  │
│  │                 │  │ • Whisper       │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow Architecture

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ User    │───▶│ API     │───▶│ Queue   │───▶│ Worker  │
│ Upload  │    │ Gateway │    │ (Redis) │    │ Process │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
                                                   │
                                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AI/RAG Processing Pipeline                    │
│                                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Smart     │─▶│ Optimized   │─▶│ Context     │             │
│  │   Classify  │  │ RAG         │  │ Prompts     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│         │                │                │                    │
│         ▼                ▼                ▼                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Multi-modal │  │ Quality     │  │ Monitoring  │             │
│  │ Processing  │  │ Control     │  │ & Metrics   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Storage                               │
│                                                                │
│  ┌─────────────────┐           ┌─────────────────┐              │
│  │   PostgreSQL    │           │   File System   │              │
│  │                 │           │                 │              │
│  │ • Case Data     │           │ • Original Docs │              │
│  │ • Document Meta │           │ • Audio Files   │              │
│  │ • User Profiles │           │ • Generated     │              │
│  │ • Vector        │           │   Reports       │              │
│  │   Embeddings    │           │ • Logos         │              │
│  │ • Quality       │           │                 │              │
│  │   Metrics       │           │                 │              │
│  └─────────────────┘           └─────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

### Component Interaction Diagram

```
Frontend (Vue.js)
       │
       │ HTTP/REST
       ▼
Backend API (FastAPI)
       │
       ├─ Authentication ────┐
       │                    │
       ├─ Request Validation │
       │                    │
       ├─ Business Logic ────┤
       │                    │
       └─ Response Format ───┘
       │
       │ Task Queue
       ▼
Celery Workers
       │
       ├─ Document Processing
       │    │
       │    ├─ Smart Classification
       │    ├─ Content Extraction  
       │    ├─ Embedding Generation
       │    └─ Vector Storage
       │
       ├─ Report Generation
       │    │
       │    ├─ Context Assembly
       │    ├─ Prompt Generation
       │    ├─ LLM Integration
       │    ├─ Quality Control
       │    └─ Output Formatting
       │
       └─ Audio Processing
            │
            ├─ Whisper Transcription
            ├─ Content Classification
            └─ Multi-modal Integration
```

## Code Structure

### Backend Structure

```
app/backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── celery_worker.py          # Celery configuration
│   │
│   ├── api/                      # API layer
│   │   └── v1/
│   │       ├── endpoints/        # API endpoints
│   │       │   ├── auth.py
│   │       │   ├── cases.py
│   │       │   ├── documents.py
│   │       │   ├── reports.py
│   │       │   ├── audio.py
│   │       │   ├── profiles.py
│   │       │   ├── monitoring.py
│   │       │   └── ...
│   │       └── router.py         # Route registration
│   │
│   ├── core/                     # Core functionality
│   │   ├── config.py            # Configuration management
│   │   ├── security.py          # Authentication & authorization
│   │   └── supabase_client.py   # Supabase integration
│   │
│   ├── db/                      # Database layer
│   │   ├── database_service.py  # Database operations
│   │   ├── init_db.py          # Database initialization
│   │   └── postgres.py         # PostgreSQL utilities
│   │
│   ├── models/                  # Data models
│   │   ├── base.py             # Base model classes
│   │   ├── case.py             # Case models
│   │   ├── document.py         # Document models
│   │   ├── report.py           # Report models
│   │   ├── user_profile.py     # User profile models
│   │   └── ...
│   │
│   ├── tasks/                   # Background tasks
│   │   ├── generate_report_tasks/
│   │   │   ├── rag_pipeline.py
│   │   │   ├── report_generator.py
│   │   │   └── report_generator_hybrid.py
│   │   ├── process_document_tasks/
│   │   │   ├── document_processor.py
│   │   │   ├── document_classifier.py
│   │   │   └── hybrid_processor.py
│   │   └── process_audio_tasks/
│   │       ├── audio_transcriber.py
│   │       └── whisper_direct_test.py
│   │
│   └── utils/                   # Utility modules
│       ├── llm_provider.py      # Multi-provider LLM interface
│       ├── vector_store_improved.py # Vector storage
│       ├── smart_document_classifier.py # AI classification
│       ├── optimized_rag_pipeline.py # RAG optimization
│       ├── context_aware_prompts.py # Prompt engineering
│       ├── quality_controller.py # Quality control
│       ├── multimodal_rag.py   # Multi-modal processing
│       ├── rag_monitoring.py   # Monitoring & metrics
│       ├── hybrid_search.py    # Hybrid search
│       ├── embeddings.py       # Embedding utilities
│       └── document_export.py  # Document export
│
├── migrations/                  # Database migrations
│   └── versions/
├── tests/                      # Test suite
│   ├── unit/
│   ├── integration/
│   └── performance/
├── requirements.txt            # Python dependencies
└── pytest.ini                # Test configuration
```

### Frontend Structure

```
app/frontend/
├── src/
│   ├── main.ts                 # Application entry point
│   ├── App.vue                 # Root component
│   │
│   ├── components/             # Reusable components
│   │   ├── NavBar.vue
│   │   ├── ErrorBoundary.vue
│   │   ├── SkeletonLoader.vue
│   │   ├── NotificationContainer.vue
│   │   ├── LazyImage.vue
│   │   ├── FormField.vue
│   │   ├── CommentSystem.vue
│   │   ├── PerformanceMonitor.vue
│   │   ├── DocumentProcessingStatus.vue
│   │   ├── HybridRagVisualizer.vue
│   │   └── audio/
│   │       └── AudioRecorder.vue
│   │
│   ├── views/                  # Page components
│   │   ├── HomeView.vue
│   │   ├── LoginView.vue
│   │   ├── CasesView.vue
│   │   ├── CaseDetailView.vue
│   │   ├── DocumentView.vue
│   │   ├── ReportView.vue
│   │   ├── AudioRecordingView.vue
│   │   ├── ProfileView.vue
│   │   ├── DebugView.vue
│   │   └── NotFoundView.vue
│   │
│   ├── stores/                 # Pinia state management
│   │   ├── auth.ts            # Authentication state
│   │   ├── case.ts            # Case management
│   │   ├── document.ts        # Document handling
│   │   ├── report.ts          # Report generation
│   │   ├── profile.ts         # User profiles
│   │   └── notification.ts    # Notifications
│   │
│   ├── services/              # API and external services
│   │   ├── api.ts            # Main API client
│   │   └── supabase.ts       # Supabase client
│   │
│   ├── composables/           # Vue 3 composables
│   │   ├── useErrorHandler.ts
│   │   └── useLazyLoad.ts
│   │
│   ├── utils/                 # Utility functions
│   │   └── helpers.ts
│   │
│   ├── types/                 # TypeScript type definitions
│   │   └── index.ts
│   │
│   ├── router/                # Vue Router configuration
│   │   └── index.ts
│   │
│   ├── assets/                # Static assets
│   │   └── main.css
│   │
│   └── test/                  # Test utilities
│       ├── setup.ts
│       └── utils.ts
│
├── public/                    # Public assets
├── package.json              # Node.js dependencies
├── vite.config.ts           # Vite configuration
├── tsconfig.json            # TypeScript configuration
└── vitest.config.ts         # Test configuration
```

## Development Workflow

### Git Workflow

We use **Gitflow** with the following branches:

- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: Individual feature development
- `release/*`: Release preparation
- `hotfix/*`: Emergency fixes

#### Feature Development Workflow

```bash
# 1. Start from develop
git checkout develop
git pull origin develop

# 2. Create feature branch
git checkout -b feature/document-classification-improvement

# 3. Develop and commit
git add .
git commit -m "feat: improve document classification accuracy

- Add confidence scoring for classification results
- Implement fallback classification strategies
- Update classification tests

Closes #123"

# 4. Push and create PR
git push origin feature/document-classification-improvement
# Create Pull Request via GitHub/GitLab
```

#### Commit Message Convention

We follow **Conventional Commits**:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(api): add document batch upload endpoint
fix(rag): resolve vector search timeout issues
docs(readme): update installation instructions
perf(db): optimize document query performance
test(classification): add edge case tests for PDF parsing
```

### Local Development Commands

#### Backend Development
```bash
# Start backend in development mode
docker-compose up -d db redis
cd app/backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
python -m pytest tests/ -v --cov=app

# Format code
python -m black app/
python -m isort app/

# Lint code
python -m flake8 app/
python -m mypy app/

# Run specific AI/RAG tests
python test_smart_classification.py
python test_optimized_rag.py
python test_quality_control.py
```

#### Frontend Development
```bash
# Start frontend development server
cd app/frontend
npm run dev

# Run tests
npm test
npm run test:coverage

# Lint and format
npm run lint
npm run format

# Build for production
npm run build
```

#### Database Operations
```bash
# Create migration
cd app/backend
alembic revision --autogenerate -m "add_document_classification_table"

# Apply migrations
alembic upgrade head

# Access database
docker-compose exec db psql -U postgres
```

### Code Review Process

#### Pull Request Requirements

1. **✅ Checklist before creating PR:**
   - [ ] All tests pass locally
   - [ ] Code follows style guidelines
   - [ ] Documentation updated if needed
   - [ ] No sensitive data in commits
   - [ ] Performance impact considered

2. **📋 PR Template:**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes or documented
```

3. **👥 Review Process:**
   - Minimum 2 approvals required
   - AI/RAG changes require specialist review
   - Security-sensitive changes require security review
   - Performance changes require performance review

## API Development

### Creating New Endpoints

#### 1. Define Models
```python
# app/models/example.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ExampleCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ExampleRead(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

#### 2. Create Endpoint
```python
# app/api/v1/endpoints/examples.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.core.security import verify_token
from app.models.example import ExampleCreate, ExampleRead
from app.db.database_service import db_service

router = APIRouter()

@router.post("/", response_model=ExampleRead, status_code=status.HTTP_201_CREATED)
async def create_example(
    example_data: ExampleCreate,
    user_info = Depends(verify_token)
):
    """
    Create a new example.
    
    Args:
        example_data: Example creation data
        user_info: Authenticated user information
        
    Returns:
        Created example data
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        example = db_service.create_example(
            user_id=user_info["user_id"],
            **example_data.dict()
        )
        return example
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create example: {str(e)}"
        )

@router.get("/", response_model=List[ExampleRead])
async def list_examples(
    user_info = Depends(verify_token),
    limit: int = 50,
    offset: int = 0
):
    """
    List examples for the authenticated user.
    
    Args:
        user_info: Authenticated user information
        limit: Maximum number of examples to return
        offset: Number of examples to skip
        
    Returns:
        List of examples
    """
    return db_service.get_examples(
        user_id=user_info["user_id"],
        limit=limit,
        offset=offset
    )
```

#### 3. Register Router
```python
# app/api/v1/router.py
from app.api.v1.endpoints import examples

api_router.include_router(
    examples.router, 
    prefix="/examples", 
    tags=["examples"]
)
```

### API Best Practices

#### Error Handling
```python
from app.core.exceptions import BusinessLogicError, ValidationError

@router.post("/process")
async def process_document(document_id: str):
    try:
        result = await document_processor.process(document_id)
        return result
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_error", "message": str(e)}
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "business_logic_error", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Unexpected error processing document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )
```

#### Input Validation
```python
from pydantic import BaseModel, validator, Field
from typing import List, Optional

class DocumentUpload(BaseModel):
    case_id: str = Field(..., description="Case ID for the document")
    title: str = Field(..., min_length=1, max_length=200, description="Document title")
    tags: Optional[List[str]] = Field(None, max_items=10, description="Document tags")
    
    @validator('case_id')
    def validate_case_id(cls, v):
        if not v or len(v) < 8:
            raise ValueError('Case ID must be at least 8 characters')
        return v
    
    @validator('tags')
    def validate_tags(cls, v):
        if v:
            for tag in v:
                if len(tag) > 50:
                    raise ValueError('Tag length cannot exceed 50 characters')
        return v
```

#### Response Formatting
```python
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    errors: Optional[List[str]] = None

@router.get("/documents/{document_id}")
async def get_document(document_id: str) -> APIResponse[DocumentRead]:
    document = db_service.get_document(document_id)
    if not document:
        return APIResponse(
            success=False,
            errors=["Document not found"]
        )
    
    return APIResponse(
        success=True,
        data=document,
        message="Document retrieved successfully"
    )
```

## Frontend Development

### Component Development

#### Vue 3 Component Template
```vue
<template>
  <div class="example-component">
    <header class="component-header">
      <h2>{{ title }}</h2>
      <button @click="handleAction" :disabled="loading">
        {{ loading ? 'Processing...' : 'Action' }}
      </button>
    </header>
    
    <main class="component-content">
      <div v-if="error" class="error-message">
        {{ error }}
      </div>
      
      <div v-else-if="loading" class="loading-state">
        <SkeletonLoader />
      </div>
      
      <div v-else class="content">
        <slot :data="data" />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useNotification } from '@/stores/notification'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

// Props
interface Props {
  title: string
  initialData?: any[]
}

const props = withDefaults(defineProps<Props>(), {
  initialData: () => []
})

// Emits
const emit = defineEmits<{
  action: [data: any]
  error: [error: string]
}>()

// Composables
const notification = useNotification()

// State
const loading = ref(false)
const error = ref<string | null>(null)
const data = ref(props.initialData)

// Computed
const hasData = computed(() => data.value.length > 0)

// Methods
const handleAction = async () => {
  try {
    loading.value = true
    error.value = null
    
    // Simulate API call
    const result = await performAction()
    
    data.value = result
    emit('action', result)
    notification.success('Action completed successfully')
    
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Unknown error'
    error.value = errorMessage
    emit('error', errorMessage)
    notification.error(`Action failed: ${errorMessage}`)
  } finally {
    loading.value = false
  }
}

const performAction = async () => {
  // Implementation here
  return []
}

// Lifecycle
onMounted(() => {
  if (!hasData.value) {
    handleAction()
  }
})
</script>

<style scoped>
.example-component {
  @apply bg-white rounded-lg shadow-sm border border-gray-200;
}

.component-header {
  @apply flex justify-between items-center p-4 border-b border-gray-200;
}

.component-content {
  @apply p-4;
}

.error-message {
  @apply text-red-600 bg-red-50 p-3 rounded-md border border-red-200;
}

.loading-state {
  @apply space-y-4;
}
</style>
```

#### Pinia Store Template
```typescript
// stores/example.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Example } from '@/types'
import { api } from '@/services/api'

export const useExampleStore = defineStore('example', () => {
  // State
  const examples = ref<Example[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const exampleCount = computed(() => examples.value.length)
  const hasExamples = computed(() => examples.value.length > 0)
  const activeExamples = computed(() => 
    examples.value.filter(example => example.status === 'active')
  )

  // Actions
  const fetchExamples = async () => {
    try {
      loading.value = true
      error.value = null
      
      const response = await api.get('/examples')
      examples.value = response.data
      
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error'
      throw err
    } finally {
      loading.value = false
    }
  }

  const createExample = async (exampleData: Partial<Example>) => {
    try {
      const response = await api.post('/examples', exampleData)
      examples.value.push(response.data)
      return response.data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create example'
      throw err
    }
  }

  const updateExample = async (id: string, updates: Partial<Example>) => {
    try {
      const response = await api.put(`/examples/${id}`, updates)
      const index = examples.value.findIndex(ex => ex.id === id)
      if (index !== -1) {
        examples.value[index] = response.data
      }
      return response.data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to update example'
      throw err
    }
  }

  const deleteExample = async (id: string) => {
    try {
      await api.delete(`/examples/${id}`)
      examples.value = examples.value.filter(ex => ex.id !== id)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to delete example'
      throw err
    }
  }

  const clearError = () => {
    error.value = null
  }

  return {
    // State
    examples,
    loading,
    error,
    
    // Getters
    exampleCount,
    hasExamples,
    activeExamples,
    
    // Actions
    fetchExamples,
    createExample,
    updateExample,
    deleteExample,
    clearError
  }
})
```

### Frontend Best Practices

#### Composables for Reusable Logic
```typescript
// composables/useApi.ts
import { ref, type Ref } from 'vue'
import { api } from '@/services/api'

export function useApi<T>() {
  const data: Ref<T | null> = ref(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const execute = async (apiCall: () => Promise<T>) => {
    try {
      loading.value = true
      error.value = null
      data.value = await apiCall()
      return data.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error'
      throw err
    } finally {
      loading.value = false
    }
  }

  const reset = () => {
    data.value = null
    error.value = null
    loading.value = false
  }

  return {
    data,
    loading,
    error,
    execute,
    reset
  }
}

// Usage in component
const { data: documents, loading, error, execute } = useApi<Document[]>()

const loadDocuments = () => execute(() => api.get('/documents'))
```

#### Error Boundary Component
```vue
<template>
  <div class="error-boundary">
    <div v-if="hasError" class="error-display">
      <div class="error-icon">⚠️</div>
      <h3>Something went wrong</h3>
      <p>{{ errorMessage }}</p>
      <button @click="retry" class="retry-button">
        Try Again
      </button>
    </div>
    <slot v-else />
  </div>
</template>

<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'

const hasError = ref(false)
const errorMessage = ref('')

onErrorCaptured((error) => {
  hasError.value = true
  errorMessage.value = error.message || 'An unexpected error occurred'
  console.error('Error caught by boundary:', error)
  return false
})

const retry = () => {
  hasError.value = false
  errorMessage.value = ''
}
</script>
```

## AI/RAG Components

### Adding New AI Components

#### 1. Component Structure
```python
# app/utils/example_ai_component.py
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class BaseAIComponent(ABC):
    """Base class for AI components"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics = {}
    
    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """Process input data and return results"""
        pass
    
    def health_check(self) -> bool:
        """Check component health"""
        return True
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get component metrics"""
        return self.metrics

class ExampleAIComponent(BaseAIComponent):
    """Example AI component implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_name = config.get('model_name', 'default')
        self.threshold = config.get('threshold', 0.8)
    
    async def process(self, input_data: str) -> Dict[str, Any]:
        """
        Process input text and return analysis results
        
        Args:
            input_data: Input text to analyze
            
        Returns:
            Analysis results with confidence scores
        """
        try:
            # Start timing
            start_time = time.time()
            
            # Perform analysis
            results = await self._analyze_text(input_data)
            
            # Record metrics
            processing_time = time.time() - start_time
            self.metrics['last_processing_time'] = processing_time
            self.metrics['total_processed'] = self.metrics.get('total_processed', 0) + 1
            
            logger.info(f"Processed text analysis in {processing_time:.2f}s")
            
            return {
                'results': results,
                'confidence': results.get('confidence', 0.0),
                'processing_time': processing_time,
                'model_used': self.model_name
            }
            
        except Exception as e:
            logger.error(f"Error in text analysis: {e}")
            self.metrics['error_count'] = self.metrics.get('error_count', 0) + 1
            raise
    
    async def _analyze_text(self, text: str) -> Dict[str, Any]:
        """Internal analysis method"""
        # Implementation here
        return {
            'analysis_type': 'example',
            'confidence': 0.9,
            'results': {}
        }
```

#### 2. Integration with Monitoring
```python
# Register component with monitoring
from app.utils.rag_monitoring import metrics_collector, ComponentType

class MonitoredAIComponent(BaseAIComponent):
    """AI component with integrated monitoring"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.component_type = ComponentType.CUSTOM
        self.component_name = self.__class__.__name__
    
    async def process(self, input_data: Any) -> Any:
        # Record start metric
        metrics_collector.record_metric(
            MetricType.PROCESSING_STARTED,
            self.component_type,
            1.0,
            metadata={'component': self.component_name}
        )
        
        try:
            start_time = time.time()
            result = await super().process(input_data)
            processing_time = time.time() - start_time
            
            # Record success metrics
            metrics_collector.record_metric(
                MetricType.PROCESSING_TIME,
                self.component_type,
                processing_time,
                metadata={'component': self.component_name}
            )
            
            metrics_collector.record_metric(
                MetricType.PROCESSING_SUCCESS,
                self.component_type,
                1.0,
                metadata={'component': self.component_name}
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            metrics_collector.record_metric(
                MetricType.PROCESSING_ERROR,
                self.component_type,
                1.0,
                metadata={
                    'component': self.component_name,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
            raise
```

#### 3. Testing AI Components
```python
# test_example_ai_component.py
import pytest
from unittest.mock import AsyncMock, patch
from app.utils.example_ai_component import ExampleAIComponent

@pytest.fixture
def ai_component():
    config = {
        'model_name': 'test_model',
        'threshold': 0.75
    }
    return ExampleAIComponent(config)

@pytest.mark.asyncio
async def test_process_success(ai_component):
    """Test successful processing"""
    input_data = "Test input text"
    
    result = await ai_component.process(input_data)
    
    assert 'results' in result
    assert 'confidence' in result
    assert 'processing_time' in result
    assert result['confidence'] >= 0.0
    assert result['confidence'] <= 1.0

@pytest.mark.asyncio
async def test_process_error_handling(ai_component):
    """Test error handling"""
    with patch.object(ai_component, '_analyze_text', side_effect=Exception("Test error")):
        with pytest.raises(Exception, match="Test error"):
            await ai_component.process("test input")
        
        # Check error metrics were recorded
        assert ai_component.metrics.get('error_count', 0) > 0

def test_health_check(ai_component):
    """Test health check"""
    assert ai_component.health_check() is True

def test_metrics(ai_component):
    """Test metrics collection"""
    metrics = ai_component.get_metrics()
    assert isinstance(metrics, dict)
```

## Testing Guidelines

### Test Structure

We use a comprehensive testing strategy:

1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test component interactions
3. **Performance Tests**: Test performance characteristics
4. **End-to-End Tests**: Test complete user workflows

### Backend Testing

#### Unit Test Example
```python
# tests/unit/utils/test_document_classifier.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.utils.smart_document_classifier import SmartDocumentClassifier, DocumentType

@pytest.fixture
def document_classifier():
    return SmartDocumentClassifier()

@pytest.fixture
def sample_document():
    return {
        'id': 'test-doc-id',
        'content': 'This is a medical report about patient symptoms...',
        'filename': 'medical_report.pdf',
        'metadata': {'pages': 3, 'word_count': 500}
    }

@pytest.mark.asyncio
async def test_classify_medical_report(document_classifier, sample_document):
    """Test classification of medical reports"""
    with patch.object(document_classifier, '_analyze_content') as mock_analyze:
        mock_analyze.return_value = {
            'document_type': DocumentType.MEDICAL_REPORT,
            'confidence': 0.95,
            'indicators': ['medical terms', 'patient information']
        }
        
        result = await document_classifier.classify(sample_document)
        
        assert result['document_type'] == DocumentType.MEDICAL_REPORT
        assert result['confidence'] == 0.95
        assert 'indicators' in result
        mock_analyze.assert_called_once_with(sample_document['content'])

@pytest.mark.asyncio
async def test_classify_low_confidence(document_classifier, sample_document):
    """Test handling of low confidence classifications"""
    sample_document['content'] = 'Ambiguous content that could be anything'
    
    with patch.object(document_classifier, '_analyze_content') as mock_analyze:
        mock_analyze.return_value = {
            'document_type': DocumentType.UNKNOWN,
            'confidence': 0.45,
            'indicators': []
        }
        
        result = await document_classifier.classify(sample_document)
        
        assert result['document_type'] == DocumentType.UNKNOWN
        assert result['confidence'] < 0.5
        assert result.get('needs_manual_review', False) is True

def test_confidence_threshold(document_classifier):
    """Test confidence threshold configuration"""
    assert document_classifier.confidence_threshold == 0.8
    
    # Test with custom threshold
    custom_classifier = SmartDocumentClassifier(confidence_threshold=0.9)
    assert custom_classifier.confidence_threshold == 0.9
```

#### Integration Test Example
```python
# tests/integration/rag/test_hybrid_rag_pipeline.py
import pytest
from app.utils.optimized_rag_pipeline import OptimizedRAGPipeline
from app.utils.vector_store_improved import VectorStoreService
from app.utils.llm_provider import get_llm_provider

@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_rag_pipeline(test_db, sample_documents):
    """Test complete RAG pipeline with real components"""
    # Setup
    vector_store = VectorStoreService()
    llm_provider = get_llm_provider()
    rag_pipeline = OptimizedRAGPipeline(vector_store, llm_provider)
    
    # Index test documents
    for doc in sample_documents:
        await vector_store.index_document(doc)
    
    # Test query
    query = "What are the medical conditions mentioned?"
    results = await rag_pipeline.query(
        query=query,
        case_id="test-case-id",
        max_results=5
    )
    
    # Assertions
    assert 'results' in results
    assert len(results['results']) > 0
    assert all('relevance_score' in result for result in results['results'])
    assert results['metadata']['query_time_ms'] > 0
    
    # Test result quality
    top_result = results['results'][0]
    assert top_result['relevance_score'] > 0.7
    assert 'content' in top_result
    assert len(top_result['content']) > 0
```

### Frontend Testing

#### Component Test Example
```typescript
// components/__tests__/AudioRecorder.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import AudioRecorder from '@/components/audio/AudioRecorder.vue'

// Mock MediaRecorder
const mockMediaRecorder = {
  start: vi.fn(),
  stop: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  state: 'inactive'
}

global.MediaRecorder = vi.fn(() => mockMediaRecorder) as any
global.navigator.mediaDevices = {
  getUserMedia: vi.fn().mockResolvedValue(new MediaStream())
} as any

describe('AudioRecorder', () => {
  let wrapper: any
  let pinia: any

  beforeEach(() => {
    pinia = createPinia()
    wrapper = mount(AudioRecorder, {
      props: {
        caseId: 'test-case-id'
      },
      global: {
        plugins: [pinia]
      }
    })
  })

  it('renders correctly', () => {
    expect(wrapper.find('.audio-recorder').exists()).toBe(true)
    expect(wrapper.find('button').text()).toContain('Start Recording')
  })

  it('starts recording when button clicked', async () => {
    const button = wrapper.find('button')
    await button.trigger('click')
    
    expect(mockMediaRecorder.start).toHaveBeenCalled()
    expect(wrapper.vm.isRecording).toBe(true)
    expect(button.text()).toContain('Stop Recording')
  })

  it('handles recording errors gracefully', async () => {
    vi.spyOn(navigator.mediaDevices, 'getUserMedia')
      .mockRejectedValue(new Error('Permission denied'))
    
    const button = wrapper.find('button')
    await button.trigger('click')
    
    expect(wrapper.vm.error).toBeTruthy()
    expect(wrapper.find('.error-message').exists()).toBe(true)
  })

  it('emits recording-complete event with audio data', async () => {
    const mockBlob = new Blob(['audio data'], { type: 'audio/mp3' })
    
    // Simulate recording completion
    wrapper.vm.handleRecordingStop(mockBlob)
    
    expect(wrapper.emitted('recording-complete')).toBeTruthy()
    expect(wrapper.emitted('recording-complete')[0][0]).toEqual({
      audioBlob: mockBlob,
      duration: expect.any(Number)
    })
  })
})
```

## Performance Optimization

### Backend Performance

#### Database Optimization
```python
# Database query optimization
from sqlalchemy import text, Index
from sqlalchemy.orm import selectinload

# Use indexes for frequent queries
Index('idx_documents_case_type', 'case_id', 'document_type')
Index('idx_embeddings_vector', 'embedding', postgresql_using='ivfflat')

# Optimize queries with proper loading
def get_case_with_documents(case_id: str):
    return session.query(Case).options(
        selectinload(Case.documents).selectinload(Document.embeddings)
    ).filter(Case.id == case_id).first()

# Use raw SQL for complex queries
def get_document_similarity(embedding: List[float], limit: int = 10):
    query = text("""
        SELECT d.id, d.title, e.embedding <-> :embedding as distance
        FROM documents d
        JOIN document_embeddings e ON d.id = e.document_id
        ORDER BY distance
        LIMIT :limit
    """)
    return session.execute(query, {
        'embedding': str(embedding),
        'limit': limit
    }).fetchall()
```

#### Caching Strategy
```python
# Redis caching implementation
import redis
import json
import pickle
from functools import wraps
from typing import Optional, Any

redis_client = redis.Redis.from_url(settings.REDIS_URL)

def cache_result(
    key_prefix: str, 
    ttl: int = 3600,
    serialize_method: str = 'json'
):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = redis_client.get(cache_key)
            if cached_result:
                if serialize_method == 'json':
                    return json.loads(cached_result)
                else:
                    return pickle.loads(cached_result)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            if serialize_method == 'json':
                redis_client.setex(cache_key, ttl, json.dumps(result))
            else:
                redis_client.setex(cache_key, ttl, pickle.dumps(result))
            
            return result
        return wrapper
    return decorator

# Usage
@cache_result("document_classification", ttl=7200)
async def classify_document(document_content: str) -> Dict[str, Any]:
    # Expensive classification operation
    return await classifier.classify(document_content)
```

#### Async Processing Optimization
```python
# Optimized async processing
import asyncio
from typing import List, Coroutine, Any

async def process_documents_batch(
    documents: List[Dict], 
    batch_size: int = 5
) -> List[Any]:
    """Process documents in batches to avoid overwhelming resources"""
    results = []
    
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        
        # Process batch concurrently
        tasks = [process_single_document(doc) for doc in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Document processing failed: {result}")
                results.append(None)
            else:
                results.append(result)
        
        # Small delay between batches to prevent resource exhaustion
        await asyncio.sleep(0.1)
    
    return results

async def process_with_semaphore(
    documents: List[Dict], 
    max_concurrent: int = 10
) -> List[Any]:
    """Process documents with concurrency control"""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def bounded_process(doc):
        async with semaphore:
            return await process_single_document(doc)
    
    tasks = [bounded_process(doc) for doc in documents]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

### Frontend Performance

#### Code Splitting and Lazy Loading
```typescript
// Router with lazy loading
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/views/HomeView.vue')
    },
    {
      path: '/cases',
      component: () => import('@/views/CasesView.vue')
    },
    {
      path: '/reports/:id',
      component: () => import('@/views/ReportView.vue'),
      // Route-level code splitting
      meta: { requiresAuth: true }
    }
  ]
})
```

#### Performance Monitoring
```typescript
// Performance monitoring composable
import { ref, onMounted, onUnmounted } from 'vue'

export function usePerformanceMonitor(componentName: string) {
  const metrics = ref({
    mountTime: 0,
    renderTime: 0,
    memoryUsage: 0
  })

  let startTime: number
  let observer: PerformanceObserver | null = null

  onMounted(() => {
    startTime = performance.now()
    
    // Monitor long tasks
    if ('PerformanceObserver' in window) {
      observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.duration > 50) {
            console.warn(`Long task detected in ${componentName}:`, entry.duration)
          }
        }
      })
      observer.observe({ entryTypes: ['longtask'] })
    }
    
    // Measure mount time
    metrics.value.mountTime = performance.now() - startTime
    
    // Measure memory usage if available
    if ('memory' in performance) {
      metrics.value.memoryUsage = (performance as any).memory.usedJSHeapSize
    }
  })

  onUnmounted(() => {
    observer?.disconnect()
  })

  return { metrics }
}
```

## Contribution Guidelines

### Before Contributing

1. **Read Documentation**: Familiarize yourself with the project architecture and conventions
2. **Check Issues**: Look for existing issues or create a new one
3. **Discuss Changes**: For major changes, discuss with maintainers first
4. **Environment Setup**: Ensure your development environment matches the project requirements

### Making Contributions

#### 1. Fork and Clone
```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/ai-arbeidsdeskundige.git
cd ai-arbeidsdeskundige
git remote add upstream https://github.com/ORIGINAL_OWNER/ai-arbeidsdeskundige.git
```

#### 2. Create Feature Branch
```bash
git checkout develop
git pull upstream develop
git checkout -b feature/your-feature-name
```

#### 3. Make Changes
- Follow code standards and conventions
- Write tests for new functionality
- Update documentation as needed
- Test locally before committing

#### 4. Commit and Push
```bash
git add .
git commit -m "feat: add your feature description

- Detailed description of changes
- Why this change is needed
- Any breaking changes

Closes #issue-number"

git push origin feature/your-feature-name
```

#### 5. Create Pull Request
- Use the PR template
- Provide clear description of changes
- Include screenshots for UI changes
- Link relevant issues
- Request appropriate reviewers

### Code Review Guidelines

#### For Contributors
- Respond to feedback promptly
- Make requested changes in new commits
- Keep discussions focused and professional
- Test suggestions before implementing

#### For Reviewers
- Be constructive and specific in feedback
- Focus on code quality, security, and maintainability
- Consider performance implications
- Suggest alternatives when requesting changes
- Approve when ready, even if minor improvements could be made

## Code Standards

### Python Standards

#### Code Formatting
```python
# We use Black for code formatting
# Configuration in pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  migrations
  | venv
  | build
  | dist
)/
'''
```

#### Import Organization
```python
# We use isort for import sorting
# Standard library imports
import os
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# Third-party imports
import redis
import asyncio
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import Column, String, DateTime
from pydantic import BaseModel, validator

# Local application imports
from app.core.config import settings
from app.db.database_service import db_service
from app.utils.llm_provider import get_llm_provider
```

#### Docstring Standards
```python
def process_document(
    document_id: str, 
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process a document using the optimized RAG pipeline.
    
    This function handles the complete document processing workflow including
    classification, chunking, embedding generation, and quality validation.
    
    Args:
        document_id: Unique identifier for the document to process
        options: Optional processing configuration including:
            - quality_threshold: Minimum quality score (default: 0.8)
            - chunk_size: Maximum chunk size in characters (default: 1000)
            - strategy: Processing strategy ('auto', 'hybrid', 'full_rag')
    
    Returns:
        Dictionary containing processing results:
            - success: Boolean indicating if processing succeeded
            - document_type: Classified document type
            - chunks_created: Number of chunks generated
            - embeddings_created: Number of embeddings generated
            - quality_score: Overall quality score (0.0-1.0)
            - processing_time: Time taken in seconds
            - metadata: Additional processing metadata
    
    Raises:
        DocumentNotFoundError: If document_id doesn't exist
        ProcessingError: If document processing fails
        ValidationError: If document content is invalid
    
    Example:
        >>> result = process_document("doc-123", {"quality_threshold": 0.9})
        >>> print(f"Processing completed with quality: {result['quality_score']}")
    """
```

### TypeScript Standards

#### Type Definitions
```typescript
// Strong typing for all interfaces
interface Document {
  readonly id: string
  title: string
  content: string
  documentType: DocumentType
  processingStatus: ProcessingStatus
  createdAt: Date
  updatedAt: Date
  metadata?: DocumentMetadata
}

interface DocumentMetadata {
  fileSize: number
  pageCount?: number
  wordCount?: number
  language?: string
  confidenceScore?: number
}

// Use enums for constants
enum DocumentType {
  MEDICAL_REPORT = 'medical_report',
  CV_RESUME = 'cv_resume',
  EMPLOYER_INFO = 'employer_info',
  LEGAL_DOCUMENT = 'legal_document',
  UNKNOWN = 'unknown'
}

enum ProcessingStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed'
}
```

#### Function Documentation
```typescript
/**
 * Upload and process a document for a specific case
 * 
 * @param caseId - The case ID to associate the document with
 * @param file - The file to upload and process
 * @param options - Optional upload configuration
 * @returns Promise resolving to the created document
 * 
 * @throws {ValidationError} When file type is not supported
 * @throws {NetworkError} When upload fails due to network issues
 * @throws {AuthenticationError} When user is not authenticated
 * 
 * @example
 * ```typescript
 * const document = await uploadDocument('case-123', file, {
 *   autoProcess: true,
 *   qualityThreshold: 0.9
 * })
 * console.log(`Document ${document.id} uploaded successfully`)
 * ```
 */
async function uploadDocument(
  caseId: string,
  file: File,
  options: UploadOptions = {}
): Promise<Document> {
  // Implementation here
}
```

### CSS/SCSS Standards

#### Utility-First with Tailwind
```css
/* Use Tailwind utility classes for consistency */
.document-card {
  @apply bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow;
}

.error-message {
  @apply text-red-600 bg-red-50 border border-red-200 rounded-md p-3 text-sm;
}

/* Custom properties for consistent theming */
:root {
  --color-primary: #3b82f6;
  --color-primary-dark: #1e40af;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
}
```

## Release Process

### Version Management

We follow **Semantic Versioning** (SemVer):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Workflow

#### 1. Prepare Release
```bash
# Create release branch from develop
git checkout develop
git pull origin develop
git checkout -b release/v1.2.0

# Update version numbers
# - package.json (frontend)
# - pyproject.toml (backend)
# - docker-compose.yml (image tags)

# Update CHANGELOG.md
# Add release notes and breaking changes
```

#### 2. Testing and Validation
```bash
# Run full test suite
npm run test  # Frontend tests
python -m pytest  # Backend tests

# Run integration tests
python run_tests.py --test-type integration

# Performance testing
python run_tests.py --test-type performance

# Security scanning
npm audit
bandit -r app/backend/app/
```

#### 3. Release Deployment
```bash
# Merge to main
git checkout main
git merge release/v1.2.0
git tag v1.2.0

# Push to repository
git push origin main
git push origin v1.2.0

# Deploy to production
./deployment/scripts/deploy.sh production
```

#### 4. Post-Release
```bash
# Merge back to develop
git checkout develop
git merge main
git push origin develop

# Delete release branch
git branch -d release/v1.2.0
git push origin --delete release/v1.2.0
```

### Release Checklist

#### Pre-Release
- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version numbers bumped
- [ ] Security scan completed
- [ ] Performance benchmarks met
- [ ] Breaking changes documented

#### Release
- [ ] Release notes prepared
- [ ] Production deployment successful
- [ ] Health checks passing
- [ ] Monitoring alerts configured
- [ ] Rollback plan prepared

#### Post-Release
- [ ] Release announcement sent
- [ ] Documentation published
- [ ] Support team notified
- [ ] Next sprint planned
- [ ] Lessons learned documented

---

## Getting Help

### Documentation Resources
- **📖 User Guide**: [docs/USER_GUIDE.md](USER_GUIDE.md)
- **📡 API Documentation**: [docs/API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **🔧 Troubleshooting**: [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **🧪 Testing Guide**: [TESTING.md](../TESTING.md)

### Community and Support
- **💬 Discussions**: GitHub Discussions for questions and ideas
- **🐛 Bug Reports**: GitHub Issues with bug template
- **✨ Feature Requests**: GitHub Issues with feature template
- **📧 Email Support**: developers@ai-arbeidsdeskundige.nl

### Development Environment Help
- **🆘 Setup Issues**: Check [Environment Troubleshooting](#troubleshooting)
- **🔧 Configuration**: Review [Development Setup](#development-setup)
- **📋 Best Practices**: Follow [Code Standards](#code-standards)

---

**Last Updated**: January 29, 2025  
**Version**: 1.0.0  
**Next Review**: February 29, 2025