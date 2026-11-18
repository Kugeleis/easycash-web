# EasyCash&Tax Web

[![CI](https://github.com/Kugeleis/easycash-web/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/Kugeleis/easycash-web/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.15](https://img.shields.io/badge/python-3.15-blue.svg)](https://www.python.org/downloads/)

A self-hosted web app for **cash-basis bookkeeping (EÜR)** and **VAT pre-registration
(Umsatzsteuer-Voranmeldung)**, aimed at German freelancers and small businesses. It is a
reimplementation of the classic Windows program *EasyCash&Tax* as a FastAPI + plain
HTML/JS web application.

Everything runs on your own machine. There is no account, no cloud, no telemetry — your
books are plain JSON files in a directory you control.

---

## Features

### Bookkeeping
- **Income & expense bookings** (Einnahmen/Ausgaben) with date, description, account,
  gross amount, VAT rate and receipt number.
- **Inline editing** in a spreadsheet-style grid (Tabulator) with keyboard navigation.
- **Expression calculator** in amount fields: type `100+50*1.19` (German decimal comma
  `,` also accepted) and it is evaluated to cents — no separate calculator needed.
- **Recurring bookings** (Dauerbuchungen): define a template with an interval and let the
  app generate the entries.
- **Accounts** (Konten) for income and expenses, organised per client/business.

### VAT (Umsatzsteuer)
- **Configurable VAT rates** with **validity dates** — the correct rate is resolved from
  the booking date (default: 19 % standard, 7 % reduced since 2007).
- **Kleinunternehmer mode** (§19 UStG): optional per business; suppresses VAT fields and
  books revenue gross, per the legal threshold.
- **VAT prepayments** (USt-Voranmeldung) for monthly / quarterly periods.

### Depreciation (AfA)
- **Linear and degressive** methods.
- **Four accuracy modes**: annual (Ganzjahres-AfA), half-year rule (Halbjahresregel),
  month-precise, and per-settings — matching the original EasyCash&Tax behaviour.

### Reports & tax forms
- **EÜR (Anlage EÜR)** — income surplus statement per §4(3) EStG, with line mapping
  (lines 12/15–17 for income, 24/30/34/50 for expenses), including a Kleinunternehmer
  variant.
- **GuV** (Gewinn- und Verlustrechnung) — profit & loss with income/expense sections.
- **SuSa** (Summen- und Saldenliste) — account balance list.
- **Journal** (Buchungsjournal) — chronological list of all bookings.
- All reports are available both from the web UI and as JSON via the REST API.

### Data & portability
- **One JSON file per client** (`<Mandant>.json`) in `DATA_DIR` — human-readable,
  diff-friendly and easy to back up.
- **1:1 download/upload** of a client's file through the UI/API.
- **Schema endpoint** for the full data model.
- **UUIDv7** IDs for stable, sortable entity identifiers.
- **Money stored as integer cents** internally; decimal strings (`"119.00"`) in files
  and the API.

### Deployment
- **Local server only** by design: no authentication, no cookies, CORS closed. Run it on
  `localhost` and keep it there.
- **Docker** image and a `compose.yaml` for one-command startup.

---

## Quick start

### With Docker (recommended)

```bash
docker compose up -d
```

Open <http://127.0.0.1:8999>. Data is stored in `./data` on the host.

Stop with:

```bash
docker compose down
```

### Without Docker

Requirements: [uv](https://docs.astral.sh/uv/) and Python 3.15.

```bash
uv sync
task dev            # or: DATA_DIR=./data uv run uvicorn easycash_web.api:app --reload
```

Open <http://127.0.0.1:8000>. Data is stored in `./data`.

---

## Usage

1. **Create/open a client (Mandant).** Each client maps to one JSON file in `DATA_DIR`.
2. **Pick the client** in the top bar. The booking grid loads that client's bookings.
3. **Add a booking** with *Neue Buchung*: enter date, description, account, gross amount,
   VAT rate and receipt number. Amounts accept arithmetic expressions.
4. **Edit inline** by clicking a cell; changes are saved automatically via the API.
5. **Run reports** through the report endpoints (see below) or the UI navigation.
6. **Back up** by downloading the client's JSON file, or copy `DATA_DIR` wholesale.

### Data directory

Set `DATA_DIR` to change where books are stored (default `/data` inside Docker,
`./data` in the examples above). Each file is a self-contained book:

```
DATA_DIR/
├── Müller.json
└── Schmidt.json
```

---

## REST API

All endpoints are under `/api/v1`. Interactive docs are served by FastAPI at `/docs`.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |
| GET | `/schema` | JSON Schema of the data model |
| GET | `/clients` | List clients |
| GET/POST | `/book/{client}` | Load / save a client's book |
| GET | `/book/{client}/download` | Download the book file 1:1 |
| POST | `/book/{client}/upload` | Upload (replace/create) a book |
| GET/POST | `/accounts/{client}` | List / add accounts |
| PUT/DELETE | `/accounts/{client}/{account_id}` | Update / delete an account |
| GET/POST | `/bookings/{client}` | List / add bookings |
| PUT/DELETE | `/bookings/{client}/{booking_id}` | Update / delete a booking |
| GET/POST | `/tax-rates/{client}` | List / add VAT rates |
| GET/POST | `/recurring/{client}` | List / add recurring bookings |
| GET/POST | `/businesses/{client}` | List / add businesses |
| GET | `/reports/euer/{client}/{year}?kleinunternehmer=` | EÜR report |
| GET | `/reports/guv/{client}/{year}` | GuV report |
| GET | `/reports/susa/{client}/{year}` | SuSa report |
| GET | `/reports/journal/{client}/{year}` | Journal report |
| GET | `/reports/accounts/{client}/{account_id}/balance?year=` | Account balance |

---

## Development

### Architecture

- **Backend**: FastAPI (Python 3.15), Pydantic v2, no database/ORM.
- **Frontend**: plain HTML/CSS/ES modules, no build step (import map + vendored libraries).
- **Storage**: one JSON file per client in `DATA_DIR`.
- **Third-party**: Web Awesome (MIT) + Tabulator (MIT), vendored under `static/vendor/`.

### Task runner

Common tasks are defined in `Taskfile.yml`:

| Task | Description |
|------|-------------|
| `task install` | Install dependencies (`uv sync`) |
| `task dev` | Run the app locally with hot reload on port 8000 |
| `task lint` | Ruff lint with autofix |
| `task format` | Ruff format |
| `task type-check` | Static type checking (`ty`) |
| `task test` | Run the test suite (`pytest`) |
| `task check` | All quality checks |

### Quality gates

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check .
```

Git hooks are managed by [prek](https://prek.j178.dev): trailing whitespace, end-of-file,
large files, ruff, ruff-format, `ty check`, and `pytest`. Commit messages follow
[Conventional Commits](https://www.conventionalcommits.org/) — see `CONTRIBUTING.md`.

### Docker build

```bash
docker build -t easycash-web .
docker run -p 8000:8000 -v ./data:/data easycash-web
```

---

## License

GPL-3.0-or-later. See `NOTICE` for third-party licenses.
