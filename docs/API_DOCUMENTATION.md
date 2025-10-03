# AI-Arbeidsdeskundige API Documentation

Complete API documentation for the AI-Arbeidsdeskundige application, including all endpoints, request/response schemas, authentication, and usage examples.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URL and Versioning](#base-url-and-versioning)
4. [Common Response Formats](#common-response-formats)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [API Endpoints](#api-endpoints)
   - [Authentication](#authentication-endpoints)
   - [Cases](#cases-endpoints)
   - [Documents](#documents-endpoints)
   - [Reports](#reports-endpoints)
   - [Audio](#audio-endpoints)
   - [User Profiles](#user-profiles-endpoints)
   - [Comments](#comments-endpoints)
   - [Smart Documents](#smart-documents-endpoints)
   - [Optimized RAG](#optimized-rag-endpoints)
   - [Context-Aware Prompts](#context-aware-prompts-endpoints)
   - [Quality Control](#quality-control-endpoints)
   - [Multi-modal RAG](#multi-modal-rag-endpoints)
   - [Monitoring](#monitoring-endpoints)
8. [Code Examples](#code-examples)
9. [SDK and Libraries](#sdk-and-libraries)

## Overview

The AI-Arbeidsdeskundige API is a RESTful service designed for Dutch labor experts (arbeidsdeskundigen) to create comprehensive reports using advanced AI and RAG (Retrieval-Augmented Generation) technology. The API supports multi-modal document processing, audio transcription, and intelligent report generation.

### Key Features

- **Multi-format Document Processing**: Support for .docx, .txt, and PDF files
- **Audio Transcription**: Whisper-powered speech-to-text conversion
- **Hybrid RAG Pipeline**: Intelligent document classification and processing strategies
- **Multi-Provider LLM Support**: Anthropic Claude, OpenAI GPT, Google Gemini
- **Real-time Monitoring**: Comprehensive performance and quality tracking
- **Professional Report Templates**: Multiple Dutch arbeidsdeskundige report formats

### System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI        │    │   PostgreSQL    │
│   (Vue.js)      │◄──►│   REST API       │◄──►│   with pgvector │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Celery         │    │   Redis         │
                       │   Workers        │◄──►│   (Cache/Queue) │
                       └──────────────────┘    └─────────────────┘
                              │
                       ┌──────────────────┐
                       │   AI/LLM         │
                       │   Providers      │
                       └──────────────────┘
```

## Authentication

### JWT Bearer Token Authentication

All API endpoints (except health checks) require authentication using JWT Bearer tokens.

#### Headers Required
```http
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

#### Token Format
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "exp": 1234567890,
  "iat": 1234567890
}
```

#### Getting a Token
Tokens are obtained through the authentication endpoints (see [Authentication Endpoints](#authentication-endpoints)).

## Base URL and Versioning

- **Base URL**: `https://api.your-domain.com` (production) or `http://localhost:8000` (development)
- **API Version**: v1
- **Full Base Path**: `/api/v1`

## Common Response Formats

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data here
  },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "error": {
    "type": "validation_error",
    "status_code": 400,
    "message": "Invalid input data",
    "details": {
      "field": "case_id",
      "issue": "Must be a valid UUID"
    },
    "path": "/api/v1/documents/upload"
  }
}
```

### Async Task Response
```json
{
  "task_id": "uuid-task-id",
  "status": "PENDING",
  "message": "Task has been queued for processing"
}
```

## Error Handling

### HTTP Status Codes

| Code | Description | Use Case |
|------|-------------|----------|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST |
| 202 | Accepted | Async task started |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Missing or invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Duplicate resource |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Temporary unavailability |

### Error Types

- `authentication_error`: Invalid or missing authentication
- `authorization_error`: Insufficient permissions
- `validation_error`: Invalid request data
- `not_found_error`: Resource not found
- `conflict_error`: Resource conflict
- `rate_limit_error`: Too many requests
- `processing_error`: Task processing failed
- `internal_error`: Server error

## Rate Limiting

### Limits by Endpoint Type

| Endpoint Category | Requests per Minute | Burst Limit |
|-------------------|---------------------|-------------|
| Authentication | 10 | 20 |
| Document Upload | 5 | 10 |
| Report Generation | 3 | 5 |
| Search/Query | 30 | 60 |
| General API | 60 | 120 |

### Rate Limit Headers
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640995200
```

## API Endpoints

### Authentication Endpoints

#### POST /api/v1/auth/login
Login with email and password.

**Request Body:**
```json
{
  "email": "arbeidsdeskundige@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "arbeidsdeskundige@example.com",
    "profile": {
      "name": "Dr. Jan van der Berg",
      "specialization": "Arbeidsdeskundige"
    }
  }
}
```

#### POST /api/v1/auth/refresh
Refresh an existing token.

**Request Body:**
```json
{
  "refresh_token": "refresh_token_here"
}
```

#### POST /api/v1/auth/logout
Logout and invalidate token.

**Headers:** `Authorization: Bearer <token>`

### Cases Endpoints

#### POST /api/v1/cases/
Create a new case.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "title": "Arbeidsdeskundig onderzoek - Jan de Vries",
  "description": "Onderzoek naar arbeidsgeschiktheid na langdurige ziekte",
  "client_info": {
    "name": "Jan de Vries",
    "date_of_birth": "1980-05-15",
    "bsn": "123456789"
  }
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "title": "Arbeidsdeskundig onderzoek - Jan de Vries",
  "description": "Onderzoek naar arbeidsgeschiktheid na langdurige ziekte",
  "status": "active",
  "created_at": "2025-01-29T10:00:00Z",
  "updated_at": "2025-01-29T10:00:00Z",
  "user_id": "uuid",
  "client_info": {
    "name": "Jan de Vries",
    "date_of_birth": "1980-05-15",
    "bsn": "123456789"
  },
  "document_count": 0,
  "report_count": 0
}
```

#### GET /api/v1/cases/
List all cases for the authenticated user.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `limit` (optional): Number of cases to return (default: 50, max: 100)
- `offset` (optional): Number of cases to skip (default: 0)
- `status` (optional): Filter by status (active, completed, archived)

**Response (200):**
```json
[
  {
    "id": "uuid",
    "title": "Arbeidsdeskundig onderzoek - Jan de Vries",
    "status": "active",
    "created_at": "2025-01-29T10:00:00Z",
    "document_count": 3,
    "report_count": 1
  }
]
```

#### GET /api/v1/cases/{case_id}
Get details of a specific case.

**Headers:** `Authorization: Bearer <token>`

**Path Parameters:**
- `case_id`: UUID of the case

**Response (200):**
```json
{
  "id": "uuid",
  "title": "Arbeidsdeskundig onderzoek - Jan de Vries",
  "description": "Onderzoek naar arbeidsgeschiktheid na langdurige ziekte",
  "status": "active",
  "created_at": "2025-01-29T10:00:00Z",
  "updated_at": "2025-01-29T10:00:00Z",
  "client_info": {
    "name": "Jan de Vries",
    "date_of_birth": "1980-05-15",
    "bsn": "123456789"
  },
  "documents": [
    {
      "id": "uuid",
      "filename": "medisch_rapport.docx",
      "type": "medical_report",
      "processed": true,
      "uploaded_at": "2025-01-29T10:30:00Z"
    }
  ],
  "reports": [
    {
      "id": "uuid",
      "template": "staatvandienst",
      "status": "completed",
      "created_at": "2025-01-29T14:00:00Z"
    }
  ]
}
```

#### PUT /api/v1/cases/{case_id}
Update case information.

**Headers:** `Authorization: Bearer <token>`

**Path Parameters:**
- `case_id`: UUID of the case

**Request Body:**
```json
{
  "title": "Updated case title",
  "description": "Updated description",
  "status": "completed"
}
```

#### DELETE /api/v1/cases/{case_id}
Delete a case and all associated data.

**Headers:** `Authorization: Bearer <token>`

**Path Parameters:**
- `case_id`: UUID of the case

**Response (204):** No content

### Documents Endpoints

#### POST /api/v1/documents/upload
Upload a document to a case.

**Headers:** 
- `Authorization: Bearer <token>`
- `Content-Type: multipart/form-data`

**Form Data:**
- `case_id`: UUID of the case
- `file`: Document file (.docx, .txt, .pdf)

**Response (201):**
```json
{
  "id": "uuid",
  "filename": "medisch_rapport.docx",
  "original_filename": "medisch_rapport.docx",
  "file_size": 245760,
  "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "document_type": "medical_report",
  "processing_status": "pending",
  "case_id": "uuid",
  "uploaded_at": "2025-01-29T10:30:00Z",
  "metadata": {
    "pages": 5,
    "word_count": 1250,
    "language": "nl"
  }
}
```

#### GET /api/v1/documents/
List documents for a case.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `case_id`: UUID of the case (required)
- `processed_only`: Boolean, only return processed documents

**Response (200):**
```json
[
  {
    "id": "uuid",
    "filename": "medisch_rapport.docx",
    "document_type": "medical_report",
    "processing_status": "completed",
    "uploaded_at": "2025-01-29T10:30:00Z",
    "processed_at": "2025-01-29T10:32:00Z",
    "metadata": {
      "confidence_score": 0.95,
      "chunk_count": 12,
      "embedding_status": "completed"
    }
  }
]
```

#### GET /api/v1/documents/{document_id}
Get document details and processing status.

**Headers:** `Authorization: Bearer <token>`

**Path Parameters:**
- `document_id`: UUID of the document

**Response (200):**
```json
{
  "id": "uuid",
  "filename": "medisch_rapport.docx",
  "original_filename": "medisch_rapport.docx",
  "document_type": "medical_report",
  "processing_status": "completed",
  "case_id": "uuid",
  "uploaded_at": "2025-01-29T10:30:00Z",
  "processed_at": "2025-01-29T10:32:00Z",
  "content_preview": "Medisch rapport betreffende...",
  "metadata": {
    "pages": 5,
    "word_count": 1250,
    "language": "nl",
    "confidence_score": 0.95,
    "processing_strategy": "hybrid_rag",
    "chunk_count": 12,
    "embedding_dimension": 768
  },
  "processing_log": [
    {
      "timestamp": "2025-01-29T10:30:30Z",
      "stage": "classification",
      "status": "completed",
      "details": "Document classified as medical_report with 0.95 confidence"
    },
    {
      "timestamp": "2025-01-29T10:31:15Z",
      "stage": "chunking",
      "status": "completed",
      "details": "Document split into 12 chunks using intelligent chunking"
    },
    {
      "timestamp": "2025-01-29T10:32:00Z",
      "stage": "embedding",
      "status": "completed",
      "details": "Generated embeddings for all chunks"
    }
  ]
}
```

#### DELETE /api/v1/documents/{document_id}
Delete a document.

**Headers:** `Authorization: Bearer <token>`

**Path Parameters:**
- `document_id`: UUID of the document

**Response (204):** No content

### Reports Endpoints

#### GET /api/v1/reports/templates
Get available report templates.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "templates": {
    "staatvandienst": {
      "id": "staatvandienst",
      "name": "Staatvandienst Format",
      "description": "Standaard rapportage format volgens Staatvandienst richtlijnen",
      "sections": {
        "persoonsgegevens": {
          "title": "Persoonsgegevens",
          "description": "Persoonlijke informatie van de cliënt",
          "required": true
        },
        "werkgever_functie": {
          "title": "Werkgever en Functie",
          "description": "Gegevens over de huidige of laatste werkgever en functie",
          "required": true
        },
        "medische_situatie": {
          "title": "Medische Situatie",
          "description": "Beschrijving van de medische situatie en beperkingen",
          "required": true
        },
        "conclusie": {
          "title": "Conclusie en Advies",
          "description": "Conclusies en aanbevelingen",
          "required": true
        }
      }
    }
  },
  "layout_options": {
    "standaard": {
      "id": "standaard",
      "name": "Standaard Layout",
      "description": "Eenvoudige, klassieke opmaak"
    },
    "modern": {
      "id": "modern",
      "name": "Modern Layout",
      "description": "Moderne, professionele opmaak"
    },
    "professioneel": {
      "id": "professioneel",
      "name": "Professioneel Layout",
      "description": "Formele zakelijke opmaak"
    },
    "compact": {
      "id": "compact",
      "name": "Compact Layout",
      "description": "Ruimtebesparende opmaak"
    }
  }
}
```

#### POST /api/v1/reports/generate
Generate a new report for a case.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "case_id": "uuid",
  "template_id": "staatvandienst",
  "layout_style": "modern",
  "sections": [
    "persoonsgegevens",
    "werkgever_functie",
    "medische_situatie",
    "conclusie"
  ],
  "options": {
    "include_document_references": true,
    "language": "nl",
    "quality_level": "high"
  }
}
```

**Response (202):**
```json
{
  "task_id": "uuid",
  "report_id": "uuid",
  "status": "PENDING",
  "message": "Report generation started",
  "estimated_completion_time": "2025-01-29T10:45:00Z"
}
```

#### GET /api/v1/reports/{report_id}/status
Check report generation status.

**Headers:** `Authorization: Bearer <token>`

**Path Parameters:**
- `report_id`: UUID of the report

**Response (200):**
```json
{
  "report_id": "uuid",
  "status": "IN_PROGRESS",
  "progress": 65,
  "current_section": "medische_situatie",
  "completed_sections": [
    "persoonsgegevens",
    "werkgever_functie"
  ],
  "estimated_completion_time": "2025-01-29T10:45:00Z",
  "quality_metrics": {
    "overall_quality": 0.87,
    "section_scores": {
      "persoonsgegevens": 0.92,
      "werkgever_functie": 0.83
    }
  }
}
```

#### GET /api/v1/reports/{report_id}
Get completed report content.

**Headers:** `Authorization: Bearer <token>`

**Path Parameters:**
- `report_id`: UUID of the report

**Response (200):**
```json
{
  "id": "uuid",
  "case_id": "uuid",
  "template_id": "staatvandienst",
  "layout_style": "modern",
  "status": "completed",
  "created_at": "2025-01-29T10:30:00Z",
  "completed_at": "2025-01-29T10:44:00Z",
  "content": {
    "persoonsgegevens": {
      "title": "Persoonsgegevens",
      "content": "Naam: Jan de Vries\\nGeboortedatum: 15 mei 1980\\n...",
      "word_count": 145,
      "quality_score": 0.92
    },
    "werkgever_functie": {
      "title": "Werkgever en Functie",
      "content": "Huidige werkgever: ABC Bedrijf B.V.\\nFunctie: Software Developer\\n...",
      "word_count": 234,
      "quality_score": 0.83
    }
  },
  "metadata": {
    "total_word_count": 2145,
    "generation_time_seconds": 840,
    "quality_score": 0.87,
    "document_references": 5,
    "llm_provider": "anthropic",
    "model_used": "claude-3-7-sonnet-20250219"
  },
  "export_formats": [
    "html",
    "pdf",
    "docx"
  ]
}
```

#### GET /api/v1/reports/{report_id}/export
Export report in different formats.

**Headers:** `Authorization: Bearer <token>`

**Path Parameters:**
- `report_id`: UUID of the report

**Query Parameters:**
- `format`: Export format (html, pdf, docx)
- `include_references`: Include document references (true/false)

**Response (200):**
- Content-Type varies by format
- Content-Disposition: attachment; filename="rapport_jan_de_vries.pdf"

### Audio Endpoints

#### POST /api/v1/audio/upload
Upload audio file for transcription.

**Headers:** 
- `Authorization: Bearer <token>`
- `Content-Type: multipart/form-data`

**Form Data:**
- `case_id`: UUID of the case
- `file`: Audio file (.mp3, .wav, .m4a, .ogg)

**Response (202):**
```json
{
  "task_id": "uuid",
  "audio_id": "uuid",
  "status": "PENDING",
  "message": "Audio transcription started",
  "estimated_completion_time": "2025-01-29T10:35:00Z"
}
```

#### GET /api/v1/audio/{audio_id}/status
Check transcription status.

**Headers:** `Authorization: Bearer <token>`

**Path Parameters:**
- `audio_id`: UUID of the audio file

**Response (200):**
```json
{
  "audio_id": "uuid",
  "status": "COMPLETED",
  "progress": 100,
  "transcription": {
    "text": "Dit is een gesproken notitie over de arbeidsgeschiktheid van de cliënt...",
    "word_count": 324,
    "duration_seconds": 145,
    "language": "nl",
    "confidence": 0.94
  },
  "processing_time_seconds": 23,
  "model_used": "whisper-large-v2"
}
```

#### GET /api/v1/audio/
List audio files for a case.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `case_id`: UUID of the case (required)

**Response (200):**
```json
[
  {
    "id": "uuid",
    "filename": "interview_jan_de_vries.mp3",
    "case_id": "uuid",
    "status": "completed",
    "duration_seconds": 145,
    "uploaded_at": "2025-01-29T10:15:00Z",
    "transcribed_at": "2025-01-29T10:18:00Z",
    "word_count": 324,
    "language": "nl"
  }
]
```

### User Profiles Endpoints

#### GET /api/v1/profiles/me
Get current user's profile.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "Dr. Jan van der Berg",
  "title": "Arbeidsdeskundige",
  "company": "Arbeidsdeskundig Adviesbureau Nederland",
  "email": "j.vandenberg@adviesnederland.nl",
  "phone": "+31 6 12345678",
  "specializations": [
    "Medische arbeidsdeskundigheid",
    "Reïntegratie",
    "Arbeidsongeschiktheidsbeoordeling"
  ],
  "certifications": [
    {
      "name": "NVAOS Arbeidsdeskundige",
      "issued_date": "2018-06-15",
      "expiry_date": "2025-06-15"
    }
  ],
  "logo": {
    "filename": "company_logo.png",
    "url": "/api/v1/profiles/me/logo",
    "uploaded_at": "2025-01-15T09:30:00Z"
  },
  "created_at": "2025-01-10T08:00:00Z",
  "updated_at": "2025-01-29T10:00:00Z",
  "completion_status": {
    "is_complete": true,
    "missing_fields": [],
    "completion_percentage": 100
  }
}
```

#### PUT /api/v1/profiles/me
Update current user's profile.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "Dr. Jan van der Berg",
  "title": "Senior Arbeidsdeskundige",
  "company": "Arbeidsdeskundig Adviesbureau Nederland",
  "phone": "+31 6 12345678",
  "specializations": [
    "Medische arbeidsdeskundigheid",
    "Reïntegratie",
    "Arbeidsongeschiktheidsbeoordeling"
  ],
  "certifications": [
    {
      "name": "NVAOS Arbeidsdeskundige",
      "issued_date": "2018-06-15",
      "expiry_date": "2025-06-15"
    }
  ]
}
```

#### POST /api/v1/profiles/me/logo
Upload company logo.

**Headers:** 
- `Authorization: Bearer <token>`
- `Content-Type: multipart/form-data`

**Form Data:**
- `file`: Image file (.png, .jpg, .jpeg, .svg)

**Response (200):**
```json
{
  "logo": {
    "filename": "company_logo.png",
    "url": "/api/v1/profiles/me/logo",
    "file_size": 45632,
    "uploaded_at": "2025-01-29T10:30:00Z"
  }
}
```

#### GET /api/v1/profiles/me/logo
Get company logo file.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
- Content-Type: image/png (or appropriate image type)
- Content-Disposition: inline; filename="company_logo.png"

### Smart Documents Endpoints

#### POST /api/v1/smart/classify
Classify a document using AI.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "document_id": "uuid",
  "content_preview": "Medisch rapport betreffende arbeidsgeschiktheid..."
}
```

**Response (200):**
```json
{
  "document_id": "uuid",
  "classification": {
    "document_type": "medical_report",
    "confidence": 0.95,
    "processing_strategy": "hybrid_rag",
    "recommended_sections": [
      "medische_situatie",
      "belastbaarheid"
    ]
  },
  "metadata": {
    "language": "nl",
    "estimated_word_count": 1250,
    "complexity_score": 0.73,
    "medical_terms_count": 45
  }
}
```

#### GET /api/v1/smart/document-types
Get available document types and their characteristics.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "document_types": {
    "medical_report": {
      "name": "Medisch rapport",
      "description": "Medische rapporten en uitslagen",
      "processing_strategy": "hybrid_rag",
      "confidence_threshold": 0.8,
      "relevant_sections": [
        "medische_situatie",
        "belastbaarheid"
      ]
    },
    "cv": {
      "name": "Curriculum Vitae",
      "description": "CV en arbeidsverleden documenten",
      "processing_strategy": "direct_llm",
      "confidence_threshold": 0.85,
      "relevant_sections": [
        "arbeidsverleden",
        "persoonsgegevens"
      ]
    },
    "employer_info": {
      "name": "Werkgeversinformatie",
      "description": "Functieomschrijvingen en werkgeversdocumenten",
      "processing_strategy": "hybrid_rag",
      "confidence_threshold": 0.75,
      "relevant_sections": [
        "werkgever_functie",
        "belasting_huidige_functie"
      ]
    }
  }
}
```

### Optimized RAG Endpoints

#### POST /api/v1/optimized-rag/search
Perform optimized RAG search across case documents.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "query": "Wat zijn de medische klachten van de cliënt?",
  "case_id": "uuid",
  "max_results": 10,
  "include_scores": true,
  "document_types": ["medical_report"],
  "search_strategy": "hybrid"
}
```

**Response (200):**
```json
{
  "query": "Wat zijn de medische klachten van de cliënt?",
  "results": [
    {
      "document_id": "uuid",
      "chunk_id": "uuid",
      "content": "De patiënt klaagt over chronische rugpijn ter hoogte van L4-L5...",
      "relevance_score": 0.94,
      "document_type": "medical_report",
      "metadata": {
        "page": 2,
        "section": "klachten_analyse",
        "word_count": 156
      }
    }
  ],
  "search_metadata": {
    "total_results": 8,
    "search_time_ms": 245,
    "strategy_used": "hybrid",
    "vector_matches": 5,
    "keyword_matches": 3
  },
  "query_enhancement": {
    "original_query": "Wat zijn de medische klachten van de cliënt?",
    "enhanced_query": "medische klachten patiënt symptomen gezondheid beperkingen",
    "query_expansion_applied": true
  }
}
```

#### GET /api/v1/optimized-rag/stats
Get RAG pipeline performance statistics.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `time_range`: Time range for statistics (1h, 24h, 7d, 30d)

**Response (200):**
```json
{
  "time_range": "24h",
  "performance_stats": {
    "total_queries": 1245,
    "average_response_time_ms": 312,
    "success_rate": 0.98,
    "average_relevance_score": 0.84
  },
  "strategy_distribution": {
    "hybrid": 0.65,
    "vector_only": 0.25,
    "keyword_only": 0.10
  },
  "document_type_queries": {
    "medical_report": 456,
    "cv": 234,
    "employer_info": 123,
    "other": 432
  }
}
```

### Monitoring Endpoints

#### GET /api/v1/monitoring/metrics/snapshot
Get real-time performance snapshot.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "timestamp": "2025-01-29T10:30:00Z",
  "system_health": {
    "status": "healthy",
    "uptime_seconds": 86400,
    "memory_usage_mb": 512,
    "cpu_usage_percent": 23
  },
  "api_metrics": {
    "requests_per_minute": 45,
    "average_response_time_ms": 234,
    "error_rate": 0.02,
    "active_connections": 12
  },
  "rag_pipeline": {
    "documents_processed_today": 156,
    "reports_generated_today": 34,
    "average_processing_time_seconds": 23,
    "quality_score": 0.87
  },
  "llm_providers": {
    "anthropic": {
      "status": "healthy",
      "requests_today": 234,
      "average_response_time_ms": 1245,
      "tokens_used_today": 145623
    },
    "openai": {
      "status": "healthy",
      "requests_today": 89,
      "average_response_time_ms": 987,
      "tokens_used_today": 67432
    }
  }
}
```

#### GET /api/v1/monitoring/components/{component}/stats
Get component-specific statistics.

**Headers:** `Authorization: Bearer <token>`

**Path Parameters:**
- `component`: Component name (rag_pipeline, document_processor, vector_store, etc.)

**Query Parameters:**
- `time_range`: Time range (1h, 24h, 7d, 30d)

**Response (200):**
```json
{
  "component": "rag_pipeline",
  "time_range": "24h",
  "statistics": {
    "total_operations": 1245,
    "success_rate": 0.98,
    "average_duration_seconds": 12.5,
    "error_count": 25,
    "performance_trend": "stable"
  },
  "detailed_metrics": {
    "document_classification": {
      "operations": 234,
      "average_confidence": 0.91,
      "accuracy": 0.95
    },
    "chunk_generation": {
      "operations": 234,
      "average_chunks_per_document": 8.5,
      "processing_time_ms": 2341
    },
    "embedding_generation": {
      "operations": 234,
      "batch_size": 10,
      "processing_time_ms": 5678
    }
  }
}
```

#### GET /api/v1/monitoring/quality/dashboard
Get quality control dashboard data.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "quality_overview": {
    "overall_quality_score": 0.87,
    "quality_trend": "improving",
    "reports_generated_today": 34,
    "quality_issues_today": 3
  },
  "section_quality": {
    "persoonsgegevens": {
      "average_score": 0.94,
      "total_sections": 156,
      "low_quality_count": 2
    },
    "medische_situatie": {
      "average_score": 0.85,
      "total_sections": 134,
      "low_quality_count": 8
    }
  },
  "quality_metrics": {
    "factual_accuracy": 0.92,
    "completeness": 0.88,
    "coherence": 0.85,
    "professional_tone": 0.91
  },
  "improvement_suggestions": [
    {
      "area": "medische_situatie",
      "issue": "Medical terminology consistency",
      "suggestion": "Review medical term translations and standardize usage"
    }
  ]
}
```

## Code Examples

### Python (using requests)

```python
import requests
import json

# Authentication
def login(email, password):
    url = "http://localhost:8000/api/v1/auth/login"
    data = {"email": email, "password": password}
    response = requests.post(url, json=data)
    return response.json()["access_token"]

# Upload document
def upload_document(token, case_id, file_path):
    url = "http://localhost:8000/api/v1/documents/upload"
    headers = {"Authorization": f"Bearer {token}"}
    
    with open(file_path, 'rb') as file:
        files = {"file": file}
        data = {"case_id": case_id}
        response = requests.post(url, headers=headers, files=files, data=data)
    
    return response.json()

# Generate report
def generate_report(token, case_id, template_id="staatvandienst"):
    url = "http://localhost:8000/api/v1/reports/generate"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "case_id": case_id,
        "template_id": template_id,
        "layout_style": "modern"
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# Usage example
token = login("arbeidsdeskundige@example.com", "password")
document = upload_document(token, "case-uuid", "medisch_rapport.docx")
report = generate_report(token, "case-uuid")
```

### JavaScript (using axios)

```javascript
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/v1';

// Create API client with interceptors
const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// Add auth token to requests
apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Authentication
export const login = async (email, password) => {
  const response = await apiClient.post('/auth/login', { email, password });
  localStorage.setItem('authToken', response.data.access_token);
  return response.data;
};

// Case management
export const createCase = async (caseData) => {
  const response = await apiClient.post('/cases/', caseData);
  return response.data;
};

export const getCases = async () => {
  const response = await apiClient.get('/cases/');
  return response.data;
};

// Document upload
export const uploadDocument = async (caseId, file) => {
  const formData = new FormData();
  formData.append('case_id', caseId);
  formData.append('file', file);
  
  const response = await apiClient.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

// Report generation
export const generateReport = async (caseId, templateId = 'staatvandienst') => {
  const response = await apiClient.post('/reports/generate', {
    case_id: caseId,
    template_id: templateId,
    layout_style: 'modern'
  });
  return response.data;
};

// Check report status
export const getReportStatus = async (reportId) => {
  const response = await apiClient.get(`/reports/${reportId}/status`);
  return response.data;
};
```

### cURL Examples

```bash
# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "arbeidsdeskundige@example.com", "password": "password"}'

# Create case
curl -X POST "http://localhost:8000/api/v1/cases/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Arbeidsdeskundig onderzoek - Jan de Vries",
    "description": "Onderzoek naar arbeidsgeschiktheid na langdurige ziekte"
  }'

# Upload document
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "case_id=case-uuid-here" \
  -F "file=@medisch_rapport.docx"

# Generate report
curl -X POST "http://localhost:8000/api/v1/reports/generate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "case-uuid-here",
    "template_id": "staatvandienst",
    "layout_style": "modern"
  }'

# Get monitoring snapshot
curl -X GET "http://localhost:8000/api/v1/monitoring/metrics/snapshot" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## SDK and Libraries

### Official Python SDK

```python
# pip install ai-arbeidsdeskundige-sdk
from ai_arbeidsdeskundige import ArbeidsdeskundigeClient

client = ArbeidsdeskundigeClient(
    base_url="http://localhost:8000",
    email="arbeidsdeskundige@example.com",
    password="password"
)

# Create case
case = client.cases.create(
    title="Arbeidsdeskundig onderzoek - Jan de Vries",
    description="Onderzoek naar arbeidsgeschiktheid"
)

# Upload document
document = client.documents.upload(
    case_id=case.id,
    file_path="medisch_rapport.docx"
)

# Generate report
report = client.reports.generate(
    case_id=case.id,
    template="staatvandienst",
    wait_for_completion=True
)

print(f"Report generated: {report.id}")
```

### TypeScript/JavaScript SDK

```typescript
// npm install @ai-arbeidsdeskundige/sdk
import { ArbeidsdeskundigeClient } from '@ai-arbeidsdeskundige/sdk';

const client = new ArbeidsdeskundigeClient({
  baseUrl: 'http://localhost:8000',
  email: 'arbeidsdeskundige@example.com',
  password: 'password'
});

// Create case
const case = await client.cases.create({
  title: 'Arbeidsdeskundig onderzoek - Jan de Vries',
  description: 'Onderzoek naar arbeidsgeschiktheid'
});

// Upload document
const document = await client.documents.upload(case.id, file);

// Generate report
const report = await client.reports.generate({
  caseId: case.id,
  template: 'staatvandienst',
  waitForCompletion: true
});

console.log(`Report generated: ${report.id}`);
```

---

**Last Updated**: January 29, 2025  
**API Version**: v1.0.0  
**Documentation Version**: 1.0.0

For additional support, please contact the development team or refer to the [User Guide](USER_GUIDE.md) and [Developer Documentation](DEVELOPER_GUIDE.md).