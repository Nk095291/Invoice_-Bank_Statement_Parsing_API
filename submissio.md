# Project Submission Summary
## Financial Document Parsing API

---

## 1. GitHub Repository

**Repo:** [https://github.com/Nk095291/Invoice_-Bank_Statement_Parsing_API](https://github.com/Nk095291/Invoice_-Bank_Statement_Parsing_API)

---

## 2. Local Setup (README)

Full setup instructions are available in the README at the repository root.

**Quick start:**
```bash
cp .env.example .env
docker compose up --build
```

This spins up all four services defined in `docker-compose.yml`:

| Service | Role |
|---|---|
| `db` | PostgreSQL 16 |
| `redis` | Celery message broker |
| `web` | Django app — runs migrations + `runserver :8000` |
| `worker` | Celery worker (`celery -A myproject worker`) |

---

## 3. API Documentation

API documentation is provided as a **Postman collection export** (attached separately / included in the repository).

---

## 4. Deployment Plan

### Local / Docker Compose *(implemented)*

`docker-compose.yml` defines all four services (see Section 2). Run with:

```bash
cp .env.example .env
docker compose up --build
```

### Cloud — AWS *(planned architecture)*

| Component | AWS Service |
|---|---|
| `web` + `worker` tasks | ECS Fargate |
| PostgreSQL | RDS (PostgreSQL) |
| Redis | ElastiCache |
| File storage | S3 (replaces local `FileField` in production) |
| Traffic routing | ALB → web service |

In production, `MEDIA_ROOT` file storage would be replaced with an S3-backed storage backend (e.g., `django-storages`).

---

## 5. Database Schema

### Entity Relationship Diagram

```mermaid
erDiagram
    auth_user ||--o{ documents_document : owns
    documents_document ||--o{ documents_lineitem : has
    documents_document ||--o{ documents_banktransaction : has
    documents_document {
        uuid doc_id PK
        string content_hash UK_partial
        int user_id FK
        string document_type
        string status
        string vendor
        date document_date
        decimal total_amount
        string currency
        json metadata
        bool is_deleted
        datetime deleted_at
    }
    documents_lineitem {
        int id PK
        uuid document_id FK
        string description
        decimal amount
    }
    documents_banktransaction {
        int id PK
        uuid document_id FK
        date transaction_date
        string description
        decimal debit
        decimal credit
        decimal balance
        string currency
    }
```

### `documents_document` (core table)

| Field | Type | Purpose |
|---|---|---|
| `doc_id` | UUID (PK) | Opaque ID returned to clients after upload |
| `content_hash` | String (partial unique) | SHA-256 of file bytes; enforces deduplication when `is_deleted=false` |
| `user_id` | Int (FK → auth_user) | Ownership via `X-User-Id` header |
| `document_type` | String | `invoice_pdf` or `bank_statement_csv` |
| `status` | String | `processing` / `completed` / `failed` |
| `vendor` | String | Normalized vendor name extracted from document |
| `document_date` | Date | Normalized document/invoice date |
| `total_amount` | Decimal | Normalized total amount |
| `currency` | String | ISO currency code |
| `metadata` | JSON | Invoice #, subtotal, tax, and other extras |
| `file` | FileField | Stored under `media/uploads/YYYY/MM/` |
| `error_message` | String | Parse failure detail (populated on `failed` status) |
| `is_deleted` | Bool | Soft delete flag |
| `deleted_at` | DateTime | Timestamp of soft deletion |

### `documents_lineitem` (child — PDF invoices)

| Field | Type | Purpose |
|---|---|---|
| `id` | Int (PK) | — |
| `document_id` | UUID (FK) | Parent document |
| `description` | String | Line item description |
| `amount` | Decimal | Line item amount |
| `quantity` | Decimal | Quantity (if present) |
| `sort_order` | Int | Preserves original line order |

### `documents_banktransaction` (child — CSV bank statements)

| Field | Type | Purpose |
|---|---|---|
| `id` | Int (PK) | — |
| `document_id` | UUID (FK) | Parent document |
| `transaction_date` | Date | Normalized transaction date |
| `description` | String | Transaction description |
| `debit` | Decimal | Debit amount |
| `credit` | Decimal | Credit amount |
| `balance` | Decimal | Running balance |
| `currency` | String | ISO currency code |

### Indexes

- `(user_id, status)` — composite, for filtered user queries
- `vendor`, `document_date`, `currency`, `document_type` — individual indexes for search/filter
- Partial unique on `content_hash` where `is_deleted = false` — deduplication guard

---

## 6. Sample Input Files

Sample PDF invoices and CSV bank statements are available in the repository:

📁 [/samples](https://github.com/Nk095291/Invoice_-Bank_Statement_Parsing_API/tree/master/samples)

---

## 7. AI Tool Usage

### Claude (claude.ai)
- **Used for:** Initial architecture planning questions, database design decisions (UUID vs filename key, SQLite vs Postgres trade-offs), and this submission document.
- **Chat history:** [https://claude.ai/share/d6b8d948-b77c-4377-a8e6-220535761aaf](https://claude.ai/share/d6b8d948-b77c-4377-a8e6-220535761aaf)

### Cursor (Claude / Auto Agent)
- **Used for:** Architecture planning (Phase 1–2 via Cursor's Plan mode), Django/DRF implementation, Celery/Windows troubleshooting, Postman-aligned test writing, and README drafts.
- **Plan 1:** [/myproject/logs/plan1.md](https://github.com/Nk095291/Invoice_-Bank_Statement_Parsing_API/blob/master/myproject/logs/plan1.md)
- **Plan 2:** [/myproject/logs/plan2.md](https://github.com/Nk095291/Invoice_-Bank_Statement_Parsing_API/blob/master/myproject/logs/plan2.md)
- **Test case instructions:** [/myproject/logs/testcase_standard.txt](https://github.com/Nk095291/Invoice_-Bank_Statement_Parsing_API/blob/master/myproject/logs/testcase_standard.txt)

---

## 8. Known Limitations & Assumptions

| Area | Limitation / Assumption |
|---|---|
| **Authentication** | `X-User-Id` header is a placeholder for testing only — not real auth. APIs are designed to accept it so authentication middleware can be plugged in later without structural changes. |
| **Framework** | Used Django/DRF instead of the spec's suggested FastAPI. Functionally equivalent REST API — chosen due to stronger familiarity with Django. |
| **API Docs** | Used Postman for API documentation instead of Swagger screenshots. Auto-docs available at `/api/schema/swagger-ui/` when running locally. |
| **File type detection** | Assumed PDF = invoice, CSV = bank statement. A MIME-type-based classifier was not implemented due to time constraints. |
| **File storage** | Media files stored in a local folder (`media/`). In production this would be replaced with AWS S3 via `django-storages`. The `media/` folder and `logs/` are committed to this repo for reviewer reference only. |
| **Caching** | No response caching implemented. |
| **Rate limiting** | No rate limiting implemented. |
| **Bulk upload** | Single file per request only; no bulk upload endpoint. |
| **Parsing robustness** | Parser handles common format variations (date formats, currency symbols, missing fields) but may not cover all real-world edge cases. |

---

*Submitted by: Nk095291*