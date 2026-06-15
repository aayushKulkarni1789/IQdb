.PHONY: migrate upgrade db

migrate:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

upgrade:
	docker compose exec backend alembic upgrade head

db:
	docker compose exec db psql -U root -d imagedb
