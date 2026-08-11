"""말투 프로필 테스트."""

import unittest

from humanizer import detect, presets, voice


HUMAN = """\
- obsCall 새로 만들었음
- devel/smartchair에도 적용해야 하는데 확장 사항이 있고 완함
- n초 관련해서 gui에서 초 세팅 가능하도록 수정할 것
- 일단 이 부분 봐야 함 위에 작성한 대로 했는데 안먹힘
- 재부팅 후 다시 진행하려고 했으나 현지 직원 퇴근 시간에 물림
"""

MACHINE = """\
**설정과 자율 SDLC 설계** — 커스터마이징 레이어 스캐폴딩과 훅 부활을 진행했다.
결론적으로 이번 작업은 시사하는 바가 크다.
"""

LOGS = """\
[1697696304.043202][DEBUG][State] Querying[Start]
libsnappy.so.1 => /snap/coga-cona/x1/usr/lib/libsnappy.so.1
/amcl/max_particles: 5000
"""


class TestCleanSample(unittest.TestCase):
    def test_strips_export_artifacts(self):
        raw = '<span underline="true">**제목**</span>\n## 날짜 {toggle="true"}\n대동에서 로봇 가져감 \\~ 7월 말'
        out = voice.clean_sample(raw)
        self.assertNotIn("<span", out)
        self.assertNotIn('toggle="true"', out)
        self.assertIn("~ 7월 말", out)
        self.assertNotIn("\\~", out)

    def test_keeps_ordinary_comparison(self):
        # '<'가 태그가 아니라 부등호인 경우까지 지우면 안 된다.
        self.assertIn("a < b", voice.clean_sample("조건은 a < b 이면 통과"))


class TestScreen(unittest.TestCase):
    def test_drops_machine_written_block(self):
        kept, stats = voice.screen(MACHINE)
        self.assertEqual(stats["blocks_kept"], 0)
        self.assertEqual(kept, "")

    def test_keeps_human_block(self):
        kept, stats = voice.screen(HUMAN)
        self.assertEqual(stats["blocks_dropped"], 0)
        self.assertIn("obsCall", kept)

    def test_mixed_sample_keeps_only_the_human_part(self):
        kept, stats = voice.screen(HUMAN + "\n" + MACHINE)
        self.assertIn("obsCall", kept)
        self.assertNotIn("스캐폴딩", kept)
        self.assertIn("J-2", stats["dropped_by_rule"])

    def test_emoji_and_tilde_do_not_count_as_machine(self):
        # 사람은 메모에 이모지와 물결표를 즐겨 쓴다. 오염 신호로 삼으면 표본이 날아간다.
        block = "🏆 오늘 할 일 정리함\n대동에서 로봇 가져감 ~ 7월 말\n🚩 수요일 오전에 회의록 쓸 것"
        _, stats = voice.screen(block)
        self.assertEqual(stats["blocks_dropped"], 0)


class TestProseGate(unittest.TestCase):
    def test_drops_pasted_logs(self):
        kept, stats = voice.prose_gate(LOGS)
        self.assertEqual(kept, "")
        self.assertEqual(stats["lines_kept"], 0)

    def test_keeps_korean_prose(self):
        kept, _ = voice.prose_gate(HUMAN)
        self.assertEqual(len(kept.splitlines()), 5)

    def test_keeps_mixed_line_with_enough_hangul(self):
        line = "192.168.50.126에서 snap 파일을 scp로 전송하였다"
        self.assertTrue(voice.is_prose(line))

    def test_rejects_line_with_a_stray_hangul_word(self):
        self.assertFalse(voice.is_prose("move_base_msgs, 참고"))


class TestClassifyEnding(unittest.TestCase):
    def test_categories(self):
        cases = {
            "이 값을 확인했습니다": "합니다체",
            "이 값을 확인했어요": "해요체",
            "이 값을 확인했음": "음슴체",
            "이 값을 확인한다": "평서-다",
            "이 값을 확인했어": "반말",
            "prev, curr 비교할것": "할것체",
            "센서 등 코가 쪽 세팅 확인 요망": "개조식",
        }
        for sentence, expected in cases.items():
            with self.subTest(sentence=sentence):
                self.assertEqual(voice.classify_ending(sentence), expected)

    def test_mieum_ending_covers_any_stem(self):
        # 낱말 목록으로는 못 잡는다. 종성만 본다.
        for sentence in ("안될 것들 넣어둠", "브릿지가 ACS연결 끊김", "위에서 안먹힘", "해야 함"):
            with self.subTest(sentence=sentence):
                self.assertEqual(voice.classify_ending(sentence), "음슴체")

    def test_mieum_nouns_are_not_verb_forms(self):
        for sentence in ("담당은 우리 팀", "이건 그냥 게임", "확인은 다음"):
            with self.subTest(sentence=sentence):
                self.assertNotEqual(voice.classify_ending(sentence), "음슴체")

    def test_trailing_punctuation_is_ignored(self):
        self.assertEqual(voice.classify_ending("정립된 것이 없음."), "음슴체")


