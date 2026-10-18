# Verified before one paid RunB replication

- Native build, UPX integrity, four paired probes, resource exactness, and
  preflight: pass. Candidate SHA-256:
  `21ca462e8065182a9b35b574c591506063d78d19c5227dc6afccc3bd66f42684`.
- Selective resource-ID list yields packed RunB SHA-256
  `c7f0e7ca83d8da07b34a44caa23659909ee40af1ebac73bde799e63492a423ca`;
  byte-identical to completed v15 fire. Packed local `rz-bin -z` finds
  each of 15 distinct complete resource bundles once in its own row,
  longest matched raw row 184 characters (<256 cutoff).
- RunB only; no previous reports in this new arm. The $5 spec field is NOT
  a hard cost limit. No model call occurred during preparation.
