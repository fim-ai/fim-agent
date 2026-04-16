# CC Insights Integration — Manual Test Guide

> Agent Infrastructure Improvements (Phase 0 ~ Phase 3)
> Phase 0-2 implemented 2026-04-01
> Phase 3 implemented 2026-04-10

---

## Phase 0: Zero-Risk Quick Wins

### I.1 Compact Prompt 9-Section Format

**File**: `src/fim_one/core/memory/context_guard.py`

**How to test**:
1. Start dev server: `./start.sh api`
2. Open a chat conversation, send a long multi-step query (e.g., "help me analyze a complex business scenario" with follow-ups)
3. Keep chatting until the conversation is long enough to trigger context compaction (you'll see a `compact` SSE event in the stream)
4. Check the server logs — the compacted summary should use the 9-section format:
   - `## 1. Primary Request`
   - `## 2. Key Concepts`
   - `## 3. Files and Code`
   - etc.
5. The `<analysis>` tags should NOT appear in the final compacted content (they're stripped in post-processing)

**What to look for**:
- Compacted summaries preserve the original request and errors
- No `<analysis>` blocks leak into conversation history
- Agent continues working correctly after compaction

---

### I.2 Empty Result Protection

**File**: `src/fim_one/core/agent/react.py`

**How to test**:
1. Create a connector or tool that returns empty/no content (e.g., a webhook that returns 204)
2. Ask the agent to use it
3. Check the conversation — the tool result should show:
   `"Tool 'xxx' completed successfully with no output. Do not retry with same arguments."`
4. The agent should NOT retry the same tool call

**What to look for**:
- No infinite retry loops on empty tool results
- Agent moves on to the next step or finalizes

---

### I.3 Anti-loop Prompt + Cycle Detection

**File**: `src/fim_one/core/agent/react.py`

**How to test**:
1. Ask the agent a question where it might loop (e.g., "search for X" where X doesn't exist, causing repeated searches)
2. The agent should be caught after 2 identical consecutive tool calls (was 3 before)
3. Check that the agent diagnoses the failure rather than blindly retrying

**What to look for**:
- Agent loops are caught faster (2 iterations instead of 3)
- Agent provides diagnostic reasoning when an approach fails

---

### I.4 Domain Classifier Parallelization

**File**: `src/fim_one/web/api/chat.py`

**How to test**:
1. Send a chat message and measure the time from request to first SSE event
2. Compare with previous behavior — should be ~300-800ms faster
3. Domain classification result should still be correct (check `step` events for domain hint)

**What to look for**:
- No change in functionality
- Faster first response
- Domain hint still appears correctly in logs

---

### I.5 Pre-flight DB Parallelization

**File**: `src/fim_one/web/api/chat.py`

**How to test**:
1. Same as I.4 — send a chat message
2. The LLM config resolution (model, fast model, context budget, vision support) should all resolve concurrently
3. Check that the correct model is selected and vision toggle works

**What to look for**:
- Correct model selection
- Vision mode works when enabled on the model
- Faster startup

---

### I.6 `end` Event Early Send

**File**: `src/fim_one/web/api/chat.py`

**How to test**:
1. Send a chat message and observe the SSE event stream (browser DevTools > Network > EventStream)
2. The `end` event should arrive immediately after `done` — no `post_processing`, `suggestions`, or `title` events between them
3. Refresh the conversation list after ~2-3 seconds — the auto-generated title should appear (written by background task)
4. Check that suggestions are persisted to the assistant message metadata (visible via message API)

**What to look for**:
- `end` arrives immediately after `done` (no delay)
- No `post_processing`, `suggestions`, or `title` SSE events
- Title appears in conversation list after refresh
- **Known trade-off**: title/suggestions no longer update in real-time; user must refresh

---

## Phase 1: Context Anti-Bloat

### I.7 MicroCompact — Old Tool Result Cleanup

**Files**: `src/fim_one/core/memory/microcompact.py` (new), `src/fim_one/core/agent/react.py`

**Automated tests**: `uv run pytest tests/test_microcompact.py -v` (21 tests)

**How to test manually**:
1. Start a conversation that triggers 8+ tool calls (e.g., "analyze this data" with a connector that returns results)
2. After 8+ tool calls, check the conversation messages (via API or logs)
3. The first 2 tool results (oldest) should show `"[result cleared -- older than 6 most recent tool results]"`
4. The 6 most recent tool results should be intact

**What to look for**:
- Old tool results are cleared, recent ones preserved
- Agent can still reference recent tool results
- Context window usage decreases as conversation grows
- No crash or error when all tool results are cleared

---

### I.8 Tool Result Aggregate Budget

**File**: `src/fim_one/core/agent/react.py`

**Env var**: `REACT_TOOL_RESULT_BUDGET` (default: 40000 tokens)

**How to test manually**:
1. Set a very low budget for testing: `REACT_TOOL_RESULT_BUDGET=100`
2. Start the server and send a query that triggers tool calls
3. After the first 1-2 tool results, subsequent results should be truncated with a message like:
   `[Truncated: tool result exceeded aggregate budget (xxx/100 tokens used)]`
4. Reset to default (40000) and verify normal operation — most conversations should not hit the budget

**What to look for**:
- Tool results are truncated when budget is exceeded
- Truncation message is visible in the tool result
- Agent can still function with truncated results
- Default budget (40K) is generous enough for normal use

---

### I.9 Reactive Compact — Context Overflow Recovery

**Files**: `src/fim_one/core/model/retry.py` (new `is_context_overflow()`), `src/fim_one/core/agent/react.py`

**How to test manually**:
1. This is hard to trigger naturally — requires a very long conversation that exceeds the model's context window
2. **Simulation approach**: Use a model with a small context window (e.g., set up a model with 4K context limit) and send a conversation that exceeds it
3. When the LLM returns HTTP 400 with "context_length" error, the agent should:
   - Log a warning: "Context overflow detected, forcing compact to 50%"
   - Compact the conversation to 50% of budget
   - Retry the LLM call once
4. If the retry also fails, the error should propagate normally

**What to look for**:
- Agent recovers from context overflow instead of crashing
- Recovery only happens once per turn (no infinite recovery loops)
- Warning is logged when recovery triggers
- If recovery fails, error is propagated cleanly

**is_context_overflow detection patterns** (covered by unit tests):
- HTTP 400 + "context_length_exceeded"
- HTTP 400 + "maximum context length"
- HTTP 413 + "request too large"
- "token" + "limit" / "exceed" in error message
- Anthropic: "context window" pattern

---

## Phase 2: Speed Improvements

### I.10 Keyword Tool Selection

**File**: `src/fim_one/core/agent/react.py`

**How to test**:
1. Start server with `DEBUG` logging and register 12+ tools on an agent
2. Send a query that obviously matches a specific tool (e.g., "search the web for Python tutorials" when `web_search` is registered)
3. Check logs for: `Tool selection (keyword shortcut): 1/N tools selected: ['web_search'] — LLM call skipped`
4. Send an ambiguous query (e.g., "help me") — should fall back to LLM selection

**What to look for**:
- Obvious matches skip the LLM call (faster first response)
- Ambiguous queries still use LLM selection (no wrong tool chosen)
- Pinned tools (`read_skill`, etc.) are always included regardless of keyword match

---

### I.11 Connection Pooling

**File**: `src/fim_one/core/model/openai_compatible.py`

**Automated tests**: `uv run pytest tests/test_model.py::TestSharedHttpClient -v` (7 tests)

**How to test manually**:
1. Start `./start.sh api` and send several chat messages
2. All LLM calls should work identically — pooling is transparent
3. Check that shutdown is clean (no "unclosed client" warnings in logs)

**What to look for**:
- No behavioral change — just faster connections
- Clean shutdown without warnings
- Pool settings: 100 max connections, 20 keepalive, 30s expiry

---

### I.12 Completion Check Lightweighting

**File**: `src/fim_one/core/agent/react.py`

**Env var**: `REACT_COMPLETION_CHECK_SKIP_CHARS` (default: 800)

**How to test manually**:
1. Ask the agent a complex question that triggers tool calls and produces a long answer (>800 chars)
2. Check logs for: `Skipped completion check — answer length (N chars) exceeds threshold`
3. Ask a simple question that produces a short answer (<800 chars) — completion check should still run
4. To force the skip, set `REACT_COMPLETION_CHECK_SKIP_CHARS=10`

**What to look for**:
- Long answers skip the check (faster finalization)
- Short answers still get verified
- Answer quality is not degraded

---

### I.13 Model Fallback

**Files**: `src/fim_one/core/model/fallback.py` (new), `src/fim_one/web/api/chat.py`

**Automated tests**: `uv run pytest tests/test_fallback.py -v` (34 tests)

**How to test manually**:
1. Configure a primary model pointing to a non-existent endpoint (to simulate downtime)
2. Ensure a fast model is configured
3. Send a chat message — should fall back to fast model with a warning in logs:
   `Primary model unavailable, falling back to {fast_model}`
4. Configure an invalid API key on primary — should NOT fall back (auth errors are not availability errors)

**What to look for**:
- Availability errors (429/503/529/connection) trigger fallback
- Auth errors (401/403) do NOT trigger fallback
- Context overflow (400 + context_length) does NOT trigger fallback (handled by I.9)
- When both models fail, error propagates normally

**Fallback trigger conditions** (covered by unit tests):
- HTTP 429 (rate limited)
- HTTP 503 (service unavailable)
- HTTP 529 (overloaded)
- Connection errors / timeouts

---

## Phase 3: Production Hardening (Runtime Invariants)

> Goal: close the gap between demo-quality agent loop and production runtime
> by enforcing CC's four runtime invariants (trajectory topology, cache prefix,
> capability surface, continuity). Phase 3 is four bug-fixes and observability
> upgrades, all on completely independent files.

### I.14 Conversation Recovery — Dangling tool_use Repair

**Files**: `src/fim_one/core/memory/db.py`, `tests/test_db_memory_recovery.py` (new, 9 tests)

**What it does**: `DbMemory.get_messages()` now scans the loaded message list for
`assistant` messages containing `tool_calls` whose ids have no matching downstream
`tool_result`. For each dangling id, a synthetic `tool_result` with content
`"[interrupted: tool execution did not complete]"` is inserted immediately after
the assistant message. Repair is **read-path only** — the DB log is not mutated.
A WARNING is logged with the `conversation_id` and synthetic count.

**Why**: invariant #1 (trajectory topology) — Anthropic/OpenAI reject message
lists where a `tool_use` has no matching `tool_result` with a 400 error. Ctrl+C,
SSE disconnect, or a crash mid-tool-execution can produce these dangling blocks.
Without the repair, the next turn explodes with an opaque API error.

**Also fixed as a side effect**: the empty-assistant filter in `db.py` was
dropping assistant rows with empty text content. This silently wiped out
native-FC intermediates whose only content is `tool_calls`. The filter now
requires BOTH empty content AND no `tool_calls`.

**How to test manually**:
1. **Automated first**: `uv run pytest tests/test_db_memory_recovery.py -v` — all 9 should pass.
2. **Simulated interruption**: start a long-running connector / tool (e.g., `web_search` with a slow network path, or a database `query` against a big table). Once the tool is "executing" (SSE step event shows it started), kill the request — close the tab, hit the browser Stop button, or disconnect the network. This mid-tool abort is the scenario that creates a dangling `tool_use`.
3. **Verify repair on resume**: open a new conversation reply on the same thread. Check the server logs for a line like:
   ```
   WARNING: Repaired N dangling tool_use(s) in conversation <conv_id>
   ```
4. **Verify no crash**: the new reply should proceed normally without an HTTP 400 from the LLM API. Before this fix, you would get an error like `"tool_use ids were found without tool_result blocks"`.

**What to look for**:
- Warning log fires with the correct conversation id
- Next turn proceeds normally (no 400)
- Real tool results are NOT duplicated — only genuinely missing ids get synthetic ones
- A well-formed conversation (no interruption) passes through with NO repair log

**Known caveat (read this first!)**: the current `chat.py` write path only persists
the FINAL assistant answer, not intermediate tool-calling assistant turns. This
means in production as of 2026-04-10, the repair code is **armed but dormant** —
it will fire the moment intermediate persistence is enabled (follow-up work), but
not before. You can still exercise it via the unit tests (`test_db_memory_recovery.py`)
or by manually crafting a test row directly in the SQLite DB. For ops: watch for
the WARNING log once intermediate persistence ships.

---

### I.15 Structured Compact Work Card

**Files**: `src/fim_one/core/memory/work_card.py` (new), `src/fim_one/core/memory/context_guard.py`, `tests/test_work_card.py` (new, 20 tests), `tests/test_context_guard.py` (+3 tests)

**What it does**: Phase 0 (I.1) shipped the 9-section compact prompt, producing
structured markdown. I.15 takes the next step: the markdown is now parsed into a
typed `WorkCard` dataclass with 9 fields (`primary_request`, `key_concepts`,
`files_and_code`, `errors`, `problem_solving`, `user_messages`, `pending_tasks`,
`current_work`, `next_step`). When a second compact runs in the same session, the
new card is **merged** into the previous one rather than overwriting it:
- String fields prefer the newer non-empty value
- List fields do order-preserving union dedup (capped at 10 items; errors capped at 5)
- The final compact text is still the same markdown shape, so downstream code is unchanged

**Why**: invariant #4 (continuity must not rely on transcript alone) — without
merging, each compact re-summarizes from scratch and can forget pending tasks or
error history recorded in the previous compact. The work card preserves those
structured fields across multiple compaction rounds.

**How to test manually**:
1. **Automated first**: `uv run pytest tests/test_work_card.py tests/test_context_guard.py -v` — 37 should pass.
2. **Trigger two compacts**: open a fresh chat, ask the agent to do a multi-step task that produces errors mid-way (e.g., "query the sales DB for last quarter, chart the top 10 customers, then fetch their contact info from CRM" — with at least one step that genuinely fails). Keep the conversation going until you see a `compact` SSE event in the stream.
3. **Compact #1 happens**: check the server logs or the message store — the compacted summary should contain a section like `## 4. Errors` listing the failure.
4. **Keep chatting** until a second compact triggers (send more messages until the budget hits again).
5. **Verify merge**: the SECOND compact's markdown should still contain the original error(s) from compact #1 under `## 4. Errors`, even though those errors are no longer present in the raw messages (they were already truncated out). This is the merge working.
6. **Verify pending task persistence**: similarly, any `## 7. Pending Tasks` item from compact #1 should survive into compact #2.

**What to look for**:
- Two successive compacts preserve errors and pending tasks from the first
- No duplicate bullets in merged lists (dedup works)
- The compact SYSTEM MESSAGE content format is still markdown starting with `[Conversation summary]:` (backward compat)
- Pending tasks list does NOT grow unbounded — capped at 10 items; errors capped at 5
- `<analysis>` tags still stripped (carried over from I.1)

**Known caveat**: the `_last_work_card` is instance-scoped on the `ContextGuard`. If the process restarts mid-session, the merge starts fresh. Follow-up to stash in DbMemory for cross-session continuity is tracked as a v0.9 candidate.

---

### I.16 Turn Profiler — Phase-Level Timing

**Files**: `src/fim_one/core/agent/turn_profiler.py` (new), `src/fim_one/core/agent/react.py`, `tests/test_turn_profiler.py` (new, 10 tests), `tests/test_react.py` (+2 integration tests)

**Env var**: `REACT_TURN_PROFILE_ENABLED` (default: `true`)

**What it does**: each ReAct turn records phase-level timings for six phases and
emits one structured log line per turn:

```
turn_profile conv=abc123 turn=2 compact=3ms llm_first_token=245ms llm_total=245ms memory_load=12ms tool_exec=187ms tool_schema_build=4ms
```

Phases:
- `memory_load` — loading messages from `BaseMemory` (measured once, attributed to turn 1)
- `compact` — `MicroCompact` + `ContextGuard.check_and_compact` time per turn
- `tool_schema_build` — tool selection + schema construction (includes keyword shortcut path)
- `llm_first_token` — time to first token (currently equal to `llm_total` since ReAct uses non-streaming `chat()`; the separate key is preserved for future streaming migration)
- `llm_total` — total LLM call wall time (includes context-overflow retries as a single sum)
- `tool_exec` — wall time executing tools (sum across all tool calls in the turn)

When `REACT_TURN_PROFILE_ENABLED=false`, `make_profiler()` returns a `NoOpTurnProfiler` whose context manager yields but records nothing — zero overhead.

**How to test manually**:
1. **Automated first**: `uv run pytest tests/test_turn_profiler.py tests/test_react.py -v` — 33 should pass.
2. **Live test — log inspection**: start the server (`./start.sh api`) with `LOG_LEVEL=INFO` or lower. Open a chat and ask the agent a multi-turn task with several tool calls. In the server logs, you should see one `turn_profile` line per iteration, with `conv=<uuid>` and `turn=<n>`.
3. **Phase sanity check**: the numbers should be physically sensible — `tool_exec > 0` when a tool ran that turn; `compact > 0` only on turns that triggered compaction; `llm_total >= llm_first_token` always. Most turns should have `tool_schema_build` in single-digit ms after the first turn (cached); `memory_load` should only be non-zero on turn 1.
4. **Disabled mode**: restart with `REACT_TURN_PROFILE_ENABLED=false`. Repeat the same chat — no `turn_profile` log lines should appear. Functionality should be identical.
5. **Grep helper**: `tail -f` the server log with `| grep turn_profile` to get a live stream of timing. Useful for spotting unexpectedly slow phases.

**What to look for**:
- One log line per turn, containing conversation id and turn number
- `compact` > 0 only on turns that trigger compaction
- `llm_total` dominates fast turns; `tool_exec` dominates I/O-heavy turns
- `conv=-` when memory backend is not `DbMemory` (e.g., window memory in tests) — acceptable
- Disabled mode: zero log lines, zero overhead

**Known caveats**:
- `conv` is best-effort via `getattr(self._memory, "_conversation_id", None)` — only `DbMemory` exposes it; other backends log `conv=-`
- Turn-budget early-exit path does not emit a profile (nothing measured)
- `llm_first_token == llm_total` always (non-streaming); the key is preserved for future streaming migration
- Profiling is **per-request logs only** — there is no metrics endpoint or aggregation yet. That's Agent Trace Layer territory (v0.9)

---

### I.17 Per-User Rate Limiting (bug fix)

**Files**: `src/fim_one/core/model/rate_limit.py`, `src/fim_one/web/api/chat.py`, `tests/test_rate_limit_per_user.py` (new, 16 tests), `tests/test_rate_limit.py` (4 tests adapted)

**Env var**: `LLM_RATE_LIMIT_PER_USER` (default: `true`)

**What it does**: the model-layer rate limiter (`LLMRateLimiter`) previously used a
single process-global token bucket. One noisy user saturating the bucket would
block ALL other users on the same worker. This fix partitions the bucket
state by user id:

- Lookup key priority: explicit `user_id=` arg → `current_user_id` ContextVar → `"__shared__"` sentinel
- Each user gets independent `request_tokens` / `token_tokens` counters with its own `asyncio.Lock`
- Lazy sampling cleanup: each `acquire()` calls `_maybe_evict_idle()`, sampling one random bucket and evicting if `last_touched > cleanup_idle_seconds` (default 600s)
- When `LLM_RATE_LIMIT_PER_USER=false`, all three lookup paths collapse to `"__global__"` (legacy bucket, unchanged math)

**Why**: this was a latent multi-tenancy bug. With per-user token quotas already
enforced at the HTTP layer (429), we'd expect user A's heavy usage to only hit
user A. But the LLM-layer limiter below that was still global, so user A's bursts
would also throttle users B, C, D on the same worker.

**Wiring note**: the fix uses a `ContextVar` (set in the chat handler) rather than
threading `user_id` through `BaseLLM.chat()`. Rationale: the signature change
would have cascaded to 20+ call sites including the off-limits `core/agent/react.py`.
The ContextVar propagates naturally through `asyncio.gather`, `create_task`, and
the `StreamingResponse` generator because Python copies the context at task creation.

**How to test manually**:
1. **Automated first**: `uv run pytest tests/test_rate_limit_per_user.py tests/test_rate_limit.py -v` — 31 should pass.
2. **Starvation test — two users**: this is the crucial bug the fix addresses.
   - Configure a model with a low RPM limit (e.g., 5 requests/minute) in Admin → Models
   - Log in as **user A** in one browser profile. Spam 6 quick chat messages in a row → user A should get throttled / queued after 5
   - IMMEDIATELY in a different browser profile, log in as **user B** and send ONE chat message
   - **Before this fix**: user B would be stuck waiting in the same bucket as user A
   - **After this fix**: user B responds normally, unaffected by user A's saturation
3. **Same-user serialization**: same browser (user A), fire two rapid messages. They should be processed in order, respecting the limit — but only against user A's own bucket.
4. **Disable test**: set `LLM_RATE_LIMIT_PER_USER=false` and restart. Repeat step 2. Both users should now share the single global bucket (legacy behavior). Re-enable to confirm fix.
5. **Memory hygiene**: send requests as many different users (create test accounts, or use a script). Over many requests, old idle users should get evicted from the bucket dict (check memory growth via `/api/health` or a Python memory snapshot). Default idle cutoff is 10 minutes.

**What to look for**:
- User A's saturation does NOT block user B (core fix)
- Same-user requests still respect the rate limit
- Backward compat: existing callers without `user_id` continue working
- No background task spawned — cleanup is lazy sampling on `acquire()`
- Per-worker only: if you run multiple uvicorn workers, each maintains its own bucket dict (Redis-backed cross-worker limiting is out of scope)

**Known caveats**:
- Background jobs (non-web handlers without a ContextVar) fall to `"__shared__"` — one global bucket for all background work. Acceptable and matches pre-fix behavior.
- The ContextVar is set-without-reset in the handler — safe because FastAPI runs each request in a fresh asyncio task whose context is a copy, so the leaked binding dies with the task. If the handler is ever moved to a long-lived shared task, wrap in `try/finally` with a reset token.

---

## Quick Reference

```bash
# Run all tests
uv run pytest tests/ -x -q

# Run Phase 1 tests only
uv run pytest tests/test_microcompact.py tests/test_retry.py -v

# Run Phase 2 tests only
uv run pytest tests/test_model.py::TestSharedHttpClient tests/test_fallback.py -v

# Run Phase 3 tests only
uv run pytest tests/test_db_memory_recovery.py tests/test_work_card.py tests/test_turn_profiler.py tests/test_rate_limit_per_user.py -v

# Type check all Phase 3 changed files
uv run mypy src/fim_one/core/memory/db.py src/fim_one/core/memory/work_card.py src/fim_one/core/memory/context_guard.py src/fim_one/core/agent/turn_profiler.py src/fim_one/core/agent/react.py src/fim_one/core/model/rate_limit.py src/fim_one/web/api/chat.py

# Test with low tool budget (to observe I.8 truncation)
REACT_TOOL_RESULT_BUDGET=100 ./start.sh api

# Test with low completion check threshold (to observe I.12 skip)
REACT_COMPLETION_CHECK_SKIP_CHARS=10 ./start.sh api

# Watch I.16 profiler output in real time
tail -f ~/.fim-one/logs/server.log | grep turn_profile

# Disable I.16 profiler entirely
REACT_TURN_PROFILE_ENABLED=false ./start.sh api

# Disable I.17 per-user rate limiting (revert to legacy global)
LLM_RATE_LIMIT_PER_USER=false ./start.sh api
```
