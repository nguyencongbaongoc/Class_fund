# PHASE 0 — RISK REGISTER

## Executive Summary
**Status: 8 Critical / 5 High / 6 Medium / 3 Low** — Critical risks concentrated in financial integrity, security (guest recall authorization), and AI pipeline unverified capabilities. No source modifications made.

---

## Risk Classification

### Critical (Requires Immediate Remediation Before Production)

| ID | Risk | Evidence | Impact | Mitigation |
|----|------|----------|--------|------------|
| R-C-01 | **Guest can revert any transaction** | `AppContext.revertTransaction()` has no ownership/auth check (`AppContext.tsx:310`) | Financial fraud | Implement recall token authorization |
| R-C-02 | **AI output can corrupt balance** | Mock `addLedgerEntry` updates balance directly without backend validation (`AppContext.tsx:219`) | Incorrect financial records | Route through backend `verify_and_post_from_ai()` |
| R-C-03 | **Ollama vision accuracy unverified** | `qwen2.5vl:3b` installed (`ollama list`) but no integration or Vietnamese receipt test | Incorrect extraction → wrong transactions | Build `OllamaVisionClient`, test 50+ receipts |
| R-C-04 | **Duplicate credit from AI retry** | `IdempotencyKey` exists in DB but not wired in mock (`models.py:202`); Celery retry exists (`ai/worker/queue.py:108`) but no Supabase persistence | Double posting | Persist idempotency keys; worker pass keys |
| R-C-05 | **No authorization for recall** | No token mechanism; mock allows any role to revert (`AppContext.tsx:310`) | Any user can reverse any transaction | Recall token + RLS |
| R-C-06 | **No admin review for AI low confidence** | `NEEDS_REVIEW` has no approval endpoint; mock has no admin UI (`UploadReceiptView.tsx:123`) | Unverified transactions posted | Add `awaiting_admin` → approve endpoint |
| R-C-07 | **Message ID not cryptographically safe** | `'msg_' + Date.now()` (`AppContext.tsx:452`) — predictable, not UUID | Duplicate messages, weak audit trail | Generate UUID v4 |
| R-C-08 | **No database-level authorization** | No RLS policies; backend relies only on `require_roles()` (`deps.py:31`) | Direct DB access bypasses auth | Implement RLS |

### High (Requires Remediation Before Deployment)

| ID | Risk | Evidence | Impact | Mitigation |
|----|------|----------|--------|------------|
| R-H-01 | **No Supabase Auth integration** | Custom JWT only (`security.py`); no `supabase-js` (`package.json` has `@google/genai` but unused) | User identity unreliable | Migrate to Supabase Auth |
| R-H-02 | **No realtime updates** | Zero WebSocket/realtime code (`grep` found nothing) | Chat stale, ledger delays | Add `supabase-js` subscriptions |
| R-H-03 | **No persistent message storage** | All chat data in React state (`AppContext.tsx`) | Data lost on refresh | Persist to `messages` table |
| R-H-04 | **Local file storage only** | `upload_dir: str = "./storage/uploads"` (`config.py:12`) | Data lost if server restarts; no cloud backup | Move to Supabase Storage |
| R-H-05 | **Frontend no error boundaries** | Zero `ErrorBoundary` components; no network error handling | App crash on API failure | Add error boundaries |

### Medium (Requires Attention)

| ID | Risk | Evidence | Impact | Mitigation |
|----|------|----------|--------|------------|
| R-M-01 | **No rate limiting** | No middleware; `chat.py` allows unlimited POST | Spam, DoS | Add pg_cron rate limits |
| R-M-02 | **No offline message queue** | No IndexedDB or service worker (`package.json` no PWA) | Messages lost when offline | IndexedDB queue |
| R-M-03 | **No message delivery receipts** | No `message_receipts` table; no read/delivered tracking | Unknown if user saw message | Add receipts table |
| R-M-04 | **AI pipeline in-memory duplicates only** | `DuplicateDetector.seen_hashes` dict (`ai/duplicate/service.py:22`) | Duplicate allowed after restart | Persist to DB |
| R-M-05 | **No worker heartbeat/monitoring** | Celery events only (`ai/worker/queue.py:228`); no persistent table | Worker failure undetected | Add `worker_status` table |
| R-M-06 | **No MFA for admin** | JWT only (`security.py:25`); no MFA in `auth.py` | Admin account compromise | Enable Supabase Auth MFA |

### Low (Document/Plan)

