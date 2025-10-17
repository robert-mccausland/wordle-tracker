from datetime import date, timedelta
import enum
import logging
import discord
from django.db import IntegrityError

from apps.core.models import WordleChannel
from services.bot.config import SUMMARY_LIMIT_DEFAULT
from services.bot.scanner import scan_messages_for_channel
from services.bot.summarizer import Ranking, Summarizer

logger = logging.getLogger(__name__)

CHANNEL_ADDED_SUCCESS = "Wordle Tracker has been added to this channel"
CHANNEL_REMOVED_SUCCESS = "Wordle Tracker has been removed from this channel. "
INVALID_CHANNEL_TYPE = "Wordle Tracker can not be added to this type of channel"
CHANNEL_ALREADY_ADDED = "Wordle Tracker has already been added to this channel"
CHANNEL_NOT_ADDED = (
    "Wordle Tracker has not yet been added to this channel. "
    "Run the `/admin add` command to add the bot to this channel"
)
GENERIC_ERROR = "Oopsie woopsie! Something went wrong while processing your command (*^ω^*)~"


class ResponseType(enum.Enum):
    Whisper = "Whisper"
    Post = "Post"


class Admin(discord.app_commands.Group):
    def __init__(self) -> None:
        super().__init__(name="admin", description="Setup and debugging commands")

    @discord.app_commands.command(name="add", description="Add current channel to the Wordle Tracker")
    async def add(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.channel, discord.TextChannel) or interaction.guild is None:
            await interaction.response.send_message(content=INVALID_CHANNEL_TYPE, ephemeral=True)
            return

        try:
            await WordleChannel.objects.acreate(
                channel_id=interaction.channel.id,
                guild_id=interaction.channel.guild.id,
                daily_summary_enabled=True,
            )
        except IntegrityError:
            await interaction.response.send_message(content=CHANNEL_ALREADY_ADDED, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        content = GENERIC_ERROR
        try:
            await scan_messages_for_channel(interaction.channel, None)
            content = CHANNEL_ADDED_SUCCESS
        finally:
            await interaction.edit_original_response(content=content)

    @discord.app_commands.command(name="info", description="Show current channel info")
    async def info(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.channel, discord.TextChannel) or interaction.guild is None:
            await interaction.response.send_message(content=GENERIC_ERROR, ephemeral=True)
            return

        try:
            channel = await WordleChannel.objects.filter(channel_id=interaction.channel.id).afirst()
            if channel is None:
                content = CHANNEL_NOT_ADDED
            else:
                content = (
                    "Wordle Tracker has been added to this channel!\n"
                    f"Daily Summary Enabled: {channel.daily_summary_enabled}\n"
                )
            await interaction.response.send_message(content=content, ephemeral=True)
        except Exception as ex:
            await interaction.response.send_message(content=GENERIC_ERROR, ephemeral=True)
            logger.error("Error getting channel info: %s", ex, exc_info=ex)

    @discord.app_commands.command(name="remove", description="Remove current channel from the Wordle Tracker")
    async def remove(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.channel, discord.TextChannel) or interaction.guild is None:
            await interaction.response.send_message(content=INVALID_CHANNEL_TYPE, ephemeral=True)
            return

        deleted_count, _ = await WordleChannel.objects.filter(channel_id=interaction.channel.id).adelete()

        if deleted_count == 0:
            await interaction.response.send_message(content=CHANNEL_NOT_ADDED, ephemeral=True)
        else:
            await interaction.response.send_message(content=CHANNEL_REMOVED_SUCCESS, ephemeral=True)

    @discord.app_commands.command(name="rescan", description="Rescan all the messages in current channel")
    async def rescan(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.channel, discord.TextChannel) or interaction.guild is None:
            await interaction.response.send_message(content=GENERIC_ERROR, ephemeral=True)
            return

        if not await WordleChannel.objects.filter(channel_id=interaction.channel.id).aexists():
            await interaction.response.send_message(content=CHANNEL_NOT_ADDED, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            await scan_messages_for_channel(interaction.channel, None)
            await interaction.edit_original_response(content="Rescanning finished!")
        except Exception as ex:
            await interaction.edit_original_response(content=GENERIC_ERROR)
            logger.error("Error rescanning messages: %s", ex, exc_info=ex)


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
    if not isinstance(interaction.channel, discord.TextChannel) or interaction.guild is None:
        await interaction.response.send_message(content=GENERIC_ERROR, ephemeral=True)
        return

    if not await WordleChannel.objects.filter(channel_id=interaction.channel.id).aexists():
        await interaction.response.send_message(content=CHANNEL_NOT_ADDED, ephemeral=True)
        return

    summarizer = Summarizer(interaction.channel)
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
    if not isinstance(interaction.channel, discord.TextChannel) or interaction.guild is None:
        await interaction.response.send_message(content=GENERIC_ERROR, ephemeral=True)
        return

    if not await WordleChannel.objects.filter(channel_id=interaction.channel.id).aexists():
        await interaction.response.send_message(content=CHANNEL_NOT_ADDED, ephemeral=True)
        return

    summarizer = Summarizer(interaction.channel)
    yesterday = date.today() - timedelta(days=1)
    embed = await summarizer.get_daily_results(yesterday)
    await interaction.response.send_message(
        embed=embed, ephemeral=response == ResponseType.Whisper, silent=response == ResponseType.Post
    )
