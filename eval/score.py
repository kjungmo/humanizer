#!/usr/bin/env python3
"""회귀 채점기.

`eval/fixtures/<preset>/<이름>.{before,after}.md` 와 `<이름>.expect.json` 을 읽어
스캐너가 흔적을 놓치지 않는지(before), 정답 윤문이 깨끗한지(after)를 확인한다.

프롬프트를 손볼 때 이 채점기가 통과하는지 보고 나서 커밋한다. 픽스처가 늘어나면
"이 규칙을 느슨하게 바꿨더니 저 케이스를 놓친다"가 즉시 드러난다.

사용:
    python3 eval/score.py            # 전체
    python3 eval/score.py general    # 프리셋 하나만
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from humanizer import detect, metrics  # noqa: E402

FIXTURES = ROOT / "eval" / "fixtures"


def check(stem: Path) -> list:
    """한 케이스를 채점한다. 반환값은 실패 사유 목록이며, 비어 있으면 통과다."""
    expect = json.loads(stem.with_suffix(".expect.json").read_text(encoding="utf-8"))
    preset = expect.get("preset", "general")
    before = stem.with_suffix(".before.md").read_text(encoding="utf-8")
    after = stem.with_suffix(".after.md").read_text(encoding="utf-8")

    failures = []

    scanned_before = detect.scan(before, preset=preset)
    found = {f.rule_id for f in scanned_before.findings}
    missing = [r for r in expect["before"].get("must_detect", []) if r not in found]
    if missing:
        failures.append(f"before에서 놓친 규칙: {', '.join(missing)}")
    floor = expect["before"].get("s1_min")
    if floor is not None and len(scanned_before.s1) < floor:
        failures.append(f"before S1 {len(scanned_before.s1)}건, 최소 {floor}건 필요")

    scanned_after = detect.scan(after, preset=preset)
    ceiling = expect["after"].get("s1_max", 0)
    if len(scanned_after.s1) > ceiling:
        ids = ", ".join(f.rule_id for f in scanned_after.s1)
        failures.append(f"after에 S1 잔존 {len(scanned_after.s1)}건 ({ids}), 상한 {ceiling}건")
    still = {f.rule_id for f in scanned_after.findings}
    lingering = [r for r in expect["after"].get("must_not_detect", []) if r in still]
    if lingering:
        failures.append(f"after에 남은 규칙: {', '.join(lingering)}")

    limit = expect.get("change_rate_max")
    if limit is not None:
        rate = metrics.change_rate(before, after)
        if rate > limit:
            failures.append(f"변경률 {rate:.1%}, 상한 {limit:.0%}")

    return failures


def main(argv) -> int:
    wanted = argv[1] if len(argv) > 1 else None
    stems = sorted(
        {
            path.with_suffix("").with_suffix("")
            for path in FIXTURES.rglob("*.expect.json")
            if wanted is None or path.parent.name == wanted
        }
    )
    if not stems:
        print("채점할 픽스처가 없습니다.")
        return 1

    passed = 0
    for stem in stems:
        failures = check(stem)
        label = f"{stem.parent.name}/{stem.name}"
        if failures:
            print(f"FAIL  {label}")
            for reason in failures:
                print(f"        {reason}")
        else:
            passed += 1
            print(f"ok    {label}")

    print(f"\n{passed}/{len(stems)} 케이스 통과")
    return 0 if passed == len(stems) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
