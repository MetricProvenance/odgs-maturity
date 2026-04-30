"""
Maturity scoring engine.

Orchestrates rule evaluation against a workspace snapshot
and assembles the MaturityResult.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .models import MaturityResult, Pillar, PillarResult
from .rules import get_all_rules

if TYPE_CHECKING:
    from ..workspace.reader import WorkspaceSnapshot

logger = logging.getLogger(__name__)


def score_workspace(snapshot: "WorkspaceSnapshot") -> MaturityResult:
    """
    Run all scoring rules against a workspace snapshot.

    Returns a MaturityResult with per-pillar breakdowns.
    """
    result = MaturityResult(
        org_name=snapshot.org_name,
        industry=snapshot.industry,
        workspace_path=str(snapshot.workspace_root or ""),
        errors=list(snapshot.errors),
    )

    # Initialise empty pillar results
    for pillar in Pillar:
        result.pillars[pillar] = PillarResult(pillar=pillar)

    # Evaluate each registered rule
    for rule_id, rule_name, pillar, rule_fn in get_all_rules():
        try:
            rule_result = rule_fn(snapshot)
            result.pillars[pillar].rules.append(rule_result)
        except Exception as e:
            logger.error("Rule %s failed: %s", rule_id, e)
            result.errors.append(f"Rule {rule_id} error: {e}")

    return result
