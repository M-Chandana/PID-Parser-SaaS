# B4 Production Checklist (50 DAU Signoff)


Branch: dev
Scope: B4 Deploy + Hardening + Runbook

## Core Service Readiness
- [x] Backend API healthy (`/api/health`)
- [x] AI service healthy (`/health`)
- [x] DB connectivity verified
- [x] Worker processing verified

## End-to-End Flow
- [x] Upload accepted with auth
- [x] Job lifecycle verified (`queued -> processing -> completed`)
- [x] Artifacts persisted for completed jobs

## Billing and Plan Controls
- [x] Webhook happy path validated (`checkout.session.completed`, `subscription.updated`)
- [x] Webhook invalid plan handling validated (404)
- [x] Webhook unknown user handling validated (404)
- [x] Free-plan daily quota limit validated (429 on 6th upload)
- [x] Counter reset behavior validated (simulated day rollover)

## Reliability and Operations
- [x] Continuous uptime observation window recorded (60s, all checks pass)
- [x] Runbook exists for restart, key rotation, rollback, failed jobs, quota/reset checks
- [x] Failed-jobs inspection and reset procedure executed
- [x] Internal API key auth enforcement verified (403 wrong key, 200 correct key)

## Docs and Config
- [x] Backend runbook present and updated
- [x] B4 evidence log filled with command outputs
- [x] Environment example updated with B4 variables

## Signoff
- [x] Team can deploy and recover system using docs
- [x] Production checklist for 50 DAU signed off


