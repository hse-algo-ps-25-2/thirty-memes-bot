import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import algorithm
from thirty_memes_bot.loader import load_module

ROOT = Path(__file__).resolve().parent
HISTORY_A = ["Завтра экзамен, паника", "да"]
HISTORY_B = ["Сдал экзамен, победа", "да"]


class TestChooseMeme(unittest.TestCase):
    def test_history_changes_answer(self):
        self.assertEqual(algorithm.choose_meme(HISTORY_A), "01_panic.jpg")
        self.assertEqual(algorithm.choose_meme(HISTORY_B), "02_success.jpg")

    def test_determinism_without_mutating_input(self):
        history = list(HISTORY_A)
        first = algorithm.choose_meme(history)
        algorithm.choose_meme(HISTORY_B)
        self.assertEqual(first, algorithm.choose_meme(history))
        self.assertEqual(history, HISTORY_A)

    def test_normalization(self):
        self.assertEqual(algorithm.choose_meme(["ДЕДЛАЙНЫ!!!"]), "15_deadline.jpg")

    def test_fallback_for_unknown_or_empty_text(self):
        for messages in (["qzxv"], [""], ["!!!"], ["да"], []):
            with self.subTest(messages=messages):
                self.assertEqual(algorithm.choose_meme(messages), "30_neutral.jpg")

    def test_latest_message_has_greater_weight(self):
        self.assertEqual(algorithm.choose_meme(["паника", "победа"]), "02_success.jpg")
        self.assertEqual(algorithm.choose_meme(["победа", "паника"]), "01_panic.jpg")

    def test_repeated_word_does_not_increase_score(self):
        self.assertEqual(algorithm.choose_meme(["паника " * 100, "победа"]), "02_success.jpg")

    def test_only_last_five_messages_are_used(self):
        tail = ["да"] * 5
        self.assertEqual(algorithm.choose_meme(["паника"] + tail), algorithm.choose_meme(tail))

    def test_removing_old_message_can_change_answer(self):
        self.assertNotEqual(algorithm.choose_meme(HISTORY_A), algorithm.choose_meme(HISTORY_A[1:]))

    def test_tie_uses_lower_number_independent_of_word_order(self):
        for text in ("обед кофе", "кофе обед"):
            self.assertEqual(algorithm.choose_meme([text]), "06_lunch.jpg")

    def test_exactly_thirty_images_match_configuration(self):
        data = json.loads(algorithm.FEATURES_PATH.read_text(encoding="utf-8"))
        configured = {meme["file"] for meme in data["memes"]}
        actual = {path.name for path in (ROOT / "memes").iterdir() if path.is_file()}
        self.assertEqual(len(actual), 30)
        self.assertEqual(actual, configured)

    def test_every_meme_is_reachable(self):
        data = json.loads(algorithm.FEATURES_PATH.read_text(encoding="utf-8"))
        for meme in data["memes"]:
            with self.subTest(meme=meme["file"]):
                text = " ".join(meme["weights"])
                self.assertEqual(algorithm.choose_meme([text]), meme["file"])

    def test_feature_edit_changes_answer_without_reloading_module(self):
        data = json.loads(algorithm.FEATURES_PATH.read_text(encoding="utf-8"))
        with TemporaryDirectory() as directory:
            path = Path(directory) / "features.txt"
            path.write_text(json.dumps(data), encoding="utf-8")
            with patch.object(algorithm, "FEATURES_PATH", path):
                self.assertEqual(algorithm.choose_meme(["обед"]), "06_lunch.jpg")
                data["memes"][5]["weights"]["обед"] = 0
                path.write_text(json.dumps(data), encoding="utf-8")
                self.assertEqual(algorithm.choose_meme(["обед"]), data["fallback"])

    def test_shell_can_load_module(self):
        loaded = load_module("cherepaha", ROOT)
        name = loaded.choose_meme(HISTORY_A)
        self.assertTrue((loaded.memes_dir / name).is_file())


if __name__ == "__main__":
    unittest.main()
