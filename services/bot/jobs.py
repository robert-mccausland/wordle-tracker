from asyncio import AbstractEventLoop
import asyncio
from datetime import date, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
import logging
import discord

from services.bot.config import CHANNEL_NAME, CLIENT_WAIT_TIMEOUT
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

    def start(self) -> None:
        self.scheduler.start()

    def stop(self) -> None:
        self.scheduler.shutdown()


async def _daily_summary() -> None:
    assert services is not None, "Services must exist for jobs to run"
    logger.info("Daily summary running")

    await asyncio.wait_for(services.client.wait_until_ready(), timeout=CLIENT_WAIT_TIMEOUT)
    yesterday = date.today() - timedelta(days=1)
    async for guild in services.client.fetch_guilds():
        for channel in await guild.fetch_channels():
            if not isinstance(channel, discord.TextChannel):
                continue

            if channel.name != CHANNEL_NAME:
                continue

            try:
                summarizer = Summarizer(guild, channel)
                results = await summarizer.get_daily_results(yesterday)
                await channel.send(embed=results)
            except Exception as ex:
                logger.error(
                    "Unable to post daily summary to channel: %s",
                    ex,
                    exc_info=ex,
                    extra={"guild_id": guild.id, "channel_id": channel.id},
                )

    logger.info("Daily summary finished")
