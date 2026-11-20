import pytest

from risk_intel.cli import build_summariser, main
from risk_intel.config import INTERIM_DIR, RAW_DIR
from risk_intel.pipeline import run_pipeline

PDF = RAW_DIR / "VestasAnnualReport2025.pdf"
pytestmark = pytest.mark.skipif(not PDF.exists(), reason="put the PDF in data/raw/")

STAGE_NAMES = {"stage1 document", "stage2 candidates", "stage3 extraction", "stage4 validation"}


@pytest.fixture(scope="module")
def result():
    return run_pipeline(PDF)   # rules only; runs the whole pipeline once, shared by the tests below


def test_pipeline_returns_validated_records(result):
    out = result.output
    assert len(out.risks) == 12
    assert sum(r.kind.value == "risk" for r in out.risks) == 9
    assert sum(r.kind.value == "opportunity" for r in out.risks) == 3
    assert out.issues == []
    assert len(out.merges) == 1
    assert out.governance.review_frequency == "every six months"
    assert all(r.description_origin == "rules" for r in out.risks)


def test_final_file_is_written_and_matches_stage4(result):
    assert result.final_file.name == "VestasAnnualReport2025.risks.json"
    stage4 = INTERIM_DIR / "VestasAnnualReport2025.stage4.json"
    assert result.final_file.read_text(encoding="utf-8") == stage4.read_text(encoding="utf-8")


def test_every_stage_saves_its_own_file(result):
    for stage in ("stage1", "stage2", "stage3", "stage4"):
        assert (INTERIM_DIR / f"VestasAnnualReport2025.{stage}.json").exists(), stage


def test_all_four_stages_are_timed(result):
    assert set(result.seconds) == STAGE_NAMES


def test_rejects_a_missing_pdf(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_pipeline(tmp_path / "missing.pdf")


def test_rejects_a_file_that_is_not_a_pdf(tmp_path):
    notes = tmp_path / "notes.txt"
    notes.write_text("not a pdf")
    with pytest.raises(ValueError):
        run_pipeline(notes)


def test_cli_run_with_eval_passes(capsys):
    assert main(["run", str(PDF), "--eval"]) == 0
    assert "Evaluation: PASS (13 gates)" in capsys.readouterr().out


def test_cli_returns_1_for_a_missing_pdf(capsys, tmp_path):
    assert main(["run", str(tmp_path / "missing.pdf")]) == 1
    assert "Error:" in capsys.readouterr().out


def test_llm_flag_needs_credentials(monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: None)   # do not read the real .env file
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("RISK_LLM_MODEL", raising=False)
    with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
        build_summariser()