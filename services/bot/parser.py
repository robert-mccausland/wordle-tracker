from dataclasses import dataclass
from enum import Enum
import logging
from typing import Optional
import unittest
import regex

WORD_LENGTH = 5
MAX_GUESSES = 6

logger = logging.getLogger(__name__)


class LetterGuess(Enum):
    NONE = 0
    YELLOW = 1
    GREEN = 2


@dataclass
class GameResult:
    game_number: int
    is_win: bool
    is_hard_mode: bool
    guesses: list[list[LetterGuess]]


def parse_message(message: str) -> Optional[GameResult]:
    # Any messages not starting with Wordle are not results so we skip them immediately
    if not message.startswith("Wordle "):
        return None

    lines = message.split("\n")
    header = lines[0].split(" ")

    # A malformed header may just be a random message starting with "Wordle "
    if len(header) != 3:
        return None

    # Here we are quite confident that its a real wordle result so log any errors as
    # the noise should be fairly low
    game_number = _parse_int(header[1])
    if game_number is None:
        logger.warning("Wordle message contained invalid game number", extra={"game_number": header[1]})
        return None

    is_hard_mode = header[2].endswith("*")
    summaryText = header[2].removesuffix("*").split("/")
    if len(summaryText) != 2:
        logger.warning("Wordle message contained invalid summary text", extra={"summary_text": header[2]})
        return None

    guess_count = _parse_int(summaryText[0])
    if guess_count is None:
        if summaryText[0] != "X":
            logger.warning("Wordle message contained invalid guess count", extra={"guess_count": summaryText[0]})
            return None
    elif guess_count <= 0 or guess_count > MAX_GUESSES:
        logger.warning("Wordle message contained invalid guess count", extra={"guess_count": guess_count})
        return None

    max = _parse_int(summaryText[1])
    if max is None:
        logger.warning("Wordle message contained invalid max", extra={"max": summaryText[1]})
        return None

    if max != MAX_GUESSES:
        logger.warning("Wordle message contained invalid max", extra={"max": max})
        return None

    if len(lines[1]) != 0:
        logger.warning("Wordle message did not contain empty second line", extra={"line1": lines[1]})
        return None

    guesses: list[list[LetterGuess]] = []
    for line in lines[2:]:
        guess = _parse_guess(line)
        if guess is None:
            return None
        guesses.append(guess)

    if len(guesses) != (guess_count or MAX_GUESSES):
        logger.warning(
            "Number of guesses included do not match guess count in header",
            extra={"guess_count": guess_count, "guess_length": len(guesses)},
        )
        return None

    return GameResult(
        game_number=game_number,
        is_win=guess_count is not None,
        is_hard_mode=is_hard_mode,
        guesses=guesses,
    )


GRAPHEME_REGEX = regex.compile(r"\X")


def _parse_int(value: str) -> Optional[int]:
    try:
        sanitized = value.replace(",", "").strip()
        return int(sanitized)
    except ValueError:
        return None


def _parse_guess(guess: str) -> Optional[list[LetterGuess]]:
    result = []

    # Out of an abundance of caution make sure we do not have a very long string which
    # could cause some sort of attack vector due to regex being a strange beast.
    # We do not expect each character to be more than a double character so twice the
    # word length should be plenty.
    if len(guess) > WORD_LENGTH * 2:
        return None

    graphemes = GRAPHEME_REGEX.findall(guess)
    for grapheme in graphemes:
        letter_guess = _parse_letter_guess(grapheme)
        if letter_guess is None:
            logger.info("Guess contains invalid character", extra={"character": grapheme})
            return None
        result.append(letter_guess)

    if len(result) != WORD_LENGTH:
        logger.info("Guess has invalid length", extra={"length": len(result)})
        return None

    return result


def _parse_letter_guess(letter_guess: str) -> Optional[LetterGuess]:
    match letter_guess:
        case "🟩":
            return LetterGuess.GREEN
        case "🟨":
            return LetterGuess.YELLOW
        case "⬛":
            return LetterGuess.NONE
        case "⬜":
            return LetterGuess.NONE
        case _:
            return None


class TestParser(unittest.TestCase):
    def test_parse_result(self) -> None:
        message = """Wordle 1,555 4/6*

🟩⬛⬛🟨⬛
🟩🟨🟨⬛🟨
🟩🟩⬛🟩🟩
🟩🟩🟩🟩🟩"""

        result = parse_message(message)

        self.assertNoLogs(logger)
        self.assertIsNotNone(result)
        if result is None:
            return

        self.assertEqual(result.game_number, 1555)
        self.assertTrue(result.is_hard_mode)
        self.assertTrue(result.is_win)
        self.assertEqual(
            result.guesses,
            [
                [
                    LetterGuess.GREEN,
                    LetterGuess.NONE,
                    LetterGuess.NONE,
                    LetterGuess.YELLOW,
                    LetterGuess.NONE,
                ],
                [
                    LetterGuess.GREEN,
                    LetterGuess.YELLOW,
                    LetterGuess.YELLOW,
                    LetterGuess.NONE,
                    LetterGuess.YELLOW,
                ],
                [
                    LetterGuess.GREEN,
                    LetterGuess.GREEN,
                    LetterGuess.NONE,
                    LetterGuess.GREEN,
                    LetterGuess.GREEN,
                ],
                [
                    LetterGuess.GREEN,
                    LetterGuess.GREEN,
                    LetterGuess.GREEN,
                    LetterGuess.GREEN,
                    LetterGuess.GREEN,
                ],
            ],
        )


if __name__ == "__main__":
    unittest.main()
