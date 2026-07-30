"""탐지 규칙 단위 테스트.

규칙마다 발동해야 하는 예문(POSITIVE)과, 멀쩡한 사람 글을 흔적으로 오해하지
않는지(NEGATIVE)를 함께 본다. 오탐 쪽이 더 중요하다. 과윤문이 이 스킬의 가장 흔한 실패다.
"""

import unittest

from humanizer import detect

#: 규칙 ID -> 그 규칙이 반드시 발동해야 하는 예문
POSITIVE = {
    "A-1": "정책에 대해 논의했다. 예산에 대해 검토했다. 일정에 대해 정리했다. 결과에 대해 보고했다.",
    "A-2": "도구를 통해 처리한다. 회의를 통해 정한다. 문서를 통해 공유한다.",
    "A-3": "업무에 있어서 가장 중요한 부분이다.",
    "A-6": "성능의 향상을 도모하고 점검을 실시하며 작업의 진행을 확인한다.",
    "A-7": "이 연구는 중요한 의미를 가진다.",
    "A-8": "이 방식이 더 안전하다고 보여진다.",
    "A-9": "규정에 의해 정해지고 관리자에 의해 승인되며 시스템에 의해 기록된다.",
    "A-16": "그것은 빠르다. 그것은 싸다. 그것은 좋다.",
    "A-17": "개발자들이 도구들을 쓰고 문제들을 풀며 사용자들에게 결과들을 준다.",
    "A-19": "현장에서의 개선이 필요하다.",
    "B-1": (
        "주권 인공지능(Sovereign artificial intelligence)이 화두다. "
        "대규모 언어모형(large language model)도 그렇다. "
        "검색 증강 생성(retrieval augmented generation)까지 묶인다."
    ),
    "C-5": "🚀 출시 일정을 공유한다.",
    "C-7": "빠름, 안전, 그리고 편리. 신뢰와 가치와 만족.",
    "C-9": "절차는 (1) 접수 (2) 검토 (3) 승인으로 나뉜다.",
    "C-10": "## 도입: 배경과 목적\n\n본문\n\n## 조치: 단기와 중기\n\n본문",
    "C-11": "자료를 검토하고, 부서에 공유했으며, 일정을 조정했지만, 합의하지 못했다.",
    "D-1": "결론적으로, 이 방향이 맞다.",
    "D-2": "본질적으로 같은 문제다.",
    "D-4": "혁신적인 도구가 진정한 가치를 담아낸다.",
    "D-6": "지금이야말로 결정할 시점이다.",
    "D-8": "이 발표는 업계에 중요한 이정표를 세웠다.",
    "D-9": "전문가들은 그렇게 말한다.",
    "E-1": (
        "회의를 열었고 자료를 냈다. 자료를 냈고 결과를 봤다. 결과를 봤고 점검을 했다. "
        "점검을 했고 정리를 했다. 정리를 했고 보고를 했다."
    ),
    "E-2": "문제가 있다. 여유가 있다. 대안이 있다. 근거가 있다.",
    "F-4": "적극적인 안정성을 표준화를 " * 4,
    "G-3": "다소 어려울 수도 있다. 어느 정도 볼 수 있다. 일정 부분 신중하게 본다.",
    "H-1": "또한 그렇다. 따라서 좋다. 즉 맞다. 게다가 빠르다. 더욱이 싸다.",
    "H-3": "이는 좋다. 이 점에서 맞다. 이 관점에서 옳다.",
    "I-1": "그런 것이다. 이런 것이다. 저런 것이다.",
    "I-4": "무엇보다 사용자를 살피는 것이 중요하다.",
    "J-1": "**가** **나** **다** **라** **마** **바**",
    "J-2": "이 정책은 — 예고 없이 — 발표됐다.",
    "J-4": "“가”와 ‘나’와 “다”를 골랐다.",
    "K-1": "좋은 질문이에요! 아래에 정리해 드릴게요.",
}

#: 사람이 쓴 멀쩡한 문단. S1이 하나도 나오면 안 된다.
CLEAN = """어제 창고에 다시 갔다. 지게차 두 대가 통로를 막고 있어서 한참 서 있었다.
담당자는 미안하다고 했지만 표정은 이미 익숙해 보였다. 온도계는 4도를 가리켰다.
기준은 2도다. 냉장고 문을 여닫는 횟수를 세어 보니 한 시간에 열일곱 번이었다.
그 숫자를 적어 두고 나왔다. 고칠 방법이 바로 떠오르지는 않았다."""


class TestPositives(unittest.TestCase):
    def test_every_rule_fires(self):
        for rule_id, text in POSITIVE.items():
            with self.subTest(rule=rule_id):
                found = {f.rule_id for f in detect.scan(text).findings}
                self.assertIn(rule_id, found, f"{rule_id}가 발동하지 않음: {text[:40]}")

    def test_every_rule_has_a_positive_case(self):
        self.assertEqual(
            sorted(POSITIVE), sorted(detect.RULES_BY_ID),
            "규칙을 추가하면 POSITIVE 예문도 추가해야 합니다",
        )


