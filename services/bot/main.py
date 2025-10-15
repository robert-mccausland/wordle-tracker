import django
import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,  # show INFO and above
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wordletracker.settings")
django.setup()
logger = logging.getLogger(__name__)

# Some setup code importantly needs to be ran before the rest of the app is imported
from services.bot.startup import startup  # noqa: E402


def main() -> int:
    return asyncio.run(startup())


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
