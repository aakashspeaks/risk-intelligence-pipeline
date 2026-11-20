"""One call that runs Stages 1 to 4 and writes the final result.

Each stage still saves its own file in data/interim (so a later stage never re-reads the PDF),
and the validated records are also written to data/output as the final product.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import INTERIM_DIR, OUTPUT_DIR
from .stage1_document import read_document
from .stage1_document.models import DocumentLayout
from .stage2_candidates.runner import run_stage2, save_stage2
from .stage3_extraction.llm_summary import Summariser
from .stage3_extraction.runner import run_stage3, save_stage3
from .stage4_validation.models import Stage4Output
from .stage4_validation.runner import run_stage4, save_stage4


@dataclass
class PipelineResult:
    output: Stage4Output
    final_file: Path
    seconds: dict[str, float] = field(default_factory=dict)


def save_stage1(doc: DocumentLayout, pdf_path: str | Path) -> Path:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    out = INTERIM_DIR / f"{Path(pdf_path).stem}.stage1.json"
    out.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    return out


def run_pipeline(pdf_path: str | Path, summariser: Summariser | None = None, label: str = "") -> PipelineResult:
    """PDF in, validated risk records out. Pass a summariser to use the optional LLM step."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {pdf_path.name}")

    seconds: dict[str, float] = {}

    start = time.time()
    save_stage1(read_document(pdf_path), pdf_path)
    seconds["stage1 document"] = time.time() - start

    start = time.time()
    save_stage2(run_stage2(pdf_path), pdf_path)
    seconds["stage2 candidates"] = time.time() - start

    start = time.time()
    save_stage3(run_stage3(pdf_path, summariser, label), pdf_path)
    seconds["stage3 extraction"] = time.time() - start

    start = time.time()
    output = run_stage4(pdf_path)
    save_stage4(output, pdf_path)
    seconds["stage4 validation"] = time.time() - start

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    final_file = OUTPUT_DIR / f"{pdf_path.stem}.risks.json"
    final_file.write_text(output.model_dump_json(indent=2), encoding="utf-8")
    return PipelineResult(output=output, final_file=final_file, seconds=seconds)