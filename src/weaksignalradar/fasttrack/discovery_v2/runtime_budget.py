"""Discovery v2 LIVE runtime LLM budget policy (Tranche 2)."""

from __future__ import annotations

# Target is guidance; runs may exceed target when authorized but must not exceed hard limit.
TARGET_LLM_CALLS = 40
HARD_LLM_CALL_LIMIT = 60

LIVE_TARGET_WALL_SEC = 600
LIVE_HARD_TIMEOUT_SEC = 900

TARGET_CORPUS_DOCUMENTS = 200
TMF_BATCH_SIZE = 10

# Worst-case planning reference (not a hard failure at target):
# 1 planner + ceil(200/10) TMF batches + <=15 signature extractions = 36 at target corpus.
