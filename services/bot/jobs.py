from asyncio import AbstractEventLoop
import asyncio
from datetime import date, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
import logging
import discord

from apps.core.models import WordleChannel
from services.bot.config import CLIENT_WAIT_TIMEOUT
from services.bot.scanner import scan_unseen_messages
from services.bot.summarizer import Summarizer
from wordletracker.settings import DB_PATH

logger = logging.getLogger(__name__)


class Services:
    def __init__(self, client: discord.Client) -> None:
        self.client = client


# Singleton to get around issues passing instance variable to cron jobs
services: Services | None = None


class JobScheduler:
    def __init__(self, event_loop: AbstractEventLoop, client: discord.Client) -> None:
        global services
        assert services is None, "JobScheduler must only be created once"
        services = Services(client)
        path = DB_PATH / "scheduler.sqlite"
        jobstores = {"default": SQLAlchemyJobStore(url=f"sqlite:///{path}")}
        self.scheduler = AsyncIOScheduler(jobstores=jobstores, event_loop=event_loop)
        self.scheduler.add_job(
            _daily_summary,
            CronTrigger(hour=9, minute=0, second=0, timezone="Europe/London"),
            id="daily_summary",
            replace_existing=True,
        )
        self.scheduler.add_job(
            _scan_unseen_messages,
            CronTrigger(minute="*/5", timezone="Europe/London"),
            id="scan_unseen_messages",
            replace_existing=True,
        )

    def start(self) -> None:
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown()


async def _scan_unseen_messages() -> None:
    assert services is not None, "Services must exist for jobs to run"
    await scan_unseen_messages(services.client)


async def _daily_summary() -> None:
    assert services is not None, "Services must exist for jobs to run"
    logger.info("Daily summary running")

    await asyncio.wait_for(services.client.wait_until_ready(), timeout=CLIENT_WAIT_TIMEOUT)
    yesterday = date.today() - timedelta(days=1)
    async for wordle_channel in WordleChannel.objects.aiterator():
        if not wordle_channel.daily_summary_enabled:
            continue

        channel = await services.client.fetch_channel(wordle_channel.channel_id)
        if not isinstance(channel, discord.TextChannel):
            continue

        try:
            summarizer = Summarizer(channel)
            results = await summarizer.get_daily_results(yesterday)
            await channel.send(embed=results)
        except Exception as ex:
            logger.error(
                "Unable to post daily summary to channel: %s",
                ex,
                exc_info=ex,
                extra={"guild_id": channel.guild.id, "channel_id": channel.id},
            )

    logger.info("Daily summary finished")
