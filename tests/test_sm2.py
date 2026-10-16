from datetime import datetime, timezone

from learning_engine.algorithms.sm2 import SchedulingState, schedule

NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)


def test_first_good_review():
    r = schedule(SchedulingState(), 4, now=NOW)
    assert r.interval == 1 and r.repetitions == 1


def test_second_good_review():
    r = schedule(SchedulingState(interval=1, repetitions=1), 4, now=NOW)
    assert r.interval == 6 and r.repetitions == 2


def test_lapse_resets():
    r = schedule(SchedulingState(ease_factor=2.5, interval=20, repetitions=5), 1, now=NOW)
    assert r.repetitions == 0 and r.interval == 1


def test_ease_factor_floor():
    r = schedule(SchedulingState(ease_factor=1.3, interval=10, repetitions=3), 0, now=NOW)
    assert r.ease_factor == 1.3