"""
agent_context/context_store.py
Minimal, pragmatic shared context store for multi-agent handoffs.
"""

from __future__ import annotations

import functools
import inspect
import os
import shutil
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONTEXT_FILE = os.path.join(BASE_DIR, "CONTEXT.md")
DEFAULT_HISTORY_DIR = os.path.join(BASE_DIR, "history")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


# --- Parsing & Serializing ---

def parse_markdown(text: str) -> Dict[str, Any]:
    """Parse YAML frontmatter + markdown sections into a simple dict."""
    parts = text.split("---", 2)
    meta = yaml.safe_load(parts[1]) if len(parts) >= 3 else {}
    body = parts[2] if len(parts) >= 3 else text

    sections: Dict[str, str] = {}
    current_sec = None
    for line in body.splitlines():
        if line.startswith("# "):
            current_sec = line[2:].strip()
            sections[current_sec] = ""
        elif current_sec:
            sections[current_sec] += line + "\n"

    def bullets(raw: str) -> List[str]:
        items = []
        for l in raw.splitlines():
            l = l.strip()
            if l.startswith("- ") and l[2:].strip().lower() != "none":
                items.append(l[2:].strip())
        return items

    artifacts: Dict[str, str] = {}
    for l in sections.get("Artifacts", "").splitlines():
        if ":" in l and not l.strip().startswith("#"):
            k, v = l.split(":", 1)
            if k.strip().lower() != "none":
                artifacts[k.strip()] = v.strip()

    return {
        "version": int(meta.get("version", 1)),
        "last_updated": str(meta.get("last_updated", _now())),
        "last_agent": str(meta.get("last_agent", "system")),
        "workflow_id": str(meta.get("workflow_id", "default")),
        "status": str(meta.get("status", "in_progress")),
        "objective": sections.get("Objective", "").strip(),
        "current_focus": sections.get("Current Focus", "").strip(),
        "completed_work": bullets(sections.get("Completed Work", "")),
        "blockers": bullets(sections.get("Open Questions / Blockers", "")),
        "artifacts": artifacts,
        "handoff_notes": sections.get("Handoff Notes", "").strip(),
        "decision_log": bullets(sections.get("Decision Log", "")),
    }


def serialize(state: Dict[str, Any]) -> str:
    """Format dict back into canonical CONTEXT.md format."""
    meta = {
        "version": int(state.get("version", 1)),
        "last_updated": state.get("last_updated", _now()),
        "last_agent": state.get("last_agent", "system"),
        "workflow_id": state.get("workflow_id", "default"),
        "status": state.get("status", "in_progress"),
    }
    frontmatter = yaml.safe_dump(meta, sort_keys=False).strip()

    completed = "\n".join(f"- {x}" for x in state.get("completed_work", [])) or "- None"
    blockers = "\n".join(f"- {x}" for x in state.get("blockers", [])) or "- None"
    artifacts = "\n".join(f"{k}: {v}" for k, v in state.get("artifacts", {}).items()) or "none: none"
    decisions = "\n".join(f"- {x}" for x in state.get("decision_log", [])) or "- None"

    return f"""---
{frontmatter}
---

# Objective
{state.get('objective', '').strip()}

# Current Focus
{state.get('current_focus', '').strip()}

# Completed Work
{completed}

# Open Questions / Blockers
{blockers}

# Artifacts
{artifacts}

# Handoff Notes
{state.get('handoff_notes', '').strip()}

# Decision Log
{decisions}
"""


# --- Core Read / Write ---

def load(path: str = DEFAULT_CONTEXT_FILE) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return parse_markdown(f.read())


def save(
    state: Dict[str, Any],
    agent: str,
    note: str = "",
    rescope: bool = False,
    path: str = DEFAULT_CONTEXT_FILE,
    history_dir: str = DEFAULT_HISTORY_DIR,
) -> None:
    # Snapshot prior file if exists
    if os.path.exists(path):
        os.makedirs(history_dir, exist_ok=True)
        old_state = load(path)
        if not rescope and old_state.get("objective") and state.get("objective") != old_state.get("objective"):
            raise ValueError("Objective is locked. Pass rescope=True to change.")
        snap = os.path.join(history_dir, f"snapshot_{_stamp()}_v{old_state.get('version', 0)}_{agent}.md")
        shutil.copy2(path, snap)
        state["version"] = old_state.get("version", 0) + 1
    else:
        state["version"] = state.get("version", 1)

    state["last_updated"] = _now()
    state["last_agent"] = agent
    if note:
        state["handoff_notes"] = note

    content = serialize(state)
    tmp_file = f"{path}.tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp_file, path)


