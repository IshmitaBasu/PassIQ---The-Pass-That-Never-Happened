# Phase 0 feasibility plan

The audited feasibility profile contains the 2022 World Cup final (`3869685`), Argentina–Croatia semi-final (`3869519`), and England–France quarter-final (`3869354`). These cover late-tournament game states and allow event/frame coverage to be checked across three fixtures. `passiq fetch --profile feasibility`, followed by `normalize` and `qa`, creates the quantitative profile in `data/silver/qa_summary.json`.

The first preview selects the joined pass frame with the greatest visible teammate count. This deterministic choice is a data-quality proof, not a claim that the event is tactically representative. Its event UUID, source commit, and selection rule are written into the PNG metadata and a sidecar JSON file.

