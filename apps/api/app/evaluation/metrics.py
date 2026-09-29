from datetime import datetime
from typing import Any, Dict, List


def calculate_normalized_gain(pre_score: float, post_score: float) -> float:
    """
    Computes Hake's normalized learning gain:
    g = (post - pre) / (1.0 - pre)
    """
    if pre_score >= 1.0:
        return 1.0 if post_score >= 1.0 else 0.0
    gain = (post_score - pre_score) / (1.0 - pre_score)
    return round(max(0.0, min(1.0, gain)), 4)


def calculate_calibration_error(confidence: float, accuracy: float) -> float:
    """Computes absolute calibration gap between subjective confidence and empirical accuracy."""
    return round(abs(confidence - accuracy), 4)


def calculate_schedule_stability_index(
    original_task_slots: Dict[str, str],
    replanned_task_slots: Dict[str, str],
) -> float:
    """
    Computes stability index:
    ratio of tasks whose time slots were preserved without churn.
    """
    if not original_task_slots:
        return 1.0

    common_keys = set(original_task_slots.keys()) & set(replanned_task_slots.keys())
    if not common_keys:
        return 0.0

    unmoved = sum(
        1 for k in common_keys if original_task_slots[k] == replanned_task_slots[k]
    )
    return round(unmoved / len(common_keys), 4)


def verify_hard_constraints(
    tasks: List[Dict[str, Any]],
    daily_max_minutes: int = 360,
) -> List[str]:
    """
    Validates hard constraint satisfaction:
    1. Zero interval overlap between any tasks.
    2. Zero daily capacity violations.
    Returns list of violations (must be strictly empty).
    """
    violations: List[str] = []

    # 1. Non-overlapping intervals
    sorted_tasks = sorted(tasks, key=lambda t: datetime.fromisoformat(t["planned_start"]))
    for i in range(len(sorted_tasks) - 1):
        t1_end = datetime.fromisoformat(sorted_tasks[i]["planned_end"])
        t2_start = datetime.fromisoformat(sorted_tasks[i + 1]["planned_start"])
        if t2_start < t1_end:
            violations.append(
                f"Overlap detected: Task {sorted_tasks[i].get('id')} ends at {t1_end} but Task {sorted_tasks[i+1].get('id')} starts at {t2_start}"
            )

    # 2. Daily capacity limits
    daily_minutes: Dict[str, int] = {}
    for t in sorted_tasks:
        start_dt = datetime.fromisoformat(t["planned_start"])
        day_key = start_dt.date().isoformat()
        dur = t.get("duration_minutes", 45)
        daily_minutes[day_key] = daily_minutes.get(day_key, 0) + dur

    for day, total in daily_minutes.items():
        if total > daily_max_minutes:
            violations.append(
                f"Capacity violation: {day} scheduled {total}m exceeding ceiling of {daily_max_minutes}m"
            )

    return violations
