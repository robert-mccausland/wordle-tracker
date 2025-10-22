from datetime import date


WORDLE_EPOCH = date(2021, 6, 19)


def game_number_for_day(day: date) -> int | None:
    game_number = (day - WORDLE_EPOCH).days
    if game_number <= 0:
        return None

    return game_number
