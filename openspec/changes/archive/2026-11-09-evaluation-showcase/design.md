## Context

동기는 `proposal.md`의 Why, 요구사항은 `specs/evaluation-showcase/spec.md`를 따른다.

공개할 데이터는 출처가 둘로 갈린다.

- **측정부** (반복 격자 · 거절 · 재현 조건 · 한계): `ask_replay_reliability.py`가 만든 `reliability-report.json`(schema `ask-replay-reliability-v1`)에 기계 집계로 이미 있다. 문항별 `outcomes` · `stability` · `reported_stages` · `automatic_stages`, 회차별 `answerable_interval_95` · `refusal_*` · `false_refusals` · `cost_micros`, `spread.all` / `spread.http_only`, `series_key`, `limitations`가 들어 있다. 이 파일은 저장소 밖 증거 디렉터리(`.worktrees/reliability-evidence-20261109/`)에 있고, sha256은 `openspec/changes/archive/2026-11-09-eval-reliability/verification.md`에 기록돼 있다.
- **지도와 원장**: `docs/ops/evaluation-map.md` §2 · §5의 산문 표에만 있다. 한 칸에 수치 · 분모 · 설명이 섞여 있고(정답성 칸 약 200자, 원장 칸 300자 이상) 측정일은 별도 필드가 아니다. §2 검색 행은 v1 값(hit@1 16/29)으로 남아 있지만, 2026-11-09 같은 수집의 검색 평가는 hit@1 27/29 · hit@8 28/29 · MRR 0.940이다.

질문 문구는 커밋된 `scripts/fixtures/ask_replay.v1.json`(`questions[].query`)에, 알려진 실패 메모는 `scripts/fixtures/ask_replay_labels.v1.json`에 있다.

기존 공개 쇼케이스(`evidence-research`)는 export 스크립트가 허용 필드 JSON을 `apps/dashboard/content/`에 쓰고, 페이지와 `results.json` 라우트가 그 JSON을 `force-static`으로 import한다. 컴포넌트 테스트가 Supabase/API import 금지를 검사한다. 두 기존 쇼케이스는 시각 패턴이 서로 다르다. notice는 3px 왼쪽 띠와 1px 전체 테두리로 갈리고, 최대 폭은 1080px과 960px, 모바일 분기점은 680px과 640px이다. 표 처리도 `nowrap` + 가로 스크롤과 `table-layout: fixed` 줄바꿈으로 다르다.

화면 설계는 impeccable critique(2026-11-09, 24/40, P1 4건 · P2 1건)를 받아 D2 · D3 · D5 · D6에 반영했다. 원본 기록은 로컬 `.impeccable/critique/2026-11-09T03-34-58Z__apps-dashboard-app-showcase-evaluation.md`이며 저장소에 커밋하지 않는다. 반영한 지적은 이 문서의 D2 · D3 · D5 · D6이 전부다.

## Goals / Non-Goals

**Goals:**

- 측정부 숫자는 사람이 손으로 옮기지 않고 보존 기록에서 export하며, 원본 sha256을 공개 기록에 남긴다.
- 지도와 원장은 구조화한 입력 파일 하나를 유일한 원본으로 둔다. `evaluation-map.md`와 페이지가 다른 숫자를 말할 수 없게 한다.
- 반복 측정에서 파생되는 숫자(정답성 · 거절)는 화면 어디서든 `series` 한 곳에서만 나온다.
- 공개 기록의 내부 정합성(합계 · 구간 · 안정성 · 허용 필드)은 CI 테스트가 매번 검사한다.
- 10초 방문자는 결론 문장과 회차 요약표만으로 무엇을 몇 번 쟀고 무엇이 틀렸는지 안다.

**Non-Goals:**

- 새 측정이나 유료 호출. 이미 보존한 기록만 옮긴다.
- CI에서 export를 다시 실행하기. 원본 report가 저장소 밖에 있어서다. CI는 커밋된 공개 기록만 검사한다.
- `evaluation-map.md` 표를 JSON에서 자동 생성하기. §2 · §5는 링크로 바꾸고 산문 절(§1 · 3 · 4 · 6 · 7)은 손으로 유지한다.
- 운영 데이터(Control Room 품질 탭 등)를 공개 화면에 연결하기.
- 랜딩 페이지 변경, 영어 번역, 차트 라이브러리 같은 새 의존성, 다크 모드(현재 디자인 시스템이 라이트 전용이다).
- 기존 두 쇼케이스의 시각 정리. 이 change는 링크만 추가하고, notice · 대비 · 최대 폭 통일은 새 페이지에만 적용한다.
- 답변 본문 공개. 격자에는 문항 id · 합성 질문 문구 · 판정만 둔다. 오답 내용은 labels의 사람 메모 범위에서만 보인다.
- 워커의 402 처리. 별도 이슈로 다룬다.

