"""
Test suite for charter generation.

Tests the full pipeline:
  1. Data loading from embedded JSON
  2. Gap-to-dimension mapping
  3. SPOT classification
  4. Charter template population
  5. Export to Markdown and JSON
"""

from __future__ import annotations

import json

import pytest

from odgs_maturity.charter.generator import (
    _extract_gap_dimensions,
    _classify_spot,
    _find_best_strategic_objective,
    _build_dimension_summary,
    _populate_template,
    build_context_from_result,
    generate_charter,
)
from odgs_maturity.charter.models import CharterType, CharterContext, Charter
from odgs_maturity.charter.export import to_markdown, to_json, to_plain_text
from odgs_maturity.data.loader import (
    load_charter_templates,
    load_dq_dimensions,
    load_business_impacts,
    load_business_lifecycles,
    load_strategic_alignment,
    load_environmental_factors,
    load_lifecycle_impacts,
    get_dimension_by_index,
    get_impacts_for_dimension,
    get_lifecycle_by_id,
)
from odgs_maturity.scoring.models import (
    CostFlag,
    MaturityLevel,
    MaturityResult,
    Pillar,
    PillarResult,
    RuleResult,
)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_result():
    """Build a MaturityResult with realistic gaps for charter testing."""
    result = MaturityResult(
        org_name="Acme Corp",
        industry="Manufacturing",
    )

    # Initialise all pillars
    for pillar in Pillar:
        result.pillars[pillar] = PillarResult(pillar=pillar)

    # Add some passing rules and some failing rules
    result.pillars[Pillar.GOVERNANCE_FOUNDATIONS].rules = [
        RuleResult(
            rule_id="GOV-01",
            rule_name="Context Bindings Populated",
            pillar=Pillar.GOVERNANCE_FOUNDATIONS,
            score=0.5,
            max_score=1.0,
            evidence="Partial context bindings defined",
            recommendation="Map all critical business processes to governance contexts",
            cost_flag=CostFlag.AMBER,
        ),
        RuleResult(
            rule_id="GOV-03",
            rule_name="Workspace YAML Configured",
            pillar=Pillar.GOVERNANCE_FOUNDATIONS,
            score=0.3,
            max_score=1.0,
            evidence="Missing workspace YAML configuration",
            recommendation="Create and configure workspace.yaml with all required fields",
            cost_flag=CostFlag.RED,
        ),
    ]

    result.pillars[Pillar.QUALITY_ENFORCEMENT].rules = [
        RuleResult(
            rule_id="QE-01",
            rule_name="Data Rules With Logic",
            pillar=Pillar.QUALITY_ENFORCEMENT,
            score=0.4,
            max_score=1.0,
            evidence="Limited rule logic defined",
            recommendation="Add logic expressions to all data quality rules",
            cost_flag=CostFlag.RED,
        ),
        RuleResult(
            rule_id="QE-03",
            rule_name="DQ Dimensions Coverage",
            pillar=Pillar.QUALITY_ENFORCEMENT,
            score=0.8,
            max_score=1.0,
            evidence="Mostly configured",
            recommendation="Review DQ dimensions coverage completeness",
            cost_flag=CostFlag.GREEN,
        ),
    ]

    result.pillars[Pillar.METADATA_INTEGRITY].rules = [
        RuleResult(
            rule_id="META-01",
            rule_name="Ontology Graph Populated",
            pillar=Pillar.METADATA_INTEGRITY,
            score=0.2,
            max_score=1.0,
            evidence="No ontology graph defined",
            recommendation="Populate the ontology graph with entity definitions",
            cost_flag=CostFlag.RED,
        ),
    ]

    result.pillars[Pillar.BRIDGE_CONNECTIVITY].rules = [
        RuleResult(
            rule_id="BRG-01",
            rule_name="Bridge Configurations",
            pillar=Pillar.BRIDGE_CONNECTIVITY,
            score=0.6,
            max_score=1.0,
            evidence="Some bridges configured",
            recommendation="Complete all bridge configurations",
            cost_flag=CostFlag.AMBER,
        ),
    ]

    return result


