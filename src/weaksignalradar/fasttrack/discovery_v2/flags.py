"""Feature flags for Discovery v2."""

from __future__ import annotations

import os


def discovery_v2_enabled() -> bool:
    return os.environ.get("DISCOVERY_V2_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
