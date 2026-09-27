"""Read-only access to an offline-trained collaborative recommendation artifact.

Training is intentionally not exposed from a request handler. A worker may publish
versioned JSON artifacts and atomically switch the active file.
"""

import json
import os
from pathlib import Path

from .config import COLLABORATIVE_MIN_EVENTS, COLLABORATIVE_MIN_USERS


def load_scores(user_id, artifact_path=None):
    path = Path(artifact_path or os.getenv("RECOMMENDER_ARTIFACT", "instance/models/recommender-active.json"))
    if not path.is_file():
        return {}, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if int(data.get("trained_users", 0)) < COLLABORATIVE_MIN_USERS:
            return {}, None
        if int(data.get("trained_events", 0)) < COLLABORATIVE_MIN_EVENTS:
            return {}, None
        values = data.get("users", {}).get(str(user_id), {})
        return {int(key): float(value) for key, value in values.items()}, str(data.get("version", "unknown"))
    except (OSError, ValueError, TypeError):
        return {}, None
