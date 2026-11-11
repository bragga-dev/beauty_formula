#!/usr/bin/env bash
# Renova os certificados e recarrega o Nginx. Agende no cron do host, ex.:
#   0 3 * * 1  cd /caminho/do/projeto && bash infra/scripts/renew-certs.sh >> /var/log/renew-certs.log 2>&1
set -euo pipefail
COMPOSE="docker compose -f docker-compose.prod.yml"
$COMPOSE run --rm certbot renew --webroot -w /var/www/certbot --quiet
$COMPOSE exec -T nginx nginx -s reload