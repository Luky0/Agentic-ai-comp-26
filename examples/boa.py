from negmas.sao.negotiators.modular import BOANegotiator
from negmas.sao.components.offering import TimeBasedOfferingPolicy
from negmas.sao.components.acceptance import ACNext
from negmas.gb.components.genius.models import GSmithFrequencyModel


class BOANeg(BOANegotiator):
    def __init__(self, *args, **kwargs):
        offering = TimeBasedOfferingPolicy()
        kwargs |= dict(
            acceptance=ACNext(offering),
            offering=offering,
            model=GSmithFrequencyModel(),
        )
        super().__init__(*args, **kwargs)
