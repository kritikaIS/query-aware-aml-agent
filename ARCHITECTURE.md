# Architecture

## Overview

The system is a full-stack, query-aware AML compliance tool. Its central design principle is that the agent decides *what to run* based on each natural-language query, rather than executing a fixed pipeline every time. Every decision — which tools to invoke, which to skip, and why — is surfaced in a live animated interface and a fully inspectable JSON payload.

```
User (browser)
      │  natural language query
      ▼
React Frontend (Vite, port 5173)
      │  POST /query  →  ExecutionReport JSON
      ▼
FastAPI Backend (Python, port 8000)
      │
      ├── AgentController
      │     ├── Step 1: DeterministicPlanner (or LLM) → QuerySpec
      │     ├── Step 2: DeterministicPlanner (or LLM) → ExecutionPlan
      │     └── Step 3: Tool execution loop → results dict
      │           ├── data_loader
      │           ├── eda_tool (optional)
      │           ├── feature_engineering
      │           ├── anomaly_detection
      │           ├── risk_classification
      │           ├── escalation
      │           └── explanation
      │
      └── ExecutionReport JSON (returned to frontend)
```

---

## Backend Architecture

### Entry Point

`src/api/main.py` — creates the FastAPI application via `create_app()`. The app is importable as `src.api.main:app` for uvicorn.

### Tool Registry (`src/tools/registry.py`)

A simple `name → callable` mapping. All seven tools register at app startup. The planner is constrained to only reference registered tool names.

### AgentController (`src/agent/controller.py`)

Implements the documented orchestration loop:

```python
spec    = planner.extract_query_spec(user_query)   # Step 1
plan    = planner.build_execution_plan(spec)        # Step 2

context = { "transactions": ..., "customers": ..., "query_spec": ... }
for step in plan.steps:
    results[step.tool] = tool_fn(context, **step.args)
    context.update(results)   # results flow forward

return assemble_report(user_query, spec, plan, results)
```

### Planning (`src/agent/planner.py`)

Two planning paths, behind an identical interface:

- **DeterministicPlanner** (default when `ANTHROPIC_API_KEY` is absent): Rule-based keyword extraction produces `QuerySpec`; deterministic tool selection produces `ExecutionPlan`. Used for testing, demos without LLM access.
- **LLM path** (when `ANTHROPIC_API_KEY` is set): The slot exists in `AgentController._extract_query_spec()` and `_build_execution_plan()` but the Anthropic client is not yet wired in — the API returns `None` from `_build_llm_client_if_configured()`.

**PlanValidator** checks every plan against the registered tool list and falls back to a safe default plan (all tools, EDA included) on validation failure.

### Tools (`src/tools/`)

| Tool | Purpose |
|---|---|
| `data_loader` | Load and filter `transactions.csv` / `customers.csv` from `DATA_DIR` |
| `eda_tool` | Broad exploratory profiling; only invoked for `broad_exploration` intent |
| `feature_engineering` | Pattern-specific feature families (structuring, velocity, deviation, layering) |
| `anomaly_detection` | Rule engine, statistical (z-score/IQR), or ML-based (IsolationForest/LOF) |
| `risk_classification` | Maps anomaly scores to Low/Medium/High bands with percentile thresholds |
| `escalation` | Deterministic policy: band → Monitor / Flag for review / Report (SAR draft) |
| `explanation` | Generates natural-language explanation grounded in computed numeric facts |

### Schemas (`src/schemas/`)

Three Pydantic v2 models define the data contract:

- `QuerySpec` — parsed intent, AML pattern, filters, rule flags
- `ExecutionPlan` — ordered steps + skipped tools with reasons
- `ExecutionReport` — the complete result: query, spec, plan, flagged entities, metrics

### Configuration (`src/config/`)

- `settings.py` — `Settings` dataclass, reads from environment variables
- `api_config.yaml` — host, port, CORS, max query length
- Per-tool YAML files — thresholds, model parameters, column mappings, FX rates

---

## Frontend Architecture

### Application Shell

The frontend is a single-page application. There are no URL routes. Navigation between screens is driven purely by `uiStore.currentView` ('query' | 'plan' | 'results').

```
AppShell (layout wrapper)
├── TopBar           — logo, dataset pill, env label, JSON toggle
├── AnimatePresence  — page transition wrapper
│   ├── Screen ①: QueryConsole
│   ├── Screen ②: PlanVisualizer
│   └── Screen ③: ResultsDashboard
├── EntityDrawer     — overlay, Screen ④
├── JsonInspector    — overlay, Screen ⑥
└── ToastContainer   — notification layer
```

