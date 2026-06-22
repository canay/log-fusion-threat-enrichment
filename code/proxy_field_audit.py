"""Value-level audit of policy/action proxy fields against the linked-threat label.

Computes, from the processed modeling table: Session End Reason / Threat-Content
Type / AI Traffic distributions by label, the SER=='threat' depth-one rule
baseline, the maximum observed session identifier, and the receive-time span of
the chronological test segment (last 20% of rows by receive time).
Output: data/reports_presubmission/proxy_field_audit.csv
Run for the 2026-06-05 reviewer-simulation response. The processed CSV is private.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/processed/traffic_has_linked_threat.csv"
OUT = ROOT / "data/reports_presubmission/proxy_field_audit.csv"
use = ['has_linked_threat','Session ID','Receive Time','Threat/Content Type','Session End Reason','AI Traffic']
rows = []
stores = {('Session End Reason',1):{},('Session End Reason',0):{},('Threat/Content Type',1):{},('Threat/Content Type',0):{},('AI Traffic',1):{},('AI Traffic',0):{}}
rt = []; sid_max = 0; n = 0; pos = 0; rule_tp = rule_fp = 0
for ch in pd.read_csv(SRC, chunksize=300_000, usecols=use, low_memory=False):
    n += len(ch); y = ch['has_linked_threat'].values; pos += int(y.sum())
    sid_max = max(sid_max, int(ch['Session ID'].max())); rt.append(ch['Receive Time'])
    for (col, lab), store in stores.items():
        vc = ch.loc[y == lab, col].astype(str).value_counts()
        for k, v in vc.items(): store[k] = store.get(k, 0) + int(v)
    m = ch['Session End Reason'].astype(str).eq('threat')
    rule_tp += int((m & (y == 1)).sum()); rule_fp += int((m & (y == 0)).sum())
for (col, lab), store in stores.items():
    t = sum(store.values())
    for k, v in store.items():
        rows.append({'field': col, 'label': lab, 'value': k, 'count': v, 'share': v / t})
rows.append({'field': 'rule_SER_eq_threat', 'label': '', 'value': 'precision', 'count': rule_tp, 'share': rule_tp / (rule_tp + rule_fp)})
rows.append({'field': 'rule_SER_eq_threat', 'label': '', 'value': 'recall', 'count': rule_tp, 'share': rule_tp / pos})
rows.append({'field': 'session_id', 'label': '', 'value': 'max_observed', 'count': sid_max, 'share': ''})
rts = pd.to_datetime(pd.concat(rt), errors='coerce').sort_values()
span = (rts.iloc[-1] - rts.iloc[int(len(rts) * 0.8)]).total_seconds()
rows.append({'field': 'temporal_test_segment', 'label': '', 'value': 'seconds', 'count': int(span), 'share': ''})
pd.DataFrame(rows).to_csv(OUT, index=False)
print('yazildi:', OUT, '| satir:', len(rows))
