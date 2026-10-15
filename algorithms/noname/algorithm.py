import json
from pathlib import Path
from typing import NamedTuple

from thirty_memes_bot.text import normalize

FEATURES_NAME = "features.txt"


class Table(NamedTuple):
    start: str
    states: dict[str, str]
    topic: dict[str, str]
    symbols: dict[str, str]
    transitions: dict[str, dict[str, str]]
    outputs: dict[str, str]


class Symbol(NamedTuple):
    name: str
    topic: str | None = None


def _features_path() -> Path:
    return Path(__file__).resolve().parent / FEATURES_NAME


def _load_table() -> Table:
    return Table(**json.loads(_features_path().read_text(encoding="utf-8")))


def _get_symbol(part: str, table: Table) -> Symbol:
    for phrase, value in table.symbols.items():
        if phrase in part:
            return Symbol(value)

    for lemma in part.split():
        if lemma in table.topic:
            return Symbol("TOPIC", table.topic[lemma])

    return Symbol("OTHER")


def _get_key(state: str, symbol: Symbol, topic: str | None) -> str:
    if topic is None:
        return f"{state} {symbol.name}"

    return f"{state} {symbol.name} {topic}"


def choose_meme(messages: list[str]) -> str:
    """Выбирает имя файла мема по окну реплик.

    messages — реплики по времени, последняя — текущая, список непустой.
    Возвращает имя файла из memes/, например "04_base_case.jpg".
    Детерминировано: одинаковый messages даёт одинаковый файл.

    :param messages: непустой список текстовых реплик
    :return: имя существующего файла из memes/
    """
    parts = [" ".join(normalize(message)) for message in messages]
    table = _load_table()

    state = table.start
    topic = None
    key = None

    for part in parts:
        symbol = _get_symbol(part, table)

        if symbol.topic:
            topic = symbol.topic

        key = _get_key(state, symbol, topic)

        state = table.transitions[state][symbol.name]

        if table.states[state] == "forget_topic":
            topic = None

    assert isinstance(key, str)
    return table.outputs[key]
