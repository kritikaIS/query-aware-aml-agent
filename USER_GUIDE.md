# User Guide

This guide explains every screen of the AML Agent from an end-user perspective. No technical background is required.

---

## What is the AML Agent?

The AML Agent is a compliance tool that lets you ask questions about transaction data in plain English. You don't write SQL or configure rules — you just type what you want to know. The agent reads your question, decides which analysis tools to run, executes them, and shows you exactly what it did and why.

The key difference from a traditional dashboard: **you can see the agent's reasoning**. Which tools ran, which were skipped, and why — all visible before the results appear.

---

## Getting Started

Open the application in your browser. You will see the **Query Console** — a single large text input ready to receive your question.

---

## Screen 1 — Query Console

**What you see:** A dark screen with a centered command input, a "Run Query" button, and three quick-select chips at the bottom.

**What it does:** This is your entry point. Type any question about your transaction data, or click one of the pre-built chips.

### Quick-Select Chips

Three pre-built queries are available with one click:

| Chip | What it runs |
|---|---|
| **Analyse dataset** | Full exploratory analysis — all tools run |
| **10+ txns under $10k** | Rule-based detection of high-frequency near-threshold transactions |
| **Customer 4521 suspicious?** | Single-entity lookup and risk assessment |

These three queries demonstrate the full range of the agent's adaptive behaviour: broad analysis, rule-based detection, and entity-specific lookup.

### Typing Your Own Query

Examples of supported queries:

- `Find structuring patterns in the last 30 days`
- `Which customers made more than 5 transactions under $9,500?`
- `Is customer ID 7832 involved in layering?`
- `Show me high-velocity transactions from US customers`

Press **Enter** (without Shift) or click **Run Query ▸** to submit.

### While the Query Runs

Once submitted, the screen transitions automatically to the Plan Visualizer. The Run Query button shows a loading spinner — this means the backend is processing your query. Processing can take up to 90 seconds on large datasets.

---

## Screen 2 — Live Plan Visualizer

**What you see:** The submitted query shown at the top, followed by an intent summary, a progress indicator, and a row of tool cards.

**What it does:** This screen shows the agent building and executing its analysis plan in real time. You are watching the agent think.

### Intent Summary

Below the query you will see:

```
① Intent Parsed → pattern_detection · structuring
   filters: date_range = 2026-06-24 → 2026-07-24
```

This tells you what the agent understood from your question:
- **Intent** — what kind of analysis is being done (pattern detection, rule check, entity lookup, broad exploration)
- **AML pattern** — which money laundering pattern is being looked for, if any
- **Filters** — any date ranges, customer IDs, or other constraints extracted from your query

### Building Execution Plan Indicator

A pulsing indicator shows the plan being assembled. Once it disappears, the full plan is known and tools are executing.

### Tool Cards

Each tool the agent decided to run appears as a card in the pipeline:

| Card state | What it means |
|---|---|
| **Queued** — grey label | Tool will run after the current one finishes |
| **Running** — cyan border, progress bar | Tool is actively executing |
| **Done** — green tick | Tool completed successfully |
| **Skipped** — grey card, struck-through label | Tool was intentionally not run |
| **Error** — red border | Tool encountered a problem |

**Skipped tools are as important as active ones.** When a tool is skipped, the reason is printed directly on the card — for example:

> *EDA — SKIPPED*  
> "Query is pattern-targeted with explicit time filter; full-dataset profiling adds no value here."

This shows the agent exercised judgment, not just ran everything.

### Agent Reasoning Ticker

Below the pipeline, a collapsible section streams the agent's plain-language reasoning for the plan it chose. Click **▸** to expand it. Click anywhere on the text to skip the typewriter animation and see the full text immediately.

### Skip to Results

You can click **Skip to Results →** at any point to jump directly to the Results Dashboard, even while the plan is still running. The button turns cyan when the plan is fully complete.

---

## Screen 3 — Results Dashboard

**What you see:** Three KPI tiles at the top, a sortable entity table, two charts, and the Entity Risk Network.

**What it does:** This is the main output screen. It shows everything the agent found.

### Top Bar Summary

At the top: `◂ Plan · "your query" · N tools invoked · M skipped · [{ } View raw JSON]`

Click **◂ Plan** to return to the Plan Visualizer.  
Click **[{ } View raw JSON]** to open the JSON Inspector (see Screen 6).

### KPI Tiles

Three tiles show the headline numbers:

| Tile | What it shows |
|---|---|
| **N txns scanned** | Total transactions processed in this query's data slice |
| **N entities flagged** | Customers identified as potentially suspicious |
| **Risk split (donut)** | Breakdown of High / Medium / Low risk entities |

The numbers count up from zero when the screen first loads.

The **risk split donut** is interactive: click any coloured segment (red = High, amber = Medium, green = Low) to filter the entity table to that band only. Click the same segment again to clear the filter.

### Flagged Entities Table

Lists every flagged customer. Columns:

