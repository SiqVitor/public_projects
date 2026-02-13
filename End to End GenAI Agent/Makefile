.PHONY: install lint test docker-up docker-down

install:
	poetry install --with dev

lint:
	poetry run ruff check src/
	poetry run mypy src/argus/

test:
	poetry run pytest tests/ -v

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down
