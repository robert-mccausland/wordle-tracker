import logging
import os

from services.bot.client import create_client

logger = logging.getLogger(__name__)


async def startup() -> int:
    token = os.getenv("TOKEN")
    if token is None:
        logger.error("Expected TOKEN environment variable to be provided")
        return 1

    client = await create_client()
    await client.start(token)
    return 0
