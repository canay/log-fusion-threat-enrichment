# Processed data boundary

No processed row-level dataset is distributed in this repository.

The manuscript and public package may report privacy-screened aggregate counts
and metrics. Institutional permission also covers anonymized aggregate
application, category, and policy-pocket summaries when they are derived from
the corrected same-session target and contain no row-level mapping.

Do not place any of the following under this directory:

- traffic or threat rows;
- raw or hashed session identifiers;
- absolute timestamps;
- IP addresses, hostnames, usernames, zones, interfaces, countries, or rules;
- row-level labels, predictions, or group hashes; or
- synthetic data that encodes the superseded predecessor target.

Authorized researchers must supply local paths to the restricted traffic,
threat, and processed predictor files when running the pipeline.
