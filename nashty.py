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

        # Initialize the opponent model, i.e. make a first guess for the opponent's utility function
        # Example: constant utility function
        self.private_info["opponent_ufun"] = LambdaMultiFun(f=lambda x: 0.5)

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

        # Example: accept offer if utility is bigger than 80% of the maximum utility
        if self.ufun(offer) > self.ufun.max() * 0.8 > self.ufun.reserved_value:
            return True

        # Example: accept offer if utility is bigger than the reserved value
        if state.relative_time > 0.9 and self.ufun(offer) > self.ufun.reserved_value:
            return True
        return False

    def concealing_bidding_strategy(self, state: SAOState) -> Outcome | None:
        """
        This is one of the functions you need to implement.
        It should determine the next concealing counter offer.

        Returns: the counter offer as Outcome.
        """

        # Your opponent model can be accessed using self.private_info["opponent_ufun"], which is not used yet.
        #
        # Example: one of my best outcomes in the beginning of the negotiation
        if state.relative_time < 0.5:
            return random.choice(
                self.rational_outcomes[: min(len(self.rational_outcomes), 10)]
            )

        # Example: random outcome in rational_outcomes
        return random.choice(self.rational_outcomes)

    def update_opponent_model(self, state: SAOState) -> None:
        """
        This is one of the functions you need to implement.
        Using the information of the new offers, update the opponent model.

        Returns: None.
        """

        assert self.ufun and self.opponent_ufun

        # Update your opponent model based on the current offer

        # You can use, for instance, LinearMultiFun and update the weights and values for your opponent model.

        # Example: no update in opponent model
