# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important Guidelines

- Always use the Context7 MCP server for documentation and code snippets
- Use `mcp__context7__resolve-library-id` followed by `mcp__context7__get-library-docs` when looking up documentation

## Project Overview

AI-Arbeidsdeskundige is a Dutch application for generating labor expert reports using AI technologies. The system uses advanced Retrieval-Augmented Generation (RAG) with multi-provider LLM integration (Anthropic Claude, OpenAI GPT, Google Gemini). It helps labor experts create structured, consistent reports by analyzing uploaded documents and audio files.

## Development Commands

### Environment Setup

```bash
# Clone and set up the project
git clone <repository-url>
cd ai-arbeidsdeskundige_claude

# Create environment file from template
cp docker-compose.example.env .env
# Edit .env to add your API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY)
```

### Running the Application

```bash
# Start backend services with Docker
docker-compose up -d

# Start frontend development server
cd app/frontend
npm install
npm run dev
```

### Troubleshooting Common Issues

```bash
# If frontend not loading changes or shows errors
docker-compose restart frontend

# If backend API unhealthy
docker-compose restart backend-api

# Check all services status
docker-compose ps

# If development server not reloading changes
docker-compose down && docker-compose up -d
```

### Testing and Debugging

```bash
# Check backend logs
docker-compose logs -f backend-api
docker-compose logs -f backend-worker

# Test document processing
docker-compose exec backend-api python test_document_processing.py

# Test hybrid RAG functionality
docker-compose exec backend-api python test_hybrid_rag.py

# Test whisper audio transcription
docker-compose exec backend-api python test_whisper.py

# Test AI/RAG improvements
docker-compose exec backend-api python test_smart_classification.py
docker-compose exec backend-api python test_optimized_rag.py
docker-compose exec backend-api python test_quality_control.py
docker-compose exec backend-api python test_multimodal_rag.py

# Test monitoring system
docker-compose exec backend-api python test_monitoring.py
```

### Monitoring and Observability

```bash
# Check RAG pipeline performance
curl http://localhost:8000/api/v1/monitoring/metrics/snapshot

# Get component statistics
curl http://localhost:8000/api/v1/monitoring/components/rag_pipeline/stats

# Check quality dashboard
curl http://localhost:8000/api/v1/monitoring/quality/dashboard

# Monitor token usage
curl http://localhost:8000/api/v1/monitoring/tokens/usage

# Check active alerts
curl http://localhost:8000/api/v1/monitoring/alerts

# Export metrics data
curl http://localhost:8000/api/v1/monitoring/metrics/export > metrics.json
```

### Build and Production

```bash
# Build frontend
cd app/frontend
npm run build

# Stop all services
docker-compose down
```

## Architecture Overview

The application follows a modern microservices architecture with advanced AI/RAG capabilities:

### Backend (Python/FastAPI)

- **API Layer**: RESTful endpoints for document/audio upload, case management, and report generation
- **Processing Pipeline**: Asynchronous document processing with Celery workers
- **Storage**: Document storage with metadata and vector embeddings
- **Hybrid RAG System**: Intelligent document classification and processing strategies
- **Vector Database**: PostgreSQL with pgvector extension for semantic search
- **Monitoring Stack**: Complete observability for all AI/RAG components

### Frontend (Vue.js 3/TypeScript)

- **State Management**: Pinia for state management
- **API Client**: Axios for API communication
- **Authentication**: JWT-based authentication
- **UI Components**: Custom Vue components with responsive design

### AI/RAG Features (2025)

The system includes 6 major AI/RAG improvements:

1. **Smart Document Classification**: Automatic type detection and processing strategy selection
2. **Optimized RAG Pipeline**: Hybrid approach with intelligent chunking and retrieval
3. **Context-Aware Prompts**: Section-specific prompt engineering for optimal results
4. **Automatic Quality Control**: Real-time content validation and improvement
5. **Multi-modal RAG**: Seamless integration of text and audio documents
6. **Pipeline Monitoring**: Complete observability with metrics, alerts, and performance tracking

