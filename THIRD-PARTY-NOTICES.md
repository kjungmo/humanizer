# 출처와 계보 (Third-party notices)

이 저장소는 세 갈래의 선행 작업 위에 서 있다. 세 갈래 모두 MIT 라이선스이고, 여기서 그 저작권 고지를 유지한다. 어느 부분을 물려받았고 어느 부분이 새로 쓴 것인지 아래에 구분해 적는다.

## 1. blader/humanizer (영어 원형)

- 저장소: <https://github.com/blader/humanizer>
- 라이선스: MIT, Copyright (c) 2025 Siqi Chen
- 물려받은 것:
  - **영어 패턴 카탈로그 33개 전체.** `packs/en/core.md`는 상위 저장소 v2.9.1의 `SKILL.md` 패턴 절과 오탐 방지 절을 그대로 옮긴 것이다. 번호(§1~§33)도 그대로 둔다.
  - **패키징 골격.** `.claude-plugin/`, `agents/openai.yaml`, `scripts/validate-package.py`, `.github/workflows/validate.yml`의 구조와 버전 3중 동기화 규약.
  - **설계 관습.** Voice Calibration, PERSONALITY AND SOUL, 3가지 호출 모드, 초안에서 감사를 거쳐 최종본으로 가는 루프, 사실 날조 금지 규칙, 단발이 아니라 무더기로 판정하는 원칙.
- 영어 패턴의 근거는 [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)이다. WikiProject AI Cleanup이 관리한다.

## 2. NomaDamas k-skill의 korean-humanizer (한국어 선행 스킬)

- 저장소: <https://github.com/NomaDamas/k-skill>
- 라이선스: MIT, Copyright (c) 2026
- 물려받은 것:
  - **A부터 K까지의 한국어 흔적 분류 체계.** 번역체 A, 영어 병기 B, 구조 C, 관용구 D, 리듬 E, 수식 F, 완충 G, 접속사 H, 형식명사 I, 시각 장식 J, 챗봇 잔재 K.
  - **심각도 3단계(S1/S2/S3)와 개별 패턴의 심각도 배정.**
  - **4대 철칙, 변경률 30%/50% 가드, 품질 등급 A~D, 트리아지 단계, Length control 규약.**
  - 개별 패턴의 정의와 처방 방향. 표의 문장은 다시 썼고 예문은 새로 만들었다.

## 3. epoko77-ai/im-not-ai (한국어 방법론의 뿌리)

- 저장소: <https://github.com/epoko77-ai/im-not-ai>
- 라이선스: MIT
- 위 2번 스킬이 방법론을 가져온 원천이다. 한국어 고유 패턴의 학술 근거가 여기에 있다.
  - A-16 대명사 강박: 김도훈(2009)
  - A-18 관계절 좌향 수식: 박옥수(2018)
  - A-19 겹조사: 김정우(2007)
  - E-7 경어법 일관성: 김혜영(2019)
- 최초의 한국어 humanizer 스킬과 33개 패턴 카탈로그, 예문, 트리아지와 분량 조절 설계는 happy-nut(Hyungsun Song)이 k-skill PR #311로 기여했다.

## 이 저장소가 새로 쓴 것

위 세 갈래에 없던 부분이다.

1. **채널 프리셋 계층** (`packs/ko/presets/`, `humanizer/presets.py`). 일반 한국어, 네이버 블로그, 개발자 블로그, 인스타 게시글, 인스타 릴스, 인스타 댓글. 다이얼(어투·분량·이모지·해시태그·구조)과 완화 집합, 강화 항목으로 구성한다.
2. **완화 축.** 선행 작업의 패턴표는 어느 글에나 같은 규칙을 적용한다. 여기서는 패턴마다 "어느 채널에서 흔적이 아닌지"를 선언한다. 인스타에서 이모지가 정상이고 네이버 블로그에서 핵심어 반복이 필요하다는 사실을 규칙 체계 안으로 넣었다.
3. **사실 대장(fact ledger).** 리스타일 프리셋에서는 변경률 가드가 무의미해진다. 그 자리를 고유명사·수치·날짜·인용 대조로 대체하는 규약.
4. **결정론 스캐너** (`humanizer/detect.py`, `metrics.py`). 34개 규칙의 정규식과 문맥 판정, 보호 구간 마스킹, 자소 묶음 기반 글자수, 문장 길이 분포, 변경률 계산. 선행 작업은 둘 다 순수 프롬프트여서 셈이 모델 추정에 맡겨져 있었다.
5. **회귀 채점기와 픽스처** (`eval/`). 프롬프트나 규칙을 손볼 때 이전에 잡던 흔적을 놓치는지 기계로 확인한다.
6. **문서와 코드 동기화 테스트** (`tests/test_presets.py`). `packs/ko/core.md`의 완화 열과 `presets.py`의 선언이 어긋나면 테스트가 깨진다.

## 이 저장소의 저작권

- Copyright (c) 2026 Kang Jung Mo. MIT.
- 개인 작업물이다. 소속 조직과 무관하다.