| Column | Description |
|---|---|
| **Risk** | Risk band badge — colour + icon + text (● High / ● Med / ● Low) |
| **Customer** | Customer ID |
| **Score** | Continuous risk score, 0–1 |
| **Pattern** | Detected AML pattern (structuring, smurfing, etc.) |
| **Action** | Recommended action (🔴 Report / 🟡 Review / 🟢 Monitor) |

**Sorting:** Click **Risk ▾** or **Customer ID** in the sort bar above the table to change the sort order.

**Row expansion:** Click any row to expand it inline. You will see:
- The explanation paragraph
- Top contributing feature names and z-scores
- Recommended action

**Open full detail:** Click **View full analysis ▸** within the expanded row, or click the **▸** arrow at the right of any row, to open the Entity Deep-Dive Drawer.

### Charts

Two charts sit below the entity table:

**Amount Distribution** — A bar chart showing how transaction amounts are distributed. A dashed vertical line marks the $10,000 reporting threshold. Bars just under that line (amber) indicate structuring clustering.

**Flagged Activity Timeline** — A scatter chart showing flagged transactions over time. Point size is proportional to transaction amount. Red points are near-threshold transactions; they may appear with a subtle halo to highlight concentration.

### Entity Risk Network

A force-directed graph showing all flagged customers as nodes:

- **Node size** — proportional to risk score
- **Node colour** — risk band (red = High, amber = Medium, green = Low)
- **Edges** — connect customers who were co-flagged for the same AML pattern

You can:
- **Drag nodes** to rearrange the layout
- **Scroll to zoom** in and out
- **Click Reset** (↺) to return to the default view
- **Filter by risk band** or AML pattern using the pills above the graph
- **Search** by customer ID to highlight a specific node
- **Click a node** to open the Entity Deep-Dive Drawer for that customer
- **Switch to table view** (☰) for an accessible list view of all nodes

---

## Screen 4 — Entity Deep-Dive Drawer

**What you see:** A panel that slides in from the right side over the Results Dashboard.

**What it does:** Shows full detail for a single flagged customer.

**How to open it:** Click the **▸** on any entity row, or click a node in the network graph.

**How to close it:** Click the **✕** button, press **Escape**, or click anywhere outside the panel.

### Contents

**Risk score gauge** — An SVG arc gauge that sweeps to the entity's score as the drawer opens. The colour matches the risk band.

**Customer metadata** — Customer ID, risk band badge, matched AML pattern.

**Top Contributing Features** — Horizontal bars showing which features most influenced the risk score. Each bar shows the raw value and z-score. Hover over (or tab to) any bar to see a description. Features are ordered from highest to lowest impact.

**Agent Explanation** — The plain-language paragraph generated by the AI, explaining why this customer was flagged. Numbers that also appear in the feature bars above are underlined, showing the AI restated measured facts rather than inventing them.

**Recommended Action** — One of:
- 🟢 **Monitor** — No immediate action; keep in watch list
- 🟡 **Flag for review** — Analyst review within SLA
- 🔴 **Report (SAR draft)** — Draft Suspicious Activity Report for compliance sign-off

---

## Screen 6 — Raw JSON Inspector

**What you see:** A panel that slides in from the right, showing the full `ExecutionReport` JSON.

**What it does:** Provides a complete, inspectable record of everything the agent did. Every number on every screen traces back to a line in this payload.

**How to open it:** Click **[{ } JSON]** in the top bar (available on Plan Visualizer and Results Dashboard), or click **[{ } View raw JSON ⧉]** in the Results Dashboard header.

**How to close it:** Click **✕**, press **Escape**, or click outside the panel.

### Toolbar

| Control | Action |
|---|---|
| Search box | Expands nodes whose key or value matches your search term |
| Expand ⊕ | Expands all nodes |
| Collapse ⊖ | Collapses all nodes to depth 1 |
| Copy JSON | Copies the entire JSON payload to the clipboard |

### Navigation

Click any key or value in the tree to copy its dot-notation path (e.g. `execution_plan.skipped_tools.0.reason`) to the clipboard. The current path is shown in the breadcrumb strip below the toolbar.

### Colour coding

| Colour | Means |
|---|---|
| Cyan | Object keys |
| Green | String values |
| Amber | Numeric values |
| Violet | Boolean values |

---

## Notifications

Toast notifications appear in the bottom-right corner:

| Toast colour | Meaning |
|---|---|
| 🔴 Red | Error — something went wrong |
| 🟡 Amber | Warning — backend unavailable, showing demo data |
| ✓ Green | Success |
| ℹ Blue | Informational |

Toasts dismiss automatically (8s for errors, 6s for warnings). Click **✕** to dismiss immediately.

---

## Keyboard Navigation

The entire application is operable without a mouse:

| Key | Action |
|---|---|
| `Tab` | Move between interactive elements |
| `Enter` / `Space` | Activate focused button or chip |
| `Enter` (in query input) | Submit query |
| `Shift + Enter` (in query input) | Insert new line |
| `Enter` (on entity row) | Expand / collapse accordion |
| `Escape` | Close open drawer or JSON inspector |
| `Tab` (in drawer) | Cycles through elements within the drawer only |
