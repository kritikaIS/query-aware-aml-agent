# AI-Powered Suspicious Activity Detection
## Frontend Design & Experience Specification

*The Judge-Facing Cockpit — Making the Agent's Reasoning Visible, Not Just Its Output*

**VIT Campus Hackathon — Problem Statement Response**
Companion document to: *Solution Design & Technical Architecture* · *Implementation Plan & Delivery Roadmap*

---

### Scope of this document

Visual design language, information architecture, screen-by-screen wireframes, component library, motion/animation system, chart and data-visualization specifications, responsive and accessibility rules, and the frontend technology stack for the judge-facing interface of the AML Suspicious Activity Detection Agent. This document translates the `ExecutionReport` JSON schema (Solution Design §8) into a polished, production-grade, story-telling interface — one whose entire job is to make an invisible thing (an LLM deciding what to run and why) visibly, dramatically inspectable.

---

## Table of Contents

1. [Purpose & Design Thesis](#1-purpose--design-thesis)
2. [Design Philosophy & Principles](#2-design-philosophy--principles)
3. [Information Architecture & Screen Map](#3-information-architecture--screen-map)
4. [Design System — Color, Type, Space](#4-design-system--color-type-space)
5. [Screen Specifications](#5-screen-specifications)
6. [Component Library](#6-component-library)
7. [Motion & Animation System](#7-motion--animation-system)
8. [Data Visualization Specifications](#8-data-visualization-specifications)
9. [Responsive Behaviour](#9-responsive-behaviour)
10. [Accessibility](#10-accessibility)
11. [Technology Stack & Frontend Architecture](#11-technology-stack--frontend-architecture)
12. [State Management & Data Flow](#12-state-management--data-flow)
13. [Performance Budget](#13-performance-budget)
14. [Traceability: Frontend to Problem Statement](#14-traceability-frontend-to-problem-statement)
15. [Conclusion](#15-conclusion)

---

## 1. Purpose & Design Thesis

The hard part of this problem statement was never "draw a dashboard." It's this line from the Solution Design: *"Everything the judge sees must be inspectable."* A judge scoring this system in five minutes needs to **see the agent think** — watch it read a query, decide what a fixed pipeline would never decide (skip EDA, skip ML, go straight to one customer), and justify that decision in plain language — before it ever shows them a single risk score.

So the frontend's job is not to visualize *results*. It's to visualize **reasoning, selectively, in motion** — and then land on results that feel earned rather than dumped.

**Design thesis in one line:** *a live control-room read-out of an agent's decision-making, styled like the compliance-desk software a Tier-1 bank would actually pay for — not a hackathon dashboard.*

---

## 2. Design Philosophy & Principles

1. **Reasoning before results.** The plan (tools chosen, tools skipped, why) is always shown *before* the report, and it animates in like a live process — never a static block dropped on screen.
2. **Command-center aesthetic, not consumer-app aesthetic.** Dark, dense-but-organized, data-forward. Think trading floor / SOC dashboard / Bloomberg terminal — not a SaaS landing page. Compliance officers trust screens that look serious.
3. **Nothing is decoration.** Every animation communicates a state change (a tool activating, a score resolving, a risk band being computed). Motion with no informational purpose is cut.
4. **Skipped is a first-class visual state**, not an absence. A greyed-out, struck-through tool card with a one-line reason is as important as an active one — it's the entire point of the rubric.
5. **Numbers are always traceable.** Every score, every chart value, links back visually (hover / click) to the tool call and raw payload that produced it — echoing the "numbers come from code" principle from the Solution Design.
6. **Progressive disclosure.** Summary view for the 30-second judge skim; drill-down for the judge who wants to interrogate a single flagged entity or the raw JSON.
7. **Fast, legible, quiet.** No parallax gimmicks, no autoplay video. Motion is snappy (150–500 ms), purposeful, and gets out of the way the second the judge wants to read.

---

## 3. Information Architecture & Screen Map

```
┌─────────────────────────────────────────────────────────────────┐
│                         APP SHELL                                │
│  Top Bar: logo · dataset status · env indicator · raw-JSON toggle│
└─────────────────────────────────────────────────────────────────┘
                 │
     ┌───────────┼─────────────────────────────┐
     ▼           ▼                             ▼
 ① QUERY      ② LIVE PLAN                  ③ RESULTS
 CONSOLE      VISUALIZER                   DASHBOARD
 (entry)      (agent "thinking" state)     (report render)
                                                 │
                                    ┌────────────┼────────────┐
                                    ▼            ▼            ▼
                            ④ ENTITY      ⑤ CHARTS &     ⑥ RAW JSON
                            DEEP-DIVE     METRICS RAIL   INSPECTOR
                            (drawer)      (side panel)   (slide-over)
```

**Navigation model:** single-page, state-driven (no route changes mid-query) — Query Console → Plan Visualizer → Results Dashboard is one continuous animated sequence, not three separate pages. This reinforces "the agent is one continuous reasoning act," matching the architecture it's representing. Deep-dive, chart rail, and JSON inspector are overlays/drawers so the judge never loses their place in the report.

---

## 4. Design System — Color, Type, Space

### 4.1 Color Palette — "Compliance Dark"

| Token | Hex | Usage |
|---|---|---|
| `--bg-void` | `#0A0E14` | App background |
| `--bg-panel` | `#111826` | Card / panel surface |
| `--bg-panel-raised` | `#161F30` | Elevated card (active tool, hovered row) |
| `--border-hairline` | `#232D42` | Card borders, dividers |
| `--text-primary` | `#E8ECF4` | Headings, primary values |
| `--text-secondary` | `#8B98B4` | Labels, captions, metadata |
| `--accent-cyan` | `#3ED6C4` | Agent "active thinking" accent, links, focus rings |
| `--accent-violet` | `#7C6CF6` | LLM/planning-related elements (distinguishes "reasoning" from "data") |
| `--risk-low` | `#2FBF71` | Low risk band |
| `--risk-medium` | `#F5B93D` | Medium risk band |
| `--risk-high` | `#F0473C` | High risk band |
| `--skipped-grey` | `#3A445C` | Skipped-tool cards, disabled states |

Risk colors are the **only** saturated warm/cool signal colors in the system — everything else stays desaturated navy/slate so that risk bands visually "pop" the instant they appear, exactly where the judge's eye should land.

### 4.2 Typography

| Role | Font | Weight/Size |
|---|---|---|
| Display / headings | **Inter** (or *Söhne* if licensed) | 600–700, 20–32px |
| Body / UI | **Inter** | 400–500, 13–15px |
| Data, IDs, JSON, scores | **JetBrains Mono** | 400–500, 12–14px |

Monospace is reserved strictly for *machine-generated values* (customer IDs, scores, timestamps, JSON) — this creates an instant visual grammar: **sans-serif = the system talking to you, monospace = raw fact you can verify.**

### 4.3 Spacing & Grid

- 8px base unit; 12-column responsive grid, 24px gutters on desktop.
- Panels use 1px hairline borders + very subtle inner shadow (glassmorphism kept minimal — a hint of blur on overlays only, never on data-bearing surfaces, so numbers stay crisp).

---

## 5. Screen Specifications

### 5.1 Query Console (Entry State)

```
┌───────────────────────────────────────────────────────────┐
│  AML AGENT · SUSPICIOUS ACTIVITY DETECTION      ● dataset✓ │
│                                                              │
│         "Ask the agent anything about this data."           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ ⌨  Find structuring patterns in the last 30 days      │  │
│  └─────────────────────────────────────────────────────┘  │
│                                            [ Run Query ▸ ]  │
│                                                              │
│  Try:  [Analyse dataset]  [10+ txns under $10k]  [Customer  │
│        4521 suspicious?]                                    │
└───────────────────────────────────────────────────────────┘
```

- Large, centered command input — cursor blinks with a soft cyan glow (`--accent-cyan`), reinforcing "you're talking to an agent," not filling out a form.
- Three quick-select chips pre-load the exact three reference queries from the Solution Design §9 demo plan — one click, judge sees the full range of adaptive behaviour without typing.
- Dataset status pill (top-right) shows row counts / freshness, pulled live from the Data Loader Tool — first proof the system is touching real data, not a mock.

### 5.2 Live Execution Plan Visualizer ("Agent is Thinking")

This is the signature screen — it did not exist in a "just show a dashboard" design, and it is the single highest-leverage screen for the rubric criterion *"agentic behaviour / dynamic planning."*

```
┌───────────────────────────────────────────────────────────┐
│ "Find structuring patterns in the last 30 days"             │
│                                                              │
│  ① Intent Parsed →  pattern_detection · structuring          │
│     filters: date_range = last 30d                          │
│                                                              │
│  ② Building execution plan...  ▓▓▓▓▓▓▓▓░░  reasoning...     │
│                                                              │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ 🟢 DATA     │ │ ⬜ EDA       │ │ 🟢 FEATURE  │ │🟢 DETECT │ │
│  │ LOADER      │ │ SKIPPED     │ │ ENGINEERING│ │ (hybrid) │ │
│  │ ✓ ready     │ │ "query      │ │ ▓▓▓▓░ 62%  │ │ queued   │ │
│  │             │ │ scoped —    │ │            │ │          │ │
│  │             │ │ full explore│ │            │ │          │ │
│  │             │ │ unneeded"   │ │            │ │          │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
│                                                              │
│  ┌────────────┐ ┌────────────┐                              │
│  │ 🟢 RISK     │ │ 🟣 EXPLAIN  │                              │
│  │ CLASSIFIER  │ │ (LLM)       │                              │
│  │ queued      │ │ queued      │                              │
│  └────────────┘ └────────────┘                              │
└───────────────────────────────────────────────────────────┘
```

- Tool cards render as a **left-to-right pipeline that is dynamically assembled**, not a fixed row that lights up — cards for skipped tools *appear greyed-out with a strikethrough label and their skip-reason visible without a click*. This is the literal visual encoding of "not a fixed sequential pipeline."
- Each active card shows a live progress bar and status chip (`queued → running → done`) driven by real backend events (SSE/WebSocket), not a fake timer.
- A collapsible **"Agent reasoning"** ticker beneath the header streams the planner's `reasoning` string token-by-token, typewriter-style — this is the only place a typewriter effect is used, reserved deliberately for genuine LLM output so it never feels gimmicky elsewhere.

### 5.3 Risk Report Dashboard (Results)

```
┌───────────────────────────────────────────────────────────┐
│ ◂ Query recap · plan summary · [View raw JSON ⧉]           │
│                                                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ 48,213      │ │ 17          │ │  3 🔴 9 🟡 5 🟢│            │
│  │ txns scanned│ │ entities    │ │ risk split    │            │
│  │             │ │ flagged     │ │  (donut)      │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│                                                              │
│  Flagged Entities                          sort: risk ▾     │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 🔴 HIGH  Customer 4521   score 0.87  structuring   ▸   │ │
│  │ 🟡 MED   Customer 2290   score 0.61  smurfing      ▸   │ │
│  │ 🟢 LOW   Customer 8813   score 0.22  —             ▸   │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────────────┐  ┌───────────────────────────┐   │
│  │ Amount distribution   │  │ Flagged activity timeline  │   │
│  │  (histogram + $10k    │  │  (scatter, near-threshold  │   │
│  │   threshold line)     │  │   clusters highlighted)    │   │
│  └──────────────────────┘  └───────────────────────────┘   │
└───────────────────────────────────────────────────────────┘
```

- KPI tiles count up from 0 on entry (see §7.3) — the only place counting-up animation is used, since these are the "proof of scale" numbers a judge scans first.
- The risk-split donut is clickable and cross-filters the flagged-entity table (click "High" → table filters to High only) — visualization as a control, not just a picture.
- Every row expands inline (accordion) before it ever opens the full Entity Deep-Dive drawer, so a judge can skim explanations without leaving the list.

### 5.4 Entity Deep-Dive (Drawer)

Triggered by `▸` on any row or by an entity-lookup query (e.g. *"Is customer ID 4521 suspicious?"*), sliding in from the right over a dimmed backdrop.

```
┌─────────────────────────────┐
│ Customer 4521          ✕    │
│ 🔴 HIGH · score 0.87         │
│                              │
│ Matched pattern: structuring │
│                              │
│ ┌─────────────────────────┐ │
│ │ Top contributing features │
│ │ near_threshold_txn_count  │
│ │  6  ▓▓▓▓▓▓▓░░ z=3.1       │
│ │ avg_amount_deviation      │
│ │  2.4 ▓▓▓▓▓░░░░ z=2.4      │
│ └─────────────────────────┘ │
│                              │
│ "Customer 4521 made 6        │
│  deposits of $9,200–$9,800   │
│  within 7 days — just under  │
│  the $10,000 reporting       │
│  threshold, consistent with  │
│  structuring."               │
│                              │
│ Recommended: 🔴 Report        │
│ (SAR draft)        [Export ⬇]│
└─────────────────────────────┘
```

- Feature bars are horizontal, z-score labeled, and directly hoverable to reveal the exact underlying transaction rows — this is the "traceability" principle made literal and clickable.
- The explanation paragraph highlights (subtle underline, no color change) every number that also appears in a chart or feature bar above it, visually proving the LLM restated facts rather than inventing them.

### 5.5 Raw JSON Inspector (Slide-over)

A monospace, syntax-highlighted, collapsible tree view of the exact `ExecutionReport` object (Solution Design §8) behind everything the judge just saw — one click from anywhere in the app. This is the ultimate trust mechanism: nothing shown in the pretty UI has no corresponding line in this payload.

---

## 6. Component Library

| Component | States | Notes |
|---|---|---|
| `<ToolCard>` | queued · running · done · skipped · error | Skipped state always shows reason text, no hover required |
| `<RiskBadge>` | low · medium · high | Color + icon, never color alone (see §10) |
| `<PlanReasoningTicker>` | streaming · complete | Typewriter reveal, pausable |
| `<KpiTile>` | loading · counted-up | Count-up animation on mount only |
| `<EntityRow>` | collapsed · expanded | Accordion, keyboard-navigable |
| `<FeatureBar>` | — | Horizontal bar + z-score label, hoverable |
| `<RiskDonut>` | default · filtered | Click segment = cross-filter table |
| `<ThresholdHistogram>` | — | Reference line for regulatory threshold (e.g. $10,000) |
| `<TimelineScatter>` | — | Density-highlighted near-threshold clusters |
| `<JsonTree>` | collapsed/expanded per node | Search + copy-path on hover |
| `<StatusPill>` | dataset states | Top bar dataset/env indicator |

All components are built as isolated, storybook-documented units so WS-6 (front-end) can develop against the frozen `ExecutionReport` schema before backend integration, per the Implementation Plan's parallelization strategy.

---

## 7. Motion & Animation System

Motion is treated as a **specification**, not a vibe — every animation below has a fixed duration, easing curve, and trigger, so it reads as "engineered," not "decorated."

### 7.1 Motion Tokens

| Token | Duration | Easing | Used for |
|---|---|---|---|
| `motion-instant` | 100ms | `ease-out` | Hover states, focus rings |
| `motion-fast` | 180ms | `cubic-bezier(0.2, 0, 0, 1)` | Card state changes, badge appear |
| `motion-base` | 300ms | `cubic-bezier(0.2, 0, 0, 1)` | Drawer/panel slide-in, tab switches |
| `motion-slow` | 500ms | `ease-in-out` | Plan pipeline assembly, chart entrance |
| `motion-stream` | 20–35ms/char | linear | Reasoning ticker typewriter |

### 7.2 Signature Sequences

1. **Plan assembly:** tool cards fade+slide up (`motion-slow`, 60ms stagger) left-to-right in the exact order the planner decided — the *order itself* is the information, so stagger direction is never randomized.
2. **Skip reveal:** a skipped card doesn't just appear grey — it briefly appears in full color, then desaturates and strikes through over 250ms, so the judge perceives "this *was* considered, and *then* rejected," not "this was never an option."
3. **Score resolution:** risk badges resolve via a short (400ms) circular progress sweep that fills to the final score before snapping to Low/Medium/High color — visually says "this number was computed," not "this number was pasted in."
4. **Count-up KPIs:** ease-out count from 0 → final value over 600ms, only on first mount, never on re-render (prevents nervous, twitchy UI on re-filter).
5. **Reasoning ticker:** true typewriter at `motion-stream` rate, skippable on click (jumps to full text) — respects judges who read faster than the animation.

### 7.3 Motion Restraint Rules

- No animation loops indefinitely except a single slow (2.4s) breathing pulse on the "agent is actively planning" indicator — everything else runs once and rests.
- No motion blocks interaction: a judge can click "skip to results" at any point during the plan animation and jump straight to §5.3.
- `prefers-reduced-motion` disables stagger/typewriter/count-up entirely in favor of instant, final-state rendering (see §10).

---

## 8. Data Visualization Specifications

| Chart | Library | Purpose | Key encoding decision |
|---|---|---|---|
| Risk split donut | Recharts / Plotly | Portfolio-level risk composition | Fixed color mapping (low/med/high) never changes across screens |
| Amount distribution histogram | Plotly | Show clustering just under reporting threshold | Vertical reference line at $10,000 with label, always visible |
| Flagged activity timeline (scatter) | D3 / Plotly | Show velocity/burst patterns over time | Point size = transaction amount; near-threshold points get a subtle halo |
| Feature contribution bars | Custom (SVG) | Explainability per entity | Bar length = magnitude, label = raw z-score, not just "high/low" |
| Execution plan pipeline | Custom (SVG/Framer Motion) | Show dynamic tool graph | Node order = execution order; edges only drawn between tools that actually ran in sequence |
| Smurfing network graph (stretch) | D3 force-directed | Show fan-out from one source to many receiving accounts | Node size = txn count; only rendered when `aml_pattern_matched == "smurfing"` |

All charts share one **design contract**: risk-band colors are never reused for anything else in the palette, axis labels are always in `--text-secondary`, and every chart exposes a hover tooltip that cites the exact source row/feature — closing the loop back to the raw JSON inspector.

---

## 9. Responsive Behaviour

- **Desktop (≥1280px):** full multi-column dashboard as specified above — this is the primary judging surface (demo laptop/projector).
- **Tablet (768–1279px):** tool-pipeline row becomes horizontally scrollable with snap points; charts stack to single column; KPI tiles go 2×2.
- **Mobile (≤767px):** treated as a "read-only recap" mode — Query Console and Entity Deep-Dive remain fully usable; the live plan visualizer collapses to a vertical timeline instead of a horizontal pipeline, since side-scrolling six cards on a phone defeats the "see it all at once" purpose.

---

## 10. Accessibility

- **Color is never the only signal.** Every risk badge pairs color with an icon and text label (`● High`, not just a red dot); every skipped tool has a strikethrough *and* a text reason, not just greyscale.
- **Contrast:** all text/background pairs meet WCAG AA (4.5:1) against `--bg-panel`; risk colors were selected and adjusted specifically to pass AA on dark backgrounds rather than taken from a default palette.
- **Keyboard:** full app is operable without a mouse — query input → run → tab through tool cards → tab through entity rows → Enter opens deep-dive drawer → Esc closes.
- **Screen readers:** the reasoning ticker's `aria-live="polite"` region announces plan decisions as they stream; skip-reason text is always in the accessibility tree even when visually a tooltip.
- **`prefers-reduced-motion`:** disables stagger, typewriter, and count-up animations; all UI still fully functional with instant-final-state rendering (§7.3).

---

## 11. Technology Stack & Frontend Architecture

| Layer | Choice | Rationale |
|---|---|---|
| Framework | **React + Vite** (TypeScript) | Fast dev loop, matches Solution Design §7's "React front-end" option, avoids Streamlit's animation ceiling |
| Styling | **Tailwind CSS** + CSS variables for the design tokens in §4 | Utility speed without losing a real design system |
| Motion | **Framer Motion** | Declarative, interruptible animations for §7's sequences |
| Charts | **Recharts** (KPI/donut/bars) + **Plotly.js** (histogram/scatter, matches backend export format in Solution Design §7) | Reuses the same chart grammar the backend already exports |
| Live plan updates | **Server-Sent Events** from FastAPI `/query` (streaming) | Simpler than WebSockets for a one-directional plan/status feed; falls back to polling if SSE blocked on the demo network |
| State | **Zustand** (lightweight) for query/report/UI state | Avoids Redux boilerplate for a hackathon timeline while staying testable |
| JSON tree / inspector | `react-json-view` (themed to match §4 palette) | Fast to integrate, satisfies "judge-inspectable" requirement immediately |
| Icons | **Lucide** | Consistent line-icon set matching the command-center aesthetic |

**Build/run:** ships inside the same `docker-compose up` / `make dev` described in the Implementation Plan §8, so the frontend is never a separate setup step during judging.

---

## 12. State Management & Data Flow

```
User types/selects query
        │
        ▼
[QueryConsole] --POST /query (stream=true)--> FastAPI
        │                                         │
        │  SSE: intent_parsed                     ▼
        │  SSE: tool_status(tool, state, reason)  Orchestrator Agent
        │  SSE: plan_complete                     (as in Solution Design §4)
        │  SSE: report_ready(ExecutionReport)      │
        ▼                                          ▼
[PlanVisualizer] renders tool cards live  <────────┘
        │
        ▼  on report_ready
[ResultsDashboard] hydrates from ExecutionReport (single source of truth)
        │
        ├──▸ [EntityDeepDive] reads a slice of the same object (no refetch)
        └──▸ [JsonInspector] renders the same object verbatim
```

One principle carried over directly from the backend design: **the frontend never computes a number.** Every value on screen — score, count, percentage, chart datum — is read straight from the `ExecutionReport` payload, never derived client-side. This mirrors the Solution Design's "numbers come from code, words come from the LLM" rule and keeps the UI itself auditable.

---

## 13. Performance Budget

| Metric | Target | Why |
|---|---|---|
| Query Console → first plan card visible | < 800ms | Judge should never wonder if the click registered |
| Full plan animation (all tool cards) | ≤ 3s total | Long enough to read, short enough not to stall a live demo |
| Results Dashboard render after `report_ready` | < 300ms | Charts/table hydrate from already-fetched JSON, no extra round-trip |
| Bundle size (initial) | < 350KB gzipped | Fast load on venue Wi-Fi; charts code-split and lazy-loaded |
| Animation frame budget | 60fps, no layout thrash | All motion uses `transform`/`opacity` only, never animates `width`/`top` directly |

---

## 14. Traceability: Frontend to Problem Statement

| Problem Statement / Recommended Output | Where the Frontend Delivers It |
|---|---|
| Query-aware execution summary: request, filters/entities, tools invoked | §5.2 Live Execution Plan Visualizer |
| Top suspicious transactions/customers from the selected path | §5.3 Flagged Entities table |
| Risk level for each flagged item | `<RiskBadge>` component, §6, color contract §8 |
| Explanation tied to query intent and AML pattern | §5.4 Entity Deep-Dive explanation panel |
| Suggested escalation action (monitor/review/report) | §5.4 Recommended action row |
| Supporting charts/tables/metrics for reviewer confidence | §5.3 KPI tiles + §8 chart set |
| Judge-inspectable structured output ("what the agent decided and why") | §5.5 Raw JSON Inspector + skip-reason visibility throughout §5.2 |
| Agent must not follow a fixed sequential pipeline (visibly) | §7.2 Signature Sequence 1–2 (assembly order + skip reveal animation) |

---

## 15. Conclusion

This specification treats the frontend as the *proof artifact* for the entire agentic architecture, not a coat of paint on top of it. Every screen, color rule, and animation timing above exists to answer one judge-facing question as fast and as trustworly as possible: **"Did this agent actually decide something, or did it just run everything and hide the pipeline behind a dashboard?"** By making planning, skipping, and scoring all individually visible, animated in their true execution order, and traceable down to the same raw JSON payload the backend produces, the interface itself becomes evidence for the "agentic, not pipeline" claim at the center of the Solution Design — production-grade in craft, and honest in what it shows.
