# Task Instructions for Coding Agents

This file **must be read** by any coding agent before planning any code writing (not spec writing).

## 1. Project Architecture & Development Server

**Architecture**: Dockerized application with two services:
- **db**: PostgreSQL 18 with pgvector extension
- **backend**: Python 3.12, FastAPI, uv package manager, CLIP model for image embeddings

A **cli** package exists as a separate uv workspace member.

**Start development server:**
```bash
docker compose up
```

The override file (`docker-compose.override.yml`) enables hot-reload on code changes. Environment variables are configured via `.env` (copy from `.env.example`).

## 2. Tests & Migrations

**All tests and migrations must be executed via `docker compose`** — never run commands directly on the host.

### Migrations (via Alembic)
```bash
make migrate msg="<description of change>"
make upgrade
```

### Tests
```bash
# First ensure services are up
docker compose up -d

# Then run tests
make test
```

The `make test` command runs `pytest tests -v` inside the backend container with the appropriate mounts.

**Important**: If you add or modify tests in a way that breaks `make test`, **STOP immediately and notify the user**. Do not attempt to fix the command or work around it.
