# Phase 0 + Phase 1 Manual Test Guide

> CC Insights Integration — Agent Infrastructure Improvements
> Implemented 2026-04-01

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

## Quick Reference

```bash
# Run all tests
uv run pytest tests/ -x -q

# Run Phase 1 tests only
uv run pytest tests/test_microcompact.py tests/test_retry.py -v

# Type check changed files
uv run mypy src/fim_one/core/memory/microcompact.py src/fim_one/core/agent/react.py src/fim_one/core/model/retry.py

# Test with low tool budget (to observe truncation)
REACT_TOOL_RESULT_BUDGET=100 ./start.sh api
```
