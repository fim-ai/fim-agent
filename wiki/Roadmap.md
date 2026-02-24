# Roadmap

> Goal: Build a complete **Dify alternative** -- from agent runtime to visual workflow builder.
> Principles: **Provider-agnostic** (no vendor lock-in), **minimal-abstraction**, **protocol-first**.

---

### v0.2 -- Core Enhancements

- [x] **Native Function Calling**: Support OpenAI-style `tool_choice` / `parallel_tool_calls` alongside the ReAct JSON mode
- [x] **Streaming Agent Output**: ~~Yield intermediate reasoning and tool results as they happen via `AsyncIterator`~~ -- Shipped in v0.1: real-time SSE streaming with async queue bridge and `on_iteration` callbacks for both ReAct and DAG modes
- [x] **Conversation Memory**: Short-term message window + conversation summary for multi-turn agent sessions
- [x] **Retry & Rate Limiting**: Configurable retry with exponential backoff + token-bucket rate limiter respecting provider quotas
- [x] **Token Usage Tracking**: Count and aggregate prompt / completion tokens across all LLM calls; expose per-task cost summary
- [x] **Multi-Model Support**: ModelRegistry to configure multiple LLMs per project (general / fast / vision / compact), switch per step

### v0.3 -- Rich Tool Ecosystem

- [ ] **Built-in Tools**: Calculator, file ops (read / write / list / edit / delete), web search, browser automation (Playwright), image understanding
- [ ] **MCP Integration**: Model Context Protocol client for dynamic tool discovery and invocation via standardized servers
- [ ] **Tool Auto-Discovery**: Convention-based tool loading (`get_{name}_tool()`) so new tools register automatically without manual wiring
- [ ] **Tool Categories & Permissions**: Group tools by category, enable/disable per agent

### v0.4 -- RAG & Knowledge

- [ ] **LanceDB Vector Store**: Embedded vector store as the default retriever backend -- zero external services, consistent with the minimal-dependency philosophy
- [ ] **Document Loaders**: File parsers for PDF, Markdown, HTML, DOCX, CSV, and PPTX
- [ ] **Chunking Strategies**: Fixed-size, recursive, and semantic chunking out of the box
- [ ] **Hybrid Retrieval**: Combine dense vector search with BM25 sparse retrieval via LanceDB full-text search
- [ ] **Knowledge Base Management**: Create, upload, search, and manage multiple knowledge bases per user / agent
- [ ] **Multi-Backend Vector Stores** _(stretch)_: Abstract `BaseVectorStore` interface + optional FAISS / Chroma / Milvus adapters, driven by real user demand

### v0.5 -- Agent Builder

- [ ] **Agent Builder**: Visual UI to create custom agents -- set instructions, pick model, attach knowledge bases, configure tools and skills
- [ ] **Agent Lifecycle**: Draft → Published → Archived status flow with version tracking
- [ ] **Skill System**: Reusable prompt-based skills that agents can compose; agents select skills at creation time
- [ ] **Agent Templates**: Starter templates for common use cases (customer support, data analysis, code assistant, research, etc.)
- [ ] **Suggested Prompts**: Per-agent example prompts to help users get started quickly

### v0.6 -- Multi-Agent & Nested Execution

- [ ] **Nested Agent / Delegation**: Agents can spawn sub-agents for recursive task decomposition; child results bubble up to parent
- [ ] **Agent Roles**: Define specialized agents (researcher, coder, reviewer) within a single DAG plan
- [ ] **Inter-Agent Messaging**: Shared context bus for agents to exchange intermediate results
- [ ] **Human-in-the-Loop**: Approval gates and intervention points in DAG steps for high-stakes decisions
- [ ] **Pre/Post Step Hooks**: Inject user prompts before or after DAG steps for fine-grained human intervention
- [ ] **Immutable Plans + Selective Skip**: Plans are frozen after generation; individual steps can be skipped without re-planning

### v0.7 -- Production Platform

- [ ] **User Management**: Multi-user with JWT auth, role-based permissions, workspace isolation
- [ ] **Persistent Storage**: SQLAlchemy ORM with PostgreSQL / SQLite for tasks, agents, execution history, and model configs
- [ ] **Task Workspace Isolation**: Per-task working directory with isolated file space; prevent cross-task data leakage
- [ ] **File Management**: Upload, download, preview, and associate files with tasks and agents; input/output directories
- [ ] **WebSocket Communication**: Real-time bi-directional streaming replacing SSE for richer interaction
- [ ] **Task Pause / Resume**: Persist and resume long-running agent tasks across server restarts (requires persistent storage)
- [ ] **DAG Visualization**: Interactive @xyflow/react graph rendering of execution plans with live status updates
- [ ] **Graph Node System**: Typed execution nodes (Start / End / Agent / Tool / Condition) powering both DAG and workflow modes

### v0.8 -- Observability & Operations

- [ ] **Langfuse / OpenTelemetry Traces**: Structured tracing for every LLM call, tool execution, and DAG step; pluggable backend (Langfuse, Jaeger, OTLP)
- [ ] **Cost Dashboard**: Token usage aggregation by task / agent / user / model; historical cost trends (builds on v0.2 token tracking)
- [ ] **Monitoring Dashboard**: Task history, execution metrics, success/failure rates, latency percentiles
- [ ] **Execution Replay**: Historical trace replay for debugging and auditing

### v0.9 -- Workflow Engine (Dify Parity)

- [ ] **Visual Workflow Editor**: Drag-and-drop node-based workflow builder (like Dify / n8n)
- [ ] **Workflow Templates**: Pre-built workflow templates for common patterns (chatbot, RAG pipeline, data processing)
- [ ] **Conditional Branching**: If/else nodes, switch nodes, loop nodes in visual workflows
- [ ] **Variable System**: Global and step-scoped variables with type validation
- [ ] **Trigger System**: HTTP webhook, scheduled cron, and event-based workflow triggers
- [ ] **Workflow Versioning**: Version control for published workflows with rollback support

### v1.0 -- Ecosystem & Enterprise

- [ ] **Plugin System**: Pip-installable tool / retriever / agent packages with auto-registration
- [ ] **Full Web UI**: Next.js dashboard with agent marketplace, task management, knowledge base UI, and workflow editor
- [ ] **Docker Deployment**: Production-ready Docker Compose with PostgreSQL, Nginx reverse proxy, and worker processes
- [ ] **REST & SSE API**: Complete HTTP API for programmatic access to all platform features
- [ ] **Benchmarks**: Standardized evaluation suite against SWE-bench, HotpotQA, and custom enterprise tasks
- [ ] **i18n**: Multi-language support for UI and agent prompts (Chinese, English, Japanese)

Contributions and ideas are welcome -- open an issue or submit a PR on [GitHub](https://github.com/fim-ai/fim-agent).
