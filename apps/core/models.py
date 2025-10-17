from django.db import models


class WordleChannel(models.Model):
    channel_id = models.BigIntegerField(primary_key=True)
    guild_id = models.BigIntegerField(null=True)
    last_seen_message = models.BigIntegerField(null=True)
    daily_summary_enabled = models.BooleanField()


class WordleGame(models.Model):
    message_id = models.BigIntegerField(primary_key=True)
    channel = models.ForeignKey(WordleChannel, on_delete=models.CASCADE)
    guild_id = (models.BigIntegerField(null=True),)
    user_id = models.BigIntegerField()
    posted_at = models.DateTimeField()
    scanned_at = models.DateTimeField()
    game_number = models.IntegerField()
    is_win = models.BooleanField()
    is_hard_mode = models.BooleanField()
    guesses = models.IntegerField()
    is_duplicate = models.BooleanField()
    result = models.JSONField(default=list)
