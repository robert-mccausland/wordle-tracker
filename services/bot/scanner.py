import asyncio
import logging
import discord

from apps.core.models import WordleChannel, WordleGame
from services.bot.config import CLIENT_WAIT_TIMEOUT
from services.bot.parser import LetterGuess, parse_message
from django.utils import timezone

logger = logging.getLogger(__name__)


class ScannerError(Exception):
    pass


async def scan_unseen_messages(client: discord.Client) -> None:
    await asyncio.wait_for(client.wait_until_ready(), timeout=CLIENT_WAIT_TIMEOUT)

    async def scan_channel(channel_id: int) -> None:
        try:
            channel = await client.fetch_channel(channel_id)
            if channel is None:
                raise ScannerError(f"Channel {channel_id} could not be found")
            if not isinstance(channel, discord.TextChannel):
                raise ScannerError(f"Expected channel {channel_id} to be a TextChannel, got {type(channel)}")

            await _scan_unseen_messages_for_channel(channel)
        except Exception as ex:
            logger.error(
                "Error while scanning messages for channel: %s",
                ex,
                exc_info=ex,
                extra={"channel_id": channel_id},
            )

    logger.info("Scanning previous messages")
    channels = WordleChannel.objects.values("channel_id").aiterator()
    await asyncio.gather(
        *[scan_channel(channel["channel_id"]) async for channel in channels],
    )


async def _scan_unseen_messages_for_channel(channel: discord.TextChannel) -> None:
    last_seen = None
    wordle_channel = await WordleChannel.objects.filter(channel_id=channel.id).afirst()
    if wordle_channel is not None and wordle_channel.last_seen_message is not None:
        last_seen = discord.Object(id=wordle_channel.last_seen_message)

    await scan_messages_for_channel(channel, last_seen)


async def scan_messages_for_channel(channel: discord.TextChannel, from_message_id: discord.Object | None) -> None:
    new_last_seen = None

    scan_started_at = timezone.now()
    try:
        async for message in channel.history(limit=None, after=from_message_id, oldest_first=True):
            await process_message(message)
            new_last_seen = message
    finally:
        if new_last_seen is not None:
            await _update_last_seen_message(new_last_seen)

    if new_last_seen is None:
        return

    # Remove games which we did not just scan and are in the interval
    filters = {
        "scanned_at__lt": scan_started_at,
        "message_id__lte": new_last_seen.id,
    }

    if from_message_id is not None:
        filters["message_id__gt"] = from_message_id.id

    deleted_count, _ = await WordleGame.objects.filter(**filters).adelete()
    if deleted_count > 0:
        logger.info(
            f"Deleted {deleted_count} games which are no longer in the channel", extra={"channel_id": channel.id}
        )


def _map_guess(guess: list[LetterGuess]) -> int:
    result = 0
    multiplier = 1
    for letter in guess:
        result += letter.value * multiplier
        multiplier *= 3

    return result


async def process_message(message: discord.Message) -> None:
    assert message.guild is not None, "Expected message to be in a guild channel"

    result = parse_message(message.content)

    if result is None:
        return

    is_duplicate = await WordleGame.objects.filter(
        game_number=result.game_number,
        user_id=message.author.id,
        channel_id=message.channel.id,
        message_id__lt=message.id,
    ).aexists()

    await WordleGame.objects.aupdate_or_create(
        message_id=message.id,
        defaults=dict(
            user_id=message.author.id,
            channel_id=message.channel.id,
            posted_at=message.created_at,
            scanned_at=timezone.now(),
            game_number=result.game_number,
            is_duplicate=is_duplicate,
            is_win=result.is_win,
            is_hard_mode=result.is_hard_mode,
            guesses=len(result.guesses),
            result=[_map_guess(g) for g in result.guesses],
        ),
    )


async def delete_message(message: discord.Message) -> None:
    await WordleGame.objects.filter(message_id=message.id).adelete()


async def _update_last_seen_message(message: discord.Message) -> None:
    channel, created = await WordleChannel.objects.aget_or_create(
        channel_id=message.channel.id, defaults={"last_seen_message": message.id}
    )

    if not created:
        await WordleChannel.objects.filter(channel_id=channel.channel_id, last_seen_message__lt=message.id).aupdate(
            last_seen_message=message.id
        )