### Design System

All visual tokens live in `src/styles/tokens.css` as CSS custom properties. Tailwind is configured to reference these variables — no hex values exist in component files. The theme is called "Compliance Dark".

Key tokens:
- `--bg-void` `#0A0E14` — page background
- `--accent-cyan` `#3ED6C4` — active/focus accent
- `--accent-violet` `#7C6CF6` — LLM/reasoning elements
- `--risk-high/medium/low` — the only saturated signal colors

### State Management — Zustand Stores

| Store | Holds |
|---|---|
| `queryStore` | submitted query text, loading status (`idle/submitting/streaming/complete/error`) |
| `plannerStore` | querySpec, toolCards[], executionPlan, reasoningText, isPlanning flag |
| `reportStore` | ExecutionReport (single source of truth), risk filter, sort config |
| `uiStore` | currentView, drawer state, JSON inspector open, toast queue |
| `datasetStore` | dataset loaded status, row count, freshness date |

### API Integration (`src/services/api/`)

The backend `POST /query` is synchronous — it runs the full pipeline and returns a complete `ExecutionReport`. There is no real SSE endpoint.

The frontend emulates SSE by:
1. Calling `POST /query` and waiting for the full response
2. Deriving a sequence of synthetic events from the `ExecutionReport`
3. Firing those events with staggered `setTimeout` delays (120ms per tool)

This drives the Plan Visualizer animations without requiring any backend changes.

**Fallback chain:**
1. `connectSse()` — POST /query + synthetic event sequence
2. `pollQuery()` — POST /query with single `report_ready` event (retry path)
3. Mock data — populated when backend is unreachable after 2 retries

### Custom Hooks

| Hook | Purpose |
|---|---|
| `useQuery` | Submits a query, manages the full request lifecycle, populates all stores |
| `useCountUp` | Animates a number from 0 to a target value on mount (KPI tiles) |
| `useTypewriter` | Streams text character by character (reasoning ticker) |
| `useReducedMotion` | Detects `prefers-reduced-motion`, disables all animations |

---

## Data Flow

```
QueryConsole: user types or clicks chip
        │
        ▼
useQuery.submitQuery(text)
  resets all stores
  sets queryStore.status = 'submitting'
  sets uiStore.currentView = 'plan'
        │
        ▼
connectSse(query)
  → POST /query to backend (synchronous, up to 90s timeout)
        │
        ▼  (response received)
emitSyntheticEvents(report)
  fires in order with ~120ms gaps:
    intent_parsed  → plannerStore.setQuerySpec()
    tool_status × N (running/done) → plannerStore.upsertToolCard()
    tool_status × M (skipped)      → plannerStore.upsertToolCard()
    plan_complete  → plannerStore.setExecutionPlan()
    report_ready   → reportStore.setReport()
                     uiStore.setView('results')
        │
        ▼
ResultsDashboard renders from reportStore.report
EntityDrawer reads reportStore.report.flagged_entities
JsonInspector renders reportStore.report verbatim
```

The frontend never derives or computes a number — all values displayed come directly from the `ExecutionReport` payload.

---

## Store Architecture

```
uiStore
├── currentView: 'query' | 'plan' | 'results'
├── drawer: { open, entityId }
├── jsonInspectorOpen: boolean
├── toasts: ToastMessage[]
└── skipToResults: boolean

queryStore
├── submittedQuery: string | null
└── status: 'idle' | 'submitting' | 'streaming' | 'complete' | 'error'

plannerStore
├── querySpec: QuerySpec | null
├── toolCards: ToolCardModel[]  ← populated event by event
├── executionPlan: ExecutionPlan | null
├── reasoningText: string
└── isPlanning: boolean

reportStore
├── report: ExecutionReport | null  ← single source of truth
├── riskFilter: 'all' | 'High' | 'Medium' | 'Low'
├── sortConfig: { field, direction }
└── getFilteredEntities(): FlaggedEntity[]  ← computed on read

datasetStore
└── status: { loaded, rowCount, freshness }
```

---

## Component Hierarchy

