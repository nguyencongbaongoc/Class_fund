# 00 Authorization and Scope

## Executive Authorization

**ADVANCED SIMULATION REQUALIFICATION V2 — SIMULATION ONLY**

This is an advanced, read-only qualification and verification operation.

### Primary Objective

Establish whether the remediated CLASS_FUND_WEB system can safely process financial transactions under:
- Normal execution
- Concurrent requests
- Worker crashes
- Retries
- Duplicate delivery
- Partial failures
- Recall operations
- Recovery scenarios

The qualification must determine whether the system preserves financial correctness and ledger integrity under adversarial but controlled simulation.

### Authorized Activities

- Inspect application source, existing tests, migrations, configuration and previous qualification artifacts
- Execute existing tests without modifying them
- Create isolated simulation-only test harnesses under a dedicated test/artifact directory
- Create temporary simulation fixtures and in-memory test data
- Execute concurrency tests using isolated test resources
- Execute controlled failure injection
- Execute ledger integrity and financial invariant verification
- Execute E2E simulation scenarios
- Execute security and authorization tests
- Generate machine-readable and human-readable evidence
- Produce a final qualification verdict

### Explicitly Prohibited

- No production deployment
- No production database access
- No real Supabase connection
- No real Ollama connection
- No real banking/payment services
- No external storage or notification services
- No real financial transactions
- No real user data modification
- No production queue or worker execution
- No secrets or credentials printed in reports
- No source-code remediation during qualification
- No modifying existing tests to obtain a PASS
- No weakening assertions
- No silently skipping failed tests
- No automatic Phase 6
- No automatic remediation phase

All execution must remain local and isolated.

If the environment cannot guarantee simulation isolation, STOP.