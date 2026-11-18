# Implementation Plan

## Slices (small, testable, each commit green)

### Slice 1 — Project skeleton + tooling
- `pyproject.toml`: deps `fastapi`, `pydantic>=2`, `uvicorn[standard]`; dev `pytest`, `ruff`, `ty`
- `scripts/vendor.py`: downloads `@awesome.me/webawesome@3.15.0` (MIT) and `tabulator-tables@6.7.1` (MIT) into `static/vendor/`
- `Dockerfile`: `ghcr.io/astral-sh/uv:python3.15-trixie-slim`
- `static/i18n/de.json`: German strings
- `uv.lock` committed

### Slice 2 — Data models (Pydantic v2)
- `src/easycash_web/models.py`: `Money` (int cents), `Booking`, `Account`, `Business`, `Client`, `TaxRate`, `Form` (ecf), `Book`
- `docs/FORMAT.md`: field list
- `docs/format.schema.json`: generated from models, served at `/api/v1/schema`

### Slice 3 — Storage layer
- `src/easycash_web/storage.py`: `DATA_DIR`, load/save JSON per client, migration chain (format_version 1→N), refuse newer

### Slice 4 — API endpoints
- `src/easycash_web/api.py`: clients CRUD, bookings CRUD, books CRUD, accounts CRUD, tax_rates, forms, schema, calculate

### Slice 5 — Frontend (static HTML/JS)
- `static/`: index.html, app.js (ES modules), style.css
- Import map for `@awesome.me/webawesome` + `tabulator-tables`
- Booking grid with Tabulator, inline editing, calculator

### Slice 6 — Domain logic
- `src/easycash_web/domain/`: money.py, vat.py, afa.py, calculator.py, reports.py

### Slice 7 — Tests
- `tests/`: pytest suite for models, storage, domain, calculator, API
