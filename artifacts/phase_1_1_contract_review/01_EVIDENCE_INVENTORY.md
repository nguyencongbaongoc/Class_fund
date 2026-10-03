# 01_EVIDENCE_INVENTORY.md

## Phase 0 Evidence (Actual Inspection)
Directory: `artifacts/phase_0_compatibility_audit/`
File count: 20 `.md` reports (verified with `ls`).
Key files read fully in this session:
- `09_RECOMMENDED_INTEGRATION_PLAN.md` (385 lines)
- `11_HYBRID_ARCHITECTURE_COMPATIBILITY.md` (238 lines)
- `12_SUPABASE_SCHEMA_AND_DATABASE_COMPATIBILITY.md` (414 lines — partial; key sections confirmed)
- `13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md` (580 lines — partial; claim/recovery/lease sections confirmed)
- `14_ADMIN_AUTH_AND_RBAC_AUDIT.md` (406 lines)
- `15_CHAT_REALTIME_COMPATIBILITY.md` (526 lines — partial; hook/realtime design confirmed)
- `16_SECURITY_AND_CLOUD_DEPLOYMENT_AUDIT.md` (584 lines — partial; RLS/service-role sections confirmed)
- `18_PHASE_0_FINAL_CONSOLIDATED_VERDICT.md` (320 lines)
- `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` (687 lines — partial; token/recall/status sections confirmed)
- `05_AI_OLLAMA_COMPATIBILITY.md` (referenced but not fully reopened in this session; model list verified independently via `ollama list`)
- `04_DATABASE_AND_FINANCIAL_INTEGRITY.md` (referenced; actual `ledger.py` inspected directly)
- `01_BACKEND_FORENSIC_INVENTORY.md` (not reopened; design contracts preserved in Phase 1 artifacts)

Archive: `.rar` file present (not opened; design contracts do not depend on archive contents).

## Phase 1 Evidence (Actual Inspection)
Directory: `artifacts/phase_1_integration/`
Actual count: 15 `.md` files (verified with `python` count script).
All 15 files read at least partially in this session (`00_PHASE1_PREFLIGHT.md` through `14_PHASE1_FINAL_REPORT.md`).
Content types confirmed:
- `00`: Preflight checklist (evidence references, git state, model verification)
- `01`: Config contract (env vars, engine settings)
- `02`: Schema SQL contracts (new tables, constraints, indexes)
- `03`: Message contract (UUID, public code, lifecycle states)
- `04`: Auth/RBAC (4 existing roles preserved)
- `05`: RLS policies (table-level SQL contracts)
- `06`: Frontend adapter skeleton (structure, contracts only)
- `07`: Realtime adapter (subscription design, duplicate protection)
- `08`: Local worker skeleton (polling, claim SQL, heartbeat, recovery)
- `09`: Ollama adapter (design; no source code file created yet)
- `10`: AI output contract (structured JSON; allowed intents)
- `11`: Financial gatekeeper (references preserved `verify_and_post_from_ai()`; no rewrite)
- `12`: Recall safety (token strategy; before/after post; double-recall block)
- `13`: Test results (definitions only — no executed automated test output included)
- `14`: Final report (references all Phase 0 evidence; status table; STOP instruction)

## Source Code Evidence Read Directly
- `class-fund-backend-v0.1/class-fund-backend/app/services/ledger.py`: Full 242 lines inspected. Confirms `post_transaction`, `post_revert`, `verify_and_post_from_ai`, `_make_request_fingerprint`, `check_idempotency`, `save_idempotency`. Fingerprint uses `sha256` of joined parts. Idempotency key stored in `IdempotencyKey` table.
- `class-fund-backend-v0.1/class-fund-backend/app/core/config.py`: Not fully read in this session; referenced by contract.
- `ai/verification/service.py`: Not fully reopened; contract references preserved.
- `ai/contracts.py`: Not fully reopened; preserved by reference.
- `classfund/classfund/src/views/ChatView.tsx`: Not reopened; design preserved by adapter contract.

## Runtime Verification
- `ollama list`: Executed; output saved in session context (`qwen3.5:4b`, `qwen2.5vl:3b`). No `ollama run` or vision test executed.
- `git init` + initial commit (`dc7768e`): Confirmed (282 files).
- `git commit` Phase 1 artifacts (`2d20a50`): Confirmed (14 artifact files added, 1051 insertions).
- No automated test execution evidence present in repository (`pytest` results not produced; `.coverage` file exists from prior state but not updated by Phase 1).
- No Supabase connection test executed (no deployed project; adapter connects by design only).
- No actual receipt upload through Supabase Storage executed.

## Classification of Evidence Availability
- Actual code inspection: `ledger.py` (complete); adapter skeleton files (documented contracts only — source files not yet created); frontend adapter structure (design only).
- Actual file inspection: All 14 Phase 1 artifacts; all 20 Phase 0 artifacts.
- Actual command execution: `git`, `python` file counts, `ollama list`.
- Design/reference only (not runtime verified): Realtime subscription event delivery; worker claim/recovery loop; full adapter deployment; end-to-end guest flow; actual Supabase DB write; AI vision extraction accuracy.
