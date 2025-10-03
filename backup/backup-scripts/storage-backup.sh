#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Storage Backup Script for AI-Arbeidsdeskundige
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 
# Features:
# - Incremental and full backup of application storage
# - File integrity verification
# - Compression and encryption
# - Configurable retention policies
# - Monitoring and alerting integration
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -euo pipefail

# Configuration
BACKUP_DIR="/backups/storage"
LOG_FILE="/backups/logs/storage-backup.log"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SOURCE_DIR="/backups/storage"
INCREMENTAL_ENABLED="${FILE_BACKUP_INCREMENTAL:-true}"

# Backup file names
FULL_BACKUP_FILE="storage_full_${TIMESTAMP}.tar.gz"
INCREMENTAL_BACKUP_FILE="storage_incremental_${TIMESTAMP}.tar.gz"
SNAPSHOT_FILE="storage_snapshot.txt"

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
    log "Checking prerequisites for storage backup..."
    
    # Check if source directory exists
    if [ ! -d "${SOURCE_DIR}" ]; then
        log "WARNING: Source directory ${SOURCE_DIR} does not exist, creating empty backup"
        mkdir -p "${SOURCE_DIR}"
    fi
    
    # Create backup directory if it doesn't exist
    mkdir -p "${BACKUP_DIR}"
    mkdir -p "$(dirname "${LOG_FILE}")"
    
    # Check available disk space
    local available_space=$(df "${BACKUP_DIR}" | tail -1 | awk '{print $4}')
    local source_size=$(du -s "${SOURCE_DIR}" | awk '{print $1}')
    
    if [ $available_space -lt $((source_size * 2)) ]; then
        log "WARNING: Low disk space. Available: ${available_space}KB, Needed: $((source_size * 2))KB"
    fi
    
    log "Prerequisites check completed successfully"
}

# Determine backup type (full or incremental)
determine_backup_type() {
    local snapshot_path="${BACKUP_DIR}/${SNAPSHOT_FILE}"
    
    if [ "${INCREMENTAL_ENABLED}" = "true" ] && [ -f "${snapshot_path}" ]; then
        # Check if snapshot is recent (within 7 days)
        local snapshot_age=$(find "${snapshot_path}" -mtime +7 | wc -l)
        if [ $snapshot_age -eq 0 ]; then
            echo "incremental"
        else
            echo "full"
        fi
    else
        echo "full"
    fi
}

# Create file snapshot for incremental backups
create_snapshot() {
    local snapshot_path="${BACKUP_DIR}/${SNAPSHOT_FILE}"
    log "Creating file snapshot for incremental backups..."
    
    find "${SOURCE_DIR}" -type f -exec stat -c "%n %Y %s" {} \; > "${snapshot_path}.new"
    mv "${snapshot_path}.new" "${snapshot_path}"
    
    log "File snapshot created successfully"
}

# Get changed files since last snapshot
get_changed_files() {
    local snapshot_path="${BACKUP_DIR}/${SNAPSHOT_FILE}"
    local changed_files_list="/tmp/changed_files_${TIMESTAMP}.txt"
    
    if [ ! -f "${snapshot_path}" ]; then
        # No previous snapshot, backup all files
        find "${SOURCE_DIR}" -type f > "${changed_files_list}"
    else
        # Compare with previous snapshot
        find "${SOURCE_DIR}" -type f -exec stat -c "%n %Y %s" {} \; > "/tmp/current_snapshot_${TIMESTAMP}.txt"
        
        # Find files that are new or changed
        comm -23 <(sort "/tmp/current_snapshot_${TIMESTAMP}.txt") <(sort "${snapshot_path}") | \
            cut -d' ' -f1 > "${changed_files_list}"
        
        rm -f "/tmp/current_snapshot_${TIMESTAMP}.txt"
    fi
    
    echo "${changed_files_list}"
}

# Perform full backup
perform_full_backup() {
    log "Performing full storage backup..."
    
    local backup_path="${BACKUP_DIR}/${FULL_BACKUP_FILE}"
    local encrypted_path="${backup_path}.enc"
    
    # Create tar archive with compression
    log "Creating compressed archive of storage directory..."
    if ! tar -czf "${backup_path}" -C "$(dirname "${SOURCE_DIR}")" "$(basename "${SOURCE_DIR}")"; then
        error_exit "Full backup archive creation failed"
    fi
    
    # Encrypt if encryption key is provided
    if [ -n "${ENCRYPTION_KEY}" ]; then
        log "Encrypting full backup..."
        if ! openssl enc -aes-256-cbc -salt -in "${backup_path}" -out "${encrypted_path}" -k "${ENCRYPTION_KEY}"; then
            error_exit "Full backup encryption failed"
        fi
        rm "${backup_path}"
        backup_final_path="${encrypted_path}"
    else
        backup_final_path="${backup_path}"
    fi
    
    # Create new snapshot
    create_snapshot
    
    local backup_size=$(du -h "${backup_final_path}" | cut -f1)
    log "Full backup completed successfully. File: ${backup_final_path}, Size: ${backup_size}"
    echo "${backup_final_path}"
}

