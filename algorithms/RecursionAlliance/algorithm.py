import hashlib
import json
from pathlib import Path

from thirty_memes_bot.text import normalize

FEATURES_NAME = "features.txt"
KEY_TOKENS_NAME = "key_tokens.txt"
SCORES_NAME = "scores.txt"
SEPARATOR = "\n"
BUCKETS = 30


def _file_path(file_name) -> Path:
    return Path(__file__).resolve().parent / file_name


def _load_file(file_name) -> dict[int, str]:
    raw = json.loads(_file_path(file_name).read_text(encoding="utf-8"))
    return {int(key): value for key, value in raw.items()}


def choose_meme(messages: list[str]) -> str:
    """Выбирает имя файла мема по окну реплик.

    messages — реплики по времени, последняя — текущая, список непустой.
    Возвращает имя файла из memes/, например "04_base_case.jpg".
    Детерминировано: одинаковый messages даёт одинаковый файл.

    :param messages: непустой список текстовых реплик
    :return: имя существующего файла из memes/
    """
    parts = [" ".join(normalize(message)) for message in messages][-1].split()
    text = SEPARATOR.join(parts)
    table = _load_file(FEATURES_NAME)
    key_tokens = _load_file(KEY_TOKENS_NAME)
    scores = _load_file(SCORES_NAME)
    
    for pos in range(BUCKETS):
        index = pos+1
        key_tokens_list = key_tokens[index]
        file_name = table[index]
        for word in parts:
            for key_token in key_tokens_list:
                if word.startswith(key_token):
                    scores[index] += 1

    for pos in scores:
        if scores[pos] == max([scores[pos] for pos in scores]):
            return (table[pos])

    return table[1]
