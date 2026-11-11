"""
Gunicorn — perfil para API Django I/O-bound atrás do Nginx.

Capacidade simultânea por container = workers x threads.
Cada thread mantém 1 conexão com o Postgres (CONN_MAX_AGE=60), então
conexões do web ≈ workers x threads. Ajuste por variável de ambiente, sem
rebuild: GUNICORN_WORKERS, GUNICORN_THREADS, GUNICORN_TIMEOUT.
"""
import multiprocessing
import os

_cpus = multiprocessing.cpu_count()

bind = "0.0.0.0:8000"

# gthread: threads absorvem espera de DB/S3/Asaas sem multiplicar processos.
worker_class = "gthread"
workers = int(os.getenv("GUNICORN_WORKERS", max(2, _cpus)))
threads = int(os.getenv("GUNICORN_THREADS", 8))

# Timeouts: a API não faz nada síncrono longo (PDF é a exceção, ~2-5 s).
timeout = int(os.getenv("GUNICORN_TIMEOUT", 30))
graceful_timeout = 30
keepalive = 5            # conexões keep-alive vindas do Nginx

# Recicla workers para conter vazamento de memória lento.
max_requests = 2000
max_requests_jitter = 200

# Heartbeat em tmpfs: evita workers "travados" por I/O de disco em container.
worker_tmp_dir = "/dev/shm"

# Carrega o app uma vez e faz fork (menos RAM, boot mais rápido).
preload_app = True

# Só o Nginx (rede interna do compose) fala com o Gunicorn.
forwarded_allow_ips = "*"

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(M)sms "%(a)s"'