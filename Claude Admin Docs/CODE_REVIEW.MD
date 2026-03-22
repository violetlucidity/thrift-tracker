These are instructions for a code review.

Prior to writing this review, please utilize a 'dry run' (--dry-run) of all parts of the program to make sure it's working. Then, structure the review as follows:

**Section 1 — Executive Summary**
Three to five sentences: overall quality, major strengths, most critical issues.

**Section 2 — Failure Points**
For each failure point:
  - Location: file name and line number range
  - Description: what can go wrong and under what conditions
  - Severity: Critical / High / Medium / Low
  - Recommended fix: one to three sentences


**Section 3 — Areas for Improvement**
Five to ten specific, actionable improvements that are not strictly bugs.
For each: state the file and approximate line, and explain the benefit.

**Section 4 — Autonomy-Specific Weaknesses**
Risks introduced by unattended execution:
  - Silent failures: completes without error but produces wrong output.
  - Feedback gaps: problems a human would catch that the output does not flag.
  - Data drift: what happens when FDA label formatting changes in ways the
    current patterns do not anticipate.
  - Logging adequacy: is there sufficient logging to diagnose a failure after
    the fact without re-running the script?

**Section 5 — DATA_ABSENT Drugs — Recommended Path Forward**
For drugs classified as DATA_ABSENT in `PATTERN_INVESTIGATION.md`, provide
a brief technical recommendation for how their study data could be extracted
in a future module (e.g. OCR table extraction, FDA API queries, semi-automated
human review). Do not implement — recommend and explain only.

**Section 6 — Summary Scorecard**

| Dimension              | Score (1–5) | Rationale (one sentence) |
|------------------------|-------------|--------------------------|
| Correctness            |             |                          |
| Robustness             |             |                          |
| Readability            |             |                          |
| Autonomy-readiness     |             |                          |
| Documentation quality  |             |                          |

