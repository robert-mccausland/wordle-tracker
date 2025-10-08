import logging
import discord
from django.db.models import Count, Avg, Min, Q

from apps.core.models import WordleGame

logger = logging.getLogger(__name__)

MAX_SUMMARY_LENGTH = 5


async def summary(interaction: discord.Interaction) -> None:
    if interaction.channel is None or interaction.guild is None:
        return

    summary = (
        WordleGame.objects.values("user_id")
        .annotate(
            total_games=Count("message_id"),
            wins=Count("message_id", filter=Q(is_win=True)),
            average_guesses=Avg("guesses"),
            best=Min("guesses"),
        )
        .order_by("-total_games")[:MAX_SUMMARY_LENGTH]
    )

    rank = 1
    response = discord.Embed(title="🏆 Top Wordlers 🏆", color=0x00FF00)
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

    await interaction.response.send_message(embed=response)
