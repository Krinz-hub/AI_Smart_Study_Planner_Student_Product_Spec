from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class PriorityWeights:
    version: str = "priority-v1"
    w_weakness: float = 0.35
    w_urgency: float = 0.30
    w_forgetting: float = 0.15
    w_prereq: float = 0.10
    w_goal: float = 0.10


DEFAULT_PRIORITY_WEIGHTS = PriorityWeights()


def compute_topic_priority(
    mastery_prob: float,
    mastery_state: str,
    retrievability: float,
    exam_days_remaining: Optional[float],
    has_prereq_blockers: bool,
    goal_importance: float,
    syllabus_weight: float,
    weights: PriorityWeights = DEFAULT_PRIORITY_WEIGHTS,
) -> Tuple[float, str, List[str]]:
    """
    Computes normalized priority (0.0 to 1.0), recommended intervention action,
    and explainable reasons based on versioned criteria per 05_DECISION_AND_PLANNER.md.
    """
    reasons: List[str] = []

    # 1. Weakness factor (0.0 to 1.0)
    weakness = max(0.0, 1.0 - mastery_prob)
    if mastery_state == "UNKNOWN":
        weakness = 0.85
        reasons.append("Topic is unassessed / unknown in student model")
    elif weakness >= 0.40:
        reasons.append(f"Mastery is low ({mastery_prob:.0%})")

    # 2. Urgency factor (exam proximity within 14-day planning window)
    if exam_days_remaining is not None and exam_days_remaining >= 0:
        urgency = max(0.10, 1.0 - (exam_days_remaining / 14.0))
        if exam_days_remaining <= 3:
            reasons.append(f"Upcoming exam in {int(exam_days_remaining)} day(s)")
        elif exam_days_remaining <= 14:
            reasons.append(f"Approaching exam in {int(exam_days_remaining)} days")
    else:
        urgency = 0.10

    # 3. Forgetting risk (1.0 - retrievability)
    forgetting_risk = max(0.0, 1.0 - retrievability)
    if forgetting_risk >= 0.25:
        reasons.append(f"Memory retention has decayed (retrievability: {retrievability:.0%})")

    # 4. Prerequisite urgency
    prereq_score = 0.85 if has_prereq_blockers else 0.10
    if has_prereq_blockers:
        reasons.append("Foundational prerequisites are weak and require reinforcement")

    # 5. Goal importance (0.0 to 1.0)
    goal_score = min(1.0, max(0.0, goal_importance))
    if goal_score >= 0.70:
        reasons.append("Targeted by high-priority active learning goal")

    # Calculate raw weighted composite
    raw_score = (
        weights.w_weakness * weakness
        + weights.w_urgency * urgency
        + weights.w_forgetting * forgetting_risk
        + weights.w_prereq * prereq_score
        + weights.w_goal * goal_score
    )

    # Modulate slightly by syllabus weight (0.8 to 1.2 normalized around 1.0)
    syllabus_factor = max(0.8, min(1.2, syllabus_weight))
    final_score = round(max(0.05, min(0.99, raw_score * syllabus_factor)), 3)

    # Determine candidate intervention action
    if has_prereq_blockers:
        action = "PREREQUISITE_REPAIR"
    elif mastery_state == "UNKNOWN":
        action = "LEARN"
    elif forgetting_risk >= 0.30 and mastery_prob >= 0.60:
        action = "REVISE" if forgetting_risk < 0.50 else "RETRIEVE"
    elif mastery_prob < 0.40:
        action = "LEARN"
    elif mastery_prob < 0.75:
        action = "PRACTICE"
    elif urgency >= 0.60:
        action = "QUICK_REVISION"
    else:
        action = "PRACTICE"

    if not reasons:
        reasons.append("Scheduled according to regular curriculum progression")

    return final_score, action, reasons
