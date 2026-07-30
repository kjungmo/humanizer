# humanizer

AI가 쓴 티가 나는 글을 사람이 쓴 글로 되돌리는 에이전트 스킬이다. 한국어를 1순위로 다루고, 채널별 어투 프리셋을 골라 쓸 수 있다.

> A Korean-first AI-writing humanizer skill with channel presets (Naver blog, dev blog, Instagram post/reels/comment) and a dependency-free deterministic scanner. Forked from [blader/humanizer](https://github.com/blader/humanizer); the English pattern catalog is carried over unchanged. See [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

## 다른 humanizer와 무엇이 다른가

**1. 감으로 세지 않는다.** 기존 humanizer 스킬은 전부 순수 프롬프트다. "이 표현이 몇 번 나왔는지"를 모델의 추정에 맡긴다. 여기에는 의존성 없는 파이썬 스캐너가 있다. 이중피동, 연결어미 뒤 쉼표, 겹조사, hype 어휘, 줄표, 챗봇 잔재처럼 기계로 판정 가능한 34개 규칙을 결정론으로 센다. 글자수도 자소 묶음 기준으로 실제로 센다.

```
$ python3 -m humanizer detect 초안.md --preset general
프리셋: general (일반 한국어) · 가드: change-rate
S1 4건 · S2 2건 · S3 0건

[S1] A-8 이중피동 (2회) 줄 3, 12
       예: 보여진다 / 시각화되어진다

[S1] C-11 연결어미 직후 쉼표 (7회) 줄 5, 5, 8
       예: 검토하고, / 공유했으며, / 조정했지만,
```

**2. 채널 목적성이 규칙 체계 안에 있다.** 인스타에서 이모지는 흔적이 아니다. 네이버 블로그는 검색 유입을 위해 핵심어를 반복해야 한다. 개발자 블로그는 영어 용어를 그대로 둬야 한다. 프리셋은 이걸 "완화 집합"으로 선언하고, 스캐너가 `--preset`으로 그대로 반영한다. 완화 목록에 없는 패턴은 어느 채널에서도 눈감아 주지 않는다.

**3. 글쓴이 말투를 재서 파일로 남긴다.** 다른 humanizer는 "샘플을 주면 맞춰 쓴다"고만 말한다. 여기서는 `profile`이 표본에서 문장 길이 분포, 종결 유형, 문장부호 습관, 입버릇, 규칙별 개인 기준선을 결정론으로 뽑아 재사용 가능한 파일로 만든다. `detect --voice`가 그 기준선 이내의 흔적을 흔적으로 세지 않는다.

재기 전에 표본을 두 번 거르는 것이 이 기능의 핵심이다. 요즘 메모장에는 AI가 쓴 요약이 섞여 있어서, 그대로 재면 그 사람 말투가 아니라 **AI 말투를 학습한다.** 흔적을 지우려고 만든 도구가 흔적을 정답으로 배우는 셈이다. 그래서 스캐너를 표본에 먼저 돌려 생성기가 쓴 덩어리를 버리고, 붙여넣은 로그와 셸 출력도 걷어낸다. 무엇을 얼마나 버렸는지 프로필에 적는다.

```
$ python3 -m humanizer profile 일지/*.md --name devmemo
말투 프로필: devmemo
표본 3개 · 남은 글자 60,731자 · 문장 1,605개
버림: AI가 쓴 덩어리 5/646개 (1.2%) · 산문이 아닌 줄 81.7%

문장 길이: 평균 33.3자 · 표준편차 26.3 · 변동계수 0.791
종결 유형: 개조식 61% · 음슴체 22% · 평서-다 10% · 할것체 4%
문두 입버릇: 일단 1.81, 다만 1.06, 그래서 0.75, 그리고 0.56, 근데 0.44
```

**4. 회귀를 기계로 막는다.** `eval/`에 before와 after 픽스처가 있고, 채점기가 "스캐너가 흔적을 놓치지 않는지"와 "정답 윤문이 깨끗한지"를 확인한다. 규칙을 손봤을 때 예전에 잡던 것을 놓치면 즉시 드러난다.

## 설치

### Skills CLI

```bash
npx skills add kjungmo/humanizer --global
```

기존 설치 갱신:

```bash
npx skills update humanizer --global
```

지원하는 모든 하네스에 설치하려면:

```bash
npx skills add kjungmo/humanizer --global --agent '*'
```

`--global`을 빼면 프로젝트 단위로 설치되어 협업자와 함께 커밋할 수 있다. 설치 후 새 세션을 시작하거나 스킬을 다시 읽어야 한다.

### Claude Code 플러그인

```
/plugin marketplace add kjungmo/humanizer
/plugin install humanizer@humanizer
```

상위 저장소 `blader/humanizer`와 스킬 이름이 같다. 둘을 동시에 설치하지 말고 하나만 쓴다.

### 스캐너

스킬 프롬프트는 스캐너 없이도 동작하지만, 스캐너를 쓰면 셈이 확정된다. 저장소를 클론하고 `python3 -m humanizer`를 그대로 실행하면 된다. 파이썬 3.8 이상이면 되고 외부 의존성은 없다.

## 사용

에이전트 하네스가 스킬을 노출하는 방식대로 부른다.

```
이 글 AI 티 안 나게 고쳐줘
번역체 좀 자연스럽게 다듬어줘
이걸 인스타 게시글용으로 바꿔줘
릴스 대본으로 만들어줘
네이버 블로그용으로 1500자로 써줘
이 글에서 AI 흔적만 찾아줘 (고치지 말고 진단만)
```

명령줄로 직접 쓸 수도 있다.

```bash
python3 -m humanizer presets                          # 프리셋 목록과 다이얼
python3 -m humanizer detect 초안.md --preset naver-blog
python3 -m humanizer detect - --preset general < 초안.md
python3 -m humanizer metrics 결과물.md --target 1500   # 글자수·문장 리듬
python3 -m humanizer diff 원본.md 결과물.md            # 변경률 가드
python3 -m humanizer detect 초안.md --json             # 기계 판독용

python3 -m humanizer profile 표본*.md --name devmemo   # 말투 프로필을 뜬다
python3 -m humanizer detect 초안.md --voice voice/devmemo.json
```

`detect`는 S1 흔적이 남아 있으면 종료 코드 1을 낸다. 커밋 훅이나 CI에 걸 수 있다.

## 말투 프로필

`profile`은 `voice/<이름>.json`과 `voice/<이름>.md`를 만든다. 앞은 `detect --voice`가 읽고, 뒤는 스킬이 읽는다.

**말투는 하나가 아니다.** 같은 사람이라도 업무 메모, 개발 블로그, 인스타 캡션은 서로 다른 글이다. 셋을 한 표본에 섞으면 아무의 말투도 아닌 평균이 나온다. 용도별로 따로 뜨고 이름을 나눈다.

`voice/`는 `TEMPLATE.md`를 빼고 커밋되지 않는다. 말투를 재려면 그 사람이 쓴 글을 통째로 넣어야 하는데, 개인 메모장에는 거래처 이름과 동료 실명, 가족 일정이 섞여 있다. 어휘 목록(`--with-vocabulary`)이 기본으로 꺼져 있는 것도 같은 이유다.

개인 기준선은 규칙별로 "이 사람 글에서 100문장당 몇 번 나오는가"다. `detect --voice`는 그 값의 1.5배까지를 말투로 보고 S3으로 낮춘다. 문두 접속사를 원래 많이 쓰는 사람에게 H-1을 들이대면 그 사람 말투를 지우기 때문이다. **줄표(J-2)·hype 어휘(D-4)·챗봇 잔재(K-1)는 어떤 기준선으로도 낮아지지 않는다.**

## 프리셋

| 프리셋 | 어투 | 분량 | 이모지 | 해시태그 | 가드 |
|---|---|---|---|---|---|
| `general` | 원문 유지 | 원문 ±5% | 금지 | 다루지 않음 | 변경률 |
| `naver-blog` | 해요체 | 1,000~2,000자 | 문단 끝 1~2개 | 본문 밖 5~10개 | 사실 대장 |
| `dev-blog` | 합니다체 | 상한 없음 | 금지 | 없음 | 변경률 |
| `instagram-post` | 해요체 또는 반말 | 300~700자 | 자유 | 마지막 줄 10~20개 | 사실 대장 |
| `instagram-reels` | 반말·음슴체 | 200~500자 | 대본엔 최소 | 캡션 블록에만 | 사실 대장 |
| `instagram-comment` | 짧은 반말·해요체 | 40자 이내 | 1~2개 | 금지 | 사실 대장 |

`general`은 순수한 흔적 제거다. 어투를 옮기지 않고 구조를 바꾸지 않는다. 나머지는 **의도적인 리스타일**이라 세 가지가 달라진다.

- **완화**: 그 채널에서 정상인 패턴을 흔적으로 세지 않는다.
- **강화**: 코어에 없는 규칙을 더 요구한다. 릴스는 0~3초 훅이 없으면 실패고, 댓글은 광고 티가 나면 실패다.
- **가드 교체**: 리스타일은 사실상 재작성이라 변경률이 의미를 잃는다. 그 자리를 **사실 대장**(고유명사·수치·날짜·인용을 목록으로 뽑아 결과물과 대조)이 대신한다. 어투는 바꿔도 사실은 한 글자도 바꾸지 않는다.

변경률 가드가 남아 있는 프리셋은 `general`과 `dev-blog` 둘뿐이다. 이 둘만 어투와 구조와 분량을 원문에서 가져오기 때문이다. 나머지는 어투를 옮기는 순간 변경률이 30%를 넘어 가드가 뜻을 잃으므로 사실 대장이 그 자리를 대신한다.

> 지금 프롬프트 팩이 있는 프리셋은 `general`, `naver-blog`, `dev-blog` 셋이다. 인스타 3종은 다이얼과 완화 집합이 이미 스캐너에 반영되어 있고, 채널별 윤문 지침 문서는 뒤이어 붙인다.

## 저장소 구조

```
SKILL.md                     라우터. 언어·프리셋 결정, 4대 철칙, 작업 루프, 산출물 규격
packs/ko/core.md             한국어 흔적 카탈로그 (A~K, 심각도, 처방, 완화 축, 스캐너 대응)
packs/ko/presets/            채널별 윤문 지침
packs/en/core.md             영어 흔적 카탈로그 33개 (상위 저장소에서 그대로 계승)
humanizer/detect.py          34개 규칙 스캐너, 보호 구간 마스킹
humanizer/metrics.py         자소 묶음 글자수, 문장 길이 분포, 변경률
humanizer/presets.py         프리셋 레지스트리 (다이얼 + 완화 집합)
humanizer/voice.py           말투 프로필: 표본 선별, 종결 유형, 개인 기준선
voice/                       뜬 프로필이 쌓이는 곳 (커밋하지 않는다)
eval/                        회귀 픽스처와 채점기
tests/                       단위 테스트와 문서·코드 동기화 테스트
```

## 한국어 패턴 카탈로그

| 분류 | 내용 | 대표 S1 |
|---|---|---|
| A 번역체 | 영어 전치사 직역, 가지다, 이중피동, 대명사 강박, 겹조사 | A-7, A-8, A-16 |
| B 영어 병기 | 괄호 영어 매번 병기, 안 옮긴 영어 | |
| C 구조 | 이모지 장식, 3의 법칙, 콜론 헤딩, 연결어미 뒤 쉼표 | C-5, C-11 |
| D 관용구 | 결산 피벗, 의의 상투구, hype 어휘, 결말 공식, 과장된 의의 | D-1, D-2, D-4, D-6, D-8 |
| E 리듬 | 문장 길이 균일, 동일 종결어미 반복, 경어법 흔들림 | |
| F 수식 | 동의어 돌려쓰기, 가짜 범위, -성/-적/-화 누적 | |
| G 완충 | 미래 단정, 추정 남발, 안전 균형 표현 | |
| H 접속사 | 문두 접속사 남발, 메타 진입 | H-1, H-3 |
| I 형식명사 | "~인 것이다" 결말, 설교조 당위, 예고 멘트 | I-1 |
| J 시각 장식 | 볼드 남용, 줄표, 곡선따옴표 | J-2 |
| K 챗봇 잔재 | 챗봇 응대, 아첨 | K-1 |

한국어 AI 글의 1순위 정체는 **번역체**와 격식을 가장한 **상투어**다. 전체 표와 Before/After 예문은 [`packs/ko/core.md`](packs/ko/core.md)에 있다. 영어 33개 패턴은 [`packs/en/core.md`](packs/en/core.md)에 있다.

줄표(`—`, `–`)와 hype 어휘, 챗봇 잔재는 **어느 프리셋에서도 완화되지 않는다.** 인스타 캡션이라도 "진정한 가치를 담아낸"은 AI 티다.

## 개발

```bash
python3 -m unittest discover -s tests -t .   # 단위 테스트 + 문서·코드 동기화
python3 eval/score.py                        # 회귀 채점
python3 scripts/validate-package.py          # 패키지 메타데이터 동기화
npx skills add . --list                      # 스킬 탐색 확인
claude plugin validate .                     # 마켓플레이스 확인
```

규칙을 추가하거나 프리셋의 완화 집합을 바꿀 때는 `packs/ko/core.md`의 표와 `humanizer/presets.py`를 함께 고친다. 둘이 어긋나면 `tests/test_presets.py`가 깨진다. 자세한 규약은 [AGENTS.md](AGENTS.md)에 있다.

## 계보

세 갈래의 선행 작업 위에 서 있고, 셋 다 MIT다. 무엇을 물려받았고 무엇을 새로 썼는지는 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)에 구분해 적었다.

