import asyncio
import discord
import logging

from services.bot.commands import Admin, daily_summary, sodium, summary
from services.bot.config import SCAN_MESSAGES_INTERVAL
from services.bot.jobs import JobScheduler
from services.bot.scanner import CHANNEL_NAME, delete_message, process_message, scan_unseen_messages

logger = logging.getLogger(__name__)


async def create_client() -> discord.Client:
    intents: discord.Intents = discord.Intents.default()
    intents.message_content = True

    logger.info("Starting Discord client...")
    event_loop = asyncio.get_running_loop()
    client = discord.Client(intents=intents)
    tree = discord.app_commands.CommandTree(client)
    scheduler = JobScheduler(event_loop, client)

    @client.event
    async def on_ready() -> None:
        await tree.sync()
        logger.info("Discord client is ready", extra={"user": client.user})
        event_loop.create_task(_scan_previous_messages_task(client))
        scheduler.start()

    @client.event
    async def on_message(message: discord.Message) -> None:
        if not isinstance(message.channel, discord.TextChannel):
            return

        if message.channel.name != CHANNEL_NAME:
            return

        await process_message(message)

    @client.event
    async def on_message_edit(before: discord.Message, after: discord.Message) -> None:
        if not isinstance(after.channel, discord.TextChannel):
            return

        if after.channel.name != CHANNEL_NAME:
            return

        await process_message(after)

    @client.event
    async def on_message_delete(message: discord.Message) -> None:
        if not isinstance(message.channel, discord.TextChannel):
            return

        if message.channel.name != CHANNEL_NAME:
            return

        await delete_message(message)

    @client.event
    async def on_close() -> None:
        scheduler.stop()

    tree.add_command(sodium)
    tree.add_command(summary)
    tree.add_command(daily_summary)
    tree.add_command(Admin())

    return client


async def _scan_previous_messages_task(client: discord.Client) -> None:
    while True:
        await asyncio.gather(scan_unseen_messages(client), asyncio.sleep(SCAN_MESSAGES_INTERVAL))