### Key Technical Features

- **Hybrid RAG**: Smart document classification and processing:
  - Small documents (<20K chars): Direct LLM processing
  - Medium documents (<60K chars): Hybrid approach
  - Large documents (>60K chars): Full RAG pipeline with vector search
  
- **Audio Processing**: Whisper-based transcription for dictated notes

- **User Profiles**: Complete profile management for labor experts with branding options

- **Multi-Provider LLM**: Support for Anthropic Claude, OpenAI GPT, and Google Gemini

## Important Files and Components

### Backend Core

- `app/backend/app/core/config.py`: Configuration settings
- `app/backend/app/utils/llm_provider.py`: Multi-provider LLM interface
- `app/backend/app/utils/vector_store_improved.py`: Hybrid vector storage implementation
- `app/backend/app/utils/hybrid_search.py`: Hybrid search implementation
- `app/backend/app/utils/rag_monitoring.py`: RAG pipeline monitoring and metrics

### AI/RAG Enhancement Components

- `app/backend/app/utils/smart_document_classifier.py`: Document classification and type detection
- `app/backend/app/utils/optimized_rag_pipeline.py`: Optimized RAG pipeline with intelligent chunking
- `app/backend/app/utils/context_aware_prompts.py`: Section-specific prompt engineering
- `app/backend/app/utils/quality_control.py`: Automatic quality control and validation
- `app/backend/app/utils/multimodal_rag.py`: Multi-modal document processing

### Processing Pipeline

- `app/backend/app/tasks/generate_report_tasks/rag_pipeline.py`: Main RAG pipeline
- `app/backend/app/tasks/generate_report_tasks/report_generator.py`: Report generation with AI improvements
- `app/backend/app/tasks/process_document_tasks/hybrid_processor.py`: Document processing
- `app/backend/app/tasks/process_audio_tasks/audio_transcriber.py`: Audio transcription

### API Endpoints

- `app/backend/app/api/v1/endpoints/`: API endpoints for different resources
- `app/backend/app/api/v1/endpoints/monitoring.py`: RAG monitoring and metrics endpoints
- `app/backend/app/api/v1/endpoints/smart_documents.py`: Smart document classification endpoints
- `app/backend/app/api/v1/endpoints/optimized_rag.py`: Optimized RAG endpoints
- `app/backend/app/api/v1/endpoints/context_aware_prompts.py`: Context-aware prompt endpoints
- `app/backend/app/api/v1/endpoints/quality_control.py`: Quality control endpoints
- `app/backend/app/api/v1/endpoints/multimodal_rag.py`: Multi-modal RAG endpoints
- `app/backend/app/api/v1/router.py`: API route definitions

### Frontend Components

- `app/frontend/src/components/`: Reusable Vue components
- `app/frontend/src/components/DocumentProcessingStatus.vue`: Document processing status component
- `app/frontend/src/components/HybridRagVisualizer.vue`: RAG pipeline visualization component
- `app/frontend/src/components/audio/AudioRecorder.vue`: Audio recording component
- `app/frontend/src/views/`: Page views for the application
- `app/frontend/src/stores/`: Pinia stores for state management

## AI/RAG Monitoring API Endpoints

The system includes comprehensive monitoring for all AI/RAG components:

### Performance Monitoring
- `GET /api/v1/monitoring/metrics/snapshot` - Real-time performance snapshot
- `GET /api/v1/monitoring/components/{component}/stats` - Component-specific statistics
- `GET /api/v1/monitoring/metrics/export` - Export metrics data

### Quality Control
- `GET /api/v1/monitoring/quality/dashboard` - Quality dashboard data
- `POST /api/v1/monitoring/quality/feedback` - Submit quality feedback
- `GET /api/v1/monitoring/quality/trends` - Quality trend analysis

