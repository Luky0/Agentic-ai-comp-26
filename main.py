#! /usr/bin/env python3
"""
ANL2026 CLI application for running negotiations and tournaments.

This CLI is designed to be easy to use (not easy to read) so that you can
quickly run negotiations and tournaments without worrying about code. It also
includes options for generating random scenarios, plotting results, and
exporting traces. You do not need to understand the code to use the CLI, but
you can read it if you want.

"""

import random
import sys
import tempfile
import textwrap
import webbrowser
from pathlib import Path

# Add project root to sys.path so local modules like 'examples' can be imported
sys.path.insert(0, str(Path(__file__).parent))

from negmas.helpers import get_class, instantiate
from negmas.inout import Scenario, get_full_type_name, unique_name
from negmas.preferences import compare_ufuns
from negmas.preferences.generators import generate_multi_issue_ufuns
from negmas.sao import SAOMechanism
from negmas.tournaments.neg.simple import cartesian_tournament
from rich import print
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
import typer
from typing import Annotated

try:
    from .nashty import NashtyNegotiator
except ImportError:
    from nashty import NashtyNegotiator

MY_NEGOTIATOR = get_full_type_name(NashtyNegotiator)

app = typer.Typer(help="ANL2026 CLI application")


def generate_random_scenarios(
    n_scenarios: int = 1,
    n_issues: tuple[int, int] = (1, 4),
    n_values: tuple[int, int] = (5, 10),
    rational_fraction: float = 1.0,
) -> list[Scenario]:
    """Generate random negotiation scenarios."""
    scenarios = []
    for _ in range(n_scenarios):
        ufuns = generate_multi_issue_ufuns(
            n_issues=random.randint(*n_issues),
            n_values=n_values,
            ufun_names=("First", "Second"),
            rational_fractions=[rational_fraction, rational_fraction],
        )
        scenarios.append(Scenario(outcome_space=ufuns[0].outcome_space, ufuns=ufuns))  # type: ignore
    return scenarios


def progress_callback(message: str, i: int, n: int, conf: dict | None = None) -> None:
    print(message)


def calc_scores(m: SAOMechanism) -> dict[str, dict[str, float]]:
    """Compute scores for the given agreement according the ANL 2026 rules."""

    # extract the agreement
    agreement = m.agreement

    # extract negotiator names
    negotiators = [_.__class__.__name__ for _ in m.negotiators]

    # find advantages (utility above reserved value)
    advantages = [
        float(_.ufun(agreement)) - float(_.ufun.reserved_value) if _.ufun else 0.0
        for _ in m.negotiators
    ]

    # calculate modeling accuracies
    ufuns = [_.ufun for _ in m.negotiators]
    models = [_.opponent_ufun for _ in m.negotiators]
    models.reverse()
    accuracies = [
        (1 + compare_ufuns(u, m, method="kendall")) / 2 for u, m in zip(ufuns, models)
    ]

    # normalize accuracies so that we divide one point among all negotiators with
    # negotiators with higher accuracy getting higher part of this point.
    accsum = sum(accuracies)
    if accsum > 0:
        accuracies = [_ / accsum for _ in accuracies]
    else:
        accuracies = [0] * len(negotiators)
    # we need to reverse to model concealing (higher accuracy for opponent means lower concealing score)
    accuracies.reverse()
    # return final scores. You can improve your score in one of three ways:
    # 1. Increase your advantage (negotiating a better deal for yourself)
    # 2. Increase your modeling accuracy (better opponent modeling)
    # 3. Decrease your opponent's accuracy (confuse their opponent modeling)
    return dict(
        zip(
            negotiators,
            (
                dict(Advantage=adv, Concealing=acc, Score=adv + acc)
                for adv, acc in zip(advantages, accuracies)
            ),
        )
    )


