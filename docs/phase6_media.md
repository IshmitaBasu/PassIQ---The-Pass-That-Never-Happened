# Phase 6: tactical decision clips

Render an audited 12-second clip from Phase 4 rankings:

```powershell
uv run passiq render-clip --event-id <event-uuid> --output-dir reports/media
```

The command exports an H.264 MP4, GIF preview, and a `render_manifest.json` sidecar. It uses the bundled `imageio-ffmpeg` executable, so a separate system FFmpeg installation is not required.

The clip is a timed explanation of one observed 360 freeze frame: source citation, recorded pass, model-estimated alternatives, metric comparison, and a limitations card. Actors remain at their observed coordinates throughout. It contains no broadcast footage, invented movement, or claim that a hypothetical option happened.
