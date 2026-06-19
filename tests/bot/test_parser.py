import unittest
from dataclasses import dataclass

from services.bot.parser import parse_message, logger, LetterGuess


@dataclass(frozen=True)
class TestCase:
    name: str
    message: str
    expected_game_number: int
    expected_is_hard_mode: bool
    expected_is_win: bool
    expected_guesses: list[list[LetterGuess]]


class TestParser(unittest.TestCase):
    def test_parse_result(self) -> None:
        test_cases: list[TestCase] = [
            TestCase(
                name="hard mode win in 4",
                message="""Wordle 1,555 4/6*

🟩⬛⬛🟨⬛
🟩🟨🟨⬛🟨
🟩🟩⬛🟩🟩
🟩🟩🟩🟩🟩

Look at my result!
""",
                expected_game_number=1555,
                expected_is_hard_mode=True,
                expected_is_win=True,
                expected_guesses=[
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
            ),
            TestCase(
                name="wordle birthday puzzle 1826",
                message="""Happy 5th Birthday Wordle 🎂
Wordle 1,826 4/6*

⬛⬛⬛⬛⬛
⬛⬛🟩⬛⬛
⬛⬛🟩⬛🟨
🟩🟩🟩🟩🟩
""",
                expected_game_number=1826,
                expected_is_hard_mode=True,
                expected_is_win=True,
                expected_guesses=[
                    [
                        LetterGuess.NONE,
                        LetterGuess.NONE,
                        LetterGuess.NONE,
                        LetterGuess.NONE,
                        LetterGuess.NONE,
                    ],
                    [
                        LetterGuess.NONE,
                        LetterGuess.NONE,
                        LetterGuess.GREEN,
                        LetterGuess.NONE,
                        LetterGuess.NONE,
                    ],
                    [
                        LetterGuess.NONE,
                        LetterGuess.NONE,
                        LetterGuess.GREEN,
                        LetterGuess.NONE,
                        LetterGuess.YELLOW,
                    ],
                    [
                        LetterGuess.GREEN,
                        LetterGuess.GREEN,
                        LetterGuess.GREEN,
                        LetterGuess.GREEN,
                        LetterGuess.GREEN,
                    ],
                ],
            ),
        ]

        for case in test_cases:
            with self.subTest(case=case.name):
                result = parse_message(case.message)

                self.assertNoLogs(logger)
                self.assertIsNotNone(result)
                assert result is not None
                self.assertEqual(result.game_number, case.expected_game_number)
                self.assertEqual(result.is_hard_mode, case.expected_is_hard_mode)
                self.assertEqual(result.is_win, case.expected_is_win)
                self.assertEqual(result.guesses, case.expected_guesses)
