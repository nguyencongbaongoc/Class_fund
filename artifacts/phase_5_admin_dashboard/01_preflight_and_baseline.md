# Phase 5 — Preflight and Baseline Assessment

## Git Status (as of Phase 5 start)

### Current Branch
- Branch: `master`
- HEAD: `f7ac634` - "Merge Phase 3 AI Pipeline + Phase 4 Guest Chat"

### Modified Files (Unstaged)
```
ai/duplicate/__pycache__/service.cpython-312.pyc
ai/duplicate/service.py
class-fund-backend-v0.1/class-fund-backend/.env.example
class-fund-backend-v0.1/class-fund-backend/app/api/routes/messages.py
class-fund-backend-v0.1/class-fund-backend/app/api/routes/vision.py
class-fund-backend-v0.1/class-fund-backend/app/main.py
class-fund-backend-v0.1/class-fund-backend/app/models/models.py
class-fund-backend-v0.1/class-fund-backend/app/schemas/schemas.py
class-fund-backend-v0.1/class-fund-backend/app/services/ollama_client.py
class-fund-backend-v0.1/class-fund-backend/worker/main.py
classfund/classfund/.env.example
classfund/classfund/src/components/chat/MessageItem.tsx
classfund/classfund/src/components/chat/RecallButton.tsx
classfund/classfund/src/hooks/useChat.ts
classfund/classfund/src/lib/recall.ts
classfund/classfund/src/types/chat.ts
```

### New Files (Untracked)
```
ai/tests/__pycache__/test_duplicate_persistence.cpython-312-pytest-9.1.1.pyc
ai/tests/__pycache__/test_review_api.cpython-312-pytest-9.1.1.pyc
ai/tests/test_duplicate_persistence.py
ai/tests/test_review_api.py
artifacts/master_consolidation/
artifacts/phase_2_merge_resolution/
artifacts/phase_3_1_4_1/
artifacts/phase_3_1_4_1_closure/
artifacts/residual_blocker_closure/
class-fund-backend-v0.1/class-fund-backend/alembic/versions/0005_add_attachment_ids_and_ai_fields.py
class-fund-backend-v0.1/class-fund-backend/app/api/routes/review.py
classfund/classfund/src/components/chat/ExtractionResultDisplay.tsx
classfund/classfund/src/hooks/useRecall.ts
classfund/classfund/src/lib/retry.ts
```

### Existing Artifacts (from previous phases)
- `artifacts/master_consolidation/` - Phase 1-2 consolidation
- `artifacts/phase_2_merge_resolution/` - Phase 2 merge
- `artifacts/phase_3_1_4_1/` - Phase 3.1 + 4.1 artifacts
- `artifacts/phase_3_1_4_1_closure/` - Phase 3.1 + 4.1 closure
- `artifacts/residual_blocker_closure/` - Residual blocker closure

## Backend Architecture (Existing)

### API Routes (class-fund-backend-v0.1/class-fund-backend/app/api/routes/)
- `auth.py` - Authentication (login, logout, me)
- `fund.py` - Fund management (balance, transactions, accounts, bank accounts, manual credit/debit, revert)
- `review.py` - AI Review queue (list, detail, approve, reject) - **Phase 3.1**
- `ai_internal.py` - Internal AI worker endpoints
- `messages.py` - Chat messages
- `chat.py` - Chat functionality
- `uploads.py` - File uploads
- `vision.py` - Vision/OCR processing
- `health.py` - Health check
- `campaigns.py` - Collection campaigns
- `public.py` - Public endpoints

### Key Backend Models
- `User` with Role: `OWNER_TREASURER`, `MODERATOR`, `MEMBER`, `PUBLIC`
- `Account` - Fund accounts with opening_balance
- `Transaction` - Ledger entries (CREDIT, DEBIT, REVERT)
- `LedgerEntry` - Immutable ledger records
- `Upload` - File uploads with status tracking
- `ExtractedTransaction` - AI extraction results
- `Message` - Chat messages with status
- `WorkerStatus` - Worker health tracking
- `AuditLog` - Immutable audit trail
- `RecallToken` - Recall authorization
- `BankAccount` - Bank account info
- `CollectionCampaign` - Fundraising campaigns
- `CampaignMember` - Campaign participants
- `PaymentMatch` - AI payment matching

