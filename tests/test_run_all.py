import importlib

from schneider_forecast import run_all


def test_steps_run_in_dependency_order():
    assert run_all.STEPS[0] == "data"
    assert run_all.STEPS[-1] == "submit"
    assert run_all.STEPS.index("pricing") > run_all.STEPS.index("p3_selection")


def test_every_step_has_a_main():
    for step in run_all.STEPS:
        assert callable(importlib.import_module(f"schneider_forecast.{step}").main)


def test_missing_raw_files_are_listed(tmp_path):
    present = tmp_path / "here.csv"
    present.write_text("x")
    absent = tmp_path / "gone.csv"
    assert run_all.missing_raw_files((present, absent)) == [absent]
