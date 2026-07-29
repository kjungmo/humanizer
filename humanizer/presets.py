"""채널 프리셋 레지스트리.

각 프리셋은 다이얼(어투·분량·이모지·해시태그)과 완화 집합(relax)을 선언한다.
완화 집합에 든 규칙 ID는 그 프리셋에서 흔적으로 세지 않는다.

이 표는 `packs/ko/core.md`의 "완화" 열과 반드시 일치해야 한다.
둘이 어긋나면 스캐너와 프롬프트가 다른 말을 하게 된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Optional


@dataclass(frozen=True)
class Preset:
    id: str
    label: str
    register: str
    char_min: Optional[int]
    char_max: Optional[int]
    emoji: str
    hashtags: str
    structure: str
    guard: str
    relax: FrozenSet[str] = field(default_factory=frozenset)
    pack: Optional[str] = None
    enforce: tuple = ()

    @property
    def budget(self) -> str:
        if self.char_min is None and self.char_max is None:
            return "원문 ±5%"
        if self.char_max is None:
            return f"{self.char_min:,}자 이상"
        if self.char_min is None:
            return f"{self.char_max:,}자 이내"
        return f"{self.char_min:,}~{self.char_max:,}자"


_GENERAL = Preset(
    id="general",
    label="일반 한국어",
    register="원문 유지",
    char_min=None,
    char_max=None,
    emoji="금지",
    hashtags="다루지 않음",
    structure="원문 유지",
    guard="change-rate",
    relax=frozenset(),
    pack="packs/ko/presets/general.md",
    enforce=("장르 유지", "격식 유지", "1인칭 임의 추가 금지"),
)

_NAVER_BLOG = Preset(
    id="naver-blog",
    label="네이버 블로그 글",
    register="해요체",
    char_min=1000,
    char_max=2000,
    emoji="문단 끝 1~2개",
    hashtags="본문 밖 5~10개",
    structure="짧은 문단 + 소제목",
    guard="change-rate",
    relax=frozenset({"C-5", "C-9", "C-10", "E-2", "J-1"}),
    pack=None,
    enforce=("핵심어 자연 반복 3~5회", "사진 삽입 지점 표시", "1인칭 체험 근거"),
)

_DEV_BLOG = Preset(
    id="dev-blog",
    label="개발자 블로그 글",
    register="합니다체",
    char_min=None,
    char_max=None,
    emoji="금지",
    hashtags="없음",
    structure="소제목 + 코드블록",
    guard="change-rate",
    relax=frozenset({"B-1", "C-9", "C-10", "J-1"}),
    pack=None,
    enforce=("코드·명령어·버전 문자열 무변경", "재현 절차", "근거 링크 자리"),
)

_IG_POST = Preset(
    id="instagram-post",
    label="인스타 게시글",
    register="해요체 또는 반말",
    char_min=300,
    char_max=700,
    emoji="자유",
    hashtags="마지막 줄 10~20개",
    structure="1~2문장마다 줄바꿈",
    guard="fact-ledger",
    relax=frozenset({"A-16", "C-5", "E-1", "E-2", "J-1", "J-4"}),
    pack=None,
    enforce=("첫 2줄 안에 훅", "마지막 CTA 한 줄"),
)

_IG_REELS = Preset(
    id="instagram-reels",
    label="인스타 릴스 대본",
    register="반말·음슴체",
    char_min=200,
    char_max=500,
    emoji="대본엔 최소",
    hashtags="캡션 블록에만",
    structure="씬 번호 + 자막 줄",
    guard="fact-ledger",
    relax=frozenset({"A-16", "C-5", "E-1", "E-2", "J-1", "J-4"}),
    pack=None,
    enforce=("0~3초 훅 필수", "자막 한 줄 12자 이내", "구어 축약"),
)

_IG_COMMENT = Preset(
    id="instagram-comment",
    label="인스타 댓글",
    register="짧은 반말·해요체",
    char_min=None,
    char_max=40,
    emoji="1~2개",
    hashtags="금지",
    structure="한 줄",
    guard="fact-ledger",
    relax=frozenset({"A-16", "B-1", "C-5", "E-1", "E-2", "J-1", "J-4"}),
    pack=None,
    enforce=("상대 언급 1회", "공감 또는 질문 1개", "광고 티 금지"),
)

PRESETS = {
    p.id: p
    for p in (_GENERAL, _NAVER_BLOG, _DEV_BLOG, _IG_POST, _IG_REELS, _IG_COMMENT)
}

DEFAULT = "general"

#: 줄표와 챗봇 잔재는 어느 프리셋에서도 완화되지 않는다.
NEVER_RELAXED = frozenset({"J-2", "K-1", "D-4"})


def ids() -> list:
    return list(PRESETS)


def get(preset_id: str) -> Preset:
    try:
        return PRESETS[preset_id]
    except KeyError:
        raise KeyError(
            f"모르는 프리셋입니다: {preset_id!r}. 쓸 수 있는 값: {', '.join(ids())}"
        ) from None


def relaxed(preset_id: str) -> FrozenSet[str]:
    """프리셋이 완화하는 규칙 ID. NEVER_RELAXED는 어떤 선언보다 우선한다."""
    return get(preset_id).relax - NEVER_RELAXED