# ── Data Loading Tests ────────────────────────────────────────────────


class TestDataLoading:
    """Verify embedded reference data loads correctly."""

    def test_charter_templates_load(self):
        templates = load_charter_templates()
        assert "charterTemplates" in templates
        assert len(templates["charterTemplates"]) == 3

    def test_charter_template_types(self):
        templates = load_charter_templates()
        types = {t["charterType"] for t in templates["charterTemplates"]}
        assert types == {
            "LifecyclePainPoint",
            "KPIImprovement",
            "StrategicOrAIInitiative",
        }

    def test_dq_dimensions_load(self):
        dims = load_dq_dimensions()
        assert len(dims) == 60
        # Verify structure
        assert "dimensionIndex" in dims[0]
        assert "name" in dims[0]
        assert "category" in dims[0]

    def test_business_lifecycles_load(self):
        lifecycles = load_business_lifecycles()
        assert len(lifecycles) == 7
        # Verify O2C is present
        o2c = next(lc for lc in lifecycles if lc["lifecycleId"] == "LC_O2C")
        assert o2c["lifecycleName"] == "Order to Cash (O2C)"
        assert len(o2c["stages"]) >= 4

    def test_strategic_alignment_load(self):
        objectives = load_strategic_alignment()
        assert len(objectives) == 8
        assert objectives[0]["strategicObjectiveId"] == "SO_001"

    def test_environmental_factors_load(self):
        factors = load_environmental_factors()
        assert len(factors) > 0

    def test_lifecycle_impacts_load(self):
        impacts = load_lifecycle_impacts()
        assert len(impacts) > 0

    def test_dimension_lookup(self):
        dim = get_dimension_by_index(3)
        assert dim is not None
        assert "name" in dim

    def test_dimension_lookup_missing(self):
        dim = get_dimension_by_index(99999)
        assert dim is None

    def test_lifecycle_lookup(self):
        lc = get_lifecycle_by_id("LC_P2P")
        assert lc is not None
        assert "Procure" in lc["lifecycleName"]

    def test_lifecycle_lookup_missing(self):
        lc = get_lifecycle_by_id("LC_NONEXISTENT")
        assert lc is None


# ── Generator Core Logic Tests ────────────────────────────────────────


class TestGeneratorLogic:
    """Test the internal generator functions."""

    def test_extract_gap_dimensions(self, mock_result):
        dims = _extract_gap_dimensions(mock_result)
        assert len(dims) > 0
        # Should be deduplicated integers
        assert all(isinstance(d, int) for d in dims)
        assert len(dims) == len(set(dims))

    def test_classify_spot(self, mock_result):
        spot = _classify_spot(mock_result)
        assert isinstance(spot, dict)
        # Should have at least some categories populated
        total_items = sum(len(v) for v in spot.values())
        assert total_items > 0

    def test_classify_spot_categories(self, mock_result):
        spot = _classify_spot(mock_result)
        valid_cats = {"Standard", "Process", "Organization", "Technology"}
        for cat in spot:
            assert cat in valid_cats

    def test_find_strategic_objective(self, mock_result):
        dims = _extract_gap_dimensions(mock_result)
        obj_id, obj_name = _find_best_strategic_objective(dims)
        assert obj_id.startswith("SO_")
        assert len(obj_name) > 5

    def test_build_dimension_summary(self, mock_result):
        dims = _extract_gap_dimensions(mock_result)
        names, pos, neg = _build_dimension_summary(dims)
        assert len(names) > 0
        assert len(pos) > 0
        assert len(neg) > 0

    def test_populate_template_basic(self):
        text = "Hello {Name}, welcome to {Place}."
        result = _populate_template(text, {"Name": "Alice", "Place": "London"})
        assert result == "Hello Alice, welcome to London."

    def test_populate_template_conditional_present(self):
        text = "Item: {A} {B_if_exists?and {B}}"
        result = _populate_template(text, {"A": "one", "B": "two"})
        assert "one" in result
        assert "and two" in result

    def test_populate_template_conditional_missing(self):
        text = "Item: {A} {B_if_exists?and {B}}"
        result = _populate_template(text, {"A": "one"})
        assert "one" in result
        assert "and" not in result

    def test_populate_template_unreplaced_fallback(self):
        text = "Unknown: {SomeVariable}"
        result = _populate_template(text, {})
        assert "[To be specified]" in result


