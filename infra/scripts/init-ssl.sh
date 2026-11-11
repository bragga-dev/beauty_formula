#!/usr/bin/env bash
# Emite o certificado Let's Encrypt (1ª vez) e sobe o Nginx em HTTPS.
# Uso (na raiz do projeto, com .env contendo APP_DOMAIN, MEDIA_DOMAIN e LETSENCRYPT_EMAIL):
#   bash infra/scripts/init-ssl.sh
# Pré-requisito: DNS de APP_DOMAIN e MEDIA_DOMAIN apontando para este servidor
# e portas 80/443 liberadas.
set -euo pipefail

COMPOSE="docker compose -f docker-compose.prod.yml"
set -a; source .env; set +a

: "${APP_DOMAIN:?defina APP_DOMAIN no .env}"
: "${MEDIA_DOMAIN:?defina MEDIA_DOMAIN no .env}"
: "${LETSENCRYPT_EMAIL:?defina LETSENCRYPT_EMAIL no .env}"
STAGING_FLAG="${LETSENCRYPT_STAGING:+--staging}"   # LETSENCRYPT_STAGING=1 para testar sem gastar limite

echo ">> 1/3 Nginx em modo bootstrap (só HTTP, para o desafio ACME)"
NGINX_MODE=bootstrap $COMPOSE up -d --build nginx

echo ">> 2/3 Emitindo certificado para ${APP_DOMAIN} e ${MEDIA_DOMAIN}"
$COMPOSE run --rm certbot certonly --webroot -w /var/www/certbot \
    -d "${APP_DOMAIN}" -d "${MEDIA_DOMAIN}" \
    --email "${LETSENCRYPT_EMAIL}" --agree-tos --no-eff-email --non-interactive ${STAGING_FLAG}

echo ">> 3/3 Nginx em modo HTTPS"
NGINX_MODE=https $COMPOSE up -d --force-recreate nginx
echo "OK: https://${APP_DOMAIN}"