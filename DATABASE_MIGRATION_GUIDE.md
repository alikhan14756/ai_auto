# CREATOR STUDIO AI — DATABASE MIGRATION & RECOVERY GUIDE

**Project Owner:** Muhammad Ali  
**Portfolio:** [https://alibuild.site](https://alibuild.site)  
**Database Engine:** PostgreSQL 15+ (Local / Supabase)  
**Migration Tool:** Alembic (Python)

---

## 1. Migration Architecture & Version History

Creator Studio AI maintains a strict, linear Alembic migration history without conflicting heads or branching. The current active chain contains 10 migrations:

| Revision ID | Milestone | Description | Affected Tables / Entities |
| :--- | :--- | :--- | :--- |
| `0001` | M01–M03 | Initial Foundation Schema | `users`, `channels`, `video_projects`, `usage_records` |
| `0002` | M04 | Durable Job Queue | `automation_jobs`, queue state, retry counters |
| `0003` | M05 | Topic Discovery Engine | `topic_proposals`, research metrics, difficulty scores |
| `0004` | M06 | Script Studio & Claims | `scripts`, `script_claims`, fact-checking status |
| `0005` | M07 | Narration & Voice Studio | `voice_profiles`, `narration_tracks`, audio files |
| `0006` | M08 | Visual Assets & Storyboards | `storyboards`, `scenes`, `media_assets`, licensing |
| `0007` | M09–M10 | Video Renders & Thumbnails | `timelines`, `timeline_scenes`, `render_jobs`, `thumbnails` |
| `0008` | M11–M12 | QA Veto & Resumable Publish | `qa_runs`, `qa_findings`, `qa_exceptions`, `publishing_jobs`, `resumable_sessions` |
| `0009` | M13 | Analytics & Retention Curves | `analytics_snapshots`, `video_metrics`, `retention_curves`, `sync_audits` |
| `0010` | M14–M15 | Workflow Orchestration & Policies | `workflow_runs`, `workflow_stages`, `automation_policies`, `content_schedules` |

---

## 2. Executing Migrations

### 2.1. Standard Migration to Latest Head
To apply all pending migrations against the configured database:

```powershell
cd backend
.venv\Scripts\alembic upgrade head
```

### 2.2. Checking Current Database Revision
To verify the active migration revision recorded in the `alembic_version` table:

```powershell
cd backend
.venv\Scripts\alembic current
```

### 2.3. Inspecting Migration History
To display full migration history and dependencies:

```powershell
cd backend
.venv\Scripts\alembic history --verbose
```

---

## 3. Supabase Connection & Pooling Specifications

### 3.1. Connection Strings
Supabase provides two distinct endpoints:

- **Transaction Pooler (PgBouncer, Port 6543):**
  - **Protocol:** `postgresql+asyncpg://`
  - **Host:** `aws-0-[REGION].pooler.supabase.com:6543`
  - **Application Settings:** Transaction poolers require disabling asyncpg's prepared statement cache. This is handled automatically in `app/db/session.py` when port `6543` or `pooler.supabase.com` is present (`statement_cache_size = 0`).
  - **SSL Requirement:** Remote connections require SSL (`ssl="require"` is automatically injected in `app/db/session.py`).

- **Direct Session Connection (Port 5432):**
  - **Protocol:** `postgresql://`
  - **Host:** `aws-0-[REGION].pooler.supabase.com:5432`
  - **Alembic Requirement:** DDL migration commands like `CREATE TABLE` and `ALTER TABLE` must run against the direct session port with `sslmode=require`.

---

## 4. Empirical Backup & Disaster Recovery Verification

Disaster recovery readiness is verified via automated simulation in `tests/test_backup_restoration_evidence.py`.

### 4.1. Creating a Database Dump
```powershell
# Using pg_dump with custom compressed archive format
pg_dump --dbname="postgresql://postgres:[PASSWORD]@[HOST]:5432/creator_studio_ai" `
        --format=c `
        --file="storage/backups/creator_studio_ai_$(Get-Date -Format 'yyyyMMdd_HHmmss').dump"
```

### 4.2. Restoring from a Backup Archive
```powershell
# Clean restore using pg_restore
pg_restore --clean --if-exists `
           --dbname="postgresql://postgres:[PASSWORD]@[HOST]:5432/creator_studio_ai" `
           "storage/backups/[BACKUP_FILE].dump"
```

### 4.3. Post-Restoration Verification
1. Verify tables exist: `SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';`
2. Run backend health check: `GET /api/v1/health`
3. Execute test suite: `pytest tests/test_backup_restoration_evidence.py`
