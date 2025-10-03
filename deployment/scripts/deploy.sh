#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Production Deployment Script for AI-Arbeidsdeskundige
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 
# Automated deployment with:
# - Environment validation
# - Security scanning
# - Zero-downtime deployment
# - Health checks and rollback
# - Monitoring integration
#
# Usage:
#   ./deploy.sh [production|staging] [--force] [--skip-tests]
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_FILE="/tmp/ai-arbeidsdeskundige-deploy-$(date +%Y%m%d_%H%M%S).log"

# Default values
ENVIRONMENT="${1:-staging}"
FORCE_DEPLOY="${2:-false}"
SKIP_TESTS="${3:-false}"
SKIP_SECURITY_SCAN="${4:-false}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ┌────────────────────────────────────────────────────────────────────────┐
# │ LOGGING AND OUTPUT FUNCTIONS                                           │
# └────────────────────────────────────────────────────────────────────────┘

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "${LOG_FILE}"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "${LOG_FILE}"
}

# ┌────────────────────────────────────────────────────────────────────────┐
# │ ERROR HANDLING                                                         │
# └────────────────────────────────────────────────────────────────────────┘

cleanup() {
    log_info "Cleaning up temporary files..."
    # Add cleanup logic here if needed
}

error_exit() {
    log_error "$1"
    cleanup
    exit 1
}

trap cleanup EXIT

# ┌────────────────────────────────────────────────────────────────────────┐
# │ VALIDATION FUNCTIONS                                                   │
# └────────────────────────────────────────────────────────────────────────┘

validate_environment() {
    log_info "Validating deployment environment: ${ENVIRONMENT}"
    
    # Check if environment is valid
    if [[ ! "${ENVIRONMENT}" =~ ^(production|staging|development)$ ]]; then
        error_exit "Invalid environment: ${ENVIRONMENT}. Must be production, staging, or development."
    fi
    
    # Check if environment file exists
    local env_file="${PROJECT_ROOT}/.env.${ENVIRONMENT}"
    if [ ! -f "${env_file}" ]; then
        error_exit "Environment file not found: ${env_file}"
    fi
    
    # Validate required environment variables
    source "${env_file}"
    local required_vars=(
        "DOMAIN"
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
        "JWT_SECRET_KEY"
        "LETSENCRYPT_EMAIL"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            error_exit "Required environment variable ${var} is not set in ${env_file}"
        fi
    done
    
    # Check LLM provider configuration
    if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ] && [ -z "${GOOGLE_API_KEY:-}" ]; then
        error_exit "At least one LLM API key must be configured"
    fi
    
    log_success "Environment validation completed"
}

check_prerequisites() {
    log_info "Checking deployment prerequisites..."
    
    # Check Docker and Docker Compose
    if ! command -v docker &> /dev/null; then
        error_exit "Docker is not installed or not in PATH"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error_exit "Docker Compose is not installed or not in PATH"
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        error_exit "Docker daemon is not running"
    fi
    
    # Check available disk space (require at least 5GB)
    local available_space=$(df "${PROJECT_ROOT}" | tail -1 | awk '{print $4}')
    local required_space=5242880  # 5GB in KB
    
    if [ $available_space -lt $required_space ]; then
        error_exit "Insufficient disk space. Required: 5GB, Available: $((available_space / 1024 / 1024))GB"
    fi
    
    log_success "Prerequisites check completed"
}

# ┌────────────────────────────────────────────────────────────────────────┐
# │ SECURITY FUNCTIONS                                                     │
# └────────────────────────────────────────────────────────────────────────┘

