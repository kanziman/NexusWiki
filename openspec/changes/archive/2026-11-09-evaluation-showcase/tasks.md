# Tasks — evaluation-showcase

- Umbrella Issue: https://github.com/kanziman/NexusWiki/issues/249

## 1. 반복 측정 요약과 결론이 공개 페이지에 보인다 (https://github.com/kanziman/NexusWiki/issues/250)

의존성: 없음. 예상: 1일. 유료 호출: 없음.

- [x] 1.1 `scripts/evaluation_showcase.py`에 `export`와 `check`를 만든다. 이 슬라이스에서는 `schema` · `generated_at` · `provenance` · `synthetic` · `series`(문항 제외: `valid` · `invalid_reason` · `key` · `runs` · `spread` · `stability_counts`) · `limitations`를 허용 목록으로 내보낸다. 회차 이름은 공개용 이름으로 바꾸고, 구간은 `ask_replay_reliability.wilson_interval`로 다시 계산해 검사한다. 보존된 `reliability-report.json`으로 `apps/dashboard/content/evaluation.json`을 만든다(설계 D1 · D2 · D3).
- [x] 1.2 `/showcase/evaluation` 페이지와 `results.json` 라우트를 `force-static`으로 만든다. 머리(제목 · series에서 조립한 결론 문장 · 합성 샘플 notice · 점프 목차), 회차 요약표, HTTP 회차만 줄, 거절 성능 블록, 재현 조건과 한계 구역, 무효 상태를 그린다. 기존 두 쇼케이스 nav와 새 페이지 nav가 서로 연결된다. 화면 문구 사전 · 접근성 · 시각 기준은 설계 D5 · D6을 따른다.

Given 보존된 3회차 report, When export 후 페이지를 렌더링하면, Then 결론은 "세 번 모두 답할 수 있는 29문항 중 28개"를 말하고, 요약표에는 회차마다 경로 · 30/30 실행 · 28/29 · "82.8%에서 99.4%" · 비용이 보이며, HTTP 회차만 줄이 따로 보인다.
Given 같은 기록, When 거절 블록을 보면, Then 회차마다 답할 수 있는 문항 통과 28/29 · 정확한 거절 1/1 · 잘못된 거절 0/29와 "거절 문항 1개"가 보인다.
Given `refusal_asked`가 0인 회차가 있는 변형 기록, When 렌더링하면, Then 그 회차의 정확한 거절은 0이 아니라 "없음"이다.
Given `series.valid`가 false이고 이유가 있는 변형 기록, When 렌더링하면, Then 결론 · 요약표 · 거절 블록에 수치가 없고 무효와 이유가 보인다.
Given 회차의 `interval_95`나 `answerable_passed`를 바꾼 기록, When `check`를 실행하면, Then 실패한다.
Given 허용 목록 밖 키나 `workspace_id` · `answer` 키가 든 기록, When `check`를 실행하면, Then 실패한다.
Given 로그인하지 않은 방문자, When `/showcase/evaluation`과 `results.json`을 열면, Then 로그인 화면으로 가지 않고 `results.json`은 content JSON과 같다.
Given 페이지 컴포넌트와 라우트 소스, When import 경계 테스트를 실행하면, Then Supabase · API 클라이언트 import가 없다.
Given `controlled-ai` 또는 `evidence-research` 페이지, When nav를 보면, Then `/showcase/evaluation` 링크가 있다.

검증: `uv run pytest apps/worker/tests/test_evaluation_showcase.py && uv run ruff check apps packages scripts/evaluation_showcase.py && uv run python scripts/evaluation_showcase.py check apps/dashboard/content/evaluation.json && pnpm --dir apps/dashboard test && pnpm --dir apps/dashboard typecheck && pnpm --dir apps/dashboard lint`

## 2. 문항 격자가 예외부터 보인다 (https://github.com/kanziman/NexusWiki/issues/251)

의존성: 1. 예상: 반나절~1일. 유료 호출: 없음.

- [x] 2.1 export에 `series.questions[]`(`id` · `query` · `kind` · `outcomes` · `stability` · `known_failure` · `reported_stage` · `automatic_stage` · `note`)를 더한다. 질문 문구와 유형은 `scripts/fixtures/ask_replay.v1.json`, 메모는 `scripts/fixtures/ask_replay_labels.v1.json`에서 가져온다. `check`에 문항 수 · 거절 문항 수 · `kind`별 합계 · 안정성 재유도 · 미실행 불변식을 더한다(설계 D2 · D3).
- [x] 2.2 반복 측정 구역에 예외 우선 격자를 그린다. 안정 통과가 아닌 문항은 펼친 표, 세 번 모두 통과한 문항은 `<details>` 안에 둔다. 보고 단계 · 자동 단계 · 메모는 행 아래 설명 줄로 붙이고, q30은 거절 문항으로 표시한다. 표 머리 scope, 글자 상태, 미실행 기호, 키보드 스크롤 래퍼를 지킨다(설계 D6).

