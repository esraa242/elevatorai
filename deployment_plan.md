# ElevatorAI - Vercel & Managed Services Deployment Plan

This guide outlines the strategy to deploy the ElevatorAI - Google ADK Multi-Agent System using Vercel for the frontend and managed serverless infrastructure for the backend and databases. This approach requires zero server maintenance and scales automatically.

## 1. Architecture Overview
*   **Frontend**: Next.js React application hosted on **Vercel**.
*   **Backend (FastAPI)**: Hosted on **Railway** (Recommended due to Vercel's Serverless Function timeout limits which can interrupt the `ModelingAgent`'s 3D generation) OR deployed as **Vercel Serverless Functions**.
*   **Database (PostgreSQL)**: Fully managed Serverless Postgres (e.g., **Supabase**, Neon, or Vercel Postgres).
*   **Cache/Vector DB (Redis)**: Fully managed Serverless Redis (e.g., **Upstash** or Vercel KV).
*   **External APIs**: Google Gemini API, WhatsApp Business API.

---

## 2. Setting Up Databases (Supabase & Upstash)

Before deploying the code, you need to spin up the required backing services.

### A. PostgreSQL Setup (Supabase)
1. Go to [Supabase](https://supabase.com/) and create a new project.
2. Once the database is ready, go to Project Settings -> Database.
3. Copy the **Connection String (URI)**. It will look like: `postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres`

### B. Redis Setup (Upstash)
1. Go to [Upstash](https://upstash.com/) and create a new Redis database.
2. Scroll to the "Connect to your database" section.
3. Copy the **Redis URL** (make sure it's the standard connection string, usually starting with `rediss://`).

---

## 3. Backend Deployment (FastAPI)

While you *can* deploy FastAPI to Vercel using a `vercel.json` rewrite, **Vercel has execution timeouts (10 seconds on the Free tier, up to 300 seconds on Pro)**. Because your `ModelingAgent` generates 3D models using Trimesh, this process might exceed these limits. 

We highly recommend deploying the Python API to **Railway** for reliable background processing.

### Deploying the Backend to Railway:
1. Ensure your codebase is pushed to GitHub.
2. Sign in to [Railway](https://railway.app) and click **New Project**.
3. Select **Deploy from GitHub repo** and connect your repository.
4. Railway will automatically detect the Python environment or the Dockerfile in your repository.
5. Go to your newly created service's **Variables** tab and add:
   * `GOOGLE_CLOUD_PROJECT` = `your-cloud-project`
   * `GEMINI_API_KEY` = `your-key`
   * `WHATSAPP_API_TOKEN` = `your-token`
   * `WHATSAPP_PHONE_NUMBER_ID` = `your-id`
   * `DATABASE_URL` = `your-supabase-postgres-url`
   * `REDIS_URL` = `your-upstash-redis-url`
6. Railway will automatically build and deploy your service. Once deployed, click on **Settings** -> **Networking** and click **Generate Domain** to get your public URL (e.g., `https://elevatorai-api-production.up.railway.app`).

---

## 4. Frontend Deployment (Vercel)

Vercel provides native support for Next.js, making the frontend deployment incredibly smooth.

1. Go to [Vercel](https://vercel.com/) and click **Add New Project**.
2. Import your GitHub repository.
3. In the "Configure Project" step:
   * **Framework Preset**: Next.js (usually auto-detected).
   * **Root Directory**: Click "Edit" and select `frontend/`.
4. Open the **Environment Variables** section and add:
   * Name: `NEXT_PUBLIC_API_URL`
   * Value: `https://elevatorai-api-production.up.railway.app` (Your Railway backend URL).
5. Click **Deploy**. Vercel will build and launch your Next.js application.

---

## 5. Post-Deployment Steps

### 1. Initialize Database Models
You need to create the tables in your Supabase database. You can do this by running the initialization script locally (connected to Supabase) or from your Railway project by using the Railway CLI (`railway run`).
* **Locally**: Ensure your local `.env` has the Supabase `DATABASE_URL`, then run:
  ```bash
  python -c "from shared.models import init_database; init_database()"
  ```

### 2. Configure WhatsApp Webhook
For the `SalesAgent` to function, Meta needs to reach your live backend server to send new messages.
1. Enter the Meta Developer Dashboard -> WhatsApp -> Configuration.
2. Set the callback URL to your deployed backend URL: `https://elevatorai-api-production.up.railway.app/webhook/whatsapp`
3. Enter your verification token and save.

### 3. Add Custom Domain
If you have a custom domain (e.g., `elevatorai.com`), you can add it directly in the Vercel project settings under **Settings -> Domains**. Vercel will automatically provision SSL certificates for you.
