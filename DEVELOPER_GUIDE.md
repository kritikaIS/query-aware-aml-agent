# Developer Guide

This guide explains how to understand, run, test, and extend the codebase.

---

## Prerequisites

- Python 3.11+
- Node.js 20+ and npm 10+
- An Anthropic API key (optional — the system works without one)
- Git

---

## Getting the Code Running in 5 Minutes

```bash
# 1. Backend
cd hackathon_project
pip install -r requirements.txt
cp .env.example .env
make dev                     # runs STUB_MODE=true, no LLM needed

# 2. Frontend (new terminal)
cd frontend
npm install
cp .env.example .env
npm run dev
# → http://localhost:5173
```

The backend runs on `http://localhost:8000`. The frontend Vite dev server proxies `/query` and `/health` to it automatically.

---

## Understanding the Codebase

### The Central Principle

This system makes one architectural decision that shapes everything: **the agent decides which tools to run, not the code.** There is no `if query_type == "structuring": run_structuring_tools()` anywhere. The planner — either deterministic or LLM-backed — produces an `ExecutionPlan` (a JSON list of tool names and arguments) and the `AgentController` walks it.

```python
for step in plan.steps:
    results[step.tool] = tool_fn(context, **step.args)
    context.update(results)   # results flow forward to later tools
```

This is the entire execution loop. Everything else is configuration.

### Backend — Where to Start

| File | Read this first |
|---|---|
| `src/schemas/` | The three Pydantic schemas are the data contract. Read them before anything else. |
| `src/agent/controller.py` | The orchestration loop — only ~150 lines. |
| `src/agent/planner.py` | How queries become plans. The `DeterministicPlanner` shows the logic explicitly. |
| `src/api/main.py` | The FastAPI app — two endpoints: `POST /query` and `GET /health`. |
| `src/tools/registry.py` | How tools are registered and looked up. |

### Frontend — Where to Start

| File | Read this first |
|---|---|
| `src/types/api.ts` | TypeScript mirror of the Python Pydantic schemas. This is the contract. |
| `src/stores/` | Five Zustand stores hold all application state. |
| `src/services/api/sse.ts` | How the frontend bridges the synchronous backend to the animated UI. |
| `src/hooks/useQuery.ts` | The main hook — ties query submission to all stores. |
| `src/App.tsx` | The root component — shows the SPA state machine. |

### The SSE Emulation Layer

The backend has **no streaming endpoint**. It runs the full pipeline and returns a JSON blob. The frontend emulates SSE by:

1. Receiving the full `ExecutionReport`
2. Building a synthetic event sequence (intent_parsed → tool_status × N → plan_complete → report_ready)
3. Firing each event with a staggered `setTimeout` (120ms apart)

This is in `src/services/api/sse.ts` — `emitSyntheticEvents()`. The Plan Visualizer animations are driven by these synthetic events, not by real-time backend events.

---

## Backend — Adding a New Tool

### Step 1 — Implement the tool function

Create `src/tools/my_tool.py`:

```python
from typing import Any

def my_tool(context: dict[str, Any], **kwargs) -> dict[str, Any]:
    """
    context keys available:
      context["transactions"]  — pandas DataFrame or None
      context["customers"]     — pandas DataFrame or None
      context["query_spec"]    — QuerySpec as dict
      context["data_loader"]   — data_loader result, if it ran before this tool
      ... (results of any tools that ran before this one)
    """
    # Your logic here
    return {
        "my_result_key": ...,
    }
```

### Step 2 — Register the tool

In `src/api/main.py`, inside `build_tool_registry()`:

```python
from src.tools.my_tool import my_tool

registry.register("my_tool", my_tool)
```

### Step 3 — Add tool configuration (optional)

Create `src/config/my_tool_config.yaml` for any thresholds or parameters.

### Step 4 — Update the planner

In `src/agent/planner.py`, inside `DeterministicPlanner.build_execution_plan()`, add a condition for when `my_tool` should be included:

```python
if some_condition(spec):
    if "my_tool" in self._registered_tools:
        steps.append(PlanStep(tool="my_tool", args={"param": value}))
```

### Step 5 — Write a unit test

```python
# tests/unit/test_my_tool.py
from src.tools.my_tool import my_tool

def test_my_tool_basic():
    context = {
        "transactions": small_dataframe,
        "customers": None,
        "query_spec": {},
    }
    result = my_tool(context)
    assert "my_result_key" in result
```

