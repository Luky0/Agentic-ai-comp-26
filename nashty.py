import random
import numpy as np
from negmas.sao import SAOState, ResponseType
from negmas.outcomes import Outcome
from negmas.sao.components.offering import TimeBasedOfferingPolicy
from negmas.sao.components.acceptance import ACNext
from negmas.gb.components.genius.models import GSmithFrequencyModel
from negmas.sao.negotiators.modular import BOANegotiator
from negmas.preferences import LambdaMultiFun, LinearUtilityFunction

class BayesianOpponentModel:
    """
    A Bayesian Opponent Model that uses Monte Carlo sampling to generate
    a robust hypothesis space of possible opponent utility functions.
    """
    def __init__(self, num_hypotheses: int = 500):
        self.num_hypotheses = num_hypotheses
        self.nmi = None
        self.issues = None
        self.num_issues = 0
        self.hypotheses = None
        self.probabilities = None
        self.estimated_ufun = None

    def _generate_hypotheses(self):
        """
        Generates robust hypotheses using a Dirichlet distribution for weights
        and random utility mappings for categorical values, avoiding NegMAS
        normalization bugs with string types.
        """
        hypotheses = []
        alpha = np.ones(self.num_issues)
        sampled_weights = np.random.dirichlet(alpha, size=self.num_hypotheses)
        
        if self.nmi and self.issues:
            # Pre-extract all possible string/categorical values for each issue
            issue_values = []
            for issue in self.issues:
                if hasattr(issue, 'values'):
                    issue_values.append(list(issue.values))
                elif hasattr(issue, 'all'):
                    issue_values.append(list(issue.all))
                else:
                    issue_values.append([])

            for weights in sampled_weights:
                # Generate a random utility score for every specific string value
                hypothesis_value_mapping = []
                for vals in issue_values:
                    if vals:
                        # Assign random scores and normalize the best item to 1.0
                        scores = np.random.rand(len(vals))
                        if len(scores) > 0:
                            scores = scores / scores.max() 
                        mapping = {v: float(s) for v, s in zip(vals, scores)}
                    else:
                        mapping = {}
                    hypothesis_value_mapping.append(mapping)

                # Create a fast pure-Python evaluator
                def make_evaluator(w, v_map):
                    def evaluator(outcome):
                        if outcome is None: 
                            return 0.0
                        u = 0.0
                        for idx, val in enumerate(outcome):
                            if val in v_map[idx]:
                                u += w[idx] * v_map[idx][val]
                            elif isinstance(val, (int, float)):
                                u += w[idx] * float(val)
                        return u
                    return evaluator

                # Wrap it in LambdaMultiFun (No .normalize() crash!)
                ufun = LambdaMultiFun(make_evaluator(weights, hypothesis_value_mapping))
                hypotheses.append(ufun)
            
        return hypotheses
    
    def update(self, state, offer, nmi):
        """
        Executes the Bayesian update using Temperature-Scaled Likelihoods.
        """
        if offer is None:
            return
        
        if self.hypotheses is None:
            self.nmi = nmi
            self.issues = nmi.outcome_space.issues
            self.num_issues = len(self.issues)
            self.hypotheses = self._generate_hypotheses()
            self.probabilities = np.ones(self.num_hypotheses) / self.num_hypotheses

        # 1. Temperature Annealing
        # Starts at 1.05 (highly forgiving of decoys) and cools down to 0.05 (strictly rational)
        # as the negotiation approaches the deadline.
        tau_initial = 1.0
        tau_final = 0.05
        tau = tau_initial * (1.0 - state.relative_time) + tau_final

        # 2. Evaluate the offer against all 500 hypotheses
        # U is an array storing the utility of the current offer under every hypothesis
        U = np.zeros(self.num_hypotheses)
        for i, h in enumerate(self.hypotheses):
            U[i] = float(h(offer))

        # 3. Calculate Likelihoods (The Softmax with Temperature)
        # NUMERICAL STABILITY TRICK: We subtract the maximum value before applying np.exp(). 
        # This prevents Python from crashing with an OverflowError if the exponents get too large.
        scaled_utilities = U / tau
        max_u = np.max(scaled_utilities)
        likelihoods = np.exp(scaled_utilities - max_u)

        # 4. The Bayesian Update (Posterior = Prior * Likelihood)
        unnormalized_posterior = self.probabilities * likelihoods
        
        # Normalize the array so all probabilities sum exactly to 1.0
        sum_posterior = np.sum(unnormalized_posterior)
        if sum_posterior > 0:
            self.probabilities = unnormalized_posterior / sum_posterior
        else:
            # Failsafe: If math underflows, reset to uniform distribution
            self.probabilities = np.ones(self.num_hypotheses) / self.num_hypotheses

        # 5. Generate the expected utility function for the tournament judge
        self._update_estimated_ufun()

    def _update_estimated_ufun(self):
        """
        Collapses the 500 hypotheses into a single 'Expected Utility Function'.
        The judge uses this exact output to calculate the Kendall Tau-b distance.
        """
        
        # Safely capture the current state of the arrays
        if self.probabilities is not None and self.hypotheses is not None:
            current_probs = self.probabilities.copy()
            current_hyps = self.hypotheses
        else:
            return

        def expected_utility_eval(outcome):
            if outcome is None or current_hyps is None:
                return 0.0
            
            # The expected utility of an outcome is the weighted average 
            # of its utility across all hypotheses.
            expected_u = 0.0
            for i, h in enumerate(current_hyps):
                expected_u += current_probs[i] * float(h(outcome))
                
            return expected_u
            
        self.estimated_ufun = LambdaMultiFun(expected_utility_eval)

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
    Decoy Bidding (Bait and Switch).
    Identifies the least important issue and aggressively bids on it early 
    to poison the opponent's model, then drops it late to force an agreement.
    """
    def __init__(self, tolerance: float = 0.05, switch_time: float = 0.60, *args, **kwargs):
        self.tolerance = tolerance
        self.switch_time = switch_time
        self._rational_outcomes_with_utils = None
        self._decoy_issue_idx = None
        self._bait_value = None
        super().__init__(*args, **kwargs)

    def before_negotiation_starts(self, state, **kwargs):
        super().before_negotiation_starts(state, **kwargs)
        
        # Identify our least valuable issue to use as a decoy
        if self.negotiator and self.negotiator.ufun:
            issues = self.negotiator.nmi.outcome_space.issues
            if len(issues) > 1:
                weights = self.negotiator.ufun.weights
                if weights:
                    decoy_issue_name = min(weights, key=weights.get)
                    for idx, issue in enumerate(issues):
                        if issue.name == decoy_issue_name:
                            self._decoy_issue_idx = idx
                            if hasattr(issue, 'values'):
                                self._bait_value = random.choice(list(issue.values))
                            elif hasattr(issue, 'all'):
                                self._bait_value = random.choice(list(issue.all))
                            break

    def __call__(self, state, dest=None) -> Outcome | None:
        if self._rational_outcomes_with_utils is None and self.negotiator and self.negotiator.ufun:
            outcomes = list(self.negotiator.nmi.outcome_space.enumerate_or_sample())
            self._rational_outcomes_with_utils = [
                (float(self.negotiator.ufun(o)), o) for o in outcomes 
                if float(self.negotiator.ufun(o)) >= float(self.negotiator.ufun.reserved_value)
            ]

        # Let the base class calculate the target utility based on time
        base_offer = super().__call__(state, dest=dest)
        
        if base_offer is None or self.negotiator.ufun is None:
            return base_offer
            
        target_utility = float(self.negotiator.ufun(base_offer))
        
        # Filter for outcomes that match our target utility
        if self._rational_outcomes_with_utils:
            candidates = [
                outcome for util, outcome in self._rational_outcomes_with_utils
                if abs(util - target_utility) <= self.tolerance
            ]
            
            if candidates and self._decoy_issue_idx is not None and self._bait_value is not None:
                if state.relative_time < self.switch_time:
                    # THE BAIT: Force the agent to constantly demand the decoy value
                    decoy_candidates = [c for c in candidates if c[self._decoy_issue_idx] == self._bait_value]
                    if decoy_candidates:
                        return random.choice(decoy_candidates)
                else:
                    # THE SWITCH: Purposely offer deals that DO NOT contain the bait
                    switch_candidates = [c for c in candidates if c[self._decoy_issue_idx] != self._bait_value]
                    if switch_candidates:
                        return random.choice(switch_candidates)
            
            # Fallback if filters are too strict
            if candidates:
                return random.choice(candidates)
        
        return base_offer


# -------------------------------------------------------------------
# ACCEPTANCE STRATEGY (AS)
# -------------------------------------------------------------------
class CustomAcceptanceStrategy(ACNext):
    """
    AC_combi: Combines AC_next with a Model-Driven Acceptance threshold.
    Includes a Spite Threshold and detailed Debug Logging.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.opp_min_utility_offered = 1.0 

    def __call__(self, state, offer=None, source=None):
        # 1. AC_next Base Logic
        base_response = super().__call__(state, offer, source)
        if base_response == ResponseType.ACCEPT_OFFER:
            print(f"[AS-DEBUG] AC_Next Base Logic accepted the offer.")
            return ResponseType.ACCEPT_OFFER

        current_offer = offer if offer is not None else state.current_offer
        if current_offer is None or self.negotiator.ufun is None:
            return ResponseType.REJECT_OFFER

        our_utility = float(self.negotiator.ufun(current_offer))
        reserved_value = float(self.negotiator.ufun.reserved_value)
        max_utility = float(self.negotiator.ufun.max())

        # 2. AC_model Logic (The Bayesian Trap)
        est_opp_ufun = self.negotiator.private_info.get("opponent_ufun")
        if est_opp_ufun:
            opp_utility = float(est_opp_ufun(current_offer))
            
            if opp_utility < self.opp_min_utility_offered:
                self.opp_min_utility_offered = opp_utility

            time_left = 1.0 - state.relative_time
            assumed_future_concession = self.opp_min_utility_offered * time_left
            projected_opp_bottom = max(0.0, self.opp_min_utility_offered - assumed_future_concession)
            
            # THE BUG FIX: The Spite Threshold
            # We refuse to trigger the trap if the best deal gives us less than 50% utility.
            spite_threshold = max(reserved_value, max_utility * 0.50)
            
            outcomes = list(self.negotiator.nmi.outcome_space.enumerate_or_sample())
            best_expected_for_us = spite_threshold
            best_deal_found = None
            
            for o in outcomes:
                if float(est_opp_ufun(o)) >= projected_opp_bottom:
                    val_for_us = float(self.negotiator.ufun(o))
                    if val_for_us > best_expected_for_us:
                        best_expected_for_us = val_for_us
                        best_deal_found = o
                        
            if state.relative_time > 0.15:
                if our_utility >= (best_expected_for_us - 0.02) and our_utility >= spite_threshold:
                    print(f"\n[AS-DEBUG] 🚨 TRAP SPRUNG at t={state.relative_time:.2f} 🚨")
                    print(f"[AS-DEBUG] Opponent's projected floor: {projected_opp_bottom:.3f}")
                    print(f"[AS-DEBUG] Best valid compromise found: {best_deal_found} yielding {best_expected_for_us:.3f} for us.")
                    print(f"[AS-DEBUG] Accepting current offer because {our_utility:.3f} >= {spite_threshold:.3f} (Spite Threshold)")
                    return ResponseType.ACCEPT_OFFER

        # 3. Safety Nets
        if our_utility >= (max_utility * 0.90):
            print(f"\n[AS-DEBUG] ✅ Accepted Absolute Good Deal ({our_utility:.3f} >= 90%)")
            return ResponseType.ACCEPT_OFFER

        if state.relative_time > 0.99:
            if our_utility > reserved_value:
                print(f"\n[AS-DEBUG] ⚠️ End of game panic! Accepted {our_utility:.3f} to avoid timeout.")
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
        
        # Instantiate our highly competitive custom opponent model
        self.custom_om = BayesianOpponentModel(num_hypotheses=500)

    def __call__(self, *args, **kwargs):
        """
        We intercept the main game loop to secretly update our custom OM 
        before the rest of the agent makes its decisions.
        """
        # Safely extract the state regardless of how NegMAS passes it
        state = kwargs.get('state') if 'state' in kwargs else (args[0] if args else None)
        
        if state and getattr(state, 'current_offer', None) is not None:
            # 1. Update our mathematical model with the opponent's offer
            self.custom_om.update(state, state.current_offer, self.nmi)
            
            # 2. OVERRIDE: Assign our custom estimate directly into private_info.
            # This is exactly where the competition judge looks to score the Concealing Bonus!
            if self.custom_om.estimated_ufun is not None:
                self.private_info["opponent_ufun"] = self.custom_om.estimated_ufun
            
        # Let the BOA framework continue with its normal logic
        response = super().__call__(*args, **kwargs)

        # DEBUGGER: Print our OM's guess vs Reality in the final 2% of the game
        if state:
            if self.custom_om.estimated_ufun and self.nmi:
                print("\n" + "="*60)
                print("🧠 BAYESIAN OM DIAGNOSTIC 🧠")
                print("="*60)
                
                # --- 1. PRINT THE TOP HYPOTHESES (PROBABILITIES) ---
                print("Top 3 Most Probable Utility Hypotheses:")
                if self.custom_om.probabilities is not None:
                    # Get the indices of the highest probabilities
                    top_indices = np.argsort(self.custom_om.probabilities)[::-1][:3]
                    for rank, idx in enumerate(top_indices):
                        prob = self.custom_om.probabilities[idx]
                        print(f"  {rank+1}. Hypothesis #{idx:03d} -> {prob*100:.2f}% certainty")
                
                print("-" * 60)
                
                # --- 2. PRINT THE TOP OUTCOMES (EXPECTED UTILITY) ---
                outcomes = list(self.nmi.outcome_space.enumerate_or_sample())
                guessed_top = sorted(outcomes, key=lambda o: float(self.custom_om.estimated_ufun(o)), reverse=True)[:3]
                
                print(f"My OM Guesses Opponent's Top 3 Deals:")
                for o in guessed_top: 
                    util = float(self.custom_om.estimated_ufun(o))
                    print(f"  - {o} (Expected Utility: {util:.3f})")
                    
                print("="*60 + "\n")

        return response
    
    def on_negotiation_end(self, state) -> None:
        """
        Called automatically by NegMAS when the negotiation finishes.
        Perfect for end-of-game diagnostic printing.
        """
        super().on_negotiation_end(state)
        
        if self.custom_om.estimated_ufun and self.nmi:
            
            print("\n" + "="*60)
            print("🧠 BAYESIAN OM DIAGNOSTIC 🧠")
            print("="*60)
            
            # --- 1. PRINT THE TOP HYPOTHESES (PROBABILITIES) ---
            print("Top 3 Most Probable Utility Hypotheses:")
            if self.custom_om.probabilities is not None:
                # Get the indices of the highest probabilities
                top_indices = np.argsort(self.custom_om.probabilities)[::-1][:3]
                for rank, idx in enumerate(top_indices):
                    prob = self.custom_om.probabilities[idx]
                    print(f"  {rank+1}. Hypothesis #{idx:03d} -> {prob*100:.2f}% certainty")
            
            print("-" * 60)
            
            # --- 2. PRINT THE TOP OUTCOMES (EXPECTED UTILITY) ---
            outcomes = list(self.nmi.outcome_space.enumerate_or_sample())
            guessed_top = sorted(outcomes, key=lambda o: float(self.custom_om.estimated_ufun(o)), reverse=True)[:3]
            
            print(f"My OM Guesses Opponent's Top 3 Deals:")
            for o in guessed_top: 
                util = float(self.custom_om.estimated_ufun(o))
                print(f"  - {o} (Expected Utility: {util:.3f})")
                
            print("="*60 + "\n")