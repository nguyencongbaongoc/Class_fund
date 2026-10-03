# 03_IMPLEMENTATION_STATUS_MATRIX.md

## Classification Definitions (Evidence-Based)
- DESIGNED: Only contract/design document exists; no production source file implements it.
- IMPLEMENTED: Source code exists and is traceable to the contract.
- UNIT_TESTED: Automated test executed (evidence: test output, `.coverage` update, or `pytest` result). Not claimed without evidence.
- INTEGRATION_TESTED: Components tested together (evidence: integration test result). Not claimed without evidence.
- RUNTIME_VERIFIED: Verified during live execution (e.g., `ollama list`, adapter connection, DB write). Evidence must reference command/result.
- PRODUCTION_VERIFIED: Deployed and verified in production. Not applicable to Phase 1 (no production deploy).
- BLOCKED: Cannot proceed due to missing evidence, unresolved conflict, or dependency gap.
- UNVERIFIED: Claim made in design but no verification evidence exists.

## Requirement Status (Evidence-Based Assessment)

| Requirement | Evidence Source | Actual Status | Evidence / Note |
|---|---|---|---|
| Environment/config contract (`01`) | `01_CONFIGURATION_CONTRACT.md` | DESIGNED | Contract only; no `.env` file modified; `vite.config.ts` unchanged |
| Supabase engine config (`01`) | `01` contract | DESIGNED | SQLAlchemy config documented; no `engine` instance created in new adapter source (adapter file not yet written) |
| Message UUID + public code (`03`) | `03_MESSAGE_CONTRACT.md` | DESIGNED | Schema in `02`; adapter skeleton (`messages.ts`) not yet a file; no DB insert executed |
| Message persistence (`03`) | `02_SUPABASE_SCHEMA.md` | DESIGNED | `messages` table SQL defined; no `CREATE TABLE` executed; no adapter write executed |
| Message lifecycle states (`03`) | `03` contract + `08` skeleton | DESIGNED | State machine documented; no runtime state transition executed |
| Guest identity (`03`) | `03` + `19` Phase 0 evidence | DESIGNED | Contract defines `sender_name`, `sender_photo`; no frontend input change executed
| Photo upload adapter (`06`) | `06_FRONTEND_ADAPTER.md` | DESIGNED | Adapter contract; `storage.ts` not created; no upload executed |
| Auth / RBAC contract (`04`) | `04_AUTH_RBAC.md` | DESIGNED | `user_roles` table SQL; no `auth.users` sync; no login UI change executed |
| Admin role mapping (`04`) | `14` (existing roles verified in `ledger.py`) | DESIGNED | `OWNER_TREASURER` etc. preserved in code; new table contract only |
| RLS policies (`05`) | `05_RLS_SECURITY.md` | DESIGNED | SQL contracts defined; no `ALTER TABLE ENABLE ROW LEVEL SECURITY` executed; no Supabase dashboard interaction |
| RLS testing (`05`) | `05` contract | UNVERIFIED | No executed policy test (no deployed DB); design contracts only |
| Service-role isolation (`05`) | `05` + `01` config | DESIGNED | Contract excludes key from frontend; adapter skeleton not deployed |
| Frontend adapter (`06`) | `06_FRONTEND_ADAPTER.md` | DESIGNED | `src/lib/supabase/` files not created as source (only design contract) |
| Mock data preservation (`06`) | `01` preflight + `11` evidence | IMPLEMENTED (preserved) | `mockDatabase.ts` unchanged; `AppContext` unchanged |
| Realtime adapter (`07`) | `07_REALTIME.md` | DESIGNED | Subscription design; no actual `supabase` channel executed against remote DB |
| Real-time duplicate event protection (`07`) | `07` design | DESIGNED | Event ID tracking concept; no executed realtime event stream |
| Realtime publication (`07`) | `02` SQL contracts (`ALTER PUBLICATION`) | DESIGNED | SQL contracts; no `ALTER PUBLICATION` executed |
| Local worker skeleton (`08`) | `08_LOCAL_WORKER.md` | DESIGNED | `main.py`, `claim.py`, `heartbeat.py` not created; claim SQL verified syntactically but not executed |
| Atomic claim (`08`) | `08` SQL contract; `13` claim design | DESIGNED | SQL syntax valid for PostgreSQL; no `UPDATE ... FOR UPDATE SKIP LOCKED` executed against DB |
| Lease recovery (`08`) | `08` design; `13` claim/recovery | DESIGNED | `lease_expires_at` reset SQL contract; no startup reclaim executed |
| Heartbeat (`08`) | `08` contract | DESIGNED | `upsert` design; no `worker_status` insert/update executed |
| Ollama adapter (`09`) | `09_OLLAMA_ADAPTER.md` | DESIGNED | No `ai/ollama_client.py` source file exists; design only |
| Ollama model verified (`09`) | `01` + `ollama list` result | RUNTIME_VERIFIED | `qwen2.5vl:3b` (3.2 GB) and `qwen3.5:4b` (3.4 GB) listed; endpoint `127.0.0.1:11434` assumed local |
| AI structured output (`10`) | `10_AI_CONTRACT.md` | DESIGNED | Schema defined; no executed vision request; no JSON validation executed |
| AI intent whitelist (`10`) | `10` contract | DESIGNED | Intents listed; no enforced validation executed |
| AI confidence threshold (`10`) | `10` + `11` (existing `VerificationPolicy`) | DESIGNED / IMPLEMENTED | Existing `threshold` preserved in `verification/service.py`; contract aligns; no new enforcement added |
| AI never modifies balance (`10`) | `10` + `11` gatekeeper design | IMPLEMENTED (preserved by design) | `verify_and_post_from_ai()` is only posting path; adapter produces structured result; balance mutation remains in `post_transaction()` only |
| Financial gatekeeper (`11`) | `11_FINANCIAL_GATEKEEPER.md` + `ledger.py` actual inspection | IMPLEMENTED (preserved) | `verify_and_post_from_ai()` unchanged (lines 172–241 of `ledger.py`); fingerprint (`sha256`) verified; `IdempotencyKey` table verified; `post_revert()` verified; no source modifications |
| Idempotency format (`11`) | `08` + `11` + `ledger.py` lines 39–57 | IMPLEMENTED (preserved design; new contract unverified) | Existing key format uses fingerprint (`_make_request_fingerprint`); new proposed format (`msg_{message.id}_attempt_{retry_count}`) is a design contract; no code creates this format; no DB entry uses this format |
| Idempotency stable design (`11`) | `08` audit (critical) | BLOCKED / UNVERIFIED | See `08_FINANCIAL_IDEMPOTENCY_AUDIT.md` — new proposed format changes with `retry_count`; stability not guaranteed across retries; requires resolution |
| Message-to-transaction linkage (`11`) | `02` (`messages.transaction_id`) + `11` design | DESIGNED | FK designed; no record with `transaction_id` set; no `verify_and_post_from_ai()` call links message ID |
| Recall before post (`12`) | `12` contract + `ledger.py` line 177–182 (`existing_tx` check by `upload.id`) | DESIGNED / PARTIALLY VERIFIED | Existing code checks `upload.status` (`REJECTED`, `DUPLICATE`) and `upload.id` duplicate; `message.status = 'recalled'` check is new contract; no new code added; `REJECTED`/`DUPLICATE` behavior preserved |
| Recall after post (`12`) | `12` contract + `ledger.py` `post_revert()` (line 121–169) | IMPLEMENTED (preserved) | `post_revert()` creates `REVERT` entry; preserves original; prevents double revert; no changes to `post_revert()` |
| Recall authorization (`12`) | `12` token design | DESIGNED | Token hash (`recall_token_hash`) in `messages` table design; no token generation source; no recall endpoint implemented |
| Public code authorization (`03` + `12`) | `03` + `12` contracts | DESIGNED / UNVERIFIED | Contract explicitly states `public_code` is NOT authorization; security relies on private token (not yet implemented) |
| Double-recall prevention (`12`) | `12` contract + `ledger.py` lines 134–138 (`already` check) | IMPLEMENTED (preserved) | `post_revert()` checks `original_entry_id` + `REVERT` type; prevents duplicate; message-level `recalled` state is design addition |
| Guest photo upload (`03`) | `03` + `19` Phase 0 audit (`UploadReceiptView` has name input; no inline chat photo) | DESIGNED | Photo reference (`sender_photo`) field designed; no `Supabase Storage` upload executed; no `upload_receipt()` adapter executed |
| Photo storage (`05`) | `05` policies (public verified uploads) | DESIGNED | `uploads` RLS contracts; no storage bucket `receipts` created; no upload executed |
| Photo validation (`06`) | `06` adapter contract | DESIGNED | MIME/extension/size rules documented; no validation function source executed |
| Frontend realtime event handling (`07`) | `07` subscription design | DESIGNED | `channel.subscribe()` design; no `supabase` client instance created; no event stream received |
| Realtime reconnect (`07`) | `07` design | DESIGNED | Auto-reconnect contract; no connection failure simulated |
| Duplicate realtime event (`07`) | `07` event-ID tracking design | DESIGNED | Bounded set (`size > 1000`) concept; no executed realtime stream to test deduplication |
| Worker claim atomic (`08`) | `08` SQL contract; `13` test definition | DESIGNED / UNVERIFIED (SQL syntax only) | SQL is syntactically valid (`UPDATE ... FOR UPDATE SKIP LOCKED`); no DB connection to verify execution; claim logic not executed |
| Worker claim concurrency (`08`) | `08` design; `13` reference to 2-worker race | DESIGNED / UNVERIFIED | `FOR UPDATE SKIP LOCKED` prevents blocking; concurrency test not executed |
| Lease expiration (`08`) | `08` `lease_expires_at` design; `02` schema | DESIGNED | Schema includes `lease_expires_at`; no `UPDATE` to reset stale leases executed |
| Lease recovery on startup (`08`) | `08` startup/reclaim logic design | DESIGNED | `reclaim_stale_leases()` concept; no worker process started; no startup event executed |
| Heartbeat persistence (`08`) | `08` heartbeat loop design; `02` `worker_status` | DESIGNED | Heartbeat concept (10s interval); no `INSERT/UPDATE` to `worker_status` executed |
| Worker shutdown (`08`) | `08` graceful shutdown design | DESIGNED | Shutdown logic (stop claim, complete current); no process lifecycle event executed |
| AI output contract enforcement (`10`) | `10` schema + `05` (AI untrusted) | DESIGNED | Schema enforced conceptually; no actual AI call executed; no Pydantic validation executed |
| AI malformed response (`09` + `10`) | `09` adapter retry + `10` failure states | DESIGNED | Adapter handles malformed output; no malformed response simulated or handled |
| AI unavailable (`09`) | `09` adapter unavailable detection | DESIGNED / PARTIALLY RUNTIME VERIFIED | `ollama list` confirms model exists; adapter detects unavailability by concept; no simulated unavailable endpoint executed |
| AI vision accuracy (`05` Phase 0) | `05_AI_OLLAMA_COMPATIBILITY.md` (unverified capabilities) | UNVERIFIED / BLOCKED | No 20+ receipt test executed; no accuracy measurement (85% threshold) verified |
| Financial idempotency (`08` audit) | `11_FINANCIAL_GATEKEEPER.md` + `ledger.py` inspection | BLOCKED (design conflict identified) | See `08_FINANCIAL_IDEMPOTENCY_AUDIT.md` — new proposed format (`msg_{message.id}_attempt_{retry_count}`) changes with `retry_count`; stability not guaranteed; resolution required |
| Financial duplicate transaction (`11`) | `11` + `ledger.py` line 194–202 (`duplicate` DB check) | IMPLEMENTED (preserved) | DB `WITH FOR UPDATE` check + unique constraint preserved; no changes |
| Message recall before post (`03` + `12`) | `12` design + `11` `verify_and_post_from_ai()` (line 177–182 checks `upload.status`) | DESIGNED (new check unverified) | Existing `upload.status` checks preserved; new `message.status = 'recalled'` check is contract only; no code added to check it before posting |
| Financial reversal (`11` + `12`) | `11` (`post_revert`) preserved; `12` contract aligns | IMPLEMENTED (preserved) | `post_revert()` unchanged; `REVERT` entry preserved; original preserved |
| Recall token authorization (`12`) | `12` token/hash concept | DESIGNED / BLOCKED (security gap) | Token generation and hash storage contract only; no source for token creation; authorization endpoint not implemented; `public_code` must not authorize (contract confirmed, but authorization mechanism missing) |
| Recall authorization security (`12`) | `12` contract; `16` Phase 0 audit (critical: zero authorization) | BLOCKED (security critical gap) | Phase 0 (`19`) identified zero authorization; Phase 1 (`12`) proposes token strategy; token mechanism not implemented; security authorization remains unaddressed in source |
| Integration end-to-end (`27` gate) | `27` end-to-end criteria; `09` Phase 0 plan | BLOCKED / UNVERIFIED | No end-to-end execution: guest message → claim → AI → verification → ledger → realtime → recall; all components exist separately (design/code) but not connected; adapter/wroker/realtime not fully deployed |

## Overall Status Classification (Phase 1.1)
- DESIGNED (contracts only): 28 requirements
- IMPLEMENTED (preserved / unchanged): 7 requirements (ledger functions, AI modules, mock preservation, model verification, role mapping)
- IMPLEMENTED (new adapter source): 0 requirements (adapter source files not created; contracts only)
- UNIT_TESTED (evidence of execution): 0 requirements (no `pytest` output; `.coverage` unchanged; no automated test executed)
- INTEGRATION_TESTED: 0 requirements
- RUNTIME_VERIFIED: 2 requirements (`ollama list`; `git` states)
- PRODUCTION_VERIFIED: 0 requirements
- BLOCKED (critical unresolved): 3 requirements (idempotency stability; AI vision accuracy unverified; recall authorization security gap)
- BLOCKED / UNVERIFIED: 7 requirements (realtime; full adapter; claim/recovery execution; end-to-end; recall token source; AI accuracy threshold; message-to-transaction link in live DB)
- UNVERIFIED (design claim only): 9 requirements (RLS execution; adapter deployment; duplicate realtime dedup; message persistence write; photo upload; public code authorization; AI schema enforcement; worker shutdown; message lifecycle state transition execution)