---

## Backend — Enabling the LLM

Currently `_build_llm_client_if_configured()` always returns `None`. To wire in a real Anthropic client:

1. Set `ANTHROPIC_API_KEY` in your `.env`
2. Implement `_build_llm_client_if_configured()` in `src/api/main.py` to return a client that implements:
   - `client.extract_query_spec(user_query: str) -> QuerySpec`
   - `client.build_execution_plan(spec: QuerySpec, tool_names: list[str]) -> ExecutionPlan`

The `AgentController` will use it automatically — no other changes needed.

---

## Frontend — Adding a New Screen

The application has three full screens (`query`, `plan`, `results`) driven by `uiStore.currentView`. To add a fourth screen:

### Step 1 — Add the view type

In `src/types/ui.ts`:

```typescript
export type AppView = 'query' | 'plan' | 'results' | 'my-screen'
```

### Step 2 — Create the feature directory

```
src/features/my-screen/
├── MyScreen.tsx
└── index.ts
```

### Step 3 — Wire into App.tsx

```tsx
import { MyScreen } from '@/features/my-screen'
// inside AnimatePresence:
{currentView === 'my-screen' && (
  <ErrorBoundary name="My Screen">
    <MyScreen />
  </ErrorBoundary>
)}
```

### Step 4 — Navigate to it

```typescript
const setView = useUiStore((s) => s.setView)
setView('my-screen')
```

---

## Frontend — Adding a New AML Component

AML-specific components live in `src/components/aml/`. They read from Zustand stores or receive data as props. They must not receive raw `ExecutionReport` directly — use the store or a typed adapter.

```tsx
// src/components/aml/MyAmlComponent.tsx
import React from 'react'
import { useReportStore } from '@/stores'
import { cn } from '@/utils'
import type { FlaggedEntity } from '@/types'

interface Props {
  entity: FlaggedEntity
}

export const MyAmlComponent: React.FC<Props> = ({ entity }) => {
  // Read from store if you need report-level data
  const report = useReportStore((s) => s.report)

  return (
    <div className="panel p-4">
      {/* Use design tokens via Tailwind classes, never hardcode hex */}
      <span className="text-text-primary font-mono">{entity.customer_id}</span>
    </div>
  )
}
```

Export it from `src/components/aml/index.ts`.

---

## Frontend — Adding to the Network Graph

The network visualization lives in `src/features/network/`. The `adapter.ts` converts `ExecutionReport` → `GraphData`. If you want new node types or edge types:

1. Extend `GraphNode` or `GraphEdge` in `adapter.ts`
2. Update `buildGraphData()` to populate the new fields
3. Update `NetworkCanvas.tsx` to render them

**Important:** Only add edges that can be derived from fields that actually exist in `ExecutionReport`. Do not invent backend fields. If you need additional relationship data (e.g. counterparty links), extend the backend schema first.

---

## Design System — Using Tokens

Always use Tailwind utility classes that reference CSS variables. Never hardcode hex values.

```tsx
// ✓ Correct
<div className="bg-bg-panel border border-border-hairline text-text-primary">

// ✗ Wrong
<div style={{ background: '#111826', color: '#E8ECF4' }}>
```

Available token classes: `bg-bg-void`, `bg-bg-panel`, `bg-bg-panel-raised`, `text-text-primary`, `text-text-secondary`, `border-border-hairline`, `text-accent-cyan`, `text-accent-violet`, `text-risk-high`, `text-risk-medium`, `text-risk-low`, `bg-skipped`.

---

## State Management Rules

1. **Never compute numbers in the frontend.** All values displayed come from `ExecutionReport`. No arithmetic, aggregation, or scoring in React components.

2. **Use stable action selectors in `useCallback` deps:**
   ```typescript
   // ✓ Correct — selects the stable action function
   const setReport = useReportStore((s) => s.setReport)
   // ✗ Wrong — store object is recreated every render
   const reportStore = useReportStore()
   ```

3. **Reset stores on new query.** `useQuery.submitQuery()` calls `.reset()` on all stores before starting a new request. This is intentional.

4. **Do not add loading spinners inside individual components.** Loading state is managed in `queryStore.status` and displayed at the screen level.

---

