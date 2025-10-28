# File to track known bugs

### Scheduler issues during DST offset change period

On 1am - 2am (UTC) on the day the clocks went backwards in the London Timezone there was lots of warnings from the scheduler and the container OOMed itself. Unsure if this is a bug in my code or the scheduler itself has a bug / is misconfigured.

### Games delete from channel are not removed

I had to comment out the logic that handled this as it kept deleting games that still existed. Not sure if this is a bug in my code or some misunderstanding of how the discord client give me historic messages.
