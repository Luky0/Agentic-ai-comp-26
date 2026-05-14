from negmas.gb.negotiators.cab import MAPNegotiator
from negmas.sao.components.offering import TimeBasedOfferingPolicy
from negmas.sao.components.acceptance import ACNext
from negmas.gb.components.genius.models import GSmithFrequencyModel


class MAPNeg(MAPNegotiator):
    def __init__(self, *args, **kwargs):
        offering = TimeBasedOfferingPolicy()
        kwargs |= dict(
            acceptance=ACNext(offering),
            offering=offering,
            models=[GSmithFrequencyModel()],
            model_names=["Smith"],
            acceptance_first=True,
        )
        super().__init__(*args, **kwargs)