## Decisions

### D1. 혼합 생성: 측정부는 export, 지도·원장은 구조화 입력

`scripts/evaluation_showcase.py`에 두 하위 명령을 둔다.

- `export --report <reliability-report.json> --curated scripts/fixtures/evaluation_showcase.curated.v1.json --out apps/dashboard/content/evaluation.json`: report에서 허용 필드를 고르고, fixture의 질문 문구 · 유형과 labels의 메모를 붙인다. curated 파일의 지도 · 원장을 합친 뒤 검증을 통과해야 쓴다.
- `check <evaluation.json>`: 허용 필드와 불변식(D3)을 검사한다. pytest(`apps/worker/tests/test_evaluation_showcase.py`)가 커밋된 파일에 대해 이 검사를 실행하므로 CI에서 돈다.

구간 계산은 `ask_replay_reliability.wilson_interval`을 재사용한다. 숫자를 두 번 구현하지 않기 위해서다.

대안:
- (A) `evaluation-map.md` 표 파싱: 산문 칸이 바뀌면 필드가 조용히 빠진다. 버렸다.
- (C) 공개 JSON 전부 수기 작성: 격자 87칸을 손으로 옮겨야 하고 출처 추적이 끊긴다. 버렸다.

### D2. 공개 기록 스키마 `evaluation-showcase-v1` (허용 목록)

최상위 키는 다음으로 닫는다. 목록 밖 키가 하나라도 있으면 `check`가 실패한다.

- `schema`, `generated_at`, `provenance`: `report_sha256`, `fixture_sha256`, `labels_sha256`, `curated_sha256`.
- `synthetic`: `documents`(8), `questions`(30), `answerable`(29), `unanswerable`(1).
- `map[]`: `surface`, `status`(`measured` | `partial` | `empty`), `derived_from`(`series.answerable` | `series.refusal` | null), `summary`, `detail`, `denominator`, `measured_at`, `source`, `source_url`, `reason`.
  - `summary`는 지도 행에 보이는 한 줄(60자 이하)이고, `detail`은 펼쳐 보는 상세 산문이다.
  - `derived_from`이 있는 칸(최종 답 정답성 → `series.answerable`, 거절 → `series.refusal`)은 `summary` · `detail` · `denominator`가 null이다. 화면이 `series`에서 값을 만든다(D5).
  - `source_url`은 커밋 고정 GitHub 링크다. `source`는 사람이 읽는 이름이다.
- `series`: `valid`, `invalid_reason`, `key`(지문 sha256 · 모델 · 정책 · k), `runs[]`, `questions[]`, `spread`(`all` · `http_only`), `stability_counts`.
  - `runs[]`: `label`(공개용 이름 "HTTP 1" · "HTTP 2" · "스크립트 재집계 #232"), `path`(`http` | `harness`), `planned`, `asked`, `answerable_passed`, `answerable_asked`, `interval_95`, `refusal_correct`, `refusal_asked`, `false_refusals`, `cost_usd`.
  - `questions[]`: `id`, `query`, `kind`(`answerable` | `refusal`), `outcomes`(`pass` | `fail` | `not_run`), `stability`, `known_failure`, `reported_stage`, `automatic_stage`, `note`. 단계는 실패한 회차들의 값이 하나로 같으면 그 값, 서로 다르면 `mixed`("회차마다 다름")다. `note`는 labels의 방문자용 메모만 쓰고, 라벨의 내부 근거 경로(`evidence`)는 내보내지 않는다.
- `ledger[]`: `date`, `changed`, `technique`, `applied`, `evidence`, `evidence_url`. `changed`(측정이 바꾼 것)를 맨 앞에 둔다. 화면에서도 첫 문장이 되기 때문이다. 강의 편 번호 같은 내부 참조는 `technique`에 넣지 않는다.
- `limitations[]`: 문자열.

