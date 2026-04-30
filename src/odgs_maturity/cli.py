"""
CLI entry point for odgs-maturity.

Commands:
  odgs-maturity score [--workspace PATH] [--json]
  odgs-maturity charter [--workspace PATH] [--output PATH]
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="odgs-maturity",
    help="ODGS Governance Maturity Assessment",
    no_args_is_help=True,
)
console = Console()


@app.command()
def score(
    workspace: Optional[Path] = typer.Option(
        None, "--workspace", "-w",
        help="Path to ODGS workspace (auto-detects if omitted)",
    ),
    output_json: bool = typer.Option(
        False, "--json", "-j",
        help="Output as JSON instead of rich table",
    ),
):
    """Run maturity assessment against an ODGS workspace."""
    import json as json_mod

    from .scoring.engine import score_workspace
    from .workspace.reader import WorkspaceReader

    reader = WorkspaceReader()
    snapshot = reader.read(workspace)

    if snapshot.errors:
        for err in snapshot.errors:
            console.print(f"[yellow]⚠ {err}[/yellow]")

    result = score_workspace(snapshot)

    if output_json:
        print(json_mod.dumps(result.to_dict(), indent=2))
        return

    # Rich output
    _render_score(result)


def _render_score(result):
    """Render maturity score as rich console output."""
    from .scoring.models import CostFlag

    agg = result.aggregate_score
    level = result.level

    # Progress bar
    filled = int(agg / 100 * 30)
    bar = "█" * filled + "░" * (30 - filled)

    header = (
        f"  ODGS Governance Maturity Score\n\n"
        f"  {bar}  {agg}%  ({level.label})\n"
    )
    console.print(Panel(header, title="[bold]Assessment[/bold]", border_style="blue"))

    # Pillar table
    table = Table(title="Pillar Breakdown", show_lines=True)
    table.add_column("Pillar", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Level")
    table.add_column("Gaps", justify="right")
    table.add_column("Flag")

    flag_style = {
        CostFlag.GREEN: "[green]●[/green]",
        CostFlag.AMBER: "[yellow]●[/yellow]",
        CostFlag.RED: "[red]●[/red]",
    }

    for pillar, pr in result.pillars.items():
        table.add_row(
            pillar.display_name,
            f"{pr.score}%",
            pr.level.label,
            str(len(pr.gaps)),
            flag_style.get(pr.cost_flag, "?"),
        )

    console.print(table)

    # Red flags summary
    reds = result.red_flags
    if reds:
        console.print(f"\n[red bold]⚠ {len(reds)} critical gap(s):[/red bold]")
        for r in reds:
            console.print(f"  [red]• {r.rule_name}[/red]: {r.recommendation}")

    console.print(f"\n[dim]{result.total_rules} rules evaluated, "
                  f"{result.total_gaps} gaps found[/dim]")


@app.command()
def charter(
    workspace: Optional[Path] = typer.Option(
        None, "--workspace", "-w",
        help="Path to ODGS workspace",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output file path (default: stdout)",
    ),
    output_json: bool = typer.Option(
        False, "--json", "-j",
        help="Output as JSON instead of Markdown",
    ),
    charter_type: Optional[str] = typer.Option(
        None, "--type", "-t",
        help="Charter type: lifecycle | kpi | strategic",
    ),
    non_interactive: bool = typer.Option(
        False, "--non-interactive",
        help="Skip prompts, use defaults (for CI/scripts)",
    ),
):
    """Generate an improvement charter from maturity assessment gaps."""
    import json as json_mod

    from .charter.generator import generate_charter
    from .charter.models import CharterType
    from .charter.export import to_markdown, to_json
    from .data.loader import load_business_lifecycles
    from .scoring.engine import score_workspace
    from .workspace.reader import WorkspaceReader

    # Step 1: Score the workspace
    reader = WorkspaceReader()
    snapshot = reader.read(workspace)
    result = score_workspace(snapshot)

    console.print(f"\n[bold]Maturity Score:[/bold] {result.aggregate_score}% "
                  f"({result.level.label}) — {result.total_gaps} gaps\n")

    if result.total_gaps == 0:
        console.print("[green]✓ No gaps found — no charter needed![/green]")
        return

    # Step 2: Select charter type
    selected_type = _resolve_charter_type(charter_type, non_interactive)
    user_inputs: dict = {}

    # Step 3: Gather context based on charter type
    if selected_type == CharterType.LIFECYCLE_PAIN_POINT and not non_interactive:
        user_inputs = _prompt_lifecycle_context()
    elif selected_type == CharterType.KPI_IMPROVEMENT and not non_interactive:
        user_inputs = _prompt_kpi_context()
    elif selected_type == CharterType.STRATEGIC_OR_AI and not non_interactive:
        user_inputs = _prompt_strategic_context()

    # Step 4: Generate charter
    with console.status("[bold blue]Generating charter..."):
        charter_doc = generate_charter(result, selected_type, **user_inputs)

    # Step 5: Export
    if output_json:
        content = to_json(charter_doc)
    else:
        content = to_markdown(charter_doc)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        console.print(f"\n[green]✓ Charter saved to {output}[/green]")
    else:
        console.print()
        print(content)

    console.print(f"\n[dim]Charter type: {selected_type.display_name}[/dim]")
    console.print(f"[dim]{len(charter_doc.sections)} sections generated[/dim]")


def _resolve_charter_type(type_str: Optional[str], non_interactive: bool):
    """Resolve charter type from CLI arg or interactive prompt."""
    from .charter.models import CharterType

    type_map = {
        "lifecycle": CharterType.LIFECYCLE_PAIN_POINT,
        "kpi": CharterType.KPI_IMPROVEMENT,
        "strategic": CharterType.STRATEGIC_OR_AI,
    }

    if type_str and type_str.lower() in type_map:
        return type_map[type_str.lower()]

    if non_interactive:
        return CharterType.LIFECYCLE_PAIN_POINT

    console.print("[bold]Select charter type:[/bold]\n")
    for i, ct in enumerate(CharterType, 1):
        console.print(f"  [cyan]{i}[/cyan]. {ct.display_name}")
        console.print(f"     [dim]{ct.description}[/dim]\n")

    choice = typer.prompt("Enter choice (1-3)", default="1")
    idx = int(choice) - 1
    return list(CharterType)[max(0, min(idx, 2))]


def _prompt_lifecycle_context() -> dict:
    """Interactive prompts for Lifecycle Pain Point charter."""
    from .data.loader import load_business_lifecycles

    lifecycles = load_business_lifecycles()

    console.print("\n[bold]Select a business lifecycle:[/bold]\n")
    for i, lc in enumerate(lifecycles, 1):
        console.print(f"  [cyan]{i}[/cyan]. {lc['lifecycleName']}")
        console.print(f"     [dim]{lc['description'][:80]}...[/dim]")

    lc_choice = int(typer.prompt("\nLifecycle (1-7)", default="1")) - 1
    lc_choice = max(0, min(lc_choice, len(lifecycles) - 1))
    selected_lc = lifecycles[lc_choice]

    console.print(f"\n[bold]Stages in {selected_lc['lifecycleName']}:[/bold]\n")
    stages = selected_lc.get("stages", [])
    for i, stage in enumerate(stages, 1):
        console.print(f"  [cyan]{i}[/cyan]. {stage['stageName']}")

    stage_choice = int(typer.prompt(f"\nStage (1-{len(stages)})", default="1")) - 1
    stage_choice = max(0, min(stage_choice, len(stages) - 1))
    selected_stage = stages[stage_choice]

    pain_point = typer.prompt(
        "\nDescribe the primary pain point (or press Enter for default)",
        default=f"Data quality issues affecting {selected_stage['stageName'].lower()}",
    )

    return {
        "lifecycle_id": selected_lc["lifecycleId"],
        "lifecycle_name": selected_lc["lifecycleName"],
        "stage_id": selected_stage["stageId"],
        "stage_name": selected_stage["stageName"],
        "pain_points": [pain_point],
    }


def _prompt_kpi_context() -> dict:
    """Interactive prompts for KPI Improvement charter."""
    kpi_name = typer.prompt("KPI name", default="On-Time Delivery Rate")
    kpi_objective = typer.prompt("KPI business area", default="Operational Excellence")
    sources = typer.prompt(
        "Data sources (comma-separated)",
        default="ERP, CRM, Warehouse Management",
    )
    return {
        "kpi_name": kpi_name,
        "kpi_objective": kpi_objective,
        "data_sources": [s.strip() for s in sources.split(",")],
    }


def _prompt_strategic_context() -> dict:
    """Interactive prompts for Strategic/AI Initiative charter."""
    initiative = typer.prompt(
        "Strategic initiative name",
        default="Data-Driven Decision Making Programme",
    )
    ai_use_case = typer.prompt(
        "AI/ML use case (or leave blank for strategic-only)",
        default="",
    )
    return {
        "initiative_name": initiative,
        "ai_use_case": ai_use_case,
    }


if __name__ == "__main__":
    app()
