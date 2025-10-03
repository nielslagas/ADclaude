# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Backup Service Dockerfile for AI-Arbeidsdeskundige
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 
# Automated backup service for:
# - PostgreSQL database dumps with compression and encryption
# - Redis data backup and restore
# - Application file storage backup
# - Configurable retention policies
# - Health monitoring and alerting
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FROM alpine:3.18

# Install required packages
RUN apk add --no-cache \
    postgresql15-client \
    redis \
    bash \
    curl \
    gzip \
    tar \
    openssl \
    gnupg \
    coreutils \
    findutils \
    dcron \
    shadow \
    tzdata

# Create backup user
RUN addgroup -g 1000 backup && \
    adduser -D -s /bin/bash -u 1000 -G backup backup

# Create backup directories
RUN mkdir -p /backups/{postgres,redis,storage,logs} && \
    chown -R backup:backup /backups

# Create script directory
RUN mkdir -p /usr/local/bin && \
    chown -R backup:backup /usr/local/bin

# Copy backup scripts
COPY --chown=backup:backup backup-scripts/ /usr/local/bin/
RUN chmod +x /usr/local/bin/*.sh

# Copy crontab configuration
COPY --chown=backup:backup crontab /var/spool/cron/crontabs/backup
RUN chmod 0600 /var/spool/cron/crontabs/backup

# Switch to backup user
USER backup

# Set working directory
WORKDIR /backups

# Health check
HEALTHCHECK --interval=300s --timeout=30s --start-period=60s --retries=3 \
    CMD /usr/local/bin/backup-health-check.sh

# Default command - start cron daemon
CMD ["crond", "-f", "-d", "8"]