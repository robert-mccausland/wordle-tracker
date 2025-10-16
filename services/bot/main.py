from pathlib import Path
import signal
import django
import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

from services.bot.logging import JsonFormatter

load_dotenv(Path.cwd() / ".env")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wordletracker.settings")

handler = logging.StreamHandler(sys.stdout)
if os.getenv("ENVIRONMENT") == "production":
    handler.setFormatter(JsonFormatter())
else:
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

logging.basicConfig(level=logging.INFO, handlers=[handler])
django.setup()

# The above code needs to be ran before the rest of the app is imported
from services.bot.client import run_client  # noqa: E402

logger = logging.getLogger(__name__)


async def main() -> int:
    run_client_task = asyncio.create_task(run_client())

    def handle_signal(signal: signal.Signals) -> None:
        logger.warning(f"Got {signal.name} signal, shuting down")
        run_client_task.cancel()

    # Signals only supported on unix type systems
    try:
        loop = asyncio.get_running_loop()
        for shutdown_signal in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(shutdown_signal, handle_signal, shutdown_signal)
    except Exception as ex:
        logger.warning("Failed to register signal handlers (are you using windows?) %s", ex, exc_info=ex)

    try:
        await run_client_task
    except Exception as ex:
        logger.error("Error while running client: %s", ex, exc_info=ex)
        return 1
    except asyncio.exceptions.CancelledError:
        logger.info("Program shutdown due to cancellation request")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
