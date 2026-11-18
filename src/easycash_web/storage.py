"""Storage layer — plain JSON file per client, no database.

DATA_DIR holds one `<client>.json` file per Mandant. Download returns exactly
the file on disk; upload creates or replaces a book (1:1).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from easycash_web.models import BookFile, apply_migrations

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))


class BookNotFoundError(Exception):
    pass


class BookVersionError(Exception):
    """Raised when a book file has a newer format_version than supported."""


def _safe_name(name: str) -> str:
    """Reject path traversal; allow letters, digits, dash, underscore, dot, spaces."""
    name: str = name.strip()
    if not name or any(c in name for c in "/\\"):
        raise ValueError("invalid client name")
    if name in {".", ".."}:
        raise ValueError("invalid client name")
    return name


def book_path(data_dir: Path, client_name: str) -> Path:
    return data_dir / f"{_safe_name(client_name)}.json"


def load_book(data_dir: Path, client_name: str) -> BookFile:
    path: Path = book_path(data_dir, client_name)
    if not path.exists():
        raise BookNotFoundError(client_name)
    raw: str = path.read_text(encoding="utf-8")
    data: Any = json.loads(raw)
    current: Any = BookFile.model_fields["format_version"].default
    version = int(data.get("format_version", 1))
    if version > current:
        raise BookVersionError(f"file format_version {version} is newer than supported {current}")
    data = apply_migrations(data)
    return BookFile.model_validate(data)


def load_or_new(data_dir: Path, client_name: str) -> BookFile:
    try:
        return load_book(data_dir, client_name)
    except BookNotFoundError:
        return BookFile(meta={"client_name": client_name})


def save_book(data_dir: Path, client_name: str, book: BookFile) -> BookFile:
    data_dir.mkdir(parents=True, exist_ok=True)
    book.revision += 1
    path: Path = book_path(data_dir, client_name)
    # Deterministic output: indent=2, sorted by model definition order.
    path.write_text(
        book.model_dump_json(indent=2, exclude_none=False),
        encoding="utf-8",
    )
    return book


def export_bytes(data_dir: Path, client_name: str) -> bytes:
    """Return the file exactly as stored on disk (1:1 download)."""
    path: Path = book_path(data_dir, client_name)
    if not path.exists():
        raise BookNotFoundError(client_name)
    return path.read_bytes()


def import_bytes(data_dir: Path, client_name: str, payload: bytes) -> BookFile:
    """Validate an uploaded book and write it 1:1 (creates or replaces)."""
    data = json.loads(payload.decode("utf-8"))
    current = BookFile.model_fields["format_version"].default
    version = int(data.get("format_version", 1))
    if version > current:
        raise BookVersionError(f"file format_version {version} is newer than supported {current}")
    data = apply_migrations(data)
    book = BookFile.model_validate(data)
    data_dir.mkdir(parents=True, exist_ok=True)
    path = book_path(data_dir, client_name)
    # Store byte-for-byte what the user uploaded (after validation).
    path.write_bytes(payload)
    return book


def list_books(data_dir: Path) -> list[str]:
    if not data_dir.exists():
        return []
    return sorted(p.stem for p in data_dir.glob("*.json"))
