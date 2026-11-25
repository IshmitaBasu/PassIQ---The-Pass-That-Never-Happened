# Phase 5: interactive Decision Room

Launch the dashboard after running the Phase 3 and Phase 4 commands:

```powershell
uv run streamlit run app/Home.py
```

The Decision Room reads the stored candidate rankings and never retrains a model. A user can select a World Cup match and pass event, choose either transparent ranking view, inspect the candidate table, and download a 16:9 PNG or SVG scene. Rendered files are cached by event ID under `reports/dashboard_cache/`.

The tactical-clip control is deliberately unavailable until Phase 6, when the animation renderer and media manifest are implemented. The app distinguishes the observed recorded pass from model-estimated alternatives and warns when the recorded-pass association is uncertain or ranking sensitivity is inconclusive.
