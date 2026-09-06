# Contributing to FleetPulse

Thanks for taking the time to improve FleetPulse. The project intentionally stays small, so focused
bug fixes, tests, accessibility improvements, and documentation updates are especially welcome.

## Local setup

Fork and clone the repository, then create an isolated Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Start the application with `uvicorn app.main:app --reload` and open
[http://127.0.0.1:8000](http://127.0.0.1:8000).

## Before opening a pull request

Run the same checks used by GitHub Actions:

```bash
ruff format --check .
ruff check .
pytest -q
```

Keep each change narrow, add tests for behavior changes, and update the README when setup or public
API behavior changes. Use a short commit subject such as `fix: preserve the latest vehicle reading`
that explains the purpose of the change.

## Project boundaries

FleetPulse is a lightweight portfolio and learning project. Changes should preserve its FastAPI,
SQLite, and vanilla JavaScript approach. Large infrastructure additions or framework rewrites should
be discussed in an issue before implementation.
