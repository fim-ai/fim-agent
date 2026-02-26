"""SSE chat endpoints for ReAct and DAG agent modes.

Both endpoints stream Server-Sent Events with the following event names:

- ``step``           – ReAct iteration progress (tool calls, thinking).
- ``step_progress``  – DAG per-step progress (started / iteration / completed).
- ``phase``          – DAG pipeline phase transitions (planning / executing / analyzing).
- ``done``           – Final result payload (always the last event).

A keepalive comment (``": keepalive\\n\\n"``) is emitted every 15 seconds of
inactivity to prevent proxy/browser timeouts during long LLM calls.

When the SSE client disconnects, running agent tasks are cancelled promptly
(checked every 0.5 s) so that LLM and tool work does not continue in the
background.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import suppress
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from fim_agent.core.agent import ReActAgent
from fim_agent.core.planner import DAGExecutor, DAGPlanner, PlanAnalyzer

from ..deps import get_fast_llm, get_llm, get_max_concurrency, get_model_registry, get_tools

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------


def _sse(event: str, data: Any) -> str:
    """Format a Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _emit(sse_events: list[dict[str, Any]], event: str, data: Any) -> str:
    """Accumulate event for persistence and return SSE frame for streaming."""
    sse_events.append({"event": event, "data": data})
    return _sse(event, data)


# ---------------------------------------------------------------------------
# ReAct endpoint
# ---------------------------------------------------------------------------


