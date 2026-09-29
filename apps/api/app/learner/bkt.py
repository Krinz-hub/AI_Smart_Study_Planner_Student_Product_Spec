import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Tuple


@dataclass(frozen=True)
class BKTParams:
    p_init: float = 0.10    # P(L_0): initial prior
    p_transit: float = 0.15 # P(T): probability of learning during opportunity
    p_guess: float = 0.20   # P(G): probability of correct response despite not knowing
    p_slip: float = 0.10    # P(S): probability of incorrect response despite knowing


DEFAULT_BKT_PARAMS = BKTParams()


def compute_bkt_posterior(
    p_known: float,
    is_correct: bool,
    params: BKTParams = DEFAULT_BKT_PARAMS,
) -> float:
    """Computes updated knowledge probability P(L_t) given observation."""
    p_known = max(0.001, min(0.999, p_known))

    if is_correct:
        numerator = p_known * (1.0 - params.p_slip)
        denominator = numerator + (1.0 - p_known) * params.p_guess
    else:
        numerator = p_known * params.p_slip
        denominator = numerator + (1.0 - p_known) * (1.0 - params.p_guess)

    p_observed = numerator / denominator if denominator > 0 else p_known

    # Apply learning transition for opportunity
    p_next = p_observed + (1.0 - p_observed) * params.p_transit
    return round(max(0.01, min(0.99, p_next)), 3)


def compute_confidence(evidence_count: int) -> float:
    """Computes statistical confidence based on observed assessment count."""
    if evidence_count <= 0:
        return 0.0
    conf = 1.0 - math.exp(-0.45 * evidence_count)
    return round(min(1.0, conf), 3)


def classify_mastery_state(mastery_prob: float, confidence: float, evidence_count: int) -> str:
    """Classifies mastery state strictly according to 04_LEARNER_INTELLIGENCE.md."""
    if evidence_count == 0 or confidence < 0.15:
        return "UNKNOWN"
    if mastery_prob < 0.35:
        return "CRITICAL"
    if mastery_prob < 0.60:
        return "WEAK"
    if mastery_prob < 0.75:
        return "DEVELOPING"
    if mastery_prob < 0.90:
        return "STRONG"
    # Mastery prob >= 0.90
    if confidence >= 0.65:
        return "MASTERED"
    return "STRONG"