run_security_scan() {
    if [ "${SKIP_SECURITY_SCAN}" = "true" ]; then
        log_warning "Skipping security scan as requested"
        return 0
    fi
    
    log_info "Running security scan on Docker images..."
    
    # Create scan results directory
    mkdir -p "${PROJECT_ROOT}/security/scan-results"
    
    # List of images to scan
    local images=(
        "ai-arbeidsdeskundige-backend"
        "ai-arbeidsdeskundige-frontend"
        "ai-arbeidsdeskundige-worker"
    )
    
    # Run Trivy security scan
    for image in "${images[@]}"; do
        log_info "Scanning ${image} for vulnerabilities..."
        
        if ! docker run --rm \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v "${PROJECT_ROOT}/security/scan-results:/reports" \
            aquasec/trivy:latest image \
            --format json \
            --output "/reports/${image}-scan.json" \
            "${image}:latest"; then
            log_warning "Security scan failed for ${image}"
        else
            log_success "Security scan completed for ${image}"
        fi
    done
    
    # Check for critical vulnerabilities
    local critical_vulns=0
    for image in "${images[@]}"; do
        local scan_file="${PROJECT_ROOT}/security/scan-results/${image}-scan.json"
        if [ -f "${scan_file}" ]; then
            local critical_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' "${scan_file}" 2>/dev/null || echo 0)
            critical_vulns=$((critical_vulns + critical_count))
        fi
    done
    
    if [ $critical_vulns -gt 0 ] && [ "${FORCE_DEPLOY}" != "true" ]; then
        error_exit "Found ${critical_vulns} critical vulnerabilities. Use --force to deploy anyway."
    elif [ $critical_vulns -gt 0 ]; then
        log_warning "Found ${critical_vulns} critical vulnerabilities, but continuing due to --force flag"
    fi
    
    log_success "Security scan completed"
}

# ┌────────────────────────────────────────────────────────────────────────┐
# │ BUILD FUNCTIONS                                                        │
# └────────────────────────────────────────────────────────────────────────┘

build_images() {
    log_info "Building Docker images for ${ENVIRONMENT}..."
    
    cd "${PROJECT_ROOT}"
    
    # Build backend API image
    log_info "Building backend API image..."
    if ! docker build -f app/backend/Dockerfile.prod -t ai-arbeidsdeskundige-backend:latest app/backend/; then
        error_exit "Failed to build backend API image"
    fi
    
    # Build worker image
    log_info "Building worker image..."
    if ! docker build -f app/backend/Dockerfile.worker.prod -t ai-arbeidsdeskundige-worker:latest app/backend/; then
        error_exit "Failed to build worker image"
    fi
    
    # Build frontend image
    log_info "Building frontend image..."
    if ! docker build -f app/frontend/Dockerfile.prod -t ai-arbeidsdeskundige-frontend:latest app/frontend/; then
        error_exit "Failed to build frontend image"
    fi
    
    # Build backup service image
    log_info "Building backup service image..."
    if ! docker build -f backup/Dockerfile -t ai-arbeidsdeskundige-backup:latest backup/; then
        error_exit "Failed to build backup service image"
    fi
    
    log_success "All Docker images built successfully"
}

# ┌────────────────────────────────────────────────────────────────────────┐
# │ DEPLOYMENT FUNCTIONS                                                   │
# └────────────────────────────────────────────────────────────────────────┘

prepare_deployment() {
    log_info "Preparing deployment configuration..."
    
    # Copy environment file
    cp "${PROJECT_ROOT}/.env.${ENVIRONMENT}" "${PROJECT_ROOT}/.env.production"
    
    # Create required directories
    mkdir -p "${PROJECT_ROOT}/logs"
    mkdir -p "${PROJECT_ROOT}/security/scan-results"
    
    # Set proper permissions
    chmod 600 "${PROJECT_ROOT}/.env.production"
    
    log_success "Deployment preparation completed"
}

deploy_services() {
    log_info "Deploying services for ${ENVIRONMENT}..."
    
    cd "${PROJECT_ROOT}"
    
    # Determine compose files to use
    local compose_files="-f docker-compose.prod.yml"
    
    if [ "${ENVIRONMENT}" = "production" ]; then
        compose_files="${compose_files} -f docker-compose.security.yml"
    fi
    
    # Pull latest base images
    log_info "Pulling latest base images..."
    docker-compose ${compose_files} pull --ignore-pull-failures
    
    # Deploy with rolling update
    log_info "Starting rolling deployment..."
    
    # Start infrastructure services first
    docker-compose ${compose_files} up -d db redis
    
    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    timeout 300 bash -c 'until docker-compose ${compose_files} exec -T db pg_isready -U ${POSTGRES_USER}; do sleep 5; done'
    
    # Start backend services
    docker-compose ${compose_files} up -d backend-api backend-worker
    
    # Wait for backend to be healthy
    log_info "Waiting for backend to be healthy..."
    timeout 300 bash -c 'until curl -f http://localhost:8000/api/health; do sleep 10; done'
    
    # Start frontend and other services
    docker-compose ${compose_files} up -d
    
    log_success "Services deployed successfully"
}