## Animation Rules

All animations must follow the motion token specification in `src/constants/index.ts`:

| Token | Duration | Used for |
|---|---|---|
| `MOTION.INSTANT` | 100ms | Hover states, focus rings |
| `MOTION.FAST` | 180ms | Card state changes, badge appear |
| `MOTION.BASE` | 300ms | Drawer slide-in, tab switches |
| `MOTION.SLOW` | 500ms | Plan pipeline assembly, chart entrance |

Rules:
- Never animate `width` or `top` directly. Use `scaleX`/`transform`/`opacity` only.
- The breathing pulse in `PlanningIndicator` is the **only** infinite animation.
- Always check `useReducedMotion()` and set `duration: 0` when it returns `true`.

---

## Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# A specific tool
pytest tests/unit/test_anomaly_detection.py -v

# Integration
pytest tests/integration/ -v
```

### Test Structure

| Directory | Tests |
|---|---|
| `tests/unit/` | Individual tool functions with hand-crafted fixture DataFrames |
| `tests/integration/` | Full pipeline execution with synthetic dataset |
| `tests/e2e/` | End-to-end query execution through the full stack |

### Writing a Unit Test

```python
# tests/unit/test_my_tool.py
import pandas as pd
from src.tools.my_tool import my_tool

def test_basic_case():
    txn = pd.DataFrame({
        "customer_id": ["C001", "C002"],
        "amount":      [9800.0, 5000.0],
        # ... other required columns
    })
    context = {
        "transactions": txn,
        "customers": None,
        "query_spec": {},
    }
    result = my_tool(context)
    assert isinstance(result, dict)
    # assert specific expected values
```

---

## Common Development Tasks

### View the API schema

```
http://localhost:8000/docs
```

### Check which tools are registered

```bash
curl http://localhost:8000/health | python -m json.tool
```

### Run the backend without starting uvicorn

```bash
python -m src.main
```

### Run TypeScript type check

```bash
cd frontend
npx tsc --noEmit
```

### Run the frontend linter

```bash
cd frontend
npm run lint
```

### Produce a production frontend build

```bash
cd frontend
npm run build
# Check output sizes:
ls -lah dist/assets/
```

### Add a new frontend dependency

```bash
cd frontend
npm install <package>@<version> --save
```

> Use exact or tightly pinned versions. Prefer well-maintained packages with TypeScript types.

---

## Configuration Files Reference

| File | Purpose |
|---|---|
| `src/config/api_config.yaml` | FastAPI host, port, CORS, max query length |
| `src/config/settings.py` | Environment variable → Python dataclass mapping |
| `src/config/column_mapping.yaml` | Maps source CSV column names to internal schema |
| `src/config/structuring_thresholds.yaml` | Near-threshold detection configuration |
| `src/config/velocity_config.yaml` | Velocity feature time buckets |
| `src/config/amount_deviation_config.yaml` | Amount deviation feature parameters |
| `src/config/ml_detection_config.yaml` | IsolationForest / LOF parameters |
| `src/config/statistical_detection_config.yaml` | Z-score / IQR thresholds |
| `src/config/risk_classification_config.yaml` | Percentile thresholds for band assignment |
| `src/config/escalation_policy.yaml` | Risk band → recommended action mapping |
| `src/config/explanation_config.yaml` | Explanation template configuration |
| `src/config/fx_rates.yaml` | Static FX rates for currency normalisation |
| `src/config/layering_config.yaml` | Layering pattern detection parameters |
| `frontend/tailwind.config.js` | Design token extension for Tailwind |
| `frontend/vite.config.ts` | Build config, path aliases, dev proxy, chunk splitting |

---

## Architecture Invariants

These are rules baked into the design that must be preserved when extending the system:

1. **The planner never touches raw data.** It receives only the query string and the tool name list.
2. **Tools are pure functions.** Each tool receives `context` and `**kwargs`, returns a dict, has no hidden state.
3. **The frontend never computes a number.** All displayed values come from `ExecutionReport`.
4. **Every skip is visible.** `ExecutionPlan.skipped_tools` must include a reason for every tool that was not run.
5. **The tool registry is the boundary.** The planner can only reference tool names that are registered. The `PlanValidator` enforces this.
6. **No hardcoded hex values in React components.** All colors come from CSS custom properties via Tailwind token classes.
