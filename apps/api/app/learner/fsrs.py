import math
from datetime import datetime, timedelta, timezone
from typing import Tuple


def compute_retrievability(stability_days: float, elapsed_days: float) -> float:
    """Computes retention probability R(t) = (1 + t / (9 * S))^-1."""
    if stability_days <= 0:
        return 0.0
    r = 1.0 / (1.0 + (max(0.0, elapsed_days) / (9.0 * stability_days)))
    return round(max(0.01, min(1.0, r)), 3)


def update_fsrs_state(
    current_stability: float,
    current_difficulty: float,
    rating: int,  # 1=Again, 2=Hard, 3=Good, 4=Easy
    elapsed_days: float,
) -> Tuple[float, float, float, int]:
    """
    Updates stability, difficulty, retrievability, and optimal review interval (in hours).
    Ratings: 1=Again, 2=Hard, 3=Good, 4=Easy
    """
    rating = max(1, min(4, rating))
    r = compute_retrievability(current_stability, elapsed_days)

    # 1. Update Difficulty (1.0 to 10.0)
    delta_d = -0.5 * (rating - 3)
    new_difficulty = max(1.0, min(10.0, current_difficulty + delta_d))

    # 2. Update Stability
    if rating == 1:
        # Lapse / forgotten
        new_stability = max(0.4, current_stability * 0.25)
    else:
        # Successful retrieval bonus
        factor = 1.0 + (11.0 - new_difficulty) * 0.15 * math.pow(current_stability, -0.2)
        multiplier = {2: 1.2, 3: 2.0, 4: 2.8}.get(rating, 2.0)
        new_stability = max(0.8, current_stability * factor * (multiplier / 2.0))

    new_stability = round(new_stability, 2)
    new_difficulty = round(new_difficulty, 2)

    # 3. Next review interval (target retention = 0.90 -> interval ~ stability days)
    interval_hours = max(4, int(new_stability * 24))
    new_retrievability = 1.0  # Just reviewed

    return new_stability, new_difficulty, new_retrievability, interval_hours
