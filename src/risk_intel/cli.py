# from __future__ import annotations

# import argparse
# from collections import Counter
# from pathlib import Path

# from .config import INTERIM_DIR
# from .stage1_document import read_document

# KEY_PAGES = [50, 51, 71, 72, 73, 74, 75, 85, 118]  # the pages our case points to, plus page 75


# def run_stage1(pdf_path: str) -> int:
#     pdf = Path(pdf_path)
#     if not pdf.exists():
#         print(f"File not found: {pdf}")
#         return 1

#     print(f"Reading {pdf.name} ... (this takes about a minute)")
#     doc = read_document(pdf)

#     # Save the result so later stages never need to re-read all 195 pages.
#     INTERIM_DIR.mkdir(parents=True, exist_ok=True)
#     out = INTERIM_DIR / f"{pdf.stem}.stage1.json"
#     out.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
#     print(f"{doc.n_pages} pages, {len(doc.sections)} section runs -> {out}")

#     print("\nLayout types:")
#     for kind, n in Counter(p.layout_type for p in doc.pages).most_common():
#         print(f"  {n:4d}  {kind}")

#     print("\nKey pages:")
#     for n in KEY_PAGES:
#         if n <= doc.n_pages:
#             p = doc.pages[n - 1]
#             print(f"  p{n:<4d} {p.layout_type:16s} cols={p.n_columns} rules={p.n_rule_lines:<3d}"
#                   f" | {p.part} > {p.section} | {p.title}")
#     return 0


# def main(argv: list[str] | None = None) -> int:
#     parser = argparse.ArgumentParser(prog="risk-intel")
#     sub = parser.add_subparsers(dest="command", required=True)
#     s1 = sub.add_parser("stage1", help="Read the PDF and describe every page")
#     s1.add_argument("pdf")
#     args = parser.parse_args(argv)
#     if args.command == "stage1":
#         return run_stage1(args.pdf)
#     return 1


# if __name__ == "__main__":
#     raise SystemExit(main())

from __future__ import annotations

import argparse
import os
from collections import Counter
from pathlib import Path

from .config import INTERIM_DIR
from .pipeline import run_pipeline
from .stage1_document import read_document

KEY_PAGES = [50, 51, 71, 72, 73, 74, 75, 85, 118]  # the pages our case points to, plus page 75


def run_stage1(pdf_path: str) -> int:
    pdf = Path(pdf_path)
    if not pdf.exists():
        print(f"File not found: {pdf}")
        return 1

    print(f"Reading {pdf.name} ... (this takes about a minute)")
    doc = read_document(pdf)

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    out = INTERIM_DIR / f"{pdf.stem}.stage1.json"
    out.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    print(f"{doc.n_pages} pages, {len(doc.sections)} section runs -> {out}")

    print("\nLayout types:")
    for kind, n in Counter(p.layout_type for p in doc.pages).most_common():
        print(f"  {n:4d}  {kind}")

    print("\nKey pages:")
    for n in KEY_PAGES:
        if n <= doc.n_pages:
            p = doc.pages[n - 1]
            print(f"  p{n:<4d} {p.layout_type:16s} cols={p.n_columns} rules={p.n_rule_lines:<3d}"
                  f" | {p.part} > {p.section} | {p.title}")
    return 0


def build_summariser():
    """The optional LLM step. Needs OPENAI_API_KEY and RISK_LLM_MODEL (read from the .env file)."""
    from dotenv import load_dotenv

    load_dotenv()
    model = os.environ.get("RISK_LLM_MODEL")
    if not os.environ.get("OPENAI_API_KEY") or not model:
        raise SystemExit("--llm needs OPENAI_API_KEY and RISK_LLM_MODEL in the .env file")

    from openai import OpenAI

    from .stage3_extraction.llm_summary import openai_summariser

    return openai_summariser(OpenAI(), model), model


def run_all(pdf_path: str, use_llm: bool, run_eval: bool) -> int:
    summariser, label = build_summariser() if use_llm else (None, "")
    mode = f"with LLM summaries ({label})" if use_llm else "rules only"
    print(f"Running the pipeline on {Path(pdf_path).name}, {mode} ...")

    try:
        result = run_pipeline(pdf_path, summariser, label)
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}")
        return 1

    out = result.output
    print(f"\nFinal result: {result.final_file}")
    print(f"records: {len(out.risks)} {dict(Counter(r.kind.value for r in out.risks))}")
    print(f"issues: {len(out.issues)} | merges: {len(out.merges)} | excluded as immaterial: {len(out.excluded_immaterial)}")
    if out.governance:
        print(f"risks reviewed {out.governance.review_frequency} by {', '.join(out.governance.reviewed_by)}")
    print(f"descriptions from: {dict(Counter(r.description_origin.split(' (')[0] for r in out.risks))}")
    print(f"time: {sum(result.seconds.values()):.1f} s")

    if run_eval:
        from .stage4_validation.checks import load_page_tokens
        from .stage5_evaluation.gate import evaluate
        from .stage5_evaluation.golden import DEFAULT_GOLDEN, load_golden

        if not DEFAULT_GOLDEN.exists():
            print(f"\nNo golden set found at {DEFAULT_GOLDEN}")
            return 1
        report = evaluate(out, load_golden(), load_page_tokens(pdf_path))
        print(f"\nEvaluation: {'PASS' if report.passed else 'FAIL'} ({len(report.scores)} gates)")
        if report.failed:
            print("  failed gates:", report.failed)
            return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="risk-intel")
    sub = parser.add_subparsers(dest="command", required=True)

    s1 = sub.add_parser("stage1", help="Read the PDF and describe every page")
    s1.add_argument("pdf")

    run = sub.add_parser("run", help="Run the whole pipeline: PDF in, validated risk records out")
    run.add_argument("pdf")
    run.add_argument("--llm", action="store_true", help="Use the optional LLM step for principal-risk summaries")
    run.add_argument("--eval", action="store_true", help="Score the result against the golden set")

    args = parser.parse_args(argv)
    if args.command == "stage1":
        return run_stage1(args.pdf)
    return run_all(args.pdf, args.llm, args.eval)


if __name__ == "__main__":
    raise SystemExit(main())