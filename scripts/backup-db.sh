#!/bin/bash
set -euo pipefail

# STRATYON Backend - Database Backup to S3
# Runs daily via cron (configured by setup-ec2.sh)
#
# Usage: bash scripts/backup-db.sh [bucket-name]

S3_BUCKET="${1:-stratyon-backups-670048192993}"
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
BACKUP_FILE="stratyon_db_${TIMESTAMP}.sql.gz"

echo "[$(date)] Starting database backup..."

# Dump and compress
docker exec stratyon-postgres pg_dump \
    -U "${POSTGRES_USER:-stratyon}" \
    "${POSTGRES_DB:-stratyon_db}" \
    | gzip > "/tmp/${BACKUP_FILE}"

# Upload to S3
aws s3 cp "/tmp/${BACKUP_FILE}" "s3://${S3_BUCKET}/db/${BACKUP_FILE}"

# Cleanup local temp file
rm -f "/tmp/${BACKUP_FILE}"

# Remove backups older than 30 days from S3
aws s3 ls "s3://${S3_BUCKET}/db/" \
    | awk '{print $4}' \
    | while read -r file; do
        file_date=$(echo "$file" | grep -oP '\d{4}-\d{2}-\d{2}')
        if [ -n "$file_date" ]; then
            file_epoch=$(date -d "$file_date" +%s 2>/dev/null || echo 0)
            cutoff_epoch=$(date -d "30 days ago" +%s)
            if [ "$file_epoch" -lt "$cutoff_epoch" ] && [ "$file_epoch" -gt 0 ]; then
                echo "Removing old backup: $file"
                aws s3 rm "s3://${S3_BUCKET}/db/${file}"
            fi
        fi
    done

echo "[$(date)] Backup complete: s3://${S3_BUCKET}/db/${BACKUP_FILE}"
