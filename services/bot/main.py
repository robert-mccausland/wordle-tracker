import django
import os
import sys
import asyncio

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wordletracker.settings")
django.setup()

import logging  # noqa: E402

logging.basicConfig(
    level=logging.INFO,  # show INFO and above
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.bot.client import create_client  # noqa: E402


async def main() -> int:
    token = os.getenv("TOKEN")
    if token is None:
        logger.error("Expected TOKEN environment variable to be provided")
        return 1

    client = await create_client()
    await client.start(token)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
