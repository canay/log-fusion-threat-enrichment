# Traffic-Threat Linkage Audit

Raw enterprise exports are not redistributed. Absolute timestamps and local file paths are withheld in this public copy; only aggregate spans and linkage counts are reported.

## Rows and columns

- Traffic rows: 1,048,576
- Threat rows: 186,271
- Traffic columns: 128
- Threat columns: 131
- Common columns: 93

## Time spans

- Traffic receive-time span: 2794 seconds
- Threat receive-time span: 23426 seconds

## Session-level overlap

- Traffic unique nonzero session identifiers: 816,849
- Threat unique nonzero session identifiers: 22,214
- Traffic rows with nonzero session overlap: 19,311
- Threat nonzero session identifiers observed in traffic: 19,283
- Share of threat nonzero session identifiers observed in traffic: 0.868056

## Exact tuple overlap

- Key columns: session identifier, source endpoint, destination endpoint, source port, destination port, protocol
- Threat unique tuple keys: 59,507
- Threat unique nonzero session tuple keys: 22,464
- Traffic rows with nonzero session tuple overlap: 1,233
- Unique nonzero tuple keys overlapping: 1,233
