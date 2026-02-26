# Execution Modes

## Two execution modes

FIM Agent provides two execution modes that cover the full spectrum from simple queries to complex parallel tasks:

| Mode | Best for | Determinism | Flexibility | Status |
|---|---|---|---|---|
| **ReAct Agent** | Single complex queries, tool-use loops | Medium | Medium | Implemented |
| **DAG Planning** | Multi-step tasks with parallelizable subtasks | Medium | High | Implemented |

ReAct is the atomic execution unit -- a single agent that reasons, acts, and observes in a loop. DAG Planning is the orchestration layer on top -- it decomposes a goal into a dependency graph and runs independent steps concurrently, with each step powered by its own ReAct Agent.

```
DAG Planning (orchestration layer)
  |
  +-- step_1 --> ReAct Agent --> Tools     \
  |                                         |  step_1 & step_2 run in parallel
  +-- step_2 --> ReAct Agent --> Tools     /
  |
  +-- step_3 --> ReAct Agent --> Tools        (waits for step_1 & step_2)
```

## Why no traditional workflow engine

FIM Agent deliberately does **not** build a Dify-style drag-and-drop workflow editor. This is a strategic choice, not a gap.

**The core argument:**

1. **Clients already have workflows.** Government and enterprise clients' fixed processes (approval chains, report generation, audit flows) already live in their OA, ERP, and legacy systems. They don't need another workflow engine -- they need AI that can **read and operate** the systems they already have. This is exactly what the Adapter Protocol (v0.6) delivers.

2. **Dynamic DAG covers the flexible case.** For tasks that aren't pre-defined, LLM-generated DAGs adapt to each request at runtime -- no human pre-design required. This is strictly more capable than static flowcharts for exploratory and analytical work.

3. **Existing capabilities already compose into fixed pipelines.** Scheduled Jobs (v1.0) trigger a DAG agent with a fixed prompt; the DAG dynamically plans the steps; Adapters (v0.6) connect to the target systems. The combination is equivalent to a static pipeline -- but more flexible, because the LLM can adjust its plan based on the data it encounters.

```
Scheduled Job ("0 8 * * *")
  → DAG Agent: "Query finance DB, analyze anomalies, push summary to DingTalk"
  → LLM generates DAG: fetch_data ──→ analyze ──→ notify
  → Adapter connects to finance DB + DingTalk
```

No separate pipeline DSL needed. The agent IS the pipeline engine.

4. **ROI is negative.** A visual workflow editor (canvas, node types, variable passing, debug/replay, versioning) represents months of full-time work to produce a lower-quality version of what Dify already offers with 121K stars and a dedicated team.

**Summary:** ReAct handles exploration, DAG handles parallel intelligence, Scheduled Jobs + DAG + Adapters handle repeatable fixed processes, and Adapters connect to where the real workflows already live. A drag-and-drop editor adds complexity without adding capability that matters to our target users.
