"""개인 말투 프로필.

`SKILL.md` 9절은 "표본이 있으면 표본이 스킬 규칙을 이긴다"고 선언한다.
그런데 그 표본을 매번 사람이 붙여 넣어야 했다. 여기서는 한 번 재서 파일로 남긴다.

핵심 문제는 표본 오염이다. 요즘 메모장에는 AI가 쓴 요약이 섞여 있다.
그걸 그대로 재면 그 사람 말투가 아니라 AI 말투를 학습한다. 흔적을 지우려고
만든 도구가 흔적을 정답으로 배우는 셈이다. 그래서 프로파일러는 계량에 앞서
자기 탐지기를 표본에 돌려 AI가 쓴 덩어리를 먼저 버린다.

산출물은 두 개다. 기계가 읽는 `<이름>.json`과 사람이 읽는 `<이름>.md`.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import detect, metrics, presets

# ---------------------------------------------------------------------------
# 표본 청소
# ---------------------------------------------------------------------------

_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_TAG = re.compile(r"</?[a-zA-Z][^>\n]*/?>")
_ATTR = re.compile(r"\{[a-z_]+=\"[^\"]*\"\}")
_URL_LINE = re.compile(r"(?m)^\s*<?https?://\S+>?\s*$")
_ESCAPE = re.compile(r"\\([~`*_\[\]()#+\-.!])")


def clean_sample(text: str) -> str:
    """내보내기 부산물을 걷어내고 사람이 친 글자만 남긴다.

    Notion·Obsidian·Bear에서 내보낸 마크다운에는 첨부 태그, 토글 속성,
    역슬래시 이스케이프가 섞여 들어온다. 이걸 문장으로 세면 통계가 망가진다.
    """
    text = _IMAGE.sub("", text)
    text = _TAG.sub("", text)
    text = _ATTR.sub("", text)
    text = _URL_LINE.sub("", text)
    text = _ESCAPE.sub(r"\1", text)
    return text


# ---------------------------------------------------------------------------
# 오염 선별
# ---------------------------------------------------------------------------

# 개인 메모에는 거의 나오지 않고 생성기에는 흔한 흔적들.
# 가중치 합이 DROP_AT 이상이면 그 덩어리를 표본에서 뺀다.
#
# 일부러 뺀 규칙이 있다. C-5 이모지와 J-4 물결표는 사람이 메모에 즐겨 쓰고,
# A-8 이중피동은 한국인이 자연스럽게 쓰는 번역체라 오염 신호가 되지 못한다.
# 여기 목록은 "사람이 쓸 리 없는 것"만 담는다.
AI_SIGNATURES: Dict[str, float] = {
    "J-2": 1.0,  # 줄표. 한국어 자판으로는 나오지 않는다
    "K-1": 1.0,  # 챗봇 응대 잔재
    "D-1": 1.0,  # 결산 피벗
    "D-2": 1.0,  # 의의 상투구
    "D-6": 1.0,  # 결말 공식
    "D-8": 1.0,  # 과장된 의의
    "I-1": 0.5,  # '~인 것이다' 결말
    "D-4": 0.5,  # hype 어휘
    "H-3": 0.5,  # 메타 진입
}

DROP_AT = 1.0
_MAX_BLOCK_LINES = 20

# 이보다 적은 문장으로 뜬 분포는 믿을 수 없다. 표본을 더 넣어야 한다.
MIN_SENTENCES = 200


def split_blocks(text: str) -> List[Tuple[int, str]]:
    """빈 줄로 나누어 오염 판정 단위를 만든다.

    글 전체를 한 번에 판정하면 AI가 쓴 한 문단 때문에 표본 전체를 버리게 된다.
    반대로 한 줄씩 보면 문맥이 없어 판정이 흔들린다. 그 사이를 잡는다.
    """
    blocks: List[Tuple[int, str]] = []
    current: List[str] = []
    start = 1
    for lineno, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            if not current:
                start = lineno
            current.append(line)
            if len(current) >= _MAX_BLOCK_LINES:
                blocks.append((start, "\n".join(current)))
                current = []
        elif current:
            blocks.append((start, "\n".join(current)))
            current = []
    if current:
        blocks.append((start, "\n".join(current)))
    return blocks


def contamination(block: str) -> Tuple[float, List[str]]:
    """덩어리 하나의 오염 점수와 근거 규칙을 낸다."""
    counts = detect.raw_counts(block)
    score = 0.0
    reasons: List[str] = []
    for rule_id, weight in AI_SIGNATURES.items():
        hits = counts.get(rule_id, 0)
        if hits:
            score += weight * hits
            reasons.append(rule_id)
    return score, sorted(reasons)


def screen(text: str) -> Tuple[str, dict]:
    """AI가 쓴 것으로 보이는 덩어리를 표본에서 뺀다."""
    blocks = split_blocks(text)
    kept: List[str] = []
    dropped_chars = 0
    kept_chars = 0
    by_rule: Dict[str, int] = {}

    for _, block in blocks:
        score, reasons = contamination(block)
        size = len(block)
        if score >= DROP_AT:
            dropped_chars += size
            for rule_id in reasons:
                by_rule[rule_id] = by_rule.get(rule_id, 0) + 1
        else:
            kept_chars += size
            kept.append(block)

    total = kept_chars + dropped_chars
    stats = {
        "blocks": len(blocks),
        "blocks_kept": len(kept),
        "blocks_dropped": len(blocks) - len(kept),
        "chars_kept": kept_chars,
        "chars_dropped": dropped_chars,
        "dropped_ratio": round(dropped_chars / total, 4) if total else 0.0,
        "dropped_by_rule": dict(sorted(by_rule.items(), key=lambda kv: -kv[1])),
    }
    return "\n\n".join(kept), stats


# ---------------------------------------------------------------------------
# 산문 게이트
# ---------------------------------------------------------------------------

MIN_HANGUL_CHARS = 4
MIN_HANGUL_RATIO = 0.25


def _hangul_count(line: str) -> int:
    return sum(1 for ch in line if "가" <= ch <= "힣")


def is_prose(line: str) -> bool:
    """사람이 한국어로 쓴 줄인지 본다.

    개발자 메모장의 절반은 붙여넣은 로그와 셸 출력이다. 그걸 문장으로 세면
    종결 유형이 전부 '개조식'으로 뭉개지고 문장 길이 분포도 엉뚱해진다.
    한글이 일정 비율 이상인 줄만 말투의 근거로 삼는다.
    """
    stripped = "".join(line.split())
    if not stripped:
        return False
    hangul = _hangul_count(stripped)
    if hangul < MIN_HANGUL_CHARS:
        return False
    return hangul / len(stripped) >= MIN_HANGUL_RATIO


def prose_gate(text: str) -> Tuple[str, dict]:
    """로그·경로·설정 덤프를 걷어내고 사람이 쓴 줄만 남긴다."""
    lines = [line for line in text.splitlines() if line.strip()]
    kept = [line for line in lines if is_prose(line)]
    stats = {
        "lines": len(lines),
        "lines_kept": len(kept),
        "dropped_ratio": round(1 - len(kept) / len(lines), 4) if lines else 0.0,
    }
    return "\n".join(kept), stats


# ---------------------------------------------------------------------------
# 종결 유형
# ---------------------------------------------------------------------------

_TRAILING = re.compile(r"[\s.!?…·:;)\]\"'’”~,]+$")

# ㅁ 받침으로 끝나지만 명사인 낱말. 음슴체로 오인하지 않는다.
#
# 두 갈래로 나눈 이유가 있다. '김'을 접미사로 막으면 '끊김'까지 막힌다.
# 한 음절짜리는 낱말 전체가 일치할 때만 막고, 여러 음절짜리만 접미사로 막는다.
_NOUN_M_EXACT = frozenset(
    ("팀", "힘", "밤", "꿈", "삶", "몸", "김", "홈", "램", "컴", "폼", "룸",
     "심", "점", "금", "담", "남", "섬", "봄", "곰", "감", "잠", "춤", "숨")
)
_NOUN_M_SUFFIX = (
    "게임", "시스템", "프로그램", "알고리즘", "플랫폼", "마음", "처음", "다음",
    "사람", "이름", "그림", "아침", "점심", "저녁", "여름", "겨울", "느낌",
)


def _is_noun_m(tail: str) -> bool:
    last = tail.split()[-1] if tail.split() else tail
    if last in _NOUN_M_EXACT:
        return True
    return any(last.endswith(noun) for noun in _NOUN_M_SUFFIX)

_MIEUM = 16  # 한글 종성 인덱스에서 ㅁ의 자리


def _ends_with_mieum(tail: str) -> bool:
    """마지막 글자가 ㅁ 받침인지 본다.

    음슴체의 낱말 목록을 손으로 다 적을 수는 없다. '넣어둠'·'물림'·'안먹힘'처럼
    어간에 따라 앞 글자가 무한히 바뀐다. 받침만 보면 전부 잡힌다.
    """
    ch = tail[-1]
    if not ("가" <= ch <= "힣"):
        return False
    return (ord(ch) - 0xAC00) % 28 == _MIEUM


_ENDING_TESTS: Sequence[Tuple[str, "re.Pattern"]] = (
    ("합니다체", re.compile(r"(?:습니다|입니다|십시오|읍시다|습니까|랍니다|됩니다|합니다)$")),
    ("해요체", re.compile(r"(?:아요|어요|여요|해요|에요|예요|세요|께요|네요|나요|까요|는데요|군요|지요|죠)$")),
    ("평서-다", re.compile(r"[가-힣]다$")),
    ("반말", re.compile(r"(?:았어|었어|했어|이야|거야|더라|거든|잖아|는걸|자|네|야)$")),
    ("할것체", re.compile(r"(?:것|것들|거)$")),
)


def classify_ending(sentence: str) -> str:
    """문장 하나의 종결 유형. 어디에도 안 걸리면 개조식으로 본다."""
    tail = _TRAILING.sub("", sentence)
    if not tail:
        return "개조식"
    if _ends_with_mieum(tail) and not _is_noun_m(tail):
        return "음슴체"
    for name, pattern in _ENDING_TESTS:
        if pattern.search(tail):
            return name
    return "개조식"


# ---------------------------------------------------------------------------
# 습관 어휘
# ---------------------------------------------------------------------------

DISCOURSE_MARKERS = (
    "근데", "그런데", "그래서", "그리고", "하지만", "그러나", "다만", "일단",
    "약간", "되게", "암튼", "아무튼", "그냥", "진짜", "좀", "결국", "사실",
    "아마", "혹시", "이제", "우선", "참고로", "따라서", "또한", "즉", "물론",
)

_PUNCTUATION = {
    "쉼표": ",",
    "물음표": "?",
    "느낌표": "!",
    "물결표": "~",
    "화살표": "→",
    "줄표": "—",
    "말줄임": "…",
}

_WORD = re.compile(r"[0-9A-Za-z가-힣][0-9A-Za-z가-힣._/-]*")
_ENGLISH = re.compile(r"^[A-Za-z][A-Za-z0-9._/-]*$")
_NUMERIC = re.compile(r"^[0-9][0-9.,/-]*$")
_BULLET = re.compile(r"^(\s*)(?:[-*+]|\d+\.)\s+")


def _percentile(values: List[int], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * q
    low = int(k)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return float(ordered[low])
    return ordered[low] + (ordered[high] - ordered[low]) * (k - low)


def _ratios(counter: Dict[str, int], total: int) -> Dict[str, float]:
    if not total:
        return {}
    return {
        key: round(value / total, 4)
        for key, value in sorted(counter.items(), key=lambda kv: -kv[1])
    }


# ---------------------------------------------------------------------------
# 프로필
# ---------------------------------------------------------------------------


@dataclass
class VoiceProfile:
    name: str
    screening: dict
    volume: dict
    sentence_length: dict
    endings: dict
    punctuation: dict
    markers: dict
    tokens: dict
    structure: dict
    baseline: dict
    vocabulary: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        data = {
            "name": self.name,
            "screening": self.screening,
            "volume": self.volume,
            "sentence_length": self.sentence_length,
            "endings": self.endings,
            "punctuation": self.punctuation,
            "markers": self.markers,
            "tokens": self.tokens,
            "structure": self.structure,
            "baseline": self.baseline,
        }
        if self.vocabulary:
            data["vocabulary"] = self.vocabulary
        return data


def fingerprint(text: str, name: str, keep_vocabulary: bool = True) -> VoiceProfile:
    """표본에서 결정론 지문을 뽑는다."""
    cleaned = clean_sample(text)
    screened, screening = screen(cleaned)
    kept, gating = prose_gate(screened)
    screening["prose"] = gating

    sentences = metrics.split_sentences(kept)
    lengths = [metrics.char_count(s) for s in sentences]
    total_sentences = len(sentences)

    # 문장 길이. AI 글은 평균이 아니라 편차로 들킨다.
    if lengths:
        mean = statistics.fmean(lengths)
        stdev = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
    else:
        mean = stdev = 0.0
    sentence_length = {
        "mean": round(mean, 1),
        "stdev": round(stdev, 1),
        "cv": round(stdev / mean, 3) if mean else 0.0,
        "p10": round(_percentile(lengths, 0.10), 1),
        "p50": round(_percentile(lengths, 0.50), 1),
        "p90": round(_percentile(lengths, 0.90), 1),
        "shortest": min(lengths) if lengths else 0,
        "longest": max(lengths) if lengths else 0,
    }

    endings: Dict[str, int] = {}
    for sentence in sentences:
        kind = classify_ending(sentence)
        endings[kind] = endings.get(kind, 0) + 1

    per_100 = (100.0 / total_sentences) if total_sentences else 0.0
    punctuation = {
        label: round(kept.count(mark) * per_100, 1)
        for label, mark in _PUNCTUATION.items()
    }
    marker_counts: Dict[str, int] = {}
    for sentence in sentences:
        head = sentence.lstrip()
        for marker in DISCOURSE_MARKERS:
            if head.startswith(marker):
                marker_counts[marker] = marker_counts.get(marker, 0) + 1
                break
    markers = {
        marker: round(count * per_100, 2)
        for marker, count in sorted(marker_counts.items(), key=lambda kv: -kv[1])
    }

    words = _WORD.findall(kept)
    english = [w for w in words if _ENGLISH.match(w)]
    numeric = [w for w in words if _NUMERIC.match(w)]
    tokens = {
        "words": len(words),
        "english_ratio": round(len(english) / len(words), 4) if words else 0.0,
        "numeric_ratio": round(len(numeric) / len(words), 4) if words else 0.0,
    }

    lines = [line for line in kept.splitlines() if line.strip()]
    bullets = [line for line in lines if _BULLET.match(line)]
    depths = [len(_BULLET.match(line).group(1).expandtabs(4)) // 4 for line in bullets]
    structure = {
        "lines": len(lines),
        "bullet_ratio": round(len(bullets) / len(lines), 4) if lines else 0.0,
        "mean_indent_depth": round(statistics.fmean(depths), 2) if depths else 0.0,
        "max_indent_depth": max(depths) if depths else 0,
    }

    raw = detect.raw_counts(kept)
    baseline = {
        rule_id: round(count * per_100, 2)
        for rule_id, count in sorted(raw.items())
        if count
    }

    vocabulary: Dict[str, list] = {}
    if keep_vocabulary:
        vocabulary = {
            "korean": _top_words([w for w in words if _has_hangul(w)], 25),
            "english": _top_words([w.lower() for w in english], 25),
        }

    return VoiceProfile(
        name=name,
        screening=screening,
        volume={
            "chars": metrics.char_count(kept),
            "sentences": total_sentences,
            "blocks": screening["blocks_kept"],
        },
        sentence_length=sentence_length,
        endings=_ratios(endings, total_sentences),
        punctuation=punctuation,
        markers=markers,
        tokens=tokens,
        structure=structure,
        baseline=baseline,
        vocabulary=vocabulary,
    )


def _has_hangul(word: str) -> bool:
    return any("\uac00" <= ch <= "\ud7a3" for ch in word)


def _top_words(words: Sequence[str], limit: int) -> list:
    counter: Dict[str, int] = {}
    for word in words:
        if len(word) < 2:
            continue
        counter[word] = counter.get(word, 0) + 1
    ranked = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    return [[word, count] for word, count in ranked[:limit]]


# ---------------------------------------------------------------------------
# 개인 기준선 적용
# ---------------------------------------------------------------------------

BASELINE_TOLERANCE = 1.5


def apply_baseline(
    result: detect.ScanResult, profile: dict, text: str
) -> List[str]:
    """그 사람이 평소 쓰는 만큼이면 흔적으로 세지 않는다.

    문두 접속사를 원래 많이 쓰는 사람에게 H-1을 들이대면 그 사람 말투를 지운다.
    개인 기준선의 1.5배를 넘을 때만 흔적으로 본다.
    줄표·hype·챗봇 잔재는 예외 없이 그대로 둔다. 그건 누구의 말투도 아니다.
    """
    baseline = profile.get("baseline", {})
    sentences = len(metrics.split_sentences(text)) or 1
    softened: List[str] = []

    for finding in result.findings:
        if finding.rule_id in presets.NEVER_RELAXED:
            continue
        base = baseline.get(finding.rule_id)
        if not base:
            continue
        rate = finding.count * 100.0 / sentences
        if rate <= base * BASELINE_TOLERANCE:
            finding.severity = "S3"
            finding.label += " (개인 기준선 이내)"
            softened.append(finding.rule_id)

    result.findings.sort(
        key=lambda f: (detect.SEVERITY_ORDER[f.severity], -f.count, f.rule_id)
    )
    return softened


# ---------------------------------------------------------------------------
# 사람이 읽는 산출물
# ---------------------------------------------------------------------------


def render(profile: VoiceProfile) -> str:
    """스킬 9절 Voice Calibration에 그대로 물릴 수 있는 요약을 만든다."""
    p = profile
    lines: List[str] = []
    add = lines.append

    add("# 말투 프로필: {}".format(p.name))
    add("")
    add(
        "표본 {:,}자 · 문장 {:,}개. `python3 -m humanizer profile`이 재서 만들었다. "
        "손으로 고치지 말고 표본을 늘려 다시 뜬다.".format(
            p.volume["chars"], p.volume["sentences"]
        )
    )
    add("")

    s = p.screening
    add("## 표본 선별")
    add("")
    add(
        "덩어리 {:,}개 중 {:,}개를 AI가 쓴 것으로 보고 버렸다 (글자 기준 {:.1%}).".format(
            s["blocks"], s["blocks_dropped"], s["dropped_ratio"]
        )
    )
    if s["dropped_by_rule"]:
        reasons = ", ".join(
            "{} {}회".format(rule, count) for rule, count in s["dropped_by_rule"].items()
        )
        add("")
        add("버린 근거: {}".format(reasons))
    add("")

    sl = p.sentence_length
    add("## 문장 길이")
    add("")
    add("| 평균 | 표준편차 | 변동계수 | p10 | p50 | p90 | 최장 |")
    add("|---|---|---|---|---|---|---|")
    add(
        "| {}자 | {} | {} | {} | {} | {} | {}자 |".format(
            sl["mean"], sl["stdev"], sl["cv"], sl["p10"], sl["p50"], sl["p90"], sl["longest"]
        )
    )
    add("")
    add(
        "변동계수가 클수록 사람 글이다. AI 글은 문장을 고르게 뽑아 이 값이 작다."
    )
    add("")

    add("## 종결 유형")
    add("")
    add("| 유형 | 비율 |")
    add("|---|---|")
    for kind, ratio in p.endings.items():
        add("| {} | {:.1%} |".format(kind, ratio))
    add("")

    add("## 문장부호 습관 (100문장당)")
    add("")
    add("| 부호 | 횟수 |")
    add("|---|---|")
    for label, value in p.punctuation.items():
        add("| {} | {} |".format(label, value))
    add("")

    if p.markers:
        add("## 문두 입버릇 (100문장당)")
        add("")
        add(
            ", ".join(
                "{} {}".format(marker, value) for marker, value in list(p.markers.items())[:12]
            )
        )
        add("")

    st = p.structure
    add("## 구조와 표기")
    add("")
    add("- 불릿 줄 비율 {:.1%}, 평균 들여쓰기 깊이 {}".format(st["bullet_ratio"], st["mean_indent_depth"]))
    add("- 영문 어절 {:.1%}, 숫자 어절 {:.1%}".format(p.tokens["english_ratio"], p.tokens["numeric_ratio"]))
    add("")

    add("## 개인 기준선 (100문장당 규칙 발생률)")
    add("")
    add(
        "이 사람 글에서 원래 이 정도 나온다는 뜻이다. `detect --voice`가 "
        "이 값의 {}배까지는 흔적으로 세지 않는다. "
        "줄표(J-2)·hype(D-4)·챗봇 잔재(K-1)는 예외 없이 흔적이다.".format(BASELINE_TOLERANCE)
    )
    add("")
    add("| 규칙 | 100문장당 |")
    add("|---|---|")
    for rule_id, rate in sorted(p.baseline.items(), key=lambda kv: -kv[1]):
        label = detect.RULES_BY_ID[rule_id].label if rule_id in detect.RULES_BY_ID else ""
        add("| {} {} | {} |".format(rule_id, label, rate))
    add("")

    if p.vocabulary:
        add("## 자주 쓰는 낱말")
        add("")
        for key, title in (("korean", "한국어"), ("english", "영문")):
            entries = p.vocabulary.get(key) or []
            if entries:
                add(
                    "- {}: {}".format(
                        title, ", ".join("{}({})".format(w, c) for w, c in entries[:20])
                    )
                )
        add("")

    return "\n".join(lines) + "\n"
