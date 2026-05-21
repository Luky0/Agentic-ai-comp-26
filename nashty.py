import random
from negmas.sao import SAOState, ResponseType
from negmas.outcomes import Outcome
from negmas.sao.components.offering import TimeBasedOfferingPolicy
from negmas.sao.components.acceptance import ACNext
from negmas.gb.components.genius.models import GSmithFrequencyModel
from negmas.sao.negotiators.modular import BOANegotiator

# -------------------------------------------------------------------
# OPPONENT MODEL (OM)
# -------------------------------------------------------------------
def get_opponent_model():
    """
    Baseline: Frequency-Based Modeling.
    We use the built-in GSmithFrequencyModel which counts the frequency 
    of the opponent's requested values to estimate their utility.
    """
    return GSmithFrequencyModel()


# -------------------------------------------------------------------
# CONCEALING BIDDING STRATEGY (BS)
# -------------------------------------------------------------------
class ConcealingBiddingStrategy(TimeBasedOfferingPolicy):
    """
    Time-Dependent Bidding (Boulware) with Iso-Utility Noise.
    Generates a target utility based on time, then randomly selects an
    outcome from a band of similar utilities to confuse the opponent.
    """
    def __init__(self, tolerance: float = 0.05, *args, **kwargs):
        self.tolerance = tolerance
        self._rational_outcomes_with_utils = None
        super().__init__(*args, **kwargs)

    def __call__(self, state, dest=None) -> Outcome | None:
        if self._rational_outcomes_with_utils is None and self.negotiator and self.negotiator.ufun:
            outcomes = list(self.negotiator.nmi.outcome_space.enumerate_or_sample())
            self._rational_outcomes_with_utils = [
                (float(self.negotiator.ufun(o)), o) for o in outcomes 
                if float(self.negotiator.ufun(o)) >= float(self.negotiator.ufun.reserved_value)
            ]

        # Let the base class calculate the base offer (must pass dest)
        base_offer = super().__call__(state, dest=dest)
        
        if base_offer is None or self.negotiator.ufun is None:
            return base_offer
            
        # Explicitly cast target to float
        target_utility = float(self.negotiator.ufun(base_offer))
        
        # Iso-Utility Logic
        if self._rational_outcomes_with_utils:
            candidates = [
                outcome for util, outcome in self._rational_outcomes_with_utils
                if abs(util - target_utility) <= self.tolerance
            ]
            
            if candidates:
                return random.choice(candidates)
        
        return base_offer


# -------------------------------------------------------------------
# ACCEPTANCE STRATEGY (AS)
# -------------------------------------------------------------------
class CustomAcceptanceStrategy(ACNext):
    """
    AC_next combined with an End-of-Game safety net and an Absolute Good Deal threshold.
    """
    def __call__(self, state, offer=None, source=None):
        # Let the base ACNext logic decide first (pass required kwargs)
        base_response = super().__call__(state, offer=offer, source=source)
        
        if base_response == ResponseType.ACCEPT_OFFER:
            return ResponseType.ACCEPT_OFFER

        current_offer = offer if offer is not None else state.current_offer
        
        if current_offer is None or self.negotiator.ufun is None:
            return ResponseType.REJECT_OFFER

        offer_utility = float(self.negotiator.ufun(current_offer))
        reserved_value = float(self.negotiator.ufun.reserved_value)
        max_utility = float(self.negotiator.ufun.max())

        # End-of-game Safety Net
        if state.relative_time > 0.95:
            if offer_utility > reserved_value:
                return ResponseType.ACCEPT_OFFER

        # Absolute Good Deal
        if offer_utility >= (max_utility * 0.90):
            return ResponseType.ACCEPT_OFFER

        return ResponseType.REJECT_OFFER

# -------------------------------------------------------------------
# THE AGENT
# -------------------------------------------------------------------
class NashtyNegotiator(BOANegotiator):
    def __init__(self, *args, **kwargs):
        
        my_offering = ConcealingBiddingStrategy()
        
        my_acceptance = CustomAcceptanceStrategy(my_offering) 
        
        my_model = get_opponent_model()
        
        kwargs |= dict(
            acceptance=my_acceptance,
            offering=my_offering,
            model=my_model,
        )
        super().__init__(*args, **kwargs)