# PLAN.md: Structured risk intelligence from annual reports

## Who is the user, and how do they consume the output?
Two users. **Analysts** at the research firm read 200+ annual reports a quarter and
often disagree on which risks matter. They want a draft of each company's principal
risks with page references, to review and correct instead of starting from scratch.
**Clients** (asset managers, compliance teams) consume the reviewed data by searching
and filtering, for example "top risks at Vestas and how often are they reviewed" or
"which renewable companies list cyber security as a principal risk".

## What does the product surface look like?
Eventually: a batch pipeline that processes each new report once and stores the records;
an analyst review screen showing each record beside its PDF page; a query API or UI for
clients; alerts for year-over-year changes. This slice is only the first box: one report
in, validated structured records out.

## What is this first slice optimising for?
Correctness and auditability first, coverage second. In a compliance product, an invented
risk is worse than a missing one that an analyst can add. So every record carries its
section, page and a quote from the source; the report's structure is parsed with rules
wherever it is explicit; and anything the report rules out is kept visible, not silently
dropped. Cost and throughput matter less here, but the design is cheap anyway: one light
pass over all pages, then careful reading of a few.

## Assumptions
- Text-based PDFs, as with Vestas. Scanned reports would need OCR.
- "Principal risks" means the report's own main-risk list (p.51). The sustainability tables
  (pp.71-74) are a second list, tagged separately. Only the financial side (risks and
  opportunities for the company) is in scope; opportunities must be labelled so they never
  appear as risks.
- The same risk can be disclosed in several places (cyber on p.51 and p.74): one risk with
  cross-references, not two.
- Categories come from a fixed list so companies can be compared. The category is our
  judgment, not the report's wording.
- Parsing rules are fitted to Vestas's layout. Other companies need a layout check.

## Approach
Classical first: layout-aware parsing and rules. An LLM is an optional fallback for
summaries and hard categories, because the report already structures its risks.

## Explicitly not solving here (next)
Year-over-year trends and emerging risks (needs two or more reports); other companies and
automatic page finding at scale (a prototype page finder exists but is not relied on);
scanned PDFs; the impact side of the tables; the cyber chapter (p.118) and climate pages
(pp.85-92); the analyst UI, the query API, and storage beyond JSON files.