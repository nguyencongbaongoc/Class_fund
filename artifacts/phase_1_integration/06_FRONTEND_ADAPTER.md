# 06_FRONTEND_ADAPTER.md

## Phase 1 Frontend Data Adapter Foundation

### Source Evidence (Phase 0)
- 11_HYBRID_ARCHITECTURE_COMPATIBILITY.md: Existing frontend has zero `fetch`/network code; `AppContext` uses mock `MOCK_USERS`; `mockDatabase.ts` is production source replacement target.
- 02_FRONTEND_FORENSIC_INVENTORY.md: Full Liquid Glass design; `ChatView`, `UploadReceiptView`, `LedgerView`, `DashboardView` fully functional with mock data.
- 15_CHAT_REALTIME_COMPATIBILITY.md: `ChatView` reuse confirmed; adapter needed to replace `AppContext.chatMessages` with `useRealtimeMessages()`.
- 19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md: Photo upload simulated (`URL.createObjectURL`); full name input exists only in `UploadReceiptView`.

### Adapter Structure (Phase 1 Skeleton — Existing Views Preserved)
```
src/
  lib/
    supabase/
      client.ts          # Supabase client (anon key only; no service role)
      messages.ts        # Typed message adapter (read/write contracts)
      auth.ts            # Auth session and role fetch adapter
      storage.ts         # Storage upload/download adapter (photo reference path)
```
- Evidence: 9 (minimum new code: `src/lib/supabase/`), 11 (adapter recommendations), 15 (hook patterns).

### Design Rules (No Rewrite)
- Existing views (`ChatView`, `UploadReceiptView`, etc.) NOT rewritten; only data source replaced through adapter.
- Mock data (`mockDatabase.ts`) retained as development fallback; not deleted until production flow verified.
- `AppContext` mock state gradually replaced; adapter provides typed interface matching `ChatMessage` from `src/types/index.ts`.

### Client Contract (Public-Safe Only)
```typescript
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL!,
  import.meta.env.VITE_SUPABASE_ANON_KEY!
)
```
- No `SERVICE_ROLE_KEY` reference in any file under `src/`.
- `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` only public environment variables.

### Message Adapter Contract (Skeleton)
- `messages.read()` → `SELECT * FROM messages WHERE conversation_id = ... ORDER BY created_at`
- `messages.insert(msg)` → `INSERT INTO messages ...` (with `public_code` generation, `status='pending'`, UUID `id`)
- `messages.subscribe()` → Supabase Realtime `postgres_changes` on `messages` table (event `INSERT`, `UPDATE`)
- Evidence: 15 (realtime hook design), 03 (message contract).

### Auth Adapter Contract (Skeleton)
- `auth.getSession()` → Supabase Auth session
- `auth.getRole()` → `SELECT role FROM user_roles WHERE user_id = auth.uid()` (with `current_user_role()` RLS enforcement)
- `auth.login(email, password)` → `supabase.auth.signInWithPassword()`
- Evidence: 14 (auth flow), 12 (user_roles table).

### Storage Adapter Contract (Skeleton)
- `storage.upload(file, bucket='receipts')` → Supabase Storage upload; returns public/signed URL reference stored in `messages.sender_photo`
- `storage.download(path)` → Download bytes for worker (not frontend primary use)
- File validation: MIME (`image/jpeg`, `image/png`, `image/webp`); size ≤ 10MB; extension match.
- Evidence: 16 (upload abuse protection), 19 (photo upload gap), 11 (Supabase Storage migration).

### Type Alignment
- Snake_case database fields (`created_at`, `message_type`, `public_code`) mapped to TypeScript interfaces in adapter (optional adapter layer; direct mapping acceptable for Phase 1).
- `number` types in TypeScript mapped to `Numeric` from database (safe for VND integers up to 2^53, per 12 analysis).
