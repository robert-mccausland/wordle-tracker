import asyncio
import discord
import logging

from services.bot.commands import Admin, daily_summary, sodium, summary
from services.bot.config import CLIENT_WAIT_TIMEOUT, SCAN_MESSAGES_INTERVAL, SYNC_COMMANDS, TOKEN
from services.bot.jobs import JobScheduler
from services.bot.scanner import CHANNEL_NAME, delete_message, process_message, scan_unseen_messages

logger = logging.getLogger(__name__)


async def run_client() -> None:
    client = _WordleTrackerClient()
    try:
        logger.info("Logging in client...")
        await client.login(TOKEN)
        await client.sync_commands()

        # Connect in the background so we can run some setup code once the client is ready
        logger.info("Waiting for client to be ready...")
        wait = asyncio.create_task(client.connect())
        await asyncio.wait_for(client.wait_until_ready(), CLIENT_WAIT_TIMEOUT)

        logger.info("Running client setup...")
        await client.setup()

        # Wait for the client to close its connection (normally will happen on SIGINT or similar)
        logger.info("Client successfully started")
        await wait
        logger.warning("Client shutting down...")
    finally:
        await client.close()
        logger.warning("Client closed successfully")


class _WordleTrackerClient(discord.Client):
    def __init__(self) -> None:
        intents: discord.Intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.event_loop = asyncio.get_running_loop()
        self.scheduler = JobScheduler(self.event_loop, self)

    async def setup(self) -> None:
        self.event_loop.create_task(_scan_previous_messages_task(self))
        self.scheduler.start()

    async def sync_commands(self) -> None:
        if SYNC_COMMANDS:
            logger.info("Syncing command definitions...")
            tree = discord.app_commands.CommandTree(self)
            tree.add_command(sodium)
            tree.add_command(summary)
            tree.add_command(daily_summary)
            tree.add_command(Admin())
            await tree.sync()
            logger.info("Command definitions synced successfully")
        else:
            logger.warning("Skipping syncing commands, set SYNC_COMMAND=TRUE to enable this behavior")

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

    async def on_close(self) -> None:
        self.scheduler.stop()


async def _scan_previous_messages_task(client: discord.Client) -> None:
    while True:
        await asyncio.gather(scan_unseen_messages(client), asyncio.sleep(SCAN_MESSAGES_INTERVAL))
