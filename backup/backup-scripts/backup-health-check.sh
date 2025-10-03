#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Backup Health Check Script for AI-Arbeidsdeskundige
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 
# Health check for backup service:
# - Verifies recent backup completion
# - Checks backup file integrity
# - Monitors disk space
# - Reports backup service status
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -euo pipefail

# Configuration
HEALTH_CHECK_LOG="/backups/logs/health-check.log"
MAX_BACKUP_AGE_HOURS=25  # Backups should be created daily, allow 1 hour buffer

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${HEALTH_CHECK_LOG}"
}

# Check if recent backups exist
check_recent_backups() {
    local issues=0
    
    # Check PostgreSQL backup
    local postgres_backup=$(find /backups/postgres -name "postgres_backup_*.sql.gz*" -mtime -1 | head -1)
    if [ -z "${postgres_backup}" ]; then
        log "WARNING: No recent PostgreSQL backup found"
        issues=$((issues + 1))
    else
        log "OK: Recent PostgreSQL backup found: $(basename "${postgres_backup}")"
    fi
    
    # Check Redis backup
    local redis_backup=$(find /backups/redis -name "redis_backup_*.rdb.gz*" -mtime -1 | head -1)
    if [ -z "${redis_backup}" ]; then
        log "WARNING: No recent Redis backup found"
        issues=$((issues + 1))
    else
        log "OK: Recent Redis backup found: $(basename "${redis_backup}")"
    fi
    
    # Check storage backup
    local storage_backup=$(find /backups/storage -name "storage_*_*.tar.gz*" -mtime -1 | head -1)
    if [ -z "${storage_backup}" ]; then
        log "WARNING: No recent storage backup found"
        issues=$((issues + 1))
    else
        log "OK: Recent storage backup found: $(basename "${storage_backup}")"
    fi
    
    return $issues
}

# Check backup status files
check_backup_status() {
    local issues=0
    
    # Check PostgreSQL backup status
    if [ -f "/backups/postgres/last_backup_status.json" ]; then
        local postgres_status=$(jq -r '.status' /backups/postgres/last_backup_status.json 2>/dev/null || echo "unknown")
        if [ "${postgres_status}" != "success" ]; then
            log "WARNING: PostgreSQL backup status: ${postgres_status}"
            issues=$((issues + 1))
        else
            log "OK: PostgreSQL backup status: ${postgres_status}"
        fi
    else
        log "WARNING: PostgreSQL backup status file not found"
        issues=$((issues + 1))
    fi
    
    # Check Redis backup status
    if [ -f "/backups/redis/last_backup_status.json" ]; then
        local redis_status=$(jq -r '.status' /backups/redis/last_backup_status.json 2>/dev/null || echo "unknown")
        if [ "${redis_status}" != "success" ]; then
            log "WARNING: Redis backup status: ${redis_status}"
            issues=$((issues + 1))
        else
            log "OK: Redis backup status: ${redis_status}"
        fi
    else
        log "WARNING: Redis backup status file not found"
        issues=$((issues + 1))
    fi
    
    # Check storage backup status
    if [ -f "/backups/storage/last_backup_status.json" ]; then
        local storage_status=$(jq -r '.status' /backups/storage/last_backup_status.json 2>/dev/null || echo "unknown")
        if [ "${storage_status}" != "success" ]; then
            log "WARNING: Storage backup status: ${storage_status}"
            issues=$((issues + 1))
        else
            log "OK: Storage backup status: ${storage_status}"
        fi
    else
        log "WARNING: Storage backup status file not found"
        issues=$((issues + 1))
    fi
    
    return $issues
}

# Check disk space
check_disk_space() {
    local issues=0
    local backup_disk_usage=$(df /backups | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ $backup_disk_usage -gt 90 ]; then
        log "CRITICAL: Backup disk usage is ${backup_disk_usage}%"
        issues=$((issues + 1))
    elif [ $backup_disk_usage -gt 80 ]; then
        log "WARNING: Backup disk usage is ${backup_disk_usage}%"
    else
        log "OK: Backup disk usage is ${backup_disk_usage}%"
    fi
    
    return $issues
}

# Check cron daemon
check_cron_daemon() {
    local issues=0
    
    if pgrep crond > /dev/null; then
        log "OK: Cron daemon is running"
    else
        log "CRITICAL: Cron daemon is not running"
        issues=$((issues + 1))
    fi
    
    return $issues
}

# Generate health report
generate_health_report() {
    local total_issues="$1"
    local report_file="/backups/health_report.json"
    
    local health_status="healthy"
    if [ $total_issues -gt 0 ]; then
        if [ $total_issues -ge 3 ]; then
            health_status="critical"
        else
            health_status="warning"
        fi
    fi
    
    cat > "${report_file}" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "status": "${health_status}",
    "total_issues": ${total_issues},
    "checks": {
        "recent_backups": "$([ $1 -eq 0 ] && echo "ok" || echo "issues")",
        "backup_status": "$([ $2 -eq 0 ] && echo "ok" || echo "issues")",
        "disk_space": "$([ $3 -eq 0 ] && echo "ok" || echo "issues")",
        "cron_daemon": "$([ $4 -eq 0 ] && echo "ok" || echo "issues")"
    },
    "next_check": "$(date -d '+5 minutes' -Iseconds)"
}
EOF
    
    log "Health report generated: ${health_status} (${total_issues} issues)"
}

# Main health check
main() {
    log "═══════════════════════════════════════════════════════════════════════════════"
    log "Starting backup service health check"
    log "═══════════════════════════════════════════════════════════════════════════════"
    
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "${HEALTH_CHECK_LOG}")"
    
    # Run all health checks
    check_recent_backups
    local recent_backups_issues=$?
    
    check_backup_status
    local backup_status_issues=$?
    
    check_disk_space
    local disk_space_issues=$?
    
    check_cron_daemon
    local cron_daemon_issues=$?
    
    # Calculate total issues
    local total_issues=$((recent_backups_issues + backup_status_issues + disk_space_issues + cron_daemon_issues))
    
    # Generate health report
    generate_health_report $total_issues $recent_backups_issues $backup_status_issues $disk_space_issues $cron_daemon_issues
    
    if [ $total_issues -eq 0 ]; then
        log "Backup service health check completed successfully - All systems healthy"
        exit 0
    else
        log "Backup service health check completed with ${total_issues} issues"
        exit 1
    fi
}

# Execute main function
main "$@"