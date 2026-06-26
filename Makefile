.PHONY: install test api web cli db

db:
	docker run -d --name ai-project-cto-db \
		-e POSTGRES_PASSWORD=William1! \
		-e POSTGRES_DB=ai_project_cto \
		-p 5432:5432 postgres:16-alpine 2>/dev/null || echo "Container already exists. Run: docker start ai-project-cto-db"

install:
	python3 -m venv venv
	venv/bin/pip install -e ".[dev]"
	cd apps/web && npm install

test:
	PYTHONPATH=. venv/bin/pytest tests/ -q

api:
	PYTHONPATH=. venv/bin/python -m uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8100

web:
	cd apps/web && npm run dev

cli:
	PYTHONPATH=. venv/bin/python scripts/cli.py "$(IDEA)" --export
