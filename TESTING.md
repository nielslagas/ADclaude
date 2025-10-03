# Testing Guide - AI-Arbeidsdeskundige

This document provides comprehensive guidance for testing the AI-Arbeidsdeskundige application, including unit tests, integration tests, performance tests, and end-to-end testing.

## Overview

The AI-Arbeidsdeskundige application has a comprehensive test suite covering:
- **Backend API testing** with pytest and httpx
- **RAG pipeline integration tests** for AI/ML components  
- **Frontend component testing** with Vue Test Utils and Vitest
- **Performance testing** for document processing workflows
- **Automated CI/CD testing** with GitHub Actions

## Quick Start

### Run All Tests
```bash
python run_tests.py
```

### Backend Tests Only
```bash
python run_tests.py --backend-only
```

### Frontend Tests Only
```bash
python run_tests.py --frontend-only
```

### Specific Test Types
```bash
python run_tests.py --test-type unit
python run_tests.py --test-type integration
python run_tests.py --test-type performance
```

## Backend Testing

### Setup
```bash
cd app/backend
pip install -r requirements.txt
```

### Test Structure
```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests
│   ├── api/                 # API endpoint tests
│   │   ├── test_reports.py
│   │   ├── test_documents.py
│   │   └── test_audio.py
│   ├── utils/               # Utility function tests
│   └── models/              # Data model tests
├── integration/             # Integration tests
│   ├── rag/                 # RAG pipeline tests
│   │   └── test_hybrid_rag_pipeline.py
│   ├── document_processing/ # Document workflow tests
│   └── audio_processing/    # Audio workflow tests
├── performance/             # Performance tests
│   └── test_document_processing_performance.py
└── fixtures/                # Test data and mocks
```

### Running Backend Tests

#### Unit Tests
```bash
pytest tests/unit/ -v --cov=app --cov-report=html
```

#### Integration Tests
```bash
pytest tests/integration/ -v --cov=app --cov-append
```

#### Performance Tests
```bash
pytest tests/performance/ -v -m "not slow"
```

#### API Endpoint Testing
```bash
# Test specific endpoint
pytest tests/unit/api/test_reports.py -v

# Test with markers
pytest -m "api and unit" -v
```

### Test Markers

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests  
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.rag` - RAG pipeline tests
- `@pytest.mark.audio` - Audio processing tests
- `@pytest.mark.document` - Document processing tests
- `@pytest.mark.slow` - Long-running tests

### Key Backend Test Features

#### API Testing
```python
async def test_create_report_success(async_client, auth_headers, mock_db_service):
    """Test successful report creation."""
    with patch('app.api.v1.endpoints.reports.verify_token') as mock_auth:
        mock_auth.return_value = {"user_id": "test_user"}
        
        response = await async_client.post(
            "/api/v1/reports/generate",
            headers=auth_headers,
            json={"case_id": "test-case", "template_id": "staatvandienst"}
        )
        
        assert response.status_code == 202
        assert "task_id" in response.json()
```

#### RAG Pipeline Testing
```python
async def test_hybrid_search_integration(mock_llm_provider, mock_vector_store):
    """Test hybrid search functionality."""
    search_service = HybridSearchService(mock_vector_store, mock_llm_provider)
    
    result = await search_service.hybrid_search(
        query="Wat zijn de medische klachten?",
        case_id="test-case",
        max_results=10
    )
    
    assert "combined_results" in result
    assert len(result["combined_results"]) > 0
```

#### Performance Testing
```python
@pytest.mark.performance
async def test_concurrent_document_processing(mock_llm_provider, mock_vector_store):
    """Test system performance under concurrent load."""
    # Process multiple documents concurrently
    tasks = [process_document(doc) for doc in test_documents]
    results = await asyncio.gather(*tasks)
    
    assert all(r["success"] for r in results)
    assert processing_time < 10.0  # Performance requirement
```

## Frontend Testing

### Setup
```bash
cd app/frontend
npm install
```

### Test Structure
```
src/
├── test/
│   ├── setup.ts             # Test configuration
│   └── utils.ts             # Test utilities
├── components/
│   └── __tests__/           # Component tests
│       └── AudioRecorder.test.ts
└── stores/
    └── __tests__/           # Store tests
        └── auth.test.ts
```

### Running Frontend Tests

```bash
# Run all tests
npm run test

# Run with coverage
npm run test:coverage

# Run with UI
npm run test:ui
```

### Component Testing Example

```typescript
import { describe, it, expect, vi } from 'vitest'
import { mountComponent, mockGetUserMedia } from '../../test/utils'
import AudioRecorder from '../audio/AudioRecorder.vue'

describe('AudioRecorder', () => {
  it('starts recording when button clicked', async () => {
    mockGetUserMedia()
    
    const wrapper = mountComponent(AudioRecorder, {
      props: { caseId: 'test-case-id' }
    })
    
    await wrapper.find('button').trigger('click')
    
    expect(wrapper.vm.isRecording).toBe(true)
    expect(wrapper.find('.status-indicator').text()).toContain('Opname:')
  })
})
```

### Store Testing Example

```typescript
import { describe, it, expect } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../auth'

describe('Auth Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('handles successful login', async () => {
    const store = useAuthStore()
    await store.login('test@example.com', 'password')
    
    expect(store.isAuthenticated).toBe(true)
    expect(store.user).toBeTruthy()
  })
})
```

## Test Configuration

### pytest.ini (Backend)
```ini
[tool:pytest]
testpaths = tests
addopts = 
    --strict-markers
    --cov=app
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=80
    --asyncio-mode=auto
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    api: API endpoint tests
    rag: RAG pipeline tests
