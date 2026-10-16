import hashlib
import json
from pathlib import Path

from thirty_memes_bot.text import normalize

FEATURES_NAME = "features.txt"
SEPARATOR = "\n"
BUCKETS = 30

WEIGHT_THR = 0.01
AGGR_THR = 0.9
WORD_THR = 3

AGGR_THEME_SCALE = 0.3
AGGR_THEME_COUNT_THR = 2
AGGR_ACTION_SCALE = 0.5
AGGR_SYMB_SCALE = 0.06
AGGR_SYMB_THR = 10
AGGR_HISTORY = 0.5

def _features_path() -> Path:
    return Path(__file__).resolve().parent / FEATURES_NAME


def _load_table() -> dict:
    raw = json.loads(_features_path().read_text(encoding="utf-8"))
    return raw

def _check_key(message, key) -> bool:
    nKey = normalize(key)
    for word in nKey:
        if word not in message:
            return False
    return True

def _calc_keys(message, table) -> dict[str, dict[str, int]]:
    result = {}
    for name, entry in table.items():
        keyCount = 0
        wordCount = len(message)

        for key in entry["keys"]:
            if _check_key(message, key):
                keyCount += len(normalize(key))
        for key in entry["additional_keys"]:
            if _check_key(message, key):
                wordCount -= len(normalize(key))

        if keyCount > 0:
            result[name] = { "count": keyCount, "word_count": wordCount }
    return result


def _get_themes(message, themes) -> dict[str, float]:
    result = {}
    keys = _calc_keys(message, themes)
    for key, value in keys.items():
        result[key] = value["count"] / float(max(1, value["word_count"] - WORD_THR))
    return result

def _get_actions(message, actions) -> list[str]:
    return [key for key in _calc_keys(message, actions)]

def _get_info(messages, info) -> list[str]:
    result = []
    for m in messages:
        result += [key for key in _calc_keys(m, info)]
    return result

def _get_aggression(messages, table) -> float:
    result = 0

    for m in messages:
        curResult = 0

        themes = _get_themes(m, table["themes"])
        actions = _get_actions(m, table["actions"])
        info = _get_info([m], table["info"])
        curResult += max(0., (len(themes) - AGGR_THEME_COUNT_THR) * AGGR_THEME_SCALE)
        curResult += max(0., (len(actions) - 1) * AGGR_ACTION_SCALE)
        
        words = [word for word in m]
        keys = []
        deletedWords = []
        for name, theme in themes.items():
            keys += [key for key in table["themes"][name]["keys"] + table["themes"][name]["additional_keys"]]
        for name in actions:
            keys += [key for key in table["actions"][name]["keys"] + table["actions"][name]["additional_keys"]]
        for name in info:
            keys += [key for key in table["info"][name]["keys"] + table["info"][name]["additional_keys"]]
        for key in keys:
            if _check_key(words, key):
                deletedWords += normalize(key)

        symbCount, keySymbCount = len("".join(words)), len("".join(deletedWords))
        curResult += max(0., (symbCount - keySymbCount - min(keySymbCount, AGGR_SYMB_THR)) * AGGR_SYMB_SCALE)

        result = min(1., curResult) * ((1. - AGGR_HISTORY) + AGGR_HISTORY * result)

    return result

def choose_meme(messages: list[str]) -> str:
    """Выбирает имя файла мема по окну реплик.

    messages — реплики по времени, последняя — текущая, список непустой.
    Возвращает имя файла из memes/, например "04_base_case.jpg".
    Детерминировано: одинаковый messages даёт одинаковый файл.

    :param messages: непустой список текстовых реплик
    :return: имя существующего файла из memes/
    """
    parts = [normalize(message) for message in messages]
    table = _load_table()

    info = _get_info(parts, table["info"])

    actions = _get_actions(parts[-1], table["actions"])
    themes = _get_themes(parts[-1], table["themes"])

    agression = _get_aggression(parts, table)

    needsKeys = actions + info + [key for key, value in themes.items()]

    results = {}
    for key, value in table["responces"].items():
        aggrWeight = max(0., 1. - abs(value["agressive"] - agression) / AGGR_THR)

        if len(actions) == 1:
            if actions[0] in value["actions"] and aggrWeight > 0.:
                results[key] = aggrWeight
            continue

        if not all([need in needsKeys for need in value["needs"]]):
            continue

        weight = 0.0
        for theme, themeWeight in value["themes"].items():
            if theme in themes:
                weight += max(themeWeight, themes[theme])
        if len(value["themes"]) == 0:
            weight += max(0., 0.4 - len(themes) * .19)

        weight *= aggrWeight
        if weight > 0.0:
            results[key] = weight

    text = SEPARATOR.join([" ".join(part) for part in parts])
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()

    maxWeight = max([value for key, value in results.items()])
    croppedResults = []
    for key, value in results.items():
        if value >= maxWeight - WEIGHT_THR:
            croppedResults.append(key)

    return croppedResults[int(digest, 16) % len(croppedResults)]
