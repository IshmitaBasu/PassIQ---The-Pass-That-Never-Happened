from passiq.visuals.animations import clip_phase


def test_decision_clip_has_all_required_storyboard_phases():
    phases = {clip_phase(frame) for frame in range(12 * 12)}

    assert phases == {"source", "recorded_pass", "alternatives", "comparison", "limitations"}
