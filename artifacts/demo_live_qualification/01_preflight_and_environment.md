# Preflight and Environment Report

## Git Status
- **Branch**: master
- **HEAD**: f7ac634 - "Merge Phase 3 AI Pipeline + Phase 4 Guest Chat"
- **Working Tree**: Clean except for modified files and untracked artifacts
- **No branches or worktrees**: Confirmed working directly on master

## Repository Structure

### Backend (FastAPI)
```
class-fund-backend-v0.1/class-fund-backend/
├── app/
│   ├── api/
│   │   ├── deps.py
│   │   └── routes/
│   │       ├── admin.py         # Admin dashboard APIs
│   │       ├── ai_internal.py   # Internal AI endpoints
│   │       ├── auth.py          # Authentication
│   │       ├── campaigns.py     # Campaign management
│   │       ├── chat.py          # Chat messaging
│   │       ├── fund.py          # Fund operations
│   │       ├── health.py        # Health checks
│   │       ├── messages.py      # Message processing
│   │       ├── public.py        # Public endpoints
│   │       ├── review.py        # Human review queue
│   │       ├── uploads.py       # File uploads
│   │       └── vision.py        # Vision extraction
│   ├── core/
│   │   ├── config.py            # Configuration
│   │   └── security.py          # Security utilities
│   ├── db/
│   │   ├── base.py              # SQLAlchemy base
│   │   └── session.py           # Database session
│   ├── models/
│   │   └── models.py            # SQLAlchemy models
│   ├── schemas/
│   │   ├── admin.py             # Admin schemas
│   │   ├── __init__.py
│   │   └── schemas.py           # Core schemas
│   ├── services/
│   │   ├── activity.py          # Activity tracking
│   │   ├── audit.py             # Audit logging
│   │   ├── ledger.py            # Financial ledger (CRITICAL)
│   │   ├── ollama_client.py     # Ollama vision client
│   │   └── supabase_client.py   # Supabase integration
│   └── main.py                  # FastAPI application
├── worker/
│   └── main.py                  # Persistent worker
├── tests/
│   ├── test_admin.py
│   ├── test_financial_core.py
│   ├── test_idempotency.py
│   └── test_recall.py
└── alembic/                     # Database migrations
```

### Frontend (React + Vite)
```
classfund/classfund/
├── src/
│   ├── components/
│   │   ├── chat/
│   │   ├── common/
│   │   └── modals/
│   ├── context/
│   │   └── AppContext.tsx
│   ├── data/
│   │   └── mockDatabase.ts
│   ├── hooks/
│   ├── lib/
│   ├── pages/
│   ├── types/
│   ├── utils/
│   ├── views/
│   │   ├── AdminDashboardView.tsx
│   │   ├── AdminLedgerView.tsx
│   │   ├── AIReviewQueueView.tsx
│   │   ├── AuditLogView.tsx
│   │   ├── SystemMonitoringView.tsx
│   │   └── ...
│   ├── App.tsx
│   ├── index.css
│   └── main.tsx
└── package.json
```

### AI Package
```
ai/
├── contracts.py           # Pydantic contracts for AI pipeline
├── duplicate/
├── extraction/
├── matching/
├── ocr/
├── verification/
├── worker/
│   └── queue.py
└── tests/
```

## Environment Configuration

### Backend Environment (.env.example)
- `DATABASE_URL` - PostgreSQL connection string
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Service role key (admin)
- `SUPABASE_ANON_KEY` - Anonymous key (frontend)
- `SUPABASE_JWT_SECRET` - JWT signing secret
- `OLLAMA_BASE_URL` - http://127.0.0.1:11434
- `OLLAMA_VISION_MODEL` - qwen2.5vl:3b
- `OLLAMA_TEXT_MODEL` - qwen3.5:4b
- `OLLAMA_TIMEOUT` - 120s
- `OLLAMA_MAX_RETRIES` - 3
- `AI_CONFIDENCE_THRESHOLD` - 0.9
- `WORKER_ID` - Worker identifier
- `LEASE_DURATION` - 300s

### Frontend Environment (.env.example)
- `VITE_API_BASE_URL` - Backend API URL

## Existing Test Infrastructure
- Backend: pytest with in-memory SQLite for unit/integration tests
- Test files: test_financial_core.py, test_idempotency.py, test_recall.py, test_admin.py
- All tests use isolated in-memory databases

## Current Phase Artifacts
- phase_5_admin_dashboard/
- phase_5_1_closure/
- phase_5_2_remediation/
- demo_live_qualification/ (new)

## Isolation Verification
✅ No production credentials found in codebase
✅ Tests use in-memory SQLite
✅ .env.example files only contain placeholders
✅ No hardcoded secrets in source code
✅ Simulation infrastructure will use isolated test databases

## Preflight Checks Passed
- [x] Git repository clean
- [x] No branches/worktrees to manage
- [x] Target branch is master
- [x] Preserved milestones documented
- [x] Environment isolation verified
- [x] Test infrastructure available
- [x] Existing architecture understood