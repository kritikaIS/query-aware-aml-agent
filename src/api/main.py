"""FastAPI service — AML Suspicious Activity Detection Agent.

Reference: Solution Design §7, Implementation Plan §6.8.

DOCUMENTED REQUIREMENTS:
  - FastAPI backend exposing /query endpoint (§7)
  - POST /query accepting {"query": str} (§6.8 step 1)
  - Returns full ExecutionReport JSON (§6.8 step 1)
  - Raw-JSON response the judge can inspect (§6.8 step 3)

IMPLEMENTATION ASSUMPTIONS:
  - Host/port/CORS from api_config.yaml (not specified in docs).
  - Request validation (max length, non-empty) is good practice; not in docs.
  - /health endpoint for readiness checking; not in docs.
  - The API loads the synthetic dataset on startup and passes DataFrames
    to the AgentController. The docs say the Data Loader tool handles loading,
    but the API needs to provide the initial DataFrames per §4.3 Listing 3:
    run(user_query, df_transactions, df_customers). IMPLEMENTATION ASSUMPTION:
    pass None and let data_loader tool load from DATA_DIR at runtime.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from src.agent.controller import AgentController
from src.tools.registry import ToolRegistry
from src.tools.data_loader import data_loader
from src.tools.eda_tool import eda_tool
from src.tools.feature_engineering import feature_engineering
from src.tools.anomaly_detection import anomaly_detection
from src.tools.risk_classification import risk_classification
from src.tools.escalation import escalation
from src.tools.explanation import explanation


# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------

_API_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "api_config.yaml"
)


def _load_api_config() -> dict:
    with open(_API_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """DOCUMENTED: POST /query accepts {"query": str} (§6.8 step 1)."""

    query: str = Field(
        description="Natural language AML query.",
        min_length=1,
    )

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query must not be blank.")
        return v.strip()


class ErrorResponse(BaseModel):
    """Structured error response. IMPLEMENTATION ASSUMPTION."""
    status: str = "error"
    message: str
    detail: str | None = None


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def build_tool_registry() -> ToolRegistry:
    """Register all implemented tools.

    DOCUMENTED: ToolRegistry pattern (§3.1 principle 2, §4.3).
    Each tool registered under the name used in ExecutionPlan steps.
    """
    registry = ToolRegistry()
    registry.register("data_loader", data_loader)
    registry.register("eda_tool", eda_tool)
    registry.register("feature_engineering", feature_engineering)
    registry.register("anomaly_detection", anomaly_detection)
    registry.register("risk_classification", risk_classification)
    registry.register("escalation", escalation)
    registry.register("explanation", explanation)
    return registry


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    DOCUMENTED: FastAPI backend (§7).
    """
    cfg = _load_api_config()
    max_query_length = int(cfg.get("max_query_length", 2000))

    app = FastAPI(
        title=cfg.get("title", "AML Detection Agent"),
        description=cfg.get("description", ""),
        version=cfg.get("version", "1.0.0"),
    )

    # CORS — from config
    cors_origins = cfg.get("cors_origins", ["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Build tool registry and controller at startup
    registry = build_tool_registry()

    # LLM client: use if API key is configured
    # IMPLEMENTATION ASSUMPTION: None → DeterministicPlanner
    llm_client = _build_llm_client_if_configured()

    controller = AgentController(
        tool_registry=registry,
        llm_client=llm_client,
    )

    # -----------------------------------------------------------------------
    # POST /query — DOCUMENTED §6.8 step 1, §7
    # -----------------------------------------------------------------------

    @app.post("/query")
    async def query_endpoint(request: QueryRequest) -> JSONResponse:
        """Accept a natural language AML query and return the full ExecutionReport.

        DOCUMENTED: POST /query accepting {"query": str} → ExecutionReport JSON
        (§6.8 step 1, §7).

        Returns:
            JSON body containing the full ExecutionReport (§8 schema).
        """
        query_text = request.query
        if len(query_text) > max_query_length:
            raise HTTPException(
                status_code=400,
                detail=f"Query exceeds maximum length of {max_query_length} characters.",
            )

        start_time = time.time()
        try:
            # AgentController.run() — DOCUMENTED §4.3 Listing 3
            # Passes None for DataFrames; the data_loader tool loads from DATA_DIR.
            report = controller.run(
                user_query=query_text,
                df_transactions=None,
                df_customers=None,
            )

            elapsed_ms = round((time.time() - start_time) * 1000, 1)

            # Return the full ExecutionReport as JSON — DOCUMENTED §6.8 step 1
            report_dict = report.model_dump(mode="json")
            report_dict["_meta"] = {
                "elapsed_ms": elapsed_ms,
                "plan_id": report.execution_plan.plan_id,
                "tools_invoked": [s.tool for s in report.execution_plan.steps],
                "tools_skipped": [
                    {"tool": s.tool, "reason": s.reason}
                    for s in report.execution_plan.skipped_tools
                ],
            }
            return JSONResponse(content=report_dict, status_code=200)

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except KeyError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Tool not found in registry: {e}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Pipeline execution error: {type(e).__name__}: {e}",
            )

    # -----------------------------------------------------------------------
    # GET /health — IMPLEMENTATION ASSUMPTION (not documented)
    # -----------------------------------------------------------------------

    @app.get("/health")
    async def health_check() -> dict[str, Any]:
        """Readiness check. IMPLEMENTATION ASSUMPTION — not in documentation."""
        return {
            "status": "healthy",
            "registered_tools": registry.list_tools(),
            "llm_configured": llm_client is not None,
        }

    return app


def _build_llm_client_if_configured() -> Any:
    """Return an LLM client if ANTHROPIC_API_KEY is set, else None.

    IMPLEMENTATION ASSUMPTION: if API key is absent, returns None and the
    DeterministicPlanner is used. The LLM client interface matches §4.3.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    # Slot for real LLM client — not yet implemented.
    # DOCUMENTED §4.3: would implement extract_query_spec() and
    # build_execution_plan() here using the Anthropic Claude API.
    return None


# ---------------------------------------------------------------------------
# Application instance (importable by uvicorn)
# ---------------------------------------------------------------------------

app = create_app()
