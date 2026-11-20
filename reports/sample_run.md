# Sample run: a regression caught by the eval gate

**Fault injected:** the page 51 matrix reader reads each row straight across all three risk columns, as a plain reader would. Titles stay correct, but every risk receives the spliced text of all three risks.

**Result:** baseline PASS, regression FAIL.

| gate | threshold | baseline | regression | status |
|---|---|---|---|---|
| recall | 1.0 | 1.0 | 1.0 | ok |
| precision | 1.0 | 1.0 | 1.0 | ok |
| principal_recall | 1.0 | 1.0 | 1.0 | ok |
| category_accuracy | 1.0 | 1.0 | 1.0 | ok |
| kind_accuracy | 1.0 | 1.0 | 1.0 | ok |
| tier_accuracy | 1.0 | 1.0 | 1.0 | ok |
| page_accuracy | 1.0 | 1.0 | 1.0 | ok |
| immaterial_leak_free | 1.0 | 1.0 | 1.0 | ok |
| evidence_accuracy | 1.0 | 1.0 | 1.0 | ok |
| grounding | 1.0 | 1.0 | 1.0 | ok |
| mitigation_coverage | 1.0 | 1.0 | 0.833 | FAIL |
| contamination_free | 1.0 | 1.0 | 0.0 | FAIL |
| governance | 1.0 | 1.0 | 1.0 | ok |

**What the evaluator reported:**

- Cyber attacks: contains 'tariffs'
- Project execution: contains 'hedging'
- Project execution: contains 'indexation'
- Project execution: contains 'cyber'
- Geopolitics and regulatory framework: contains 'cyber'

**Mitigation phrases the broken run lost:**

- Cyber attacks: mitigation lacks 'critical infrastructure'

**Why this matters:** contamination is the primary detector. All three principal risks received words from a neighbouring risk, and no other check looks for that. One expected mitigation phrase was also missing from the Cyber attacks record, so mitigation coverage failed too. We have not investigated why that particular phrase was lost.

The gates that compare a record's text with its page (grounding, evidence accuracy) stayed at 1.0, because the spliced words really are on page 51. A check that only asked whether the text appears on the page would have let this regression through.
