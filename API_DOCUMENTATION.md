# API Documentation

Base URL: `http://localhost:8000`

Interactive docs (Swagger UI): `http://localhost:8000/docs`  
ReDoc: `http://localhost:8000/redoc`

---

## Endpoints

### POST /query

Submit a natural-language AML query. The backend runs the full agent pipeline synchronously and returns a complete `ExecutionReport`.

**Request**

```
POST /query
Content-Type: application/json
```

**Request Body**

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| `query` | string | Yes | 1–2000 characters, not blank | Natural language AML query |

**Example Requests**

```json
{ "query": "Find structuring patterns in the last 30 days" }
```

```json
{ "query": "Which customers made 10+ transactions under $10,000?" }
```

```json
{ "query": "Is customer ID 4521 suspicious?" }
```

```json
{ "query": "Analyse this dataset for suspicious activity" }
```

---

**Response — 200 OK**

Returns the full `ExecutionReport` object plus a `_meta` field added by the API layer.

```json
{
  "user_query": "Find structuring patterns in the last 30 days",
  "query_spec": {
    "intent": "pattern_detection",
    "aml_pattern": "structuring",
    "filters": {
      "date_range": { "start": "2026-06-24", "end": "2026-07-24" },
      "customer_id": null,
      "segment": null,
      "country": null,
      "transaction_type": null
    },
    "explicit_rule": {
      "condition": null,
      "present": false
    },
    "requires_ml_anomaly_detection": true,
    "requires_full_eda": false
  },
  "execution_plan": {
    "plan_id": "plan_0091abcd",
    "reasoning": "Query targets a specific AML pattern (structuring) with a time filter; broad EDA unnecessary. Pattern-specific features and detection applied.",
    "steps": [
      { "tool": "data_loader",          "args": { "date_range": ["2026-06-24", "2026-07-24"] } },
      { "tool": "feature_engineering",  "args": { "feature_set": "structuring" } },
      { "tool": "anomaly_detection",    "args": { "method": "ml", "target_pattern": "structuring" } },
      { "tool": "risk_classification",  "args": { "scheme": "pattern_aware" } },
      { "tool": "escalation",           "args": {} },
      { "tool": "explanation",          "args": { "tie_to_query": true } }
    ],
    "skipped_tools": [
      {
        "tool": "eda_tool",
        "reason": "Query is pattern-targeted or entity-scoped; full-dataset profiling adds no value here."
      }
    ]
  },
  "flagged_entities": [
    {
      "customer_id": "4521",
      "risk_score": 0.87,
      "risk_band": "High",
      "aml_pattern_matched": "structuring",
      "top_contributing_features": [
        { "feature": "near_threshold_txn_count_7d", "value": 6.0, "z_score": 3.1 },
        { "feature": "avg_txn_amount_deviation",    "value": 2.4, "z_score": 2.4 }
      ],
      "explanation": "Customer 4521 made 6 deposits of $9,200–$9,800 within 7 days — just under the $10,000 reporting threshold, consistent with structuring.",
      "recommended_action": "Report (SAR draft)"
    }
  ],
  "summary_metrics": {
    "total_transactions_scanned": 48213,
    "entities_flagged": 17,
    "high_risk": 3,
    "medium_risk": 9,
    "low_risk": 5
  },
  "charts": [],
  "_meta": {
    "elapsed_ms": 1423.7,
    "plan_id": "plan_0091abcd",
    "tools_invoked": [
      "data_loader",
      "feature_engineering",
      "anomaly_detection",
      "risk_classification",
      "escalation",
      "explanation"
    ],
    "tools_skipped": [
      { "tool": "eda_tool", "reason": "Query is pattern-targeted..." }
    ]
  }
}
```

---

**Response Schema**

### `ExecutionReport`

| Field | Type | Description |
|---|---|---|
| `user_query` | string | The original query text |
| `query_spec` | `QuerySpec` | Parsed intent and filters |
| `execution_plan` | `ExecutionPlan` | The plan that was executed |
| `flagged_entities` | `FlaggedEntity[]` | Entities flagged as suspicious |
| `summary_metrics` | `SummaryMetrics` | Aggregate counts |
| `charts` | string[] | File paths to chart images (may be empty) |
| `_meta` | object | Added by API: elapsed_ms, plan_id, tools_invoked, tools_skipped |

### `QuerySpec`

| Field | Type | Values | Description |
|---|---|---|---|
| `intent` | string | `pattern_detection` `aggregation_rule` `entity_lookup` `broad_exploration` | Classified query intent |
| `aml_pattern` | string \| null | `structuring` `smurfing` `layering` `rapid_cashout` `null` | Detected AML pattern |
| `filters.date_range` | object \| null | `{ "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" }` | Date range filter |
| `filters.customer_id` | string \| null | | Specific customer ID filter |
| `filters.segment` | string \| null | | Customer segment filter |
| `filters.country` | string \| null | | Country filter |
| `filters.transaction_type` | string \| null | `deposit` `withdrawal` `transfer` `atm` | Transaction type filter |
| `explicit_rule.condition` | string \| null | | Rule expression (e.g. `count(transactions) >= 10 AND amount < 10000`) |
| `explicit_rule.present` | boolean | | Whether an explicit rule was detected |
| `requires_ml_anomaly_detection` | boolean | | Whether ML-based detection should be used |
| `requires_full_eda` | boolean | | Whether full EDA should be performed |

