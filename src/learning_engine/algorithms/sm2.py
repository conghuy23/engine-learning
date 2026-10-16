from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class SchedulingState:
    ease_factor: float = 2.5
    interval: int = 0
    repetitions: int = 0


@dataclass(frozen=True)
class ScheduleResult:
    ease_factor: float
    interval: int
    repetitions: int
    due_at: datetime


def schedule(
    state: SchedulingState,
    quality: int,
    *,
    now: datetime | None = None,
) -> ScheduleResult:
    """SM-2. quality: 0=blackout ... 5=perfect. <3 = lapse."""
    if not 0 <= quality <= 5:
        raise ValueError("quality must be 0..5")

    now = now or datetime.now(timezone.utc)
    ef, reps, interval = state.ease_factor, state.repetitions, state.interval

    if quality < 3:
        reps = 0
        interval = 1
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = max(1, round(interval * ef))
        reps += 1

    ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ef = max(1.3, ef)

    return ScheduleResult(
        ease_factor=round(ef, 4),
        interval=interval,
        repetitions=reps,
        due_at=now + timedelta(days=interval),
    )