# File to track known bugs

### Scheduler issues during DST offset change period

On 1am - 2am (UTC) on the day the clocks went backwards in the London Timezone there was lots of warnings from the scheduler and the container OOMed itself. Unsure if this is a bug in my code or the scheduler itself has a bug / is misconfigured.

**Fixed (ZOO-50):** this was an APScheduler bug ([agronholm/apscheduler#1021](https://github.com/agronholm/apscheduler/issues/1021)). In 3.11.0 a `CronTrigger` in a DST timezone could loop forever in the repeated hour when the clocks go back. It is fixed in 3.11.2; we now pin 3.11.3 and run the five-minute scan job in UTC. `tests/bot/test_triggers.py` covers both DST transitions.

### Games delete from channel are not removed

I had to comment out the logic that handled this as it kept deleting games that still existed. Not sure if this is a bug in my code or some misunderstanding of how the discord client give me historic messages.