# ── Context Building Tests ────────────────────────────────────────────


class TestContextBuilding:
    """Test context construction from MaturityResult."""

    def test_build_context_defaults(self, mock_result):
        ctx = build_context_from_result(mock_result)
        assert ctx.org_name == "Acme Corp"
        assert ctx.maturity_score > 0
        assert len(ctx.affected_dimension_ids) > 0
        assert len(ctx.dimension_names) > 0

    def test_build_context_lifecycle_type(self, mock_result):
        ctx = build_context_from_result(
            mock_result,
            CharterType.LIFECYCLE_PAIN_POINT,
            lifecycle_name="Order to Cash (O2C)",
            stage_name="Order Entry",
            pain_points=["Duplicate order entries"],
        )
        assert ctx.lifecycle_name == "Order to Cash (O2C)"
        assert ctx.stage_name == "Order Entry"
        assert "Duplicate order entries" in ctx.pain_points

    def test_build_context_kpi_type(self, mock_result):
        ctx = build_context_from_result(
            mock_result,
            CharterType.KPI_IMPROVEMENT,
            kpi_name="On-Time Delivery Rate",
            kpi_objective="Supply Chain Excellence",
        )
        assert ctx.kpi_name == "On-Time Delivery Rate"
        assert ctx.kpi_objective == "Supply Chain Excellence"

    def test_build_context_strategic_type(self, mock_result):
        ctx = build_context_from_result(
            mock_result,
            CharterType.STRATEGIC_OR_AI,
            initiative_name="ML Demand Forecasting",
            ai_use_case="Predictive demand model",
        )
        assert ctx.initiative_name == "ML Demand Forecasting"
        assert ctx.ai_use_case == "Predictive demand model"

    def test_context_cost_flags(self, mock_result):
        ctx = build_context_from_result(mock_result)
        # Should have cost flags from RED/AMBER rules
        assert len(ctx.cost_flags) > 0

    def test_context_spot_classification(self, mock_result):
        ctx = build_context_from_result(mock_result)
        assert len(ctx.spot_classifications) > 0

    def test_context_strategic_objective(self, mock_result):
        ctx = build_context_from_result(mock_result)
        assert ctx.strategic_objective_id.startswith("SO_")


# ── Full Charter Generation Tests ─────────────────────────────────────


class TestCharterGeneration:
    """End-to-end charter generation tests."""

    def test_generate_lifecycle_charter(self, mock_result):
        charter = generate_charter(
            mock_result,
            CharterType.LIFECYCLE_PAIN_POINT,
            lifecycle_name="Procure to Pay (P2P)",
            stage_name="Invoice Processing",
            pain_points=["Mismatched PO data"],
        )
        assert charter.charter_type == CharterType.LIFECYCLE_PAIN_POINT
        assert len(charter.sections) == 8  # Lifecycle has 8 sections
        assert "Procure to Pay" in charter.title
        assert charter.metadata["total_gaps"] > 0

    def test_generate_kpi_charter(self, mock_result):
        charter = generate_charter(
            mock_result,
            CharterType.KPI_IMPROVEMENT,
            kpi_name="Customer Satisfaction Score",
        )
        assert charter.charter_type == CharterType.KPI_IMPROVEMENT
        assert len(charter.sections) == 3  # KPI has 3 sections
        assert "Customer Satisfaction" in charter.title

    def test_generate_strategic_charter(self, mock_result):
        charter = generate_charter(
            mock_result,
            CharterType.STRATEGIC_OR_AI,
            initiative_name="Data Mesh Programme",
        )
        assert charter.charter_type == CharterType.STRATEGIC_OR_AI
        assert len(charter.sections) == 2  # Strategic has 2 sections
        assert "Data Mesh" in charter.title

    def test_charter_sections_have_content(self, mock_result):
        charter = generate_charter(mock_result)
        for section in charter.sections:
            assert section.heading
            assert section.section_id
            assert len(section.content) > 0
            # Content should have been populated (no raw placeholders)
            for line in section.content:
                assert "{" not in line or "[To be specified]" in line

    def test_charter_to_dict(self, mock_result):
        charter = generate_charter(mock_result)
        d = charter.to_dict()
        assert d["charter_type"] == CharterType.LIFECYCLE_PAIN_POINT.value
        assert "sections" in d
        assert "metadata" in d
        assert d["maturity_score"] > 0

    def test_charter_metadata(self, mock_result):
        charter = generate_charter(mock_result)
        assert charter.metadata["generator_version"] == "1.0.0"
        assert charter.metadata["dimensions_affected"] > 0
        assert "spot_summary" in charter.metadata


