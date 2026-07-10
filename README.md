# Beauty Formula

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)
![Django Ninja](https://img.shields.io/badge/Django%20Ninja-1.6-black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-async%20tasks-37814A?logo=celery&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-4.x-FF6600?logo=rabbitmq&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![MinIO](https://img.shields.io/badge/MinIO-S3%20storage-C72E49?logo=minio&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-private-lightgrey)

Sistema de agendamento para salões e barbearias. Controla clientes, funcionários, catálogo de serviços, horários de trabalho, folgas/bloqueios de agenda, agendamentos com prevenção de conflito de horário, avaliações e cobrança via Asaas.

---

## Visão geral

O backend é construído em **Django 5.2** com **Django Ninja** para expor a API (tipada com Pydantic, documentação automática via Swagger), autenticação por **JWT** (django-ninja-jwt), e um pipeline assíncrono com **Celery + RabbitMQ** para tarefas em segundo plano (envio de e-mails, notificações, integrações). Arquivos (fotos de perfil, imagens de serviço) são armazenados no **MinIO**, compatível com S3 via `django-storages`. O banco de dados é **PostgreSQL**, e o **Redis** serve como result backend do Celery. Todo o ambiente de desenvolvimento sobe via **Docker Compose**, com provisionamento automático dos buckets e políticas do MinIO.

## Domínio da aplicação

**Contas (`accounts`)**
- Usuário customizado (`AUTH_USER_MODEL = accounts.User`) com autenticação por e-mail, `UUID` como chave primária e três papéis: Administrador Root, Funcionário e Cliente.
- Perfis separados de `Employee` e `Client`, cada um com foto de perfil validada (formato, tamanho, dimensões e integridade da imagem) e imagem padrão de fallback.

**Serviços e agenda (`services`)**
- Catálogo de `Service` (nome, preço, duração, imagem).
- `Scheduling` (agendamento) com máquina de estados (pendente → confirmado → em andamento → concluído / cancelado / não compareceu), preço e duração congelados no momento da reserva, motivo e autor de cancelamento, e constraints de banco garantindo consistência entre status e data de cancelamento.
- `EmployeeWorkingHours` para definir a jornada semanal recorrente de cada funcionário.
- `EmployeeTimeOff` para folgas e bloqueios de agenda, aceitando tanto um bloqueio recorrente (dia da semana + horário) quanto um bloqueio pontual (intervalo de data/hora), nunca os dois ao mesmo tempo — validado a nível de modelo.
- `AverageRating` para consolidar a avaliação média de funcionários/serviços.

**Pagamentos (`payment`)**
- Integração com a API do **Asaas** para cobrança dos agendamentos.

**Núcleo (`core`)**
- Validadores compartilhados (ex.: validação robusta de upload de imagem — extensão, peso, formato real do arquivo, dimensões e proteção contra "pixel bomb").
- Constantes de domínio (gênero, tipos de bloqueio de agenda).

## Infraestrutura de desenvolvimento

O `docker-compose.dev.yml` orquestra:

- **rabbitmq** — broker do Celery, com painel de management.
- **db** — PostgreSQL.
- **redis** — result backend do Celery.
- **minio** — armazenamento de objetos S3-compatible.
- **setup-minio** — job que roda uma vez, cria buckets (`media`, `static`, `private`), usuário IAM dedicado, política de acesso e envia as imagens padrão.
- **web** — servidor de desenvolvimento Django.
- **celery** — worker de tarefas assíncronas.
- **celery-beat** — agendador de tarefas periódicas.

## Pré-requisitos

- Docker e Docker Compose
- Python 3.12+ (opcional, apenas se for rodar fora de container)

## Configuração

1. Copie o arquivo de exemplo de variáveis de ambiente:

   ```bash
   cp .env.example .env
   ```

2. Preencha o `.env` com valores reais. **Atenção**: `RABBITMQ_PASSWORD` e a senha embutida em `CELERY_BROKER_URL` precisam ser exatamente a mesma — o RabbitMQ sobe com as credenciais de `RABBITMQ_USER`/`RABBITMQ_PASSWORD`, e o Celery se autentica usando a URL completa. Senhas divergentes causam falha de autenticação.

3. Gere uma `FIELD_ENCRYPTION_KEY` válida para os campos criptografados.

## Subindo o ambiente

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

Acompanhar os logs:

```bash
docker compose -f docker-compose.dev.yml logs -f
```

## Migrações

```bash
docker compose -f docker-compose.dev.yml exec web python manage.py makemigrations
docker compose -f docker-compose.dev.yml exec web python manage.py migrate
```

Criar um superusuário:

```bash
docker compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
```

## Portas expostas (dev)

| Serviço | Porta | Descrição |
|---|---|---|
| web | 8000 | API Django |
| db | 5432 | PostgreSQL |
| redis | 6379 | Redis |
| rabbitmq | 5672 | AMQP |
| rabbitmq | 15672 | Painel de management |
| minio | 9000 | API S3 |
| minio | 9001 | Console web |

## Notas de compatibilidade — RabbitMQ 4.x

O RabbitMQ 4.x bloqueia por padrão algumas features legadas que o Celery ainda usa internamente (filas transitórias exclusivas, QoS global). As exceções necessárias são liberadas via `infra/rabbitmq/permit-deprecated.conf`, montado no container do RabbitMQ. Se aparecerem novos avisos de `Deprecated features` travando a conexão do Celery (nível `[error]`, não `[warning]`), adicione a flag indicada na mensagem de erro nesse arquivo e reinicie o serviço:

```bash
docker compose -f docker-compose.dev.yml restart rabbitmq
```

## Produção

Use `docker-compose.prod.yml`, com as variáveis de produção configuradas no `.env` (`DEBUG=False`, `ALLOWED_HOSTS` restritivo, credenciais reais de banco/MinIO/Asaas).

## Licença

