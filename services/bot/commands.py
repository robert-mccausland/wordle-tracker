from datetime import date
import enum
import logging
import discord

from django.db.models import Count, Avg, Min, Q
from apps.core.models import WordleGame
from services.bot.scanner import scan_messages_for_channel

logger = logging.getLogger(__name__)

SUMMARY_LIMIT_DEFAULT = 5
SUMMARY_DELETE_AFTER = 60
DEFAULT_RANKING = ["-games", "-wins", "average", "best"]
WORDLE_EPOCH = date(2021, 6, 19)


class Admin(discord.app_commands.Group):

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


class Ranking(enum.Enum):
    GAMES = "games"
    WINS = "wins"
    AVERAGE = "average"
    BEST = "best"


RANKING_FIELD_MAP = {
    Ranking.BEST: "best",
    Ranking.WINS: "-wins",
    Ranking.AVERAGE: "average",
    Ranking.GAMES: "-games",
}


@discord.app_commands.command(
    name="wordle-summary", description="Make a summary of wordle games posted in current channel"
)
@discord.app_commands.describe(days="Number of days to limit the summary to")
@discord.app_commands.describe(limit="Number of autists to include")
@discord.app_commands.describe(ranking="How to rank the autists")
async def summary(
    interaction: discord.Interaction,
    days: int | None,
    ranking: Ranking | None,
    limit: int = SUMMARY_LIMIT_DEFAULT,
) -> None:
    if interaction.channel is None or interaction.guild is None:
        return

    min_wordle_game_number = None
    if days is not None:
        min_wordle_game_number = _wordle_number_for_day(date.today()) - days

    games = WordleGame.objects.filter(channel_id=interaction.channel.id, is_duplicate=False).values("user_id")

    if min_wordle_game_number is not None:
        games = games.filter(game_number__gt=min_wordle_game_number)

    order = DEFAULT_RANKING
    if ranking is not None:
        ranking_field = RANKING_FIELD_MAP[ranking]
        order = [ranking_field] + [x for x in order if x != ranking_field]

    summary = games.annotate(
        games=Count("message_id"),
        wins=Count("message_id", filter=Q(is_win=True)),
        average=Avg("guesses"),
        best=Min("guesses"),
    ).order_by(*order)[:limit]

    rank = 1

    title = "🏆 Top Autists 🏆"

    if days is not None:
        title += f" | last {days} days"

    if ranking is not None:
        title += f" | ranked by {ranking.value}"

    response = discord.Embed(title=title, color=0x00FF00)
    async for row in summary.aiterator():
        username: str
        try:
            user = await interaction.guild.fetch_member(row["user_id"])
            username = user.display_name
        except discord.NotFound:
            username = "Unknown User"

        row_summary = (
            f"Wins: {row['wins']}, "
            f"Games: {row['games']}, "
            f"Best: {row['best']}, "
            f"Average: {row['average']:.1f}"
        )

        response.add_field(
            name=f"{rank}. {username}",
            value=row_summary,
            inline=False,
        )

        response.set_author(name="Wordle Tracker")

        rank += 1

    await interaction.response.send_message(embed=response, delete_after=SUMMARY_DELETE_AFTER)


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


def _wordle_number_for_day(day: date) -> int:
    return (day - WORDLE_EPOCH).days
