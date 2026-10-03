# PHASE 0 — FRONTEND FORENSIC INVENTORY

## Repository: `C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB\classfund\classfund`

### Git Status
- Not a git repository (no `.git` directory found)
- No commit history available for inspection

### Directory Structure
```
classfund/
├── src/
│   ├── assets/
│   ├── components/
│   │   ├── common/
│   │   │   ├── FrostedContextMenu.tsx
│   │   │   ├── LiquidCard.tsx
│   │   │   ├── MobileTabBar.tsx
│   │   │   ├── Navbar.tsx
│   │   │   └── ToastContainer.tsx
│   │   └── modals/
│   │       ├── CreateCampaignModal.tsx
│   │       ├── E2ETesterModal.tsx
│   │       ├── ManualExpenseModal.tsx
│   │       ├── TransactionDetailModal.tsx
│   │       └── WallpaperModal.tsx
│   ├── context/
│   │   └── AppContext.tsx
│   ├── data/
│   │   ├── mockDatabase.ts
│   │   └── wallpapers.ts
│   ├── lib/
│   │   └── liquidglass/
│   │       ├── HtmlCapture.ts
│   │       └── LiquidGlass.ts
│   ├── types/
│   │   └── index.ts
│   ├── utils/
│   │   └── soundEffects.ts
│   ├── views/
│   │   ├── BankQRView.tsx
│   │   ├── CampaignView.tsx
│   │   ├── ChatView.tsx
│   │   ├── DashboardView.tsx
│   │   ├── DonateView.tsx
│   │   ├── LedgerView.tsx
│   │   ├── PublicFundView.tsx
│   │   └── UploadReceiptView.tsx
│   ├── App.tsx
│   ├── index.css
│   └── main.tsx
├── web gay/ (appears to be unused/legacy directory)
├── .env.example
├── .gitignore
├── bun.lock
├── index.html
├── metadata.json
├── package.json
├── tsconfig.json
└── vite.config.ts
```

### Entry Points
- **Main**: `src/main.tsx` → `App.tsx` → `AppProvider` (Context) → Views
- **HTML**: `index.html` — Vite entry with root div
- **Config**: `vite.config.ts` — Vite + React + Tailwind v4, port 3000

### Runtime Versions
- **Package Manager**: Bun (evidenced by `bun.lock`)
- **React**: `^19.0.1`
- **TypeScript**: `^7.0.2`
- **Vite**: `^8.3.0`
- **Tailwind CSS**: `^4.3.3` (v4 alpha/beta)
- **Node Types**: `@types/node ^22.14.0`

### Dependency Manifest (package.json)
```json
{
  "dependencies": {
    "@google/genai": "^2.4.0",
    "@tailwindcss/vite": "^4.3.3",
    "@types/three": "^0.186.0",
    "@vitejs/plugin-react": "^6.1.1",
    "@ybouane/liquidglass": "^1.0.3",
    "dotenv": "^17.2.3",
    "express": "^4.21.2",
    "html-to-image": "^1.11.13",
    "lucide-react": "^0.546.0",
    "motion": "^12.23.24",
    "react": "^19.0.1",
    "react-dom": "^19.0.1",
    "three": "^0.186.1",
    "vite": "^8.3.0"
  },
  "devDependencies": {
    "@types/node": "^22.14.0",
    "@types/react": "^19.3.0",
    "@types/react-dom": "^19.3.0",
    "autoprefixer": "^10.4.21",
    "esbuild": "^0.25.0",
    "tailwindcss": "^4.3.3",
    "tsx": "^4.21.0",
    "typescript": "^7.0.2",
    "@types/express": "^4.17.21"
  }
}
```

### Environment Variables (.env.example)
| Variable | Description |
|----------|-------------|
| GEMINI_API_KEY | **REDACTED** - Google Gemini API key (injected by AI Studio) |
| APP_URL | **REDACTED** - App URL for self-referential links (injected by AI Studio) |

