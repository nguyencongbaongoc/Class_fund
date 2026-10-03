# 12_KNOWN_LIMITATIONS.md

## Phase 2 Known Limitations

**Status**: Documented for transparency — Not blockers for Phase 2 completion
**Classification**: Technical debt, external dependencies, scope boundaries

### 1. External Dependency Limitations (BLOCKED_EXTERNAL_DEPENDENCY)

| Limitation | Impact | Workaround |
|------------|--------|------------|
| **No Supabase credentials** | Cannot verify live PostgreSQL, RLS, Realtime, Storage | All adapters implemented with mocks; marked BLOCKED |
| **No Ollama server** | Cannot verify vision model accuracy | Client handles gracefully; marked UNVERIFIED |
| **No frontend build** | Cannot verify end-to-end integration | API contracts defined; frontend changes documented |
| **No concurrent worker test** | Race conditions unverified | Logic tested sequentially; atomic claim verified |

### 2. Security Hardening Gaps (Phase 2 Scope - Not Yet Implemented)

| Gap | Risk | Priority | Effort |
|-----|------|----------|--------|
| **Rate limiting** on public endpoints | DoS via message/upload spam | HIGH | 1 day |
| **File upload validation** (MIME, size, magic bytes) | Malicious file upload | HIGH | 0.5 day |
| **Malware scanning** (ClamAV integration) | Infected receipts | MEDIUM | 2 days |
| **CSP headers** | XSS mitigation | MEDIUM | Frontend |
| **CORS configuration** | Cross-origin attacks | MEDIUM | 0.5 day |
| **Security headers** (X-Frame-Options, etc.) | Defense in depth | MEDIUM | 0.5 day |
| **RLS policy deployment** | Data isolation | HIGH | Requires Supabase |
| **Penetration testing** | Unknown vulns | LOW | Phase 2+ |

### 3. Operational Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| **No monitoring/alerting** | Blind to failures | Add Prometheus/Grafana (Phase 2+) |
| **No backup/restore procedures** | Data loss risk | Document PG dump/restore (Phase 2+) |
| **No disaster recovery** | Extended downtime | Multi-region Supabase (Phase 2+) |
| **No log aggregation** | Debugging difficult | Structured logging + Loki (Phase 2+) |
| **No secrets rotation** | Long-lived credentials | Document rotation procedure |
| **Worker: single-threaded** | Throughput limited | Run multiple workers |
| **Worker: no priority queue** | All messages equal priority | Add priority column if needed |
| **Worker: no dead letter queue** | Failed messages stuck | Manual review via admin UI |
| **Idempotency keys: no TTL** | Table growth | Cleanup job (Phase 2 ops) |

### 4. Functional Limitations

| Limitation | Impact | Resolution |
|------------|--------|------------|
| **Single currency (VND)** | No multi-currency support | Schema supports currency; logic needs work |
| **No transaction editing** | Immutable by design | Revert + new transaction |
| **No partial revert** | All-or-nothing | Design decision |
| **No batch operations** | Admin efficiency | Individual API calls |
| **No webhook notifications** | External integrations | Phase 5+ |
| **No scheduled transactions** | Recurring payments | Phase 5+ |
| **No multi-fund support** | Single account only | Schema supports multiple; UI needed |
| **Guest: no session persistence** | Recall token lost on refresh | Store in sessionStorage (frontend) |

### 5. Scalability Limitations

| Limitation | Current | Target | Plan |
|------------|---------|--------|------|
| **Worker polling interval** | 5 seconds | Configurable | Add env var |
| **Lease duration** | 300 seconds | Tunable | Add env var |
| **Max retries** | 3 | Configurable | Add env var |
| **Database connections** | Pool 5+10 | Tunable | Pool sizing guide |
| **Message throughput** | ~12/min/worker | Higher | Multiple workers + batch claim |
| **Concurrent workers** | Tested 1 | 10+ | Need PostgreSQL test |

### 6. Data Integrity Limitations

