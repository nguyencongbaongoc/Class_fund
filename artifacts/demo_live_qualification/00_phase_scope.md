# Phase Scope: Demo & Live Integration Qualification

## Project
CLASS_FUND_WEB

## Phase
DEMO & LIVE INTEGRATION QUALIFICATION

## Mode
FULL SYSTEM SIMULATION

## Target Branch
master

## Repository
C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB

## Primary Objective
Qualify the complete CLASS_FUND_WEB integration architecture using isolated simulated services, deterministic mocks, contract tests, failure injection, and end-to-end workflow simulations.

## Simulation vs Live
**CRITICAL**: Simulation success is NOT live integration success. This phase must distinguish:
- SIMULATION_PASS
- SIMULATION_PARTIAL
- SIMULATION_BLOCKED
- LIVE_VERIFICATION_NOT_PERFORMED

## Preserved Milestones
- Phase 3.1 AI Pipeline: CLOSED_SOURCE_LEVEL
- Phase 4.1 Guest Chat: CLOSED_SOURCE_LEVEL
- Phase 5 Admin Dashboard: PHASE_5_SOURCE_COMPLETE
- Phase 5.1 Closure Gate: PHASE_5_CLOSED_WITH_LIMITATIONS
- Phase 5.2 Remediation: PHASE_5_2_REMEDIATION_COMPLETE

## Execution Rules
- Work directly on master
- Do not create branches or worktrees
- Do not reset, clean, rebase, or force-push
- Preserve all existing user changes
- Inspect Git status and HEAD before modifying files
- Do not overwrite unrelated source code
- Do not change production authentication behavior
- Do not weaken security or financial invariants
- Do not remove existing tests
- Do not replace real service adapters with permanent mocks
- Do not place test credentials in production configuration

## Strict Isolation Requirements
Simulation must NEVER:
- Connect to the real Supabase project
- Use production database credentials
- Use real service-role keys
- Post actual financial transactions
- Send real notifications
- Access real class member financial data
- Expose Ollama publicly
- Modify real ledger records
- Execute migrations against a production database

Use only synthetic data and isolated test infrastructure.

## Required Artifacts
1. 00_phase_scope.md
2. 01_preflight_and_environment.md
3. 02_existing_architecture_map.md
4. 03_simulation_strategy.md
5. 04_supabase_simulation_report.md
6. 05_ollama_simulation_report.md
6. 06_worker_queue_simulation_report.md
7. 07_e2e_simulation_report.md
8. 08_failure_injection_report.md
9. 09_frontend_backend_integration_report.md
10. 10_security_financial_invariant_report.md
11. 11_simulation_runner_report.md
12. 12_test_evidence.md
13. 13_known_limitations.md
14. 14_live_verification_deferred.md
15. 15_final_qualification_report.md
16. simulation_results.json

## Final Qualification Criteria

### SIMULATION_PASS
- All mandatory simulation scenarios pass
- All critical financial invariants pass
- No unauthorized posting
- No duplicate posting
- Recall and reversal scenarios pass
- Role restrictions pass
- Worker/queue recovery passes
- API contracts are compatible
- Frontend/backend integration tests pass where executable
- TypeScript strict and production build pass
- Evidence artifacts are complete
- No critical security issue remains

### SIMULATION_PARTIAL
- Core architecture passes
- Some non-critical scenarios remain blocked or incomplete
- Limitations are documented

### SIMULATION_BLOCKED
- Financial invariant failure
- Authorization bypass
- Duplicate posting
- Simulation isolation failure
- Critical integration contract mismatch
- Data leakage into production

### LIVE_VERIFICATION
Always report: LIVE_VERIFICATION_NOT_PERFORMED

Unless separate live qualification is explicitly authorized and actual external services are genuinely tested.

## Stop Conditions
Stop immediately if:
- Simulation could touch production data
- A test requires a real financial transaction
- Existing financial invariants are broken
- A fix requires changing completed financial core architecture
- A database migration would affect real data
- A security issue requires expanding scope
- Existing user modifications could be overwritten