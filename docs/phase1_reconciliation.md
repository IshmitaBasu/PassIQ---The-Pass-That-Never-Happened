# Phase 1 full-scope reconciliation

**Run date:** 24 November 2026  
**Scope:** all 64 matches in StatsBomb competition `43`, season `106`  
**Source revision:** `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`

| Measure | Value |
| --- | ---: |
| Recorded events | 234,637 |
| Recorded passes | 68,515 |
| 360 frames | 203,882 |
| Anonymous frame actors | 3,084,800 |
| Passes joined to a 360 frame | 57,393 (83.77%) |
| Visible teammate positions after actor exclusion | 1,339,421 |
| Frames without visible teammate candidates | 209 |
| Fixture metadata rows without event rows | 0 |
| Missing event/frame links | 0 |
| Duplicate anonymous actor keys | 0 |
| Invalid event/pass coordinates | 0 |
| Raw actor coordinates beyond pitch boundary | 31,638 |

The final row is preserved as source camera/calibration geometry, described in the [data dictionary](data_dictionary.md); it is not an event-coordinate failure. The committed source manifest records an upstream URL and SHA-256 for every downloaded file. Re-running `passiq fetch --profile tournament` first verifies each checksum, and `normalize` rewrites the Silver tables deterministically.

