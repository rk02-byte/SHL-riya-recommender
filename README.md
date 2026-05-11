# SHL Conversational Assessment Recommender

AI-powered agent for recommending SHL assessments through natural dialogue.

## Features

- **Conversational AI Agent**: Natural language interface for assessment recommendations
- **Semantic Search**: FAISS-powered vector search for relevant assessments
- **4 Behaviors**: Clarify, Recommend, Refine, Compare
- **Guardrails**: Catalog-only responses, prompt injection protection
- **FastAPI**: RESTful API with health and chat endpoints
- **Schema Compliance**: Exact JSON response format for evaluation

## Quick Start

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Build assets:
```bash
python build_assets.py
```

3. Run server:
```bash
python main.py
```

4. Test endpoints:
```bash
# Health check
curl http://localhost:8000/health

# Chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Java developer assessment"}]}'
```

## Deployment to Render.com

### Prerequisites
- Render.com account
- GitHub repository with this code
- Anthropic API key (set as environment variable in Render)

### Deployment Steps

1. **Push to GitHub**:
```bash
git add .
git commit -m "Deploy SHL recommender"
git push origin main
```

2. **Create Render Service**:
   - Go to Render.com dashboard
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Select "Python" as runtime
   - Use existing `render.yaml` configuration

3. **Set Environment Variables**:
   In Render dashboard, add:
   - `ANTHROPIC_API_KEY`: Your Anthropic API key
   - `PYTHON_VERSION`: `3.12.0`

4. **Deploy**:
   - Render will automatically build and deploy
   - FAISS index is built during build step (not runtime)
   - Health check ensures service is ready

### Build Process

The `build_assets.py` script runs during deployment:
1. Scrapes SHL catalog (if not present)
2. Generates FAISS index (if not present) 
3. Verifies all required files
4. Optimizes for production deployment

### Environment Variables

| Variable | Required | Description |
|-----------|-----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic Claude API key |
| `PYTHON_VERSION` | No | Python version (default: 3.12.0) |

## API Endpoints

### GET /health
Returns service health status.

**Response:**
```json
{"status": "ok"}
```

### POST /chat
Processes conversational requests for assessment recommendations.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Hiring a Java developer"},
    {"role": "assistant", "content": "What seniority level?"},
    {"role": "user", "content": "Mid-level, 4 years experience"}
  ]
}
```

**Response:**
```json
{
  "reply": "Based on your needs, here are 3 assessments...",
  "recommendations": [
    {
      "name": "Java 8 Programming Test",
      "url": "https://www.shl.com/...",
      "test_type": "S"
    }
  ],
  "end_of_conversation": false
}
```

## Architecture

- **Catalog Scraping**: BeautifulSoup-based SHL catalog extraction
- **Vector Store**: FAISS with sentence-transformers embeddings
- **Agent Logic**: 4-phase conversation management with guardrails
- **API**: FastAPI with strict schema validation
- **Deployment**: Docker container optimized for Render.com

## Performance

- **Cold Start**: < 2 minutes (requirement)
- **Response Time**: < 30 seconds per request
- **Memory**: 512MB (Render free tier)
- **Uptime**: Always-on with health monitoring

## Testing

Run comprehensive test suite:
```bash
python test_agent.py
```

Expected: 100% pass rate across all behaviors and guardrails.

## Files Structure

```
├── main.py              # FastAPI application
├── agent.py             # Conversational AI agent
├── scraper.py           # SHL catalog scraper
├── embeddings.py        # Vector embeddings generator
├── vector_store.py      # FAISS vector store
├── test_agent.py        # Comprehensive test suite
├── build_assets.py      # Build script for deployment
├── render.yaml          # Render.com deployment config
├── Dockerfile           # Container configuration
├── requirements.txt     # Python dependencies
├── catalog.json         # SHL assessment catalog
├── faiss_index.bin     # Pre-built vector index
└── README.md           # This file
```

## License

MIT License - see LICENSE file for details.
