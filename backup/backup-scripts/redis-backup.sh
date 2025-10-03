#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Redis Backup Script for AI-Arbeidsdeskundige
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 
# Features:
# - Redis RDB and AOF backup
# - Compression and encryption
# - Backup verification
# - Configurable retention
# - Monitoring integration
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -euo pipefail

# Configuration
BACKUP_DIR="/backups/redis"
LOG_FILE="/backups/logs/redis-backup.log"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="redis_backup_${TIMESTAMP}.rdb"
COMPRESSED_FILE="${BACKUP_FILE}.gz"
ENCRYPTED_FILE="${COMPRESSED_FILE}.enc"

# Redis connection parameters
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

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
    log "Checking prerequisites for Redis backup..."
    
    # Check if redis-cli is available
    if ! command -v redis-cli &> /dev/null; then
        error_exit "redis-cli command not found"
    fi
    
    # Check Redis connectivity
    if [ -n "${REDIS_PASSWORD}" ]; then
        auth_param="-a ${REDIS_PASSWORD}"
    else
        auth_param=""
    fi
    
    if ! redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${auth_param} ping &> /dev/null; then
        error_exit "Cannot connect to Redis server"
    fi
    
    # Create backup directory if it doesn't exist
    mkdir -p "${BACKUP_DIR}"
    mkdir -p "$(dirname "${LOG_FILE}")"
    
    log "Prerequisites check completed successfully"
}

# Perform Redis backup
perform_backup() {
    log "Starting Redis backup..."
    
    local backup_path="${BACKUP_DIR}/${BACKUP_FILE}"
    local compressed_path="${BACKUP_DIR}/${COMPRESSED_FILE}"
    local encrypted_path="${BACKUP_DIR}/${ENCRYPTED_FILE}"
    
    # Force Redis to save current state
    log "Forcing Redis BGSAVE..."
    if [ -n "${REDIS_PASSWORD}" ]; then
        auth_param="-a ${REDIS_PASSWORD}"
    else
        auth_param=""
    fi
    
    if ! redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${auth_param} BGSAVE; then
        error_exit "Redis BGSAVE command failed"
    fi
    
    # Wait for background save to complete
    log "Waiting for BGSAVE to complete..."
    while [ "$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${auth_param} LASTSAVE)" == "$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${auth_param} LASTSAVE)" ]; do
        sleep 1
    done
    
    # Copy RDB file from Redis container (this would need to be adapted based on your setup)
    # For now, we'll create a dump using redis-cli
    log "Creating Redis dump..."
    if ! redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${auth_param} --rdb "${backup_path}"; then
        error_exit "Redis dump creation failed"
    fi
    
    # Verify the backup file exists and is not empty
    if [ ! -f "${backup_path}" ] || [ ! -s "${backup_path}" ]; then
        error_exit "Backup file is missing or empty"
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
    
    local backup_size=$(du -h "${backup_final_path}" | cut -f1)
    log "Redis backup completed successfully. File: ${backup_final_path}, Size: ${backup_size}"
}

# Clean up old backups
cleanup_old_backups() {
    log "Cleaning up Redis backups older than ${RETENTION_DAYS} days..."
    
    local deleted_count=0
    while IFS= read -r -d '' file; do
        rm -f "$file"
        deleted_count=$((deleted_count + 1))
        log "Deleted old backup: $(basename "$file")"
    done < <(find "${BACKUP_DIR}" -name "redis_backup_*.rdb.gz*" -type f -mtime +${RETENTION_DAYS} -print0)
    
    if [ $deleted_count -eq 0 ]; then
        log "No old Redis backups to clean up"
    else
        log "Cleaned up ${deleted_count} old Redis backup files"
    fi
}

# Update backup status for monitoring
update_backup_status() {
    local status="$1"
    local message="$2"
    local status_file="/backups/redis/last_backup_status.json"
    
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
    log "Starting Redis backup process"
    log "═══════════════════════════════════════════════════════════════════════════════"
    
    if check_prerequisites && perform_backup && cleanup_old_backups; then
        log "Redis backup process completed successfully"
        update_backup_status "success" "Backup completed successfully"
        exit 0
    else
        log "Redis backup process failed"
        update_backup_status "failed" "Backup process encountered errors"
        exit 1
    fi
}

# Execute main function
main "$@"