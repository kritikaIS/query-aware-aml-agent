"""Application settings — loaded from environment variables.

Reference: Implementation Plan §8 (Deployment & Demo Environment Plan).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Application configuration loaded from environment.

    Attributes:
        anthropic_api_key: API key for Claude (required for Phase 2+).
        model_name: Claude model identifier for planning/extraction calls.
        stub_mode: If True, use stub tools and hard-coded plans (no LLM calls).
        data_dir: Path to data directory containing CSV files.
        log_level: Logging level.
    """

    anthropic_api_key: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )
    model_name: str = field(
        default_factory=lambda: os.getenv("MODEL_NAME", "claude-sonnet-4-20250514")
    )
    stub_mode: bool = field(
        default_factory=lambda: os.getenv("STUB_MODE", "true").lower() == "true"
    )
    data_dir: str = field(
        default_factory=lambda: os.getenv("DATA_DIR", "data/synthetic")
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )


def load_settings() -> Settings:
    """Load settings from environment variables.

    Call after loading .env file if using python-dotenv.
    """
    return Settings()
