"""Stage 4 runner: validate the Stage 3 records, merge duplicates, save the audit trail."""
from __future__ import annotations

from pathlib import Path

from ..config import INTERIM_DIR
from ..stage3_extraction.models import Stage3Output
from .checks import check_evidence, check_section, load_page_sections, load_page_tokens
from .dedupe import merge_duplicates
from .models import Issue, Stage4Output


def run_stage4(pdf_path: str | Path) -> Stage4Output:
    """Read the saved Stage 3 file (not the PDF), validate every record, merge duplicates."""
    stage3_file = INTERIM_DIR / f"{Path(pdf_path).stem}.stage3.json"
    if not stage3_file.exists():
        raise FileNotFoundError(f"{stage3_file} not found. Run Stage 3 first.")
    stage3 = Stage3Output.model_validate_json(stage3_file.read_text(encoding="utf-8"))

    page_tokens = load_page_tokens(pdf_path)
    page_sections = load_page_sections(pdf_path)

    # Validate every original record first, so a record that is about to be folded away is checked too.
    issues: list[Issue] = []
    for risk in stage3.risks:
        _, evidence_issue = check_evidence(risk, page_tokens)
        section_issue = check_section(risk, page_sections)
        issues += [i for i in (evidence_issue, section_issue) if i is not None]

    risks, merges = merge_duplicates(stage3.risks)

    return Stage4Output(
        source_file=stage3.source_file,
        risks=risks,
        excluded_immaterial=stage3.excluded_immaterial,
        governance=stage3.governance,
        issues=issues,
        merges=merges,
    )


def save_stage4(output: Stage4Output, pdf_path: str | Path) -> Path:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    out = INTERIM_DIR / f"{Path(pdf_path).stem}.stage4.json"
    out.write_text(output.model_dump_json(indent=2), encoding="utf-8")
    return out