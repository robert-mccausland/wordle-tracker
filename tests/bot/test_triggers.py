"""Regression tests for ZOO-49 / ZOO-50.

At 00:55 UTC on 2026-10-25 (01:55 BST, five minutes before the clocks went back) APScheduler 3.11.0 got stuck in
``Job._get_run_times`` working out the next run of the five-minute scan job: ``CronTrigger`` kept handing back fire
times inside the repeated 01:00-02:00 hour that were never later than ``now``, so the loop never ended and the list of
run times grew until the VM ran out of memory. These tests drive the triggers the way the scheduler does across both
Europe/London DST transitions, with hard bounds so a regression fails quickly instead of hanging CI.
"""

import threading
import unittest
from datetime import datetime, timedelta, timezone, tzinfo
from types import SimpleNamespace
from typing import Any, Callable, TypeVar
from zoneinfo import ZoneInfo

from apscheduler.job import Job
from apscheduler.triggers.cron import CronTrigger

from services.bot.triggers import (
    DAILY_REMINDER_HOUR,
    DAILY_SUMMARY_HOUR,
    SCAN_INTERVAL_MINUTES,
    daily_reminder_trigger,
    daily_summary_trigger,
    scan_unseen_messages_trigger,
)

LONDON = ZoneInfo("Europe/London")
UTC = timezone.utc

# Clocks go back at 02:00 BST (01:00 UTC); 01:00-02:00 local time happens twice.
FALL_BACK = datetime(2026, 10, 25, 1, 0, tzinfo=UTC)
# Clocks go forward at 01:00 GMT (01:00 UTC); 01:00-02:00 local time never happens.
SPRING_FORWARD = datetime(2027, 3, 28, 1, 0, tzinfo=UTC)

# Generous bounds: each scenario needs a few dozen trigger calls and finishes in milliseconds.
MAX_TRIGGER_CALLS = 1_000
TIMEOUT_SECONDS = 10.0

T = TypeVar("T")


class RunawayTrigger(AssertionError):
    pass


class CountingTrigger:
    """Wraps a trigger and fails once it has been asked for too many fire times."""

    def __init__(self, trigger: CronTrigger) -> None:
        self.trigger = trigger
        self.calls = 0

    def get_next_fire_time(self, previous_fire_time: datetime | None, now: datetime) -> datetime | None:
        self.calls += 1
        if self.calls > MAX_TRIGGER_CALLS:
            raise RunawayTrigger(f"trigger called more than {MAX_TRIGGER_CALLS} times (last: {previous_fire_time})")
        result: datetime | None = self.trigger.get_next_fire_time(previous_fire_time, now)
        return result


def run_with_timeout(fn: Callable[[], T]) -> T:
    """Runs fn in a daemon thread so a hang inside a single trigger call fails the test instead of CI."""
    outcome: dict[str, Any] = {}

    def target() -> None:
        try:
            outcome["result"] = fn()
        except BaseException as ex:
            outcome["error"] = ex

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(TIMEOUT_SECONDS)
    if thread.is_alive():
        raise AssertionError(f"scheduler computation did not finish within {TIMEOUT_SECONDS}s")
    if "error" in outcome:
        raise outcome["error"]
    result: T = outcome["result"]
    return result


def simulate_scheduler(
    trigger: CronTrigger, scheduler_tz: tzinfo, start: datetime, end: datetime, tick: timedelta
) -> list[datetime]:
    """Replays BaseScheduler._process_jobs: wake every `tick`, collect due run times, then schedule the next one.

    Returns the UTC fire times between start and end (inclusive). The clock runs one tick past end so a run due at end
    is picked up even when the ticks don't land on it exactly.
    """
    counting = CountingTrigger(trigger)
    job = SimpleNamespace(
        trigger=counting, next_run_time=counting.get_next_fire_time(None, start.astimezone(scheduler_tz))
    )
    fired: list[datetime] = []
    now_utc = start
    while now_utc < end + tick:
        now = now_utc.astimezone(scheduler_tz)
        if job.next_run_time is not None and job.next_run_time.astimezone(UTC) <= now_utc:
            # Called unbound with a stand-in job: this is the loop that never terminated in ZOO-49.
            run_times = Job._get_run_times(job, now)
            if not run_times:
                raise AssertionError(f"job was due at {job.next_run_time} but _get_run_times returned nothing")
            fired.extend(rt.astimezone(UTC) for rt in run_times)
            job.next_run_time = counting.get_next_fire_time(run_times[-1], now)
        now_utc += tick
    return [ft for ft in fired if ft <= end]


def walk_fire_times(trigger: CronTrigger, start: datetime, count: int) -> list[datetime]:
    """Asks the trigger for `count` consecutive fire times, the way the scheduler advances a job after each run."""
    counting = CountingTrigger(trigger)
    fire_times: list[datetime] = []
    previous: datetime | None = None
    now = start.astimezone(LONDON)
    for _ in range(count):
        next_fire = counting.get_next_fire_time(previous, now)
        assert next_fire is not None
        fire_times.append(next_fire)
        previous = next_fire
        now = next_fire.astimezone(LONDON)
    return fire_times


