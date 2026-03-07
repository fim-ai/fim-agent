# Environment Variables

All configuration is done via `.env`. Copy `example.env` and fill in your values:

```bash
cp example.env .env
```

---

## LLM

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_API_KEY` | **Yes** | — | API key for the LLM provider |
| `LLM_BASE_URL` | No | `https://api.openai.com/v1` | Base URL of any OpenAI-compatible API |
| `LLM_MODEL` | No | `gpt-4o` | Main model — used for planning, analysis, and ReAct agent |
| `FAST_LLM_MODEL` | No | *(falls back to `LLM_MODEL`)* | Fast model — used for DAG step execution (cheaper, faster) |
| `LLM_TEMPERATURE` | No | `0.7` | Default sampling temperature |
| `LLM_CONTEXT_SIZE` | No | `128000` | Context window size for the main LLM |
| `LLM_MAX_OUTPUT_TOKENS` | No | `64000` | Max output tokens per call for the main LLM |
| `FAST_LLM_CONTEXT_SIZE` | No | *(falls back to `LLM_CONTEXT_SIZE`)* | Context window size for the fast LLM |
| `FAST_LLM_MAX_OUTPUT_TOKENS` | No | *(falls back to `LLM_MAX_OUTPUT_TOKENS`)* | Max output tokens per call for the fast LLM |

> DB model config (Settings → Models) takes priority over these ENV vars when set.

---

## Agent Execution

| Variable | Required | Default | Description |
|---|---|---|---|
| `REACT_MAX_ITERATIONS` | No | `20` | Max tool-call iterations per ReAct request |
| `MAX_CONCURRENCY` | No | `5` | Max parallel steps in DAG executor |
| `DAG_STEP_MAX_ITERATIONS` | No | `15` | Max tool-call iterations within each DAG step |
| `DAG_MAX_REPLAN_ROUNDS` | No | `3` | Max autonomous re-plan attempts when goal is not achieved |
| `DAG_REPLAN_STOP_CONFIDENCE` | No | `0.8` | Stop retrying when agent confidence that goal is unachievable exceeds this threshold (`0.0` = never stop early, `1.0` = stop on any failure) |

---

## Web Tools

