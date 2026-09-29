import uuid
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from ortools.sat.python import cp_model

from app.common.logging import get_logger

logger = get_logger("ortools_scheduler")


@dataclass
class ScheduledSlot:
    candidate_id: str
    topic_id: uuid.UUID
    topic_name: str
    subject_id: uuid.UUID
    action: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    priority: float
    reasons: List[str]
    locked: bool = False


@dataclass
class PlannerCandidate:
    candidate_id: str
    topic_id: uuid.UUID
    topic_name: str
    subject_id: uuid.UUID
    action: str
    priority: float
    duration_minutes: int
    reasons: List[str]
    exam_deadline: Optional[datetime] = None


@dataclass
class TimeSlot:
    start: datetime
    end: datetime
    duration_minutes: int


class ORToolsPlanner:
    """
    Constraint-aware CP-SAT scheduler using Google OR-Tools.
    Strictly enforces hard capacity, availability, exam, and locked-task constraints.
    """

    def __init__(
        self,
        daily_max_minutes: int = 240,       # 4 hours max study per day
        session_duration_minutes: int = 45,  # Standard 45-min study block
        min_break_minutes: int = 15,        # 15 mins break between sessions
    ):
        self.daily_max_minutes = daily_max_minutes
        self.session_duration = session_duration_minutes
        self.min_break_minutes = min_break_minutes

    def schedule(
        self,
        planning_start: datetime,
        planning_end: datetime,
        availability_slots: List[TimeSlot],
        candidates: List[PlannerCandidate],
        locked_tasks: Optional[List[ScheduledSlot]] = None,
    ) -> List[ScheduledSlot]:
        if not candidates or not availability_slots:
            return []

        locked_tasks = locked_tasks or []

        # 1. Generate discrete candidate placement intervals from availability slots
        discrete_slots: List[Tuple[datetime, datetime]] = []
        for slot in availability_slots:
            curr = slot.start
            step = timedelta(minutes=self.session_duration + self.min_break_minutes)
            session_delta = timedelta(minutes=self.session_duration)

            while curr + session_delta <= slot.end and curr + session_delta <= planning_end:
                slot_start = curr
                slot_end = curr + session_delta

                # Check if this slot conflicts with any locked task
                overlaps_locked = False
                for lt in locked_tasks:
                    if not (slot_end <= lt.start_time or slot_start >= lt.end_time):
                        overlaps_locked = True
                        break

                if not overlaps_locked:
                    discrete_slots.append((slot_start, slot_end))

                curr += step

        if not discrete_slots:
            logger.info("no_available_discrete_slots_found")
            return locked_tasks

        # 2. Build CP-SAT Model
        model = cp_model.CpModel()

        num_candidates = len(candidates)
        num_slots = len(discrete_slots)

        # Decision variables: x[i, j] == 1 if candidate i is placed in slot j
        x: Dict[Tuple[int, int], cp_model.IntVar] = {}
        for i in range(num_candidates):
            for j in range(num_slots):
                x[(i, j)] = model.NewBoolVar(f"x_{i}_{j}")

        # Constraint 1: Each candidate is scheduled at most once
        for i in range(num_candidates):
            model.Add(sum(x[(i, j)] for j in range(num_slots)) <= 1)

        # Constraint 2: Each slot holds at most one candidate
        for j in range(num_slots):
            model.Add(sum(x[(i, j)] for i in range(num_candidates)) <= 1)

        # Constraint 3: Exam Deadline Hard Constraint (task must finish before subject exam)
        for i, cand in enumerate(candidates):
            if cand.exam_deadline:
                for j, (slot_start, slot_end) in enumerate(discrete_slots):
                    if slot_end > cand.exam_deadline:
                        # Cannot place task after exam
                        model.Add(x[(i, j)] == 0)

        # Constraint 4: Daily Capacity Limit
        # Group slots by calendar date
        slots_by_day: Dict[date, List[int]] = {}
        for j, (slot_start, _) in enumerate(discrete_slots):
            day_key = slot_start.date()
            if day_key not in slots_by_day:
                slots_by_day[day_key] = []
            slots_by_day[day_key].append(j)

        max_sessions_per_day = self.daily_max_minutes // self.session_duration
        for day_key, day_slot_indices in slots_by_day.items():
            # Sum of sessions on this day <= max_sessions_per_day
            model.Add(
                sum(x[(i, j)] for i in range(num_candidates) for j in day_slot_indices)
                <= max_sessions_per_day
            )

        # 3. Objective Function: Maximize weighted priority of scheduled candidates
        objective_terms = []
        for i, cand in enumerate(candidates):
            # Scale priority (0.0 - 1.0) to integer for CP-SAT
            priority_weight = int(cand.priority * 1000)
            for j in range(num_slots):
                objective_terms.append(priority_weight * x[(i, j)])

        model.Maximize(sum(objective_terms))

        # 4. Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5.0
        status = solver.Solve(model)

        scheduled_results: List[ScheduledSlot] = list(locked_tasks)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for i, cand in enumerate(candidates):
                for j, (slot_start, slot_end) in enumerate(discrete_slots):
                    if solver.Value(x[(i, j)]) == 1:
                        scheduled_results.append(
                            ScheduledSlot(
                                candidate_id=cand.candidate_id,
                                topic_id=cand.topic_id,
                                topic_name=cand.topic_name,
                                subject_id=cand.subject_id,
                                action=cand.action,
                                start_time=slot_start,
                                end_time=slot_end,
                                duration_minutes=self.session_duration,
                                priority=cand.priority,
                                reasons=cand.reasons,
                                locked=False,
                            )
                        )

            # Sort chronologically
            scheduled_results.sort(key=lambda s: s.start_time)
            logger.info(
                "schedule_optimization_complete",
                total_scheduled=len(scheduled_results),
                solver_status=solver.StatusName(status),
            )
        else:
            logger.warning("solver_did_not_find_feasible_schedule", status=solver.StatusName(status))

        return scheduled_results
