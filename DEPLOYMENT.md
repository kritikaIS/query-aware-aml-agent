# Deployment Guide

## Production Build

### Backend

The backend runs directly from source — there is no compile step.

```bash
# 1. Install dependencies (production)
pip install -r requirements.txt

# 2. Set environment variables (see below)
cp .env.example .env
# Edit .env

# 3. Start the server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 1
```

> Note: The backend runs a synchronous, CPU-bound pipeline per request. Use `--workers 1` unless you have tested concurrent isolation. Multiple workers may lead to shared-state issues with the in-memory data loading.

### Frontend

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Set environment variables
cp .env.example .env
# Edit .env — set VITE_API_BASE_URL to your backend URL

# 3. Build
npm run build
# Output written to: frontend/dist/

# 4. Preview locally (optional)
npm run preview
```

The `frontend/dist/` directory contains static files that can be served by any HTTP server (nginx, Caddy, etc.).

---

## Environment Variables

### Backend

Copy `.env.example` to `.env` and set the following:

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | No | _(empty)_ | Set to enable LLM-based planning and explanation. Leave blank for deterministic mode. |
| `MODEL_NAME` | No | `claude-sonnet-4-20250514` | Claude model identifier. Only used when `ANTHROPIC_API_KEY` is set. |
| `STUB_MODE` | No | `true` | Set `false` for production. `true` uses hard-coded stub tools with no real data processing. |
| `DATA_DIR` | No | `data/synthetic` | Relative path (from project root) to the directory containing `transactions.csv` and `customers.csv`. |
| `LOG_LEVEL` | No | `INFO` | Python logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |

**Minimal production `.env`:**

```dotenv
ANTHROPIC_API_KEY=sk-ant-...
MODEL_NAME=claude-sonnet-4-20250514
STUB_MODE=false
DATA_DIR=data/synthetic
LOG_LEVEL=INFO
```

### Frontend

Copy `frontend/.env.example` to `frontend/.env`:

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_API_BASE_URL` | Yes | `http://localhost:8000` | Full URL of the backend API, including protocol and port. No trailing slash. |
| `VITE_APP_TITLE` | No | `AML Agent · Suspicious Activity Detection` | Browser tab title. |
| `VITE_ENV` | No | `development` | Label shown in the top bar env badge. |

**Production frontend `.env`:**

```dotenv
VITE_API_BASE_URL=https://your-backend-domain.com
VITE_APP_TITLE=AML Agent · Suspicious Activity Detection
VITE_ENV=production
```

> `VITE_` variables are embedded at build time. You must rebuild the frontend if you change them.

---

## Running with Docker

No `Dockerfile` is included in the current codebase. The following instructions describe a manual approach.

### Backend Container (example)

```dockerfile
# Dockerfile.backend (not included — create manually)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -f Dockerfile.backend -t aml-backend .
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e STUB_MODE=false \
  -e DATA_DIR=data/synthetic \
  -v $(pwd)/data:/app/data \
  aml-backend
```

### Frontend Container (example)

```dockerfile
# Dockerfile.frontend (not included — create manually)
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
ARG VITE_API_BASE_URL=http://localhost:8000
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
```

```bash
docker build -f Dockerfile.frontend \
  --build-arg VITE_API_BASE_URL=https://your-backend.com \
  -t aml-frontend .
docker run -p 80:80 aml-frontend
```

---

## Reverse Proxy Recommendations

When deploying both backend and frontend behind a reverse proxy (nginx, Caddy, etc.):

### nginx Example

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    # Serve the React SPA
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to FastAPI
    location /query {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;   # backend can take up to 90s
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

> Set `proxy_read_timeout` to at least 120 seconds. The backend runs the full ML pipeline synchronously, which can take up to 90 seconds on large datasets.

### CORS

CORS is configured in `src/config/api_config.yaml`. For production, replace the wildcard with your actual frontend origin:

```yaml
cors_origins:
  - "https://your-domain.com"
```

---

## Bundle Sizes (Production Build)

| Chunk | Gzipped Size | Loaded when |
|---|---|---|
| `index` (initial app) | ~94 kB | Always |
| `motion` (Framer Motion) | ~38 kB | Always (split chunk) |
| `json-view` (react-json-view) | ~33 kB | JSON Inspector opens |
| `charts-recharts` | ~95 kB | Results Dashboard loads |
| `charts-plotly` | ~1,358 kB | Results Dashboard loads |
| `NetworkCanvas` (D3) | ~3 kB | Network graph renders |

Plotly.js is large (~1.4 MB gzipped). It is lazy-loaded and only fetched when the Results Dashboard renders charts. On slow connections, charts may show a loading spinner for 1–2 seconds.

---

## Deployment Checklist

- [ ] `ANTHROPIC_API_KEY` set (or `STUB_MODE=true` explicitly set for demo)
- [ ] `STUB_MODE=false` for production
- [ ] `DATA_DIR` points to a directory containing `transactions.csv` and `customers.csv`
- [ ] `VITE_API_BASE_URL` set to the correct backend URL before building frontend
- [ ] Frontend rebuilt after changing any `VITE_` variable
- [ ] `cors_origins` in `api_config.yaml` updated to production frontend origin
- [ ] Reverse proxy `proxy_read_timeout` set to ≥120s
- [ ] Backend `--workers 1` unless concurrent isolation is tested
- [ ] `LOG_LEVEL=WARNING` or `ERROR` in production to reduce log noise
- [ ] HTTPS configured (Anthropic API key must not transit unencrypted)
