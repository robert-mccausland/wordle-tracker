import logging
import discord

from django.db.models import Count, Avg, Min, Q
from apps.core.models import WordleGame
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MAX_SUMMARY_LENGTH = 5
SUMMARY_DELETE_AFTER = 60


@dataclass
class SummaryArguments:
    last_games: int | None


async def summary(interaction: discord.Interaction, arguments: SummaryArguments) -> None:
    if interaction.channel is None or interaction.guild is None:
        return

    summary = (
        WordleGame.objects.values("user_id")
        .filter(guild_id=interaction.guild.id)
        .annotate(
            total_games=Count("message_id"),
            wins=Count("message_id", filter=Q(is_win=True)),
            average_guesses=Avg("guesses"),
            best=Min("guesses"),
        )
        .order_by("-total_games", "-wins")[:MAX_SUMMARY_LENGTH]
    )

    rank = 1
    response = discord.Embed(title="🏆 Top Autists 🏆", color=0x00FF00)
    async for row in summary.aiterator():
        username: str
        try:
            user = await interaction.guild.fetch_member(row["user_id"])
            username = user.display_name
        except discord.NotFound:
            username = "Unknown User"

        row_summary = (
            f"Wins: {row['wins']}, "
            f"Games: {row['total_games']}, "
            f"Best: {row['best']}, "
            f"Average: {row['average_guesses']:.1f}"
        )

        response.add_field(
            name=f"{rank}. {username}",
            value=row_summary,
            inline=False,
        )
        rank += 1

    await interaction.response.send_message(embed=response, delete_after=SUMMARY_DELETE_AFTER)


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
