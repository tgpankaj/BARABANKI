# Barabanki Connect — Production Deployment & Operations Runbook

**District Civic Portal for Barabanki, Uttar Pradesh**  
**Version:** 1.0.0 (Production Release)  
**Architecture:** FastAPI + Neon Managed PostgreSQL + Render Web Hosting + Cloudflare Edge DNS

---

## 1. System Architecture

```
[ Citizen / Merchant / Student Browser ]
                  │
                  ▼  (HTTPS / TLS 1.3 / Port 443)
       [ Cloudflare Edge / Render Reverse Proxy ]
                  │
                  ├── (Static Caching: Cache-Control public, max-age=86400)
                  ▼  (HTTP / Proxy Headers)
      [ Render Web Service (Uvicorn ASGI — 2 Workers) ]
      ├── FastAPI Web & REST Endpoints (164 routes)
      ├── Jinja2 SSR Templates (Mobile-First Responsive UI)
      ├── Security Middlewares (CSP, HSTS, CORS, CSRF, Rate Limiting)
      └── Lifespan Initializer & Alembic Migration Engine
                  │
                  ▼  (TLS 1.3 Encrypted / Connection Pooled)
       [ Neon Managed PostgreSQL (Serverless) ]
      ├── Persistent Database Tables (Users, Businesses, Ads, Civic Issues)
      ├── Automatic Continuous WAL Backup & 7-Day PITR
      └── Connection Pooler (pgBouncer on port 5432 / 6543)
```

---

## 2. Environment Variables Specification

> [!IMPORTANT]
> Never commit actual credentials or secret values to Git. All secrets must be populated through the Render Environment Console or in a secure `.env` file that is ignored by Git.

| Variable Name | Required | Default / Format | Description |
|---|---|---|---|
| `ENVIRONMENT` | **Yes** | `production` | Switches application to production security posture |
| `DEBUG` | **Yes** | `False` | Disables verbose debug stack traces in production |
| `HOST` | **Yes** | `0.0.0.0` | Binds to all network interfaces |
| `PORT` | **Yes** | `$PORT` (10000 on Render) | Dynamically assigned port from Render runtime |
| `DATABASE_URL` | **Yes** | `postgresql+psycopg2://...` | Connection string to Neon PostgreSQL with SSL |
| `SECRET_KEY` | **Yes** | 32-byte URL-safe string | Signs session tokens & JWT auth tokens |
| `CSRF_SECRET` | **Yes** | 32-byte URL-safe string | Signs HMAC-SHA256 CSRF protection tokens |
| `COOKIE_SECURE` | **Yes** | `True` | Enforces HTTPS-only transmission for session cookies |
| `ALLOWED_ORIGINS` | **Yes** | JSON array or comma list | Production CORS allowlist (e.g. `["https://barabanki-connect.onrender.com"]`) |
| `RATE_LIMIT_ENABLED` | **Yes** | `True` | Activates in-memory rate limiting against burst abuse |
| `STATIC_CACHE_MAX_AGE` | Optional | `86400` | Browser cache expiration for static assets in seconds |
| `STORAGE_BACKEND` | Optional | `url` | Media storage mode (`url`, `s3`, or `cloudinary`) |

---

## 3. Step-by-Step Neon PostgreSQL Setup

Neon provides a managed serverless PostgreSQL database with an ongoing free tier.