# Perform incremental backup
perform_incremental_backup() {
    log "Performing incremental storage backup..."
    
    local backup_path="${BACKUP_DIR}/${INCREMENTAL_BACKUP_FILE}"
    local encrypted_path="${backup_path}.enc"
    local changed_files_list=$(get_changed_files)
    
    # Check if there are any changed files
    if [ ! -s "${changed_files_list}" ]; then
        log "No files have changed since last backup"
        rm -f "${changed_files_list}"
        return 0
    fi
    
    local changed_count=$(wc -l < "${changed_files_list}")
    log "Found ${changed_count} changed files for incremental backup"
    
    # Create tar archive with only changed files
    log "Creating incremental backup archive..."
    if ! tar -czf "${backup_path}" -T "${changed_files_list}"; then
        error_exit "Incremental backup archive creation failed"
    fi
    
    # Clean up temporary file
    rm -f "${changed_files_list}"
    
    # Encrypt if encryption key is provided
    if [ -n "${ENCRYPTION_KEY}" ]; then
        log "Encrypting incremental backup..."
        if ! openssl enc -aes-256-cbc -salt -in "${backup_path}" -out "${encrypted_path}" -k "${ENCRYPTION_KEY}"; then
            error_exit "Incremental backup encryption failed"
        fi
        rm "${backup_path}"
        backup_final_path="${encrypted_path}"
    else
        backup_final_path="${backup_path}"
    fi
    
    # Update snapshot
    create_snapshot
    
    local backup_size=$(du -h "${backup_final_path}" | cut -f1)
    log "Incremental backup completed successfully. File: ${backup_final_path}, Size: ${backup_size}"
    echo "${backup_final_path}"
}

# Verify backup integrity
verify_backup() {
    local backup_file="$1"
    log "Verifying backup integrity..."
    
    if [ ! -f "${backup_file}" ] || [ ! -s "${backup_file}" ]; then
        error_exit "Backup file is missing or empty"
    fi
    
    # If encrypted, we can't easily verify without decrypting
    if [[ "${backup_file}" == *.enc ]]; then
        log "Backup is encrypted, skipping detailed integrity check"
        return 0
    fi
    
    # Test tar file integrity
    if ! tar -tzf "${backup_file}" > /dev/null 2>&1; then
        error_exit "Backup file integrity check failed"
    fi
    
    log "Backup integrity verification completed successfully"
}

# Clean up old backups
cleanup_old_backups() {
    log "Cleaning up storage backups older than ${RETENTION_DAYS} days..."
    
    local deleted_count=0
    
    # Clean up full backups
    while IFS= read -r -d '' file; do
        rm -f "$file"
        deleted_count=$((deleted_count + 1))
        log "Deleted old full backup: $(basename "$file")"
    done < <(find "${BACKUP_DIR}" -name "storage_full_*.tar.gz*" -type f -mtime +${RETENTION_DAYS} -print0)
    
    # Clean up incremental backups
    while IFS= read -r -d '' file; do
        rm -f "$file"
        deleted_count=$((deleted_count + 1))
        log "Deleted old incremental backup: $(basename "$file")"
    done < <(find "${BACKUP_DIR}" -name "storage_incremental_*.tar.gz*" -type f -mtime +${RETENTION_DAYS} -print0)
    
    if [ $deleted_count -eq 0 ]; then
        log "No old storage backups to clean up"
    else
        log "Cleaned up ${deleted_count} old storage backup files"
    fi
}

# Update backup status for monitoring
update_backup_status() {
    local status="$1"
    local message="$2"
    local backup_type="$3"
    local backup_file="$4"
    local status_file="/backups/storage/last_backup_status.json"
    
    cat > "${status_file}" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "status": "${status}",
    "message": "${message}",
    "backup_type": "${backup_type}",
    "backup_file": "$(basename "${backup_file}")",
    "retention_days": ${RETENTION_DAYS},
    "incremental_enabled": ${INCREMENTAL_ENABLED}
}
EOF
}

# Main execution
main() {
    log "═══════════════════════════════════════════════════════════════════════════════"
    log "Starting storage backup process"
    log "═══════════════════════════════════════════════════════════════════════════════"
    
    if ! check_prerequisites; then
        update_backup_status "failed" "Prerequisites check failed" "unknown" ""
        exit 1
    fi
    
    local backup_type=$(determine_backup_type)
    log "Backup type determined: ${backup_type}"
    
    local backup_file=""
    if [ "${backup_type}" = "full" ]; then
        backup_file=$(perform_full_backup)
    else
        backup_file=$(perform_incremental_backup)
    fi
    
    if [ -n "${backup_file}" ] && verify_backup "${backup_file}" && cleanup_old_backups; then
        log "Storage backup process completed successfully"
        update_backup_status "success" "Backup completed successfully" "${backup_type}" "${backup_file}"
        exit 0
    else
        log "Storage backup process failed"
        update_backup_status "failed" "Backup process encountered errors" "${backup_type}" "${backup_file}"
        exit 1
    fi
}

# Execute main function
main "$@"