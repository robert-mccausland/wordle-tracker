from pathlib import Path
import signal
import django
import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

from services.bot.logging import setup_logging

load_dotenv(Path.cwd() / ".env")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wordletracker.settings")
setup_logging()
django.setup()

# The above code needs to be ran before the rest of the app is imported
from services.bot.startup import run  # noqa: E402

logger = logging.getLogger(__name__)


async def main() -> int:
    application = asyncio.create_task(run())

    def handle_signal(signal: signal.Signals) -> None:
        logger.info(f"Got {signal.name} signal, sending cancellation request")
        application.cancel()

    # Signals only supported on unix type systems
    try:
        loop = asyncio.get_running_loop()
        for shutdown_signal in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(shutdown_signal, handle_signal, shutdown_signal)
    except Exception as ex:
        logger.warning("Failed to register signal handlers (are you using windows?) %s", ex, exc_info=ex)

    try:
        await application
    except Exception as ex:
        logger.error("Error while running app: %s", ex, exc_info=ex)
        return 1
    except asyncio.exceptions.CancelledError:
        logger.warning("App shutdown due to cancellation request")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
