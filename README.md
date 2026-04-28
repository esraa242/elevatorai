# ElevatorAI - Google ADK Multi-Agent System

## Architecture

```
Customer Upload
      |
      v
┌─────────────────┐
│  VisionAgent    │  <- Gemini Pro Vision
│  (Style Analysis)│
└────────┬────────┘
         |
         v
┌─────────────────┐
│ MatchingAgent   │  <- Gemini Embeddings 2.0
│ (Cabin Matching)│
└────────┬────────┘
         |
         v
┌─────────────────┐
│ ModelingAgent   │  <- Procedural 3D Generation
│ (3D Model Gen)  │
└────────┬────────┘
         |
         v
┌─────────────────┐
│  SalesAgent     │  <- WhatsApp Business API
│ (Quote + Lead)  │
└─────────────────┘
```

## Agents

### 1. VisionAgent (`agents/vision_agent/`)
- **Model**: Gemini 1.5 Pro Vision
- **Purpose**: Analyzes villa interior images
- **Output**: Style taxonomy, color palette, materials, mood, spatial analysis

### 2. MatchingAgent (`agents/matching_agent/`)
- **Model**: Gemini Embeddings 2.0 (text-embedding-004)
- **Purpose**: Semantic search matching interior style to cabin designs
- **Store**: Redis Vector Database with FAISS
- **Metrics**: Style 35%, Color 25%, Material 20%, Mood 15%, Price 5%

### 3. ModelingAgent (`agents/modeling_agent/`)
- **Model**: Gemini 1.5 Pro Vision + Trimesh
- **Purpose**: Generates interactive 3D models from 2D cabin images
- **Output**: GLB/GLTF files with PBR materials

### 4. SalesAgent (`agents/sales_agent/`)
- **API**: WhatsApp Business API
- **Purpose**: Quote generation and lead conversion
- **Features**: Interactive buttons, media messages, template messages

## Quick Start

```bash
# Setup
cp .env.example .env
# Edit .env with your API keys

# Start infrastructure
docker-compose up -d db redis

# Install dependencies
pip install -e .

# Initialize database
python -c "from shared.models import init_database; init_database()"

# Run API
uvicorn workflows.orchestrator:app --reload

# Run frontend
cd frontend && npm install && npm run dev
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v2/full-pipeline` | POST | Complete workflow |
| `/api/v2/analyze` | POST | Vision analysis only |
| `/api/v2/match` | POST | Cabin matching only |
| `/api/v2/generate-3d` | POST | 3D generation only |
| `/api/v2/get-quote` | POST | Quote + WhatsApp |
| `/webhook/whatsapp` | POST | WhatsApp webhooks |

## Environment Variables

```
GOOGLE_CLOUD_PROJECT=your-project
GEMINI_API_KEY=your-key
WHATSAPP_API_TOKEN=your-token
WHATSAPP_PHONE_NUMBER_ID=your-id
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
```
