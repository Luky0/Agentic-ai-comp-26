import random
from negmas.sao import SAOCallNegotiator, ResponseType, SAOState, SAOResponse
from negmas.outcomes import Outcome
from negmas.preferences import LambdaMultiFun


class NashtyNegotiator(SAOCallNegotiator):
    """
    Your negotiator code. This is the ONLY class you need to implement.
    """

    rational_outcomes = tuple()

    def on_preferences_changed(self, changes):
        """
        Called when preferences change. In ANL 2026, this is equivalent with initializing the agent.

        Remarks:
            - Can optionally be used for initializing your agent.
            - We use it to save a list of all rational outcomes.

        """

        # If there are no outcomes (should in theory never happen)
        if self.ufun is None:
            return

        # create a list of all rational outcomes (i.e. outcomes with utility bigger than the reserved value) sorted by utility
        ufun_outcome = [
            (self.ufun(_), _)
            for _ in self.nmi.outcome_space.enumerate_or_sample()  # enumerates outcome space when finite, samples when infinite
            if self.ufun(_) > self.ufun.reserved_value
        ]
        self.rational_outcomes = tuple(_[1] for _ in sorted(ufun_outcome, reverse=True))
        print(f"N. rational: {len(self.rational_outcomes)}")

        # 2. Initialize frequency counters for the Opponent Model
        # Format: { issue_index: { value: count } }
        self.opponent_counts = {}

        # 3. Define the dynamic utility estimator
        def estimate_opponent_utility(outcome: Outcome) -> float:
            if not outcome:
                return 0.0
            
            score = 0.0
            num_issues = len(outcome)
            
            for i, val in enumerate(outcome):
                if i not in self.opponent_counts or not self.opponent_counts[i]:
                    # If we have no data for this issue yet, assume a neutral 0.5 utility
                    score += 0.5
                    continue
                
                counts = self.opponent_counts[i]
                max_count = max(counts.values())
                
                if max_count > 0:
                    # Normalize the frequency between 0 and 1
                    score += (counts.get(val, 0) / max_count)
                else:
                    score += 0.5
                    
            # Assume equal weights for all issues for this baseline
            return score / num_issues if num_issues > 0 else 0.0

        # Bind the estimator to the opponent model
        self.private_info["opponent_ufun"] = LambdaMultiFun(f=estimate_opponent_utility)

    def __call__(self, state: SAOState, dest: str | None = None) -> SAOResponse:
        """
        Called to (counter-)offer.

        Args:
            state: the `SAOState` containing the offer from your partner (None if you are just starting the negotiation)
                   and other information about the negotiation (e.g. current step, relative time, etc).
        Returns:
            A response of type `SAOResponse` which indicates whether you accept, or reject the offer or leave the negotiation.
            If you reject an offer, you are required to pass a counter offer.

        Remarks:
            - You can access your ufun using `self.ufun`.
            - You can access the opponent model using self.opponent_ufun
            - You can access the mechanism for helpful functions like sampling from the outcome space using `self.nmi` (returns an `SAONMI` instance).
            - You can access the current offer (from your partner) as `state.current_offer`.
              - If this is `None`, you are starting the negotiation now (no offers yet).
        """

        offer = state.current_offer

        # If there are no outcomes (should in theory never happen)
        if self.ufun is None:
            return SAOResponse(ResponseType.END_NEGOTIATION, None)

        # If there is no offer yet (first call), make a counter offer
        if offer is None:
            return SAOResponse(
                ResponseType.REJECT_OFFER, self.concealing_bidding_strategy(state)
            )

        self.update_opponent_model(state)

        # Determine the acceptability of the offer in the acceptance_strategy
        if self.acceptance_strategy(state):
            return SAOResponse(ResponseType.ACCEPT_OFFER, offer)

        # If it's not acceptable, determine the counter offer in the concealing_bidding_strategy
        return SAOResponse(
            ResponseType.REJECT_OFFER, self.concealing_bidding_strategy(state)
        )

    def acceptance_strategy(self, state: SAOState) -> bool:
        """
        This is one of the functions you need to implement.
        It should determine whether or not to accept the offer.

        Returns: a bool.
        """

        assert self.ufun

        offer = state.current_offer

        # Cannot accept a non-existent offer
        if offer is None:
            return False
        
        # 1. Calculate the exact utility of the opponent's offer to us
        offer_utility = float(self.ufun(offer))
        
        # 2. Ask the bidding strategy what we would propose if we rejected this offer
        next_planned_bid = self.concealing_bidding_strategy(state)
        
        # Fallback: if we somehow have no valid next bid, reject.
        if next_planned_bid is None:
            return False
            
        # 3. Calculate the utility of our planned next bid
        next_bid_utility = float(self.ufun(next_planned_bid))
        
        # 4. ACNext Core Logic: Is their offer better than or equal to our next move?
        if offer_utility >= next_bid_utility:
            return True
            
        # 5. Safety Net (Optional but recommended): 
        # If we are in the final 1% of the negotiation time, accept ANYTHING 
        # that is strictly better than our reservation value to avoid a walk-away (utility = 0).
        if state.relative_time > 0.99 and offer_utility > self.ufun.reserved_value:
             return True

        return False

    def concealing_bidding_strategy(self, state: SAOState) -> Outcome | None:
        """
        This is one of the functions you need to implement.
        It should determine the next concealing counter offer.

        Returns: the counter offer as Outcome.
        """
        if not self.ufun or not self.rational_outcomes:
            return None
            
        # 1. Define concession parameters
        t = state.relative_time  # Progresses from 0.0 to 1.0
        max_utility = float(self.ufun.max())
        
        # We should never concede below our reservation value
        min_utility = float(self.ufun.reserved_value)
        
        # 'e' defines the shape of our concession curve. 
        # e < 1: Boulware (holds firm for a long time, then concedes rapidly at the end)
        # e = 1: Linear (concedes steadily)
        # e > 1: Conceder (concedes quickly, then holds firm)
        e = 0.2  # A Boulware strategy is generally safest in competitive environments
        
        # 2. Calculate the target utility for the current turn
        target_utility = max_utility - (max_utility - min_utility) * (t ** e)
        
        # 3. Create the "Iso-Curve" pool for concealment
        # We look for all outcomes within a 5% margin of our target utility
        tolerance = 0.05 
        valid_outcomes = [
            outcome for outcome in self.rational_outcomes
            if abs(float(self.ufun(outcome)) - target_utility) <= tolerance
        ]
        
        # 4. Randomly select from the valid pool to inject noise into the opponent's model
        if valid_outcomes:
            return random.choice(valid_outcomes)
            
        # 5. Fallback Mechanism
        # If no outcomes fall perfectly within our tolerance window (which can happen 
        # in domains with very few issues/values), just return the absolute closest one.
        closest_outcome = min(
            self.rational_outcomes, 
            key=lambda o: abs(float(self.ufun(o)) - target_utility)
        )
        
        return closest_outcome

    def update_opponent_model(self, state: SAOState) -> None:
        """
        This is one of the functions you need to implement.
        Using the information of the new offers, update the opponent model.

        Returns: None.
        """

        assert self.ufun and self.opponent_ufun

        offer = state.current_offer
        
        # If it is the first round and there is no offer, skip the update
        if offer is None:
            return

        # Increment frequency counts for each value in the current offer
        for i, val in enumerate(offer):
            if i not in self.opponent_counts:
                self.opponent_counts[i] = {}
            
            # Add 1 to the count of the proposed value
            self.opponent_counts[i][val] = self.opponent_counts[i].get(val, 0) + 1

        # Update your opponent model based on the current offer

        # You can use, for instance, LinearMultiFun and update the weights and values for your opponent model.

        # Example: no update in opponent model
