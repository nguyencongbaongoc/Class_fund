# 15_PHASE_1_1_TEST_AND_EVIDENCE_REPORT.md

## Actual Inspections (Evidence — Not Assumed)
Every claim references a real inspection result from this session.

### File System / Evidence Inventory (Executed)
- `python -c` script: counted `.md` files (`phase_0_compatibility_audit`: 20; `phase_1_integration`: 15; `phase_1_1_contract_review`: 16 after this file).
- `ls artifacts/phase_1_integration/*.md`: 15 files confirmed.
- `ls artifacts/phase_1_1_contract_review/*.md`: growing (files added incrementally).
- `git log --oneline`: `2d20a50` (Phase 1 artifacts); `dc7768e` (initial working state); no additional commits made during Phase 1.1 (only artifacts created).

### Source Code Inspection (Actual — Not Memory)
- `class-fund-backend-v0.1/class-fund-backend/app/services/ledger.py`: Full 242 lines read (`read` tool). Confirmed: `post_transaction()` (lines 59–118), `post_revert()` (lines 121–169), `verify_and_post_from_ai()` (lines 172–241), `_make_request_fingerprint()` (lines 39–40), `check_idempotency()` (lines 43–51), `save_idempotency()` (lines 54–57), `calculate_balance()` (lines 19–36). No modifications made to file.
- `ollama list`: Executed (`ollama_client` not called; only `list` executed). Output: `qwen3.5:4b` (3.4 GB), `qwen2.5vl:3b` (3.2 GB). Confirmed installed.
- `git status`: Confirmed clean working tree before Phase 1.1 artifacts (only artifacts added; tracked source unchanged).
- `git diff`: Confirmed zero tracked source modifications (only artifacts added by Phase 1; Phase 1.1 artifacts untracked initially, then added to new directory — no tracked source changes).

### Document / Contract Inspection (Actual — Read)
- `artifacts/phase_1_integration/00_PHASE1_PREFLIGHT.md` through `14_PHASE1_FINAL_REPORT.md`: All 15 files read at least partially (full reads for `01`, `02`, `03`, `11`, `12`, `13`, `14`; partial for others). Confirmed contracts exist; references preserved; no missing files.
- `artifacts/phase_0_compatibility_audit/09`, `11`, `12`, `13`, `14`, `15`, `16`, `18`, `19`: Read fully or partially (key sections confirmed); no missing Phase 0 files (`20` `.md` files present; `.rar` archive present but not opened — not required by contracts).
- `classfund/classfund/src/views/ChatView.tsx`: Not reopened (design contracts preserved; adapter skeleton references it; no modifications needed or made).
- `classfund/classfund/src/context/AppContext.tsx`: Not reopened (design contracts reference `mockDatabase.ts`; adapter design preserves mock; source unchanged).

### Runtime / Command Evidence
- `ollama list`: Executed; result saved (session context; `01` preflight references it).
- `python` file count: Executed; results saved (`01` inventory references count script output).
- `git init` + `git commit`: Executed; `dc7768e` and `2d20a50` confirmed.
- No `pytest` execution (`.coverage` file exists from previous state — `53248` bytes; unchanged by Phase 1; `pytest_cache` exists; no new test execution evidence).
- No `npm` / `bun` build execution (`build/` exists; `dist/` exists; no build output change during Phase 1.1).
- No `supabase` connection (`supabase` Python package or CLI not executed; adapter contracts only).
- No `python -m pytest` execution (no test results produced; `pytest_cache` unchanged).
- No `ollama run` or vision test executed (`05` Phase 0 vision requirements remain unverified; `10` adapter contract defines vision but no execution).
- No `python worker/main.py` execution (adapter skeleton `08` not implemented; no runtime evidence).

### Evidence Not Produced / Unverified (Explicitly Recorded)
- No automated test output (`pytest`): `UNIT_TESTED` = 0 requirements verified.
- No adapter source execution (`client.ts` / `ollama_client.py`): `IMPLEMENTED` adapter = 0 requirements.
- No Supabase DB connection (`CREATE TABLE`, `INSERT`, `SELECT`, `ALTER PUBLICATION`): `RUNTIME_VERIFIED` DB = 0 requirements.
- No end-to-end flow execution: `INTEGRATION_TESTED` = 0 requirements.
- No vision accuracy measurement: `UNVERIFIED` / `BLOCKED` for vision accuracy (`05` Phase 0 gate).
- No recall authorization endpoint execution: `BLOCKED` for authorization mechanism (`05` security review; `12` contract; `19` Phase 0 audit).
- No realtime subscription event stream: `UNVERIFIED` for realtime event delivery (`07` design only).
- No claim/recovery loop execution: `UNVERIFIED` for claim/recovery (`08` SQL syntax verified; execution unverified).
- No `message.transaction_id` set execution: `DESIGNED` for linkage (contract exists; no DB record set; no adapter executed).
- No `idempotency_key` format stability test (`retry_count` change): `BLOCKED` (audit `08` documented conflict; no test executed).

