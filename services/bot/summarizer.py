from datetime import date
import discord
from django.db.models import Count, Avg, Min, Q, Max
from apps.core.models import WordleGame
import enum

from services.bot.config import USERNAME_MAX_LENGTH
from services.bot.utils import game_number_for_day

REMINDER_MAX_DAYS = 3
DEFAULT_RANKING = ["-wins", "-games", "average", "best"]
RANK_EMOJIS = {1: "🥇", 2: "🥈", 3: "🥉"}


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


class SummarizerError(Exception):
    pass


class Summarizer:
    def __init__(self, channel: discord.TextChannel) -> None:
        self.channel = channel

    async def get_summary(
        self,
        limit: int,
        end: date,
        ranking: Ranking,
        days: int | None,
    ) -> discord.Embed:

        max_game_number = game_number_for_day(end) or 0
        games = WordleGame.objects.filter(
            channel_id=self.channel.id,
            is_duplicate=False,
            is_correct_day=True,
            game_number__lt=max_game_number,
        )

        if days is not None:
            min_game_number = max_game_number - days
            games = games.filter(game_number__gte=min_game_number)

        order = DEFAULT_RANKING
        ranking_field = RANKING_FIELD_MAP[ranking]
        order = [ranking_field] + [x for x in order if x != ranking_field]

        data = (
            games.values("user_id")
            .annotate(
                games=Count("message_id"),
                wins=Count("message_id", filter=Q(is_win=True)),
                average=Avg("guesses"),
                best=Min("guesses"),
            )
            .order_by(*order)[:limit]
        )

        rank = 1
        title = "🏆 Top Autists 🏆"
        if days is not None:
            title += f" | last {days} days"

        if ranking is not None:
            title += f" | ranked by {ranking.value}"

        summary = discord.Embed(title=title, color=0x00FF00)
        async for row in data.aiterator():
            display_name = await self._get_display_name(row["user_id"])
            rank_symbol = _get_rank_symbol(rank)
            row_summary = (
                f"Wins:** {row['wins']}/{row['games']}** | Avg:**  {row['average']:.1f}** | Best:** {row['best']}**"
            )

            summary.add_field(
                name=f"\u200b\n{rank_symbol} {display_name}",
                value=row_summary,
                inline=False,
            )

            rank += 1

        if len(summary.fields) == 0:
            summary.add_field(name="\u200b\n", value="No games found in the current channel 😥")

        return summary

    async def get_daily_results(self, game_number: int) -> discord.Embed:
        rank = 1
        title = f"🏆 Game {game_number} Results 🏆"
        results = discord.Embed(title=title, color=0x00FF00)
        games = WordleGame.objects.filter(
            channel_id=self.channel.id,
            is_duplicate=False,
            is_correct_day=True,
            game_number=game_number,
        ).order_by("guesses", "-is_win", "posted_at")

        async for row in games.aiterator():
            display_name = await self._get_display_name(row.user_id)
            rank_symbol = _get_rank_symbol(rank)

            guesses = str(row.guesses)
            if not row.is_win:
                guesses = "X"

            row_summary = f"Guesses: {guesses}"

            results.add_field(
                name=f"\u200b\n{rank_symbol} {display_name}",
                value=row_summary,
                inline=False,
            )

            rank += 1

        if len(results.fields) == 0:
            results.add_field(name="\u200b\n", value="No games found in the current channel 😥")

        return results

    async def get_daily_reminder(self, game_number: int) -> discord.Embed | None:

        last_played = (
            WordleGame.objects.filter(
                channel_id=self.channel.id,
                is_duplicate=False,
                is_correct_day=True,
                game_number__gte=game_number - REMINDER_MAX_DAYS,
                game_number__lte=game_number,
            )
            .values("user_id")
            .annotate(last_played=Max("game_number"))
            .aiterator()
        )

        title = "⏰ Reminder ⏰\n\u200b\nSome regulars have not played a game today!"
        reminder = discord.Embed(title=title, color=0xFFFF00)
        async for row in last_played:
            days_missing = game_number - row["last_played"]
            if days_missing > 0:
                user_id = row["user_id"]
                display_name = await self._get_display_name(user_id)
                days_display = f"{days_missing} " + ("day" if days_missing == 1 else "days")
                row_summary = f"<@{user_id}> last played {days_display} ago"
                reminder.add_field(
                    name=f"\u200b\n{display_name}",
                    value=row_summary,
                    inline=False,
                )

        if len(reminder.fields) == 0:
            return None

        return reminder

    async def _get_display_name(self, user_id: int) -> str:
        display_name: str
        try:
            user = await self.channel.guild.fetch_member(user_id)
            display_name = (
                (user.display_name[: USERNAME_MAX_LENGTH - 1] + "…")
                if len(user.display_name) > USERNAME_MAX_LENGTH
                else user.display_name
            )
        except discord.NotFound:
            display_name = "Unknown User"

        return display_name


def _get_rank_symbol(rank: int) -> str:
    return RANK_EMOJIS.get(rank, f"{rank}.")
