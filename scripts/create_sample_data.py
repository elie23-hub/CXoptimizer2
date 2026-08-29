"""
Generate a sample rental_survey.xlsx for testing the upload page.
Run once: python scripts/create_sample_data.py
"""

import random
from pathlib import Path

import pandas as pd

OUTPUT = Path(__file__).parent.parent / "data" / "rental_survey.xlsx"

COLUMNS = {
    "id": None,
    "OSAT Overall": None,
    # Section 1 — Logistics
    "S1_Q1 Deliv.": None,
    "S1_Q2 Ops": None,
    "S1_Q3 Insurance": None,
    "S1_Q4 On time": None,
    "S1_Q5 Vehicle cond.": None,
    # Section 2 — Staff & service
    "S2_Q1 Staff": None,
    "S2_Q2 Friendly": None,
    "S2_Q3 Knowledge": None,
    "S2_Q4 Response": None,
    "S2_Q5 Problem solve": None,
    # Section 3 — Booking & pricing
    "S3_Q1 Book.": None,
    "S3_Q2 Price": None,
    "S3_Q3 Transparency": None,
    "S3_Q4 Online": None,
}

STATEMENT_COLS = [c for c in COLUMNS if c.startswith("S")]


def random_rating():
    r = random.choices([1, 2, 3, 4, 5, 6], weights=[3, 5, 15, 30, 42, 5])[0]
    return r


def main():
    random.seed(42)
    rows = []
    for i in range(1, 313):
        row = {"id": f"R{i:03d}"}
        stmt_vals = []
        for col in STATEMENT_COLS:
            val = random_rating()
            row[col] = val
            if val != 6:
                stmt_vals.append(val)

        # Overall from average of valid + noise
        if stmt_vals:
            base = sum(stmt_vals) / len(stmt_vals)
            row["OSAT Overall"] = max(1, min(5, round(base + random.uniform(-0.5, 0.5))))
        else:
            row["OSAT Overall"] = 3

        rows.append(row)

    # One fully blank row (will be removed)
    blank = {col: ("" if col != "id" else "R999") for col in COLUMNS}
    rows.append(blank)

    df = pd.DataFrame(rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(OUTPUT, index=False)
    print(f"Created {OUTPUT} ({len(df)} rows, {len(STATEMENT_COLS)} statements)")


if __name__ == "__main__":
    main()