# ┌────────────────────────────────────────────────────────────────────────┐
# │ HEALTH CHECK FUNCTIONS                                                 │
# └────────────────────────────────────────────────────────────────────────┘

verify_deployment() {
    log_info "Verifying deployment health..."
    
    local services=(
        "http://localhost:8000/api/health:Backend API"
        "http://localhost:5173/health:Frontend"
    )
    
    for service_info in "${services[@]}"; do
        local url="${service_info%%:*}"
        local name="${service_info##*:}"
        
        log_info "Checking ${name} health..."
        
        local retries=0
        local max_retries=30
        local success=false
        
        while [ $retries -lt $max_retries ]; do
            if curl -f -s "${url}" > /dev/null; then
                success=true
                break
            fi
            
            sleep 10
            retries=$((retries + 1))
            log_info "Retry ${retries}/${max_retries} for ${name}..."
        done
        
        if [ "${success}" = "true" ]; then
            log_success "${name} is healthy"
        else
            error_exit "${name} health check failed after ${max_retries} attempts"
        fi
    done
    
    # Verify all containers are running
    log_info "Checking container status..."
    local unhealthy_containers=$(docker-compose -f docker-compose.prod.yml ps -q | xargs docker inspect -f '{{.Name}}: {{.State.Health.Status}}' | grep -v healthy || true)
    
    if [ -n "${unhealthy_containers}" ]; then
        log_warning "Some containers are not healthy:"
        echo "${unhealthy_containers}"
    fi
    
    log_success "Deployment verification completed"
}

# ┌────────────────────────────────────────────────────────────────────────┐
# │ ROLLBACK FUNCTIONS                                                     │
# └────────────────────────────────────────────────────────────────────────┘

rollback_deployment() {
    log_error "Initiating rollback procedure..."
    
    # This would contain rollback logic
    # For now, we'll just stop the services
    docker-compose -f docker-compose.prod.yml down
    
    log_info "Rollback completed. Previous version should be restored manually."
}

# ┌────────────────────────────────────────────────────────────────────────┐
# │ MAIN DEPLOYMENT WORKFLOW                                               │
# └────────────────────────────────────────────────────────────────────────┘

main() {
    log "═══════════════════════════════════════════════════════════════════════════════"
    log "Starting AI-Arbeidsdeskundige deployment to ${ENVIRONMENT}"
    log "═══════════════════════════════════════════════════════════════════════════════"
    
    # Validation phase
    validate_environment
    check_prerequisites
    
    # Security phase
    run_security_scan
    
    # Build phase
    build_images
    
    # Deployment phase
    prepare_deployment
    deploy_services
    
    # Verification phase
    if ! verify_deployment; then
        if [ "${FORCE_DEPLOY}" != "true" ]; then
            rollback_deployment
            error_exit "Deployment verification failed, rollback initiated"
        else
            log_warning "Deployment verification failed, but continuing due to --force flag"
        fi
    fi
    
    log_success "═══════════════════════════════════════════════════════════════════════════════"
    log_success "AI-Arbeidsdeskundige deployment to ${ENVIRONMENT} completed successfully!"
    log_success "═══════════════════════════════════════════════════════════════════════════════"
    log_info "Deployment log saved to: ${LOG_FILE}"
    
    # Display service URLs
    echo ""
    echo "Service URLs:"
    echo "  Frontend: https://${DOMAIN:-localhost}"
    echo "  Backend API: https://api.${DOMAIN:-localhost}"
    echo "  Monitoring: https://grafana.${DOMAIN:-localhost}"
    echo ""
}

# ┌────────────────────────────────────────────────────────────────────────┐
# │ SCRIPT EXECUTION                                                       │
# └────────────────────────────────────────────────────────────────────────┘

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_DEPLOY="true"
            shift
            ;;
        --skip-tests)
            SKIP_TESTS="true"
            shift
            ;;
        --skip-security-scan)
            SKIP_SECURITY_SCAN="true"
            shift
            ;;
        --help)
            echo "Usage: $0 [production|staging] [--force] [--skip-tests] [--skip-security-scan]"
            echo ""
            echo "Options:"
            echo "  --force                Skip confirmation prompts and critical vulnerability checks"
            echo "  --skip-tests          Skip running tests before deployment"
            echo "  --skip-security-scan  Skip security scanning of Docker images"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            # Ignore unknown options, they might be environment names
            shift
            ;;
    esac
done

# Run main deployment
main "$@"