- [blader/humanizer](https://github.com/blader/humanizer): 영어 패턴 33개와 패키징 골격
- [NomaDamas/k-skill](https://github.com/NomaDamas/k-skill)의 `korean-humanizer`: 한국어 A~K 분류 체계와 심각도, 철칙, 가드, 등급
- [epoko77-ai/im-not-ai](https://github.com/epoko77-ai/im-not-ai): 한국어 방법론의 뿌리와 국어학 근거

영어 패턴의 근거는 [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)이다.

## Version History

- **3.2.0** - `naver-blog`과 `dev-blog` 프롬프트 팩을 넣고 회귀 픽스처를 4건 붙였다. `naver-blog`의 가드를 사실 대장으로 바로잡았다(어투와 분량을 옮기는 프리셋이라 변경률이 뜻을 잃는다). 이중피동 A-8이 합니다체 활용형 "되어집니다"를 놓치던 것을 고쳤다. 팩 문서와 코드가 다른 가드를 말하거나, 완화 규칙 설명이 빠지거나, 윤문이 코드블록을 건드리면 테스트가 깨진다.
- **3.1.0** - 말투 프로필(`humanizer/voice.py`, `profile` 명령, `detect --voice`)을 넣었다. 표본에서 문장 길이 분포·종결 유형·문장부호 습관·입버릇·규칙별 개인 기준선을 결정론으로 뽑는다. 재기 전에 AI가 쓴 덩어리와 붙여넣은 로그를 두 단계로 걸러낸다. 프로필은 커밋하지 않고 어휘 목록은 기본으로 끈다.
- **3.0.0** - 한국어 우선으로 재편했다. `SKILL.md`를 라우터로 바꾸고 패턴 카탈로그를 언어 팩(`packs/ko`, `packs/en`)으로 분리했다. 채널 프리셋 계층(6종 다이얼과 완화 집합), 리스타일용 사실 대장 규약, 34개 규칙의 결정론 스캐너와 계량 모듈, 회귀 채점기, 문서·코드 동기화 테스트를 새로 넣었다. 영어 패턴 33개는 번호까지 그대로 유지한다.
- **2.9.1** - (상위 저장소) 배포와 이식성 개선: 비이식 프런트매터와 도구 사전승인 제거, 전역 설치를 기본으로 문서화, 패키지 검증 추가.
- **2.9.0** - (상위 저장소) 사실 날조 금지 규칙 추가, 정보 보존을 구조 모방보다 우선, 호출 모드 3종 도입.

2.9.1 이전 이력은 [상위 저장소](https://github.com/blader/humanizer)에 있다.

## License

MIT. Copyright (c) 2026 Kang Jung Mo, Copyright (c) 2025 Siqi Chen.

개인 작업물이다.
