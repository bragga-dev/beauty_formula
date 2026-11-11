#!/usr/bin/env bash
# Deploy/atualização: rebuild, migrações (serviço `migrate`) e restart sem derrubar o banco.
#   bash infra/scripts/deploy.sh
set -euo pipefail
COMPOSE="docker compose -f docker-compose.prod.yml"

$COMPOSE build web
$COMPOSE up -d --no-deps db redis redis-cache minio
$COMPOSE run --rm createbuckets
$COMPOSE run --rm migrate
$COMPOSE up -d --no-deps web celery celery-beat nginx
$COMPOSE ps