내부 실행 이름(`ablation-answer:bothxbody`), git revision, 공급자 generation id, workspace · 사용자 식별자, 자격증명, 답변 본문은 스키마에 자리가 없다. report에 새 필드가 생겨도 export가 고른 필드만 나간다. `check`는 이름 조각이 `workspace` · `user` · `generation` · `token` 등인 필드와, 본문 키(`answer` · `answer_text` · `body` · `content` 등 이름 전체 일치)를 추가로 거부한다. `answerable_*` 같은 정상 필드가 걸리지 않도록 본문 키는 이름 전체로만 잡고, 같은 이유로 프롬프트 지문은 `prompt_sha256`으로 이름을 바꿔 내보낸다.

대안: report를 통째로 복사하고 금지 목록만 거른다. 새 필드가 기본 공개가 돼 버렸다.

### D3. `check` 불변식

- `map`
  - `measured` · `partial`이고 `derived_from`이 null이면 `summary` · `denominator` · `measured_at` · `source`가 비어 있으면 안 된다.
  - `derived_from`이 있으면 `summary` · `detail` · `denominator`가 null이어야 한다. 묶음이 무효일 때 큐레이션 문장이 28/29를 계속 말하는 것을 막기 위해서다.
  - `empty`이면 `reason`이 있어야 하고 `summary`는 null이어야 한다.
  - `summary`는 60자 이하다.
- `series.valid`가 false이면 `invalid_reason`이 있어야 한다. true이면 다음을 만족해야 한다.
  - 문항 수 = `synthetic.questions`, `kind == "refusal"` 수 = `synthetic.unanswerable`이고, 각 `outcomes` 길이 = 회차 수다.
  - 회차별 `answerable_passed`가 `kind == "answerable"` 문항의 pass 합계와 일치한다. `refusal_correct`는 `kind == "refusal"` 문항의 pass 합계와 일치한다.
  - `interval_95`가 `wilson_interval(passed, asked)`의 재계산값과 일치한다.
  - `stability`가 `outcomes`에서 다시 유도한 값과 일치한다. `not_run`은 실패로 세지 않는다.
  - `spread.http_only`는 `path == "http"`인 회차만으로 다시 계산한 값과 일치한다.
- `ledger`: 날짜 오름차순이고 `changed` · `technique` · `applied` · `evidence`가 비어 있지 않아야 한다.
- `limitations`: 비어 있으면 안 된다.

### D4. `evaluation-map.md`와의 관계: curated 파일이 유일한 원본

지도 10칸과 원장 7행을 `scripts/fixtures/evaluation_showcase.curated.v1.json`으로 옮긴다. `evaluation-map.md` §2 · §5 표는 "원본: curated 파일 · 화면: `/showcase/evaluation`" 링크로 바꾼다. 옮기면서 바꾸는 것은 다음과 같다.

- 정답성 · 거절 칸은 `derived_from`(`series.answerable` · `series.refusal`)로 두고 숫자를 적지 않는다.
- 검색 행을 2026-11-09 값으로 갱신한다(hit@1 27/29 · hit@8 28/29 · 원문 · 위키 · 이중 적중@8 28/29 · MRR 0.940, 출처 `ask-sample-replay.md` 반복 측정 절).
- `도구 궤적`의 "해당 적음"은 `empty` + 이유("Ask는 도구 루프가 아닌 단발 호출")로 옮긴다. 스펙의 상태가 셋뿐이어서다.
- 원장의 "이 브랜치" 같은 상대 증거는 PR 번호나 문서 절로 바꾸고, 강의 편 번호는 뺀다.
- 근거성 칸의 문장 비율 평균(0.578 · 0.374)은 인용된 출처 문서에서 확인되지 않아 옮기지 않고, 확인되는 값(위조 인용 0건 · 두 종류 모두 인용한 턴 24/30)으로 바꾼다. 출처에 없는 숫자를 공개 화면에 올리지 않기 위해서다.

대안: 두 곳에 같은 표를 두고 테스트로 대조한다. 산문 칸 대조는 결국 파싱이라 (A)와 같은 문제가 생긴다. 버렸다.

### D5. 숫자에서 파생되는 문장은 컴포넌트가 만든다

- **결론 문장**: JSON 문자열로 두지 않고 `series`에서 조립한다. 형식은 "세 번 모두 답할 수 있는 29문항 중 28개를 맞혔고, 틀린 1문항(q06)은 매번 같은 이유로 틀렸습니다."이다. 주장과 단서를 한 줄에 섞지 않는다. "회차가 적어 안정성 보장은 아님"은 바로 아래 notice로 분리한다.
- **지도의 파생 칸**: `derived_from`(`series.answerable` · `series.refusal`)인 칸은 회차 요약에서 한 줄을 만든다(예: "3회 모두 28/29 · 흔들린 문항 0"). 칸은 반복 측정 구역으로 가는 앵커 링크를 갖는다.
- `series.valid`가 false이면 결론 자리, 파생 지도 칸, 요약표, 격자, 거절 블록 모두 무효와 그 이유만 보인다.