| ID | Risk | Evidence | Impact | Mitigation |
|----|------|----------|--------|------------|
| R-L-01 | **Missing `vercel.json`** | Not present; only `vite.config.ts` | Vercel deploy fails for SPA | Create `vercel.json` |
| R-L-02 | **Mock wallpaper modal** | `WallpaperModal` exists but not core function | Low impact | Optional cleanup |
| R-L-03 | **Legacy `web gay/` directory** | Unused directory (`Get-ChildItem` showed it) | Low impact | Remove |

---

## 8. FINANCIAL RISK DETAIL

### Risk: AI Can Post Directly (Mitigated)
**Evidence**: `verify_and_post_from_ai()` validates before posting (`ledger.py:183-192`). Mock bypasses this.
**Mitigation**: Route all AI results through backend endpoint.

### Risk: Concurrent Balance Corruption (Mitigated)
**Evidence**: `FOR UPDATE` locks on transactions (`ledger.py:81, 130, 194`); unique constraints.
**Mitigation**: Confirmed safe.

### Risk: Reversal Creates Infinite Loop (Mitigated)
**Evidence**: `post_revert()` checks `original.type == REVERT` (`ledger.py:132`).
**Mitigation**: Confirmed safe.

---

## 9. SECURITY RISK DETAIL

### Risk: Service Role Key Exposure
**Evidence**: `AI_SERVICE_KEY` in `.env.example` (`class-fund-backend-v0.1/class-fund-backend/.env.example:9`).
**Mitigation**: Store in Windows Credential Manager; rotate; monitor Supabase logs.

### Risk: Public Receipt Access
**Evidence**: `FileResponse` serves images at `/internal/ai/uploads/{id}/file` (`ai_internal.py:16`).
**Mitigation**: Access requires `AI_SERVICE_KEY`; public only sees verified transactions.

### Risk: No Input Sanitization in Chat
**Evidence**: `ChatMessageIn.content` has max_length=5000 but no HTML/script filtering (`schemas.py:142`).
**Mitigation**: Add DOMPurify on frontend; backend sanitize.

---

## 10. AI/OLLAMA RISK DETAIL

### Risk: Model Accuracy Unknown
**Evidence**: `qwen2.5vl:3b` installed (`ollama list`) but `ai/` has zero Ollama integration.
**Mitigation**: Build `OllamaVisionClient`, test with real receipts before deployment.

### Risk: Timeout/Crash During Processing
**Evidence**: Celery `task_time_limit=300` (`ai/worker/queue.py:96`) but no timeout in mock.
**Mitigation**: Implement timeout in worker polling loop; lease expiration handles crashes.

---

## 11. HYBRID-SPECIFIC RISKS

### Risk: PC Offline = No AI Processing
**Evidence**: No cloud AI; only local Ollama.
**Mitigation**: Messages queued in Supabase; processed when PC online.

### Risk: Message Lost If Not Processed Before Recall
**Evidence**: No `PENDING` status in chat; no recall mechanism.
**Mitigation**: Implement message status + recall token.

---

## 12. EVIDENCE SUMMARY

Every critical finding includes exact file/line evidence. Key sources:
- `C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB\artifacts\phase_0_compatibility_audit\01_BACKEND_FORENSIC_INVENTORY.md`
- `02_FRONTEND_FORENSIC_INVENTORY.md`
- `05_AI_OLLAMA_COMPATIBILITY.md`
- `16_SECURITY_AND_CLOUD_DEPLOYMENT_AUDIT.md`
- `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md`

---

## 13. REMEDIATION ORDER FOR CRITICAL RISKS

**Before Any Implementation:**
1. Verify `qwen2.5vl:3b` accuracy on Vietnamese receipts
2. Define `messages` table with UUID, status, public code
3. Implement RLS policies
4. Build recall token mechanism
5. Build Supabase polling worker (replaces Celery for hybrid)
6. Route all mutations through backend (not mock state)

---

## 14. NO MODIFICATIONS CONFIRMED

**CONFIRMED**: During this Phase 0 audit (original + addendums A and B):
- Zero source file modifications
- Zero database modifications
- Zero `.env` or config changes
- Zero package installations
- Zero migrations executed
- Zero Ollama model changes
- Zero production service starts
- Zero financial transactions submitted
- Zero user accounts created
- All work read-only: file reads, `ollama list`, static code analysis

---

## 15. NEXT GATE

**STOP** — Await user review and explicit approval of:
1. Phase 0 original reports (00-10)
2. Hybrid architecture reports (11-18)
3. Guest chat/recal audit (19)
4. This risk register

Only after explicit approval should Phase 1 begin.

**No implementation until user confirms:**
- Overall verdict (`PARTIALLY_COMPATIBLE`)
- Critical path (Supabase → Worker → Frontend)
- Risk acceptance (critical gaps identified)
- Responsibility assignments (Minh: DB/auth; Ngọc: AI/worker; Hải: frontend/realtime)