### Alert Management
- `GET /api/v1/monitoring/alerts` - Get active alerts
- `POST /api/v1/monitoring/alerts/acknowledge` - Acknowledge alerts
- `GET /api/v1/monitoring/alerts/history` - Alert history

### Token Usage Tracking
- `GET /api/v1/monitoring/tokens/usage` - Token usage statistics
- `GET /api/v1/monitoring/tokens/costs` - Cost estimation and tracking

## Common Workflows

### Document Processing Workflow
1. Upload document via `/api/v1/documents/upload`
2. System automatically classifies document type
3. Intelligent processing strategy selected based on size and type
4. Document processed with hybrid RAG approach
5. Embeddings generated asynchronously in background
6. Real-time monitoring tracks all processing steps

### Report Generation Workflow
1. Select case and relevant documents
2. Generate report via `/api/v1/reports/generate`
3. System uses context-aware prompts for each section
4. Quality control validates generated content
5. Multi-modal integration for text and audio sources
6. Performance metrics tracked throughout process

### Audio Integration Workflow
1. Upload audio file via `/api/v1/audio/upload`
2. Whisper transcription converts speech to text
3. Multi-modal RAG combines audio transcript with document data
4. Integrated processing for comprehensive report generation

### Report Template System
The application includes 4 professionally styled report templates:

#### Template Options
- **Standaard**: Traditional Dutch business format with professional black section headers and blue content headers
- **Modern**: Clean contemporary layout with blue header hierarchy throughout
- **Professioneel**: Formal business style with structured blue subsection headers
- **Compact**: Space-efficient format with smaller blue headers for concise reports

#### Template Styling Features
- **Header Hierarchy**: Professional blue color scheme (#1e40af, #2563eb, #3b82f6)
- **Typography**: Times New Roman, 11pt body text following Dutch document standards
- **Spacing**: Tight professional line spacing (1.25) with proper header margins
- **Content Processing**: Automatic H1 header removal to prevent duplicates with CSS-generated section headers

#### Template System Files
- `app/frontend/src/views/ReportView.vue`: Main report rendering with template system (lines 2590-3050)
- Template CSS classes: `.template-standaard`, `.template-modern`, `.template-professioneel`, `.template-compact`
- Content processing: `processContentForTemplate()` function removes duplicate headers

## Testing and Quality Assurance

The system includes comprehensive testing tools for all AI/RAG components:

- `test_smart_classification.py`: Test document classification accuracy
- `test_optimized_rag.py`: Test RAG pipeline optimization
- `test_context_aware_prompts.py`: Test prompt engineering effectiveness
- `test_quality_control.py`: Test quality control mechanisms
- `test_multimodal_rag.py`: Test multi-modal document processing
- `test_monitoring.py`: Test monitoring and metrics collection

## Performance Optimization

The system includes several performance optimization features:

- **Intelligent Caching**: Multi-layer caching for embeddings and responses
- **Priority Queuing**: Celery priority queues based on document size
- **Resource Management**: Memory-efficient processing with garbage collection
- **Fallback Mechanisms**: Graceful degradation when components are unavailable
- **Load Balancing**: Distributed processing for high-volume scenarios

## Recent Fixes and Updates

### Report Template System Improvements (Latest Session)
- **Fixed Frontend Code Loading**: Resolved Docker container cache issues preventing new code from loading
- **Professional Header Styling**: Implemented blue header hierarchy across all templates (#1e40af, #2563eb, #3b82f6)
- **Header Spacing**: Fixed headers sticking to previous text with proper margin spacing (16pt, 12pt, 8pt)
- **Template Consistency**: Standardized styling across Standaard, Modern, Professioneel, and Compact templates
- **Code Cleanup**: Removed debug console logs and test content from production code

### Known Working Features
- Template system with 4 professional layouts fully functional
- Report generation with proper Dutch arbeidsdeskundige formatting
- Blue header hierarchy working correctly in all templates
- Content processing properly removes duplicate H1 headers
- Frontend development server properly reloads changes after container restart