# Phase 0 feasibility audit

**Run date:** 24 November 2026  
**Source:** StatsBomb Open Data, commit `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`  
**Method:** `passiq fetch --profile feasibility`, `normalize`, and `qa`

| Match ID | Fixture | Passes | 360 frames | Pass/frame joins | Pass-frame coverage | Frames without a visible teammate |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 3869685 | Argentina v France | 1,263 | 3,683 | 998 | 79.0% | 11 |
| 3869519 | Argentina v Croatia | 1,080 | 3,127 | 813 | 75.3% | 0 |
| 3869354 | England v France | 966 | 2,749 | 794 | 82.2% | 3 |
| **Total** | **Three fixtures** | **3,309** | **9,559** | **2,605** | **78.7%** | **14** |

All 9,559 frames link to a known event; there are no duplicate anonymous actor keys and no invalid event/pass coordinates. 1,585 raw freeze-frame actors lie slightly beyond the nominal pitch boundary, a retained source/camera-geometry characteristic documented in the [data dictionary](data_dictionary.md), rather than an event-data error.

The checked profile contains 66,701 visible teammate positions after excluding the event actor. The Phase 0 visual gate is satisfied by 20 deterministic, source-provenance sidecar scenes produced with `passiq fixture-gallery --limit 20`. The first vertical-slice fixture remains the Argentina–France final, while the gallery intentionally samples all three fixtures.

