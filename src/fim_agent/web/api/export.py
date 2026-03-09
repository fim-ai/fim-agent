"""Conversation export -- MD, TXT, DOCX."""

from __future__ import annotations

import io
import json
import logging
import re
from datetime import datetime
from enum import Enum
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fim_agent.db import get_session
from fim_agent.web.auth import get_current_user
from fim_agent.web.exceptions import AppError
from fim_agent.web.models import Conversation, Message, User

router = APIRouter(prefix="/api/conversations", tags=["export"])
logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    MD = "md"
    TXT = "txt"
    DOCX = "docx"


class DetailLevel(str, Enum):
    FULL = "full"
    SUMMARY = "summary"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sanitize_filename(title: str) -> str:
    """Replace characters unsafe for filenames with underscores."""
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title)
    safe = safe.strip(". ")
    return safe or "conversation"


def _format_date(dt: datetime | None) -> str:
    """Return an ISO-8601 date string or empty string."""
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


def _format_date_compact(dt: datetime | None) -> str:
    """Return a compact date for filenames like 20260309."""
    return dt.strftime("%Y%m%d") if dt else "export"


def _mode_label(mode: str) -> str:
    return "DAG (Plan & Execute)" if mode == "dag" else "Standard (ReAct)"


def _pair_messages(messages: list[Message]) -> list[dict[str, Any]]:
    """Group messages into turns: each turn has a user message and an
    optional assistant message.  Messages are expected to be sorted by
    ``created_at``."""
    turns: list[dict[str, Any]] = []
    current_turn: dict[str, Any] | None = None

    for msg in messages:
        if msg.role == "user":
            current_turn = {"user": msg, "assistant": None}
            turns.append(current_turn)
        elif msg.role == "assistant":
            if current_turn is not None:
                current_turn["assistant"] = msg
            else:
                # Orphan assistant message -- create a turn without user msg
                turns.append({"user": None, "assistant": msg})

    return turns


# ---------------------------------------------------------------------------
# SSE event parsing helpers
# ---------------------------------------------------------------------------


def _extract_sse_events(msg: Message) -> list[dict[str, Any]]:
    """Return the sse_events list from an assistant message's metadata."""
    meta = msg.metadata_ or {}
    return meta.get("sse_events", [])


