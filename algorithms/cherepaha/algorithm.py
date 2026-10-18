"""Детерминированный линейный счёт по словам и окну истории."""

import json
import math
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from thirty_memes_bot.text import normalize

FEATURES_PATH = Path(__file__).resolve().with_name("features.txt")
WINDOW = 5
MEME_NAME = re.compile(r"^(0[1-9]|[12]\d|30)_[A-Za-z0-9_]+\.(jpg|png)$")


@lru_cache(maxsize=1)
def _compile_features(source: str):
    """Строит обратный индекс. Ключ кеша — содержимое, поэтому правки видны сразу."""
    data = json.loads(source)
    memes = data["memes"]
    names = sorted(item["file"] for item in memes)
    if (
        len(names) != 30
        or any(not MEME_NAME.fullmatch(name) for name in names)
        or {name[:2] for name in names} != {f"{i:02}" for i in range(1, 31)}
    ):
        raise ValueError("Нужны ровно 30 файлов с уникальными номерами 01–30")
    fallback = data["fallback"]
    if fallback not in names:
        raise ValueError("fallback должен входить в список мемов")

    indices = {name: i for i, name in enumerate(names)}
    index = defaultdict(list)
    for meme in memes:
        weights = {}
        for word, weight in meme["weights"].items():
            if (
                isinstance(weight, bool)
                or not isinstance(weight, (int, float))
                or not math.isfinite(weight)
            ):
                raise ValueError("Вес должен быть конечным числом")
            tokens = normalize(word)
            if len(tokens) != 1:
                raise ValueError(f"Признак должен быть одним словом: {word!r}")
            lemma = tokens[0]
            if lemma in weights:
                raise ValueError(f"Повтор леммы {lemma!r} для {meme['file']}")
            weights[lemma] = weight
        for word, weight in weights.items():
            index[word].append((indices[meme["file"]], weight))
    return names, dict(index), fallback


def choose_meme(messages: list[str]) -> str:
    """Выбирает максимум суммы i * weight(meme, word) по последним 5 репликам.

    Внутри одной реплики слово учитывается один раз. Реплики нумеруются
    от старой к новой, начиная с 1. При равенстве побеждает меньший номер;
    если нет положительного счёта, возвращается настроенный fallback.
    """
    names, index, fallback = _compile_features(
        FEATURES_PATH.read_text(encoding="utf-8")
    )
    scores = [0] * len(names)
    for recency, message in enumerate(messages[-WINDOW:], start=1):
        for word in dict.fromkeys(normalize(message)):
            for meme_index, weight in index.get(word, ()):
                scores[meme_index] += recency * weight
    best = max(range(len(names)), key=scores.__getitem__)
    return names[best] if scores[best] > 0 else fallback
