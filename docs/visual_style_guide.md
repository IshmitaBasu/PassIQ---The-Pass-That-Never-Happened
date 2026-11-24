# Visual style guide

PassIQ uses a 120 × 80 StatsBomb coordinate pitch. Source coordinates stay raw for replay; future value calculations may normalize attack direction in a separate, tested field.

| Element | Treatment | Meaning |
| --- | --- | --- |
| Selected recorded pass | solid white arrow | observed event geometry |
| Candidate option | dashed amber arrow | model-estimated alternative |
| Pass actor | blue marker | observed event player location |
| Visible teammate point | green marker | anonymous observed 360 actor |
| Visible opponent point | coral marker | anonymous observed 360 actor |
| Visible area | pale translucent mask | camera/data coverage only |

Use the color values in `configs/visual.yml`, DejaVu Sans (available in CI), at least 10 pt labels, and 16:9 exports at 1600×900. Every scene has a readable source line containing competition, match ID, event UUID, source commit, and renderer version. Every modeled layer says “model estimate.”

Mobile/portrait exports preserve pitch margins and put provenance below the pitch. Lines must use solid/dashed patterns as well as color.