# ── Export Tests ───────────────────────────────────────────────────────


class TestExport:
    """Test charter export formatters."""

    def test_markdown_export(self, mock_result):
        charter = generate_charter(mock_result)
        md = to_markdown(charter)
        # Should be a valid markdown document
        assert md.startswith("# ")
        assert "Maturity Score" in md
        assert "Executive Summary" in md
        assert "Next Steps" in md
        assert "SPOT Framework" in md

    def test_markdown_contains_org_name(self, mock_result):
        charter = generate_charter(mock_result)
        md = to_markdown(charter)
        assert "Acme Corp" in md

    def test_markdown_contains_dimensions(self, mock_result):
        charter = generate_charter(mock_result)
        md = to_markdown(charter)
        assert "Key Data Quality Dimensions" in md

    def test_markdown_contains_cta(self, mock_result):
        charter = generate_charter(mock_result)
        md = to_markdown(charter)
        assert "odgs-maturity score" in md
        assert "odgs discover" in md

    def test_json_export(self, mock_result):
        charter = generate_charter(mock_result)
        json_str = to_json(charter)
        parsed = json.loads(json_str)
        assert parsed["charter_type"] in [ct.value for ct in CharterType]
        assert len(parsed["sections"]) > 0

    def test_json_roundtrip(self, mock_result):
        charter = generate_charter(mock_result)
        json_str = to_json(charter)
        parsed = json.loads(json_str)
        assert parsed["maturity_score"] == charter.context.maturity_score

    def test_plain_text_export(self, mock_result):
        charter = generate_charter(mock_result)
        txt = to_plain_text(charter)
        # Should not contain markdown markup
        assert "## " not in txt
        assert "**" not in txt
        # Should contain charter content
        assert "Acme Corp" in txt

    def test_export_with_no_cost_flags(self, mock_result):
        """Charters with no cost flags should still export cleanly."""
        # Remove all flags
        for pillar in mock_result.pillars.values():
            for rule in pillar.rules:
                rule.cost_flag = CostFlag.GREEN
        charter = generate_charter(mock_result)
        md = to_markdown(charter)
        assert "# " in md  # Should still be valid markdown


# ── Charter Model Tests ───────────────────────────────────────────────


class TestCharterModels:
    """Test the charter data models."""

    def test_charter_type_display_name(self):
        assert "Lifecycle" in CharterType.LIFECYCLE_PAIN_POINT.display_name
        assert "KPI" in CharterType.KPI_IMPROVEMENT.display_name
        assert "Strategic" in CharterType.STRATEGIC_OR_AI.display_name

    def test_charter_type_description(self):
        for ct in CharterType:
            assert len(ct.description) > 20

    def test_charter_context_defaults(self):
        ctx = CharterContext()
        assert ctx.charter_type == CharterType.LIFECYCLE_PAIN_POINT
        assert ctx.maturity_score == 0.0
        assert ctx.generated_at  # Should be auto-populated

    def test_charter_to_dict_structure(self):
        charter = Charter(
            charter_type=CharterType.KPI_IMPROVEMENT,
            title="Test Charter",
        )
        d = charter.to_dict()
        assert d["charter_type"] == "KPIImprovement"
        assert d["title"] == "Test Charter"
        assert "sections" in d