@router.get("/react")
async def react_endpoint(
    request: Request,
    q: str,
    user_id: str = "default",
    conversation_id: str | None = None,
) -> StreamingResponse:
    """Run a ReAct agent query with SSE progress updates.

    Parameters
    ----------
    request : Request
        The incoming HTTP request; used to detect client disconnects.
    q : str
        The user query / task description.
    user_id : str
        Identifier for the requesting user (reserved for future auth).
    conversation_id : str | None
        Optional conversation ID. When provided, user and assistant messages
        are persisted to the database.
    """
    _ = user_id  # reserved for future auth

    async def generate() -> AsyncGenerator[str, None]:  # noqa: C901
        t0 = time.time()
        sse_events: list[dict[str, Any]] = []
        yield _emit(sse_events, "step", {"type": "thinking", "iteration": 0})

        # -- Optional persistence setup ------------------------------------
        db_session = None
        if conversation_id:
            try:
                from fim_agent.db import create_session
                from fim_agent.web.models import Message as MessageModel

                db_session = create_session()
                user_msg = MessageModel(
                    conversation_id=conversation_id,
                    role="user",
                    content=q,
                    message_type="text",
                )
                db_session.add(user_msg)
                await db_session.commit()
            except Exception:
                logger.warning(
                    "Failed to persist user message for conversation %s",
                    conversation_id,
                    exc_info=True,
                )
                db_session = None

        progress_queue: asyncio.Queue[str] = asyncio.Queue()
        done_event = asyncio.Event()
        iter_start = time.time()

        def on_iteration(
            iteration: int,
            action: Any,
            observation: str | None,
            error: str | None,
        ) -> None:
            nonlocal iter_start
            if action.type == "tool_call":
                is_starting = observation is None and error is None
                now = time.time()
                iter_elapsed: float | None = None
                if is_starting:
                    # Reset timer when tools start executing, so parallel
                    # tools all measure from the same baseline.
                    iter_start = now
                else:
                    iter_elapsed = round(now - iter_start, 2)
                payload: dict[str, Any] = {
                    "type": "tool_start" if is_starting else "tool_call",
                    "iteration": iteration,
                    "tool_name": action.tool_name,
                    "tool_args": action.tool_args,
                    "reasoning": action.reasoning,
                    "observation": observation,
                    "error": error,
                }
                if iter_elapsed is not None:
                    payload["iter_elapsed"] = iter_elapsed
                sse_events.append({"event": "step", "data": payload})
                progress_queue.put_nowait(_sse("step", payload))

        try:
            llm = get_llm()
            tools = get_tools()
            memory = None
            if conversation_id:
                from fim_agent.core.memory import DbMemory
                memory = DbMemory(conversation_id=conversation_id)
            agent = ReActAgent(llm=llm, tools=tools, max_iterations=20, memory=memory)

            async def _run() -> Any:
                try:
                    return await agent.run(q, on_iteration=on_iteration)
                finally:
                    done_event.set()

            run_task = asyncio.create_task(_run())

            # Drain the queue until the agent task signals completion.
            # Poll every 0.5 s so we can detect client disconnect quickly;
            # keepalive comments are sent every 15 s of inactivity.
            last_keepalive = time.time()
            while not done_event.is_set():
                try:
                    item = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    # Check for client disconnect.
                    if await request.is_disconnected():
                        logger.info("Client disconnected — cancelling ReAct task")
                        run_task.cancel()
                        with suppress(asyncio.CancelledError, TimeoutError, Exception):
                            await asyncio.wait_for(run_task, timeout=5.0)
                        return
                    # Send keepalive only every 15 seconds.
                    now = time.time()
                    if now - last_keepalive >= 15.0:
                        yield ": keepalive\n\n"
                        last_keepalive = now
                    continue
                last_keepalive = time.time()
                yield item

            # Flush any remaining items queued between the last get() and done_event.
            while not progress_queue.empty():
                yield progress_queue.get_nowait()

            # If the task was cancelled (e.g. disconnect during flush), don't
            # try to read its result.
            if run_task.cancelled():
                return

            result = run_task.result()

            elapsed = round(time.time() - t0, 2)
            last_iter_elapsed = round(time.time() - iter_start, 2)
            done_payload: dict[str, Any] = {
                "answer": result.answer,
                "iterations": result.iterations,
                "elapsed": elapsed,
                "iter_elapsed": last_iter_elapsed,
            }
            if result.usage is not None:
                done_payload["usage"] = {
                    "prompt_tokens": result.usage.prompt_tokens,
                    "completion_tokens": result.usage.completion_tokens,
                    "total_tokens": result.usage.total_tokens,
                }
            # Append the done event to sse_events before persisting.
            sse_events.append({"event": "done", "data": done_payload})

            # -- Persist assistant message BEFORE yielding done -----------
            # The client closes the SSE connection as soon as it receives the
            # "done" event, which terminates this async generator.  Any code
            # after the final yield would never execute.
            if db_session and conversation_id:
                try:
                    from fim_agent.web.models import (
                        Conversation,
                        Message as MessageModel,
                    )
                    from sqlalchemy import select as sa_select

                    assistant_msg = MessageModel(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=result.answer,
                        message_type="done",
                        metadata_={**done_payload, "sse_events": sse_events},
                    )
                    db_session.add(assistant_msg)
                    if "usage" in done_payload:
                        stmt = sa_select(Conversation).where(
                            Conversation.id == conversation_id
                        )
                        conv = (
                            await db_session.execute(stmt)
                        ).scalar_one_or_none()
                        if conv:
                            conv.total_tokens = (
                                conv.total_tokens or 0
                            ) + done_payload["usage"].get("total_tokens", 0)
                    await db_session.commit()
                except Exception:
                    logger.warning(
                        "Failed to persist assistant message for "
                        "conversation %s",
                        conversation_id,
                        exc_info=True,
                    )

            yield _sse("done", done_payload)
        except Exception as exc:
            logger.exception("ReAct agent failed")
            elapsed = round(time.time() - t0, 2)
            yield _sse(
                "done",
                {
                    "answer": f"Agent error: {type(exc).__name__}: {exc}",
                    "iterations": 0,
                    "elapsed": elapsed,
                },
            )
        finally:
            if db_session:
                await db_session.close()

    return StreamingResponse(generate(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# DAG endpoint
# ---------------------------------------------------------------------------


@router.get("/dag")
async def dag_endpoint(
    request: Request,
    q: str,
    user_id: str = "default",
    conversation_id: str | None = None,
) -> StreamingResponse:
    """Run a DAG planner pipeline with SSE progress updates.

    Parameters
    ----------
    request : Request
        The incoming HTTP request; used to detect client disconnects.
    q : str
        The user query / task description.
    user_id : str
        Identifier for the requesting user (reserved for future auth).
    conversation_id : str | None
        Optional conversation ID. When provided, user and assistant messages
        are persisted to the database.
    """
    _ = user_id  # reserved for future auth

    async def generate() -> AsyncGenerator[str, None]:  # noqa: C901
        t0 = time.time()
        sse_events: list[dict[str, Any]] = []

        # -- Optional persistence setup ------------------------------------
        db_session = None
        if conversation_id:
            try:
                from fim_agent.db import create_session
                from fim_agent.web.models import Message as MessageModel

                db_session = create_session()
                user_msg = MessageModel(
                    conversation_id=conversation_id,
                    role="user",
                    content=q,
                    message_type="text",
                )
                db_session.add(user_msg)
                await db_session.commit()
            except Exception:
                logger.warning(
                    "Failed to persist user message for conversation %s",
                    conversation_id,
                    exc_info=True,
                )
                db_session = None

        # -- Load conversation context for multi-turn DAG planning ----------
        enriched_query = q
        dag_memory = None
        if conversation_id:
            try:
                from fim_agent.core.memory import DbMemory

                dag_memory = DbMemory(conversation_id=conversation_id)
                history = await dag_memory.get_messages()
                if history:
                    context_lines = []
                    for msg in history:
                        prefix = "User" if msg.role == "user" else "Assistant"
                        context_lines.append(f"{prefix}: {msg.content}")
                    context_str = "\n".join(context_lines)
                    enriched_query = (
                        f"Previous conversation:\n{context_str}\n\n"
                        f"Current request: {q}"
                    )
            except Exception:
                logger.warning(
                    "Failed to load conversation history for DAG planning "
                    "(conversation %s)",
                    conversation_id,
                    exc_info=True,
                )

        # Queue bridges the executor's synchronous callback into the async SSE stream.
        progress_queue: asyncio.Queue[str] = asyncio.Queue()
        done_event = asyncio.Event()

        def on_step_progress(step_id: str, event: str, data: dict[str, Any]) -> None:
            step_payload = {"step_id": step_id, "event": event, **data}
            sse_events.append({"event": "step_progress", "data": step_payload})
            progress_queue.put_nowait(_sse("step_progress", step_payload))

        try:
            llm = get_llm()           # Sonnet — planning & analysis
            fast_llm = get_fast_llm()  # Haiku — step execution
            tools = get_tools()

            # Phase 1: Plan (Sonnet)
            yield _emit(sse_events, "phase", {"name": "planning", "status": "start"})
            planner = DAGPlanner(llm=llm)
            plan = await planner.plan(enriched_query)
            yield _emit(
                sse_events,
                "phase",
                {
                    "name": "planning",
                    "status": "done",
                    "steps": [
                        {
                            "id": s.id,
                            "task": s.task,
                            "deps": s.dependencies,
                            "tool_hint": s.tool_hint,
                        }
                        for s in plan.steps
                    ],
                },
            )

            # Phase 2: Execute — Haiku (with real-time step progress)
            yield _emit(sse_events, "phase", {"name": "executing", "status": "start"})
            agent = ReActAgent(llm=fast_llm, tools=tools, max_iterations=15, memory=dag_memory)
            registry = get_model_registry()
            executor = DAGExecutor(
                agent=agent,
                max_concurrency=get_max_concurrency(),
                model_registry=registry,
            )

            async def _exec() -> Any:
                try:
                    return await executor.execute(plan, on_progress=on_step_progress)
                finally:
                    done_event.set()

            exec_task = asyncio.create_task(_exec())

            # Poll every 0.5 s so we can detect client disconnect quickly;
            # keepalive comments are sent every 15 s of inactivity.
            last_keepalive = time.time()
            while not done_event.is_set():
                try:
                    item = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    # Check for client disconnect.
                    if await request.is_disconnected():
                        logger.info("Client disconnected — cancelling DAG exec task")
                        exec_task.cancel()
                        with suppress(asyncio.CancelledError, TimeoutError, Exception):
                            await asyncio.wait_for(exec_task, timeout=5.0)
                        return
                    # Send keepalive only every 15 seconds.
                    now = time.time()
                    if now - last_keepalive >= 15.0:
                        yield ": keepalive\n\n"
                        last_keepalive = now
                    continue
                last_keepalive = time.time()
                yield item

            # Flush remaining items.
            while not progress_queue.empty():
                yield progress_queue.get_nowait()

            # If the task was cancelled (e.g. disconnect during flush), skip
            # the remaining phases.
            if exec_task.cancelled():
                return

            plan = exec_task.result()

            yield _emit(
                sse_events,
                "phase",
                {
                    "name": "executing",
                    "status": "done",
                    "results": [
                        {
                            "id": s.id,
                            "task": s.task,
                            "status": s.status,
                            "result": s.result,
                            "started_at": s.started_at,
                            "completed_at": s.completed_at,
                            "duration": s.duration,
                        }
                        for s in plan.steps
                    ],
                },
            )

            # Check disconnect before starting Phase 3 — no point analysing
            # if nobody is listening.
            if await request.is_disconnected():
                logger.info("Client disconnected — skipping DAG analysis phase")
                return

            # Phase 3: Analyze (Sonnet)
            yield _emit(sse_events, "phase", {"name": "analyzing", "status": "start"})
            analyzer = PlanAnalyzer(llm=llm)
            analysis = await analyzer.analyze(enriched_query, plan)
            elapsed = round(time.time() - t0, 2)
            yield _emit(
                sse_events,
                "phase",
                {
                    "name": "analyzing",
                    "status": "done",
                    "achieved": analysis.achieved,
                    "confidence": analysis.confidence,
                    "reasoning": analysis.reasoning,
                },
            )

            # Build the answer: prefer analyzer's final_answer, fall back to
            # concatenated step results so users always see something useful.
            answer = analysis.final_answer
            if not answer:
                completed = [
                    s for s in plan.steps if s.status == "completed" and s.result
                ]
                if completed:
                    answer = "\n\n---\n\n".join(
                        f"**{s.id}**: {s.result}" for s in completed
                    )
                else:
                    answer = "(goal not achieved)"

            # Aggregate total usage across all DAG phases.
            total_usage = plan.total_usage
            if analysis.usage is not None:
                if total_usage is not None:
                    total_usage += analysis.usage
                else:
                    total_usage = analysis.usage

            dag_done_payload: dict[str, Any] = {
                "answer": answer,
                "achieved": analysis.achieved,
                "confidence": analysis.confidence,
                "elapsed": elapsed,
            }
            if total_usage is not None:
                dag_done_payload["usage"] = {
                    "prompt_tokens": total_usage.prompt_tokens,
                    "completion_tokens": total_usage.completion_tokens,
                    "total_tokens": total_usage.total_tokens,
                }
            # Append the done event to sse_events before persisting.
            sse_events.append({"event": "done", "data": dag_done_payload})

            # -- Persist assistant message BEFORE yielding done -----------
            if db_session and conversation_id:
                try:
                    from fim_agent.web.models import (
                        Conversation as ConvModel,
                        Message as MessageModel,
                    )
                    from sqlalchemy import select as sa_select

                    assistant_msg = MessageModel(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=answer,
                        message_type="done",
                        metadata_={**dag_done_payload, "sse_events": sse_events},
                    )
                    db_session.add(assistant_msg)
                    if "usage" in dag_done_payload:
                        stmt = sa_select(ConvModel).where(
                            ConvModel.id == conversation_id
                        )
                        conv = (
                            await db_session.execute(stmt)
                        ).scalar_one_or_none()
                        if conv:
                            conv.total_tokens = (
                                conv.total_tokens or 0
                            ) + dag_done_payload["usage"].get(
                                "total_tokens", 0
                            )
                    await db_session.commit()
                except Exception:
                    logger.warning(
                        "Failed to persist assistant message for "
                        "conversation %s",
                        conversation_id,
                        exc_info=True,
                    )

            yield _sse("done", dag_done_payload)
        except Exception as exc:
            logger.exception("DAG pipeline failed")
            elapsed = round(time.time() - t0, 2)
            yield _sse(
                "done",
                {
                    "answer": f"Pipeline error: {type(exc).__name__}: {exc}",
                    "achieved": False,
                    "confidence": 0.0,
                    "elapsed": elapsed,
                },
            )
        finally:
            if db_session:
                await db_session.close()

    return StreamingResponse(generate(), media_type="text/event-stream")
