# Vestas risk intelligence pipeline

Turns the Vestas Annual Report 2025 (PDF) into validated, page-cited risk records, and scores the result
against a hand-checked golden set. Built for the case study; see PLAN.md, DESIGN.md and STRETCH.md.

## Setup

Needs [uv](https://docs.astral.sh/uv/) and Python 3.12.

```
uv sync
```

Put the report at `data/raw/VestasAnnualReport2025.pdf`.

## Run

```
uv run risk-intel run data/raw/VestasAnnualReport2025.pdf --eval
```

The same thing as a plain Python file call (no shortcut needed):

```
uv run python -m risk_intel.cli run data/raw/VestasAnnualReport2025.pdf --eval
```

No API key is needed: the default run uses rules only.

Reads the PDF, runs stages 1 to 4, writes `data/output/VestasAnnualReport2025.risks.json`, and scores it
against the golden set. Takes about 8.5 seconds. It exits with an error code if any gate fails.

Expected result: 12 records (9 risks, 3 opportunities), 0 issues, 1 merge, the review frequency
("every six months", by the Executive Management Team, the Board and the Audit Committee), and
`Evaluation: PASS (13 gates)`.

Each stage also saves its own file in `data/interim/`. Stages 3 to 5 work from those files and never open the
PDF; Stage 2 re-opens it for the case pages only, because it needs word positions the Stage 1 file does not keep.
Stage 1 alone: `uv run risk-intel stage1 data/raw/VestasAnnualReport2025.pdf`.

## Tests

```
uv run pytest -q
```

88 tests. The tests that use the real report need the PDF in `data/raw` and the stage files in
`data/interim` (created by running the pipeline once); they skip themselves if those are missing.
The tests never call the LLM API.

## Optional LLM step

`--llm` rewrites the 3 principal-risk descriptions with a model. Create a `.env` file in the project root:

```
OPENAI_API_KEY=your-key
RISK_LLM_MODEL=your-model-name
```

then run the command above with `--llm`. A summary is used only if it passes the checks in
`stage3_extraction/llm_summary.py`; otherwise the rule-based text is kept and the reason is recorded in
`description_origin`. Never commit `.env`. The pipeline works without any of this.

## Layout

```
src/risk_intel/
  stage1_document/     page map: layout type, columns, section, title
  stage2_candidates/   matrix, table and governance readers; page finder
  stage3_extraction/   categories, risk or opportunity, descriptions, optional LLM
  stage4_validation/   evidence and section checks, duplicate merge
  stage5_evaluation/   golden set, evaluators, the gate, fault injection
  pipeline.py, cli.py  the one-command run
data/golden/           the golden set
reports/sample_run.md  a regression caught by the gate
scripts/               helper scripts used while building (not part of the product)
```

## Limits

The readers are fitted to Vestas's layout and to the case's pages (50-51, 71-74). The golden set is one
report. See "Known limits" in DESIGN.md.