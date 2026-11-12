#!/usr/bin/env bash
# Renderiza o template da política IAM do MinIO substituindo os nomes dos buckets.
#   render-policy.sh <template> <saida>
# Usa envsubst quando existir; senão, cai para substituição pura em bash
# (a imagem minio/mc não garante envsubst).
set -euo pipefail

TEMPLATE="${1:?uso: render-policy.sh <template> <saida>}"
OUTPUT="${2:?uso: render-policy.sh <template> <saida>}"

: "${MINIO_BUCKET_MEDIA:?MINIO_BUCKET_MEDIA não definido}"
: "${MINIO_BUCKET_STATIC:?MINIO_BUCKET_STATIC não definido}"
: "${MINIO_BUCKET_PRIVATE:?MINIO_BUCKET_PRIVATE não definido}"

export MINIO_BUCKET_MEDIA MINIO_BUCKET_STATIC MINIO_BUCKET_PRIVATE

if command -v envsubst >/dev/null 2>&1; then
  # Lista explícita: só estas variáveis são substituídas.
  envsubst '${MINIO_BUCKET_MEDIA} ${MINIO_BUCKET_STATIC} ${MINIO_BUCKET_PRIVATE}' \
    < "$TEMPLATE" > "$OUTPUT"
else
  content="$(<"$TEMPLATE")"
  content="${content//'${MINIO_BUCKET_MEDIA}'/$MINIO_BUCKET_MEDIA}"
  content="${content//'${MINIO_BUCKET_STATIC}'/$MINIO_BUCKET_STATIC}"
  content="${content//'${MINIO_BUCKET_PRIVATE}'/$MINIO_BUCKET_PRIVATE}"
  printf '%s\n' "$content" > "$OUTPUT"
fi

# Falha se sobrou placeholder sem substituir.
rendered="$(<"$OUTPUT")"
if [[ "$rendered" == *'${'* ]]; then
  echo "ERRO: placeholder não substituído em $OUTPUT" >&2
  exit 1
fi

echo "Política renderizada: $OUTPUT"