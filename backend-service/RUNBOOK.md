# Backend + Worker Ops Runbook (B4)

This runbook is for staging/production operations of the backend API and worker.

## Services
- Backend API: Express app (`src/index.js`)
- Worker: background job processor (`src/worker.js`)
- DB: PostgreSQL via Prisma
- AI Service: external FastAPI endpoint via `AI_SERVICE_URL`

## Quick Start/Stop (Local Staging)
- Start full stack from repo root:
	`powershell -ExecutionPolicy Bypass -File .\scripts\start_b4_staging.ps1`
- Stop full stack from repo root:
	`powershell -ExecutionPolicy Bypass -File .\scripts\stop_b4_staging.ps1`
- Log files are written under `logs/b4`.
- Record outputs in `B4_EVIDENCE_LOG.md`.

## Required Environment Variables
- `PORT`
- `DATABASE_URL`
- `JWT_SECRET`
- `AI_SERVICE_URL`
- `STORAGE_DIR`
- `SECRET_API_KEY` (must match AI service)

## 1) Restart Services

### Restart backend
1. Stop current backend process.
2. Run `npm run dev` (or `npm start` in production).
3. Check `GET /api/health` returns `status: ok`.

### Restart worker
1. Stop current worker process.
2. Run `npm run worker`.
3. Confirm worker logs show startup and polling.

### Restart order recommendation
1. DB
2. AI service
3. Backend API
4. Worker

## 2) Rotate Keys

### JWT secret rotation
1. Generate new `JWT_SECRET`.
2. Update secret in environment.
3. Restart backend.
4. Force re-login for existing user sessions if needed.

### Internal API key rotation (backend <-> AI)
1. Generate new value for `SECRET_API_KEY`.
2. Update backend and AI service environment values to the same key.
3. Restart AI service first, then backend and worker.
4. Run one upload job to verify parsing still works.

## 3) Rollback

### Code rollback
1. Identify last known good commit.
2. Deploy that commit for backend/worker.
3. Restart services in standard order.
4. Validate health endpoints and one test flow.

### Config rollback
1. Restore prior environment values from secure backup.
2. Restart affected services.
3. Re-run health and upload smoke checks.

## 4) Check Failed Jobs

### Quick inspection
1. Use Prisma Studio (`npm run db:studio`) or DB query.
2. Filter jobs where `status = failed`.
3. Inspect `error` field and `updatedAt`.

### Re-queue failed jobs
Use existing script:
- `node scripts/reset_jobs.js`

### Diagnose common causes
- missing file in `STORAGE_DIR`
- AI service unavailable
- invalid `SECRET_API_KEY`
- invalid file type or size

## 5) Verify Plan Limits and Counter Resets

### Free plan daily limit
1. Create or use a free-plan user.
2. Upload until limit reached.
3. Confirm API returns HTTP 429 after limit.
4. Simulate next day by adjusting `lastResetDate` in DB and re-test.

### Paid plan monthly limit
1. Use paid-plan user.
2. Upload until monthly limit threshold.
3. Confirm API returns HTTP 429 at cap.
4. Simulate month rollover via `lastResetDate` update and verify reset behavior.

## Incident Notes Template
- Timestamp:
- Service impacted:
- Symptom:
- Root cause:
- Immediate fix:
- Preventive action:
