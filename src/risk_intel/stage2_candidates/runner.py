"""Stage 2 runner: run the three readers and save one file for Stage 3."""
from __future__ import annotations

from pathlib import Path

from ..config import INTERIM_DIR
from ..stage1_document.models import DocumentLayout
from .governance_reader import read_governance
from .matrix_reader import read_matrix
from .models import Stage2Output
from .table_reader import read_tables

# Pages named in the case. The page finder (page_finder.py) is the scalable alternative:
# it proposes pages for reports where we don't know them.
CASE_SCOPE = {"governance": 50, "matrix": [51], "tables": [71, 72, 73, 74]}


def _load_sections(pdf_path: Path) -> dict[int, str | None]:
    """Page number -> section line, taken from the Stage 1 output."""
    stage1 = INTERIM_DIR / f"{pdf_path.stem}.stage1.json"
    if not stage1.exists():
        raise FileNotFoundError(f"{stage1} not found. Run Stage 1 first.")
    doc = DocumentLayout.model_validate_json(stage1.read_text(encoding="utf-8"))
    return {p.page_number: p.section for p in doc.pages}


def run_stage2(pdf_path: str | Path, scope: dict | None = None) -> Stage2Output:
    """Run all three readers and return one combined result."""
    pdf_path = Path(pdf_path)
    scope = scope or CASE_SCOPE
    sections = _load_sections(pdf_path)

    candidates = []
    for page in scope["matrix"]:
        candidates += read_matrix(pdf_path, page, sections.get(page))
    table_candidates, immaterial = read_tables(pdf_path, scope["tables"], sections)
    candidates += table_candidates
    governance = read_governance(pdf_path, scope["governance"])

    return Stage2Output(
        source_file=pdf_path.name,
        pages_used=sorted({scope["governance"], *scope["matrix"], *scope["tables"]}),
        candidates=candidates,
        immaterial_statements=immaterial,
        governance=governance,
    )


def save_stage2(output: Stage2Output, pdf_path: str | Path) -> Path:
    """Save the result so Stage 3 never has to re-read the PDF."""
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    out = INTERIM_DIR / f"{Path(pdf_path).stem}.stage2.json"
    out.write_text(output.model_dump_json(indent=2), encoding="utf-8")
    return out