# Agent Context Store

A minimal, pragmatic shared context system for multi-agent workflows.

All agents share a single file: `agent_context/CONTEXT.md`. State survives across agent handoffs, subagent executions, and crashes.

---

## ⚡ Quick Usage

### 1. Decorate an Agent Function
Wrap any agent function with `@with_context`:

```python
from agent_context.context_store import with_context

@with_context(agent_name="ocr_agent")
def run_extraction(image_path: str, context=None):
    # 'context' dictionary is injected automatically
    print("Goal:", context["objective"])
    print("Focus:", context["current_focus"])
    
    # Return a string: auto-appends to Completed Work & clears handoff mailbox
    return f"Extracted declarations from {image_path}"

# Or return a dict for multi-field updates:
@with_context(agent_name="rule_agent")
def evaluate():
    return {
        "output": "Rules passed with 95% compliance",
        "focus": "Generate PDF report",
        "artifacts": {"report_pdf": "backend/reports/scan_1.pdf"},
        "handoff_notes": "PDF generator should sign the report next."
    }
```

If an unhandled exception occurs in your agent, the decorator catches it and logs it as an **Open Question / Blocker** in `CONTEXT.md` before re-raising.

---

### 2. Direct Updates

Update specific sections directly:

```python
import agent_context.context_store as cs

# Update what's being worked on
cs.set_focus("Refine packaging label OCR bounding boxes", agent="vision_agent")

# Log completed milestone
cs.append_completed("vision_agent", "Finished thresholding pipeline")

# Raise a blocker
cs.add_blocker("qa_agent", "Missing barcode scanner test samples")

# Resolve a blocker (logs resolution under Completed Work)
cs.resolve_blocker("barcode", "Added 5 sample images to sample_images/", agent="lead")

# Record architectural decisions
cs.record_decision("lead", "Use RapidOCR", "Eliminates system binary setup", "Tesseract binary")

# Store artifacts
cs.set_artifact("api_endpoint", "http://localhost:5000/api")
```

---

## 📁 Directory Layout

```
agent_context/
├── CONTEXT.md          # Active single source of truth
├── context_store.py    # Lightweight read/write library (~130 lines)
├── test_context_store.py # Pytest test suite
├── history/            # Auto-saved snapshots before each write
└── README.md           # This guide
```

## 🧪 Run Tests

```bash
pytest agent_context/test_context_store.py -v
```
