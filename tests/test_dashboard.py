from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_decision_room_loads_real_precomputed_data():
    app = AppTest.from_file(Path(__file__).parents[1] / "app" / "Home.py")

    app.run(timeout=60)

    assert not app.exception
    assert app.title[0].value == "PassIQ Decision Room"
