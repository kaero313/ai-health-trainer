#!/bin/bash

set -euo pipefail

BACKUP_DIR="/opt/backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "Starting PostgreSQL backup..."

if docker compose -f docker-compose.prod.yml exec -T db sh -lc 'PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}"' | gzip > "${BACKUP_FILE}"; then
  find "${BACKUP_DIR}" -type f -name "*.sql.gz" -mtime +7 -delete
  echo "Backup completed successfully: ${BACKUP_FILE}"
else
  rm -f "${BACKUP_FILE}"
  echo "Backup failed"
  exit 1
fi