class TestNegatives(unittest.TestCase):
    def test_clean_prose_has_no_s1(self):
        result = detect.scan(CLEAN)
        self.assertEqual([], [f.rule_id for f in result.s1])

    def test_sentence_initial_conjunction_is_not_c11(self):
        text = "하지만, 그렇다. 그리고, 좋다. 그러나, 아쉽다."
        found = {f.rule_id for f in detect.scan(text).findings}
        self.assertNotIn("C-11", found)

    def test_noun_ending_in_go_is_not_c11(self):
        text = "교통사고, 화재, 침수가 났다. 중고, 신고, 광고가 늘었다."
        found = {f.rule_id for f in detect.scan(text).findings}
        self.assertNotIn("C-11", found)

    def test_standard_abbreviation_is_not_b1(self):
        text = "표준 약어(LLM)와 인터페이스(API)와 장치(GPU)를 그대로 둔다."
        found = {f.rule_id for f in detect.scan(text).findings}
        self.assertNotIn("B-1", found)

    def test_common_particle_is_not_a19(self):
        text = "고객과의 관계와 동료와의 협업이 중요하다."
        found = {f.rule_id for f in detect.scan(text).findings}
        self.assertNotIn("A-19", found)

    def test_pronoun_below_paragraph_threshold(self):
        text = "그것은 빠르다. 다음 문장은 다르다.\n\n그것은 싸다. 여기도 다르다."
        found = {f.rule_id for f in detect.scan(text).findings}
        self.assertNotIn("A-16", found)


class TestMasking(unittest.TestCase):
    def test_code_fence_is_not_scanned(self):
        text = "정상 문장이다.\n\n```python\n# 보여진다 되어진다 — 🚀\n```\n"
        found = {f.rule_id for f in detect.scan(text).findings}
        self.assertNotIn("A-8", found)
        self.assertNotIn("J-2", found)
        self.assertNotIn("C-5", found)

    def test_double_passive_covers_hamnida_inflections(self):
        # 합니다체에서는 '되어집니다' 꼴로 나타난다. '되어지'를 찾으면 못 잡는다.
        for text in ("데이터가 수집되어집니다.", "그렇게 보여집니다.", "결과가 확인되어짐."):
            with self.subTest(text=text):
                found = {f.rule_id for f in detect.scan(text).findings}
                self.assertIn("A-8", found)

    def test_inline_code_is_not_scanned(self):
        found = {f.rule_id for f in detect.scan("`보여진다` 를 설명한다.").findings}
        self.assertNotIn("A-8", found)

    def test_masking_preserves_line_numbers(self):
        text = "첫 줄\n```\n코드\n```\n이 방식이 보여진다.\n"
        finding = next(f for f in detect.scan(text).findings if f.rule_id == "A-8")
        self.assertEqual([5], finding.lines)

    def test_url_is_not_scanned(self):
        found = {f.rule_id for f in detect.scan("https://example.com/a—b 를 열었다.").findings}
        self.assertNotIn("J-2", found)


class TestPresetRelaxation(unittest.TestCase):
    def test_emoji_relaxed_on_instagram(self):
        text = "🚀 오늘의 기록 💡"
        self.assertIn("C-5", {f.rule_id for f in detect.scan(text, "general").findings})
        self.assertNotIn(
            "C-5", {f.rule_id for f in detect.scan(text, "instagram-post").findings}
        )

    def test_em_dash_never_relaxed(self):
        text = "이건 — 저건이다."
        for preset in ("general", "instagram-post", "instagram-reels", "instagram-comment"):
            with self.subTest(preset=preset):
                found = {f.rule_id for f in detect.scan(text, preset).findings}
                self.assertIn("J-2", found)

    def test_hype_never_relaxed(self):
        text = "혁신적인 도구가 진정한 가치를 담아낸다."
        for preset in detect.presets.ids():
            with self.subTest(preset=preset):
                found = {f.rule_id for f in detect.scan(text, preset).findings}
                self.assertIn("D-4", found)

    def test_unknown_preset_raises(self):
        with self.assertRaises(KeyError):
            detect.scan("글", preset="tiktok")


class TestRuleTable(unittest.TestCase):
    def test_every_rule_is_executable(self):
        for rule in detect.RULES:
            with self.subTest(rule=rule.id):
                self.assertTrue(
                    rule.pattern is not None or rule.id in detect.CUSTOM,
                    f"{rule.id}에 패턴도 핸들러도 없습니다",
                )

    def test_severities_are_known(self):
        for rule in detect.RULES:
            self.assertIn(rule.severity, detect.SEVERITY_ORDER)

    def test_findings_are_sorted_by_severity(self):
        text = POSITIVE["K-1"] + POSITIVE["A-1"] + POSITIVE["J-4"]
        order = [detect.SEVERITY_ORDER[f.severity] for f in detect.scan(text).findings]
        self.assertEqual(sorted(order), order)


if __name__ == "__main__":
    unittest.main()
