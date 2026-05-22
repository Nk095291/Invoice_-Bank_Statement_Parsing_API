# Django Financial Documents Backend

Production-oriented Django REST API for uploading PDF invoices and CSV bank statements, extracting structured financial data, and persisting it in PostgreSQL.

## Features

### Phase 1
- `POST /documents/upload/` — upload PDF or CSV (multipart field: `file`)
- `GET /documents/{doc_id}/` — retrieve parsed document
- `PATCH /documents/{doc_id}/` — update metadata
- `DELETE /documents/{doc_id}/` — soft-delete document
- SHA-256 deduplication (409 on duplicate active document)
- Re-upload after soft-delete allowed (partial unique index on `content_hash`)
- Optional `X-User-Id` header for ownership testing
- Structured logging via `AppLogger`

### Phase 2
- **Async parsing** via Celery + Redis (upload returns `processing` immediately)
- **GET while processing** returns a clear message instead of full payload
- **Invalid `doc_id`** returns JSON `400` (not Django HTML 404)
- **`GET /documents/`** — list, search, and filter with pagination

## Tech Stack

- Django 6 + Django REST Framework
- PostgreSQL 16
- Celery + Redis (background parsing)
- pdfplumber (PDF text extraction)
- Docker Compose

## Quick Start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

Services:
- **web** — http://localhost:8000
- **worker** — Celery parser
- **db** — PostgreSQL
- **redis** — message broker

## Local Development

### Prerequisites

- Python 3.12+
- PostgreSQL
- Redis (for async parsing)

### Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# POSTGRES_HOST=localhost, CELERY_BROKER_URL=redis://localhost:6379/0

python scripts/generate_sample_pdf.py
cd myproject
python manage.py migrate
python manage.py runserver
```

**Terminal 2 — Celery worker (required for parsing):**

```bash
cd myproject
celery -A myproject worker -l info
```

On **Windows**, the project uses the `solo` pool automatically (avoids multiprocessing `PermissionError`). You can also pass it explicitly:

```bash
celery -A myproject worker -l info --pool=solo
```

**Optional:** set `SYNC_PARSE=true` in `.env` to parse inline without Redis/Celery.

## API Reference

### Upload

```bash
curl -X POST http://localhost:8000/documents/upload/ \
  -H "X-User-Id: 1" \
  -F "file=@samples/invoice_acme.pdf"
```

Response `201`:

```json
{"doc_id": "uuid-here", "status": "processing"}
```

Poll `GET /documents/{doc_id}/` until `status` is `completed` or `failed`.

### Get document

```bash
curl http://localhost:8000/documents/{doc_id}/
```

While processing (`200`):

```json
{
  "doc_id": "uuid-here",
  "status": "processing",
  "detail": "Document is still being processed."
}
```

When complete (`200`): full document with `line_items` or `transactions`.

**Invalid doc_id** (incomplete UUID, etc.) → `400`:

```json
{"detail": "Invalid document id format."}
```

**Unknown doc_id** → `404`:

```json
{"detail": "Not found."}
```

### List, search, and filter

```bash
curl "http://localhost:8000/documents/?vendor=acme&status=completed&currency=USD"
```

| Query param | Description |
|-------------|-------------|
| `vendor` | Case-insensitive substring match |
| `date_from` | `document_date >=` (flexible date formats) |
| `date_to` | `document_date <=` |
| `amount_min` | `total_amount >=` |
| `amount_max` | `total_amount <=` |
| `currency` | Exact match (e.g. `USD`) |
| `document_type` | `invoice_pdf` or `bank_statement_csv` |
| `status` | `processing`, `completed`, `failed` |
| `page` | Page number (20 per page default) |

With `X-User-Id` header, results are scoped to that user's documents.

### Update metadata

```bash
curl -X PATCH http://localhost:8000/documents/{doc_id}/ \
  -H "Content-Type: application/json" \
  -d '{"vendor": "Acme Corporation", "currency": "USD"}'
```

### Delete

```bash
curl -X DELETE http://localhost:8000/documents/{doc_id}/
```

Returns `204`. Same file can be uploaded again after delete.

### Duplicate upload

```json
{"detail": "Duplicate document", "doc_id": "existing-uuid"}
```

Status `409`.

## Running Tests

```bash
cd myproject
python manage.py test documents
```

Tests use in-memory SQLite and `CELERY_TASK_ALWAYS_EAGER=True` automatically.

## Project Structure

```
myproject/
  core/logging.py
  documents/
    parsers/
    services/document_service.py
    tasks.py              # Celery parse task
    views.py
    tests/                # API tests (Postman-aligned)
  myproject/celery.py
```

## Known Limitations

- Celery worker must be running or parsing stays in `processing`
- PDF parsing requires text-extractable PDFs (no OCR)
- `X-User-Id` is not authenticated
- List search is document-level only (not line items / transactions)

## Environment Variables

See [`.env.example`](.env.example) for `POSTGRES_*`, `CELERY_*`, `SYNC_PARSE`, `LOG_LEVEL`, etc.
