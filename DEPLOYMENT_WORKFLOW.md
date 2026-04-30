# ElevatorAI - Deployment Workflow

This guide walks you through deploying the fixed ElevatorAI project step by step.

## Prerequisites

- **Docker & Docker Compose** installed
- **Google AI Studio API Key** ([Get one free](https://aistudio.google.com/app/apikey))
- **Git** installed

---

## Step 1: Clone and Setup

```bash
# Clone the fixed repo
git clone https://github.com/esraa242/elevatorai.git
cd elevatorai

# Copy environment file
cp .env.example .env

# Edit .env with your Gemini API key
nano .env
```

**Minimum required in `.env`:**
```env
GEMINI_API_KEY=your-gemini-api-key-here
DATABASE_URL=postgresql://postgres:postgres@db:5432/elevatorai_adk
REDIS_URL=redis://redis:6379/0
SECRET_KEY=any-random-secret
```

> **Note:** WhatsApp fields are optional. If left empty, quotes will be generated but not sent via WhatsApp.

---

## Step 2: Start Infrastructure (Local Development)

```bash
# Start PostgreSQL and Redis only
docker-compose up -d db redis

# Wait 10 seconds for databases to be ready
sleep 10
```

---

## Step 3: Initialize Database & Seed Data

### Option A: Using local Python
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Create tables and seed cabin data
python seed_data.py
```

### Option B: Using Docker
```bash
# Build the API image
docker-compose build api

# Run seed script in container
docker-compose run --rm api python seed_data.py
```

You should see output like:
```
Connecting to database...
Creating tables...
Seeding cabin designs...
  Added cabin: Imperial Gold
  Added cabin: Skyline Minimalist
  Added cabin: Biophilic Sanctuary
  ...
Done! Database is ready.
```

---

## Step 4: Start All Services

```bash
# Start everything
docker-compose up -d

# Check all services are running
docker-compose ps

# View logs
docker-compose logs -f
```

Services will be available at:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Health Check:** http://localhost:8000/health
- **Database:** localhost:5432
- **Redis:** localhost:6379

---

## Step 5: Test the Pipeline

### Test 1: Health Check
```bash
curl http://localhost:8000/health
```
Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "gemini_configured": true,
  "whatsapp_configured": false
}
```

### Test 2: Vision Analysis Only
```bash
curl -X POST http://localhost:8000/api/v2/analyze \
  -F "file=@/path/to/your/villa-photo.jpg"
```

### Test 3: Full Pipeline
```bash
curl -X POST http://localhost:8000/api/v2/full-pipeline \
  -F "file=@/path/to/your/villa-photo.jpg" \
  -F "customer_name=John Doe" \
  -F "customer_phone=+1234567890"
```

### Test 4: Using the Web UI
1. Open http://localhost:3000
2. Upload a villa interior photo
3. Watch the AI pipeline run (Vision → Matching → 3D → Quote)
4. Enter your WhatsApp number to receive the quote

---

## Production Deployment (Railway + Vercel)

### Backend (Railway)

1. Push code to your GitHub repo
2. Go to [Railway](https://railway.app) → New Project → Deploy from GitHub
3. Add a **PostgreSQL** database (Railway plugin)
4. Add a **Redis** instance (Railway plugin or Upstash)
5. Add environment variables:
   - `GEMINI_API_KEY`
   - `DATABASE_URL` (auto-filled by Railway Postgres)
   - `REDIS_URL` (auto-filled by Railway Redis)
   - `SECRET_KEY`
   - `FRONTEND_URL` (your Vercel frontend URL)
6. Railway auto-detects the Dockerfile
7. Generate domain: Settings → Networking → Generate Domain
8. Run seed data: Railway CLI → `railway run python seed_data.py`

### Frontend (Vercel)

1. Go to [Vercel](https://vercel.com) → Add New Project
2. Import your GitHub repo
3. **Root Directory:** `frontend/`
4. **Environment Variable:**
   - `NEXT_PUBLIC_API_URL` = your Railway backend URL
5. Click Deploy

---

## Key Fixes Applied

| Issue | Fix |
|-------|-----|
| `_get_cabin_image` placeholder | Now uses cached uploaded image + static file fallback |
| InMemorySessionService with 4 workers | Reduced to 1 worker (session-stable) |
| `get-quote` endpoint missing cabin data | Now looks up full cabin details from matching agent |
| WhatsApp failures crashing pipeline | Graceful fallback - quote still generated |
| Missing `frontend/Dockerfile` | Created Alpine-based Node.js Dockerfile |
| `.env.example` had Vertex AI requirements | Cleaned for AI Studio-only setup |
| No cabin seed data | Created `seed_data.py` with 8 diverse designs |
| Frontend `any` type in QuoteStep | Properly typed with interfaces |
| `next.config.js` ignoring all errors | Clean config with `standalone` output |
| No health check endpoint | Added `/health` for monitoring |

---

## Troubleshooting

### "Pipeline failed" error on upload
1. Check backend logs: `docker-compose logs api`
2. Verify Gemini API key: `curl http://localhost:8000/health`
3. Test vision endpoint directly with curl

### "No cabin matches found"
- Run seed script: `python seed_data.py`
- Check database: `docker-compose exec db psql -U postgres -d elevatorai_adk -c "SELECT * FROM cabin_designs;"`

### WhatsApp not sending
- This is optional! The quote is still generated and shown in the UI
- To enable: add WhatsApp credentials to `.env` and restart

### Database connection errors
- Ensure PostgreSQL is running: `docker-compose ps`
- Check DATABASE_URL in `.env` matches docker-compose config
