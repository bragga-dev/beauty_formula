# Homologação / Produção — Fórmula da Beleza

Alvo: **~1000 usuários simultâneos** em 1 host (premissa: **4 vCPU / 8 GB RAM / SSD**).

## Arquitetura

```
Internet ──443──> nginx ──/api,/admin──> web (gunicorn gthread)
                    │  ──/static───────> volume static_volume (collectstatic)
                    │  ──/ (SPA)───────> build do frontend (imagem ../formula-da-beleza)
                    └──media.<dominio>─> minio (cache 7d, só leitura)
web/celery ──> db (Postgres 16)
web        ──> redis-cache (cache, sessões, rate-limit — LRU, sem disco)
web/celery ──> redis (broker + resultados — noeviction + AOF)
celery-beat (1 instância) ──> redis
migrate (one-shot): migrate + collectstatic a cada deploy
```

## Por que isso aguenta 1000 simultâneos

"1000 usuários simultâneos" ≠ 1000 requisições simultâneas. Com ~1 requisição a cada 5–10 s por usuário são **100–200 req/s**.

| Camada | Configuração | Capacidade |
|---|---|---|
| Gunicorn | 4 workers × 8 threads (gthread) | **32 requisições em voo**; a ~80 ms/req ≈ 400 req/s |
| Postgres | `max_connections=200` | web usa ≤ 32 + celery 4 + beat/migrate ≈ 40 conexões |
| Nginx | 8192 conexões/worker, keep-alive, gzip, cache de mídia | milhares de conexões ociosas |
| Redis | 2 instâncias | fila nunca perde mensagem; cache pode ser descartado |

Se o `k6` mostrar p95 alto: suba `GUNICORN_WORKERS`/`GUNICORN_THREADS` no `.env` (limite ≈ `max_connections`), ou o host.

## Primeira subida

```bash
cp .env.example .env            # aplique por cima o que está em .env.staging.example
# preencha segredos (SECRET_KEY, POSTGRES_*, MINIO_*, ASAAS_*, FIELD_ENCRYPTION_KEY...)
bash infra/scripts/init-ssl.sh  # emite o certificado e sobe o nginx em HTTPS
bash infra/scripts/deploy.sh    # build, migrações, sobe web/celery/beat
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

Atualizar versão: `bash infra/scripts/deploy.sh`. Renovar certificado (cron semanal): `bash infra/scripts/renew-certs.sh`.

## Teste de carga

```bash
# no .env da homologação (somente lá): RATELIMIT_ENABLE=False   e recriar o web
k6 run -e BASE_URL=https://SEU_DOMINIO infra/loadtest/k6-staging.js
```
Passa se: erro < 1% e p95 < 800 ms sustentando 1000 VUs por 10 min. Acompanhe `docker stats` e `docker compose logs -f web nginx`.
O limite por IP do Nginx (20 r/s) bloqueia gerador de carga de 1 IP: rode o k6 de várias máquinas ou aumente `zone=api` temporariamente.

## Premissas (confirme)

1. O `nginx` continua sendo construído de `../formula-da-beleza` e essa imagem é baseada em `nginx` oficial com o build do SPA em `/usr/share/nginx/html`. A config daqui **substitui** a da imagem (monta `nginx.conf` e `/etc/nginx/templates`).
2. Front e API na **mesma origem** (`/api`), por isso `COOKIE_SAMESITE=Lax`.
3. Este nginx é a borda. Se houver Cloudflare/balanceador na frente, o IP real chega em outro header: habilite `real_ip_header` no nginx e ajuste `client_ip()` em `prod.py`.
4. DNS de `APP_DOMAIN` e `MEDIA_DOMAIN` apontando para o servidor; portas 80/443 abertas.

## Pontos de atenção encontrados

- `default/product_img.png` não existe, mas o model `Product` usa esse caminho como padrão e o `createbuckets` não o envia ao MinIO.
- `STATICFILES_DIRS` aponta para `beauty_formula/static`, que não existe (aviso `staticfiles.W004` no `check --deploy`; inofensivo, some criando a pasta).
- `requirements.txt` inclui libs de teste e os dois drivers do Postgres (`psycopg` e `psycopg2-binary`): funciona, mas deixa a imagem maior.
- O console do MinIO fica só em `127.0.0.1:9001` (use túnel SSH). A porta 9000 deixou de ser pública: a mídia sai por `https://MEDIA_DOMAIN`.