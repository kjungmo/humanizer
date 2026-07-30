"""기계로 판정 가능한 한국어 AI 흔적을 결정론으로 탐지한다.

규칙 ID는 `packs/ko/core.md`의 표에 적힌 ID와 일치한다. 표에 스캐너 ID가 없는 패턴은
문맥 판단이 필요해서 일부러 구현하지 않았다. 이 모듈은 판정을 대신하지 않고
"몇 번 나왔는지"만 확정한다.

임계값(threshold)은 그 횟수 이상일 때 보고한다는 뜻이다. 심각도의 관용 범위를 담는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from . import metrics, presets

# ---------------------------------------------------------------------------
# 보호 구간 마스킹
# ---------------------------------------------------------------------------

_FENCE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
_INLINE_CODE = re.compile(r"`[^`\n]+`")
_URL = re.compile(r"https?://\S+|\b[\w.\-]+@[\w.\-]+\.\w+")
_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def _blank(match: re.Match) -> str:
    """길이와 줄바꿈을 보존한 채 내용만 지운다. 줄 번호가 밀리지 않는다."""
    return "".join("\n" if ch == "\n" else " " for ch in match.group(0))


def mask_protected(text: str) -> str:
    """코드블록·인라인코드·URL·프런트매터를 탐지 대상에서 제외한다.

    `SKILL.md`의 "절대 건드리지 않는 것" 중 기계로 가려낼 수 있는 것만 처리한다.
    고유명사와 직접 인용은 문맥이 필요해 여기서 가리지 않는다.
    """
    for pattern in (_FRONTMATTER, _FENCE, _INLINE_CODE, _URL):
        text = pattern.sub(_blank, text)
    return text


# ---------------------------------------------------------------------------
# 규칙 정의
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    id: str
    label: str
    severity: str
    threshold: int = 1
    pattern: Optional[re.Pattern] = None
    note: str = ""


def _rx(source: str, flags: int = 0) -> re.Pattern:
    return re.compile(source, flags)


HYPE = (
    "다채로운|풍부한|깊이 있는|진정한|궁극적으로|중추적인|필수적인|혁신적인|독보적인"
    "|파격적인|압도적인|획기적인|아우르(?:는|며|다)|녹여낸|녹여내|담아낸|담아내"
    "|선사하(?:는|며|다|였)|자리매김|발돋움|방증하|의 향연|각광받|눈길을 끌"
)

RULES: Tuple[Rule, ...] = (
    # --- A. 번역체 ---
    Rule("A-1", "'~에 대해/~에 대한' 남발", "S2", 4, _rx(r"에 대(?:해서?|한|하여)")),
    Rule("A-2", "'~를 통해' 남발", "S2", 3, _rx(r"(?:을|를) 통(?:해서?|하여)")),
    Rule("A-3", "'~에 있어(서)'", "S2", 1, _rx(r"에 있어(?:서)?")),
    Rule(
        "A-6",
        "명사화 과잉",
        "S2",
        3,
        _rx(r"의\s*(?:향상|개선|증대|확대|감소|저하|진행)|(?:을|를)\s*(?:수행|실시|도모|진행)"),
    ),
    Rule(
        "A-7",
        "'의미를/중요성을 가지다' 직역",
        "S1",
        1,
        _rx(
            r"(?:의미|중요성|영향력|가치|특징|장점|단점|가능성|잠재력|의의|한계|성격)"
            r"(?:를|을)?\s*가(?:지|진|집|져|지고)"
        ),
    ),
    # 활용형까지 잡는다. "되어지다"는 본문에 "되어진다·되어져·되어졌다"로 나타난다.
    Rule(
        "A-8",
        "이중피동",
        "S1",
        1,
        _rx(r"(?:되어|보여|불려|불리어|쓰여|씌여|나뉘어|짜여|모아)(?:지|진|져|졌|질)"),
    ),
    Rule("A-9", "'~에 의해' 피동", "S2", 3, _rx(r"에 의(?:해서?|하여)")),
    Rule("A-16", "'그/그것/그들' 대명사 강박", "S1", 1, note="단락당 3회 이상"),
    Rule(
        "A-17",
        "복수 접미사 '~들' 남발",
        "S2",
        5,
        _rx(r"[가-힣]들(?:에게|이|을|은|의|과|도|만|에)"),
    ),
    Rule(
        "A-19",
        "겹조사 '~에서의/~으로의'",
        "S2",
        1,
        _rx(r"에서의|으로부터의|로부터의|으로의|에게의|에의|(?<![가-힣])로의"),
    ),
    # --- B. 영어 병기 ---
    # 괄호 안이 전부 대문자·숫자면 표준 약어나 식별자다(Do-NOT 목록). 소문자 두 자 이상을 요구한다.
    Rule(
        "B-1",
        "괄호 영어 매번 병기",
        "S2",
        3,
        _rx(r"[가-힣]\s*\([A-Za-z0-9 .\-]{0,60}[a-z]{2}[A-Za-z0-9 .\-]{0,60}\)"),
    ),
    # --- C. 구조 ---
    Rule("C-5", "이모지 장식", "S1", 1, _rx(
        "[\U0001F000-\U0001FAFF☀-➿⬀-⯿️✅❌]"
    )),
    Rule(
        "C-7",
        "3의 법칙 (억지 3항 나열)",
        "S2",
        2,
        _rx(r"[가-힣]{2,}, [가-힣]{2,}, 그리고 [가-힣]{2,}|[가-힣]{2,}와 [가-힣]{2,}와 [가-힣]{2,}"),
    ),
    Rule("C-9", "숫자 괄호 인덱싱", "S2", 3, _rx(r"\([1-9]\)")),
    Rule("C-10", "콜론 부제 헤딩 반복", "S2", 2, _rx(r"(?m)^#{1,6}\s+\S.*:\s*\S")),
    # 한국어에서 긴 절을 잇는 "~고, "는 정상 문장부호다. 떡칠일 때만 흔적이다.
    Rule("C-11", "연결어미 직후 쉼표", "S1", 3, note="6회 이상이면 결정적"),
    # --- D. 관용구 ---
    Rule(
        "D-1",
        "결산 피벗 ('결론적으로')",
        "S1",
        1,
        _rx(r"결론적으로|요약하(?:면|자면)|정리하(?:면|자면)|종합하(?:면|자면)|끝으로,"),
    ),
    Rule(
        "D-2",
        "의의 상투구 ('시사하는 바가 크다')",
        "S1",
        1,
        _rx(r"시사하는 바가|주목할 만하다|주목할 만한|본질적으로|핵심적으로"),
    ),
    Rule("D-4", "hype 어휘", "S1", 3, _rx(HYPE)),
    Rule(
        "D-6",
        "결말 공식 ('~할 때다')",
        "S1",
        1,
        _rx(
            r"할 때다|해야 할 때|지금이야말로|귀추가 주목|무한한 가능성|밝은 미래"
            r"|기대를 모은다|행보가 기대|기대해 본다"
        ),
    ),
    Rule(
        "D-8",
        "과장된 의의 부여",
        "S1",
        1,
        _rx(
            r"중요한 이정표|한 획을 그|새로운 지평|의 산물|을 상징한다"
            r"|단순한 .{1,14}(?:이|가) 아니라|단순한 .{1,14}(?:을|를) 넘어"
        ),
    ),
    Rule(
        "D-9",
        "출처 없는 권위 호출",
        "S2",
        1,
        _rx(r"전문가들(?:은|이)|많은 사람들이|업계에서는|로 알려져 있다|라고 평가받"),
    ),
    # --- E. 리듬 ---
    Rule("E-1", "문장 길이 균일", "S2", 1, note="표준편차 8 미만, 5문장 이상"),
    Rule("E-2", "동일 종결어미 4문장 연속", "S2", 1),
    # --- F. 수식 ---
    Rule(
        "F-4",
        "-성/-적/-화 누적",
        "S2",
        12,
        _rx(r"적인|적\s|성(?:을|이|의)|화(?:를|가|의|에)"),
    ),
    # --- G. 완충 ---
    Rule(
        "G-3",
        "완충 표현 누적",
        "S2",
        4,
        _rx(
            r"수도 있다|수 있을 것이다|볼 수 있다|다소 |어느 정도|일정 부분"
            r"|장점도 있지만|신중하게|균형을"
        ),
    ),
    # --- H. 접속사 ---
    Rule("H-1", "문두 접속사 남발", "S1", 5),
    Rule(
        "H-3",
        "메타 진입 ('이는', '이 점에서')",
        "S1",
        3,
        _rx(r"이는 |이 점에서|이러한 점에서|이 관점에서|이와 관련하여"),
    ),
    # --- I. 형식명사 ---
    Rule("I-1", "'~인 것이다' 결말", "S1", 3, _rx(r"것이다\.|것입니다\.|것이었다\.")),
    Rule(
        "I-4",
        "설교조 당위 / 예고 멘트",
        "S2",
        1,
        _rx(
            r"것이 중요하다|할 필요가 있다|명심해야|유의해야"
            r"|살펴보(?:자|겠|기로)|알아보(?:자|겠)|들어가기에 앞서"
        ),
    ),
    # --- J. 시각 장식 ---
    Rule("J-1", "볼드 남용", "S2", 6, _rx(r"\*\*[^*\n]+\*\*")),
    Rule("J-2", "줄표(em/en dash)", "S1", 1, _rx(r"[—–]")),
    Rule("J-4", "곡선따옴표·물결표", "S3", 5, _rx(r"[“”‘’]|[가-힣]~(?=\s|$)")),
    # --- K. 챗봇 잔재 ---
    Rule(
        "K-1",
        "챗봇 잔재",
        "S1",
        1,
        _rx(
            r"물론이죠|물론입니다!|좋은 질문|훌륭한 지적|도움이 되(?:었|셨)으면"
            r"|더 궁금(?:한|하신)|무엇이든 물어보세요|기꺼이 도와|말씀해 주세요!"
        ),
    ),
)

RULES_BY_ID: Dict[str, Rule] = {rule.id: rule for rule in RULES}

SEVERITY_ORDER = {"S1": 0, "S2": 1, "S3": 2}


# ---------------------------------------------------------------------------
# 문맥이 필요한 규칙 (정규식 하나로 끝나지 않는 것들)
# ---------------------------------------------------------------------------

#: 문두 접속부사는 연결어미가 아니다. "하지만," 은 C-11이 아니다.
_CONJUNCTION_WORDS = frozenset(
    {
        "하지만", "그렇지만", "그러나", "그리고", "그런데", "다만", "반면", "또는",
        "혹은", "게다가", "더구나", "따라서", "왜냐하면", "만약", "아니면", "근데",
        "그러니까", "그러므로", "즉", "예를 들면", "이를테면",
    }
)

#: '고,' 로 끝나는 명사. "교통사고, 화재" 를 연결어미로 오해하지 않는다.
_NOUN_GO = frozenset(
    {
        "사고", "참고", "보고", "신고", "광고", "창고", "최고", "예고", "중고",
        "냉장고", "원고", "재고", "누고", "삼고", "회고", "경고", "권고", "충고",
    }
)

_CONJ_ENDING = re.compile(r"([가-힣]{2,})(?:고|으며|며|지만|면서|아서|어서|는데|으나)\s*,")

_SENTENCE_INITIAL = re.compile(
    r"(?:^|(?<=[.!?])\s|(?<=\n))\s*(또한|따라서|즉|나아가|아울러|게다가|더욱이"
    r"|더불어|한편|이처럼|무엇보다|그러므로)[,\s]"
)

_PRONOUN = re.compile(r"(?<![가-힣])(그|그녀|그것|그들|이것)(?:은|는|이|가|을|를|의|도)(?![가-힣])")


def _lines_of(text: str, offsets: List[int]) -> List[int]:
    starts = [0]
    for index, ch in enumerate(text):
        if ch == "\n":
            starts.append(index + 1)
    out = []
    for offset in offsets:
        low, high = 0, len(starts) - 1
        while low < high:
            mid = (low + high + 1) // 2
            if starts[mid] <= offset:
                low = mid
            else:
                high = mid - 1
        out.append(low + 1)
    return out


def _regex_hits(rule: Rule, text: str) -> Tuple[int, List[str], List[int]]:
    matches = list(rule.pattern.finditer(text))
    samples, offsets = [], []
    for match in matches:
        sample = match.group(0).strip()
        if sample and sample not in samples and len(samples) < 3:
            samples.append(sample)
        offsets.append(match.start())
    return len(matches), samples, _lines_of(text, offsets[:3])


def _hits_c11(text: str) -> Tuple[int, List[str], List[int]]:
    count, samples, offsets = 0, [], []
    for match in _CONJ_ENDING.finditer(text):
        stem = match.group(1)
        whole = match.group(0).rstrip().rstrip(",")
        if whole in _CONJUNCTION_WORDS or stem in _CONJUNCTION_WORDS:
            continue
        # "교통사고," 처럼 명사로 끝나면 연결어미가 아니다. 접미 일치로 본다.
        if any(whole.endswith(noun) for noun in _NOUN_GO):
            continue
        count += 1
        if len(samples) < 3:
            samples.append(match.group(0).strip())
        offsets.append(match.start())
    return count, samples, _lines_of(text, offsets[:3])


def _hits_h1(text: str) -> Tuple[int, List[str], List[int]]:
    matches = list(_SENTENCE_INITIAL.finditer(text))
    samples, offsets = [], []
    for match in matches:
        word = match.group(1)
        if word not in samples and len(samples) < 3:
            samples.append(word)
        offsets.append(match.start(1))
    return len(matches), samples, _lines_of(text, offsets[:3])


def _hits_a16(text: str) -> Tuple[int, List[str], List[int]]:
    """단락 단위로 센다. 한 단락에 3회 이상이면 그 단락의 초과분을 흔적으로 본다."""
    total, samples, offsets = 0, [], []
    cursor = 0
    for block in text.split("\n\n"):
        hits = list(_PRONOUN.finditer(block))
        if len(hits) >= 3:
            total += len(hits)
            for hit in hits:
                if hit.group(0) not in samples and len(samples) < 3:
                    samples.append(hit.group(0))
                offsets.append(cursor + hit.start())
        cursor += len(block) + 2
    return total, samples, _lines_of(text, offsets[:3])


def _hits_e1(text: str) -> Tuple[int, List[str], List[int]]:
    stats = metrics.sentence_stats(text)
    if stats.count >= 5 and stats.stdev < 8:
        return 1, [f"문장 {stats.count}개, 표준편차 {stats.stdev:.1f}"], [1]
    return 0, [], []


def _hits_e2(text: str) -> Tuple[int, List[str], List[int]]:
    endings = []
    for sentence in metrics.split_sentences(text):
        stripped = sentence.rstrip(".!?…\"')」』 ")
        tail = stripped[-2:] if len(stripped) >= 2 else stripped
        endings.append(tail)
    runs, samples = 0, []
    index = 0
    while index < len(endings):
        run = 1
        while index + run < len(endings) and endings[index + run] == endings[index]:
            run += 1
        if run >= 4 and endings[index]:
            runs += 1
            if len(samples) < 3:
                samples.append(f"'{endings[index]}' {run}문장 연속")
        index += run
    return runs, samples, [1] if runs else []


CUSTOM: Dict[str, Callable[[str], Tuple[int, List[str], List[int]]]] = {
    "A-16": _hits_a16,
    "C-11": _hits_c11,
    "E-1": _hits_e1,
    "E-2": _hits_e2,
    "H-1": _hits_h1,
}


# ---------------------------------------------------------------------------
# 결과
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    rule_id: str
    label: str
    severity: str
    count: int
    samples: List[str] = field(default_factory=list)
    lines: List[int] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "id": self.rule_id,
            "label": self.label,
            "severity": self.severity,
            "count": self.count,
            "samples": self.samples,
            "lines": self.lines,
        }


@dataclass
class ScanResult:
    preset: str
    findings: List[Finding] = field(default_factory=list)
    relaxed: List[str] = field(default_factory=list)

    def by_severity(self, severity: str) -> List[Finding]:
        return [f for f in self.findings if f.severity == severity]

    @property
    def s1(self) -> List[Finding]:
        return self.by_severity("S1")

    @property
    def counts(self) -> Dict[str, int]:
        return {s: len(self.by_severity(s)) for s in ("S1", "S2", "S3")}

    def as_dict(self) -> dict:
        return {
            "preset": self.preset,
            "counts": self.counts,
            "relaxed": self.relaxed,
            "findings": [f.as_dict() for f in self.findings],
        }


def raw_counts(text: str) -> Dict[str, int]:
    """규칙별 원시 발생 수. 임계값도 프리셋 완화도 적용하지 않는다.

    말투 프로필이 개인 기준선을 잡을 때 쓴다. "이 사람은 문두 접속사를
    100문장당 몇 번 쓰는가"를 알려면 임계값을 넘겼는지가 아니라 날것의 수가 필요하다.
    """
    masked = mask_protected(text)
    counts: Dict[str, int] = {}
    for rule in RULES:
        handler = CUSTOM.get(rule.id)
        if handler is not None:
            count, _, _ = handler(masked)
        elif rule.pattern is not None:
            count, _, _ = _regex_hits(rule, masked)
        else:  # pragma: no cover - 규칙 표 실수 방어
            raise RuntimeError(f"규칙 {rule.id}에 패턴도 핸들러도 없습니다")
        counts[rule.id] = count
    return counts


def scan(text: str, preset: str = presets.DEFAULT) -> ScanResult:
    """프리셋을 반영해 흔적을 센다. 완화된 규칙은 아예 보고하지 않는다."""
    relax = presets.relaxed(preset)
    masked = mask_protected(text)
    findings: List[Finding] = []

    for rule in RULES:
        if rule.id in relax:
            continue
        handler = CUSTOM.get(rule.id)
        if handler is not None:
            count, samples, lines = handler(masked)
        elif rule.pattern is not None:
            count, samples, lines = _regex_hits(rule, masked)
        else:  # pragma: no cover - 규칙 표 실수 방어
            raise RuntimeError(f"규칙 {rule.id}에 패턴도 핸들러도 없습니다")
        if count >= rule.threshold:
            findings.append(Finding(rule.id, rule.label, rule.severity, count, samples, lines))

    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], -f.count, f.rule_id))
    return ScanResult(preset=preset, findings=findings, relaxed=sorted(relax))