@app.command()
def run(
    # Scenario Loading Options
    scenario: Annotated[
        str | None,
        typer.Option(
            help="Scenario name to use. If not provided, a random scenario is selected from the scenarios folder.",
            rich_help_panel="Scenario Loading",
        ),
    ] = None,
    # Scenario Generation Options
    generate: Annotated[
        bool,
        typer.Option(
            "--generate-scenario/--no-generate-scenario",
            help="Generate a random scenario instead of loading one.",
            rich_help_panel="Scenario Generation",
        ),
    ] = False,
    rational_fraction: Annotated[
        float,
        typer.Option(
            help="Fraction of rational outcomes in generated scenarios (0.0-1.0).",
            min=0.0,
            max=1.0,
            rich_help_panel="Scenario Generation",
        ),
    ] = 1.0,
    # Negotiation Options
    negotiator: Annotated[
        str | None,
        typer.Option(
            "--negotiator",
            "--agent",
            help=f"Your negotiator class (module.ClassName). If not provided, uses {MY_NEGOTIATOR}.",
            rich_help_panel="Negotiation",
        ),
    ] = None,
    opponent: Annotated[
        str | None,
        typer.Option(
            help="Opponent class to negotiate against. If not provided, a random opponent is selected.",
            rich_help_panel="Negotiation",
        ),
    ] = None,
    negotiator_first: Annotated[
        bool | None,
        typer.Option(
            "--negotiator-first/--opponent-first",
            help="Whether your negotiator goes first (default: randomly chosen).",
            rich_help_panel="Negotiation",
        ),
    ] = None,
    # Output Options
    verbose: Annotated[
        bool,
        typer.Option(
            help="Show full negotiation trace with utilities.",
            rich_help_panel="Output",
        ),
    ] = False,
    plot: Annotated[
        bool,
        typer.Option(
            help="Plot the negotiation trace.",
            rich_help_panel="Output",
        ),
    ] = True,
    show_trace: Annotated[
        bool,
        typer.Option(
            help="Display full trace as a formatted table in terminal.",
            rich_help_panel="Output",
        ),
    ] = False,
    export_trace: Annotated[
        str | None,
        typer.Option(
            help="Export full trace to CSV file (provide file path).",
            rich_help_panel="Output",
        ),
    ] = None,
    trace_browser: Annotated[
        bool,
        typer.Option(
            "--trace-browser/--no-trace-browser",
            help="Open full trace in browser as an interactive table.",
            rich_help_panel="Output",
        ),
    ] = False,
):
    """Run a single negotiation against an opponent."""
    if generate:
        s = generate_random_scenarios(
            n_scenarios=1, rational_fraction=rational_fraction
        )[0]
        print("[blue]Using randomly generated scenario[/blue]")
    elif scenario is None:
        scenario = random.choice(
            list((Path(__file__).parent / "scenarios").iterdir())
        ).name
        print(
            f"Will use scenario [blue]{scenario}[/blue] (to select a specific scenario pass --scenario=<scenario_name>)"
        )
        s = Scenario.load(
            Path(__file__).parent / "scenarios" / scenario, ignore_discount=True
        )
        assert s is not None, f"Could not load scenario {scenario}"
    else:
        s = Scenario.load(
            Path(__file__).parent / "scenarios" / scenario, ignore_discount=True
        )
        assert s is not None, f"Could not load scenario {scenario}"
    if opponent is None:
        opponent = random.choice(
            (
                "negmas.sao.BoulwareTBNegotiator",
                "examples.boa.BOANeg",
                "examples.map.MAPNeg",
                "examples.simple.SimpleNegotiator",
            )
        )
        print(
            f"Will use opponent [green]{opponent}[/green] (to select a specific opponent pass --opponent=<opponent_class>)"
        )

    # Set default negotiator if not provided
    if negotiator is None:
        negotiator = MY_NEGOTIATOR
        print(
            f"Will use negotiator [magenta]{negotiator}[/magenta] (to select a specific negotiator pass --negotiator=<negotiator_class>)"
        )
    else:
        print(f"Using negotiator [magenta]{negotiator}[/magenta]")

    # Determine order
    if negotiator_first is None:
        negotiator_first = random.choice([True, False])
        print(
            f"Order: [yellow]{'Negotiator first' if negotiator_first else 'Opponent first'}[/yellow] (randomly chosen)"
        )
    else:
        print(
            f"Order: [yellow]{'Negotiator first' if negotiator_first else 'Opponent first'}[/yellow]"
        )

    opp_name = opponent.split(".")[-1]
    neg_name = negotiator.split(".")[-1]
    m = SAOMechanism(n_steps=100, outcome_space=s.outcome_space)

    # Add negotiators in the correct order
    if negotiator_first:
        m.add(instantiate(negotiator, ufun=s.ufuns[0], id=neg_name, name=neg_name))
        m.add(instantiate(opponent, ufun=s.ufuns[1], id=opp_name, name=opp_name))
    else:
        m.add(instantiate(opponent, ufun=s.ufuns[0], id=opp_name, name=opp_name))
        m.add(instantiate(negotiator, ufun=s.ufuns[1], id=neg_name, name=neg_name))
    m.run()

    # Get the trace dataframe
    trace_df = m.full_trace_with_utils_df()

    # Handle trace display options
    if verbose:
        print(trace_df)

    if show_trace:
        # Display trace as a rich table in terminal
        console = Console()
        table = Table(title="Negotiation Trace", show_lines=True)

        # Add columns
        for col in trace_df.columns:
            table.add_column(str(col), style="cyan")

        # Add rows
        for _, row in trace_df.iterrows():
            table.add_row(*[str(val) for val in row])

        console.print(table)

    if export_trace:
        # Export trace to CSV
        export_path = Path(export_trace)
        trace_df.to_csv(export_path, index=False)
        print(f"[green]Trace exported to {export_path}[/green]")

    if trace_browser:
        # Create an HTML table and open in browser
        html_content = textwrap.dedent(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Negotiation Trace</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                        padding: 20px;
                        background-color: #f5f5f5;
                    }}
                    h1 {{
                        color: #333;
                        text-align: center;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        background-color: white;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        margin: 20px 0;
                    }}
                    th {{
                        background-color: #2c3e50;
                        color: white;
                        padding: 12px;
                        text-align: left;
                        position: sticky;
                        top: 0;
                        z-index: 10;
                    }}
                    td {{
                        padding: 10px 12px;
                        border-bottom: 1px solid #ddd;
                    }}
                    tr:hover {{
                        background-color: #f8f9fa;
                    }}
                    tr:nth-child(even) {{
                        background-color: #fafafa;
                    }}
                    .container {{
                        max-width: 100%;
                        overflow-x: auto;
                    }}
                </style>
            </head>
            <body>
                <h1>Negotiation Trace</h1>
                <div class="container">
                    {trace_df.to_html(index=False, classes="trace-table", border=0)}
                </div>
            </body>
            </html>
        """)
        # Create a temporary HTML file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html_content)
            temp_path = f.name

        # Open in browser
        webbrowser.open(f"file://{temp_path}")
        print("[green]Trace opened in browser[/green]")

    if plot:
        m.plot()
    print(f"Agreement: {m.agreement}")
    print(calc_scores(m))


DEFAULT_COMPETITORS = [
    "negmas.sao.BoulwareTBNegotiator",
    MY_NEGOTIATOR,
    "examples.simple.SimpleNegotiator",
    "examples.map.MAPNeg",
    "examples.boa.BOANeg",
]


SCENARIOS_DIR = Path(__file__).parent / "scenarios"


def load_scenarios(scenario_paths: list[str] | None) -> list[Scenario]:
    """Load scenarios from names or full paths. If None, load all from scenarios directory."""
    if scenario_paths is None:
        paths = list(SCENARIOS_DIR.iterdir())
    elif len(scenario_paths) == 1 and scenario_paths[0].lower() == "all":
        paths = list(SCENARIOS_DIR.iterdir())
    else:
        paths = []
        for s in scenario_paths:
            p = Path(s)
            if p.is_absolute() and p.exists():
                paths.append(p)
            else:
                # Treat as folder name under scenarios directory
                paths.append(SCENARIOS_DIR / s)
    scenarios = [Scenario.load(p, ignore_discount=True) for p in paths]
    return [s for s in scenarios if s is not None]


@app.command()
def tournament(
    # Tournament Options
    name: Annotated[
        str | None,
        typer.Option(
            help="Tournament name. If not provided, a unique name is generated.",
            rich_help_panel="Tournament",
        ),
    ] = None,
    competitor: Annotated[
        list[str] | None,
        typer.Option(
            help="Competitor classes to include. Can be specified multiple times. If not provided, uses default competitors.",
            rich_help_panel="Tournament",
        ),
    ] = None,
    # Scenario Loading Options
    scenario: Annotated[
        list[str] | None,
        typer.Option(
            help="Scenario names (folder names under scenarios) or full paths. Use 'all' to load all scenarios. Can be specified multiple times.",
            rich_help_panel="Scenario Loading",
        ),
    ] = None,
    # Scenario Generation Options
    generate: Annotated[
        int,
        typer.Option(
            "--generate-scenarios",
            help="Generate N random scenarios instead of loading.",
            rich_help_panel="Scenario Generation",
        ),
    ] = 0,
    rational_fraction: Annotated[
        float,
        typer.Option(
            help="Fraction of rational outcomes in generated scenarios (0.0-1.0).",
            min=0.0,
            max=1.0,
            rich_help_panel="Scenario Generation",
        ),
    ] = 1.0,
    # Execution Options
    verbosity: Annotated[
        int,
        typer.Option(
            help="Verbosity level for tournament execution (0 = silent, higher = more verbose).",
            min=0,
            max=5,
            rich_help_panel="Execution",
        ),
    ] = 0,
    parallel: Annotated[
        bool,
        typer.Option(
            help="Run tournament in parallel mode (use all cores).",
            rich_help_panel="Execution",
        ),
    ] = False,
):
    """Run a complete tournament with all competitors."""
    if name is None:
        name = unique_name("anl", sep="")
    if competitor is None:
        competitor = DEFAULT_COMPETITORS
    path = Path.home() / "negmas" / "anl2026" / "tournaments" / name

    # Load scenarios from paths if provided, otherwise load all from scenarios directory
    if scenario is not None:
        scenarios = load_scenarios(scenario)
    elif generate == 0:
        scenarios = load_scenarios(None)
    else:
        scenarios = []

    # Add generated scenarios if requested
    if generate > 0:
        generated = generate_random_scenarios(
            n_scenarios=generate, rational_fraction=rational_fraction
        )
        scenarios.extend(generated)
        print(f"[blue]Generated {generate} random scenarios[/blue]")

    print(f"[blue]Running tournament with {len(scenarios)} scenarios[/blue]")
    competitor_classes = [get_class(c) for c in competitor]
    results = cartesian_tournament(
        scenarios=scenarios,
        competitors=competitor_classes,  # type: ignore
        opponent_modeling_metrics=("anl2026",),
        final_score=("opp_anl2026", "mean"),
        path=path,
        verbosity=verbosity,
        njobs=-1 if not parallel else 0,
        progress_callback=progress_callback,
        sort_runs=True,
    )
    print(results.final_scores)
    print(f"All Tournament Results can be found in {path}")


@app.command()
def info():
    """Show development workflows and submission instructions."""
    # Read from source directory, not installed package
    readme_path = Path(__file__).resolve().parent / "README.md"
    if not readme_path.exists():
        print("[red]README.md not found[/red]")
        raise typer.Exit(1)

    content = readme_path.read_text()

    # Sections to extract and display
    sections_to_show = [
        "## Getting Started: Rename Your Agent",
        "## Development Workflows",
        "## Submission",
    ]

    console = Console()
    for section_header in sections_to_show:
        if section_header in content:
            start = content.find(section_header)
            end = content.find("\n## ", start + 1)
            if end == -1:
                end = len(content)
            section = content[start:end].strip()
            console.print(Markdown(section))
            console.print()


if __name__ == "__main__":
    app()