class TestFingerprint(unittest.TestCase):
    def setUp(self):
        self.profile = voice.fingerprint(HUMAN * 20, "t", keep_vocabulary=False)

    def test_endings_are_a_distribution(self):
        self.assertAlmostEqual(sum(self.profile.endings.values()), 1.0, places=2)

    def test_dominant_register_is_detected(self):
        top = next(iter(self.profile.endings))
        self.assertIn(top, ("음슴체", "개조식"))

    def test_baseline_is_per_hundred_sentences(self):
        self.assertIsInstance(self.profile.baseline, dict)
        for rate in self.profile.baseline.values():
            self.assertGreater(rate, 0)

    def test_screening_reports_both_gates(self):
        self.assertIn("dropped_ratio", self.profile.screening)
        self.assertIn("prose", self.profile.screening)

    def test_vocabulary_is_opt_in(self):
        self.assertEqual(self.profile.vocabulary, {})
        self.assertNotIn("vocabulary", self.profile.as_dict())
        with_vocab = voice.fingerprint(HUMAN * 20, "t", keep_vocabulary=True)
        self.assertIn("vocabulary", with_vocab.as_dict())

    def test_empty_sample_does_not_crash(self):
        empty = voice.fingerprint("", "t", keep_vocabulary=False)
        self.assertEqual(empty.volume["sentences"], 0)
        self.assertEqual(empty.sentence_length["mean"], 0)

    def test_render_produces_the_sections_the_skill_reads(self):
        text = voice.render(self.profile)
        for heading in ("## 표본 선별", "## 문장 길이", "## 종결 유형", "## 개인 기준선"):
            self.assertIn(heading, text)


class TestApplyBaseline(unittest.TestCase):
    def _scan(self, text):
        return detect.scan(text, preset="general"), text

    def test_habitual_rule_is_softened(self):
        text = "또한 이건 확인함.\n" * 8
        result, source = self._scan(text)
        self.assertTrue(any(f.rule_id == "H-1" for f in result.findings))
        profile = {"baseline": {"H-1": 100.0}}
        softened = voice.apply_baseline(result, profile, source)
        self.assertIn("H-1", softened)
        self.assertEqual(
            next(f.severity for f in result.findings if f.rule_id == "H-1"), "S3"
        )

    def test_never_relaxed_rules_survive_any_baseline(self):
        text = "이건 진짜 좋음 — 확실함.\n"
        result, source = self._scan(text)
        profile = {"baseline": {rule: 999.0 for rule in presets.NEVER_RELAXED}}
        softened = voice.apply_baseline(result, profile, source)
        self.assertEqual(softened, [])
        self.assertTrue(any(f.rule_id == "J-2" and f.severity == "S1" for f in result.findings))

    def test_rule_above_baseline_stays(self):
        text = "또한 이건 확인함.\n" * 8
        result, source = self._scan(text)
        voice.apply_baseline(result, {"baseline": {"H-1": 0.01}}, source)
        self.assertEqual(
            next(f.severity for f in result.findings if f.rule_id == "H-1"), "S1"
        )

    def test_missing_profile_baseline_changes_nothing(self):
        text = "또한 이건 확인함.\n" * 8
        result, source = self._scan(text)
        self.assertEqual(voice.apply_baseline(result, {}, source), [])


class TestRawCounts(unittest.TestCase):
    def test_ignores_thresholds(self):
        counts = detect.raw_counts("이 문제에 대한 검토")
        self.assertEqual(counts["A-1"], 1)  # 임계값은 4회다

    def test_covers_every_rule(self):
        counts = detect.raw_counts("아무 글")
        self.assertEqual(set(counts), {rule.id for rule in detect.RULES})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