```
App
└── AppShell
    ├── TopBar
    │   ├── StatusPill (dataset)
    │   └── JSON toggle button
    ├── AnimatePresence
    │   ├── ErrorBoundary "Query Console"
    │   │   └── QueryConsole
    │   │       ├── QueryInput (textarea, cyan glow)
    │   │       ├── RunButton
    │   │       └── QueryChip × 3
    │   │
    │   ├── ErrorBoundary "Plan Visualizer"
    │   │   └── PlanVisualizer
    │   │       ├── QuerySummary (intent parsed row)
    │   │       ├── PlanningIndicator (breathing pulse)
    │   │       ├── ToolPipeline
    │   │       │   ├── ToolCard × N (queued/running/done/skipped/error)
    │   │       │   │   ├── ToolStatusBadge
    │   │       │   │   └── ToolProgressBar
    │   │       │   └── PipelineConnector × N-1
    │   │       ├── ExecutionTimeline
    │   │       └── PlanReasoningTicker (typewriter)
    │   │
    │   └── ErrorBoundary "Results Dashboard"
    │       └── ResultsDashboard
    │           ├── SummaryHeader (◂ back, JSON toggle)
    │           ├── KpiTile × 3 (count-up animation)
    │           ├── RiskDonut + DonutLegend (Recharts)
    │           ├── FilterBar
    │           ├── FlaggedEntitiesTable
    │           │   └── EntityRow × N (accordion)
    │           │       └── RiskBadge
    │           ├── MetricsRail
    │           │   ├── ThresholdHistogram (Plotly)
    │           │   └── TimelineScatter (Plotly)
    │           └── TransactionNetwork
    │               ├── NetworkCanvas (D3, lazy-loaded)
    │               ├── NetworkControls
    │               ├── NetworkFilters
    │               ├── NetworkLegend
    │               ├── NetworkSearch
    │               └── NetworkTableView (accessible fallback)
    │
    ├── ErrorBoundary "Entity Drawer"
    │   └── EntityDrawer (Screen ④)
    │       ├── RiskScoreGauge (SVG arc)
    │       ├── CustomerMetadata
    │       ├── FeatureContributionList
    │       │   └── FeatureBar × N (scaleX animation)
    │       ├── ExplanationPanel (number underline tracing)
    │       └── RecommendedActionCard
    │
    ├── ErrorBoundary "JSON Inspector"
    │   └── JsonInspector (Screen ⑥)
    │       ├── JsonToolbar (search, copy, expand/collapse)
    │       ├── JsonBreadcrumb (node path)
    │       └── JsonViewer (react-json-view, lazy-loaded)
    │
    └── ToastContainer
```

---

## Network Visualization Architecture

The Entity Risk Network (`src/features/network/`) is an independent feature that never directly consumes `ExecutionReport`.

```
ExecutionReport (from reportStore)
        │
        ▼
buildGraphData(report) → GraphData
  nodes: one per flagged_entity
    - id       = customer_id
    - radius   = 8 + 16 × risk_score  (8–24px)
    - color    = risk_band color token
    - pattern  = aml_pattern_matched
  edges: inferred co-occurrence (star topology per pattern group)
    - source / target = customer_ids in the same pattern group
    - relationship = "co-flagged: {pattern}"
        │
        ▼
filterGraphData(data, { riskBand, pattern }) → filtered GraphData
        │
        ▼
NetworkCanvas (lazy Suspense)
  D3 force simulation (dynamic import inside useEffect)
    forceLink    — edge attraction (distance 90, strength 0.4)
    forceManyBody — repulsion (-220)
    forceCenter  — centres on (0, 0)
    forceCollide — prevents overlap (radius + 6)
  SVG rendered with zoom/pan/drag via d3-zoom + d3-drag
  ResizeObserver (100ms debounced) for responsive canvas
```

**Edge semantics:** Edges connect customers co-flagged for the same AML pattern in the same detection run. They do not represent direct transaction relationships between customers. This is stated clearly in the footer of the network panel.

---

## API Flow

```
Browser                    FastAPI (port 8000)
  │                              │
  │── POST /query ───────────────►│
  │   { "query": "..." }          │
  │                              ├── validate request (max 2000 chars)
  │                              ├── extract_query_spec() → QuerySpec
  │                              ├── build_execution_plan() → ExecutionPlan
  │                              │   (validates against registry; fallback if invalid)
  │                              ├── for step in plan.steps:
  │                              │     tool_fn(context, **args)
  │                              │     context.update(results)
  │                              └── assemble ExecutionReport
  │◄── 200 JSON ─────────────────│
  │   ExecutionReport + _meta     │
  │                              │
  │── GET /health ───────────────►│
  │◄── 200 JSON ─────────────────│
  │   { status, registered_tools, llm_configured }
```

The backend is fully synchronous. The frontend emulates streaming by deriving a sequence of UI events from the completed response.
