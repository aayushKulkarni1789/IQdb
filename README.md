# imgdb

Image database with multi-filter semantic search.

## Running tests

The test suite targets the containerized Postgres (it relies on `VECTOR(512)` / HNSW /
`JSONB`, which in-memory SQLite cannot provide). Bring the stack up, build the schema,
then run pytest:

```bash
docker compose up -d
make upgrade           # apply migrations to build schema
# (or, for fresh schema without migrations: build via SQLModel.metadata.create_all)
pytest backend/tests
```

`backend/tests/conftest.py` builds the schema with `SQLModel.metadata.create_all` and
provides `db_session` (truncate-per-test isolation) and `client` (overrides `get_db`)
fixtures, so a clean Postgres plus `docker compose up -d` is sufficient to run the suite.
