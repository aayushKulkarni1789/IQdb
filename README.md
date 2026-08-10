# IQdb

An image database with CLIP-powered semantic search and multi-filter querying, built on
Postgres + [pgvector](https://github.com/pgvector/pgvector). Ingest images, generate CLIP
embeddings, then search by combining semantic (text/image) similarity with structural
filters (datetime, geo, face).

## Key features

- **CLIP embedding ingestion** — images are embedded with a CLIP model (`openai/clip-vit-base-patch32`)
  and stored as `VECTOR(512)` rows backed by an HNSW cosine index.
- **Multi-filter semantic search** — build a *search session*, apply any number of filters in
  any order, and finalize to get top-K hits.
  - *Subset filters* (datetime, geo, face) narrow the candidate pool via SQL `WHERE` predicates.
  - *Rank filters* (CLIP text similarity) are fused by **Reciprocal Rank Fusion** (`k=60`) at finalize.
  - Execution is **two-phase** (all subsets intersect first, then ranks fuse); phase is derived
    at finalize, so tool-call order never matters.
  - Lazy SQL push-down keeps the candidate set as a `Select`; no image IDs materialize in Python
    until the final `LIMIT K`.
- **Background ingestion** — uploads trigger an async CLIP embedding + EXIF extraction pipeline
  per job.
- **Interactive CLI** — `imgdb-cli` uploads directories of images in resumable batches.

## Tech stack

- **Backend:** Python 3.12, FastAPI, SQLModel, Alembic, pgvector, psycopg3, Pillow
- **Embeddings:** PyTorch + Hugging Face `transformers` (CLIP)
- **Database:** PostgreSQL with `vector` extension
- **Packaging/build:** `uv` workspace + Docker Compose
- **CLI:** Typer + `requests`

## Project layout

```
adr/                      Architecture decision records
backend/
  app/
    api/v1/routes/        API routers: utils, uploads
    core/                 config, db engine, CLIP embedding helpers
    search/
      filters/            clip (implemented), datetime/geo/face (subsets/stubs)
      filter.py           Filter abstraction + lazy CandidateQuery
      orchestrator.py     session lifecycle (create / add filter / finalize) + RRF
      registry.py         filter-kind to class, liveness advertisement
      routes.py           /sessions, /sessions/{id}/filters, /sessions/{id}/finalize
      exif.py             capture-time and GPS extraction
    models.py             SQLModel tables (Image, CLIP_Embedding, UploadJob, SearchSession…)
    tasks.py              background embedding/EXIF ingestion
  scripts/install_model.py  downloads the CLIP model at build time
  tests/                  pytest suite
cli/                      Typer CLI (src/imgdb_cli)
database/                 Postgres image with pgvector init
docs/  glossary/  openspec/  adr/   Specs, glossaries, and change proposals
```

## Getting started

### Prerequisites

- Docker + Docker Compose
- A `./.env` file (copy `.env.example` and adjust as needed)

```bash
cp .env.example .env
```

### Bring up the stack

```bash
docker compose up -d --build
```

The build installs the CLIP model (controlled by `CLIP_MODEL_NAME` / `CLIP_MODEL_PATH`).
Migrations run automatically on backend startup (`alembic upgrade head`).

The interactive OpenAPI docs are available at `http://localhost:8000/docs`.

### Upload images

Start a session, upload batches, then complete it. The CLI wraps these steps:

```bash
# run from the repo (or `pip install` the cli package)
uv run --project cli imgdb-cli upload --directory /path/to/images
```

Or drive the API directly (see [API](#api)).

## API

Base URL: `http://localhost:8000`. All routes below are under the `/api/v1` prefix
unless noted.

### Utilities

| Method | Path              | Description                              |
|--------|-------------------|------------------------------------------|
| GET    | `/utils/health-check/` | Liveness check                      |
| POST   | `/utils/embed-text/`   | Embed a list of texts                   |
| POST   | `/utils/embed-image/`  | Embed a list of uploaded images         |

### Uploads

| Method | Path                      | Description                                  |
|--------|---------------------------|----------------------------------------------|
| POST   | `/uploads/start`          | Create an upload job (body: `expected_image_count`) |
| GET    | `/uploads/{job_id}`       | Upload job status                            |
| POST   | `/uploads/{job_id}/batch` | Upload a batch of images as multipart files  |
| POST   | `/uploads/{job_id}/complete` | Finalize the job (triggers background ingestion) |
| POST   | `/uploads/{job_id}/abort` | Abort the job                                |

### Search

Sessions are terminal: once finalized, further filter/finalize calls return `409 Conflict`.

| Method | Path                                | Description                                     |
|--------|-------------------------------------|-------------------------------------------------|
| POST   | `/sessions`                         | Create a search session                         |
| POST   | `/sessions/{id}/filters`            | Add a filter (body: `kind` + extra `kind`-specific fields) |
| POST   | `/sessions/{id}/finalize`           | Run the query, return top-K hits (body: `top_k`, default 100) |
| GET    | `/filters`                          | List available filter kinds and whether each is live |

Available filter kinds:
- `clip` — text/CLIP rank filter (live).
- `datetime` — capture-time range (subset).
- `geo` — spatial proximity around a lat/lng (subset).
- `face` — face presence threshold (subset).

Unknown kinds return `422`; live-but-stubbed subset filters return `501` at add time.

Example search session:

```bash
# 1. create a session
curl -X POST localhost:8000/api/v1/sessions
# 2. narrow by time (subset)
curl -X POST localhost:8000/api/v1/sessions/1/filters \
  -H 'Content-Type: application/json' \
  -d '{"kind": "datetime", ...}'
# 3. rank by semantics (rank filter)
curl -X POST localhost:8000/api/v1/sessions/1/filters \
  -H 'Content-Type: application/json' \
  -d '{"kind": "clip", "text": "sunset over the ocean"}'
# 4. finalize
curl -X POST localhost:8000/api/v1/sessions/1/finalize \
  -H 'Content-Type: application/json' -d '{"top_k": 50}'
```

## Running tests

The suite targets the containerized Postgres (it relies on `VECTOR(512)` / HNSW / `JSONB`,
which in-memory SQLite cannot provide). Bring the stack up, build the schema, then run pytest:

```bash
cp .env.example .env
docker compose up -d
make upgrade           # apply migrations to build schema
# (or, for fresh schema without migrations: build via SQLModel.metadata.create_all)
pytest backend/tests
```

`backend/tests/conftest.py` builds the schema with `SQLModel.metadata.create_all` and provides `db_session`
(truncate-per-test isolation) and `client` (overrides `get_db`) fixtures, so a clean Postgres plus
`docker compose up -d` is sufficient to run the suite.

### Useful Make targets

```bash
make migrate msg="description"   # autogenerate an Alembic migration
make upgrade                     # apply migrations (alembic upgrade head)
make db                          # open a psql shell against the Postgres container
make test                        # run the backend suite inside the backend container
```

## Development

- Set `.env` (see `.env.example`). `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` configure
  the database; `CLIP_MODEL_NAME` / `CLIP_MODEL_PATH` select the embedding model.
- `docker-compose.override.yml` mounts the backend source and uploads for hot reload (`fastapi run --reload`).
- Architecture decisions live in `adr/`; spec docs and change proposals in `openspec/` and `glossary/`.