```

### vitest.config.ts (Frontend)
```typescript
export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'src/test/', '**/*.test.{ts,js}']
    }
  }
})
```

## CI/CD Testing

### GitHub Actions Workflow

The application includes automated testing in GitHub Actions:

- **Backend Tests**: pytest with PostgreSQL and Redis services
- **Frontend Tests**: Vitest with Node.js
- **Code Quality**: Black, flake8, isort, mypy, bandit
- **Security Scanning**: Trivy vulnerability scanner
- **Docker Builds**: Multi-stage build validation
- **Performance Benchmarks**: Automated performance regression testing

### Test Environment Variables

```bash
# Required for testing
export TESTING=true
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test_db
export CELERY_BROKER_URL=redis://localhost:6379/1

# Mock API keys for testing
export ANTHROPIC_API_KEY=test_key_anthropic
export OPENAI_API_KEY=test_key_openai
export GOOGLE_API_KEY=test_key_google
```

## Test Data and Fixtures

### Mock Data Factories

```python
def create_mock_case(overrides={}):
    return {
        "id": "test-case-id",
        "title": "Test Arbeidsdeskundige Case",
        "client_info": {"name": "Jan de Vries"},
        ...overrides
    }
```

### Frontend Test Utilities

```typescript
export const mountComponent = (component, options = {}) => {
  const pinia = createPinia()
  const router = createMockRouter()
  
  return mount(component, {
    global: { plugins: [pinia, router] },
    ...options
  })
}
```

## Performance Testing

### Performance Benchmarks

The application includes comprehensive performance tests:

- **Document Processing**: Concurrent processing of multiple documents
- **RAG Pipeline**: Query processing speed and accuracy
- **Vector Search**: Search performance with large datasets
- **Memory Usage**: Memory consumption during processing
- **Database Performance**: Concurrent database operations

### Performance Metrics

- Document processing: < 5 seconds per document
- RAG queries: < 2 seconds average response time
- Vector search: < 0.5 seconds average search time
- Memory usage: < 500MB additional memory for large documents
- Concurrent users: Support 10+ concurrent users

## Coverage Requirements

### Backend Coverage
- **Minimum**: 80% overall coverage
- **API endpoints**: 90% coverage required
- **RAG pipeline**: 85% coverage required
- **Core utilities**: 90% coverage required

### Frontend Coverage
- **Components**: 80% coverage required
- **Stores**: 85% coverage required
- **Services**: 80% coverage required

## Best Practices

### Writing Tests

1. **Use descriptive test names** that explain what is being tested
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **Mock external dependencies** (APIs, databases, file system)
4. **Test edge cases** and error conditions
5. **Keep tests isolated** and independent
6. **Use fixtures** for reusable test data

### Test Organization

1. **Group related tests** in describe blocks
2. **Use appropriate markers** for test categorization
3. **Separate unit and integration tests**
4. **Mock external services** in unit tests
5. **Use real integrations** only in integration tests

### Performance Testing

1. **Set realistic benchmarks** based on user requirements
2. **Test with representative data** sizes
3. **Monitor memory usage** during tests
4. **Test concurrent scenarios** to identify bottlenecks
5. **Use profiling tools** to identify optimization opportunities

## Debugging Tests

### Backend Debugging
```bash
# Run with verbose output
pytest tests/ -v -s

# Run specific test with debugging
pytest tests/unit/api/test_reports.py::test_create_report -v -s --pdb

# Run with coverage debugging
pytest --cov=app --cov-report=term-missing --cov-report=html -v
```

### Frontend Debugging
```bash
# Run tests in watch mode
npm run test -- --watch

# Run with UI for debugging
npm run test:ui

# Run specific test file
npm run test -- AudioRecorder.test.ts
```

## Common Issues and Solutions

### Backend Issues

**Import Errors**
```python
# Add to conftest.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
```

**Database Connection Issues**
```bash
# Ensure test database is running
docker-compose up -d db
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test_db
```

**Mock Issues**
```python
# Use patch decorator for consistent mocking
@patch('app.utils.llm_provider.get_llm_provider')
def test_with_mock(mock_llm):
    mock_llm.return_value = AsyncMock()
```

### Frontend Issues

**Component Mount Issues**
```typescript
// Ensure all dependencies are mocked
const wrapper = mountComponent(Component, {
  global: {
    mocks: { $api: mockApi },
    stubs: { 'router-link': true }
  }
})
```

**Async Testing Issues**
```typescript
// Wait for async operations
await wrapper.vm.$nextTick()
await flushPromises()
```

## Maintenance

### Regular Tasks

1. **Update test data** when models change
2. **Review coverage reports** and improve low-coverage areas
3. **Update performance benchmarks** as requirements change
4. **Maintain CI/CD pipeline** with latest dependencies
5. **Review and update mocks** when external APIs change

### Monitoring

- Monitor test execution times in CI/CD
- Track coverage trends over time
- Review performance benchmark results
- Monitor test failure rates and flaky tests
- Update dependencies regularly for security

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Vue Test Utils Guide](https://test-utils.vuejs.org/)
- [Vitest Documentation](https://vitest.dev/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Pinia Testing](https://pinia.vuejs.org/cookbook/testing.html)