### TypeScript Types (`src/types/index.ts`)
```typescript
UserRole = 'TREASURER' | 'MODERATOR' | 'MEMBER' | 'PUBLIC'
User = { id, name, email, role, avatarUrl, studentCode? }
TransactionType = 'CREDIT' | 'DEBIT' | 'REVERT'
TransactionStatus = 'PENDING' | 'VERIFIED' | 'NEEDS_REVIEW' | 'DUPLICATE' | 'REJECTED' | 'REVERTED'
TransactionSource = 'IMAGE' | 'MANUAL' | 'REVERT'
LedgerEntry = {
  id, type, amount, currency, source, transaction_code, sender_name, uploaded_by,
  created_at, effective_at, status, original_entry_id?, reversal_entry_id?,
  image_url?, image_hash?, note?, campaign_id?, ai_confidence?, extracted_bank?,
  revert_reason?, reverted_by?, reverted_at?
}
StudentRosterItem = { id, full_name, student_code, status, matched_amount?, matched_transaction_code?, paid_at?, notes? }
CollectionCampaign = { id, title, description, expected_amount_per_student, target_students_count, paid_students_count, total_collected_amount, start_at, end_at, status }
ChatMessage = { id, sender_id, sender_name, sender_role, message_type, content, receipt_data?, is_pinned?, created_at }
BankAccountInfo = { bank_name, account_name, account_number, branch, qr_image_url, transfer_syntax_example, deep_link? }
AuditLogItem = { id, actor_name, actor_role, action, entity_type, entity_id, details, created_at }
ViewTab = 'dashboard' | 'ledger' | 'upload' | 'campaign' | 'chat' | 'bank' | 'donate' | 'public'
```

### Mock Database (`src/data/mockDatabase.ts`)
- **Users**: 4 mock users (treasurer, moderator, member, public)
- **Bank Account**: 1 MB Bank account with VietQR image URL
- **Opening Balance**: 500,000 VND
- **Ledger Entries**: 9 entries (7 VERIFIED credits, 1 DEBIT, 1 REVERTED credit + REVERT pair, 1 NEEDS_REVIEW)
- **Students**: 35 students (22 PAID, 13 UNPAID)
- **Campaign**: 1 active campaign (Oct 2026), 50k VND/student, 35 target, 22 paid, 1.1M collected
- **Chat Messages**: 5 messages (announcements, receipts, text)
- **Audit Logs**: 3 entries
- **Helper**: `calculateLedgerBalances()` — computes balance from verified entries only
- **Formatter**: `formatVND()` — Intl.NumberFormat vi-VN

### App Context (`src/context/AppContext.tsx`) — **Central State Management**
**State**:
- `currentUser` (User), `currentTab` (ViewTab)
- `ledgerEntries` (LedgerEntry[]), `studentsRoster` (StudentRosterItem[])
- `campaign` (CollectionCampaign), `chatMessages` (ChatMessage[])
- `auditLogs` (AuditLogItem[]), `balances` (computed)
- UI state: modals, wallpaper, liquid glass settings, toasts, perimeter glow

**Actions**:
- `switchRole(role)` — Switches between 4 mock users
- `addLedgerEntry(entry)` — Adds entry, auto-matches student by name, updates campaign, emits audit + chat
- `revertTransaction(id, reason)` — Creates REVERT entry, marks original REVERTED, updates student/campaign, audit, chat
- `addManualExpense(amount, recipient, reason)` — Creates DEBIT entry
- `sendChatMessage(content, type, isPinned)` — Adds chat message
- `markStudentPaid(id, paid)` — Manual student status toggle
- `resetToDefaultData()` — Resets all state to initial mock data

**Key Financial Logic** (lines 214-260):
- Balance computed from ledger via `calculateLedgerBalances()`
- Student auto-matching: `normalizedSender.includes(student.full_name.toLowerCase())`
- Campaign stats updated on verified credit

### Views Analysis

#### 1. DashboardView (`src/views/DashboardView.tsx`)
- Hero with current balance (large display)
- Quick actions: Upload Receipt, VietQR, Manual Expense (role-gated)
- Bento grid: Total Credit, Total Debit, Campaign Progress
- Class photo banner
- Recent transactions table (5 items)

#### 2. LedgerView (`src/views/LedgerView.tsx`)
- Search + filter tabs (ALL/CREDIT/DEBIT/REVERT) with sliding pill indicator
- Synchronized horizontal scroll between filter bar and table
- Full ledger table with columns: Time, Type, Tx Code, Sender, Amount, Status, Actions
- Click row → TransactionDetailModal

#### 3. UploadReceiptView (`src/views/UploadReceiptView.tsx`) — **Critical for AI Integration**
- **File Upload**: Drag-drop + file input, preview
- **Preset Testing**: 3 buttons (Valid, Duplicate, Low Confidence) — simulates AI results
- **Pipeline Simulation** (lines 77-181): 4-step async simulation with timeouts
  1. Upload (800ms)
  2. AI OCR (1000ms)
  3. Anti-Duplicate Check (1000ms)
  4. Result
