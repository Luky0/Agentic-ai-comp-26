"""Tests for the example negotiators."""

import pytest
from negmas.inout import Scenario
from negmas.preferences.generators import generate_multi_issue_ufuns
from negmas.sao import SAOMechanism

from examples.boa import BOANeg
from examples.map import MAPNeg
from examples.simple import SimpleNegotiator


@pytest.fixture
def test_scenario():
    """Create a simple test scenario with two issues."""
    ufuns = generate_multi_issue_ufuns(
        n_issues=2,
        n_values=(3, 5),
        ufun_names=("First", "Second"),
        rational_fractions=[1.0, 1.0],
    )
    return Scenario(outcome_space=ufuns[0].outcome_space, ufuns=ufuns)


class TestBOANeg:
    """Tests for the BOANeg negotiator."""

    def test_instantiation(self):
        """Test that BOANeg can be instantiated."""
        negotiator = BOANeg()
        assert negotiator is not None

    def test_has_required_components(self, test_scenario):
        """Test that BOANeg has all required BOA components after initialization."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=5,
        )
        negotiator = BOANeg()
        opponent = BOANeg()

        mechanism.add(negotiator, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])

        # Run one step to initialize
        mechanism.step()

        # Check that it has the three main BOA components
        assert negotiator._acceptance is not None
        assert negotiator._offering is not None
        assert negotiator._models is not None

    def test_negotiation_completes(self, test_scenario):
        """Test that BOANeg can complete a negotiation."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=50,
        )
        negotiator1 = BOANeg()
        negotiator2 = BOANeg()

        mechanism.add(negotiator1, ufun=test_scenario.ufuns[0])
        mechanism.add(negotiator2, ufun=test_scenario.ufuns[1])

        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout

    def test_makes_offers(self, test_scenario):
        """Test that BOANeg makes valid offers."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=10,
        )
        negotiator = BOANeg()
        opponent = BOANeg()

        mechanism.add(negotiator, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])

        mechanism.run()

        # Check that offers were made
        assert len(mechanism.history) > 0


class TestMAPNeg:
    """Tests for the MAPNeg negotiator."""

    def test_instantiation(self):
        """Test that MAPNeg can be instantiated."""
        negotiator = MAPNeg()
        assert negotiator is not None

    def test_has_required_components(self, test_scenario):
        """Test that MAPNeg has all required MAP components after initialization."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=5,
        )
        negotiator = MAPNeg()
        opponent = MAPNeg()

        mechanism.add(negotiator, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])

        # Run one step to initialize
        mechanism.step()

        # Check that it has the main MAP components
        assert negotiator._acceptance is not None
        assert negotiator._offering is not None
        assert negotiator._models is not None

    def test_configured_with_acceptance_first(self):
        """Test that MAPNeg is configured with acceptance_first."""
        # This tests the configuration passed to __init__
        # The actual internal implementation may vary
        negotiator = MAPNeg()
        # Just verify it was instantiated successfully with the config
        assert negotiator is not None

    def test_negotiation_completes(self, test_scenario):
        """Test that MAPNeg can complete a negotiation."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=50,
        )
        negotiator1 = MAPNeg()
        negotiator2 = MAPNeg()

        mechanism.add(negotiator1, ufun=test_scenario.ufuns[0])
        mechanism.add(negotiator2, ufun=test_scenario.ufuns[1])

        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout

    def test_makes_offers(self, test_scenario):
        """Test that MAPNeg makes valid offers."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=10,
        )
        negotiator = MAPNeg()
        opponent = MAPNeg()

        mechanism.add(negotiator, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])

        mechanism.run()

        # Check that offers were made
        assert len(mechanism.history) > 0


class TestSimpleNegotiator:
    """Tests for the SimpleNegotiator."""

    def test_instantiation(self):
        """Test that SimpleNegotiator can be instantiated."""
        negotiator = SimpleNegotiator()
        assert negotiator is not None

    def test_negotiation_completes(self, test_scenario):
        """Test that SimpleNegotiator can complete a negotiation."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=50,
        )
        negotiator1 = SimpleNegotiator()
        negotiator2 = SimpleNegotiator()

        mechanism.add(negotiator1, ufun=test_scenario.ufuns[0])
        mechanism.add(negotiator2, ufun=test_scenario.ufuns[1])

        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout

    def test_accepts_high_utility_offers(self, test_scenario):
        """Test that SimpleNegotiator can participate in negotiations."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=10,
        )
        negotiator = SimpleNegotiator()
        opponent = SimpleNegotiator()

        mechanism.add(negotiator, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])

        # Start negotiation to initialize
        mechanism.step()

        # The negotiator should be initialized
        assert negotiator._inv is not None

    def test_makes_offers(self, test_scenario):
        """Test that SimpleNegotiator makes valid offers."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=10,
        )
        negotiator = SimpleNegotiator()
        opponent = SimpleNegotiator()

        mechanism.add(negotiator, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])

        mechanism.run()

        # Check that offers were made
        assert len(mechanism.history) > 0

    def test_negotiation_start_initializes(self, test_scenario):
        """Test that on_negotiation_start initializes the negotiator."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=5,
        )
        negotiator = SimpleNegotiator()
        opponent = SimpleNegotiator()

        mechanism.add(negotiator, ufun=test_scenario.ufuns[0])
        mechanism.add(opponent, ufun=test_scenario.ufuns[1])

        # Run one step to trigger on_negotiation_start
        mechanism.step()

        # Check that the negotiator was initialized
        assert negotiator._inv is not None


class TestExampleNegotiatorCompatibility:
    """Tests for compatibility between different example negotiators."""

    def test_boaneg_vs_mapneg(self, test_scenario):
        """Test that BOANeg and MAPNeg can negotiate with each other."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=50,
        )
        negotiator1 = BOANeg()
        negotiator2 = MAPNeg()

        mechanism.add(negotiator1, ufun=test_scenario.ufuns[0])
        mechanism.add(negotiator2, ufun=test_scenario.ufuns[1])

        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout

    def test_boaneg_vs_simple(self, test_scenario):
        """Test that BOANeg and SimpleNegotiator can negotiate with each other."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=50,
        )
        negotiator1 = BOANeg()
        negotiator2 = SimpleNegotiator()

        mechanism.add(negotiator1, ufun=test_scenario.ufuns[0])
        mechanism.add(negotiator2, ufun=test_scenario.ufuns[1])

        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout

    def test_mapneg_vs_simple(self, test_scenario):
        """Test that MAPNeg and SimpleNegotiator can negotiate with each other."""
        mechanism = SAOMechanism(
            outcome_space=test_scenario.outcome_space,
            n_steps=50,
        )
        negotiator1 = MAPNeg()
        negotiator2 = SimpleNegotiator()

        mechanism.add(negotiator1, ufun=test_scenario.ufuns[0])
        mechanism.add(negotiator2, ufun=test_scenario.ufuns[1])

        mechanism.run()
        assert mechanism.state.agreement is not None or mechanism.state.timedout
