from datetime import date, timedelta
import enum
import logging
import discord

from services.bot.config import SUMMARY_LIMIT_DEFAULT
from services.bot.scanner import scan_messages_for_channel
from services.bot.summarizer import Ranking, Summarizer

logger = logging.getLogger(__name__)


class ResponseType(enum.Enum):
    Whisper = "Whisper"
    Post = "Post"


class Admin(discord.app_commands.Group):
    def __init__(self) -> None:
        super().__init__(name="admin", description="Setup and debugging commands")

    @discord.app_commands.command(name="rescan", description="Rescans all the messages in current channel")
    async def rescan(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.channel, discord.TextChannel) or interaction.guild is None:
            return

        await interaction.response.defer(ephemeral=True)

        try:
            await scan_messages_for_channel(interaction.channel, None)
            await interaction.edit_original_response(content="Rescanning finished!")
        except Exception as e:
            await interaction.edit_original_response(content="Something went wrong :(")
            logger.error("Error rescanning messages: %s", e, exc_info=e)


@discord.app_commands.command(name="wordle-summary", description="Summary of wordle games posted in current channel")
@discord.app_commands.describe(days="Number of days to limit the summary to")
@discord.app_commands.describe(limit="Max number of autists to include")
@discord.app_commands.describe(ranking="How to rank the autists")
@discord.app_commands.describe(response="Which format to respond to the request in")
async def summary(
    interaction: discord.Interaction,
    days: int | None,
    ranking: Ranking | None,
    limit: int = SUMMARY_LIMIT_DEFAULT,
    response: ResponseType = ResponseType.Whisper,
) -> None:
    if interaction.guild is None:
        return

    if not isinstance(interaction.channel, discord.TextChannel):
        return

    summarizer = Summarizer(interaction.guild, interaction.channel)
    embed = await summarizer.get_summary(limit, date.today(), ranking, days)
    await interaction.response.send_message(
        embed=embed, ephemeral=response == ResponseType.Whisper, silent=response == ResponseType.Post
    )


@discord.app_commands.command(name="wordle-results", description="Results of yesterdays wordle game")
@discord.app_commands.describe(response="Which format to respond to the request in")
async def daily_summary(
    interaction: discord.Interaction,
    response: ResponseType = ResponseType.Whisper,
) -> None:
    if interaction.guild is None:
        return

    if not isinstance(interaction.channel, discord.TextChannel):
        return

    summarizer = Summarizer(interaction.guild, interaction.channel)
    yesterday = date.today() - timedelta(days=1)
    embed = await summarizer.get_daily_results(yesterday)
    await interaction.response.send_message(
        embed=embed, ephemeral=response == ResponseType.Whisper, silent=response == ResponseType.Post
    )


@discord.app_commands.command(name="sodium", description="SODIUM")
async def sodium(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        return

    sounds = await interaction.guild.fetch_soundboard_sounds()
    sodium_sound = next((sound for sound in sounds if sound.name == "SODIUM"), None)
    if sodium_sound is None:
        await interaction.response.send_message("Sodium not found :(")
        return

    await interaction.response.send_message("SODIUM!")

    try:
        for channel in interaction.guild.voice_channels:
            client: discord.VoiceClient = await channel.connect()
            try:
                await channel.send_sound(sodium_sound)
            finally:
                await client.disconnect()
    except Exception as e:
        logger.error("Failed to send sodium sound: %s", e, exc_info=e)
