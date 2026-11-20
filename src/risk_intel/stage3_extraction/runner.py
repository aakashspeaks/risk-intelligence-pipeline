"""Stage 3 runner: Stage 2 candidates in, final risk records out."""
from __future__ import annotations

from pathlib import Path

from ..config import INTERIM_DIR
from ..stage2_candidates.models import Stage2Output
from .build import to_risk
from .models import Stage3Output


def run_stage3(pdf_path: str | Path, summariser=None, label: str = "") -> Stage3Output:
    """Read the saved Stage 2 file (not the PDF) and build the final records."""
    stage2_file = INTERIM_DIR / f"{Path(pdf_path).stem}.stage2.json"
    if not stage2_file.exists():
        raise FileNotFoundError(f"{stage2_file} not found. Run Stage 2 first.")
    stage2 = Stage2Output.model_validate_json(stage2_file.read_text(encoding="utf-8"))

    return Stage3Output(
        source_file=stage2.source_file,
        #risks=[to_risk(c) for c in stage2.candidates],
        risks=[to_risk(c, summariser, label) for c in stage2.candidates],
        excluded_immaterial=stage2.immaterial_statements,
        governance=stage2.governance,
    )


def save_stage3(output: Stage3Output, pdf_path: str | Path) -> Path:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    out = INTERIM_DIR / f"{Path(pdf_path).stem}.stage3.json"
    out.write_text(output.model_dump_json(indent=2), encoding="utf-8")
    return out