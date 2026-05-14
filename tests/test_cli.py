"""Tests for the ANL2026 CLI application."""

from typer.testing import CliRunner

from main import app, generate_random_scenarios, load_scenarios

runner = CliRunner()


class TestGenerateRandomScenarios:
    """Tests for the generate_random_scenarios function."""

    def test_generates_single_scenario(self):
        scenarios = generate_random_scenarios(n_scenarios=1)
        assert len(scenarios) == 1
        assert scenarios[0].outcome_space is not None
        assert len(scenarios[0].ufuns) == 2

    def test_generates_multiple_scenarios(self):
        scenarios = generate_random_scenarios(n_scenarios=3)
        assert len(scenarios) == 3
        for s in scenarios:
            assert s.outcome_space is not None
            assert len(s.ufuns) == 2

    def test_varying_issues(self):
        """Test that scenarios have between 1 and 4 issues."""
        scenarios = generate_random_scenarios(n_scenarios=10)
        issue_counts = [len(s.outcome_space.issues) for s in scenarios]
        assert all(1 <= c <= 4 for c in issue_counts)


class TestLoadScenarios:
    """Tests for the load_scenarios function."""

    def test_loads_all_scenarios_when_none(self):
        scenarios = load_scenarios(None)
        assert len(scenarios) > 0

    def test_loads_specific_scenario_by_name(self):
        scenarios = load_scenarios(["Camera"])
        assert len(scenarios) == 1

    def test_loads_multiple_scenarios_by_name(self):
        scenarios = load_scenarios(["Camera", "Car"])
        assert len(scenarios) == 2

    def test_loads_all_scenarios_with_all_keyword(self):
        all_scenarios = load_scenarios(None)
        scenarios_with_all = load_scenarios(["all"])
        assert len(scenarios_with_all) == len(all_scenarios)

    def test_loads_all_scenarios_with_all_keyword_case_insensitive(self):
        all_scenarios = load_scenarios(None)
        scenarios_with_all = load_scenarios(["ALL"])
        assert len(scenarios_with_all) == len(all_scenarios)


class TestRunCommand:
    """Tests for the 'run' command."""

    def test_run_help(self):
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "Run a single negotiation" in result.stdout

    def test_run_with_scenario(self):
        result = runner.invoke(app, ["run", "--scenario", "Camera", "--no-plot"])
        assert result.exit_code == 0
        assert "Agreement:" in result.stdout

    def test_run_with_generate_scenarios(self):
        result = runner.invoke(app, ["run", "--generate-scenario", "--no-plot"])
        assert result.exit_code == 0
        assert "Using randomly generated scenario" in result.stdout
        assert "Agreement:" in result.stdout

    def test_run_with_opponent(self):
        result = runner.invoke(
            app,
            [
                "run",
                "--scenario",
                "Camera",
                "--opponent",
                "negmas.sao.BoulwareTBNegotiator",
                "--no-plot",
            ],
        )
        assert result.exit_code == 0
        assert "Agreement:" in result.stdout

    def test_run_with_verbose(self):
        result = runner.invoke(
            app, ["run", "--scenario", "Camera", "--verbose", "--no-plot"]
        )
        assert result.exit_code == 0


class TestTournamentCommand:
    """Tests for the 'tournament' command."""

    def test_tournament_help(self):
        result = runner.invoke(app, ["tournament", "--help"])
        assert result.exit_code == 0
        assert "Run a complete tournament" in result.stdout

    def test_tournament_with_single_scenario(self):
        result = runner.invoke(
            app,
            [
                "tournament",
                "--scenario",
                "Camera",
                "--competitor",
                "negmas.sao.BoulwareTBNegotiator",
                "--competitor",
                "mynegotiator.MyNegotiator",
            ],
        )
        assert result.exit_code == 0
        assert "Tournament Results" in result.stdout

    def test_tournament_with_generate_scenarios(self):
        result = runner.invoke(
            app,
            [
                "tournament",
                "--generate-scenarios",
                "2",
                "--competitor",
                "negmas.sao.BoulwareTBNegotiator",
                "--competitor",
                "mynegotiator.MyNegotiator",
            ],
        )
        assert result.exit_code == 0
        assert "Generated 2 random scenarios" in result.stdout
        assert "Tournament Results" in result.stdout

    def test_tournament_combines_scenarios_and_generated(self):
        result = runner.invoke(
            app,
            [
                "tournament",
                "--scenario",
                "Camera",
                "--generate-scenarios",
                "1",
                "--competitor",
                "negmas.sao.BoulwareTBNegotiator",
                "--competitor",
                "mynegotiator.MyNegotiator",
            ],
        )
        assert result.exit_code == 0
        assert "Generated 1 random scenarios" in result.stdout
        assert "Running tournament with 2 scenarios" in result.stdout
        assert "Tournament Results" in result.stdout
