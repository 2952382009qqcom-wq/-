"""Recommendation settings kept in one place for safe tuning and rollback."""

ALGORITHM_VERSION = "layered-v2"
COMPATIBILITY_ALIAS = "hybrid-v1"

RANKING_WEIGHTS = {
    "domain": 0.29,
    "text": 0.22,
    "favorite": 0.14,
    "recency": 0.07,
    "popularity": 0.07,
    "freshness": 0.06,
    "source_trust": 0.06,
    "exploration": 0.05,
    "collaborative": 0.04,
    "repeat_exposure": -0.12,
    "negative_feedback": -0.30,
}

EVENT_WEIGHTS = {
    "impression": 0.0,
    "click": 1.2,
    "dwell": 1.5,
    "view": 1.0,  # compatibility
    "search": 1.2,
    "like": 1.8,
    "comment": 2.0,
    "post": 2.5,
    "favorite": 3.5,
    "unfavorite": -2.0,
    "dismiss": -3.0,
    "open_source": 1.4,
    "related_community_click": 1.6,
    "consult": 2.8,
}

COLLABORATIVE_MIN_USERS = 30
COLLABORATIVE_MIN_EVENTS = 300