# --- Section Helpers ---

def append_completed(agent: str, outcome: str, path: str = DEFAULT_CONTEXT_FILE) -> None:
    ctx = load(path)
    ctx.setdefault("completed_work", []).append(f"[{agent} @ {_now()}] — {outcome.strip()}")
    save(ctx, agent=agent, path=path)


def set_focus(focus: str, agent: str, path: str = DEFAULT_CONTEXT_FILE) -> None:
    ctx = load(path)
    ctx["current_focus"] = focus.strip()
    save(ctx, agent=agent, path=path)


def add_blocker(agent: str, question: str, path: str = DEFAULT_CONTEXT_FILE) -> None:
    ctx = load(path)
    ctx.setdefault("blockers", []).append(f"[{agent} @ {_now()}] — {question.strip()}")
    ctx["status"] = "blocked"
    save(ctx, agent=agent, path=path)


def resolve_blocker(substr: str, resolution: str, agent: str, path: str = DEFAULT_CONTEXT_FILE) -> None:
    ctx = load(path)
    remaining = []
    for b in ctx.get("blockers", []):
        if substr.lower() in b.lower():
            ctx.setdefault("completed_work", []).append(f"[{agent} @ {_now()}] Resolved: {b} — {resolution.strip()}")
        else:
            remaining.append(b)
    ctx["blockers"] = remaining
    if not remaining and ctx.get("status") == "blocked":
        ctx["status"] = "in_progress"
    save(ctx, agent=agent, path=path)


def record_decision(agent: str, decision: str, rationale: str, alternatives: str, path: str = DEFAULT_CONTEXT_FILE) -> None:
    ctx = load(path)
    entry = f"[{_now()}] DECISION: {decision} | RATIONALE: {rationale} | ALTERNATIVES: {alternatives}"
    ctx.setdefault("decision_log", []).append(entry)
    save(ctx, agent=agent, path=path)


def set_artifact(key: str, value: str, agent: str = "system", path: str = DEFAULT_CONTEXT_FILE) -> None:
    ctx = load(path)
    ctx.setdefault("artifacts", {})[key.strip()] = value.strip()
    save(ctx, agent=agent, path=path)


def get_handoff_notes(path: str = DEFAULT_CONTEXT_FILE) -> str:
    return load(path).get("handoff_notes", "")


def set_handoff_notes(agent: str, notes: str, path: str = DEFAULT_CONTEXT_FILE) -> None:
    ctx = load(path)
    ctx["handoff_notes"] = notes.strip()
    save(ctx, agent=agent, path=path)


# --- Agent Decorator ---

def with_context(agent_name: str, path: str = DEFAULT_CONTEXT_FILE) -> Callable:
    """Decorator to auto-inject context and auto-persist results/blockers."""
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            ctx = load(path)
            ctx["_prompt"] = f"Objective: {ctx.get('objective')}\nFocus: {ctx.get('current_focus')}\nHandoff: {ctx.get('handoff_notes')}"
            sig = inspect.signature(fn)
            if "context" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                kwargs["context"] = ctx

            try:
                res = fn(*args, **kwargs)
                if isinstance(res, str):
                    append_completed(agent_name, res, path=path)
                    set_handoff_notes(agent_name, "", path=path)
                elif isinstance(res, dict):
                    if res.get("focus"):
                        set_focus(res["focus"], agent_name, path=path)
                    if res.get("blocker"):
                        add_blocker(agent_name, res["blocker"], path=path)
                    if res.get("artifacts"):
                        for k, v in res["artifacts"].items():
                            set_artifact(k, v, agent=agent_name, path=path)
                    if "handoff_notes" in res:
                        set_handoff_notes(agent_name, res["handoff_notes"], path=path)
                    out = res.get("output") or res.get("completed")
                    if out:
                        append_completed(agent_name, str(out), path=path)
                return res
            except Exception as e:
                add_blocker(agent_name, f"Error: {type(e).__name__}: {str(e)}", path=path)
                raise
        return wrapper
    return decorator
