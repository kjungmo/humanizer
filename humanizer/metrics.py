"""글자수·문장 리듬·변경률을 결정론으로 계량한다.

한국어 분량 판정에서 `len(text)`는 두 군데서 틀린다.
결합 자모(U+1160 계열)와 이모지 ZWJ 연쇄가 사람이 세는 "한 글자"와 어긋난다.
여기서는 자소 묶음(grapheme cluster)을 근사해 센다.
"""

from __future__ import annotations

import difflib
import re
import statistics
import unicodedata
from dataclasses import dataclass
from typing import List

ZWJ = "‍"
_JOINING = {"Mn", "Me", "Mc", "Cf"}
_VARIATION = range(0xFE00, 0xFE10)


def graphemes(text: str) -> List[str]:
    """자소 묶음 근사. 결합 표시와 ZWJ 연쇄를 앞 글자에 붙인다.

    먼저 NFC로 정규화한다. macOS에서 복사한 한국어는 자모가 분해된(NFD) 상태로
    오는 경우가 많고, 그대로 세면 "각"이 세 글자로 잡힌다.
    """
    text = unicodedata.normalize("NFC", text)
    clusters: List[str] = []
    for ch in text:
        if not clusters:
            clusters.append(ch)
            continue
        prev = clusters[-1]
        if (
            unicodedata.category(ch) in _JOINING
            or ord(ch) in _VARIATION
            or prev.endswith(ZWJ)
        ):
            clusters[-1] = prev + ch
        else:
            clusters.append(ch)
    return clusters


def char_count(text: str, include_spaces: bool = True) -> int:
    clusters = graphemes(text)
    if include_spaces:
        return len(clusters)
    return len([c for c in clusters if not c.strip() == ""])


_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+|\n{2,}")
_DECIMAL = re.compile(r"\d\.\d")
_DROP_LINE = re.compile(r"(?m)^\s*(?:\|.*|#{1,6}\s+.*|-{3,}|={3,}|`{3,}.*)$")
_LINE_MARKER = re.compile(r"(?m)^\s{0,3}(?:>\s?|[-*+]\s+|\d+\.\s+)")


def prose_only(text: str) -> str:
    """표·헤딩·구분선을 걷어낸 산문만 남긴다.

    문장 리듬(E-1)과 종결어미 반복(E-2)은 산문에만 의미가 있다.
    마크다운 표의 셀 구분자를 문장으로 세면 표준편차가 엉뚱해진다.
    """
    text = _DROP_LINE.sub("", text)
    return _LINE_MARKER.sub("", text)


def split_sentences(text: str) -> List[str]:
    """문장 분할. 소수점과 마크다운 서식을 문장 끝으로 오해하지 않는다."""
    protected = _DECIMAL.sub(lambda m: m.group(0).replace(".", "\x00"), prose_only(text))
    parts = [p.strip() for p in _SENTENCE_END.split(protected)]
    out: List[str] = []
    for part in parts:
        part = part.replace("\x00", ".")
        for line in part.split("\n"):
            line = line.strip()
            if line:
                out.append(line)
    return out


@dataclass
class SentenceStats:
    count: int
    mean: float
    stdev: float
    shortest: int
    longest: int

    def as_dict(self) -> dict:
        return {
            "count": self.count,
            "mean": round(self.mean, 1),
            "stdev": round(self.stdev, 1),
            "shortest": self.shortest,
            "longest": self.longest,
        }


def sentence_stats(text: str) -> SentenceStats:
    lengths = [char_count(s) for s in split_sentences(text)]
    if not lengths:
        return SentenceStats(0, 0.0, 0.0, 0, 0)
    stdev = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
    return SentenceStats(
        count=len(lengths),
        mean=statistics.fmean(lengths),
        stdev=stdev,
        shortest=min(lengths),
        longest=max(lengths),
    )


def change_rate(before: str, after: str) -> float:
    """0.0~1.0. 자소 단위 유사도의 여집합이다.

    변경률 30%는 "글자 열 개 중 세 개가 달라졌다"에 가까운 값으로 읽는다.
    """
    a, b = graphemes(before), graphemes(after)
    if not a and not b:
        return 0.0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return round(1.0 - ratio, 4)


def within_budget(text: str, target: int, tolerance: float = 0.05) -> bool:
    count = char_count(text)
    return abs(count - target) <= target * tolerance


def report(text: str, target: int = None) -> dict:
    stats = sentence_stats(text)
    data = {
        "chars_with_spaces": char_count(text),
        "chars_without_spaces": char_count(text, include_spaces=False),
        "sentences": stats.as_dict(),
    }
    if target is not None:
        count = data["chars_with_spaces"]
        data["target"] = target
        data["delta"] = count - target
        data["within_5pct"] = within_budget(text, target, 0.05)
        data["within_2pct"] = within_budget(text, target, 0.02)
    return data
