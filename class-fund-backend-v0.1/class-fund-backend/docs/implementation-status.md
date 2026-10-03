# Implementation status

## Đã có trong starter

- FastAPI + OpenAPI/Swagger
- PostgreSQL cấu hình sẵn
- Alembic baseline
- JWT authentication
- Role middleware
- Accounts + opening balance
- Ledger entries + transactions
- Credit/debit
- Balance tính từ ledger
- Unique bank-account + transaction code
- Idempotency table + request fingerprint
- Upload hash / duplicate upload
- AI internal file endpoint + result callback
- Confidence gate
- Campaign/student/member/payment match foundation
- Revert + reversal entry + audit trail
- Activity/chat API
- Public fund + public bank/QR + public campaigns
- Pagination cơ bản cho transaction/chat
- Docker Compose PostgreSQL

## Cần hoàn thiện trước production

- Redis/queue worker thật và job IDs có monitoring
- Virus/malware scanner thật cho upload
- Perceptual hash thật để bắt ảnh bị resize/recompress
- Object storage + signed URLs
- Rate limiting thực tế (Redis/API gateway)
- CSRF nếu dùng cookie auth
- Token revocation/session store nếu cần logout server-side tức thời
- Security headers/CSP
- Observability + error tracking
- Backup/restore automation
- Stress test thật bằng PostgreSQL với 10/20/50/100 concurrent cases
- Migration generated SQL thay cho baseline `create_all` migration
