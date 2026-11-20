"""Deliberate faults, used to prove the gate catches realistic regressions.
Test-only code: the real pipeline never imports this file."""
from __future__ import annotations

from pathlib import Path

import pdfplumber

from ..stage2_candidates.matrix_reader import ROW_LABELS, _join, _row_tops, read_matrix
from ..stage2_candidates.models import RiskCandidate, Stage2Output
from ..stage3_extraction.build import to_risk
from ..stage4_validation.dedupe import merge_duplicates
from ..stage4_validation.models import Stage4Output

RISK_COLUMNS_START_X = 225   # the row labels sit left of this; the three risk columns start at about x=232


def read_matrix_columns_spliced(pdf_path: str | Path, page_number: int,
                                section: str | None = None) -> list[RiskCandidate]:
    """BROKEN on purpose: reads each row straight across all three columns, as a plain
    reader would. Titles stay right, but every risk gets the spliced text of all three."""
    good = read_matrix(pdf_path, page_number, section)
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_number - 1]
        words = page.extract_words(extra_attrs=["size"])
        tops = _row_tops(words)
        desc_top, impact_top, manage_top = (tops[label] for label in ROW_LABELS)
        footer_top = min((w["top"] for w in words if w["text"] == "Vestas" and w["top"] > 500),
                         default=page.height)

        def row(top: float, bottom: float) -> str:
            return _join([w for w in words
                          if w["x0"] >= RISK_COLUMNS_START_X and top - 2 <= w["top"] < bottom - 2])

        description = row(desc_top, impact_top)
        impact = row(impact_top, manage_top)
        mitigation = row(manage_top, footer_top - 5)

    return [c.model_copy(update={"description": description, "potential_impact": impact,
                                 "mitigation": mitigation, "evidence": description[:200]})
            for c in good]


def build_output(stage2: Stage2Output) -> Stage4Output:
    """Stages 3 and 4 in memory, so a faulty run never overwrites the real files in data/interim."""
    risks, merges = merge_duplicates([to_risk(c) for c in stage2.candidates])
    return Stage4Output(source_file=stage2.source_file, risks=risks,
                        excluded_immaterial=stage2.immaterial_statements,
                        governance=stage2.governance, merges=merges)


def run_with_spliced_columns(pdf_path: str | Path) -> Stage4Output:
    """Run Stage 2 with the broken matrix reader swapped in, then Stages 3 and 4 as normal."""
    from ..stage2_candidates import runner

    original = runner.read_matrix
    runner.read_matrix = read_matrix_columns_spliced
    try:
        stage2 = runner.run_stage2(pdf_path)
    finally:
        runner.read_matrix = original   # always put the real reader back
    return build_output(stage2)