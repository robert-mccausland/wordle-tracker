import asyncio
import discord
import logging

from services.bot.commands import Admin, daily_summary, sodium, summary
from services.bot.config import CLIENT_WAIT_TIMEOUT, SYNC_COMMANDS, TOKEN
from services.bot.jobs import JobScheduler
from services.bot.scanner import CHANNEL_NAME, delete_message, process_message

logger = logging.getLogger(__name__)


async def run_client() -> None:
    intents: discord.Intents = discord.Intents.default()
    intents.message_content = True
    client = _WordleTrackerClient(intents=intents)
    scheduler = JobScheduler(asyncio.get_running_loop(), client)

    try:
        logger.info("Logging in client...")
        await client.login(TOKEN)
        await _sync_commands(client)

        # Connect in the background so we can run some setup code once the client is ready
        logger.info("Waiting for client to be ready...")
        asyncio.create_task(client.connect())
        await asyncio.wait_for(client.wait_until_ready(), CLIENT_WAIT_TIMEOUT)

        logger.info("Starting Job Scheduler...")
        scheduler.start()
        logger.info("Client successfully started")

        # Wait until task is cancelled
        await asyncio.Event().wait()

    finally:
        logger.info("Client shutting down...")
        scheduler.shutdown()
        await client.close()
        logger.info("Client successfully stopped")


class _WordleTrackerClient(discord.Client):
    def __init__(self, *, intents: discord.Intents) -> None:
        super().__init__(intents=intents)

    async def on_message(self, message: discord.Message) -> None:
        if not isinstance(message.channel, discord.TextChannel):
            return

        if message.channel.name != CHANNEL_NAME:
            return

        await process_message(message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if not isinstance(after.channel, discord.TextChannel):
            return

        if after.channel.name != CHANNEL_NAME:
            return

        await process_message(after)

    async def on_message_delete(self, message: discord.Message) -> None:
        if not isinstance(message.channel, discord.TextChannel):
            return

        if message.channel.name != CHANNEL_NAME:
            return

        await delete_message(message)


async def _sync_commands(client: discord.Client) -> None:
    if not SYNC_COMMANDS:
        logger.warning("Skipping syncing commands, set SYNC_COMMAND=TRUE to enable this behavior")
        return

    logger.info("Syncing command definitions...")
    tree = discord.app_commands.CommandTree(client)
    tree.add_command(sodium)
    tree.add_command(summary)
    tree.add_command(daily_summary)
    tree.add_command(Admin())
    await tree.sync()
    logger.info("Command definitions synced successfully")
