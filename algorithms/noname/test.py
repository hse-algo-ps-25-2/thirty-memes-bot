import re
import unittest
from pathlib import Path

from algorithm import _load_table, choose_meme

MEME_NAME = re.compile(r"^(0[1-9]|[12]\d|30)_[A-Za-z0-9_]+\.(jpg|png|webp)$")
MEMES_DIR = Path(__file__).resolve().parent / "memes"

HISTORY_A = ["расскажи про рекурсию", "какая сложность"]
HISTORY_B = ["что такое очередь", "какая сложность"]

TABLE = _load_table()


def _meme_names() -> set[str]:
    """Имена jpg/png/webp в memes/ этой папки."""
    return {
        path.name
        for path in MEMES_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".png", ".webp"}
    }


class TestChooseMeme(unittest.TestCase):
    """Контракт задания: форма имени, файл на диске, детерминизм, разные истории."""

    def test_filename_matches_required_pattern(self):
        """Возврат — строка вида NN_латиница.jpg или .png или .webp"""
        name = choose_meme(["рекурсия"])
        self.assertIsInstance(name, str)
        self.assertRegex(name, MEME_NAME)

    def test_deterministic_on_repeated_call(self):
        """Одинаковое окно на двух вызовах даёт одно и то же имя."""
        messages = ["рекурсия", "не понимаю", "сложность"]
        self.assertEqual(choose_meme(messages), choose_meme(list(messages)))

    def test_returned_file_exists_when_memes_present(self):
        """Выбранное имя есть среди файлов в memes/; пустой каталог — пропуск."""
        names = _meme_names()
        if not names:
            self.skipTest("в memes/ ещё нет картинок")
        name = choose_meme(["контрпример"])
        self.assertIn(name, names)

    def test_history_changes_choice(self):
        """Одна «сложность» после разных предысторий даёт разные файлы (HISTORY_A и HISTORY_B)."""
        self.assertGreaterEqual(len(HISTORY_A), 2)
        self.assertGreaterEqual(len(HISTORY_B), 2)
        self.assertEqual(HISTORY_A[-1], HISTORY_B[-1])
        self.assertNotEqual(HISTORY_A[:-1], HISTORY_B[:-1])
        self.assertNotEqual(choose_meme(HISTORY_A), choose_meme(HISTORY_B))

    def test_any_input_has_answer(self):
        """Запасной вариант"""
        for message in ["", "здравствуйте", "до свидания"]:
            self.assertEqual(choose_meme([message]), TABLE.outputs["START OTHER"])


class TestTransitions(unittest.TestCase):
    def test_topic_moves_to_talk(self):
        self.assertEqual(
            choose_meme(["рекурсия", "сложность"]), TABLE.outputs["TALK COMPLEXITY REC"]
        )

    def test_topic_kept_through_other(self):
        """OTHER в TALK не меняет состояние"""
        self.assertEqual(
            choose_meme(["рекурсия", "привет", "сложность"]),
            choose_meme(["рекурсия", "сложность"]),
        )

    def test_confused_transit_to_lost(self):
        self.assertEqual(
            choose_meme(["стек", "не понимаю", "сложность"]),
            TABLE.outputs["LOST COMPLEXITY DS"],
        )

    def test_double_confused_forgets_topic(self):
        """Тема сбрасывается при LOST + CONFUSED."""
        self.assertEqual(
            choose_meme(["рекурсия", "не понимаю", "не понимаю", "сложность"]),
            choose_meme(["сложность"]),
        )

    def test_new_topic(self):
        """Топик меняется"""
        self.assertEqual(
            choose_meme(["рекурсия", "стек", "сложность"]),
            choose_meme(["стек", "сложность"]),
        )

    def test_diffirent_answers_for_different_histories(self):
        """Разные истории"""
        self.assertNotEqual(
            choose_meme(["рекурсия", "сложность"]), choose_meme(["сложность"])
        )


if __name__ == "__main__":
    unittest.main()
