"""계량 단위 테스트. 한국어 글자수는 `len()`으로 세면 두 군데서 틀린다."""

import unicodedata
import unittest

from humanizer import metrics


class TestCharCount(unittest.TestCase):
    def test_hangul_syllables(self):
        self.assertEqual(3, metrics.char_count("가나다"))

    def test_decomposed_hangul_counts_as_one(self):
        """macOS에서 복사한 한국어는 자모가 분해되어 온다."""
        nfd = unicodedata.normalize("NFD", "각")
        self.assertEqual(3, len(nfd))
        self.assertEqual(1, metrics.char_count(nfd))

    def test_emoji_zwj_sequence_counts_as_one(self):
        family = "👨‍👩‍👧"
        self.assertGreater(len(family), 1)
        self.assertEqual(1, metrics.char_count(family))

    def test_variation_selector_attaches(self):
        self.assertEqual(1, metrics.char_count("❤️"))

    def test_without_spaces(self):
        self.assertEqual(9, metrics.char_count("가 나 다 라 마"))
        self.assertEqual(5, metrics.char_count("가 나 다 라 마", include_spaces=False))


class TestSentences(unittest.TestCase):
    def test_decimal_is_not_a_sentence_break(self):
        self.assertEqual(
            ["기준은 3.5%다.", "다음 문장이다."],
            metrics.split_sentences("기준은 3.5%다. 다음 문장이다."),
        )

    def test_table_rows_are_dropped(self):
        text = "본문이다.\n\n| 가 | 나 |\n|---|---|\n| 1 | 2 |\n\n다음 본문이다."
        self.assertEqual(["본문이다.", "다음 본문이다."], metrics.split_sentences(text))

    def test_heading_is_dropped(self):
        self.assertEqual(["본문이다."], metrics.split_sentences("## 제목\n\n본문이다."))

    def test_bullet_marker_is_stripped(self):
        self.assertEqual(["첫째 항목", "둘째 항목"], metrics.split_sentences("- 첫째 항목\n- 둘째 항목"))

    def test_stats_on_empty_text(self):
        stats = metrics.sentence_stats("")
        self.assertEqual(0, stats.count)
        self.assertEqual(0.0, stats.stdev)

    def test_uniform_length_has_low_stdev(self):
        text = "가나다라마바사자. 아자차카타파하가. 나다라마바사자아."
        self.assertLess(metrics.sentence_stats(text).stdev, 2)


class TestChangeRate(unittest.TestCase):
    def test_identical_text_is_zero(self):
        self.assertEqual(0.0, metrics.change_rate("같은 글이다.", "같은 글이다."))

    def test_empty_pair_is_zero(self):
        self.assertEqual(0.0, metrics.change_rate("", ""))

    def test_full_rewrite_is_high(self):
        rate = metrics.change_rate("완전히 다른 원문이다.", "전혀 관계없는 결과물!")
        self.assertGreater(rate, 0.5)

    def test_small_edit_is_low(self):
        rate = metrics.change_rate(
            "이 방식이 더 안전하다고 보여진다.", "이 방식이 더 안전하다고 보인다."
        )
        self.assertLess(rate, 0.2)


class TestBudget(unittest.TestCase):
    def test_within_five_percent(self):
        self.assertTrue(metrics.within_budget("가" * 98, 100))
        self.assertFalse(metrics.within_budget("가" * 80, 100))

    def test_report_includes_both_counts(self):
        data = metrics.report("가 나 다", target=5)
        self.assertEqual(5, data["chars_with_spaces"])
        self.assertEqual(3, data["chars_without_spaces"])
        self.assertEqual(0, data["delta"])
        self.assertTrue(data["within_2pct"])

    def test_report_without_target_omits_budget_keys(self):
        self.assertNotIn("target", metrics.report("가 나 다"))


if __name__ == "__main__":
    unittest.main()
