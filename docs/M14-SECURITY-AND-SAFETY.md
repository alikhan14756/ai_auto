# Creator Studio AI — Milestone 14: Security, Safety & Threat Model
## Autonomous Execution Safety, Threat Mitigation & Audit Logging

**Project Owner:** Muhammad Ali  
**Portfolio:** [alibuild.site](https://alibuild.site)  
**System:** Creator Studio AI  
**Milestone:** M14 of 15  
**Document Status:** Production Reference  

---

## 1. Threat Modeling for Autonomous Content Systems

Allowing background systems to orchestrate generative AI models, video rendering pipelines, and social media APIs introduces unique attack vectors:

| Threat Category | Potential Attack Vector | System Defense & Mitigation |
| :--- | :--- | :--- |
| **Prompt Injection Escalation** | Malicious topic text attempting to manipulate system prompts or override automation levels. | AI outputs treated strictly as untrusted text; validated against Pydantic schemas; state transitions and permission changes are strictly code-level and restricted to authenticated owners. |
| **Resource Starvation (DoS)** | Rapid queuing of heavy 4K video rendering jobs causing worker starvation or host crash. | Queue concurrency limits (max 2 active renders), daily execution caps, and per-workflow timeout watchdogs (300s render limit). |
| **Financial Overrun** | Loop of AI token requests or paid third-party API calls exhausting developer credit. | Hard $0.00 default monthly spend limit; `UsageTrackingService` rejects billable requests unless explicitly enabled by super admin. |
| **Unauthorized YouTube Publishing** | Faulty logic or tampered state posting unreviewed or unverified content to public channel. | M11 QA Veto Gate must return `status="APPROVED"` with zero vetoes. Hardcoded database foreign key checks on `QualityAudit.id` at publication upload time. |
| **BOLA / IDOR Cross-Tenant Access** | Tenant A attempts to view or trigger workflows, schedules, or policies belonging to Tenant B. | Mandatory tenant validation query filtering by `channel_id == current_user.channel_id` on all REST endpoints and background job processors. |

---

## 2. Server-Side Policy Enforcement

All policy enforcement takes place within the backend `PolicyEngine` (`app/services/orchestration/policy_engine.py`). 

No client-supplied JSON parameters or flags (e.g. `{"skip_qa": true}`, `{"auto_publish": true}`) are trusted. The server evaluates:
1. `Channel.automation_level` (Level 0, 1, 2, or 3)
2. `WorkflowPolicy` active rules for the channel
3. `ResourceUsageRecord` against channel monthly spending limit
4. Current user's authenticated RBAC role (`SUPER_ADMIN`, `ADMIN`, `CREATOR`)

---

## 3. Comprehensive Audit Trail

Every state change, automated trigger, manual approval, failure recovery, and policy evaluation is recorded in `WorkflowEvent` and `AutomationAuditEvent`:

```json
{
  "event_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "channel_id": "3a0b5c1d-1234-5678-9abc-def012345678",
  "workflow_id": "c1f8e24a-9876-5432-10fe-dcba98765432",
  "event_type": "STAGE_COMPLETED",
  "stage_key": "render",
  "actor_type": "WORKER_DAEMON",
  "actor_id": "worker-runner-node-1",
  "details": {
    "duration_seconds": 42.1,
    "output_file": "storage/renders/proj_123_final.mp4",
    "qa_gate_status": "READY_FOR_AUDIT"
  },
  "timestamp": "2026-11-08T05:30:00Z"
}
```

Audit trails are append-only. No API endpoint exists to delete or truncate audit records.
