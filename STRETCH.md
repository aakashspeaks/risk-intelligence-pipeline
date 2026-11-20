# STRETCH.md: what I would build next, with another week

1. **Other companies.** Add a section locator and a layout router so the pipeline finds risk pages on its
   own (the page finder is a start, but it only shortlists), with a layout-aware parser or an LLM as the
   fallback for layouts the rules don't know. Add 3 to 5 more reports to the golden set. Today the eval
   catches regressions on one report; it does not measure generalisation.
2. **Year-over-year.** Ingest the 2024 report, match risks across years, and report which are new, dropped
   or reworded. This answers the case's "newly elevated" question and needs at least two reports.
3. **Harden risk vs opportunity.** Today it is a default driven by wording. Page 85 states "Type of impact"
   in text ("Financial opportunity", "Financial transition risk"), which could serve as an independent check
   for the climate items; a vision model or shape classifier on the table icons would cover the rest.
4. **A trustworthy answer key.** A second annotator, agreement on the category labels, and a bigger golden
   set. Mine is partly my own reading, and categories are judgment calls.
5. **Models.** Compare a second and a weaker model through the same gates, track the LLM fallback rate
   (100% fallback hides behind a green gate), and add a faithfulness judge calibrated on analyst edits.
6. **More of the report.** The cyber chapter (p.118: four-pillar mitigation, time horizon), the climate
   pages (pp.85 to 92), and the impact side of the tables as linked records.
7. **The product around it.** Analyst review screen showing each record beside its PDF page, a review
   queue for records with issues, a query API and storage beyond JSON files, asynchronous batch processing
   for hundreds of reports a quarter, and alerts on year-over-year changes.
8. **Housekeeping.** Fill the topic group on table records, detect duplicates that are worded differently,
   let mitigation coverage catch extra text as well as missing text, and share the stop-word list between
   stages.