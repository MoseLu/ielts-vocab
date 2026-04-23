# Local RabbitMQ for Microservices

Last updated: 2026-04-10

## Purpose

Wave 5 now includes a project-owned local RabbitMQ runtime for split-service domain events and durable work queues.

The current local baseline uses `127.0.0.1:5679` so RabbitMQ does not collide with a system default `5672` node.

## Shared Config Shape

Split services now resolve RabbitMQ config in this order:

1. `<SERVICE_PREFIX>_RABBITMQ_URL`
2. generic `RABBITMQ_URL`
3. `<SERVICE_PREFIX>_RABBITMQ_HOST`, `_PORT`, `_USER`, `_PASSWORD`, `_VHOST`, `_SSL`
4. generic `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_VHOST`, `RABBITMQ_SSL`

The checked-in example file [backend/.env.microservices.local.example](../../backend/.env.microservices.local.example) now includes:

- shared host, port, user, password, and vhost defaults for the local broker
- a shared `RABBITMQ_DOMAIN_EXCHANGE`
- service-level override support through the same `<SERVICE_PREFIX>_*` env pattern used by Redis and PostgreSQL

## Startup

Run the RabbitMQ runtime directly:

```bash
./scripts/start-local-rabbitmq-microservices.sh
```

Or start the whole split backend:

```bash
./start-microservices.sh
```

`start-microservices.sh` now starts the local RabbitMQ runtime before bringing up the HTTP services unless `--skip-rabbit` is passed.

## Binary Resolution

The RabbitMQ startup script uses the bundled runtime env first and then resolves `rabbitmq-server` and `rabbitmq-diagnostics` from `PATH`. If those binaries are unavailable, the script fails with a clear error instead of silently skipping broker startup.

## Verification

The startup script opens a TCP connection, sends the AMQP 0-9-1 protocol header, and waits for a broker response.

Expected local endpoint after startup:

```text
amqp://guest:guest@127.0.0.1:5679/%2F
```