### Key Backend Services
- `ledger.py` - Financial posting, balance calculation, idempotency, verification
- `audit.py` - Audit logging
- `activity.py` - Chat activity emission
- `supabase_client.py` - Supabase integration
- `ollama_client.py` - AI service client

### Authentication & Authorization
- JWT-based auth with `OAuth2PasswordBearer`
- Role-based access via `require_roles()` dependency
- AI service auth via `require_ai_service()` header check
- Revoked token tracking

## Frontend Architecture (Existing)

### Framework Stack
- React 19 with TypeScript
- Vite 8 for build/dev
- Tailwind CSS 4
- Lucide React for icons
- Motion for animations

### Key Components
- `AppContext` - Global state management (mock data currently)
- `Navbar` - Navigation with role switching
- `MobileTabBar` - Mobile navigation
- `LiquidCard` / `LiquidGlassCard` - Glassmorphism UI cards
- `ToastContainer` - Notifications
- `FrostedContextMenu` - Right-click context menu

### Views (src/views/)
- `DashboardView` - Main dashboard with balance, recent transactions
- `LedgerView` - Transaction table with filtering
- `UploadReceiptView` - Receipt upload
- `CampaignView` - Campaign management
- `ChatView` - Chat interface
- `BankQRView` - VietQR codes
- `DonateView` - Donation page
- `PublicFundView` - Public fund display
- `GuestChatPage` - Guest chat (Phase 4)

### Current Data Source
- **MOCK DATA** from `src/data/mockDatabase.ts`
- All financial data, ledger entries, users are mocked
- No real API integration yet (except chat/file upload via `api.ts`)

### API Client (src/lib/api.ts)
- Upload receipt
- Get upload status
- Create/list/recall messages
- Public fund/bank account info
- **Missing:** Authenticated fund/ledger/admin endpoints

## Phase 5 Implementation Baseline

### What Exists and Can Be Reused
1. **Backend Review API** (`/internal/review`) - Fully implemented with approval/rejection
2. **Backend Fund API** (`/fund`) - Balance, transactions, manual entries, revert
3. **Backend Auth** - JWT with role-based access
4. **Backend Audit Log** - `AuditLog` model and `write_audit` service
5. **Backend Worker Status** - `WorkerStatus` model, worker heartbeat
6. **Frontend UI Components** - LiquidCard, Navbar, Toast, etc.
6. **Frontend Routing** - Tab-based navigation in App.tsx
7. **Frontend Types** - TypeScript interfaces for all domain models

### What Needs to Be Built
1. **Admin Dashboard View** - New view component for admin overview
2. **AI Review Queue View** - New view for review management
3. **Admin Ledger Management** - Enhanced ledger view with admin actions
4. **Audit Log View** - New view for audit trail
5. **Worker/System Monitoring View** - New view for system health
6. **User/Role Management View** - If backend supports it
7. **API Client Extensions** - Authenticated admin endpoints
8. **Real Data Integration** - Replace mock data with API calls
9. **Role-based Navigation** - Show/hide admin tabs based on role
10. **Authentication Integration** - Login flow, token management

### Missing Backend Endpoints (Need Investigation)
- Audit log listing endpoint
- Worker status listing endpoint
- System health/queue status endpoint
- User management endpoints (list users, update roles)

## Action Items for Phase 5
1. ✅ Create artifacts directory and scope document
2. 🔄 Create architecture mapping document (next)
3. 🔄 Map API contracts to dashboard screens
4. 🔄 Identify missing backend contracts
5. 🔄 Document role/permission matrix
6. 🔄 Implement missing backend endpoints
7. 🔄 Implement frontend admin views
8. 🔄 Integrate real API calls
9. 🔄 Add authentication flow
10. 🔄 Run tests and TypeScript checks