from typing import TYPE_CHECKING
from negmas.sao import SAOCallNegotiator, SAOResponse, ResponseType
from negmas.preferences import WeightedUtilityFunction, ConstUtilityFunction

if TYPE_CHECKING:
    from negmas import (
        SAOState,
    )


class SimpleNegotiator(SAOCallNegotiator):
    """A simple negotiator implemented in one function"""

    def on_negotiation_start(self, state: SAOState) -> None:
        assert self.ufun is not None, "Cannot work without a ufun"
        self._inv = self.ufun.invert()
        rng = self._inv.max() - self._inv.min()
        # we will just assume that the opponent has a ufun which is the exact reverse of ours
        if rng == 0:
            self.private_info["opponent_ufun"] = self.ufun
        else:
            self.private_info["opponent_ufun"] = WeightedUtilityFunction(
                [
                    ConstUtilityFunction(
                        self._inv.max(), outcome_space=self.ufun.outcome_space
                    ),
                    self.ufun,
                ],  # type: ignore[reportArgumentType]
                weights=(1 / rng, -1 / rng),
                reserved_value=self.ufun.reserved_value,
            )

    def __call__(self, state: SAOState, dest: str | None = None) -> SAOResponse:
        assert self.ufun is not None, "Cannot work without a ufun"
        offer = state.current_offer
        if offer is None:
            return SAOResponse(ResponseType.REJECT_OFFER, self._inv.best())
        if self.ufun(state.current_offer) >= 0.8:
            return SAOResponse(ResponseType.ACCEPT_OFFER)
        return SAOResponse(
            ResponseType.REJECT_OFFER,
            self._inv.one_in((1.0 - state.relative_time, 1.0), normalized=True),
        )
