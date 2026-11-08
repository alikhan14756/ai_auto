# Creator Studio AI — Zero-Cost Cloud Hosting Architecture Evaluation

**Project Owner:** Muhammad Ali  
**Portfolio:** [alibuild.site](https://alibuild.site)  
**Evaluation Scope:** Genuinely Free Cloud Hosting Options vs Local-First Staging  
**Hosting Budget:** Strictly $0.00 / month  
**Status:** Independent Architectural Research  

---

## 1. Executive Summary & Verdict

To maintain a strict **$0.00/month** hosting budget while providing reliable execution for FastAPI, PostgreSQL, durable queues, and FFmpeg video compositing, an independent evaluation of cloud hosting platforms was conducted.

### Core Architecture Reality
Creator Studio AI consists of two distinct runtime workloads:
1. **Stateless Web API (FastAPI):** Request/response HTTP traffic with short execution times.
2. **Stateful Long-Running Video Worker (`app.workers.runner`):** Continuous queue polling (`SKIP LOCKED`), heartbeats, multi-minute FFmpeg rendering, and large temporary disk writes (50MB–500MB per video).

```
========================================================================================================
                               CLOUD HOSTING MATRIX (GENUINE $0.00 BUDGET)
========================================================================================================
 Platform          Stateless API    Background Worker    FFmpeg Viability   Credit Card?   True $0 Guarantee
--------------------------------------------------------------------------------------------------------
 GitHub Pages      N/A (Static)     UNSUPPORTED          UNSUPPORTED        NO             YES (Verified)
 Supabase Free     N/A (DB only)    UNSUPPORTED          UNSUPPORTED        NO             YES (500MB DB)
 Google Cloud Run  EXCELLENT        POOR (Sleeps to 0)   POOR (OOM/Disk)    YES (Mandatory) NO (Overage Risk)
 Render (Free)     ACCEPTABLE       UNSUPPORTED (Paid)   FAIL (512MB OOM)   NO             YES (Sleeps 15m)
 Fly.io            DEPRECATED       UNSUPPORTED          FAIL               YES (Mandatory) NO
 Local Workstation EXCELLENT        EXCELLENT            EXCELLENT          NO             YES (100% Zero-Cost)
========================================================================================================
```

**Architectural Recommendation:**  
**Adopt the Decoupled Local-First Hybrid Architecture**:
- **Frontend:** Hosted on **GitHub Pages** (free CDN, global availability, zero maintenance).
- **Relational Database:** Hosted on **Supabase Free Tier** (managed PostgreSQL 16, 52 tables, ACID queue leases).
- **API & Video Worker:** Hosted on the owner's **Windows Workstation** (`scripts/start-staging-backend.ps1` and `scripts/start-staging-worker.ps1`).

---

## 2. In-Depth Cloud Provider Evaluation

### A. Google Cloud Run

| Dimension | Specification & Analysis |
| :--- | :--- |
| **Free Tier Allowance** | 2,000,000 requests/month; 360,000 vCPU-seconds; 180,000 GiB-seconds memory; 1 GiB North America egress. |
| **Billing Account Requirement** | **Mandatory Credit Card.** Google Cloud requires active billing credentials to enable Cloud Run APIs. |
| **Billing Risk** | **HIGH.** If traffic spikes, or if "CPU Always Allocated" is enabled to allow background queue workers to run without incoming HTTP requests, Cloud Run burns the free allowance within days and charges the card automatically. |
| **Idle Behavior** | Scales to zero (`min-instances = 0`) when idle. Cold start: 1.5–3.5 seconds. |
| **Persistent Worker Support** | **Unviable on free tier.** Cloud Run throttles CPU to near-zero when no HTTP request is being actively processed. The worker daemon would stall mid-render. |
| **Storage Persistence** | **Ephemeral.** In-memory `/tmp` filesystem only, limited by allocated container RAM. Video rendering would easily exhaust RAM and trigger container termination. |
| **FastAPI Suitability** | **Excellent** for the stateless API if billing risk is accepted. |
| **Worker Suitability** | **Unviable** without minimum instances (paid tier). |

---

### B. Render (Free Tier)

| Dimension | Specification & Analysis |
| :--- | :--- |
| **Free Tier Allowance** | 750 instance hours/month for Web Services; 512 MB RAM; 0.1 vCPU. |
| **Billing Account Requirement** | No credit card required for free services. |
| **Billing Risk** | **Low.** Hard-capped; services pause when limit is reached. |
| **Idle Behavior** | **Spins down after 15 minutes of inactivity.** Cold start delay: **50 to 90 seconds**. |
| **Persistent Worker Support** | **UNSUPPORTED on Free Tier.** Render explicitly classifies Background Workers as a paid-only product ($7/month per worker). Running the worker inside the web service fails because Render puts the service to sleep as soon as user web traffic stops. |
| **Storage Persistence** | **Ephemeral.** Disk is completely wiped upon container restart or sleep cycle. Rendered videos, audio assets, and logs are deleted. |
| **FastAPI Suitability** | **Marginal.** The 60-second cold start on login/dashboard requests causes timeouts on client browsers. |
| **FFmpeg Worker Suitability** | **FATAL.** 512 MB RAM cannot sustain FFmpeg multi-stream video muxing and subtitle burning. Process is killed via Linux OOM (Out Of Memory) killer. |

---

### C. Fly.io & Koyeb

| Dimension | Fly.io Analysis | Koyeb Analysis |
| :--- | :--- | :--- |
| **Free Tier Reality** | Free tier discontinued for new accounts without credit card. Requires prepayment or credit card verification. | 2 nano instances (512MB RAM, 0.1 vCPU). |
| **Worker Viability** | Workers consume billable machine hours. | 512MB RAM limit causes FFmpeg OOM crash. |
| **Persistent Disk** | Paid feature ($0.15/GB/mo). | Ephemeral storage on free tier. |
| **Verdict** | Not a genuine zero-cost option. | Unsuitable for video processing. |

---

## 3. Why Local-First Staging is the Optimal Zero-Cost Choice

1. **Zero Financial Exposure:** No credit cards linked to hosting, guaranteeing $0.00 cloud expenses.
2. **Direct Hardware Access:** FFmpeg utilizes the local CPU/threads without cloud RAM caps (e.g. 512MB limits) or cloud bandwidth throttles.
3. **True Storage Persistence:** Media renders, narration WAV files, and storyboard assets remain stored on local SSD (`storage/`), with zero ephemeral wiping.
4. **Autonomous Queue Processing:** The worker daemon (`app.workers.runner`) runs continuously in the background, reliably polling Supabase PostgreSQL via `FOR UPDATE SKIP LOCKED`.
5. **Decoupled Frontend:** The static Next.js frontend deployed to **GitHub Pages** gives the owner a polished, live web interface accessible from anywhere.

---

## 4. Path to Future Cloud Deployment (When Budget Allows)

When the owner decides to allocate a cloud budget ($10–$25/month), the recommended upgrade path is:
1. **Stateless API:** Deploy FastAPI Docker container to Google Cloud Run (min instances = 0, auto-scaling up to 3). Cost: ~$0.00–$2.00/mo.
2. **Persistent Queue Worker:** Deploy worker Docker container to a lightweight Linux VPS (Hetzner Cloud CX22 or DigitalOcean Droplet: 2 vCPU, 4GB RAM, 40GB NVMe SSD). Cost: ~$4.00–$6.00/mo.
3. **Object Storage:** Cloudflare R2 for master video storage (10 GB free, $0 egress fees). Cost: $0.00/mo.
4. **Relational Database:** Supabase Pro ($25/mo) or Neon Serverless PostgreSQL ($0–$5/mo).
