"""프리셋 레지스트리 불변식과 문서·코드 동기화 테스트.

가장 중요한 것은 마지막 클래스다. `packs/ko/core.md`의 "완화" 열과 `presets.py`의
relax 집합이 어긋나면, 프롬프트와 스캐너가 서로 다른 말을 하기 시작한다.
그 드리프트를 사람이 눈으로 잡을 수는 없다.
"""

import re
import unittest
from pathlib import Path

from humanizer import detect, presets

ROOT = Path(__file__).resolve().parent.parent
KO_CORE = ROOT / "packs" / "ko" / "core.md"

ABBREV = {
    "nb": "naver-blog",
    "db": "dev-blog",
    "ig": "instagram-post",
    "rl": "instagram-reels",
    "cm": "instagram-comment",
}


def parse_core_table():
    """core.md의 패턴 표를 (패턴ID, 스캐너ID, 완화 프리셋 집합)으로 읽는다."""
    rows = []
    for line in KO_CORE.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 6 or not re.fullmatch(r"[A-K]-\d+", cells[0]):
            continue
        scanner = cells[4].strip("`") if cells[4] else ""
        relax = {ABBREV[a] for a in re.findall(r"`(nb|db|ig|rl|cm)`", cells[5])}
        rows.append((cells[0], scanner, relax))
    return rows


class TestRegistry(unittest.TestCase):
    def test_default_exists(self):
        self.assertIn(presets.DEFAULT, presets.PRESETS)

    def test_ids_match_keys(self):
        for key, preset in presets.PRESETS.items():
            self.assertEqual(key, preset.id)

    def test_relaxed_rules_exist(self):
        for preset in presets.PRESETS.values():
            for rule_id in preset.relax:
                with self.subTest(preset=preset.id, rule=rule_id):
                    self.assertIn(rule_id, detect.RULES_BY_ID)

    def test_never_relaxed_wins_over_declaration(self):
        for preset_id in presets.ids():
            with self.subTest(preset=preset_id):
                self.assertFalse(presets.relaxed(preset_id) & presets.NEVER_RELAXED)

    def test_restyle_presets_use_fact_ledger(self):
        for preset_id in ("instagram-post", "instagram-reels", "instagram-comment"):
            self.assertEqual("fact-ledger", presets.get(preset_id).guard)

    def test_general_relaxes_nothing(self):
        self.assertEqual(frozenset(), presets.get("general").relax)

    def test_unknown_preset_message_lists_valid_ids(self):
        with self.assertRaises(KeyError) as caught:
            presets.get("tiktok")
        self.assertIn("general", str(caught.exception))

    def test_budget_rendering(self):
        self.assertEqual("원문 ±5%", presets.get("general").budget)
        self.assertEqual("1,000~2,000자", presets.get("naver-blog").budget)
        self.assertEqual("40자 이내", presets.get("instagram-comment").budget)


class TestDocSync(unittest.TestCase):
    def test_table_is_parseable(self):
        self.assertGreater(len(parse_core_table()), 30)

    def test_scanner_ids_match_rule_table(self):
        documented = {scanner for _, scanner, _ in parse_core_table() if scanner}
        self.assertEqual(
            set(detect.RULES_BY_ID), documented,
            "core.md의 스캐너 열과 detect.RULES가 어긋납니다",
        )

    def test_relax_columns_match_presets(self):
        for pattern_id, scanner, documented in parse_core_table():
            if not scanner:
                continue
            actual = {
                pid for pid, preset in presets.PRESETS.items() if scanner in preset.relax
            }
            with self.subTest(pattern=pattern_id, scanner=scanner):
                self.assertEqual(
                    documented, actual,
                    f"{pattern_id}: 문서는 {sorted(documented)}, 코드는 {sorted(actual)}",
                )

    def test_declared_packs_exist(self):
        for preset in presets.PRESETS.values():
            if preset.pack:
                with self.subTest(preset=preset.id):
                    self.assertTrue((ROOT / preset.pack).is_file())


if __name__ == "__main__":
    unittest.main()
