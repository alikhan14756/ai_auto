# Creator Studio AI — Database Setup & Migration Guide

**Project Owner:** Muhammad Ali  
**Portfolio:** [alibuild.site](https://alibuild.site)  
**Database Engine:** PostgreSQL 15+ (Local / Supabase Free Tier)  
**ORM:** SQLAlchemy 2.0 Async + asyncpg  
**Migration Tool:** Alembic  
**Total Tables:** 52 tables (+1 `alembic_version`) across 10 functional domains  

---

## 1. Quickstart Connection Configuration

Set your connection string in `backend/.env` (and root `.env`):

```bash
# Asynchronous SQLAlchemy connection string (for FastAPI & Workers)
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.YOUR_SUPABASE_ID.supabase.co:5432/postgres

# Synchronous connection string (used by Alembic migrations & psycopg2)
SYNC_DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_SUPABASE_ID.supabase.co:5432/postgres
```

For local PostgreSQL instances:
```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/creator_studio
SYNC_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/creator_studio
```

---

## 2. Alembic Migration Hierarchy

The database evolution is tracked across 10 progressive migrations matching M01–M15:

```
0001_initial_core_schema.py           # Users, channels, channel_settings, automation_jobs
0002_channel_members_and_teams.py     # Channel multi-tenancy & RBAC membership
0003_topics_and_research.py           # Topics, research_sources, topic_snapshots
0004_scripts_and_fact_checking.py     # Scripts, script_sections, script_claims
0005_voice_narration_models.py        # Voice profiles, narration_tracks, voiceovers
0006_storyboards_and_media_assets.py  # Storyboards, scenes, media_assets, asset_licenses
0007_video_timelines_and_renders.py   # Timelines, tracks, render_jobs, video_masters
0008_thumbnails_and_metadata.py       # Thumbnail compositions, variants, metadata_drafts
0009_qa_veto_gate_and_reports.py      # QA runs, findings, exceptions, release certificates
0010_publishing_and_analytics.py      # Publishing jobs, youtube_videos, analytics telemetry
```

---

## 3. Applying Migrations

To apply all migrations to your database:

```powershell
# Using the backend virtual environment
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```

To roll back one migration:
```powershell
alembic downgrade -1
```

To inspect current database revision:
```powershell
alembic current
```

---

## 4. Key Architectural Patterns

### A. Atomic Queue Leasing (`FOR UPDATE SKIP LOCKED`)
The `automation_jobs` table powers the durable task queue:
```sql
SELECT id, job_type, payload
FROM automation_jobs
WHERE status = 'PENDING'
  AND (scheduled_for IS NULL OR scheduled_for <= NOW())
ORDER BY priority ASC, created_at ASC
FOR UPDATE SKIP LOCKED
LIMIT 1;
```
This guarantees that multiple concurrent workers never process the same job, and if a worker crashes, the active transaction rolls back automatically with zero job loss.

### B. Foreign Key Integrity & Cascades
All child records (scenes, voiceover chunks, claims, QA findings) reference their parent project or channel with `ON DELETE CASCADE`, preventing orphaned media references.

### C. Encrypted Credentials
The `channels.youtube_credentials` and `channel_settings.credentials_encrypted` columns store AES-256-GCM ciphertexts. Decryption is performed in memory only when calling external authorized APIs.
