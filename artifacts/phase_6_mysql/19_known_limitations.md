# Phase 6 Known Limitations

## Overview
This document records known limitations, technical debt, and deferred work items identified during Phase 6 MySQL migration and Supabase replacement.

---

## 1. MySQL Migration Limitations

### 1.1 ARM64 Performance
| Limitation | Impact | Workaround |
|------------|--------|------------|
| MySQL 8.4 runs emulated on Apple Silicon | 2-3x slower queries | Acceptable for standby; use x86_64 for active |
| No native ARM64 MySQL 8.4 Docker image | Emulation required | Wait for official ARM64 image |

### 1.2 Partial Index Support
| Limitation | Impact | Workaround |
|------------|--------|------------|
| MySQL 8.0.13+ required for partial indexes | Older MySQL versions unsupported | Enforce MySQL 8.4 minimum |
| `mysql_where` syntax differs from `postgresql_where` | Migration complexity | Handled in migration rewrite |

### 1.3 CHECK Constraints
| Limitation | Impact | Workaround |
|------------|--------|------------|
| MySQL 8.0.16+ required for CHECK constraints | Older versions ignore constraints | Enforce MySQL 8.4; app-level validation as backup |

### 1.4 JSON Indexing
| Limitation | Impact | Workaround |
|------------|--------|------------|
| No native JSON GIN indexes like PostgreSQL | Slower JSON queries | Use generated columns + B-tree indexes if needed |

### 1.5 Enum Handling
| Limitation | Impact | Workaround |
|------------|--------|------------|
| `native_enum=False` creates VARCHAR+CHECK | Slightly larger storage | Acceptable; portable |
| No native ENUM type portability | Cannot use MySQL ENUM directly | VARCHAR+CHECK is standard pattern |

---

## 2. Supabase Replacement Limitations

### 2.1 Realtime Scalability
| Limitation | Impact | Future Work |
|------------|--------|-------------|
| Single Redis Pub/Sub bottleneck | Limited to ~10k concurrent connections | Redis Cluster for horizontal scaling |
| No presence/join-leave events | Simpler than Supabase Realtime | Add if needed |
| No automatic reconnection state sync | Client must re-fetch state | Current: full state on reconnect |

### 2.2 Storage Limitations
| Limitation | Impact | Future Work |
|------------|--------|-------------|
| Local filesystem only | Single machine, no redundancy | S3-compatible storage (Phase 7+) |
| No CDN integration | Slower image delivery | CloudFront/Cloudflare (Phase 7+) |
| No automatic image optimization | Larger bandwidth | Sharp/imagemagick pipeline (Phase 7+) |

### 2.3 Authentication Limitations
| Limitation | Impact | Future Work |
|------------|--------|-------------|
| No MFA/2FA | Lower security for admin accounts | TOTP/WebAuthn (Phase 7+) |
| No social login (Google, GitHub) | Less convenient for users | OAuth2 providers (Phase 7+) |
| No email verification flow | Weaker account security | Email service integration (Phase 7+) |
| No password breach detection | Compromised passwords undetected | HaveIBeenPwned API (Phase 7+) |

---

## 3. Three-Machine Architecture Limitations

### 3.1 Manual Failover Only
| Limitation | Impact | Future Work |
|------------|--------|-------------|
| No automated failover | Human intervention required | MySQL Group Replication / InnoDB Cluster (Phase 7+) |
| RTO ~30 minutes | Downtime during handoff | Automated failover < 30 seconds |
| No read replicas | All reads on active machine | Read replicas for scaling (Phase 7+) |

### 3.2 Data Synchronization
| Limitation | Impact | Future Work |
|------------|--------|-------------|
| No live replication | RPO = backup interval (24h) | Synchronous replication (Phase 7+) |
| Manual rsync for uploads | Potential file inconsistency | Shared storage / S3 (Phase 7+) |
| No conflict resolution | Split-brain risk if misused | Strict single-active enforcement |

### 3.3 Backup Limitations
| Limitation | Impact | Future Work |
|------------|--------|-------------|
| Logical backup only (mysqldump) | Slower for large databases | Physical backup (Percona XtraBackup) |
| No incremental backup automation | Manual binary log management | Automated PITR pipeline |
| Cross-architecture restore untested | Risk on ARM64 ↔ x86_64 | Quarterly restore drills |

---

## 4. Financial System Limitations

### 4.1 Currency Support
| Limitation | Impact | Future Work |
|------------|--------|-------------|
| Single currency per account (VND default) | No multi-currency | Multi-currency accounts (Phase 7+) |
| No exchange rate handling | Manual conversion only | Exchange rate service (Phase 7+) |

