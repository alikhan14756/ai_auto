# Creator Studio AI — Backup and Disaster Recovery Strategy

**Project Owner:** Muhammad Ali ([alibuild.site](https://alibuild.site))  
**Milestone:** M15 — Production Hardening & Official Release  
**Release Version:** v0.1.0-RELEASE  

---

## 1. Recovery Objectives

- **Recovery Point Objective (RPO):** Maximum 1 hour (via Supabase automated WAL archiving and point-in-time recovery).
- **Recovery Time Objective (RTO):** Under 30 minutes to restore service on an alternative host.

---

## 2. Backup Coverage Matrix

| Asset | Storage Location | Backup Mechanism | Frequency | Retention |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL Database** | Supabase / Managed PG | Daily automated snapshot + continuous WAL archiving | Daily / Continuous | 30 Days |
| **Script History & Claims** | PostgreSQL `scripts`, `script_claims` | Relational tables in DB backup | Continuous | Indefinite |
| **Rendered Master Videos** | Cloudflare R2 / Local Disk | Multi-region bucket replication | On Upload | Indefinite |
| **Interim Video Clips / B-Roll** | Cloudflare R2 / Local Disk | Local cache with auto-cleanup | Ephemeral | 30 Days |
| **Thumbnails & Storyboards**| Cloudflare R2 / Local Disk | Multi-region bucket replication | On Upload | Indefinite |
| **Encryption Keys & Secrets**| Secure Environment / Secrets Mgr | Offline encrypted vault / Secrets Manager | On Change | Indefinite |

---

## 3. Database Restoration Procedure

### 1. Point-in-Time Recovery (PITR) on Supabase
1. Navigate to Supabase Dashboard -> Database -> Backups.
2. Select point in time prior to incident or corrupted migration.
3. Click "Restore to this point".
4. Database will restore within 5–15 minutes with zero data loss prior to the target timestamp.

### 2. Manual PostgreSQL pg_dump Restoration
```bash
# Export custom-format backup
pg_dump -h localhost -U postgres -d creator_studio_ai -F c -b -v -f creator_studio_backup.dump

# Restore backup to target database
pg_restore -h target-host -U postgres -d creator_studio_ai -v creator_studio_backup.dump
```

### 3. Verify Post-Restoration Integrity
```bash
cd backend
alembic current
.venv\Scripts\pytest tests/ -q
```

---

## 4. Disaster Recovery Runbook

### Scenario A: API Server Crash / Hardware Failure
1. Spin up replacement container or VPS using `docker compose up -d`.
2. Provide identical `.env` containing `DATABASE_URL` and `APP_MASTER_ENCRYPTION_KEY`.
3. Verify `/ready` endpoint returns HTTP 200 within 60 seconds.
4. Update DNS record or load balancer target to new server IP.

### Scenario B: Worker Daemon Hang or Stalled Rendering Job
1. The autonomous watchdog (`ProductionHealthMonitor`) automatically flags jobs whose heartbeat has lapsed for $> 180$ seconds.
2. If retries remain ($< 3$), the stage is reset to `PENDING` and assigned to an available worker thread.
3. If retries are exhausted, the execution transitions to `FAILED` and an alert is recorded in `/api/v1/system/failures`.
4. Platform administrator can restart the worker daemon process without data corruption:
   ```bash
   docker compose restart worker
   ```

### Scenario C: Master Encryption Key Loss or Rotation
1. **Critical:** Always back up `APP_MASTER_ENCRYPTION_KEY` in an offline password manager.
2. If key rotation is required:
   - Query all records with `oauth_refresh_token_encrypted`.
   - Decrypt with old key, re-encrypt with new key, and commit in a single atomic transaction.
   - Update `APP_MASTER_ENCRYPTION_KEY` in environment variables and restart backend processes.
