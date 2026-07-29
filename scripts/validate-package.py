#!/usr/bin/env python3
"""패키지 표면과 메타데이터 동기화를 외부 의존성 없이 검증한다.

내용의 정합성(규칙 표와 프리셋 선언이 맞는지)은 `tests/`가 본다.
이 스크립트는 배포 표면만 본다. 버전이 세 곳에서 같은지, 필수 파일이 있는지,
프런트매터가 이식 가능한지.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
PLUGIN = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))

REQUIRED_FILES = (
    "packs/ko/core.md",
    "packs/ko/presets/general.md",
    "packs/en/core.md",
    "humanizer/detect.py",
    "humanizer/metrics.py",
    "humanizer/presets.py",
    "humanizer/cli.py",
    "eval/score.py",
    "THIRD-PARTY-NOTICES.md",
    "LICENSE",
)

SKILL_LINE_BUDGET = 500


def fail(message: str) -> None:
    raise SystemExit(f"검증 실패: {message}")


def require(match, message):
    if match is None:
        fail(message)
    return match


# --- 필수 파일 -------------------------------------------------------------

missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
if missing:
    fail("빠진 파일: " + ", ".join(missing))

# --- 프런트매터 이식성 -----------------------------------------------------

frontmatter = require(
    re.match(r"\A---\n(.*?)\n---\n", SKILL, re.DOTALL),
    "SKILL.md는 YAML 프런트매터로 시작해야 합니다",
).group(1)

for nonportable in ("compatibility:", "allowed-tools:"):
    if re.search(rf"(?m)^{re.escape(nonportable)}", frontmatter):
        fail(f"이식 불가 프런트매터 키를 제거하세요: {nonportable[:-1]}")

if not re.search(r"(?m)^name:\s*humanizer\s*$", frontmatter):
    fail("SKILL.md의 name은 humanizer여야 합니다")

# --- 버전 3중 동기화 -------------------------------------------------------

skill_version = require(
    re.search(r'(?m)^\s+version:\s*["\']([^"\']+)["\']\s*$', frontmatter),
    "SKILL.md metadata.version이 없습니다",
).group(1)
readme_version = require(
    re.search(r"(?m)^- \*\*([0-9]+\.[0-9]+\.[0-9]+)\*\*", README),
    "README의 Version History가 없습니다",
).group(1)
package_version = require(
    re.search(
        r'(?m)^__version__ = "([^"]+)"$',
        (ROOT / "humanizer" / "__init__.py").read_text(encoding="utf-8"),
    ),
    "humanizer/__init__.py의 __version__이 없습니다",
).group(1)

versions = {skill_version, readme_version, package_version, str(PLUGIN.get("version", ""))}
if len(versions) != 1:
    fail(
        "버전 불일치: "
        f"SKILL={skill_version}, README={readme_version}, "
        f"plugin.json={PLUGIN.get('version')}, humanizer={package_version}"
    )

# --- 영어 팩의 패턴 번호 유지 ----------------------------------------------

en_core = (ROOT / "packs" / "en" / "core.md").read_text(encoding="utf-8")
en_numbers = [int(n) for n in re.findall(r"(?m)^### ([0-9]+)\. ", en_core)]
if en_numbers != list(range(1, 34)):
    fail(f"packs/en/core.md는 패턴 1~33을 유지해야 합니다. 발견: {en_numbers}")

# --- 프리셋이 README에 문서화되어 있는지 -----------------------------------

sys.path.insert(0, str(ROOT))
from humanizer import presets  # noqa: E402

undocumented = [pid for pid in presets.ids() if f"`{pid}`" not in README]
if undocumented:
    fail("README에 없는 프리셋: " + ", ".join(undocumented))

# --- 라우터 분량 -----------------------------------------------------------

skill_lines = len(SKILL.splitlines())
if skill_lines > SKILL_LINE_BUDGET:
    fail(f"SKILL.md가 {SKILL_LINE_BUDGET}줄 이식성 예산을 넘었습니다 ({skill_lines}줄)")

print(
    f"humanizer 패키지 v{skill_version} 정상 "
    f"(SKILL.md {skill_lines}줄, 프리셋 {len(presets.ids())}종, 규칙 표 33+A~K)"
)
