# Django Financial Documents Backend

Production-oriented Django REST API for uploading PDF invoices and CSV bank statements, extracting structured financial data, and persisting it in PostgreSQL.

## Features (Phase 1)

- `POST /documents/upload/` — upload PDF or CSV (multipart field: `file`)
- `GET /documents/{doc_id}/` — retrieve parsed document
- `PATCH /documents/{doc_id}/` — update metadata (vendor, date, currency, metadata JSON)
- `DELETE /documents/{doc_id}/` — soft-delete document
- SHA-256 content hash deduplication (409 on duplicate)
- Optional `X-User-Id` header for ownership testing
- Structured logging via `AppLogger`

## Tech Stack

- Django 6 + Django REST Framework
- PostgreSQL 16
- pdfplumber (PDF text extraction)
- Docker Compose

## Quick Start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

API: http://localhost:8000/documents/upload/

Admin: http://localhost:8000/admin/

## Local Development (without Docker)

### Prerequisites

- Python 3.12+
- PostgreSQL running locally

### Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Create database (psql)
# CREATE USER documents_user WITH PASSWORD 'documents_pass';
# CREATE DATABASE documents_db OWNER documents_user;

cp .env.example .env
# Set POSTGRES_HOST=localhost in .env

python scripts/generate_sample_pdf.py
cd myproject
python manage.py migrate
python manage.py createsuperuser   # optional
python manage.py runserver
```

## API Examples

### Upload PDF invoice

```bash
curl -X POST http://localhost:8000/documents/upload/ \
  -H "X-User-Id: 1" \
  -F "file=@samples/invoice_acme.pdf"
```

Response `201`:

```json
{"doc_id": "550e8400-e29b-41d4-a716-446655440000", "status": "completed"}
```

### Upload CSV bank statement

```bash
curl -X POST http://localhost:8000/documents/upload/ \
  -F "file=@samples/bank_statement.csv"
```

### Duplicate upload (409)

```bash
curl -X POST http://localhost:8000/documents/upload/ \
  -F "file=@samples/invoice_acme.pdf"
```

```json
{"detail": "Duplicate document", "doc_id": "550e8400-e29b-41d4-a716-446655440000"}
```

### Get document

```bash
curl http://localhost:8000/documents/{doc_id}/
```

### Update metadata

```bash
curl -X PATCH http://localhost:8000/documents/{doc_id}/ \
  -H "Content-Type: application/json" \
  -d '{"vendor": "Acme Corporation", "currency": "USD"}'
```

### Delete document

```bash
curl -X DELETE http://localhost:8000/documents/{doc_id}/
```

Returns `204 No Content`. Subsequent GET returns `404`.

## Database Schema

### `documents_document`

| Column | Description |
|--------|-------------|
| `doc_id` | UUID primary key (client-facing ID) |
| `content_hash` | SHA-256 hex (deduplication) |
| `user_id` | FK to auth user (nullable) |
| `document_type` | `invoice_pdf` or `bank_statement_csv` |
| `status` | `processing`, `completed`, `failed` |
| `vendor`, `document_date`, `total_amount`, `currency` | Extracted summary |
| `metadata` | JSON (invoice #, subtotal, tax, etc.) |
| `is_deleted`, `deleted_at` | Soft delete |

### `documents_lineitem` (PDF invoices)

Child rows: description, amount, quantity, sort_order.

### `documents_banktransaction` (CSV statements)

Child rows: transaction_date, description, debit, credit, balance, currency.

## Parsing Notes

Handles messy real-world input:

- Dates: `YYYY-MM-DD`, `DD/MM/YYYY`, `Jan 15 2024`
- Amounts: with/without `$`, commas, parentheses for negatives
- CSV: flexible column names and reordering (`csvDate` vs `date`, etc.)
- Missing fields stored as null; partial parse allowed

## Deployment Plan (summary)

1. **Render / Railway / Fly.io**: Deploy `web` service + managed PostgreSQL
2. **AWS**: ECS/Fargate + RDS PostgreSQL + S3 for media files
3. **GCP**: Cloud Run + Cloud SQL
4. Set `DEBUG=False`, strong `DJANGO_SECRET_KEY`, restrict `ALLOWED_HOSTS`
5. Use Gunicorn + Nginx in production
6. Phase 2: Celery + Redis for async parsing

## Known Limitations

- Parsing is synchronous (blocks upload request)
- PDF parsing requires text-extractable PDFs (no OCR)
- `X-User-Id` is not authenticated
- No list/search endpoints yet
- Soft-deleted documents free the file from storage but retain DB row

## Project Structure

```
myproject/
  core/logging.py          # AppLogger
  documents/
    models.py
    parsers/               # PDF + CSV parsers
    services/              # DocumentService
    views.py               # REST endpoints
```
