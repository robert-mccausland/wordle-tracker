import asyncio
import discord
import logging

from services.bot.commands import Admin, sodium, summary
from services.bot.scanner import CHANNEL_NAME, save_message, scan_unseen_messages

logger = logging.getLogger(__name__)

SCAN_MESSAGES_INTERVAL = 300


async def create_client() -> discord.Client:
    intents: discord.Intents = discord.Intents.default()
    intents.message_content = True

    logger.info("Starting Discord client...")
    client = discord.Client(intents=intents)
    tree = discord.app_commands.CommandTree(client)

    @client.event
    async def on_ready() -> None:
        await tree.sync()
        logger.info("Discord client is ready", extra={"user": client.user})
        asyncio.get_running_loop().create_task(_scan_previous_messages_task(client))

    @client.event
    async def on_message(message: discord.Message) -> None:
        if not isinstance(message.channel, discord.TextChannel):
            return

        if message.channel.name != CHANNEL_NAME:
            return

        await save_message(message)

    tree.add_command(sodium)
    tree.add_command(summary)
    tree.add_command(Admin(name="admin", description="Setup and debugging commands"))

    return client


async def _scan_previous_messages_task(client: discord.Client) -> None:
    while True:
        await asyncio.gather(scan_unseen_messages(client), asyncio.sleep(SCAN_MESSAGES_INTERVAL))
