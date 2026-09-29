from dataclasses import dataclass
from typing import List, Optional
import random


@dataclass
class SyntheticProfile:
    name: str
    persona: str
    initial_mastery: float
    self_confidence: float
    true_competence: float
    daily_available_minutes: int
    skip_probability: float


class SyntheticStudentFactory:
    """Creates standardized synthetic student personas defined in 09_TESTING_EVALUATION.md."""

    @staticmethod
    def get_weak_learner() -> SyntheticProfile:
        return SyntheticProfile(
            name="Weak Learner",
            persona="weak",
            initial_mastery=0.15,
            self_confidence=0.20,
            true_competence=0.25,
            daily_available_minutes=180,
            skip_probability=0.10,
        )

    @staticmethod
    def get_overconfident_learner() -> SyntheticProfile:
        return SyntheticProfile(
            name="Overconfident Learner",
            persona="overconfident",
            initial_mastery=0.20,
            self_confidence=0.90,  # High confidence
            true_competence=0.35,  # Low actual accuracy
            daily_available_minutes=180,
            skip_probability=0.05,
        )

    @staticmethod
    def get_underconfident_learner() -> SyntheticProfile:
        return SyntheticProfile(
            name="Underconfident Learner",
            persona="underconfident",
            initial_mastery=0.70,
            self_confidence=0.25,  # Low confidence
            true_competence=0.90,  # High actual accuracy
            daily_available_minutes=180,
            skip_probability=0.05,
        )

    @staticmethod
    def get_busy_learner() -> SyntheticProfile:
        return SyntheticProfile(
            name="Busy Learner",
            persona="busy",
            initial_mastery=0.40,
            self_confidence=0.50,
            true_competence=0.60,
            daily_available_minutes=60,  # Very limited hours
            skip_probability=0.15,
        )

    @staticmethod
    def get_non_adherent_learner() -> SyntheticProfile:
        return SyntheticProfile(
            name="Non-Adherent Learner",
            persona="non_adherent",
            initial_mastery=0.30,
            self_confidence=0.40,
            true_competence=0.50,
            daily_available_minutes=180,
            skip_probability=0.60,  # High skip rate
        )

    @classmethod
    def simulate_quiz_attempt(cls, profile: SyntheticProfile) -> bool:
        """Simulates question answer result based on true student competence."""
        return random.random() < profile.true_competence
