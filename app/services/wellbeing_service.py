"""Wellbeing score and trend computation utilities.

These functions encapsulate the logic for calculating a client's
weekly wellbeing score and deriving simple trend statistics.  By
placing them in a dedicated service module, we avoid cluttering
the route handlers with arithmetic and make unit testing
straightforward.

At this stage, the functions are stubs and will be expanded in
later phases. They currently demonstrate the intended shape of
the API and provide type hints for future development.
"""
from __future__ import annotations

from typing import List, Optional

from resilience_tracker.app.models import WeeklyAssessment

def compute_wellbeing(assessment: WeeklyAssessment) -> float:
    """Compute the average wellbeing score for a given assessment.

    This function iterates through all non-deleted habit scores
    associated with the provided assessment and returns the
    arithmetic mean rounded to one decimal place. If the
    assessment has no scores, it returns ``0.0``.

    Parameters
    ----------
    assessment: WeeklyAssessment
        The weekly assessment whose wellbeing score should be
        recalculated.

    Returns
    -------
    float
        The recalculated wellbeing score.
    """
    # Import here to avoid circular dependency at import time
    from resilience_tracker.app.models import HabitScore

    # Only consider scores that have not been soft-deleted
    active_scores = [score for score in assessment.scores if getattr(score, "deleted_at", None) is None]
    if not active_scores:
        return 0.0
    total = sum(score.score for score in active_scores)
    return round(float(total) / len(active_scores), 1)


def compute_trend(assessments: List[WeeklyAssessment], window: int = 4) -> Optional[dict[str, float]]:
    """Compute a simple trend over the last ``window`` assessments.

    Given a list of weekly assessments ordered from oldest to
    newest, this function calculates the average wellbeing
    score for the latest assessment and the change relative
    to the previous assessment. It returns a dictionary with
    keys ``latest_score`` and ``delta``.

    If there are fewer than two assessments, ``delta`` will be
    ``None`` because there is no prior assessment to compare.

    Parameters
    ----------
    assessments: List[WeeklyAssessment]
        A list of the client's weekly assessments ordered
        chronologically from oldest to newest.
    window: int, default 4
        The number of recent assessments to consider when
        calculating the trend. Currently unused but kept
        for future extension.

    Returns
    -------
    Optional[dict[str, float]]
        A dictionary containing the latest score and its delta
        compared to the previous week, or ``None`` if there
        are no assessments.
    """
    if not assessments:
        return None
    latest = assessments[-1]
    latest_score = compute_wellbeing(latest)
    if len(assessments) < 2:
        return {"latest_score": latest_score, "delta": None}
    previous_score = compute_wellbeing(assessments[-2])
    delta = latest_score - previous_score
    return {"latest_score": latest_score, "delta": delta}