| Limitation | Risk | Mitigation |
|------------|------|------------|
| **AMBIGUOUS state requires manual intervention** | Rare but possible | Alert on AMBIGUOUS results |
| **No automated duplicate detection** beyond constraints | Relies on DB unique | Application-level checks in place |
| **Audit log: no retention policy** | Unbounded growth | Partition + archive (Phase 6) |
| **Soft delete only** (status=RECALLED/REVERTED) | No hard delete | GDPR compliance needs review |

### 7. Integration Limitations

| Limitation | Affected Phase | Status |
|------------|----------------|--------|
| **AI adapter contract assumes single model** | Phase 3 | Extend for multi-model |
| **Vision endpoint synchronous** | Phase 3 | Consider async for large files |
| **Frontend recall token storage** | Phase 4 | sessionStorage documented |
| **Realtime requires Supabase** | Phase 4 | Fallback to polling documented |
| **Admin dashboard not built** | Phase 5 | API ready, UI pending |

### 8. Testing Limitations

| Limitation | Impact | Resolution |
|------------|--------|------------|
| **SQLite ≠ PostgreSQL behavior** | Concurrency, locking, types differ | Need PG for true tests |
| **No load testing** | Performance unknown | k6/Locust (Phase 2+) |
| **No chaos testing** | Resilience unverified | Simulate crashes (Phase 2+) |
| **No contract testing** | API drift possible | Pact or similar (Phase 2+) |

### 9. Compliance Limitations

| Area | Gap | Action |
|------|-----|--------|
| **GDPR: Right to erasure** | Only soft delete | Implement hard delete (Phase 2+) |
| **GDPR: Data portability** | No export API | Add export endpoint (Phase 2+) |
| **PCI DSS** | Not assessed | Not in scope (no card data) |
| **Audit retention** | No policy | Define 7-year retention (Phase 2+) |
| **Encryption at rest** | Supabase default | Verify when deployed |

### 10. Phase 2 Scope Boundaries (Intentional Exclusions)

The following are **NOT** Phase 2 scope per requirements:

| Excluded | Owner | Phase |
|----------|-------|-------|
| Qwen/OCR pipeline implementation | Ngọc | Phase 3 |
| Frontend Guest Chat UI | Hải | Phase 4 |
| Frontend Admin Dashboard | Hải | Phase 4 |
| Production deployment | DevOps | Phase 6+ |
| End-to-end system testing | Team | Phase 6+ |
| Phase 6 integration | Team | Phase 6 |
| Phase 7 full security qualification | Security | Phase 7 |
| Phase 8-10 | Team | Future |

### 11. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-10-03 | Use SQLite for baseline tests | Fast, no deps, sufficient for logic |
| 2026-10-03 | Stable idempotency key format | Prevents duplicate on retry |
| 2026-10-03 | Recall token = SHA256, returned once | Security: no replay, no logging |
| 2026-10-03 | Worker: Supabase polling, no Redis | Offline-capable, simpler ops |
| 2026-10-03 | Financial gatekeeper single entry | Security: no bypass paths |
| 2026-10-03 | No rate limiting in baseline | Phase 2 hardening task |
| 2026-10-03 | No file validation in baseline | Phase 2 hardening task |

### 12. Migration Path for Limitations

| Limitation | Phase 2 Action | Future Phase |
|------------|----------------|--------------|
| Rate limiting | Implement + test | Done |
| File validation | Implement + test | Done |
| Security headers | Implement + test | Done |
| RLS deployment | Document + helpers | Phase 2 (with Supabase) |
| Monitoring | Document requirements | Phase 6 |
| Backup/restore | Document procedures | Phase 6 |
| Multi-currency | Schema ready, logic later | Phase 5+ |
| Batch operations | API design | Phase 5+ |
| Webhooks | Design | Phase 5+ |

---

**Summary**: Core financial, idempotency, worker, and recall functionality is **complete and tested**. Known limitations are documented, categorized, and have migration paths. Security hardening (rate limiting, file validation, headers) is the primary Phase 2 implementation work remaining. External dependencies (Supabase, Ollama) are explicitly BLOCKED and do not block Phase 2 completion.