### 4.2 Campaign Limitations
| Limitation | Impact | Future Work |
|------------|--------|-------------|
| Fixed expected amount per campaign | No partial payments | Flexible amount campaigns |
| No recurring campaigns | Manual recreation | Recurring campaign scheduler |

### 4.3 Audit Limitations
| Limitation | Impact | Future Work |
|------------|--------|-------------|
| Audit logs in same database | Not tamper-proof | Immutable audit log (append-only table / external) |
| No audit log export scheduling | Manual export only | Scheduled exports to secure storage |

---

## 5. Testing Limitations

### 5.1 Test Coverage Gaps
| Area | Current Coverage | Gap |
|------|------------------|-----|
| MySQL-specific tests | New test suite needed | All tests currently SQLite |
| Concurrency tests | Basic only | Deadlock injection, lock contention |
| ARM64 compatibility | Not tested | CI on ARM64 runner |
| Large dataset performance | Not tested | 1M+ row tests |
| Network partition | Not tested | Chaos engineering |

### 5.2 Simulation Test Limitations
| Limitation | Impact |
|------------|--------|
| Mock Supabase/Ollama | Doesn't test real integration |
| SQLite in tests | Doesn't catch MySQL-specific bugs |
| No load testing | Performance unknown |

---

## 6. Operational Limitations

### 6.1 Monitoring Gaps
| Missing | Impact |
|---------|--------|
| MySQL slow query alerting | Performance issues undetected |
| Deadlock alerting | Concurrency issues silent |
| Backup success/failure alerts | Silent backup failures |
| Disk space monitoring | Out-of-disk crashes |

### 6.2 Deployment Limitations
| Limitation | Impact |
|------------|--------|
| No blue-green deployment | Downtime on deploy |
| No database migration strategy for prod | Risk of failed migrations |
| No feature flags | All-or-nothing releases |

---

## 7. Deferred Features (Phase 7+)

### 7.1 High Priority
1. **Automated MySQL failover** - Group Replication or InnoDB Cluster
2. **S3-compatible storage** - MinIO, AWS S3, Cloudflare R2
3. **CDN for static assets** - CloudFront, Cloudflare
4. **MFA for admin accounts** - TOTP/WebAuthn
5. **Automated backup verification** - Restore test in CI
6. **Database read replicas** - Scale reads
7. **Observability stack** - Prometheus, Grafana, Loki

### 7.2 Medium Priority
1. **Multi-currency support** - Exchange rates, conversion
2. **Social login** - Google, GitHub OAuth
3. **Email notifications** - Transactional email service
4. **Webhook system** - External integrations
5. **API rate limiting per user** - Fair usage
6. **Audit log immutability** - Append-only / external store

### 7.3 Low Priority
1. **Recurring campaigns** - Scheduler
2. **Partial payments** - Flexible amounts
3. **Advanced reporting** - BI dashboards
4. **Mobile push notifications** - FCM/APNs
5. **Dark mode** - Frontend theme

---

## 8. Technical Debt

### 8.1 Code Quality
| Item | Location | Effort |
|------|----------|--------|
| Remove dead Supabase code | supabase_client.py, vision.py, admin.py | Low |
| Consolidate duplicate validation | Multiple routes | Medium |
| Add OpenAPI descriptions | All endpoints | Low |
| Type hints coverage | ~80% | Medium |

### 8.2 Architecture
| Item | Location | Effort |
|------|----------|--------|
| Service layer abstraction | Direct DB in routes | High |
| Event-driven architecture | Direct function calls | High |
| Caching layer | None | Medium |

---

## 9. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| MySQL deadlocks under load | Medium | High | SKIP LOCKED, retry logic, monitoring |
| ARM64 performance issues | High | Medium | x86_64 for active, monitor |
| Backup corruption | Low | Critical | Checksums, monthly restore test |
| Split-brain on failover | Low | Critical | Strict manual process |
| Data loss during handoff | Low | Critical | FLUSH TABLES WITH READ LOCK |
| JWT secret compromise | Low | Critical | Rotation, short expiry |
| File storage loss | Medium | High | Daily backup, rsync to standby |

---

## 10. Acceptance Criteria for Phase 7

Phase 7 may begin when:
- [ ] All Phase 6 tests pass on MySQL 8.4
- [ ] No critical/high security findings
- [ ] Backup/restore tested on both architectures
- [ ] DR runbook validated
- [ ] Financial invariants verified on MySQL
- [ ] Supabase dependencies removed from runtime
- [ ] Documentation complete and reviewed

---

**Status: KNOWN LIMITATIONS DOCUMENTED - Ready for Final Qualification Report**