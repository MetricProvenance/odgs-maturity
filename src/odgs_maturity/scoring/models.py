"""
Maturity scoring data models.

Defines the 8-pillar maturity framework and the result structures
used by the scoring engine and downstream consumers (CLI, API, charter).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MaturityLevel(Enum):
    """
    5-point maturity scale aligned with ISO/IEC 38505-1 and ISO/IEC 25012.

    1 = Initial/Ad-hoc
    2 = Developing/Managed
    3 = Defined/Standardised
    4 = Measured/Quantitatively Managed
    5 = Optimised/Continuous Improvement
    """
    INITIAL = 1
    DEVELOPING = 2
    DEFINED = 3
    MEASURED = 4
    OPTIMISED = 5

    @classmethod
    def from_score(cls, score: float) -> "MaturityLevel":
        """Convert a 0-100 percentage score to a maturity level."""
        if score >= 80:
            return cls.OPTIMISED
        elif score >= 60:
            return cls.MEASURED
        elif score >= 40:
            return cls.DEFINED
        elif score >= 20:
            return cls.DEVELOPING
        else:
            return cls.INITIAL

    @property
    def label(self) -> str:
        """Human-readable label for display."""
        labels = {
            1: "Initial",
            2: "Developing",
            3: "Defined",
            4: "Measured",
            5: "Optimised",
        }
        return labels[self.value]


class Pillar(Enum):
    """
    The 8 maturity pillars.

    6 adapted from ISO/IEC 38505-1 & ISO/IEC 25012 governance domains + 2 ODGS-native pillars.
    """
    # ISO/IEC 38505-1 & 25012 pillars
    GOVERNANCE_FOUNDATIONS = "governance_foundations"
    QUALITY_ENFORCEMENT = "quality_enforcement"
    OPERATIONAL_READINESS = "operational_readiness"
    METADATA_INTEGRITY = "metadata_integrity"
    USAGE_ANALYTICS = "usage_analytics"
    ORGANIZATIONAL_ADOPTION = "organizational_adoption"
    # ODGS-native pillars
    CERTIFICATION_TRUST = "certification_trust"
    BRIDGE_CONNECTIVITY = "bridge_connectivity"

    @property
    def display_name(self) -> str:
        """Human-readable pillar name."""
        names = {
            "governance_foundations": "Governance Foundations",
            "quality_enforcement": "Quality Enforcement",
            "operational_readiness": "Operational Readiness",
            "metadata_integrity": "Metadata Integrity",
            "usage_analytics": "Usage & Analytics",
            "organizational_adoption": "Organisational Adoption",
            "certification_trust": "Certification & Trust",
            "bridge_connectivity": "Bridge Connectivity",
        }
        return names[self.value]

    @property
    def weight(self) -> float:
        """
        Relative weight for aggregate score calculation.

        Weights sum to 1.0. Core ISO/IEC 38505-1 & 25012 pillars are weighted higher
        because they represent fundamental governance capability.
        """
        weights = {
            "governance_foundations": 0.20,
            "quality_enforcement": 0.18,
            "operational_readiness": 0.15,
            "metadata_integrity": 0.12,
            "usage_analytics": 0.08,
            "organizational_adoption": 0.12,
            "certification_trust": 0.08,
            "bridge_connectivity": 0.07,
        }
        return weights[self.value]


class CostFlag(Enum):
    """Cost/risk flag for SPOT analysis."""
    GREEN = "green"     # No action needed
    AMBER = "amber"     # Attention recommended
    RED = "red"         # Urgent action required


@dataclass
class RuleResult:
    """Result of evaluating a single scoring rule."""
    rule_id: str
    rule_name: str
    pillar: Pillar
    score: float            # 0.0 to 1.0
    max_score: float        # Maximum possible (always 1.0 for normalisation)
    evidence: str           # What the rule checked
    recommendation: str     # What to do to improve
    cost_flag: CostFlag = CostFlag.GREEN

    @property
    def percentage(self) -> float:
        """Score as a percentage."""
        return round(self.score * 100, 1)


@dataclass
class PillarResult:
    """Aggregated result for a single pillar."""
    pillar: Pillar
    rules: list[RuleResult] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Weighted average score for this pillar (0-100)."""
        if not self.rules:
            return 0.0
        total = sum(r.score for r in self.rules)
        return round((total / len(self.rules)) * 100, 1)

    @property
    def level(self) -> MaturityLevel:
        """Governance maturity level for this pillar."""
        return MaturityLevel.from_score(self.score)

    @property
    def cost_flag(self) -> CostFlag:
        """Worst cost flag across all rules in this pillar."""
        if any(r.cost_flag == CostFlag.RED for r in self.rules):
            return CostFlag.RED
        if any(r.cost_flag == CostFlag.AMBER for r in self.rules):
            return CostFlag.AMBER
        return CostFlag.GREEN

    @property
    def gaps(self) -> list[RuleResult]:
        """Rules scoring below 100%."""
        return [r for r in self.rules if r.score < 1.0]


@dataclass
class MaturityResult:
    """
    Complete maturity assessment result.

    This is the primary output of the scoring engine. It contains
    per-pillar breakdowns, the aggregate score, and the SPOT analysis
    data needed for charter generation.
    """
    pillars: dict[Pillar, PillarResult] = field(default_factory=dict)
    org_name: str = ""
    industry: str = ""
    workspace_path: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def aggregate_score(self) -> float:
        """Weighted aggregate maturity score (0-100)."""
        total = 0.0
        for pillar_enum, pillar_result in self.pillars.items():
            total += pillar_result.score * pillar_enum.weight
        return round(total, 1)

    @property
    def level(self) -> MaturityLevel:
        """Overall Governance maturity level."""
        return MaturityLevel.from_score(self.aggregate_score)

    @property
    def total_gaps(self) -> int:
        """Total number of rules with gaps across all pillars."""
        return sum(len(p.gaps) for p in self.pillars.values())

    @property
    def total_rules(self) -> int:
        """Total number of rules evaluated."""
        return sum(len(p.rules) for p in self.pillars.values())

    @property
    def red_flags(self) -> list[RuleResult]:
        """All rules with RED cost flags (urgent action)."""
        results = []
        for p in self.pillars.values():
            results.extend(r for r in p.rules if r.cost_flag == CostFlag.RED)
        return results

    @property
    def amber_flags(self) -> list[RuleResult]:
        """All rules with AMBER cost flags."""
        results = []
        for p in self.pillars.values():
            results.extend(r for r in p.rules if r.cost_flag == CostFlag.AMBER)
        return results

    def to_dict(self) -> dict:
        """Serialise to dictionary for API/JSON output."""
        return {
            "aggregate_score": self.aggregate_score,
            "level": self.level.label,
            "level_value": self.level.value,
            "org_name": self.org_name,
            "industry": self.industry,
            "total_rules": self.total_rules,
            "total_gaps": self.total_gaps,
            "red_flags": len(self.red_flags),
            "amber_flags": len(self.amber_flags),
            "pillars": {
                pillar.value: {
                    "name": pillar.display_name,
                    "score": result.score,
                    "level": result.level.label,
                    "weight": pillar.weight,
                    "cost_flag": result.cost_flag.value,
                    "rules_evaluated": len(result.rules),
                    "gaps": len(result.gaps),
                    "rules": [
                        {
                            "rule_id": r.rule_id,
                            "rule_name": r.rule_name,
                            "score": r.percentage,
                            "evidence": r.evidence,
                            "recommendation": r.recommendation,
                            "cost_flag": r.cost_flag.value,
                        }
                        for r in result.rules
                    ],
                }
                for pillar, result in self.pillars.items()
            },
        }
