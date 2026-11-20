# DESIGN.md

## Stack
Python 3.12 managed with uv. `pdfplumber` reads the PDF (word positions, font weight, ruled lines),
`pydantic` v2 defines every record, `pytest` runs 88 tests. The optional LLM step uses the OpenAI SDK
(tested with gpt-4.1-mini). No NER model or NLP library: the report states its risks in clear
structures, so rules and layout parsing were enough here.

## How the work is split
Five stages. Each saves its own JSON in `data/interim`. Stages 3 to 5 work from those files and never open
the PDF. Stage 2 re-opens the PDF for the case pages only, because it needs word positions, fonts and rule
lines, which the Stage 1 file does not keep (it stores flat page text, not positions).
1. **Document map.** Scans all 195 pages once: layout type, columns, table lines, section, title.
2. **Candidates.** Three readers cut out raw candidates: a matrix reader (p.51 risk grid), a table reader
   (pp.71-74), and a governance reader (p.50: review frequency). A page finder scores pages but is
   advisory only; the case's pages are the input.
3. **Records.** Rules assign a category, label risk or opportunity, and trim descriptions to at most
   3 sentences. An optional LLM step rewrites principal-risk summaries.
4. **Validation.** Checks that each quote is on the cited page, that the section matches, and merges
   duplicates (cyber appears on pp.51 and 74).
5. **Evaluation.** A hand-checked golden set (12 records) and 13 gates; `risk-intel run <pdf> --eval`.

## Parsing approach
Plain text extraction splices the three risk columns on p.51, so I rebuild the grid from word positions
(row labels give rows, 12 pt titles give columns). The tables use rule lines for rows and bold font for
entry names. The PDF has no bookmarks, so the section comes from the blue active item in each page's menu.

## Trade-offs, traced to PLAN.md
- **Correctness and auditability over coverage.** Rules first; every record carries section, page and a
  quote; topics the report rules out are kept in a separate list; opportunities are labelled so they cannot
  appear as risks; duplicates merge with cross-references.
- **LLM only where rules are weakest, behind a safety net.** The model sees one risk's text. A summary is
  accepted only if it has at most 3 sentences, invents no numbers, and 75% of each sentence's words are in
  the source; otherwise the rule-based text is used and the reason is recorded. In a real run all 3
  summaries were accepted and all 13 gates passed. With a deliberately permissive prompt the net rejected
  all 3; with the net off, the grounding gate failed (0.771). I have not shown that the model beats the
  rules, only that the checks catch an unfaithful one.
- **pdfplumber over PyMuPDF.** Same 641 words on p.51, but PyMuPDF read the whole report in 1.2 s
  against 7.7 s. I kept pdfplumber for exact word positions and ruled lines, which the table reader needs.
  PyMuPDF is AGPL-licensed, which matters commercially.
- **Eval design.** Gates are all 1.0 because the golden set is small, so any single fault must fail.
  With the page 51 reader broken, contamination fails on all three principal risks and mitigation coverage
  on one phrase, while grounding and evidence stay at 1.0 because the spliced words really are on the page.

## Scaling
One report takes about 8.5 s on a laptop, 8.0 s of it in Stage 1. 200 reports is about 28 minutes
serially (simple arithmetic from one run), and reports are independent, so they can run in parallel.
LLM cost is per principal risk (3 calls here, each about 100 words of source). In production I would track
the LLM fallback rate: 100% fallback would hide behind a green gate.

## Known limits
- Page scope is the case's pages; the readers are fitted to Vestas's layout. Other companies need a
  section locator and a layout router, with a layout-aware parser or an LLM as fallback. Not built.
- Stage 1 limits. (a) The saved page text is read line by line across the page, so on multi-column pages
  (for example pp.50 and 51) the columns are mixed; the readers avoid this by cutting the page from word
  positions, but the Stage 1 text should not be used as clean reading order. (b) The page title is the
  largest text on the page, so about 10 of 195 pages with a large statistic get that number as the title
  (p.7 gives "22,000+" instead of "Highlights for the year"). Only the page finder uses the title, and the
  case pages are unaffected. (c) The scan of all 195 pages is 8.0 of the 8.5 s. The run uses it for the section
  line on each candidate (Stage 2) and for the evidence and section checks (Stage 4); the page finder, its
  other consumer, is not used in the run. Scanning only the cited pages would cut most of that time.
- One report, one golden set, partly my own labelling; categories are judgment calls.
- Risk vs opportunity comes from the wording ("opportunity"), because the report marks it with an icon.
- One model, one run. Table entries keep the one sentence the report gives them.