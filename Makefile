.PHONY: migrate upgrade db

migrate:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

upgrade:
	docker compose exec backend alembic upgrade head

db:
	docker compose exec db psql -U root -d imagedb

test:
	docker compose run --rm \
	  -v "$(CURDIR)/backend/app:/app/backend/app" \
	  -v "$(CURDIR)/backend/tests:/app/backend/tests" \
	  backend bash -c "cd /app/backend && pytest tests -v"
