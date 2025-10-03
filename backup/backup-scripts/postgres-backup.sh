#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PostgreSQL Backup Script for AI-Arbeidsdeskundige
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 
# Features:
# - Full database dump with compression
# - Encryption of backup files
# - Configurable retention policies
# - Health check and error handling
# - Logging and monitoring integration
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -euo pipefail

# Configuration
BACKUP_DIR="/backups/postgres"
LOG_FILE="/backups/logs/postgres-backup.log"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="postgres_backup_${TIMESTAMP}.sql"
COMPRESSED_FILE="${BACKUP_FILE}.gz"
ENCRYPTED_FILE="${COMPRESSED_FILE}.enc"

# Database connection parameters
POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-postgres}"

# Backup settings
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites for PostgreSQL backup..."
    
    # Check if pg_dump is available
    if ! command -v pg_dump &> /dev/null; then
        error_exit "pg_dump command not found"
    fi
    
    # Check database connectivity
    if ! PGPASSWORD="${POSTGRES_PASSWORD}" pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" &> /dev/null; then
        error_exit "Cannot connect to PostgreSQL database"
    fi
    
    # Create backup directory if it doesn't exist
    mkdir -p "${BACKUP_DIR}"
    mkdir -p "$(dirname "${LOG_FILE}")"
    
    log "Prerequisites check completed successfully"
}

# Perform database backup
perform_backup() {
    log "Starting PostgreSQL backup for database: ${POSTGRES_DB}"
    
    local backup_path="${BACKUP_DIR}/${BACKUP_FILE}"
    local compressed_path="${BACKUP_DIR}/${COMPRESSED_FILE}"
    local encrypted_path="${BACKUP_DIR}/${ENCRYPTED_FILE}"
    
    # Create database dump
    log "Creating database dump..."
    if ! PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --verbose \
        --no-password \
        --format=custom \
        --compress=9 \
        --file="${backup_path}"; then
        error_exit "Database dump failed"
    fi
    
    # Compress the backup
    log "Compressing backup file..."
    if ! gzip "${backup_path}"; then
        error_exit "Backup compression failed"
    fi
    
    # Encrypt the backup if encryption key is provided
    if [ -n "${ENCRYPTION_KEY}" ]; then
        log "Encrypting backup file..."
        if ! openssl enc -aes-256-cbc -salt -in "${compressed_path}" -out "${encrypted_path}" -k "${ENCRYPTION_KEY}"; then
            error_exit "Backup encryption failed"
        fi
        rm "${compressed_path}"
        backup_final_path="${encrypted_path}"
    else
        backup_final_path="${compressed_path}"
    fi
    
    # Verify backup integrity
    log "Verifying backup integrity..."
    if [ ! -f "${backup_final_path}" ] || [ ! -s "${backup_final_path}" ]; then
        error_exit "Backup file is missing or empty"
    fi
    
    local backup_size=$(du -h "${backup_final_path}" | cut -f1)
    log "Backup completed successfully. File: ${backup_final_path}, Size: ${backup_size}"
}

# Clean up old backups
cleanup_old_backups() {
    log "Cleaning up backups older than ${RETENTION_DAYS} days..."
    
    local deleted_count=0
    while IFS= read -r -d '' file; do
        rm -f "$file"
        deleted_count=$((deleted_count + 1))
        log "Deleted old backup: $(basename "$file")"
    done < <(find "${BACKUP_DIR}" -name "postgres_backup_*.sql.gz*" -type f -mtime +${RETENTION_DAYS} -print0)
    
    if [ $deleted_count -eq 0 ]; then
        log "No old backups to clean up"
    else
        log "Cleaned up ${deleted_count} old backup files"
    fi
}

# Update backup status for monitoring
update_backup_status() {
    local status="$1"
    local message="$2"
    local status_file="/backups/postgres/last_backup_status.json"
    
    cat > "${status_file}" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "status": "${status}",
    "message": "${message}",
    "backup_file": "${BACKUP_FILE}",
    "retention_days": ${RETENTION_DAYS}
}
EOF
}

# Main execution
main() {
    log "═══════════════════════════════════════════════════════════════════════════════"
    log "Starting PostgreSQL backup process"
    log "═══════════════════════════════════════════════════════════════════════════════"
    
    if check_prerequisites && perform_backup && cleanup_old_backups; then
        log "PostgreSQL backup process completed successfully"
        update_backup_status "success" "Backup completed successfully"
        exit 0
    else
        log "PostgreSQL backup process failed"
        update_backup_status "failed" "Backup process encountered errors"
        exit 1
    fi
}

# Execute main function
main "$@"