class TestScanTriggerAcrossDst(unittest.TestCase):
    def assert_every_interval(self, fired: list[datetime], start: datetime, end: datetime) -> None:
        interval = timedelta(minutes=SCAN_INTERVAL_MINUTES)
        expected = []
        t = start
        while t <= end:
            expected.append(t)
            t += interval
        self.assertEqual(fired, expected)

    def check_window(self, trigger: CronTrigger, start: datetime, end: datetime) -> None:
        for tick in (timedelta(seconds=1), timedelta(seconds=37), timedelta(minutes=1)):
            with self.subTest(tick=tick):
                fired = run_with_timeout(lambda: simulate_scheduler(trigger, LONDON, start, end, tick))
                self.assertTrue(all(a < b for a, b in zip(fired, fired[1:])), fired)
                self.assert_every_interval(fired, start, end)

    def test_fall_back_production_trigger(self) -> None:
        # 00:45-01:15 UTC covers 01:50 and 01:55 BST and the start of the repeated 01:00-02:00 GMT hour.
        self.check_window(
            scan_unseen_messages_trigger(), FALL_BACK - timedelta(minutes=15), FALL_BACK + timedelta(minutes=15)
        )

    def test_fall_back_whole_repeated_hour_production_trigger(self) -> None:
        self.check_window(
            scan_unseen_messages_trigger(), FALL_BACK - timedelta(hours=1), FALL_BACK + timedelta(hours=2)
        )

    def test_spring_forward_production_trigger(self) -> None:
        self.check_window(
            scan_unseen_messages_trigger(),
            SPRING_FORWARD - timedelta(minutes=15),
            SPRING_FORWARD + timedelta(minutes=15),
        )

    # The incident configuration: a */5 CronTrigger in Europe/London. Production no longer uses it, but it guards the
    # pinned APScheduler against the ZOO-49 bug coming back, since the daily jobs still use London cron triggers.
    def test_fall_back_london_trigger(self) -> None:
        trigger = CronTrigger(minute="*/5", timezone=LONDON)
        self.check_window(trigger, FALL_BACK - timedelta(minutes=15), FALL_BACK + timedelta(minutes=15))

    def test_fall_back_whole_repeated_hour_london_trigger(self) -> None:
        trigger = CronTrigger(minute="*/5", timezone=LONDON)
        self.check_window(trigger, FALL_BACK - timedelta(hours=1), FALL_BACK + timedelta(hours=2))

    def test_spring_forward_london_trigger(self) -> None:
        trigger = CronTrigger(minute="*/5", timezone=LONDON)
        self.check_window(trigger, SPRING_FORWARD - timedelta(minutes=15), SPRING_FORWARD + timedelta(minutes=15))

    def test_incident_moment_terminates(self) -> None:
        # The exact state at 00:55 UTC: the 01:55 BST run is due and the scheduler asks for the run times up to now.
        for trigger in (CronTrigger(minute="*/5", timezone=LONDON), scan_unseen_messages_trigger()):
            with self.subTest(trigger=str(trigger)):
                counting = CountingTrigger(trigger)
                due = datetime(2026, 10, 25, 0, 55, tzinfo=UTC).astimezone(LONDON)
                now = (due + timedelta(milliseconds=500)).astimezone(LONDON)
                job = SimpleNamespace(trigger=counting, next_run_time=due)
                run_times = run_with_timeout(lambda: Job._get_run_times(job, now))
                self.assertEqual([rt.astimezone(UTC) for rt in run_times], [due.astimezone(UTC)])
                next_run = counting.get_next_fire_time(run_times[-1], now)
                assert next_run is not None
                self.assertEqual(next_run.astimezone(UTC), datetime(2026, 10, 25, 1, 0, tzinfo=UTC))


class TestDailyTriggersAcrossDst(unittest.TestCase):
    def check_daily(self, trigger: CronTrigger, hour: int, transition: datetime) -> None:
        start = transition - timedelta(days=3)
        fire_times = run_with_timeout(lambda: walk_fire_times(trigger, start, 7))
        utc_times = [ft.astimezone(UTC) for ft in fire_times]
        self.assertTrue(all(a < b for a, b in zip(utc_times, utc_times[1:])), utc_times)
        local_times = [ft.astimezone(LONDON) for ft in fire_times]
        for local in local_times:
            self.assertEqual((local.hour, local.minute, local.second), (hour, 0, 0), local)
        dates = [local.date() for local in local_times]
        self.assertEqual(dates, [dates[0] + timedelta(days=i) for i in range(len(dates))])
        self.assertLess(dates[0], transition.date())
        self.assertGreater(dates[-1], transition.date())

    def test_daily_summary(self) -> None:
        for transition in (FALL_BACK, SPRING_FORWARD):
            with self.subTest(transition=transition):
                self.check_daily(daily_summary_trigger(LONDON), DAILY_SUMMARY_HOUR, transition)

    def test_daily_reminder(self) -> None:
        for transition in (FALL_BACK, SPRING_FORWARD):
            with self.subTest(transition=transition):
                self.check_daily(daily_reminder_trigger(LONDON), DAILY_REMINDER_HOUR, transition)
