import logging
from services.bot.client import run_client
from services.bot.config import SYNC_COMMANDS, TIMEZONE

logger = logging.getLogger(__name__)


async def startup() -> None:
    logger.info(
        f"Application bootstrapped with the following settings:\nTIMEZONE={TIMEZONE}\nSYNC_COMMANDS={SYNC_COMMANDS}"
    )

    logger.info("Application starting up...")
    await run_client()