### 3.1 Create Project on Neon
1. Go to [https://console.neon.tech](https://console.neon.tech) and sign in.
2. Click **Create Project**.
3. Name your project: `barabanki-connect`.
4. Region: Choose **Asia Pacific (Singapore)** (`ap-southeast-1`) for lowest latency to India.
5. PostgreSQL Version: Choose **v16** or **v15**.
6. Click **Create Project**.

### 3.2 Obtain Connection String
1. In the Neon Project Dashboard, navigate to the **Dashboard** tab.
2. Under **Connection Details**, ensure **Connection pooling** is checked (uses pgBouncer).
3. Select **SQLAlchemy** or **Connection string**.
4. The connection string looks like:
   ```text
   postgresql://barabanki_user:YOUR_SECRET_PASSWORD@ep-cool-base-123456-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```
5. Note: The application automatically converts `postgres://` to `postgresql+psycopg2://` and enforces `sslmode=require`.

---

## 4. Step-by-Step Render Deployment

### 4.1 Create Web Service from Blueprint (`render.yaml`)
1. Push your repository to GitHub:
   ```powershell
   git push origin main
   ```
2. Log in to [https://dashboard.render.com](https://dashboard.render.com).
3. Click **New +** > **Blueprint**.
4. Connect your `Barabanki` GitHub repository.
5. Render detects [`render.yaml`](file:///c:/Users/hp/OneDrive/Desktop/Projects/Barabanki/render.yaml) automatically.

### 4.2 Configure Environment Variables in Render Dashboard
1. Render will prompt you for the `DATABASE_URL` variable marked with `sync: false`.
2. Paste your Neon PostgreSQL connection string into `DATABASE_URL`.
3. Verify that `SECRET_KEY` and `CSRF_SECRET` are set to automatically generate secure random keys (`generateValue: true`).
4. Set `ALLOWED_ORIGINS`:
   ```json
   ["https://barabanki-connect.onrender.com", "https://barabanki-connect.in", "https://www.barabanki-connect.in"]
   ```
5. Click **Apply**.

### 4.3 Manual Setup (Alternative to Blueprint)
If creating the service manually without the Blueprint:
- **Service Type**: Web Service
- **Runtime**: Python 3
- **Region**: Singapore
- **Branch**: `main`
- **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
- **Start Command**: `python -m alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2 --proxy-headers`
- **Health Check Path**: `/health`
- **Plan**: Free

---

## 5. Database Migrations & Initial Data Bootstrap

### 5.1 Automatic Execution
The production start command runs migrations automatically before starting Uvicorn:
```bash
python -m alembic upgrade head
```
Upon initial boot, the application lifespan detects if the database is clean and automatically seeds authentic Barabanki baseline data (handlooms, civic departments, hospitals, schools, heritage monuments, and admin credentials).

### 5.2 Manual Migration & Pre-Flight Check
You can test the deployment pre-flight checklist locally or in a remote shell using:
```powershell
python scripts/deploy.py
```

### 5.3 Manual Alembic Commands
```powershell
# Check current migration status
python -m alembic current

# Upgrade to latest schema
python -m alembic upgrade head

# Roll back by one revision (if needed)
python -m alembic downgrade -1
```

---

## 6. Custom Domain & HTTPS Configuration

### 6.1 Render Custom Domain Setup
1. In the Render Dashboard, open your `barabanki-connect` service.
2. Navigate to **Settings** > **Custom Domains**.
3. Click **Add Custom Domain** and enter your domain (e.g. `barabanki-connect.in` or `www.barabanki-connect.in`).

### 6.2 DNS Configuration Table

| Host / Name | Record Type | Target / Value | Notes |
|---|---|---|---|
| `@` (Apex) | `ANAME` or `ALIAS` | `barabanki-connect.onrender.com` | Or Cloudflare CNAME flattening |
| `@` (Apex Alternative) | `A` | `216.24.57.1` | Render apex IP (if DNS provider lacks ALIAS) |
| `www` | `CNAME` | `barabanki-connect.onrender.com` | Standard subdomain redirect |
| `portal` | `CNAME` | `barabanki-connect.onrender.com` | Civic portal subdomain |

### 6.3 SSL Certificate
- Render automatically provisions and renews free **Let's Encrypt TLS/SSL certificates** once DNS propagates.
- HTTPS is forced by default on all Render services.
- The portal serves `Strict-Transport-Security: max-age=31536000; includeSubDomains` in production.

---

## 7. Persistent File Storage & Ephemeral Filesystem Policy

### Current Architecture: URL Reference Mode
- Render containers use an ephemeral filesystem that resets on every deploy or restart.
- To guarantee zero data loss, the Barabanki Connect application stores image references as hosted URLs (`image_url` fields) pointing to CDNs, Unsplash, or public object storage.
- User forms and APIs validate URL schemes and reject malicious inputs.
- **No uploaded files are stored on Render's ephemeral disk.**

### Optional Object Storage (Cloudflare R2 / AWS S3)
If direct binary file uploads are needed in future phases:
1. Create a Cloudflare R2 bucket (10 GB free tier with zero egress fees).
2. Set environment variables in Render:
   - `STORAGE_BACKEND=s3`
   - `STORAGE_BUCKET=barabanki-media`
   - `STORAGE_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com`
   - `STORAGE_ACCESS_KEY_ID=<r2-access-key>`
   - `STORAGE_SECRET_ACCESS_KEY=<r2-secret-key>`
   - `STORAGE_PUBLIC_BASE_URL=https://media.barabanki-connect.in`

---

## 8. Monitoring, Health Checks & Log Inspection

### 8.1 Health Endpoint
Render continuously polls:
```http
GET https://barabanki-connect.onrender.com/health
```
**Expected Response (HTTP 200):**
```json
{
  "status": "healthy",
  "database": "connected",
  "environment": "production",
  "district": "Barabanki, Uttar Pradesh",
  "pin_code": "225001",
  "version": "1.0.0"
}
```
If the database probe fails, `/health` reports `status: "degraded"` and logs the sanitized error without exposing credentials.

### 8.2 Log Inspection
- Real-time container logs are accessible in the Render Dashboard under **Logs**.
- To filter logs:
  - Startup logs: Search for `barabanki_connect: Initializing database`
  - Health check logs: Search for `health`
  - Error logs: Search for `ERROR` or `Traceback`

### 8.3 Automated Smoke Testing
Run the smoke test script against the deployed service:
```powershell
python scripts/smoke_test.py --url https://barabanki-connect.onrender.com
```

---

## 9. Backup, Recovery & Rollback Runbook

### 9.1 Neon Continuous Point-In-Time Recovery (PITR)
- Neon continuously archives database WAL (Write-Ahead Logs) for 7 days on the free plan.
- To restore to any past minute:
  1. In the Neon Console, go to **Branches**.
  2. Click **Create Branch**.
  3. Select **Point in Time** and specify the exact timestamp before the incident occurred.
  4. Point `DATABASE_URL` in Render to the restored branch connection string.

### 9.2 Logical PostgreSQL Backups (`pg_dump`)
Run a manual backup before performing schema alterations:
```powershell
# Using the backup utility:
python scripts/db_backup_restore.py --backup

# Direct PostgreSQL command:
pg_dump "$DATABASE_URL" -F c -b -v -f backups/barabanki_backup_$(Get-Date -Format "yyyyMMdd_HHmmss").dump
```

### 9.3 Restoring from Backup (`pg_restore`)
```powershell
pg_restore -d "$DATABASE_URL" -v backups/barabanki_backup_YYYYMMDD_HHMMSS.dump
```

### 9.4 Release Rollback
If a newly deployed commit introduces errors:
1. In Render Dashboard, click on **Deploys**.
2. Find the last known healthy deployment.
3. Click the three dots `...` and select **Rollback to this deploy**.
4. If a database schema rollback is required, run `alembic downgrade -1`.

---

## 10. Free-Tier Resource Limits & Cost Analysis

| Component | Provider | Free Tier Allocation | Limits & Operational Considerations | Cost |
|---|---|---|---|---|
| **Web Service** | Render | 512 MB RAM, 0.1 CPU core | Spins down after 15 min idle; cold start takes ~30–50s on first hit | ₹0 / mo |
| **Database** | Neon | 0.5 GiB storage, 100 Compute Hours | Spins down compute after 5 min idle; auto-wakes in <1 second | ₹0 / mo |
| **Bandwidth** | Render | 100 GB outbound / month | Ample for civic portal with GZip compression and static asset caching | ₹0 / mo |
| **DNS & SSL** | Cloudflare / Render | Unlimited DNS queries & auto SSL | Free Let's Encrypt TLS 1.3 certificates renewed automatically | ₹0 / mo |
| **Object Storage** | URL Reference Mode | Unlimited (uses external CDNs) | Zero storage costs; no ephemeral filesystem risk | ₹0 / mo |
| **Total Cost** | | | **Fully Operational Civic Platform at Zero Recurring Cost** | **₹0.00** |
