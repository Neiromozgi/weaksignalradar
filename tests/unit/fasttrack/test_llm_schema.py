import pytest

from weaksignalradar.fasttrack.llm.extraction_schema import validate_extraction_payload


def test_extraction_schema_accepts_null_facets():
    validate_extraction_payload(
        {
            "candidate_name": "Example",
            "object_class": None,
            "function": None,
            "mechanism": "phase change",
            "architecture_or_process": None,
            "key_technical_property": None,
            "evidence_span_refs": ["ev0"],
            "unknown_fields": [],
            "status": "PARTIAL",
        }
    )


def test_extraction_schema_rejects_extra_fields():
    with pytest.raises(Exception):
        validate_extraction_payload(
            {
                "candidate_name": "Example",
                "object_class": None,
                "function": None,
                "mechanism": None,
                "architecture_or_process": None,
                "key_technical_property": None,
                "evidence_span_refs": [],
                "unknown_fields": [],
                "status": "UNKNOWN",
                "rank": 1,
            }
        )
