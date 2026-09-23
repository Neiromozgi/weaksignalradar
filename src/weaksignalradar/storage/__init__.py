"""PostgreSQL persistence for Stage A (A-04).

Tables mirror ``contracts/stage_a_contract.json`` storage entities.
SourceSpan is storage-preparation only — no VERIFIED / bucket / ranking semantics.
"""

from weaksignalradar.storage.models import (
    SearchRunRow,
    SourceDocumentRow,
    SourceSpanRow,
    TaskLogRow,
)

__all__ = [
    "SearchRunRow",
    "SourceDocumentRow",
    "SourceSpanRow",
    "TaskLogRow",
]
