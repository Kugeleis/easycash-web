"""FastAPI application for EasyCash&Tax Web."""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, UploadFile
from fastapi.staticfiles import StaticFiles

from easycash_web.models import (
    Account,
    BookFile,
    Booking,
    Business,
    Client,
    RecurringBooking,
    TaxRate,
)
from easycash_web.storage import (
    DATA_DIR as STORAGE_DIR,
)
from easycash_web.storage import (
    BookNotFoundError,
    BookVersionError,
    export_bytes,
    import_bytes,
    list_books,
    load_book,
    save_book,
)

app = FastAPI(title="EasyCash&Tax Web", version="0.2.0")

# ── Static file serving (import map, vendor, HTML) ─────────────────────────

STATIC_DIR = Path(__file__).parent.parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── Health / schema ─────────────────────────────────────────────────────────


@app.get("/api/v1/health", include_in_schema=False)
async def health():
    return {"status": "ok", "format_version": 1}


@app.get("/api/v1/schema", include_in_schema=False)
async def schema():
    """Serve generated JSON Schema from Pydantic models."""
    return BookFile.schema()


# ── Book file CRUD ───────────────────────────────────────────────────────────


@app.get("/api/v1/book/{client_name}", response_model=BookFile)
async def get_book(client_name: str):
    try:
        return load_book(STORAGE_DIR, client_name)
    except BookNotFoundError:
        raise HTTPException(status_code=404, detail="book not found") from None


@app.post("/api/v1/book/{client_name}", response_model=BookFile)
async def save_book_endpoint(client_name: str, payload: BookFile):
    try:
        return save_book(STORAGE_DIR, client_name, payload)
    except BookVersionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@app.get("/api/v1/book/{client_name}/download")
async def download_book(client_name: str):
    """Download the book file exactly as stored (1:1)."""
    try:
        data = export_bytes(STORAGE_DIR, client_name)
    except BookNotFoundError:
        raise HTTPException(status_code=404, detail="book not found") from None
    return Response(
        content=data,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{client_name}.json"'},
    )


@app.post("/api/v1/book/{client_name}/upload")
async def upload_book(client_name: str, file: UploadFile):
    """Upload a book file — replaces or creates 1:1."""
    payload = await file.read()
    try:
        book = import_bytes(STORAGE_DIR, client_name, payload)
    except BookVersionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"invalid JSON: {e}") from e
    return {"saved": True, "revision": book.revision}


# ── List clients ────────────────────────────────────────────────────────────


@app.get("/api/v1/clients")
async def list_clients():
    names = list_books(STORAGE_DIR)
    books = []
    for n in names:
        try:
            b = load_book(STORAGE_DIR, n)
            books.append({"id": n, "name": b.meta.get("client_name", n), "revision": b.revision})
        except Exception:
            books.append({"id": n, "name": n, "revision": 0})
    return {"clients": books}


# ── Accounts ─────────────────────────────────────────────────────────────────


@app.get("/api/v1/accounts/{client_name}")
async def get_accounts(client_name: str):
    book = await get_book(client_name)
    return {"accounts": book.accounts}


@app.post("/api/v1/accounts/{client_name}")
async def add_account(client_name: str, account: dict):
    book = await get_book(client_name)
    acc = Account(**account)
    book.accounts.append(acc)
    return save_book(STORAGE_DIR, client_name, book)


@app.put("/api/v1/accounts/{client_name}/{account_id}")
async def update_account(client_name: str, account_id: str, account: dict):
    book = await get_book(client_name)
    for i, a in enumerate(book.accounts):
        if a.id == account_id:
            book.accounts[i] = Account(**account)
            return save_book(STORAGE_DIR, client_name, book)
    raise HTTPException(status_code=404, detail="account not found")


@app.delete("/api/v1/accounts/{client_name}/{account_id}")
async def delete_account(client_name: str, account_id: str):
    book = await get_book(client_name)
    book.accounts = [a for a in book.accounts if a.id != account_id]
    return save_book(STORAGE_DIR, client_name, book)


# ── Bookings ─────────────────────────────────────────────────────────────────


@app.get("/api/v1/bookings/{client_name}")
async def get_bookings(client_name: str):
    book = await get_book(client_name)
    return {"bookings": book.bookings}


@app.post("/api/v1/bookings/{client_name}")
async def add_booking(client_name: str, booking: dict):
    book = await get_book(client_name)
    b = Booking(**booking)
    book.bookings.append(b)
    return save_book(STORAGE_DIR, client_name, book)


@app.put("/api/v1/bookings/{client_name}/{booking_id}")
async def update_booking(client_name: str, booking_id: str, booking: dict):
    book = await get_book(client_name)
    for i, b in enumerate(book.bookings):
        if b.id == booking_id:
            book.bookings[i] = Booking(**booking)
            return save_book(STORAGE_DIR, client_name, book)
    raise HTTPException(status_code=404, detail="booking not found")


@app.delete("/api/v1/bookings/{client_name}/{booking_id}")
async def delete_booking(client_name: str, booking_id: str):
    book = await get_book(client_name)
    book.bookings = [b for b in book.bookings if b.id != booking_id]
    return save_book(STORAGE_DIR, client_name, book)


# ── Tax rates ────────────────────────────────────────────────────────────────


@app.get("/api/v1/tax-rates/{client_name}")
async def get_tax_rates(client_name: str):
    book = await get_book(client_name)
    return {"tax_rates": book.tax_rates}


@app.post("/api/v1/tax-rates/{client_name}")
async def add_tax_rate(client_name: str, rate: dict):
    book = await get_book(client_name)
    r = TaxRate(**rate)
    book.tax_rates.append(r)
    return save_book(STORAGE_DIR, client_name, book)


@app.put("/api/v1/tax-rates/{client_name}/{rate_id}")
async def update_tax_rate(client_name: str, rate_id: str, rate: dict):
    book = await get_book(client_name)
    for i, r in enumerate(book.tax_rates):
        if r.id == rate_id:
            book.tax_rates[i] = TaxRate(**rate)
            return save_book(STORAGE_DIR, client_name, book)
    raise HTTPException(status_code=404, detail="tax rate not found")


@app.delete("/api/v1/tax-rates/{client_name}/{rate_id}")
async def delete_tax_rate(client_name: str, rate_id: str):
    book = await get_book(client_name)
    book.tax_rates = [r for r in book.tax_rates if r.id != rate_id]
    return save_book(STORAGE_DIR, client_name, book)


# ── Recurring bookings ──────────────────────────────────────────────────────


@app.get("/api/v1/recurring/{client_name}")
async def get_recurring(client_name: str):
    book = await get_book(client_name)
    return {"recurring": book.recurring}


@app.post("/api/v1/recurring/{client_name}")
async def add_recurring(client_name: str, rec: dict):
    book = await get_book(client_name)
    r = RecurringBooking(**rec)
    book.recurring.append(r)
    return save_book(STORAGE_DIR, client_name, book)


# ── Business ────────────────────────────────────────────────────────────────


@app.get("/api/v1/businesses/{client_name}")
async def get_businesses(client_name: str):
    book = await get_book(client_name)
    return {"businesses": book.clients[0].businesses if book.clients else []}


@app.post("/api/v1/businesses/{client_name}")
async def add_business(client_name: str, biz: dict):
    book = await get_book(client_name)
    if not book.clients:
        book.clients.append(Client(name=client_name))
    b = Business(**biz)
    book.clients[0].businesses.append(b)
    return save_book(STORAGE_DIR, client_name, book)


# ── Startup: ensure DATA_DIR exists ───────────────────────────────────────────


@app.on_event("startup")
async def on_startup():
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