### `ExecutionPlan`

| Field | Type | Description |
|---|---|---|
| `plan_id` | string | Unique plan identifier |
| `reasoning` | string | Human-readable explanation of why this plan was chosen |
| `steps` | `PlanStep[]` | Ordered list of tool invocations |
| `skipped_tools` | `SkippedTool[]` | Tools intentionally excluded, each with a reason |

### `PlanStep`

| Field | Type | Description |
|---|---|---|
| `tool` | string | Registered tool name |
| `args` | object | Arguments passed to the tool |

### `SkippedTool`

| Field | Type | Description |
|---|---|---|
| `tool` | string | Skipped tool name |
| `reason` | string | Natural language explanation of why it was skipped |

### `FlaggedEntity`

| Field | Type | Description |
|---|---|---|
| `customer_id` | string | Customer identifier |
| `risk_score` | float | Continuous risk score, 0–1 |
| `risk_band` | string | `Low` `Medium` `High` |
| `aml_pattern_matched` | string \| null | Detected pattern name |
| `top_contributing_features` | `ContributingFeature[]` | Features that most influenced the score |
| `explanation` | string | Natural-language explanation |
| `recommended_action` | string | `Monitor` `Flag for review` `Report (SAR draft)` |

### `ContributingFeature`

| Field | Type | Description |
|---|---|---|
| `feature` | string | Feature name (e.g. `near_threshold_txn_count_7d`) |
| `value` | float | Raw feature value for this entity |
| `z_score` | float | Z-score relative to cohort |

### `SummaryMetrics`

| Field | Type | Description |
|---|---|---|
| `total_transactions_scanned` | integer | Total rows processed |
| `entities_flagged` | integer | Count of flagged entities across all bands |
| `high_risk` | integer | Count of High risk entities |
| `medium_risk` | integer | Count of Medium risk entities |
| `low_risk` | integer | Count of Low risk entities |

---

**Error Responses**

| Status | When | Body |
|---|---|---|
| `400 Bad Request` | Query is empty, blank, or exceeds 2000 characters | `{ "detail": "<message>" }` |
| `422 Unprocessable Entity` | Request body fails Pydantic validation (e.g. missing `query` field) | Standard FastAPI validation error |
| `500 Internal Server Error` | Tool not found in registry, or pipeline execution error | `{ "detail": "<error type>: <message>" }` |

**Example 400 — empty query**

```json
{ "detail": "query must not be blank." }
```

**Example 400 — query too long**

```json
{ "detail": "Query exceeds maximum length of 2000 characters." }
```

**Example 500 — tool error**

```json
{ "detail": "Pipeline execution error: KeyError: 'data_loader'" }
```

---

### GET /health

Check whether the backend is running and configured correctly.

**Request**

```
GET /health
```

No request body or parameters.

**Response — 200 OK**

```json
{
  "status": "healthy",
  "registered_tools": [
    "data_loader",
    "eda_tool",
    "feature_engineering",
    "anomaly_detection",
    "risk_classification",
    "escalation",
    "explanation"
  ],
  "llm_configured": false
}
```

| Field | Type | Description |
|---|---|---|
| `status` | string | Always `"healthy"` if the endpoint responds |
| `registered_tools` | string[] | Names of all tools registered in the tool registry |
| `llm_configured` | boolean | `true` if `ANTHROPIC_API_KEY` is set and non-empty |

---

## Plan Routing Logic

The deterministic planner selects tools based on detected query intent:

| Intent | Feature Eng | EDA | Anomaly Method | Notes |
|---|---|---|---|---|
| `broad_exploration` | ✓ | ✓ | statistical | Full pipeline |
| `pattern_detection` | ✓ (pattern-specific) | ✗ skipped | ml or statistical | EDA skipped with reason |
| `aggregation_rule` | ✗ skipped | ✗ skipped | rule_engine | Both skipped with reasons |
| `entity_lookup` | ✓ (entity-scoped) | ✗ skipped | statistical | Scoped to one customer |

## Registered Tool Names

Tools must be referenced by exactly these names in `ExecutionPlan.steps[].tool`:

| Name | Description |
|---|---|
| `data_loader` | Load and filter transaction/customer data |
| `eda_tool` | Exploratory data analysis |
| `feature_engineering` | Pattern-specific feature construction |
| `anomaly_detection` | Rule / statistical / ML anomaly scoring |
| `risk_classification` | Band assignment (Low/Medium/High) |
| `escalation` | Recommended action mapping |
| `explanation` | Natural-language explanation generation |
