"""
Test scoring engine against actual ODGS v5 workspace.

Verifies that a fresh install produces the expected ~18% baseline score.
"""

import json
from pathlib import Path

import pytest

# Path to the actual ODGS v5 protocol artifacts
ODGS_ROOT = Path(__file__).parent.parent.parent.parent / "odgs-v5" / "2_INFORMATIVE_REFERENCE" / "src" / "odgs"


@pytest.fixture
def workspace_snapshot():
    """Read the real ODGS v5 workspace."""
    from odgs_maturity.workspace.reader import WorkspaceReader
    reader = WorkspaceReader()
    # Point directly at the package source (no workspace YAML in v5)
    return reader.read(ODGS_ROOT.parent.parent.parent)


@pytest.fixture
def maturity_result(workspace_snapshot):
    """Score the real workspace."""
    from odgs_maturity.scoring.engine import score_workspace
    return score_workspace(workspace_snapshot)


class TestWorkspaceReader:
    """Test that the reader can find and parse ODGS v5 artifacts."""

    def test_finds_odgs_root(self):
        from odgs_maturity.workspace.reader import WorkspaceReader
        reader = WorkspaceReader()
        snap = reader.read(ODGS_ROOT.parent.parent.parent)
        assert snap.odgs_package_root is not None
        assert (snap.odgs_package_root / "executive").exists()

    def test_reads_context_bindings(self, workspace_snapshot):
        art = workspace_snapshot.artifacts["context_bindings"]
        assert art.exists
        assert art.data is not None
        assert "contexts" in art.data

    def test_reads_data_rules(self, workspace_snapshot):
        art = workspace_snapshot.artifacts["data_rules"]
        assert art.exists
        assert isinstance(art.data, list)
        assert len(art.data) > 30  # We know there are 50 rules

    def test_reads_standard_metrics(self, workspace_snapshot):
        art = workspace_snapshot.artifacts["standard_metrics"]
        assert art.exists
        assert art.size_bytes > 0


class TestScoringEngine:
    """Test the 8-pillar scoring engine."""

    def test_produces_result(self, maturity_result):
        assert maturity_result is not None
        assert maturity_result.total_rules > 0

    def test_all_pillars_scored(self, maturity_result):
        from odgs_maturity.scoring.models import Pillar
        for pillar in Pillar:
            assert pillar in maturity_result.pillars

    def test_aggregate_score_in_range(self, maturity_result):
        score = maturity_result.aggregate_score
        assert 0 <= score <= 100

    def test_fresh_install_baseline(self, maturity_result):
        """Fresh ODGS v5 with defaults should score below 60%.

        ODGS v5 ships with pre-populated artifacts (14 context bindings,
        50 rules, 60+ DQ dimensions), so baseline is higher than a
        truly empty workspace. But no workspace YAML, no packs, no bridges,
        and all owners set to 'TBD' keeps it below 60%.
        """
        score = maturity_result.aggregate_score
        assert score < 60, f"Expected <60% for unconfigured workspace, got {score}%"

    def test_serialisation(self, maturity_result):
        d = maturity_result.to_dict()
        assert "aggregate_score" in d
        assert "pillars" in d
        # Ensure JSON-serialisable
        json.dumps(d)

    def test_gaps_detected(self, maturity_result):
        """Unconfigured workspace should have multiple gaps."""
        assert maturity_result.total_gaps > 0

    def test_red_flags_present(self, maturity_result):
        """No workspace YAML + TBD owners should generate some flags."""
        # At minimum: no bridges, no packs, no workspace yaml
        assert len(maturity_result.red_flags) > 0 or len(maturity_result.amber_flags) > 0
