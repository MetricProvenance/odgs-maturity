"""
Read-only workspace reader for ODGS governance workspaces.

Inspects ODGS protocol artifacts (JSON/YAML) to extract configuration
state for maturity scoring. Never modifies any workspace files.

Supports two workspace layouts:
  1. Installed package: site-packages/odgs/{executive,judiciary,legislative}/
  2. OS workspace:     workspace_path/odgs-workspace.yaml + protocol artifacts
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


# ─── Artifact Catalog ──────────────────────────────────────────────────────────
# Maps logical artifact names to their relative paths within an ODGS installation.
# These are the files the maturity engine inspects.
ARTIFACT_PATHS = {
    # Executive branch
    "context_bindings": "executive/context_bindings.json",
    "physical_data_map": "executive/physical_data_map.json",
    "business_process_maps": "executive/business_process_maps.json",
    "interceptor": "executive/interceptor.py",
    # Judiciary branch
    "data_rules": "judiciary/standard_data_rules.json",
    "root_cause_factors": "judiciary/root_cause_factors.json",
    # Legislative branch
    "standard_metrics": "legislative/standard_metrics.json",
    "dq_dimensions": "legislative/standard_dq_dimensions.json",
    "ontology_graph": "legislative/ontology_graph.json",
}


@dataclass
class ArtifactSnapshot:
    """
    Snapshot of a single ODGS artifact file.

    Attributes:
        exists: Whether the file was found on disk.
        path: Absolute path to the artifact (if found).
        data: Parsed JSON/YAML content (None for .py files or if missing).
        size_bytes: File size in bytes.
        record_count: Number of top-level items if the artifact is a list/dict.
    """
    exists: bool = False
    path: Path | None = None
    data: Any = None
    size_bytes: int = 0
    record_count: int = 0


@dataclass
class WorkspaceSnapshot:
    """
    Complete read-only snapshot of an ODGS workspace.

    This captures the configuration state at a point in time.
    The maturity engine scores against this snapshot.
    """
    workspace_root: Path | None = None
    odgs_package_root: Path | None = None
    workspace_yaml: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, ArtifactSnapshot] = field(default_factory=dict)
    installed_packs: list[str] = field(default_factory=list)
    bridge_configs: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def org_name(self) -> str:
        """Organisation name from workspace YAML."""
        return self.workspace_yaml.get("organization", {}).get("name", "")

    @property
    def industry(self) -> str:
        """Industry from workspace YAML."""
        return self.workspace_yaml.get("organization", {}).get("industry", "")

    @property
    def enforcement_mode(self) -> str:
        """Enforcement mode (permissive/strict)."""
        return self.workspace_yaml.get("enforcement", {}).get("mode", "permissive")


class WorkspaceReader:
    """
    Read-only inspector for ODGS workspaces.

    Usage:
        reader = WorkspaceReader()
        snapshot = reader.read("/path/to/workspace")
        # or auto-detect:
        snapshot = reader.read()  # finds installed odgs package
    """

    def read(self, workspace_path: str | Path | None = None) -> WorkspaceSnapshot:
        """
        Read an ODGS workspace and return a snapshot.

        Args:
            workspace_path: Optional explicit path. If None, auto-detects
                           the installed odgs package location.

        Returns:
            WorkspaceSnapshot with all discovered artifact states.
        """
        snapshot = WorkspaceSnapshot()

        # Step 1: Locate the ODGS package artifacts
        odgs_root = self._find_odgs_root(workspace_path)
        if odgs_root is None:
            snapshot.errors.append(
                "Could not locate ODGS package. "
                "Install with: pip install odgs"
            )
            return snapshot

        snapshot.odgs_package_root = odgs_root
        logger.info("ODGS package root: %s", odgs_root)

        # Step 2: Read workspace YAML if present
        if workspace_path:
            ws_path = Path(workspace_path)
            snapshot.workspace_root = ws_path
            yaml_path = ws_path / "odgs-workspace.yaml"
            if yaml_path.exists():
                snapshot.workspace_yaml = self._read_yaml(yaml_path, snapshot)
            else:
                # Try .yml variant
                yaml_path = ws_path / "odgs-workspace.yml"
                if yaml_path.exists():
                    snapshot.workspace_yaml = self._read_yaml(yaml_path, snapshot)

        # Step 3: Read each artifact
        for name, rel_path in ARTIFACT_PATHS.items():
            snapshot.artifacts[name] = self._read_artifact(odgs_root, rel_path)

        # Step 4: Detect installed regulation packs
        snapshot.installed_packs = self._detect_packs(odgs_root)

        # Step 5: Detect bridge configurations
        snapshot.bridge_configs = self._detect_bridges(snapshot)

        return snapshot

    def _find_odgs_root(self, workspace_path: str | Path | None) -> Path | None:
        """
        Locate the ODGS package root directory.

        Search order:
        1. Explicit workspace_path + known subdirectories
        2. Installed Python package location
        """
        # If explicit path given, check common layouts
        if workspace_path:
            ws = Path(workspace_path)
            # Direct ODGS source layout (e.g., development checkout)
            for candidate in [
                ws / "executive",
                ws / "src" / "odgs" / "executive",
            ]:
                if candidate.exists():
                    return candidate.parent

        # Try to find installed odgs package
        try:
            import odgs  # type: ignore[import-not-found]
            # Namespace packages may have __file__ = None
            if odgs.__file__ is not None:
                pkg_path = Path(odgs.__file__).parent
                if (pkg_path / "executive").exists():
                    return pkg_path
        except ImportError:
            pass

        # Try common development paths relative to workspace
        if workspace_path:
            ws = Path(workspace_path)
            # Monorepo layout: workspace is project root, odgs is in a subfolder
            for candidate in [
                ws / "odgs-v5" / "2_INFORMATIVE_REFERENCE" / "src" / "odgs",
                ws / "odgs" / "src" / "odgs",
            ]:
                if (candidate / "executive").exists():
                    return candidate

        return None

    def _read_artifact(self, odgs_root: Path, rel_path: str) -> ArtifactSnapshot:
        """Read a single artifact file and return its snapshot."""
        full_path = odgs_root / rel_path
        snap = ArtifactSnapshot()

        if not full_path.exists():
            return snap

        snap.exists = True
        snap.path = full_path
        snap.size_bytes = full_path.stat().st_size

        # Only parse JSON files (not .py)
        if full_path.suffix == ".json":
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    snap.data = json.load(f)

                # Count records
                if isinstance(snap.data, list):
                    snap.record_count = len(snap.data)
                elif isinstance(snap.data, dict):
                    # For dict-shaped artifacts, count top-level keys
                    # or items in the primary collection
                    for key in ("contexts", "processes", "systems", "metrics", "dimensions"):
                        if key in snap.data and isinstance(snap.data[key], list):
                            snap.record_count = len(snap.data[key])
                            break
                    else:
                        snap.record_count = len(snap.data)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to parse %s: %s", full_path, e)

        elif full_path.suffix == ".py":
            snap.record_count = 1  # Just mark as present

        return snap

    def _read_yaml(self, path: Path, snapshot: WorkspaceSnapshot) -> dict:
        """Safely read a YAML file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data
        except (yaml.YAMLError, OSError) as e:
            snapshot.errors.append(f"Failed to read {path}: {e}")
            return {}

    def _detect_packs(self, odgs_root: Path) -> list[str]:
        """
        Detect installed Regulation Packs.

        Packs are stored as signed JSON/YAML files in the packs/ subdirectory
        or registered in a packs manifest.
        """
        packs_dir = odgs_root / "packs"
        if not packs_dir.exists():
            return []

        found = []
        for pack_file in packs_dir.glob("*.json"):
            try:
                with open(pack_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                pack_id = data.get("pack_id", pack_file.stem)
                found.append(pack_id)
            except (json.JSONDecodeError, OSError):
                continue

        return found

    def _detect_bridges(self, snapshot: WorkspaceSnapshot) -> list[dict[str, Any]]:
        """
        Detect configured bridges from workspace YAML.

        Bridges are external system connectors (Snowflake, Databricks, etc.)
        configured in the workspace but requiring env-var credentials.
        """
        bridges = snapshot.workspace_yaml.get("bridges", [])
        if isinstance(bridges, list):
            return bridges
        return []
