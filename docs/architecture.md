# Phase 0–1 architecture

```mermaid
flowchart LR
  S[StatsBomb Open Data\npinned commit] --> F[fetch\nSHA-256 manifest]
  F --> R[gitignored raw JSON]
  R --> N[streaming normalizer]
  N --> P[Silver Parquet\nevents, passes, frames, actors]
  P --> Q[reconciliation QA]
  P --> V[source-preview pitch]
  Q --> A[feasibility audit]
```

The fetcher follows only the commit in `manifests/source_data.json`. The normalizer writes typed Parquet a match at a time, so all 64 matches do not have to be held in memory. Anonymous 360 actors have their own table and never acquire player IDs.