### D6. 화면 구조

**구역 순서**: 순서 자체가 위계다. 번호 표식(01~05)은 쓰지 않는다.

1. 머리: 제목 · 결론 문장(D5) · 합성 샘플 notice · 짧은 점프 목차(5개 구역).
2. **반복 측정**
   - 회차 요약표가 먼저 온다. 회차가 열, 지표가 행이다. 지표는 경로 · 실행 수(asked/planned) · 답할 수 있는 문항 통과 · 95% 구간 · 회차 비용이다. `evidence-research` 지표표와 같은 모양이다. 경로가 섞이면 표 아래에 "HTTP 회차만: 최소 · 최대"를 한 줄로 보인다.
   - 그다음 예외 우선 격자다. 안정 통과가 아닌 문항(q06 · 미실행 · 흔들림)만 펼친 표로 보인다. 행 머리는 id와 질문, 열은 회차, 마지막 열은 안정성이다. 보고 단계와 자동 단계, 사람 메모는 열이 아니라 그 행 아래 설명 줄로 붙인다.
   - 안정 통과 문항 전체는 `<details>`("결과가 세 번 모두 통과인 28문항 보기")로 접는다. 접혀도 DOM에 있어 테스트와 다운로드가 유지된다.
   - 거절 문항(q30)은 격자 통과 칸에 섞지 않고 `kind`로 "거절 문항"이라 표시한다.
3. **거절 성능**: 요약표 바로 아래 별도 블록이다. 회차마다 답할 수 있는 문항 통과(n/분모) · 정확한 거절(n/표본) · 잘못된 거절(n/답할 수 있는 문항)을 보이고, 표본 수 "거절 문항 1개"를 옆에 둔다. `refusal_asked == 0`이면 "없음 · 이 회차엔 거절 문항 없음"이다.
4. **평가 지도**: 행마다 측정면 · 상태 · `summary`(한 줄) · 측정일 · 출처 링크를 보인다. `detail`은 행 안 `<details>`로 접는다. 비어 있는 칸은 이유를 한 줄로 보인다.
5. **적용 원장**: 표가 아니라 `<ol>` 타임라인이다. 날짜가 소제목이고 첫 문장이 `changed`다. 기법 · 한 일 · 증거는 `<dl>`로 붙인다.
6. **재현 조건과 한계**: 한계 목록을 먼저 보인다. 모델 · 정책 · k · 비용 단위 설명("회차 비용 = 30문항 전체")은 그 아래에 둔다. 지문 sha256과 provenance는 `<details>` 안에 두고, JSON 다운로드 링크와 다른 두 쇼케이스 링크로 끝낸다.

**화면 문구 사전** (`evidence-research`의 `researchLabels`와 같은 방식으로 컴포넌트 상수로 둔다):

| 기록 값 | 화면 문구 |
| --- | --- |
| `harness` | 스크립트 재집계 |
| `interval_95` | 95% 범위 (이 표본 크기에서 실제 통과율이 있을 법한 범위) |
| `unstable` | 회차마다 결과가 달라진 문항 |
| `automatic_stage` | 자동 판정이 찾은 처음 틀어진 단계 |
| `retrieval_miss` / `question_ambiguity` | 검색에서 정답 근거를 못 찾음 / 질문이 두 가지로 읽힘 |

Wilson이라는 방법 이름은 JSON과 한계 절 상세에만 둔다. 지도 `summary`에는 hit@1 · MRR 대신 "1순위 적중" 같은 평이한 말을 쓴다.

**접근성**:
- 표는 `<caption>`, `th scope="col"`(경로가 드러나는 공개 회차 이름, 예: "HTTP 1" · "스크립트 재집계 #232". 이름에 경로가 없을 때만 경로를 덧붙인다), `th scope="row"`(id + 질문)를 쓴다.
- 칸은 글자로 상태를 말한다(통과 · 실패 · 미실행). 기호를 쓰면 `aria-hidden`이고, 미실행은 실패와 모양이 다른 기호(—)다. 색만으로 구분하지 않는다.
- 범위는 "82.8%에서 99.4%"로 쓴다. 대시 범위를 쓰지 않는다.
- 가로 스크롤이 생기는 표 래퍼는 `tabIndex={0}` · `role="region"` · `aria-label`을 가진다.
- 모든 기록 문자열은 React 텍스트 노드로만 렌더한다(`dangerouslySetInnerHTML` 금지).

