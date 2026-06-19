from dataclasses import dataclass
from enum import Enum
import logging
from typing import Optional
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
    lines = message.split("\n")

    start_index = 0
    # To catch cases were people put stuff before their result we check each line to see if its
    # a reasonable looking wordle result
    while True:
        if len(lines) == start_index:
            return None

        # A line starting with "Wordle " which has 3 words total is good enough of a match for us to
        # start trying to parse it
        if lines[start_index].startswith("Wordle "):
            header = lines[start_index].split(" ")
            if len(header) == 3:
                break

        start_index += 1

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

    if len(lines[start_index + 1]) != 0:
        logger.warning("Wordle message did not contain empty second line", extra={"line1": lines[1]})
        return None

    guesses: list[list[LetterGuess]] = []
    for line in lines[start_index + 2 :]:
        guess = _parse_guess(line)
        if guess is None:
            break
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

    # We expect each character to be more than a double character so twice the
    # word length should be plenty.
    if len(guess) == 0 or len(guess) > WORD_LENGTH * 2:
        # If the length of the guess is incorrect we do not surface a warning as
        # this is is the expected way to detect when the wordle content ends
        return None

    graphemes = GRAPHEME_REGEX.findall(guess)
    for grapheme in graphemes:
        letter_guess = _parse_letter_guess(grapheme)
        if letter_guess is None:
            logger.warning("Guess contains invalid character", extra={"character": grapheme})
            return None
        result.append(letter_guess)

    if len(result) != WORD_LENGTH:
        logger.warning("Guess has invalid length", extra={"length": len(result)})
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
