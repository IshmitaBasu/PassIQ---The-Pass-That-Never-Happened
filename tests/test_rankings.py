import pandas as pd

from passiq.scoring.rankings import _frontier, _utilities


def test_frontier_marks_only_non_dominated_options():
    candidates = pd.DataFrame({"p_success": [0.8, 0.7, 0.9], "xt_delta": [0.2, 0.1, 0.1]})

    assert _frontier(candidates).tolist() == [True, False, True]


def test_utilities_reward_positive_threat_and_penalize_negative_threat():
    candidates = pd.DataFrame({"p_success": [0.8, 0.8], "xt_delta": [0.2, -0.2]})
    config = {"utilities": {"safety_adjusted": {"positive_xt_multiplier": 3.0, "negative_xt_penalty": 0.1}}}

    scored = _utilities(candidates, config)

    assert scored.loc[0, "utility_high_threat"] > scored.loc[1, "utility_high_threat"]
    assert scored.loc[0, "utility_safety_adjusted"] > scored.loc[1, "utility_safety_adjusted"]
