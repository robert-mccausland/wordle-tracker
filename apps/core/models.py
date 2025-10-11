from django.db import models


class WordleChannel(models.Model):
    channel_id = models.BigIntegerField(primary_key=True)
    last_seen_message = models.BigIntegerField()


class WordleGame(models.Model):
    message_id = models.BigIntegerField(primary_key=True)
    user_id = models.BigIntegerField()
    guild_id = models.BigIntegerField()
    channel_id = models.BigIntegerField()
    posted_at = models.DateTimeField()
    scanned_at = models.DateTimeField()
    game_number = models.IntegerField()
    is_win = models.BooleanField()
    is_hard_mode = models.BooleanField()
    guesses = models.IntegerField()
    is_duplicate = models.BooleanField()
    result = models.JSONField(default=list)
