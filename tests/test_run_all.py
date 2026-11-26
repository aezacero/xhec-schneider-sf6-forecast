import importlib

from schneider_forecast import run_all


def test_steps_run_in_dependency_order():
    assert run_all.STEPS[0] == "data"
    assert run_all.STEPS[-1] == "submit"
    assert run_all.STEPS.index("pricing") > run_all.STEPS.index("p3_selection")


def test_every_step_has_a_main():
    for step in run_all.STEPS:
        assert callable(importlib.import_module(f"schneider_forecast.{step}").main)
