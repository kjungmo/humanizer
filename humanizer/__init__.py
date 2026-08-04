"""humanizer 결정론 레이어.

프롬프트(SKILL.md)가 감으로 세지 않도록, 기계로 판정 가능한 흔적과 계량치를
결정론으로 제공한다. 외부 의존성이 없고 파이썬 3.8 이상에서 동작한다.
"""

from . import detect, metrics, presets, voice  # noqa: F401

__all__ = ["detect", "metrics", "presets", "voice"]
__version__ = "3.3.0"
