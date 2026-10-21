"""
Reference data loader for charter generation.

Loads the embedded ISO/IEC 38505-1 & ISO/IEC 25012-aligned JSON datasets that power
the charter template engine. All files ship inside the package
to avoid external network dependencies.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent


def _load_json(filename: str) -> list[dict[str, Any]] | dict[str, Any]:
    """Load a JSON file from the embedded data directory."""
    path = _DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Reference data not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Public loaders (cached for lifetime of process) ──────────────────


@lru_cache(maxsize=1)
def load_charter_templates() -> dict[str, Any]:
    """
    Load the 3 charter type templates.

    Returns dict with 'charterTemplates' key containing:
      - LifecyclePainPoint (8 sections)
      - KPIImprovement (3 sections)
      - StrategicOrAIInitiative (2 sections)
    """
    return _load_json("charter_templates.json")


@lru_cache(maxsize=1)
def load_dq_dimensions() -> list[dict[str, Any]]:
    """
    Load the 60 ISO/IEC 25012 & ISO 8000-8 data quality dimensions.

    Each dimension has: id, dimensionIndex, name, category, definition.
    """
    return _load_json("dq_dimensions.json")


@lru_cache(maxsize=1)
def load_business_impacts() -> list[dict[str, Any]]:
    """
    Load positive/negative business impact text per DQ dimension.

    Used to populate the Business Case section of charters.
    """
    return _load_json("dq_business_impacts.json")


@lru_cache(maxsize=1)
def load_business_lifecycles() -> list[dict[str, Any]]:
    """
    Load the 7 generic business lifecycles with 40+ stages.

    Lifecycles: O2C, P2P, H2R, R2R, I2M, CRM, OPS.
    """
    return _load_json("business_lifecycles.json")


@lru_cache(maxsize=1)
def load_strategic_alignment() -> list[dict[str, Any]]:
    """
    Load strategic objectives → DQ dimension mappings.

    8 universal strategic objectives (customer experience,
    AI innovation, operational efficiency, etc.).
    """
    return _load_json("strategic_alignment.json")


@lru_cache(maxsize=1)
def load_environmental_factors() -> list[dict[str, Any]]:
    """
    Load environmental factor → DQ dimension impact data.

    Factors that exacerbate data quality issues.
    """
    return _load_json("environmental_factors.json")


@lru_cache(maxsize=1)
def load_lifecycle_impacts() -> list[dict[str, Any]]:
    """
    Load stage-specific pain points → DQ dimension mappings.

    Maps business lifecycle stage pain points to affected
    DQ dimensions for targeted charter generation.
    """
    return _load_json("lifecycle_impacts.json")


def get_dimension_by_index(dim_index: int) -> dict[str, Any] | None:
    """Look up a DQ dimension by its dimension index."""
    for dim in load_dq_dimensions():
        if dim.get("dimensionIndex") == dim_index:
            return dim
    return None


def get_impacts_for_dimension(dim_index: int) -> dict[str, Any] | None:
    """Get positive/negative business impacts for a DQ dimension."""
    for impact in load_business_impacts():
        if impact.get("dimensionIndex") == dim_index:
            return impact
    return None


def get_lifecycle_by_id(lifecycle_id: str) -> dict[str, Any] | None:
    """Look up a business lifecycle by ID (e.g. 'LC_O2C')."""
    for lc in load_business_lifecycles():
        if lc.get("lifecycleId") == lifecycle_id:
            return lc
    return None