- **Duplicate Check** (lines 105-121): Client-side check against `ledgerEntries`
- **Low Confidence Path** (lines 123-148): Creates `NEEDS_REVIEW` entry with `ai_confidence: 68.2`
- **Verified Path** (lines 152-178): Creates `VERIFIED` entry with `ai_confidence: 99.4`, `campaign_id`
- **Result Display**: Color-coded card with confidence, reason, navigation buttons

#### 4. CampaignView (`src/views/CampaignView.tsx`)
- Campaign info + progress bar
- Student roster with PAID/UNPAID badges
- Manual mark paid/unpaid (role-gated)

#### 5. ChatView (`src/views/ChatView.tsx`)
- Message list with RECEIPT/ANNOUNCEMENT/TEXT types
- Receipt messages show thumbnail, amount, status
- Send message input (role-gated types)

#### 6. BankQRView (`src/views/BankQRView.tsx`)
- VietQR image display
- Bank account details
- Copy account number

#### 7. DonateView (`src/views/DonateView.tsx`)
- Public donation page with QR, bank info, syntax guide

#### 8. PublicFundView (`src/views/PublicFundView.tsx`)
- Public fund transparency page
- Balance, income, expense, recent transactions

### Components
- **LiquidCard**: Multiple variants (clear, elevated) with clarity presets
- **Navbar**: Tab navigation, role switcher, user avatar
- **MobileTabBar**: Bottom tab bar for mobile
- **ToastContainer**: Toast notifications
- **FrostedContextMenu**: Right-click context menu
- **Modals**: TransactionDetail, ManualExpense, CreateCampaign, E2ETester, Wallpaper

### API Integration Status
**NO API CALLS IMPLEMENTED** — All data flows through `AppContext` mock state.
- No `fetch`, `axios`, or API client found in source
- No authentication flow (login, token storage, interceptors)
- No environment-based API base URL configuration
- All mutations are local state updates only

### Authentication & Authorization (Frontend Only)
- **Role Switching**: `switchRole()` in AppContext cycles through 4 mock users
- **Role Gating**: Components check `currentUser.role` for UI visibility (e.g., Manual Expense button)
- **No Real Auth**: No login form, no token, no protected routes, no Authorization headers

### CORS Compatibility
- Frontend dev server: `vite.config.ts:14` — port 3000
- Backend CORS: `http://localhost:5173,http://localhost:3000` — **COMPATIBLE**

### Build & Lint Configuration
- **Build**: `vite build`
- **Dev**: `vite --port=3000 --host=0.0.0.0`
- **Lint**: `tsc --noEmit` (TypeScript type check only)
- **No ESLint, Prettier, or test runner configured**

### Missing, Duplicated, Obsolete, Conflicting Modules
- **Missing**: 
  - API client layer (`src/lib/api/`)
  - Authentication flow (login, register, token management)
  - Environment configuration for API base URL
  - Error boundaries
  - React Query / SWR for server state
  - Form validation library (react-hook-form + zod)
- **Duplicated**: None
- **Obsolete**: `web gay/` directory (appears unused)
- **Conflicting**: None

### Key Observations
1. **Complete UI, Zero Backend Integration** — The frontend is a fully functional mock application with sophisticated state management, but zero network calls.
2. **TypeScript Types Match Backend Concepts** — `LedgerEntry`, `TransactionType`, `TransactionStatus`, `TransactionSource` align with backend enums/models.
3. **Field Naming Difference** — Frontend uses camelCase (`transaction_code`, `created_at`, `sender_name`), backend uses snake_case in DB/API but Pydantic serializes to snake_case. Transformation needed.
4. **Decimal vs Number** — Backend uses `Decimal` for amounts, frontend uses `number`. Precision handling needed.
5. **Date Format** — Backend: ISO 8601 with timezone (`datetime`), Frontend: string `YYYY-MM-DD HH:mm` (local). Conversion needed.
6. **AI Integration Simulation** — `UploadReceiptView` simulates the exact 4-step pipeline the backend expects, including duplicate detection and confidence thresholds.

### Confidence Assessment
- **High Confidence**: All source files read, types and logic verified
- **Medium Confidence**: Build/lint not executed, no runtime verification
- **Low Confidence**: Production deployment config not tested