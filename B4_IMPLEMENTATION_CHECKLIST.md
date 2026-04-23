# B4 Implementation Checklist (Deploy + Hardening + Runbook)

Source of truth: roadmap B4 scope and done criteria.

## Objective
Complete production readiness for backend, worker, AI microservice, database, and storage with operational safety and repeatable recovery.

## B4 Scope Mapped to Roadmap

### 1) Deploy backend, worker, AI microservice, DB, storage config
Status: Completed

Tasks:
- [x] Finalize environment configuration for all services.
- [x] Add local staging bootstrap scripts to start/stop stack.
- [x] Verify backend API startup in staging.
- [x] Verify worker startup in staging.
- [x] Verify AI service startup in staging.
- [x] Verify DB connectivity from backend and worker.
- [x] Verify storage path and access from backend and worker.
- [x] Run full upload -> queued -> processing -> completed flow in staging.

Evidence to collect:
- startup logs
- health check responses
- one successful end-to-end job ID with artifact references
- evidence file entries (`B4_EVIDENCE_LOG.md`)

### 2) Health checks and uptime verification
Status: Completed

Tasks:
- [x] Verify backend health endpoint (`GET /api/health`).
- [x] Verify AI health endpoint (`GET /health`).
- [x] Verify DB query health from backend process.
- [x] Add periodic health-check script for staging smoke checks.
- [x] Record at least one continuous uptime observation window.

Evidence to collect:
- health script output with timestamps
- uptime observation notes

### 3) Billing webhook and subscription events verified in staging
Status: Completed

Tasks:
- [x] Validate checkout completion event path.
- [x] Validate subscription update event path.
- [x] Validate invalid plan handling.
- [x] Validate unknown user handling.
- [x] Capture before/after user plan state in DB.
- [x] Add webhook staging verification script.

Evidence to collect:
- webhook request/response logs
- DB row snapshots for test user

### 4) Ops runbook
Status: Completed

Tasks:
- [x] Restart services procedure documented.
- [x] Key rotation procedure documented.
- [x] Rollback procedure documented.
- [x] Failed jobs investigation procedure documented.
- [x] Plan-limit and counter-reset verification procedure documented.

Evidence to collect:
- runbook reviewed by team
- one dry-run execution of each runbook section

## Done Criteria (B4)
B4 is complete only when both are true:
- [x] Team can deploy and recover system using docs.
- [x] Production checklist for 50 DAU is signed off.

## Implementation Order (Recommended)
1. Deploy + health baseline
2. Staging webhook verification
3. Runbook dry-run
4. Final sign-off checklist

## Execution Commands
- Start stack: `powershell -ExecutionPolicy Bypass -File .\scripts\start_b4_staging.ps1`
- Stop stack: `powershell -ExecutionPolicy Bypass -File .\scripts\stop_b4_staging.ps1`
- Health checks: `cd backend-service && npm run b4:health`
- Webhook checks: `cd backend-service && npm run b4:webhook`