### Actual Results from Evidence
- Evidence inventory count (`python` script): Phase 0 `.md` = 20; Phase 1 `.md` = 15; Phase 1.1 `.md` = 16 (after this file).
- Artifact count reconciliation: Phase 1 `14` artifacts (numbers `00`–`14` = 15 files); discrepancy resolved (`14` is miscount; actual 15).
- `ledger.py` fingerprint (`sha256`): verified by inspection (`line 39–41`); fingerprint uses joined parts; does NOT include `message.id` or `retry_count`.
- `IdempotencyKey` table design (`models` import in `ledger.py` line 10): `key` (str), `request_fingerprint` (str), `response_status` (int), `response_body` (dict/JSON).
- `post_revert()` fingerprint (`line 123`): uses `original.id` + `reason`; stable (independent of `message.id` or `retry_count`); same stability concern applies to revert: different `reason` creates different fingerprint (by design; `post_revert()` uses `reason`; same `reason` returns same response; `reason` change creates new fingerprint — by design for revert, this is correct behavior).
- Message-to-transaction linkage (`02` SQL): `messages.transaction_id` FK to `Transaction.id`; no DB record with `transaction_id` set; `verify_and_post_from_ai()` does not pass `message.id` (current source); design contract (`11`) proposes adding `message.id` linkage; source unmodified.
- Recall authorization mechanism (`12` design + `19` Phase 0): design proposes token/hash (`recall_token_hash`); source mechanism missing; authorization endpoint unimplemented.
- Adapter source absence (`git ls-files` + directory inspection): `src/lib/supabase/` files not tracked; `ai/ollama_client.py` not tracked; `worker/main.py` not tracked.
- RLS policies (`05` contracts): SQL contracts defined; `ALTER TABLE ENABLE ROW LEVEL SECURITY` not executed; policies not executed against deployed DB.
- Security secret isolation (`01` + `05`): `SERVICE_ROLE_KEY` listed only under private environment variables; adapter design (`06`) uses `ANON_KEY` only; source confirmation (`git ls-files`): no adapter source leaks secret.

### Status Classification Evidence (Actual — Based on Inspections Above)
Refer to `03_IMPLEMENTATION_STATUS_MATRIX.md` for full matrix with evidence references.
Key verified statuses:
- DESIGNED: `01` config contract (`no .env` modified; adapter design only).
- IMPLEMENTED (preserved): `ledger.py` functions (`verify_and_post_from_ai`, `post_revert`, `post_transaction`, `calculate_balance`); `models.py` schema preserved; AI modules preserved (`ai/ocr/`, `ai/verification/`); `user_roles` mapping preserved (`OWNER_TREASURER` etc.).
- IMPLEMENTED (new adapter source): 0 (adapter files not created).
- UNIT_TESTED (automated test executed): 0 (`pytest` not executed; `.coverage` unchanged).
- INTEGRATION_TESTED (components together): 0 (no adapter deployed; no end-to-end execution).
- RUNTIME_VERIFIED: 2 (`ollama list`; `git` state verification).
- PRODUCTION_VERIFIED: 0 (no deploy; `vercel.json` not applied).
- BLOCKED (critical): 3 (`idempotency stability` — audit `08`; `vision accuracy` — `05` Phase 0; `authorization mechanism` — `05` + `12`).
- BLOCKED / UNVERIFIED: 7 (realtime; adapter; claim/recovery execution; end-to-end; recall authorization source; message-to-transaction link; AI schema enforcement).
- UNVERIFIED (design claim only): 9 (adapter persistence; photo upload execution; RLS execution; adapter deployment; realtime events; public code authorization; AI structured output enforced; message lifecycle transition execution; worker shutdown).

### Conclusion of Evidence Report
Phase 1.1 evidence confirms:
- Phase 1 artifacts exist (15 files); contracts defined; no source rewrites performed; `ledger.py` preserved; `git` state verified (`2d20a50`).
- Design contracts comprehensive (`01` through `14`); references Phase 0 evidence (`09`, `11`, `12`, `13`, `14`, `15`, `16`, `18`, `19`).
- Actual code inspection (`ledger.py`) confirms existing financial gatekeeper preserved (`verify_and_post_from_ai()`; `post_revert()`; fingerprint mechanism; `IdempotencyKey` mechanism).
- Actual command execution (`ollama list`; `git`; `python` counts) confirms model availability and artifact presence.
- No runtime verification of adapter, worker, realtime, vision accuracy, or end-to-end integration.
- Critical conflicts identified (`08` idempotency stability; `05` vision accuracy; authorization mechanism; adapter source absence; message-to-transaction link source missing; claim/recovery execution unverified).
- Phase 2 prerequisites (`14_PHASE_2_ENTRY_CRITERIA.md`) require resolution of all `BLOCKED` critical issues and execution of all unverified prerequisites before Phase 2 authorization.
