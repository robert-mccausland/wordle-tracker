import asyncio
import logging
import discord

from apps.core.models import WordleChannel, WordleGame
from services.bot.parser import LetterGuess, parse_message

logger = logging.getLogger(__name__)

CHANNEL_NAME = "wordle"


async def scan_unseen_messages(client: discord.Client) -> None:
    logger.info("Scanning previous messages")
    try:
        guilds = [guild async for guild in client.fetch_guilds()]
        results = await asyncio.gather(
            *[_scan_unseen_messages_for_guild(guild) for guild in guilds], return_exceptions=True
        )

        for result in results:
            if result is None:
                continue
            logger.error("Error while scanning messages for guild: %s", result, exc_info=result)

    except Exception as e:
        logger.error("Error scanning previous messages: %s", e, exc_info=e)


async def _scan_unseen_messages_for_guild(guild: discord.Guild) -> None:
    channels = await guild.fetch_channels()
    for channel in channels:
        if channel.name != CHANNEL_NAME:
            continue

        if not isinstance(channel, discord.TextChannel):
            continue

        last_seen = None
        wordle_channel = await WordleChannel.objects.filter(channel_id=channel.id).afirst()
        if wordle_channel is not None:
            last_seen = discord.Object(id=wordle_channel.last_seen_message)

        await scan_messages_for_channel(channel, last_seen)


async def scan_messages_for_channel(channel: discord.TextChannel, from_message_id: discord.Object | None) -> None:
    new_last_seen = None
    try:
        async for message in channel.history(after=from_message_id, oldest_first=True):
            await save_message(message)
            new_last_seen = message
    finally:
        if new_last_seen is not None:
            await _update_last_seen_message(new_last_seen)


def _map_guess(guess: list[LetterGuess]) -> int:
    result = 0
    multiplier = 1
    for letter in guess:
        result += letter.value * multiplier
        multiplier *= 3

    return result


async def save_message(message: discord.Message) -> None:
    assert message.guild is not None, "Expected message to be in a guild channel"

    result = parse_message(message.content)

    if result is None:
        return

    await WordleGame.objects.aget_or_create(
        message_id=message.id,
        defaults=dict(
            user_id=message.author.id,
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            timestamp=message.created_at,
            game_number=result.game_number,
            is_win=result.is_win,
            is_hard_mode=result.is_hard_mode,
            guesses=len(result.guesses),
            result=[_map_guess(g) for g in result.guesses],
        ),
    )


async def _update_last_seen_message(message: discord.Message) -> None:
    channel, created = await WordleChannel.objects.aget_or_create(
        channel_id=message.channel.id, defaults={"last_seen_message": message.id}
    )

    if not created:
        await WordleChannel.objects.filter(channel_id=channel.channel_id, last_seen_message__lt=message.id).aupdate(
            last_seen_message=message.id
        )
