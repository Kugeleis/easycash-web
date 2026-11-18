# EasyCash&Tax Web

[![CI](https://github.com/Kugeleis/easycash-web/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/Kugeleis/easycash-web/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.15](https://img.shields.io/badge/python-3.15-blue.svg)](https://www.python.org/downloads/)

Reimplementation of EasyCash&Tax as a FastAPI + plain HTML/JS web app.

## Architecture

- **Backend**: FastAPI (Python 3.15), Pydantic v2
- **Frontend**: Plain HTML/CSS/ES modules (no build step)
- **Storage**: One JSON file per client in `DATA_DIR`
- **Third-party**: Web Awesome (MIT) + Tabulator (MIT) vendored under `static/vendor/`

## Setup

```bash
uv sync
```

## Run

```bash
DATA_DIR=./data uv run uvicorn easycash_web.api:app --reload
```

Then open <http://127.0.0.1:8000>.

## Test

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check .
```

## Docker

```bash
docker build -t easycash-web .
docker run -p 8000:8000 -v ./data:/data easycash-web
```

## License

GPL-3.0-or-later. See `NOTICE` for third-party licenses.