**시각 기준** (새 페이지에만 적용):
- notice는 1px 전체 테두리다(`ControlledAiShowcase` 방식). 왼쪽 띠는 쓰지 않는다.
- 최대 폭과 모바일 분기점은 `evidence-research`(1080px · 680px)를 따른다. 표가 가장 많은 쇼케이스이기 때문이다.
- 표 칸은 줄바꿈을 허용한다(`nowrap` 금지). 질문 칸만 넓게 둔다. 지도 표는 680px 이하에서 측정면마다 세로로 쌓고, 칸 이름을 `data-label`로 보인다.
- 결론과 수치는 큰 숫자 타일이나 색 히트맵으로 만들지 않는다. 문장과 표로만 보인다.
- 본문 글자는 `--fg`를 쓴다. `--muted`는 caption과 보조 메모에만 쓰고 12px 미만으로 줄이지 않는다.

**연결**: `ControlledAiShowcase` · `EvidenceResearchShowcase`의 nav에 이 페이지 링크를 더한다. 새 페이지 nav도 같은 두 링크를 가진다.

### D7. 테스트 배치

- Python(`apps/worker/tests/test_evaluation_showcase.py`): export 허용 필드, 금지 필드 거부, D3 불변식 위반 사례(특히 무효 묶음 + 파생 칸 값, `summary` 길이, 거절 합계), 커밋된 `evaluation.json`이 `check`를 통과하는지.
- Dashboard(`apps/dashboard/tests/EvaluationShowcase.test.tsx`):
  - 다섯 구역과 series에서 조립된 결론 문장.
  - 요약표와 HTTP만 줄(경로 혼합).
  - q06 예외 행(안정 실패 · 두 단계 문구 사전 적용).
  - 안정 통과 문항이 `<details>` 안에 있음.
  - q30이 거절 문항으로 표시됨.
  - 미실행 변형 fixture(미실행 칸이 실패로 세지지 않음).
  - 거절 "없음".
  - 무효 묶음이면 결론 · 파생 지도 칸 · 요약표 · 격자에 수치가 없음.
  - HTML이 글자로 보임.
  - 표 머리 scope.
  - 쇼케이스 간 링크.
  - import 경계.
  - `results.json`이 content와 같음.

## Risks / Trade-offs

- [원본 report가 저장소 밖이라 잃어버리면 재export가 불가능하다] → 공개 기록에 sha256을 남기고 `verification.md`의 sha256과 대조할 수 있게 한다. 공개 기록 자체는 CI 검사로 계속 유효하다.
- [curated 지도 값이 측정 로그(`ask-sample-replay.md`)와 어긋날 수 있다] → 칸마다 `measured_at` · `source`를 필수로 둔다. 측정 로그는 계속 측정 기록이고, 지도의 현재 값은 curated 파일만 말한다. 반복 측정 파생 칸은 숫자를 아예 갖지 않는다.
- [`check`의 키 이름 휴리스틱이 정상 필드를 잘못 거를 수 있다] → 허용 목록이 1차 방어이고 휴리스틱은 보조다. 걸리면 필드 이름을 바꾼다.
- [안정 통과 28문항을 접으면 "숨긴다"고 읽힐 수 있다] → 접힌 요약 문구에 문항 수를 적고, 같은 내용을 JSON으로 내려받을 수 있게 한다.
- [격자 30행은 모바일에서 길다] → 기본 화면은 요약표와 예외 행뿐이고, 전체 격자는 펼칠 때만 보인다.
- [위키 hit@8의 무작위 기대(0.589)가 현재 위키 페이지 수 기준인지 확인되지 않았다] → curated로 옮길 때 `ask-sample-replay.md`에서 현재 수집 기준 값이 확인되면 `detail`에 붙인다. 확인되지 않으면 주석을 빼고 "위키 적중은 무작위 기대가 높아 부풀려진다"만 남긴다.

## Migration Plan

배포 단계는 없다. 정적 라우트 추가와 문서 갱신뿐이다. 되돌리기는 PR revert 한 번이며, DB · API · 워커 상태가 바뀌지 않는다.
