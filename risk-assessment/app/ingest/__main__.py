"""`python -m app.ingest` — offline workbook -> catalog pipeline.

Phase 2 implementation (plan §8). Until then the command reports that
ingestion is not yet implemented and exits non-zero.
"""

import sys


def main() -> int:
    print(
        "app.ingest is not implemented yet (Phase 2). "
        "See docs/risk-assessment/IMPLEMENTATION_PLAN_RISK_ASSESSMENT.md §8."
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
