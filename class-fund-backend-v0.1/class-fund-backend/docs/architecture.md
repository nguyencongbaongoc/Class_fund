# Kiến trúc trực quan

```mermaid
flowchart LR
    FE[Frontend / Liquid Glass UI]
    AI[AI / OCR / Matching Service]
    API[FastAPI Backend]
    DB[(PostgreSQL)]
    LEDGER[Ledger / Financial Core]
    AUDIT[Audit Log]
    ACT[Activity Feed]
    FILES[Receipt Storage]

    FE -->|upload / read / mutation| API
    API -->|store receipt| FILES
    AI -->|get receipt| API
    API -->|AI result candidate| LEDGER
    LEDGER -->|validate| DB
    LEDGER --> AUDIT
    LEDGER --> ACT
    API --> DB
    FE -->|poll status| API

    ACT --> FE
    DB --> FE
```

## Nguyên tắc

`AI -> Backend validation -> DB transaction/uniqueness -> Ledger -> Activity/UI`

Không có đường:

`AI -> Balance`

hoặc:

`Frontend -> new_balance`

## Phần dễ thay thế

- AI có thể đổi OCR model/provider mà không đổi ledger.
- Frontend có thể đổi React/Vue/Next.js mà không đổi financial rules.
- Storage có thể đổi local → S3/Cloudflare R2 mà không đổi API contract chính.
- Queue có thể thêm Celery/RQ/Redis sau Phase 5.