def _extract_react_steps(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract completed tool-call steps from ReAct SSE events."""
    steps: list[dict[str, Any]] = []
    for ev in events:
        if ev.get("event") == "step":
            data = ev.get("data", {})
            if data.get("type") == "tool_call":
                steps.append(data)
    return steps


def _extract_done_event(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Extract the done event from SSE events."""
    for ev in events:
        if ev.get("event") == "done":
            return ev.get("data", {})
    return None


def _extract_dag_plan(events: list[dict[str, Any]], target_round: int = 1) -> list[dict[str, Any]]:
    """Extract plan steps for a given DAG round."""
    for ev in events:
        if ev.get("event") == "phase":
            data = ev.get("data", {})
            if (
                data.get("name") == "planning"
                and data.get("status") == "done"
                and data.get("round", 1) == target_round
            ):
                return data.get("steps", [])
    return []


def _extract_dag_step_details(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Group step_progress events by step_id, collecting iterations and completion info."""
    steps: dict[str, dict[str, Any]] = {}
    for ev in events:
        if ev.get("event") == "step_progress":
            data = ev.get("data", {})
            sid = data.get("step_id", "")
            if sid not in steps:
                steps[sid] = {"iterations": [], "completed": None, "task": data.get("task", "")}

            event_type = data.get("event")
            if event_type == "iteration":
                steps[sid]["iterations"].append(data)
            elif event_type == "completed":
                steps[sid]["completed"] = data
            elif event_type == "started":
                steps[sid]["task"] = data.get("task", steps[sid]["task"])

    return steps


def _extract_dag_analysis(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Extract the analysis phase result."""
    for ev in events:
        if ev.get("event") == "phase":
            data = ev.get("data", {})
            if data.get("name") == "analyzing" and data.get("status") == "done":
                return data
    return None


def _extract_dag_rounds(events: list[dict[str, Any]]) -> list[int]:
    """Determine which DAG rounds exist in the events."""
    rounds: set[int] = set()
    for ev in events:
        if ev.get("event") == "phase":
            data = ev.get("data", {})
            r = data.get("round")
            if r is not None:
                rounds.add(r)
    return sorted(rounds) if rounds else [1]


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------


def _render_md(conv: Conversation, messages: list[Message], detail: DetailLevel) -> str:
    """Render a conversation as a Markdown document."""
    lines: list[str] = []
    title = conv.title or "Untitled Conversation"

    # Header
    lines.append(f"# {title}")
    lines.append("")
    meta_parts = [
        f"**Mode:** {_mode_label(conv.mode)}",
    ]
    if conv.model_name:
        meta_parts.append(f"**Model:** {conv.model_name}")
    meta_parts.append(f"**Created:** {_format_date(conv.created_at)}")
    lines.append(" | ".join(meta_parts))

    if detail == DetailLevel.FULL and conv.total_tokens:
        lines.append(f"**Total Tokens:** {conv.total_tokens:,}")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Turns
    turns = _pair_messages(messages)
    for idx, turn in enumerate(turns, 1):
        lines.append(f"## Turn {idx}")
        lines.append("")

        # User message
        user_msg: Message | None = turn.get("user")
        if user_msg:
            lines.append("**User:**")
            lines.append("")
            lines.append(user_msg.content or "")
            lines.append("")

        # Assistant message
        asst_msg: Message | None = turn.get("assistant")
        if asst_msg is None:
            lines.append("---")
            lines.append("")
            continue

        lines.append("**Assistant:**")
        lines.append("")

        if detail == DetailLevel.FULL:
            events = _extract_sse_events(asst_msg)
            done = _extract_done_event(events)

            if conv.mode == "dag":
                _render_md_dag_details(lines, events, done)
            else:
                _render_md_react_details(lines, events, done)

        # Final answer
        answer = asst_msg.content or ""
        if not answer and asst_msg.metadata_:
            answer = asst_msg.metadata_.get("answer", "")
        lines.append(answer)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def _render_md_react_details(
    lines: list[str],
    events: list[dict[str, Any]],
    done: dict[str, Any] | None,
) -> None:
    """Append ReAct execution details in Markdown."""
    steps = _extract_react_steps(events)
    if not steps:
        return

    iterations = done.get("iterations", len(steps)) if done else len(steps)
    elapsed = done.get("elapsed", 0) if done else 0

    lines.append(
        f"> **Execution Details** ({iterations} iteration{'s' if iterations != 1 else ''}, {elapsed:.1f}s)"
    )
    lines.append(">")
    lines.append("> | # | Tool | Duration |")
    lines.append("> |---|------|----------|")
    for i, step in enumerate(steps, 1):
        tool = step.get("tool_name", "unknown")
        dur = step.get("iter_elapsed", 0)
        lines.append(f"> | {i} | {tool} | {dur:.1f}s |")
    lines.append("")

    for i, step in enumerate(steps, 1):
        tool = step.get("tool_name", "unknown")
        dur = step.get("iter_elapsed", 0)
        lines.append(f"<details>")
        lines.append(f"<summary>Step {i}: {tool} ({dur:.1f}s)</summary>")
        lines.append("")

        reasoning = step.get("reasoning")
        if reasoning:
            lines.append(f"**Reasoning:** {reasoning}")
            lines.append("")

        args = step.get("tool_args")
        if args:
            lines.append("**Arguments:**")
            lines.append("```json")
            lines.append(json.dumps(args, indent=2, ensure_ascii=False))
            lines.append("```")
            lines.append("")

        observation = step.get("observation")
        if observation:
            lines.append("**Result:**")
            lines.append(str(observation))
            lines.append("")

        lines.append("</details>")
        lines.append("")


def _render_md_dag_details(
    lines: list[str],
    events: list[dict[str, Any]],
    done: dict[str, Any] | None,
) -> None:
    """Append DAG execution details in Markdown."""
    rounds = _extract_dag_rounds(events)

    for rnd in rounds:
        plan_steps = _extract_dag_plan(events, rnd)
        if plan_steps:
            lines.append(f"> **Plan** (Round {rnd})")
            lines.append(">")
            lines.append("> | Step | Task | Dependencies |")
            lines.append("> |------|------|-------------|")
            for ps in plan_steps:
                sid = ps.get("id", "?")
                task = ps.get("task", "")
                deps = ", ".join(ps.get("deps", [])) or "\u2014"
                lines.append(f"> | {sid} | {task} | {deps} |")
            lines.append("")

    step_details = _extract_dag_step_details(events)
    for sid, info in step_details.items():
        task = info.get("task", "")
        completed = info.get("completed")
        status = completed.get("status", "completed") if completed else "unknown"
        duration = completed.get("duration", 0) if completed else 0

        lines.append("<details>")
        lines.append(f"<summary>{sid}: {task} ({status}, {duration:.1f}s)</summary>")
        lines.append("")

        iterations = info.get("iterations", [])
        if iterations:
            lines.append("**Iterations:**")
            for it in iterations:
                it_num = it.get("iteration", "?")
                tool = it.get("tool_name", "unknown")
                dur = it.get("iter_elapsed", 0)
                reasoning = it.get("reasoning", "")
                observation = it.get("observation", "")
                lines.append(
                    f"{it_num}. **{tool}** ({dur:.1f}s) \u2014 Reasoning: {reasoning}"
                )
                if observation:
                    lines.append(f"   Result: {observation}")
            lines.append("")

        result = completed.get("result", "") if completed else ""
        if result:
            lines.append(f"**Step Result:** {result}")
            lines.append("")

        lines.append("</details>")
        lines.append("")

    analysis = _extract_dag_analysis(events)
    if analysis:
        achieved = analysis.get("achieved", False)
        confidence = analysis.get("confidence", 0)
        reasoning = analysis.get("reasoning", "")
        achieved_label = "Goal Achieved" if achieved else "Goal Not Achieved"
        lines.append(
            f"> **Analysis:** {achieved_label} ({confidence * 100:.0f}% confidence)"
        )
        if reasoning:
            lines.append(f"> {reasoning}")
        lines.append("")


# ---------------------------------------------------------------------------
# TXT renderer
# ---------------------------------------------------------------------------


def _strip_md(text: str) -> str:
    """Naively strip Markdown formatting for plain-text output."""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove bold/italic markers
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    # Remove heading markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove blockquote markers
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    # Remove code fences
    text = re.sub(r"```\w*\n?", "", text)
    # Remove horizontal rules
    text = re.sub(r"^---+\s*$", "=" * 60, text, flags=re.MULTILINE)
    return text


def _render_txt(conv: Conversation, messages: list[Message], detail: DetailLevel) -> str:
    """Render a conversation as plain text."""
    lines: list[str] = []
    title = conv.title or "Untitled Conversation"

    lines.append(title)
    lines.append("=" * len(title))
    lines.append("")
    lines.append(f"Mode: {_mode_label(conv.mode)}")
    if conv.model_name:
        lines.append(f"Model: {conv.model_name}")
    lines.append(f"Created: {_format_date(conv.created_at)}")
    if detail == DetailLevel.FULL and conv.total_tokens:
        lines.append(f"Total Tokens: {conv.total_tokens:,}")
    lines.append("")
    lines.append("=" * 60)
    lines.append("")

    turns = _pair_messages(messages)
    for idx, turn in enumerate(turns, 1):
        lines.append(f"Turn {idx}")
        lines.append("-" * 40)
        lines.append("")

        user_msg: Message | None = turn.get("user")
        if user_msg:
            lines.append("[User]")
            lines.append("")
            lines.append(user_msg.content or "")
            lines.append("")

        asst_msg: Message | None = turn.get("assistant")
        if asst_msg is None:
            lines.append("=" * 60)
            lines.append("")
            continue

        lines.append("[Assistant]")
        lines.append("")

        if detail == DetailLevel.FULL:
            events = _extract_sse_events(asst_msg)
            done = _extract_done_event(events)

            if conv.mode == "dag":
                _render_txt_dag_details(lines, events, done)
            else:
                _render_txt_react_details(lines, events, done)

        answer = asst_msg.content or ""
        if not answer and asst_msg.metadata_:
            answer = asst_msg.metadata_.get("answer", "")
        lines.append(answer)
        lines.append("")
        lines.append("=" * 60)
        lines.append("")

    return "\n".join(lines)


def _render_txt_react_details(
    lines: list[str],
    events: list[dict[str, Any]],
    done: dict[str, Any] | None,
) -> None:
    """Append ReAct details as plain text."""
    steps = _extract_react_steps(events)
    if not steps:
        return

    iterations = done.get("iterations", len(steps)) if done else len(steps)
    elapsed = done.get("elapsed", 0) if done else 0

    lines.append(
        f"  Execution Details: {iterations} iteration(s), {elapsed:.1f}s"
    )
    lines.append("")

    for i, step in enumerate(steps, 1):
        tool = step.get("tool_name", "unknown")
        dur = step.get("iter_elapsed", 0)
        lines.append(f"  Step {i}: {tool} ({dur:.1f}s)")

        reasoning = step.get("reasoning")
        if reasoning:
            lines.append(f"    Reasoning: {reasoning}")

        args = step.get("tool_args")
        if args:
            lines.append(f"    Arguments: {json.dumps(args, ensure_ascii=False)}")

        observation = step.get("observation")
        if observation:
            lines.append(f"    Result: {observation}")

        lines.append("")


def _render_txt_dag_details(
    lines: list[str],
    events: list[dict[str, Any]],
    done: dict[str, Any] | None,
) -> None:
    """Append DAG details as plain text."""
    rounds = _extract_dag_rounds(events)

    for rnd in rounds:
        plan_steps = _extract_dag_plan(events, rnd)
        if plan_steps:
            lines.append(f"  Plan (Round {rnd}):")
            for ps in plan_steps:
                sid = ps.get("id", "?")
                task = ps.get("task", "")
                deps = ", ".join(ps.get("deps", [])) or "none"
                lines.append(f"    {sid}: {task} [deps: {deps}]")
            lines.append("")

    step_details = _extract_dag_step_details(events)
    for sid, info in step_details.items():
        task = info.get("task", "")
        completed = info.get("completed")
        status = completed.get("status", "completed") if completed else "unknown"
        duration = completed.get("duration", 0) if completed else 0

        lines.append(f"  {sid}: {task} ({status}, {duration:.1f}s)")

        for it in info.get("iterations", []):
            it_num = it.get("iteration", "?")
            tool = it.get("tool_name", "unknown")
            dur = it.get("iter_elapsed", 0)
            reasoning = it.get("reasoning", "")
            observation = it.get("observation", "")
            lines.append(f"    Iteration {it_num}: {tool} ({dur:.1f}s)")
            if reasoning:
                lines.append(f"      Reasoning: {reasoning}")
            if observation:
                lines.append(f"      Result: {observation}")

        result = completed.get("result", "") if completed else ""
        if result:
            lines.append(f"    Step Result: {result}")
        lines.append("")

    analysis = _extract_dag_analysis(events)
    if analysis:
        achieved = analysis.get("achieved", False)
        confidence = analysis.get("confidence", 0)
        reasoning = analysis.get("reasoning", "")
        label = "Goal Achieved" if achieved else "Goal Not Achieved"
        lines.append(f"  Analysis: {label} ({confidence * 100:.0f}% confidence)")
        if reasoning:
            lines.append(f"    {reasoning}")
        lines.append("")


# ---------------------------------------------------------------------------
# DOCX renderer
# ---------------------------------------------------------------------------


def _render_docx(conv: Conversation, messages: list[Message], detail: DetailLevel) -> bytes:
    """Render a conversation as a DOCX file and return the raw bytes."""
    try:
        from docx import Document
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        raise AppError(
            "docx_not_available",
            status_code=501,
            detail="DOCX export requires the python-docx package. "
            "Install with: uv pip install python-docx",
        )

    doc = Document()
    title = conv.title or "Untitled Conversation"

    # Title
    doc.add_heading(title, level=1)

    # Metadata
    meta_text = f"Mode: {_mode_label(conv.mode)}"
    if conv.model_name:
        meta_text += f"  |  Model: {conv.model_name}"
    meta_text += f"  |  Created: {_format_date(conv.created_at)}"
    if detail == DetailLevel.FULL and conv.total_tokens:
        meta_text += f"  |  Total Tokens: {conv.total_tokens:,}"
    doc.add_paragraph(meta_text)

    # Turns
    turns = _pair_messages(messages)
    for idx, turn in enumerate(turns, 1):
        doc.add_heading(f"Turn {idx}", level=2)

        user_msg: Message | None = turn.get("user")
        if user_msg:
            doc.add_heading("User", level=3)
            doc.add_paragraph(user_msg.content or "")

        asst_msg: Message | None = turn.get("assistant")
        if asst_msg is None:
            continue

        doc.add_heading("Assistant", level=3)

        if detail == DetailLevel.FULL:
            events = _extract_sse_events(asst_msg)
            done = _extract_done_event(events)

            if conv.mode == "dag":
                _render_docx_dag_details(doc, events, done)
            else:
                _render_docx_react_details(doc, events, done)

        # Final answer
        answer = asst_msg.content or ""
        if not answer and asst_msg.metadata_:
            answer = asst_msg.metadata_.get("answer", "")
        if answer:
            doc.add_paragraph(answer)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _add_monospace_paragraph(doc: Any, text: str) -> None:
    """Add a paragraph with monospace font for code-like content."""
    try:
        from docx.shared import Pt
    except ImportError:
        doc.add_paragraph(text)
        return

    para = doc.add_paragraph()
    run = para.add_run(text)
    run.font.name = "Courier New"
    run.font.size = Pt(9)


def _render_docx_react_details(
    doc: Any,
    events: list[dict[str, Any]],
    done: dict[str, Any] | None,
) -> None:
    """Add ReAct execution details to a DOCX document."""
    steps = _extract_react_steps(events)
    if not steps:
        return

    iterations = done.get("iterations", len(steps)) if done else len(steps)
    elapsed = done.get("elapsed", 0) if done else 0

    doc.add_paragraph(
        f"Execution Details: {iterations} iteration(s), {elapsed:.1f}s"
    )

    for i, step in enumerate(steps, 1):
        tool = step.get("tool_name", "unknown")
        dur = step.get("iter_elapsed", 0)

        doc.add_paragraph(
            f"Step {i}: {tool} ({dur:.1f}s)", style="List Bullet"
        )

        reasoning = step.get("reasoning")
        if reasoning:
            doc.add_paragraph(f"Reasoning: {reasoning}", style="List Bullet 2")

        args = step.get("tool_args")
        if args:
            _add_monospace_paragraph(doc, json.dumps(args, indent=2, ensure_ascii=False))

        observation = step.get("observation")
        if observation:
            doc.add_paragraph(f"Result: {str(observation)[:500]}", style="List Bullet 2")


def _render_docx_dag_details(
    doc: Any,
    events: list[dict[str, Any]],
    done: dict[str, Any] | None,
) -> None:
    """Add DAG execution details to a DOCX document."""
    rounds = _extract_dag_rounds(events)

    for rnd in rounds:
        plan_steps = _extract_dag_plan(events, rnd)
        if plan_steps:
            doc.add_paragraph(f"Plan (Round {rnd}):")
            for ps in plan_steps:
                sid = ps.get("id", "?")
                task = ps.get("task", "")
                deps = ", ".join(ps.get("deps", [])) or "none"
                doc.add_paragraph(
                    f"{sid}: {task} [deps: {deps}]", style="List Bullet"
                )

    step_details = _extract_dag_step_details(events)
    for sid, info in step_details.items():
        task = info.get("task", "")
        completed = info.get("completed")
        status = completed.get("status", "completed") if completed else "unknown"
        duration = completed.get("duration", 0) if completed else 0

        doc.add_paragraph(f"{sid}: {task} ({status}, {duration:.1f}s)")

        for it in info.get("iterations", []):
            it_num = it.get("iteration", "?")
            tool = it.get("tool_name", "unknown")
            dur = it.get("iter_elapsed", 0)
            reasoning = it.get("reasoning", "")
            doc.add_paragraph(
                f"Iteration {it_num}: {tool} ({dur:.1f}s) - {reasoning}",
                style="List Bullet",
            )

            observation = it.get("observation", "")
            if observation:
                doc.add_paragraph(
                    f"Result: {str(observation)[:500]}", style="List Bullet 2"
                )

        result = completed.get("result", "") if completed else ""
        if result:
            doc.add_paragraph(f"Step Result: {result}", style="List Bullet")

    analysis = _extract_dag_analysis(events)
    if analysis:
        achieved = analysis.get("achieved", False)
        confidence = analysis.get("confidence", 0)
        reasoning = analysis.get("reasoning", "")
        label = "Goal Achieved" if achieved else "Goal Not Achieved"
        doc.add_paragraph(f"Analysis: {label} ({confidence * 100:.0f}% confidence)")
        if reasoning:
            doc.add_paragraph(reasoning)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

_CONTENT_TYPES: dict[ExportFormat, str] = {
    ExportFormat.MD: "text/markdown; charset=utf-8",
    ExportFormat.TXT: "text/plain; charset=utf-8",
    ExportFormat.DOCX: (
        "application/vnd.openxmlformats-officedocument"
        ".wordprocessingml.document"
    ),
}


@router.get("/{conversation_id}/export")
async def export_conversation(
    conversation_id: str,
    format: ExportFormat = Query(..., description="Export format: md, txt, or docx"),
    detail: DetailLevel = Query(
        DetailLevel.FULL, description="Detail level: full or summary"
    ),
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> StreamingResponse:
    """Export a conversation as a downloadable file.

    Supports Markdown, plain text, and DOCX formats.  The ``detail``
    parameter controls whether tool execution details are included
    (``full``) or only the final answers (``summary``).
    """
    # Fetch conversation with messages, verify ownership
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .options(selectinload(Conversation.messages))
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise AppError("conversation_not_found", status_code=404)

    # Sort messages chronologically
    messages = sorted(conv.messages, key=lambda m: m.created_at)

    # Build filename
    safe_title = _sanitize_filename(conv.title or "conversation")
    date_str = _format_date_compact(conv.created_at)
    ext = format.value
    filename = f"{safe_title}_{date_str}.{ext}"

    # Render content
    if format == ExportFormat.DOCX:
        content_bytes = _render_docx(conv, messages, detail)
        stream = io.BytesIO(content_bytes)
    elif format == ExportFormat.TXT:
        text = _render_txt(conv, messages, detail)
        stream = io.BytesIO(text.encode("utf-8"))
    else:  # MD
        text = _render_md(conv, messages, detail)
        stream = io.BytesIO(text.encode("utf-8"))

    content_type = _CONTENT_TYPES[format]

    # RFC 5987: use ASCII fallback + UTF-8 encoded filename for non-ASCII titles
    ascii_filename = filename.encode("ascii", errors="ignore").decode("ascii") or f"export.{ext}"
    utf8_filename = quote(filename)
    disposition = f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{utf8_filename}"

    return StreamingResponse(
        stream,
        media_type=content_type,
        headers={
            "Content-Disposition": disposition,
        },
    )
