from datetime import timezone, tzinfo

from apscheduler.triggers.cron import CronTrigger

DAILY_SUMMARY_HOUR = 9
DAILY_REMINDER_HOUR = 21
SCAN_INTERVAL_MINUTES = 5


def daily_summary_trigger(tz: tzinfo) -> CronTrigger:
    return CronTrigger(hour=DAILY_SUMMARY_HOUR, minute=0, second=0, timezone=tz)


def daily_reminder_trigger(tz: tzinfo) -> CronTrigger:
    return CronTrigger(hour=DAILY_REMINDER_HOUR, minute=0, second=0, timezone=tz)


def scan_unseen_messages_trigger() -> CronTrigger:
    # The scan only cares about elapsed time, not the wall clock, so it runs in UTC. That keeps it out of the
    # repeated hour when the clocks go back, which is where the scheduler hung in ZOO-49.
    return CronTrigger(minute=f"*/{SCAN_INTERVAL_MINUTES}", timezone=timezone.utc)