| Variable | Required | Default | Description |
|---|---|---|---|
| `JINA_API_KEY` | No | — | Jina API key — also used for embedding and reranker; get yours at [jina.ai](https://jina.ai/) |
| `TAVILY_API_KEY` | No | — | Tavily Search API key (auto-selected if set and `WEB_SEARCH_PROVIDER` is unset) |
| `BRAVE_API_KEY` | No | — | Brave Search API key (auto-selected if set and `WEB_SEARCH_PROVIDER` is unset) |
| `WEB_SEARCH_PROVIDER` | No | `jina` | Search provider selector: `jina` / `tavily` / `brave` |
| `WEB_FETCH_PROVIDER` | No | `jina` (if key set, else `httpx`) | Fetch provider: `jina` / `httpx` |

---

## RAG & Knowledge Base

| Variable | Required | Default | Description |
|---|---|---|---|
| `EMBEDDING_MODEL` | No | `jina-embeddings-v3` | Embedding model identifier |
| `EMBEDDING_DIMENSION` | No | `1024` | Embedding vector dimension |
| `EMBEDDING_API_KEY` | No | *(uses `JINA_API_KEY`)* | Override API key for a different embedding provider |
| `EMBEDDING_BASE_URL` | No | `https://api.jina.ai/v1` | Override base URL for a different embedding provider |
| `RETRIEVAL_MODE` | No | `grounding` | `grounding` (full pipeline with citations/conflicts/confidence) or `simple` (basic RAG) |
| `RERANKER_MODEL` | No | `jina-reranker-v2-base-multilingual` | Reranker model identifier |
| `RERANKER_PROVIDER` | No | `jina` | Reranker provider: `jina` / `cohere` / `openai` |
| `COHERE_API_KEY` | No | — | Cohere API key (auto-selects Cohere reranker when set) |
| `COHERE_RERANKER_MODEL` | No | `rerank-multilingual-v3.0` | Cohere reranker model |
| `VECTOR_STORE_DIR` | No | `./data/vector_store` | Directory for LanceDB vector store data |

---

## Code Execution

| Variable | Required | Default | Description |
|---|---|---|---|
| `CODE_EXEC_BACKEND` | No | `local` | `local` (direct host execution) or `docker` (isolated containers) |
| `DOCKER_PYTHON_IMAGE` | No | `python:3.11-slim` | Docker image for Python execution |
| `DOCKER_NODE_IMAGE` | No | `node:20-slim` | Docker image for Node.js execution |
| `DOCKER_SHELL_IMAGE` | No | `python:3.11-slim` | Docker image for shell execution |
| `DOCKER_MEMORY` | No | *(Docker default)* | RAM cap per container (e.g. `256m`, `512m`, `1g`) |
| `DOCKER_CPUS` | No | *(Docker default)* | CPU quota per container (e.g. `0.5`, `1.0`) |
| `SANDBOX_TIMEOUT` | No | `120` | Default execution timeout in seconds |

> **Security**: `local` mode runs AI-generated code directly on the host. For internet-facing or multi-user deployments, always set `CODE_EXEC_BACKEND=docker`.

---

## Tool Artifacts

Size limits for files produced by tool execution (code execution, template rendering, image generation).

| Variable | Required | Default | Description |
|---|---|---|---|
| `MAX_ARTIFACT_SIZE` | No | `10485760` (10 MB) | Max single artifact file size in bytes |
| `MAX_ARTIFACTS_TOTAL` | No | `52428800` (50 MB) | Max total artifact size per session in bytes |

---

## Image Generation

| Variable | Required | Default | Description |
|---|---|---|---|
| `IMAGE_GEN_PROVIDER` | No | — | Currently only `google` is supported |
| `IMAGE_GEN_API_KEY` | No | — | Google AI Studio API key |
| `IMAGE_GEN_MODEL` | No | `gemini-3.1-flash-image-preview` | Image generation model |
| `IMAGE_GEN_BASE_URL` | No | `https://generativelanguage.googleapis.com/v1beta` | Google API base URL |

---

## Email (SMTP)

Auto-registers the `email_send` built-in tool when `SMTP_HOST`, `SMTP_USER`, and `SMTP_PASS` are all set.

| Variable | Required | Default | Description |
|---|---|---|---|
| `SMTP_HOST` | Cond. | — | SMTP server hostname |
| `SMTP_PORT` | No | `465` | SMTP port |
| `SMTP_SSL` | No | `ssl` | TLS mode: `ssl` (port 465) / `tls` (STARTTLS, port 587) / `""` (plain) |
| `SMTP_USER` | Cond. | — | SMTP login username |
| `SMTP_PASS` | Cond. | — | SMTP login password |
| `SMTP_FROM` | No | *(uses `SMTP_USER`)* | Sender address shown in From header |
| `SMTP_FROM_NAME` | No | — | Display name shown in From header |
| `SMTP_ALLOWED_DOMAINS` | No | — | Comma-separated domain allowlist (e.g. `example.com,corp.io`); blocks recipients outside listed domains |
| `SMTP_ALLOWED_ADDRESSES` | No | — | Comma-separated exact-address allowlist; combined with `SMTP_ALLOWED_DOMAINS`; leave both unset to allow any recipient (not recommended for shared mailboxes) |

---

## Connectors

| Variable | Required | Default | Description |
|---|---|---|---|
| `CONNECTOR_RESPONSE_MAX_CHARS` | No | `50000` | Max characters for non-array JSON / plain-text connector responses |
| `CONNECTOR_RESPONSE_MAX_ITEMS` | No | `10` | Max array items to keep when connector response is a JSON array |

---

## Platform

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./data/fim_agent.db` | Database connection string (SQLite default; PostgreSQL via asyncpg also supported) |
| `JWT_SECRET_KEY` | No | `CHANGE_ME` | Secret key for JWT token signing. Placeholder value `CHANGE_ME` (or any legacy default) triggers auto-generation of a secure 256-bit random key on first start, which is written back to `.env`. Set explicitly in production to keep tokens valid across restarts and replicas. |
| `CORS_ORIGINS` | No | — | Comma-separated list of extra allowed CORS origins beyond the default localhost entries. Required when the frontend runs on a non-localhost domain (e.g. `https://app.example.com`). |
| `UPLOADS_DIR` | No | `./uploads` | Directory for uploaded files |
| `MCP_SERVERS` | No | — | JSON array of MCP server configs (requires `uv sync --extra mcp`) |
| `ALLOW_STDIO_MCP` | No | `true` | Allow stdio MCP servers. Set `false` for public/SaaS deployments |
| `LOG_LEVEL` | No | `INFO` | Logging level: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |

---

## OAuth (Optional)

| Variable | Required | Default | Description |
|---|---|---|---|
| `GITHUB_CLIENT_ID` | No | — | GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | No | — | GitHub OAuth App client secret |
| `GOOGLE_CLIENT_ID` | No | — | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No | — | Google OAuth client secret |
| `FRONTEND_URL` | No | `http://localhost:3000` | Frontend URL for OAuth callback redirect |
