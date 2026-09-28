from weaksignalradar.fasttrack.domain.run_state import CandidateRecord
from weaksignalradar.fasttrack.ui.limitations import limitations_lines
from weaksignalradar.fasttrack.ui.naming import technology_display_names


def test_display_name_keeps_candidate_id_unchanged():
    c = CandidateRecord(
        candidate_id="cand_fixed_id",
        canonical_name="Solid-state batteries",
        name_ru="Твердотельные аккумуляторы",
        name_en="Solid-state batteries",
        aliases=["SSB"],
        state="QUALIFIED",
        document_ids=[],
        first_observed_year=2020,
        document_count=10,
        organization_count=3,
        source_class_count=1,
    )
    names = technology_display_names(c)
    assert c.candidate_id == "cand_fixed_id"
    assert "Твердотельные" in names["display_label"]
    assert "Solid-state" in names["display_label"]


def test_limitations_human_readable_not_empty():
    lines = limitations_lines(
        d_diagnostics={"lineage_count": 2, "coverage_uncertainty": ["PARTIAL"]},
        features={"C": {"availability": "EMBEDDING_UNAVAILABLE"}},
        source_runs=[{"source": "cordis", "execution_status": "PARTIAL"}],
        coverage={"cordis": "PARTIAL"},
    )
    assert lines
    assert all("{" not in line for line in lines)
