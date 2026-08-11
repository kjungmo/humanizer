"""`python3 -m humanizer` 명령줄 진입점."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import detect, metrics, presets, voice


def _read(source: str) -> str:
    if source == "-":
        return sys.stdin.read()
    return Path(source).read_text(encoding="utf-8")


def _print_detect(result: detect.ScanResult, preset: presets.Preset) -> None:
    counts = result.counts
    print(f"프리셋: {preset.id} ({preset.label}) · 가드: {preset.guard}")
    print(f"S1 {counts['S1']}건 · S2 {counts['S2']}건 · S3 {counts['S3']}건")
    if not result.findings:
        print("\n탐지된 흔적이 없습니다. 손대지 않는 쪽을 우선 검토하세요.")
    for finding in result.findings:
        head = f"\n[{finding.severity}] {finding.rule_id} {finding.label} ({finding.count}회)"
        if finding.lines:
            head += " 줄 " + ", ".join(str(n) for n in finding.lines)
        print(head)
        if finding.samples:
            print("       예: " + " / ".join(finding.samples))
    if result.relaxed:
        print("\n완화된 규칙(이 프리셋에서 흔적으로 세지 않음): " + ", ".join(result.relaxed))
    print(
        "\n주의: 스캐너는 기계로 셀 수 있는 흔적만 잡습니다. "
        "과장된 의의 부여, 영혼 없음, 장르 이탈은 직접 판단하세요."
    )


def _print_metrics(data: dict) -> None:
    print(f"글자수: {data['chars_with_spaces']}자 (공백 포함) / "
          f"{data['chars_without_spaces']}자 (공백 제외)")
    stats = data["sentences"]
    print(
        f"문장: {stats['count']}개 · 평균 {stats['mean']}자 · 표준편차 {stats['stdev']} "
        f"· 최단 {stats['shortest']}자 · 최장 {stats['longest']}자"
    )
    if stats["count"] >= 5 and stats["stdev"] < 8:
        print("경고: 문장 길이가 균일합니다(E-1). 단문과 장문을 섞으세요.")
    if "target" in data:
        verdict = "통과" if data["within_5pct"] else "초과"
        strict = "통과" if data["within_2pct"] else "초과"
        print(
            f"목표 {data['target']}자 대비 {data['delta']:+d}자 · "
            f"±5% {verdict} · ±2% {strict}"
        )


def _print_diff(rate: float, preset: presets.Preset) -> None:
    print(f"변경률: {rate * 100:.1f}%")
    if preset.guard == "fact-ledger":
        print(
            f"프리셋 {preset.id}은 리스타일 계열입니다. 변경률 가드를 적용하지 않습니다. "
            "대신 사실 대장(고유명사·수치·날짜·인용)을 대조하세요."
        )
        return
    if rate > 0.50:
        print("중단: 50%를 넘었습니다. 롤백하고 다시 윤문하세요. 등급 D입니다.")
    elif rate > 0.30:
        print("경고: 30%를 넘었습니다. 왜 그만큼 손댔는지 보고에 적으세요.")
    else:
        print("가드 통과(30% 이하).")


def _print_profile(profile: voice.VoiceProfile, paths: list) -> None:
    s = profile.screening
    print(f"말투 프로필: {profile.name}")
    print(f"표본 {len(paths)}개 · 남은 글자 {profile.volume['chars']:,}자 · "
          f"문장 {profile.volume['sentences']:,}개")
    print(
        f"버림: AI가 쓴 덩어리 {s['blocks_dropped']}/{s['blocks']}개 "
        f"({s['dropped_ratio']:.1%}) · 산문이 아닌 줄 {s['prose']['dropped_ratio']:.1%}"
    )
    if s["dropped_by_rule"]:
        print("  근거: " + ", ".join(
            f"{rule} {count}회" for rule, count in s["dropped_by_rule"].items()
        ))
    if profile.volume["sentences"] < voice.MIN_SENTENCES:
        print(
            f"\n경고: 문장이 {voice.MIN_SENTENCES}개 미만이라 분포를 믿기 어렵습니다. "
            "표본을 더 넣으세요."
        )
    sl = profile.sentence_length
    print(f"\n문장 길이: 평균 {sl['mean']}자 · 표준편차 {sl['stdev']} · 변동계수 {sl['cv']}")
    print("종결 유형: " + " · ".join(
        f"{kind} {ratio:.0%}" for kind, ratio in list(profile.endings.items())[:6]
    ))
    if profile.markers:
        print("문두 입버릇: " + ", ".join(
            f"{marker} {rate}" for marker, rate in list(profile.markers.items())[:8]
        ))


def _print_presets() -> None:
    print(f"{'ID':<20} {'어투':<16} {'분량':<16} {'이모지':<14} 가드")
    for preset in presets.PRESETS.values():
        ready = "" if preset.pack else "  (프롬프트 팩 준비 중)"
        print(
            f"{preset.id:<20} {preset.register:<16} {preset.budget:<16} "
            f"{preset.emoji:<14} {preset.guard}{ready}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m humanizer",
        description="한국어 AI 글 흔적 스캐너와 계량 도구",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan_cmd = sub.add_parser("detect", help="흔적을 탐지한다")
    scan_cmd.add_argument("source", help="파일 경로 또는 '-' (표준입력)")
    scan_cmd.add_argument("--preset", default=presets.DEFAULT, choices=presets.ids())
    scan_cmd.add_argument(
        "--voice", default=None,
        help="말투 프로필 JSON. 개인 기준선 이내의 흔적은 S3으로 낮춘다",
    )
    scan_cmd.add_argument("--json", action="store_true")

    profile_cmd = sub.add_parser("profile", help="표본에서 말투 프로필을 뜬다")
    profile_cmd.add_argument("sources", nargs="+", help="표본 파일 경로")
    profile_cmd.add_argument("--name", required=True, help="프로필 이름 (파일 이름이 된다)")
    profile_cmd.add_argument("--out", default="voice", help="산출 디렉터리 (기본 voice/)")
    profile_cmd.add_argument(
        "--with-vocabulary", action="store_true",
        help="자주 쓰는 낱말 목록까지 남긴다. 표본에 실명·거래처가 있으면 켜지 마세요",
    )
    profile_cmd.add_argument("--json", action="store_true")

    metrics_cmd = sub.add_parser("metrics", help="글자수와 문장 리듬을 센다")
    metrics_cmd.add_argument("source")
    metrics_cmd.add_argument("--target", type=int, default=None, help="목표 글자수")
    metrics_cmd.add_argument("--json", action="store_true")

    diff_cmd = sub.add_parser("diff", help="변경률을 센다")
    diff_cmd.add_argument("before")
    diff_cmd.add_argument("after")
    diff_cmd.add_argument("--preset", default=presets.DEFAULT, choices=presets.ids())
    diff_cmd.add_argument("--json", action="store_true")

    sub.add_parser("presets", help="프리셋 목록과 다이얼을 출력한다")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "detect":
        text = _read(args.source)
        result = detect.scan(text, preset=args.preset)
        softened = []
        if args.voice:
            profile = json.loads(Path(args.voice).read_text(encoding="utf-8"))
            softened = voice.apply_baseline(result, profile, text)
        if args.json:
            data = result.as_dict()
            if args.voice:
                data["voice"] = {"profile": args.voice, "softened": softened}
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            _print_detect(result, presets.get(args.preset))
            if softened:
                print(
                    "\n개인 기준선 이내라 S3으로 낮춘 규칙: " + ", ".join(softened)
                )
        return 1 if result.s1 else 0

    if args.command == "profile":
        texts = [_read(source) for source in args.sources]
        profile = voice.fingerprint(
            "\n\n".join(texts), args.name, keep_vocabulary=args.with_vocabulary
        )
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / f"{args.name}.json"
        md_path = out_dir / f"{args.name}.md"
        json_path.write_text(
            json.dumps(profile.as_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        md_path.write_text(voice.render(profile), encoding="utf-8")
        if args.json:
            print(json.dumps(profile.as_dict(), ensure_ascii=False, indent=2))
        else:
            _print_profile(profile, args.sources)
            print(f"\n기록: {json_path} · {md_path}")
        return 0 if profile.volume["sentences"] >= voice.MIN_SENTENCES else 1

    if args.command == "metrics":
        data = metrics.report(_read(args.source), target=args.target)
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            _print_metrics(data)
        return 0

    if args.command == "diff":
        rate = metrics.change_rate(_read(args.before), _read(args.after))
        preset = presets.get(args.preset)
        if args.json:
            print(json.dumps({"change_rate": rate, "preset": preset.id}, ensure_ascii=False))
        else:
            _print_diff(rate, preset)
        return 1 if preset.guard == "change-rate" and rate > 0.50 else 0

    _print_presets()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
