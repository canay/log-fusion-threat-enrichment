"""Generate a small SYNTHETIC schema sample for the linked-threat pipeline.

Purpose
-------
The real row-level processed dataset (`data/processed/traffic_has_linked_threat.csv`)
is not publicly redistributed: it derives from institutional firewall telemetry and
requires explicit institutional authorization plus a privacy/security review before
any release (see `data/processed/README.md`). To keep the expected input structure
inspectable and the pipeline smoke-testable WITHOUT any operational data, this
script generates a ~100-row synthetic sample with the same column layout and
plausible vendor-style value domains.

Guarantees
----------
- No value in the output is drawn from the operational corpus. All rows are
  generated from the fixed rules below with a fixed random seed.
- Timestamps use a deliberately fake base date (2000-01-01) so the file cannot be
  mistaken for a real capture window.
- The positive share is intentionally set to 5/100 (higher than the real 1.84%
  natural prevalence) so that stratified train/test splitting code paths remain
  runnable on this tiny file. The sample CANNOT reproduce any reported result.

Usage
-----
    python code/make_synthetic_sample.py            # writes data/synthetic/
    python code/make_synthetic_sample.py --rows 100 --seed 42

Smoke test of the benchmark loader (optional):
    copy the output over data/processed/traffic_has_linked_threat.csv in a
    scratch clone, then run code/03_benchmark_baseline.py --dataset linked_full.
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

# App-conditional vendor-style metadata (subcategory, app category, technology,
# risk, saas). Values mirror the app families named in the published aggregate
# error profiles; the mapping itself is generic vendor taxonomy, not telemetry.
APP_PROFILES = {
    "dns-base": ("infrastructure", "networking", "network-protocol", 3, "no"),
    "web-browsing": ("internet-utility", "general-internet", "browser-based", 4, "no"),
    "ssl": ("encrypted-tunnel", "networking", "browser-based", 4, "no"),
    "ping": ("infrastructure", "networking", "network-protocol", 1, "no"),
    "snmpv3-get-request": ("network-management", "networking", "client-server", 2, "no"),
    "insufficient-data": ("unknown", "unknown", "unknown", 1, "no"),
    "telegram-base": ("instant-messaging", "collaboration", "client-server", 2, "yes"),
    "unknown-tcp": ("unknown", "unknown", "unknown", 1, "no"),
}

APP_WEIGHTS = [30, 18, 16, 10, 10, 8, 4, 4]
APP_PORTS = {
    "dns-base": (53, "udp"),
    "web-browsing": (80, "tcp"),
    "ssl": (443, "tcp"),
    "ping": (0, "icmp"),
    "snmpv3-get-request": (161, "udp"),
    "insufficient-data": (8443, "tcp"),
    "telegram-base": (443, "tcp"),
    "unknown-tcp": (7547, "tcp"),
}

ZONES = ["LAN", "WAN", "DMZ", "WAF"]
INTERFACES = ["ethernet1/1", "ethernet1/2", "ethernet1/3", "ae1.10"]
COUNTRIES = ["Private-Use", "United States", "Germany", "Netherlands", "France"]
END_REASONS_NEG = ["aged-out", "tcp-fin", "tcp-rst-from-client", "tcp-rst-from-server", "threat"]
END_WEIGHTS_NEG = [40, 25, 15, 10, 10]

COLUMNS = [
    "Receive Time",
    "receive_time_offset_sec",
    "Session ID",
    "session_key",
    "Type",
    "Threat/Content Type",
    "Rule",
    "Action Source",
    "Action",
    "Session End Reason",
    "Application",
    "Source Zone",
    "Destination Zone",
    "Inbound Interface",
    "Outbound Interface",
    "IP Protocol",
    "Source Port",
    "Destination Port",
    "Source Country",
    "Destination Country",
    "Category",
    "Bytes",
    "Bytes Sent",
    "Bytes Received",
    "Packets",
    "Packets Sent",
    "Packets Received",
    "Elapsed Time (sec)",
    "Subcategory of app",
    "Category of app",
    "Technology of app",
    "Risk of app",
    "SaaS of app",
    "AI Traffic",
    "has_linked_threat",
]


def make_row(rng: random.Random, idx: int, positive: bool) -> dict:
    if positive:
        # Positives echo the published high-confidence pocket: allowed dns-base
        # sessions with threat-related termination toward DMZ/WAN.
        app = rng.choices(["dns-base", "web-browsing"], weights=[85, 15])[0]
        end_reason = rng.choices(["threat", "tcp-fin"], weights=[95, 5])[0]
        action = "allow"
        dst_zone = rng.choices(["DMZ", "WAN", "WAF"], weights=[63, 29, 8])[0]
    else:
        app = rng.choices(list(APP_PROFILES), weights=APP_WEIGHTS)[0]
        end_reason = rng.choices(END_REASONS_NEG, weights=END_WEIGHTS_NEG)[0]
        action = rng.choices(["allow", "drop"], weights=[96, 4])[0]
        dst_zone = rng.choice(ZONES)

    sub, cat, tech, risk, saas = APP_PROFILES[app]
    dport, proto = APP_PORTS[app]
    src_zone = rng.choices(["LAN", "WAN", "DMZ"], weights=[70, 20, 10])[0]
    pkts_sent = rng.randint(1, 40)
    pkts_recv = rng.randint(0, 40)
    bytes_sent = pkts_sent * rng.randint(60, 900)
    bytes_recv = pkts_recv * rng.randint(60, 1400)
    offset = idx * rng.randint(1, 25)  # synthetic offsets inside a short window

    return {
        "Receive Time": f"2000/01/01 00:{offset // 60 % 60:02d}:{offset % 60:02d}",
        "receive_time_offset_sec": offset,
        "Session ID": 100000 + idx,
        "session_key": f"synthetic-{idx:04d}",
        "Type": "TRAFFIC",
        "Threat/Content Type": "end" if action == "allow" else "drop",
        "Rule": f"synthetic-rule-{rng.randint(1, 3)}",
        "Action Source": "from-policy",
        "Action": action,
        "Session End Reason": end_reason,
        "Application": app,
        "Source Zone": src_zone,
        "Destination Zone": dst_zone,
        "Inbound Interface": rng.choice(INTERFACES),
        "Outbound Interface": rng.choice(INTERFACES),
        "IP Protocol": proto,
        "Source Port": rng.randint(1024, 65535),
        "Destination Port": dport,
        "Source Country": "Private-Use",
        "Destination Country": rng.choice(COUNTRIES),
        "Category": rng.choice(["any", "unknown", "computer-and-internet-info"]),
        "Bytes": bytes_sent + bytes_recv,
        "Bytes Sent": bytes_sent,
        "Bytes Received": bytes_recv,
        "Packets": pkts_sent + pkts_recv,
        "Packets Sent": pkts_sent,
        "Packets Received": pkts_recv,
        "Elapsed Time (sec)": rng.choices([0, rng.randint(1, 300)], weights=[60, 40])[0],
        "Subcategory of app": sub,
        "Category of app": cat,
        "Technology of app": tech,
        "Risk of app": risk,
        "SaaS of app": saas,
        "AI Traffic": "no",
        "has_linked_threat": int(positive),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows", type=int, default=100)
    ap.add_argument("--positives", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--outdir", default="data/synthetic")
    a = ap.parse_args()

    rng = random.Random(a.seed)
    positive_idx = set(rng.sample(range(a.rows), a.positives))
    rows = [make_row(rng, i, i in positive_idx) for i in range(a.rows)]

    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "traffic_has_linked_threat_synthetic.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {path} ({a.rows} rows, {a.positives} positives, seed {a.seed})")


if __name__ == "__main__":
    main()
