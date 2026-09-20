"""
agent_context/test_context_store.py
Unit tests for the minimal context store.
"""

import os
import pytest
import sys

# Add agent_context to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from context_store import (
    load,
    save,
    append_completed,
    set_focus,
    add_blocker,
    resolve_blocker,
    record_decision,
    set_artifact,
    get_handoff_notes,
    set_handoff_notes,
    with_context,
    serialize,
)


@pytest.fixture
def temp_ctx(tmp_path):
    ctx_path = str(tmp_path / "CONTEXT.md")
    hist_path = str(tmp_path / "history")
    seed = {
        "version": 1,
        "workflow_id": "test-wf",
        "status": "planning",
        "objective": "Test objective statement",
        "current_focus": "Testing context store",
        "completed_work": ["[system @ 2026-09-19T12:00:00Z] — Seed task done"],
        "blockers": ["[system @ 2026-09-19T12:00:00Z] — Initial blocker"],
        "artifacts": {"key": "value"},
        "handoff_notes": "Initial note",
        "decision_log": ["[2026-09-19T12:00:00Z] DECISION: Test | RATIONALE: R | ALTERNATIVES: A"],
    }
    with open(ctx_path, "w", encoding="utf-8") as f:
        f.write(serialize(seed))
    return ctx_path, hist_path


def test_round_trip(temp_ctx):
    ctx_path, hist_path = temp_ctx
    state = load(ctx_path)
    assert state["version"] == 1
    assert state["objective"] == "Test objective statement"

    state["current_focus"] = "Updated focus"
    save(state, agent="tester", path=ctx_path, history_dir=hist_path)

    reloaded = load(ctx_path)
    assert reloaded["version"] == 2
    assert reloaded["current_focus"] == "Updated focus"
    assert len(os.listdir(hist_path)) == 1


def test_section_helpers(temp_ctx):
    ctx_path, _ = temp_ctx

    set_focus("New focus", agent="agent1", path=ctx_path)
    assert load(ctx_path)["current_focus"] == "New focus"

    append_completed("agent1", "Step 1 complete", path=ctx_path)
    assert any("Step 1 complete" in x for x in load(ctx_path)["completed_work"])

    add_blocker("agent1", "Network timeout on OCR endpoint", path=ctx_path)
    assert load(ctx_path)["status"] == "blocked"

    resolve_blocker("Network timeout", "Switched to local offline mode", agent="agent2", path=ctx_path)
    after_resolve = load(ctx_path)
    assert not any("Network timeout" in b for b in after_resolve["blockers"])
    assert any("Resolved:" in c for c in after_resolve["completed_work"])

    record_decision("lead", "Use SQLite", "Simple setup", "PostgreSQL", path=ctx_path)
    assert any("Use SQLite" in d for d in load(ctx_path)["decision_log"])

    set_artifact("model", "yolo-v8", path=ctx_path)
    assert load(ctx_path)["artifacts"]["model"] == "yolo-v8"

    set_handoff_notes("lead", "Check model next", path=ctx_path)
    assert get_handoff_notes(path=ctx_path) == "Check model next"


def test_objective_lock(temp_ctx):
    ctx_path, hist_path = temp_ctx
    state = load(ctx_path)
    state["objective"] = "Altered objective"

    with pytest.raises(ValueError, match="Objective is locked"):
        save(state, agent="rogue", path=ctx_path, history_dir=hist_path)

    # Allowed with rescope=True
    save(state, agent="pm", rescope=True, path=ctx_path, history_dir=hist_path)
    assert load(ctx_path)["objective"] == "Altered objective"


def test_decorator(temp_ctx):
    ctx_path, _ = temp_ctx

    @with_context(agent_name="worker", path=ctx_path)
    def simple_worker(context=None):
        assert "_prompt" in context
        return "Worker finished cleanly"

    simple_worker()
    state = load(ctx_path)
    assert any("Worker finished cleanly" in c for c in state["completed_work"])

    @with_context(agent_name="failing_worker", path=ctx_path)
    def crash():
        raise RuntimeError("Disk full")

    with pytest.raises(RuntimeError):
        crash()

    assert any("Disk full" in b for b in load(ctx_path)["blockers"])
