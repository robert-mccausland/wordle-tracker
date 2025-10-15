from pathlib import Path
import django
import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
load_dotenv(Path.cwd() / ".env")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wordletracker.settings")
django.setup()

# The above code needs to be ran before the rest of the app is imported
from services.bot.client import run_client  # noqa: E402

logger = logging.getLogger(__name__)


def main() -> int:
    asyncio.run(run_client())
    return 0


if __name__ == "__main__":
    sys.exit(main())
