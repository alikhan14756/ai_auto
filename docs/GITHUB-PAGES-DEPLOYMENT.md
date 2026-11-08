# Creator Studio AI — GitHub Pages Frontend Deployment Guide

**Project Owner:** Muhammad Ali  
**Portfolio:** [alibuild.site](https://alibuild.site)  
**Target:** GitHub Pages Static Site Hosting  
**Hosting Cost:** $0.00 / month  
**Status:** Static Export Verified  

---

## 1. Static Export Compatibility Audit

An exhaustive audit of the Next.js 15.1.0 frontend was conducted to evaluate full static export compatibility (`output: "export"`) per the [official Next.js Static Export specification](https://nextjs.org/docs/app/building-your-application/deploying/static-exports).

| Evaluation Category | Audit Finding | Compatibility Status |
| :--- | :--- | :---: |
| **Server Components** | All 25 pages in `frontend/src/app` declare `"use client"`. Zero runtime server-rendered data dependencies. | **COMPATIBLE** |
| **API Route Handlers** | Zero `route.ts` or `route.js` files in `frontend/src`. All API routes reside on the FastAPI backend. | **COMPATIBLE** |
| **Server Actions** | Zero `"use server"` functions exist. All mutations execute via client `fetch` calls. | **COMPATIBLE** |
| **Next.js Middleware** | Zero `middleware.ts` files exist. Auth protection and session handling are client-driven via Supabase SDK. | **COMPATIBLE** |
| **Dynamic Routes** | Zero dynamic segment folders (`[id]`). All 25 application views are statically defined. | **COMPATIBLE** |
| **Image Optimization** | `images: { unoptimized: true }` configured in `next.config.ts`, avoiding Node.js Sharp runtime dependencies. | **COMPATIBLE** |
| **Base Path Routing** | Dynamic `basePath` support via `NEXT_PUBLIC_BASE_PATH` for project sites (`/<repo>`). | **COMPATIBLE** |
| **Trailing Slashes** | `trailingSlash: true` enabled during export, generating `out/<page>/index.html` for clean static hosting. | **COMPATIBLE** |

---

## 2. Next.js Static Export Configuration

The frontend configuration in [`frontend/next.config.ts`](file:///d:/auto/ai%20automation/frontend/next.config.ts) is parameterized to toggle seamlessly between local standalone Docker mode and GitHub Pages static export:

```typescript
import type { NextConfig } from "next";

const isExport = process.env.OUTPUT_MODE === "export" || process.env.NEXT_EXPORT === "true";
const rawBasePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
const basePath = rawBasePath && rawBasePath !== "/" 
  ? (rawBasePath.startsWith("/") ? rawBasePath : `/${rawBasePath}`) 
  : undefined;
const backendUrl = process.env.INTERNAL_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  output: isExport ? "export" : "standalone",
  reactStrictMode: true,
  trailingSlash: isExport ? true : false,
  basePath: basePath,
  images: {
    unoptimized: true,
  },
  ...(isExport
    ? {}
    : {
        async rewrites() {
          return [
            { source: "/api/backend/:path*", destination: `${backendUrl}/api/v1/:path*` },
            { source: "/api/v1/:path*", destination: `${backendUrl}/api/v1/:path*` },
            { source: "/health", destination: `${backendUrl}/health` },
          ];
        },
      }),
};

export default nextConfig;
```

---

## 3. GitHub Pages Repository Base Path & Routing

### Project Sites vs User Sites
- **User / Organization Site (`https://<username>.github.io`):**
  - Requires `NEXT_PUBLIC_BASE_PATH=""`.
- **Project Site (`https://<username>.github.io/<repository-name>`):**
  - Next.js requires assets and routes to be prefixed with `/<repository-name>`.
  - In our GitHub Actions workflow, `NEXT_PUBLIC_BASE_PATH` is automatically set to `/${{ github.event.repository.name }}`.

### Nested Route Refreshes & 404 Prevention
Static web servers on GitHub Pages serve `index.html` inside folders when trailing slashes are requested. By enabling `trailingSlash: true`, Next.js creates:
- `out/analytics/index.html` (accessible via `/analytics/`)
- `out/automation/index.html` (accessible via `/automation/`)
- `out/settings/health/index.html` (accessible via `/settings/health/`)
- `out/404.html` (fallback error page automatically served by GitHub Pages)

---

## 4. GitHub Actions Deployment Pipeline

The dedicated GitHub Pages deployment workflow is located at [`.github/workflows/deploy-pages.yml`](file:///d:/auto/ai%20automation/.github/workflows/deploy-pages.yml):

### Least-Privilege Permissions
```yaml
permissions:
  contents: read
  pages: write
  id-token: write
```

### Build & Deploy Sequence
1. **Checkout Code:** Uses `actions/checkout@v4`.
2. **Setup Node 20:** Uses `actions/setup-node@v4` with npm dependency caching.
3. **Typecheck & Lint:** Executes `npm run typecheck` (`tsc --noEmit`) and `npm run lint`.
4. **Static Export Build:** Sets `OUTPUT_MODE=export` and bundles static assets into `frontend/out`.
5. **Pages Configuration:** Executes `actions/configure-pages@v5`.
6. **Artifact Packaging:** Uploads `frontend/out` via `actions/upload-pages-artifact@v3`.
7. **Deployment:** Deploys via `actions/deploy-pages@v4` to GitHub Pages CDN.

---

## 4.5. Browser Mixed Content & Private Network Access (PNA) Safeguards

> [!IMPORTANT]
> **GitHub Pages operates strictly over HTTPS (`https://<username>.github.io/<repo>/`).**

Modern web browsers enforce **Mixed Content Blocking** and **Private Network Access (PNA)** rules:
- Any API request from an HTTPS web page targeting an insecure HTTP endpoint (e.g. `http://...`) is blocked.
- Any request from a public web origin targeting loopback/local addresses (`http://localhost:8000` or `http://127.0.0.1:8000`) is blocked by default.

### Recommended Staging Connectivity:
1. **Local Staging in Browser:** Run both frontend and backend locally (`http://localhost:3000` connecting to `http://localhost:8000`). This completely avoids mixed-content restrictions.
2. **Connecting GitHub Pages to Local Backend via HTTPS Tunnel:**
   Use a free, secure HTTPS tunnel (such as Cloudflare Tunnel):
   ```powershell
   cloudflared tunnel --url http://127.0.0.1:8000
   ```
   Pass the resulting `https://...trycloudflare.com` URL as `NEXT_PUBLIC_API_BASE_URL` in GitHub Repository Variables or Secrets.

---

## 5. Security & Secret Hygiene

> [!CAUTION]
> **Never store private API keys or database passwords in GitHub Actions repository secrets for the frontend build.**

All variables prefixed with `NEXT_PUBLIC_` are inlined into client JavaScript bundles and are publicly visible in browser dev tools.
- **Allowed Frontend Variables (Public):**
  - `NEXT_PUBLIC_API_BASE_URL`: Public endpoint of the FastAPI backend (e.g., `http://localhost:8000` or secure tunnel URL).
  - `NEXT_PUBLIC_SUPABASE_URL`: Public Supabase project URL (`https://<project-ref>.supabase.co`).
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Supabase client-side anonymous key (safe for browser exposure).
  - `NEXT_PUBLIC_BASE_PATH`: URL path prefix for GitHub Pages.
- **Strictly Prohibited on Frontend (Private):**
  - `DATABASE_URL` / `DATABASE_URL_SYNC`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `SUPABASE_JWT_SECRET`
  - `APP_MASTER_ENCRYPTION_KEY`
  - `GEMINI_API_KEY`
  - `YOUTUBE_CLIENT_SECRET`

---

## 6. Owner Setup Instructions on GitHub

To enable automated deployment on GitHub Pages:

1. **Push Repository to GitHub:**
   ```powershell
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git add .
   git commit -m "feat: complete staging preparation and github pages export"
   git push -u origin master
   ```
2. **Enable GitHub Pages:**
   - In your GitHub repository, navigate to **Settings** -> **Pages**.
   - Under **Build and deployment** -> **Source**, select **GitHub Actions**.
3. **Configure Repository Variables (Optional for Custom Tunnel/Domain):**
   - Go to **Settings** -> **Secrets and variables** -> **Actions** -> **Variables** tab.
   - Add `NEXT_PUBLIC_API_BASE_URL` with your local backend tunnel URL or staging endpoint.
4. **Trigger Deployment:**
   - The workflow automatically runs on push to `main` or `master`.
   - Alternatively, trigger manually from the **Actions** tab -> **Deploy Next.js Frontend to GitHub Pages** -> **Run workflow**.
