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

    def test_only_general_and_dev_blog_keep_the_change_rate_guard(self):
        # `SKILL.md` 4절이 이 두 개만 변경률 가드라고 선언한다. 어투와 분량을
        # 옮기는 프리셋에서는 변경률이 언제나 30%를 넘어 가드가 뜻을 잃는다.
        change_rate = {
            pid for pid, preset in presets.PRESETS.items() if preset.guard == "change-rate"
        }
        self.assertEqual({"general", "dev-blog"}, change_rate)

    def test_restyle_presets_use_fact_ledger(self):
        for preset_id in (
            "naver-blog", "instagram-post", "instagram-reels", "instagram-comment"
        ):
            with self.subTest(preset=preset_id):
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

    def test_dev_blog_budget_is_not_confused_with_general(self):
        # 둘 다 상·하한이 없지만 뜻이 다르다. 개발 블로그는 길어도 되는 채널이다.
        self.assertEqual("상한 없음", presets.get("dev-blog").budget)


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

    def test_pack_documents_its_own_guard(self):
        """팩 문서가 코드와 다른 가드를 안내하면 사람이 그 문서를 믿는다."""
        wording = {"change-rate": "변경률 가드가 유효하다", "fact-ledger": "사실 대장을 쓴다"}
        for preset in presets.PRESETS.values():
            if not preset.pack:
                continue
            text = (ROOT / preset.pack).read_text(encoding="utf-8")
            with self.subTest(preset=preset.id):
                self.assertIn(wording[preset.guard], text)

    def test_packs_declare_every_relaxed_rule(self):
        for preset in presets.PRESETS.values():
            if not preset.pack:
                continue
            text = (ROOT / preset.pack).read_text(encoding="utf-8")
            for rule_id in preset.relax:
                with self.subTest(preset=preset.id, rule=rule_id):
                    self.assertIn(rule_id, text, f"{preset.pack}에 {rule_id} 설명이 없습니다")


class TestFixtureIntegrity(unittest.TestCase):
    """픽스처가 스스로 지켜야 하는 것."""

    FIXTURES = ROOT / "eval" / "fixtures"
    FENCE = re.compile(r"```.*?```", re.DOTALL)

    def test_code_blocks_survive_the_edit(self):
        """코드블록은 윤문 전후가 바이트 단위로 같아야 한다.

        스캐너의 마스킹은 탐지에서만 빼 준다. 윤문하며 코드를 건드리는 건
        사람이고, 그러면 복사해서 돌아가지 않는 글이 된다.
        """
        for expect in sorted(self.FIXTURES.rglob("*.expect.json")):
            stem = expect.with_suffix("").with_suffix("")
            before = self.FENCE.findall(
                stem.with_suffix(".before.md").read_text(encoding="utf-8")
            )
            after = self.FENCE.findall(
                stem.with_suffix(".after.md").read_text(encoding="utf-8")
            )
            with self.subTest(case=f"{stem.parent.name}/{stem.name}"):
                self.assertEqual(before, after)

    def test_every_preset_with_a_pack_has_fixtures(self):
        for preset in presets.PRESETS.values():
            if not preset.pack:
                continue
            with self.subTest(preset=preset.id):
                cases = list((self.FIXTURES / preset.id).glob("*.expect.json"))
                self.assertGreaterEqual(len(cases), 1)


if __name__ == "__main__":
    unittest.main()
