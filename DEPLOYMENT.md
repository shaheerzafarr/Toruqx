# 🚀 Toruqx Production Deployment Guide (100% Free Tier)

This guide walks you through deploying the **Toruqx Secure RAG Engine** to completely free cloud hosting services.

---

## 📋 Free Cloud Architecture

| Component | Provider | Free Tier Details | Why We Use It |
|---|---|---|---|
| **Frontend** | [Vercel](https://vercel.com) | Unlimited Bandwidth, Auto HTTPS | Native support for Next.js build caching and CDN |
| **Backend API** | [Render](https://render.com) | Free Web Service Instance (RAM capped at 512MB) | Zero-maintenance API hosting directly from GitHub |
| **Relational Database** | [Neon](https://neon.tech) | 1 Free Project (0.5 vCPU, 256MB RAM) | Serverless PostgreSQL with autoscale and branch capabilities |
| **Vector Index** | [Qdrant Cloud](https://qdrant.to/cloud) | 1 Free Cluster (1GB RAM, 0.5 vCPU) | Managed semantic indexing and search speed |
| **Caching & Rate Limiter** | [Upstash](https://upstash.com) | 1 Free Serverless Redis (10,000 reqs/day) | Sub-millisecond sliding rate limits and RAG query cache |

---

## 🛠️ Step 1: Provision Serverless Databases

Before deploying code, set up your serverless datastores.

### 🐘 1. PostgreSQL (Neon.tech)
1. Register a free account at [Neon.tech](https://neon.tech).
2. Create a new project named `toruqx-db` and select your nearest region.
3. In the Neon dashboard, copy your **Connection String** (use the pooled connection string prefix `postgresql://` or `postgres://`).
4. Note this down as `DATABASE_URL`. Ensure you replace the password placeholder.

### 🌀 2. Vector Store (Qdrant Cloud)
1. Register at [Qdrant Cloud](https://qdrant.to/cloud).
2. Click **Create Cluster** and select the **Free Tier (1GB Storage / 0.5 vCPU)**.
3. Once created, copy the **Cluster URL** (e.g. `https://xxx-xxx.aws.qdrant.io:6333`). Note this down as `QDRANT_URL`.
4. Generate an **API Key** in the Access Keys console. Note this down as `QDRANT_API_KEY`.

### ⚡ 3. Caching & Security (Upstash Redis)
1. Register at [Upstash](https://upstash.com).
2. Click **Create Database**, name it `toruqx-redis`, and select **Redis Serverless**.
3. Under the database details page, copy the **Redis URL** starting with `rediss://` (port 6379 or similar). Note this down as `REDIS_URL`.

---

## 🛠️ Step 2: Deploy FastAPI Backend on Render

1. Log in to [Render](https://render.com).
2. Click **New** ➡️ **Web Service**.
3. Link your GitHub repository (`shaheerzafarr/Toruqx`).
4. In the creation wizard, fill in the following parameters:
   - **Name**: `toruqx-backend`
   - **Environment**: `Python3` (or choose `Docker` and it will automatically use the `backend/Dockerfile` we created!)
   - **Region**: Select the region closest to your databases.
   - **Branch**: `main`
   - **Root Directory**: `backend` (This isolates build commands to the backend folder)
   - **Build Command**: `pip install -r requirements.txt` (only needed if using Python3 environment instead of Docker)
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (only needed if using Python)
   - **Instance Type**: Select **Free**
5. Click **Advanced** and add the following **Environment Variables**:
   - `DATABASE_URL` = (Your Neon PostgreSQL Connection string. *Change prefix `postgresql://` to `postgresql+asyncpg://` for async compatibility*)
   - `REDIS_URL` = (Your Upstash Redis connection string)
   - `QDRANT_URL` = (Your Qdrant Cluster URL)
   - `GEMINI_API_KEY` = (Your Google Gemini AI API key)
   - `JWT_SECRET_KEY` = (A random high-entropy alphanumeric string)
   - `TURNSTILE_SECRET_KEY` = (Your Cloudflare Turnstile Secret Key, or set `BYPASS_TURNSTILE=true` for testing/mocking)
   - `BYPASS_TURNSTILE` = `false`
6. Click **Deploy Web Service**. Once built, Render will output a live URL (e.g. `https://toruqx-backend.onrender.com`). Note this down as `BACKEND_API_URL`.

---

## 🛠️ Step 3: Deploy Next.js Frontend on Vercel

1. Log in to [Vercel](https://vercel.com).
2. Click **Add New** ➡️ **Project**.
3. Import your GitHub repository (`shaheerzafarr/Toruqx`).
4. In the Project Configuration:
   - **Framework Preset**: Select **Next.js**
   - **Root Directory**: Keep as root `./` (Vercel automatically compiles the Next.js app in the root directory)
5. Expand **Environment Variables** and add:
   - `NEXT_PUBLIC_API_URL` = `https://toruqx-backend.onrender.com` (Your live Render backend URL)
   - `NEXT_PUBLIC_TURNSTILE_SITE_KEY` = (Your Cloudflare Turnstile Site Key)
6. Click **Deploy**. Vercel will build and host your site in less than 2 minutes, giving you a custom production domain name (e.g. `https://toruqx.vercel.app`).

---

## 🛡️ Production Verification Checklist
- [ ] Confirm you can load the Vercel app domain.
- [ ] Navigate to `/signup` and verify the registration form processes data.
- [ ] Log in and enter `/chat`. Ingest a document and check the status changes to `Completed` (this tests connection between Backend, Postgres, Qdrant, and Redis).
- [ ] Send a chat prompt and verify that grounding citations return.