Given 보존된 3회차 report, When 격자를 보면, Then 펼친 표에 q06 한 행만 있고 세 칸 모두 실패 · 안정 실패이며, 그 아래에 "질문이 두 가지로 읽힘"(보고)과 "검색에서 정답 근거를 못 찾음"(자동)이 함께 보인다.
Given 같은 기록, When 접힌 영역을 열면, Then 세 번 모두 통과한 문항 수가 요약 문구와 같고 q30은 "거절 문항"으로 표시된다.
Given 한 회차가 일부 문항에서 멈춘 변형 기록, When 렌더링하면, Then 그 칸은 "미실행"이고 실패 수와 요약표 통과 수에 들어가지 않으며, 그 문항은 펼친 표에 보인다.
Given 질문 문구에 `<script>`가 든 변형 기록, When 렌더링하면, Then 글자 그대로 보이고 실행되지 않는다.
Given `outcomes`와 다른 `stability`나 `kind`별 합계가 안 맞는 기록, When `check`를 실행하면, Then 실패한다.
Given 격자 표, When 접근성 트리를 보면, Then 열 머리는 회차 이름과 경로를, 행 머리는 id와 질문을 가진다.

검증: 1과 같은 명령.

## 3. 평가 지도와 적용 원장이 하나의 원본에서 보인다 (https://github.com/kanziman/NexusWiki/issues/252)

의존성: 1. 예상: 1일. 유료 호출: 없음.

- [x] 3.1 `scripts/fixtures/evaluation_showcase.curated.v1.json`을 만든다. `evaluation-map.md` §2의 10칸과 §5의 7행을 옮기고, 정답성 · 거절 칸은 `derived_from`(`series.answerable` · `series.refusal`)로 둔다. 검색 행은 2026-11-09 값으로 바꾸고, 도구 궤적은 `empty` + 이유로, 상대 증거와 강의 편 번호는 고정 참조로 바꾼다. 위키 hit@8 무작위 기대(0.589)는 현재 수집 기준임이 `ask-sample-replay.md`에서 확인될 때만 `detail`에 둔다(확인 결과 위키 13쪽 시절 값이라 빼고 설명만 남겼다). 출처에서 확인되지 않는 근거성 문장 비율(0.578 · 0.374)은 옮기지 않는다. export가 지도 · 원장을 합치고, `check`에 지도 · 원장 불변식을 더한다(설계 D2 · D3 · D4).
- [x] 3.2 평가 지도(행마다 상태 · 한 줄 요약 · 측정일 · 출처 링크, 상세는 접기, 파생 칸은 series에서 조립 + 반복 측정 앵커)와 적용 원장(`<ol>` 타임라인, 첫 문장 = 측정이 바꾼 것)을 그린다. `evaluation-map.md` §2 · §5 표를 curated 파일과 페이지로 가는 링크로 바꾼다(설계 D4 · D6).

Given curated 파일과 보존된 report, When 지도를 보면, Then 10개 측정면이 모두 보이고, 수치가 있는 칸마다 분모 · 측정일 · 출처가 있으며, 정답성 칸은 "3회 모두 28/29"를 series에서 만들어 보인다.
Given 비어 있음 상태인 모델 선택 · 판사 자체 · 위키 컴파일 품질 · 도구 궤적, When 지도를 보면, Then 수치 없이 이유가 보인다.
Given `series.valid`가 false인 변형 기록, When 지도를 보면, Then 정답성 · 거절 칸은 무효를 보이고 28/29가 없다.
Given `derived_from`(`series.answerable` · `series.refusal`) 칸에 `summary` 값이 든 curated 파일, When `check`를 실행하면, Then 실패한다.
Given 60자를 넘는 `summary`, 날짜 역순 원장, `changed`가 빈 원장 항목, When `check`를 실행하면, Then 각각 실패한다.
Given 원장 7항목, When 원장을 보면, Then 날짜 오름차순이고 각 항목의 첫 문장이 측정이 바꾼 것이다.
Given 원장 설명에 HTML이 든 변형 기록, When 렌더링하면, Then 글자 그대로 보인다.

검증: 1과 같은 명령 + `rtk proxy grep -n "showcase/evaluation\|evaluation_showcase.curated" docs/ops/evaluation-map.md`

## 4. 최종 검증과 스펙 정리

- [x] 4.1 관련 테스트 · typecheck · lint · `openspec validate evaluation-showcase --strict`를 새로 실행하고, 페이지를 로컬에서 띄워 데스크톱 · 375px 화면을 확인한다. spec-conformance-reviewer를 수행해 지적 사항을 해소한다. 사용자 결정(2026-11-09)으로 tenant-isolation-reviewer 게이트는 생략한다. API · DB · RLS 변경이 없다.
- [x] 4.2 delta spec을 정본에 동기화하고 `openspec validate --specs`를 통과시킨 뒤 archive하고, 한국어 커밋과 PR을 만든다.

## 추적과 승인

Umbrella: https://github.com/kanziman/NexusWiki/issues/249

Gate 1~4는 사용자가 승인했다. 구현은 별도 `/opsx:apply` 요청이 필요하다.

- 1.1~1.2: https://github.com/kanziman/NexusWiki/issues/250
- 2.1~2.2: https://github.com/kanziman/NexusWiki/issues/251
- 3.1~3.2: https://github.com/kanziman/NexusWiki/issues/252
