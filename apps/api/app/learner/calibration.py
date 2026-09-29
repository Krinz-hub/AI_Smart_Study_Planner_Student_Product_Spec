from typing import Tuple


def evaluate_confidence_calibration(
    self_confidence: float,
    mastery_prob: float,
    evidence_count: int,
) -> Tuple[str, str]:
    """
    Evaluates alignment between self-reported confidence and objective mastery.
    Returns: (status, explanation)
    """
    if evidence_count == 0:
        return "UNASSESSED", "Topic has not been objectively assessed yet."

    diff = self_confidence - mastery_prob

    if abs(diff) <= 0.20:
        return "CALIBRATED", "Self-confidence accurately mirrors demonstrated mastery."
    elif diff > 0.20:
        return (
            "OVERCONFIDENT",
            f"Self-reported confidence ({self_confidence:.0%}) exceeds demonstrated mastery ({mastery_prob:.0%}). Practice recommended.",
        )
    else:
        return (
            "UNDERCONFIDENT",
            f"Demonstrated mastery ({mastery_prob:.0%}) exceeds self-confidence ({self_confidence:.0%}). Reinforce self-efficacy.",
        )
