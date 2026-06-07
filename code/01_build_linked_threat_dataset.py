"""Reference implementation of the linked-threat label construction.

Reproduces, from the two raw Palo Alto exports, the processed modeling table
and the linkage audit used in the paper. Released for transparency because the
raw exports themselves cannot be redistributed.

Pipeline (matches Section 3 of the manuscript):
  1. Load the traffic export (1,048,576 rows) and threat export (186,271 rows).
  2. Collect nonzero threat-side `Session ID` values (22,214 unique).
  3. Label a traffic row positive iff its nonzero `Session ID` appears in that
     set -> 19,311 positives (1.84%). Zero-valued identifiers (230,181 rows,
     21.95%) never match by rule.
  4. Strict diagnostic (not the target): additionally require equality of
     source/destination endpoint, source/destination port, and IP protocol
     -> 1,233 rows.
  5. Keep the 27 core predictors plus `Session ID` and time fields; drop raw
     IPs, user fields, hostnames, and direct identifiers.

UNTESTED-IN-PACKAGE NOTICE: this script ships without its inputs; it was
reconstructed from the audited pipeline and carries the expected counts as
assertions so that any holder of the raw exports can verify equivalence.
"""
import argparse, json
from pathlib import Path
import pandas as pd

EXPECTED = {
    "traffic_rows": 1_048_576, "threat_rows": 186_271,
    "threat_unique_nonzero_session_ids": 22_214,
    "positives": 19_311, "zero_id_rows": 230_181, "strict_tuple_rows": 1_233,
}
CORE = ['Action','Threat/Content Type','Session End Reason','Application','Source Zone',
        'Destination Zone','Inbound Interface','Outbound Interface','IP Protocol','Source Port',
        'Destination Port','Source Country','Destination Country','Category','Bytes','Bytes Sent',
        'Bytes Received','Packets','Packets Sent','Packets Received','Elapsed Time (sec)',
        'Subcategory of app','Category of app','Technology of app','Risk of app','SaaS of app','AI Traffic']
KEEP = ['Session ID','Receive Time','Generate Time','High Res Timestamp'] + CORE
TUPLE_COLS = ['Session ID','Source address','Destination address','Source Port','Destination Port','IP Protocol']

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--traffic', required=True); ap.add_argument('--threat', required=True)
    ap.add_argument('--outdir', default='data/processed')
    a = ap.parse_args()
    tr = pd.read_csv(a.traffic, low_memory=False)
    th = pd.read_csv(a.threat, low_memory=False)
    assert len(tr) == EXPECTED['traffic_rows'] and len(th) == EXPECTED['threat_rows']
    th_ids = set(th.loc[th['Session ID'] != 0, 'Session ID'].unique())
    assert len(th_ids) == EXPECTED['threat_unique_nonzero_session_ids']
    y = ((tr['Session ID'] != 0) & tr['Session ID'].isin(th_ids)).astype('int8')
    assert int(y.sum()) == EXPECTED['positives']
    assert int((tr['Session ID'] == 0).sum()) == EXPECTED['zero_id_rows']
    th_t = set(map(tuple, th.loc[th['Session ID'] != 0, TUPLE_COLS].itertuples(index=False)))
    strict = pd.Series(map(tuple, tr[TUPLE_COLS].itertuples(index=False))).isin(th_t) & (tr['Session ID'] != 0)
    assert int(strict.sum()) == EXPECTED['strict_tuple_rows']
    out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    res = tr[KEEP].copy(); res.insert(0, 'has_linked_threat', y.values)
    res.to_csv(out / 'traffic_has_linked_threat.csv', index=False)
    json.dump({'expected': EXPECTED, 'all_assertions_passed': True},
              open(out / 'linkage_build_audit.json', 'w'), indent=1)
    print('OK: dataset and audit written; all expected counts verified.')

if __name__ == '__main__':
    main()
