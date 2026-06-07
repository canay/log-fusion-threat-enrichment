"""Compute per-column missingness for the processed modeling table.

Outputs data/reports_presubmission/missingness_summary.csv and verifies that
missing `Outbound Interface` rows coincide exactly with zero `Session ID` rows.
Used for the pre-submission audit (S19/S8) on 2026-06-04.

Note: the processed row-level CSV is not part of the public package; this script
documents how results/missingness_summary.csv was produced from the private table.
"""
from pathlib import Path
import pandas as pd

SRC = Path(__file__).resolve().parents[1] / "data/processed/traffic_has_linked_threat.csv"
OUT = Path(__file__).resolve().parents[1] / "data/reports_presubmission/missingness_summary.csv"

total = None
rows = 0
zero = miss = both = 0
for ch in pd.read_csv(SRC, chunksize=300_000, low_memory=False):
    nn = ch.isna().sum()
    total = nn if total is None else total + nn
    rows += len(ch)
    z = ch["Session ID"].eq(0)
    m = ch["Outbound Interface"].isna()
    zero += int(z.sum()); miss += int(m.sum()); both += int((z & m).sum())

df = total.rename("missing").to_frame()
df["share"] = df["missing"] / rows
df.to_csv(OUT)
print(f"rows={rows} zero_id={zero} outbound_nan={miss} intersection={both} identical={zero==miss==both}")
