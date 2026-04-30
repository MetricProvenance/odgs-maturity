"""
Charter generator engine.

Ported from the Clavis charter-generator (script.js, 874 lines)
into a Python implementation that reads MaturityResult diagnostic
data and produces structured improvement charters.

The generator:
  1. Takes a MaturityResult from the scoring engine
  2. Identifies the worst-performing DQ dimensions
  3. Maps gaps to DAMA business lifecycles and strategic objectives
  4. Populates charter templates with contextual content
  5. Produces a Charter object ready for export

All terminal-operations-specific logic has been stripped.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from ..data.loader import (
    load_charter_templates,
    load_business_impacts,
    load_business_lifecycles,
    load_strategic_alignment,
    get_dimension_by_dama_id,
    get_impacts_for_dimension,
)
from .models import (
    Charter,
    CharterContext,
    CharterSection,
    CharterType,
    SPOTCategory,
)

if TYPE_CHECKING:
    from ..scoring.models import MaturityResult

logger = logging.getLogger(__name__)


# ── Gap-to-Dimension Mapping ─────────────────────────────────────────
#
# Maps rule IDs from the scoring engine to the DAMA dimension IDs
# they most directly relate to. This allows the charter generator
# to recommend specific DQ dimensions for improvement.

RULE_DIMENSION_MAP: dict[str, list[int]] = {
    # Governance Foundations
    "GOV-01": [7, 12, 20],    # Clarity, Completeness (Records), Consistency
    "GOV-02": [16, 31, 33],   # Completeness (Metadata), Interpretability, Linkability
    "GOV-03": [7, 14, 20],    # Clarity, Completeness (Values), Consistency
    # Quality Enforcement
    "QE-01": [3, 20, 34],     # Accuracy, Consistency, Metadata compliance
    "QE-02": [16, 17, 37],    # Completeness (Metadata), Compliance (Data), Obtainability
    "QE-03": [5, 12, 48],     # Availability, Completeness (Records), Relevance
    # Operational Readiness
    "OPS-01": [5, 30, 47],    # Availability, Integrity, Referential integrity
    "OPS-02": [17, 20, 30],   # Compliance (Data), Consistency, Integrity
    "OPS-03": [25, 50, 56],   # Credibility, Traceability, Validity
    # Metadata Integrity
    "META-01": [7, 16, 31],   # Clarity, Completeness (Metadata), Interpretability
    "META-02": [12, 14, 48],  # Completeness (Records/Values), Relevance
    "META-03": [2, 33, 37],   # Accessibility, Linkability, Obtainability
    # Usage & Analytics
    "USE-01": [12, 26, 48],   # Completeness (Records), Currency, Relevance
    "USE-02": [33, 47, 50],   # Linkability, Referential integrity, Traceability
    # Organisational Adoption
    "ORG-01": [17, 20, 48],   # Compliance (Data), Consistency, Relevance
    "ORG-02": [12, 33, 47],   # Completeness (Records), Linkability, Referential integrity
    "ORG-03": [7, 14, 16],    # Clarity, Completeness (Values/Metadata)
    # Certification & Trust
    "CERT-01": [17, 19, 30],  # Compliance, Confidentiality, Integrity
    "CERT-02": [1, 19, 25],   # Access security, Confidentiality, Credibility
    # Bridge Connectivity
    "BRG-01": [2, 5, 33],     # Accessibility, Availability, Linkability
    "BRG-02": [12, 26, 59],   # Completeness (Records), Currency, Variety
}

# SPOT classification for each rule
RULE_SPOT_MAP: dict[str, SPOTCategory] = {
    "GOV-01": SPOTCategory.ORGANIZATION,
    "GOV-02": SPOTCategory.PROCESS,
    "GOV-03": SPOTCategory.STANDARD,
    "QE-01":  SPOTCategory.STANDARD,
    "QE-02":  SPOTCategory.ORGANIZATION,
    "QE-03":  SPOTCategory.STANDARD,
    "OPS-01": SPOTCategory.TECHNOLOGY,
    "OPS-02": SPOTCategory.PROCESS,
    "OPS-03": SPOTCategory.TECHNOLOGY,
    "META-01": SPOTCategory.STANDARD,
    "META-02": SPOTCategory.STANDARD,
    "META-03": SPOTCategory.TECHNOLOGY,
    "USE-01": SPOTCategory.PROCESS,
    "USE-02": SPOTCategory.PROCESS,
    "ORG-01": SPOTCategory.ORGANIZATION,
    "ORG-02": SPOTCategory.ORGANIZATION,
    "ORG-03": SPOTCategory.ORGANIZATION,
    "CERT-01": SPOTCategory.STANDARD,
    "CERT-02": SPOTCategory.TECHNOLOGY,
    "BRG-01": SPOTCategory.TECHNOLOGY,
    "BRG-02": SPOTCategory.PROCESS,
}


def _extract_gap_dimensions(result: "MaturityResult") -> list[int]:
    """
    Extract the DAMA dimension IDs most affected by maturity gaps.

    Returns a deduplicated, priority-ordered list of dimension IDs.
    """
    dim_scores: dict[int, float] = {}

    for pillar_result in result.pillars.values():
        for rule in pillar_result.gaps:
            dama_ids = RULE_DIMENSION_MAP.get(rule.rule_id, [])
            gap_severity = 1.0 - rule.score  # Higher = worse
            for dama_id in dama_ids:
                dim_scores[dama_id] = dim_scores.get(dama_id, 0.0) + gap_severity

    # Sort by cumulative severity (worst first)
    sorted_dims = sorted(dim_scores.keys(), key=lambda d: dim_scores[d], reverse=True)
    return sorted_dims


def _classify_spot(result: "MaturityResult") -> dict[str, list[str]]:
    """
    Classify all gaps using the SPOT framework.

    Returns: {category_name: [recommendation_texts]}
    """
    spot: dict[str, list[str]] = {
        "Standard": [],
        "Process": [],
        "Organization": [],
        "Technology": [],
    }

    for pillar_result in result.pillars.values():
        for rule in pillar_result.gaps:
            category = RULE_SPOT_MAP.get(rule.rule_id)
            if category:
                spot[category.value].append(rule.recommendation)

    return {k: v for k, v in spot.items() if v}


def _find_best_strategic_objective(
    dimension_ids: list[int],
) -> tuple[str, str]:
    """
    Find the strategic objective most aligned with the affected dimensions.

    Returns (objective_id, objective_name).
    """
    objectives = load_strategic_alignment()
    best_id = ""
    best_name = "Optimize Operational Efficiency & Reduce Costs"
    best_overlap = 0

    for obj in objectives:
        critical = set(obj.get("criticalDimensionDamaIds", []))
        supporting = set(obj.get("supportingDimensionDamaIds", []))
        overlap = len(critical.intersection(dimension_ids)) * 2 + \
                  len(supporting.intersection(dimension_ids))
        if overlap > best_overlap:
            best_overlap = overlap
            best_id = obj.get("strategicObjectiveId", "")
            best_name = obj.get("strategicObjective", best_name)

    return best_id, best_name


def _build_dimension_summary(
    dimension_ids: list[int],
    max_dims: int = 5,
) -> tuple[list[str], str, str]:
    """
    Build summary text from affected dimensions.

    Returns:
      - dimension_names: list of dimension names
      - positive_summary: summarised positive impacts
      - negative_summary: summarised negative impacts
    """
    dim_names = []
    positives = []
    negatives = []

    for dama_id in dimension_ids[:max_dims]:
        dim = get_dimension_by_dama_id(dama_id)
        if dim:
            dim_names.append(dim["name"])

        impact = get_impacts_for_dimension(dama_id)
        if impact:
            pos = impact.get("positiveImpactsGoodDQ", [])
            neg = impact.get("negativeImpactsPoorDQ", [])
            if pos:
                positives.append(pos[0])
            if neg:
                negatives.append(neg[0])

    positive_summary = "; ".join(positives[:3]) if positives else \
        "improved operational efficiency and data trustworthiness"
    negative_summary = "; ".join(negatives[:3]) if negatives else \
        "reduced data reliability and increased operational risk"

    return dim_names, positive_summary, negative_summary


def _populate_template(
    template_text: str,
    replacements: dict[str, str],
) -> str:
    """
    Replace {Placeholder} tokens in template text.

    Handles conditional blocks: {Cond_if_exists?text}
    """
    result = template_text

    # Handle conditional blocks first
    cond_pattern = r"\{(\w+)_if_exists\?(.*?)\}"
    for match in re.finditer(cond_pattern, result):
        key = match.group(1)
        conditional_text = match.group(2)
        if key in replacements and replacements[key]:
            # Replace placeholders within the conditional text too
            expanded = conditional_text
            for k, v in replacements.items():
                expanded = expanded.replace(f"{{{k}}}", v)
            result = result.replace(match.group(0), expanded)
        else:
            result = result.replace(match.group(0), "")

    # Standard replacements
    for key, value in replacements.items():
        result = result.replace(f"{{{key}}}", value)

    # Clean up any unreplaced placeholders with sensible defaults
    # Handles both simple {Placeholder} and complex {Key, e.g., 'example'} forms
    result = re.sub(
        r"\{[A-Za-z_]+(?:,\s*e\.g\.\s*,[^}]*)?\}",
        "[To be specified]",
        result,
    )

    return result


def build_context_from_result(
    result: "MaturityResult",
    charter_type: CharterType = CharterType.LIFECYCLE_PAIN_POINT,
    **user_inputs,
) -> CharterContext:
    """
    Build a CharterContext by combining maturity results with user selections.

    The context combines:
      - Diagnostic data from the scoring engine (gaps, flags, SPOT)
      - User-provided selections (lifecycle, stage, KPI, initiative)
      - Auto-derived DQ dimension mappings

    Args:
        result: MaturityResult from the scoring engine
        charter_type: Which charter type to generate
        **user_inputs: User selections (lifecycle_name, stage_name, etc.)
    """
    dim_ids = _extract_gap_dimensions(result)
    dim_names, _, _ = _build_dimension_summary(dim_ids)
    spot = _classify_spot(result)
    strat_id, strat_name = _find_best_strategic_objective(dim_ids)

    # Extract cost flags
    cost_flags = []
    red_rules = []
    for rule in result.red_flags:
        cost_flags.append(f"{rule.rule_name}: {rule.recommendation}")
        red_rules.append(rule.rule_id)
    for rule in result.amber_flags:
        cost_flags.append(f"{rule.rule_name}: {rule.recommendation}")

    ctx = CharterContext(
        charter_type=charter_type,
        org_name=result.org_name or user_inputs.get("org_name", ""),
        maturity_score=result.aggregate_score,
        maturity_level=result.level.label,
        affected_dimension_ids=dim_ids[:10],
        dimension_names=dim_names,
        strategic_objective_id=strat_id,
        strategic_objective_name=strat_name,
        spot_classifications=spot,
        cost_flags=cost_flags,
        red_flag_rules=red_rules,
    )

    # Apply user inputs
    for key, value in user_inputs.items():
        if hasattr(ctx, key) and value is not None:
            setattr(ctx, key, value)

    return ctx


def generate_charter(
    result: "MaturityResult",
    charter_type: CharterType = CharterType.LIFECYCLE_PAIN_POINT,
    **user_inputs,
) -> Charter:
    """
    Generate a complete improvement charter.

    This is the main entry point for charter generation. It:
      1. Builds a CharterContext from maturity results + user input
      2. Loads the appropriate template
      3. Populates template sections with contextual content
      4. Returns a Charter ready for export

    Args:
        result: MaturityResult from the scoring engine
        charter_type: Which charter template to use
        **user_inputs: User selections for template population

    Returns:
        Charter: Complete charter with populated sections
    """
    ctx = build_context_from_result(result, charter_type, **user_inputs)
    dim_ids = ctx.affected_dimension_ids
    dim_names, positive_summary, negative_summary = _build_dimension_summary(dim_ids)

    # Build replacement dictionary for template population
    replacements = {
        # Common
        "DimensionNameList": ", ".join(dim_names) if dim_names else "key data quality dimensions",
        "SummarizedPositiveImpactsFromDQDimensions": positive_summary,
        "SummarizedNegativeImpactsFromDQDimensions": negative_summary,
        "SummarizedPositiveImpactsFromDQDimensions_KPI_Context": positive_summary,
        "SummarizedNegativeImpactsFromDQDimensions_StrategicContext": negative_summary,
        "SummarizedPositiveImpactsFromDQDimensions_StrategicContext": positive_summary,
        "RelevantStrategicObjectiveName": ctx.strategic_objective_name,
        "ExampleDimensionNameForPainPoint1": dim_names[0] if dim_names else "data quality",
        "SpecificExampleImpactForPainPoint1": (
            negative_summary.split(";")[0] if negative_summary else "operational inefficiency"
        ),
        "DimensionName1": dim_names[0] if dim_names else "a key data dimension",
        "DimensionName2": dim_names[1] if len(dim_names) > 1 else "another data dimension",
        "PrimaryDimensionToImproveName": dim_names[0] if dim_names else "core data quality",
        # Lifecycle Pain Point
        "LifecycleName": ctx.lifecycle_name or "[Selected Business Process]",
        "StageName": ctx.stage_name or "[Selected Process Stage]",
        "PainPoint1": ctx.pain_points[0] if ctx.pain_points else "data quality issues affecting process efficiency",
        "PainPoint2": ctx.pain_points[1] if len(ctx.pain_points) > 1 else "",
        "PainPoint2_if_exists": ctx.pain_points[1] if len(ctx.pain_points) > 1 else "",
        # KPI
        "KPI_Name": ctx.kpi_name or "[Selected KPI]",
        "KPI_Objective_or_Area": ctx.kpi_objective or "[KPI business area]",
        "DataSourceListForKPI": ", ".join(ctx.data_sources) if ctx.data_sources else "[data sources]",
        "ExampleImpactOfPoorDQonKPI": f"unreliable {ctx.kpi_name or 'KPI'} values due to data inconsistencies",
        # Strategic
        "StrategicInitiativeName": ctx.initiative_name or "[Strategic Initiative]",
        "AIUseCaseName": ctx.ai_use_case or "",
        "AIUseCaseContext": ctx.ai_use_case or "",
        "ExampleInputDatasets": "[relevant input datasets]",
        "SpecificRiskToAIModelOrStrategy": "unreliable outputs and degraded model performance",
        "AnotherSpecificRiskToAIModelOrStrategy": "incomplete feature coverage and biased predictions",
        # Common placeholders
        "KeyDataTypeInvolved": "governance workspace data",
        "KeyPainPointToAlleviate": ctx.pain_points[0] if ctx.pain_points else "data quality gaps",
        "Relevant_KPI_Name": ctx.kpi_name or "Governance Maturity Score",
        "DepartmentOwningProcess": "[Department]",
        "RelevantDataCategoriesList": "Governance Policies, Data Quality Rules, Metric Definitions, System Mappings",
        "SpecificDataElementsList": "Rule Logic Expressions, Metric Descriptions, Owner Assignments, Bridge Configurations",
        "SpecificExampleOfPoorDQ1": f"deficiencies in {dim_names[0]}" if dim_names else "data quality gaps",
        "SpecificExampleOfPoorDQ2": f"weaknesses in {dim_names[1]}" if len(dim_names) > 1 else "additional quality issues",
        "ReiterateKeyPainPointSymptoms": "reduced governance effectiveness and increased compliance risk",
        "EnvironmentalFactor1_Name": "",
        "BriefDescriptionOfFactor1ImpactOnDQDimensions": "",
        "EnvironmentalFactorInsight": "",
    }

    # Load template
    templates_data = load_charter_templates()
    template = None
    for t in templates_data.get("charterTemplates", []):
        if t.get("charterType") == charter_type.value:
            template = t
            break

    if template is None:
        raise ValueError(f"No template found for charter type: {charter_type.value}")

    # Generate title
    title = _populate_template(template["titleTemplate"], replacements)

    # Generate sections
    sections = []
    for section_tmpl in template.get("sections", []):
        content_lines = []
        for line in section_tmpl.get("copyTemplate", []):
            populated = _populate_template(line, replacements)
            if populated.strip():
                content_lines.append(populated)

        sections.append(CharterSection(
            heading=section_tmpl["heading"],
            section_id=section_tmpl["id"],
            content=content_lines,
            guidance=section_tmpl.get("guidanceForUser", ""),
        ))

    charter = Charter(
        charter_type=charter_type,
        title=title,
        sections=sections,
        context=ctx,
        metadata={
            "generator_version": "1.0.0",
            "template_source": "DAMA DMBOK / Clavis Framework",
            "dimensions_affected": len(dim_ids),
            "spot_summary": {k: len(v) for k, v in ctx.spot_classifications.items()},
            "maturity_score": ctx.maturity_score,
            "total_gaps": result.total_gaps,
        },
    )

    return charter
