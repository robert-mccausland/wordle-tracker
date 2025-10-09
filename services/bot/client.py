import asyncio
import discord
import logging

from apps.core.models import WordleChannel, WordleGame
from services.bot.commands import SummaryArguments, sodium, summary
from services.bot.parser import LetterGuess, parse_message

logger = logging.getLogger(__name__)

CHANNEL_NAME = "wordle"
SCAN_MESSAGES_INTERVAL = 300


async def create_client() -> discord.Client:
    intents: discord.Intents = discord.Intents.default()
    intents.message_content = True

    logger.info("Starting Discord client...")
    client = discord.Client(intents=intents)
    tree = discord.app_commands.CommandTree(client)

    @client.event
    async def on_ready() -> None:
        await tree.sync()
        logger.info("Discord client is ready", extra={"user": client.user})
        asyncio.get_running_loop().create_task(_scan_previous_messages_task(client))

    @client.event
    async def on_message(message: discord.Message) -> None:
        if not isinstance(message.channel, discord.TextChannel):
            return

        if message.channel.name != CHANNEL_NAME:
            return

        await _save_message(message)

    @tree.command(name="wordle-summary", description="Make a summary of wordle games posted in current channel")
    @discord.app_commands.describe(last_games="last_games")
    async def summary_command(interaction: discord.Interaction, last_games: int | None) -> None:
        await summary(interaction, SummaryArguments(last_games=last_games))

    @tree.command(name="sodium")
    async def sodium_command(interaction: discord.Interaction) -> None:
        await sodium(interaction)

    return client


async def _scan_previous_messages_task(client: discord.Client) -> None:
    while True:
        await asyncio.gather(_scan_previous_messages(client), asyncio.sleep(SCAN_MESSAGES_INTERVAL))


async def _scan_previous_messages(client: discord.Client) -> None:
    logger.info("Scanning previous messages")
    try:
        guilds = [guild async for guild in client.fetch_guilds()]
        results = await asyncio.gather(
            *[_scan_previous_message_for_guild(guild) for guild in guilds], return_exceptions=True
        )

        for result in results:
            if result is None:
                continue
            logger.error("Error while scanning messages for guild: %s", result, exc_info=result)

    except Exception as e:
        logger.error("Error scanning previous messages: %s", e, exc_info=e)


async def _scan_previous_message_for_guild(guild: discord.Guild) -> None:
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

        new_last_seen = None
        try:
            async for message in channel.history(after=last_seen, oldest_first=True):
                await _save_message(message)
                new_last_seen = message
        finally:
            if new_last_seen is not None:
                await _update_last_seen_message(message)


def _map_guess(guess: list[LetterGuess]) -> int:
    result = 0
    multiplier = 1
    for letter in guess:
        result += letter.value * multiplier
        multiplier *= 3

    return result


async def _save_message(message: discord.Message) -> None:
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
