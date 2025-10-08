from django.db import models


class WordleChannel(models.Model):
    channel_id = models.BigIntegerField(primary_key=True)
    last_seen_message = models.BigIntegerField()


class WordleGame(models.Model):
    message_id = models.BigIntegerField(primary_key=True)
    user_id = models.BigIntegerField()
    guild_id = models.BigIntegerField()
    channel_id = models.BigIntegerField()
    timestamp = models.DateTimeField()
    game_number = models.IntegerField()
    is_win = models.BooleanField()
    is_hard_mode = models.BooleanField()
    guesses = models.IntegerField()
    result = models.JSONField(default=list)
