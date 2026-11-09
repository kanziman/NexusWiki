# 제한된 도구 재검색 평가

변경 계약과 설계: `openspec/changes/ask-evidence-research/`. 추적: https://github.com/kanziman/NexusWiki/issues/227.

## 최종 결과 (2026-11-09)

판단 스트림 소비를 고친 코드에서 OFF/ON 1쌍을 새로 측정했다. 두 기록 모두 42문항이며 조건 해시가 일치하고 측정 장애는 0건이다.

- 통과는 OFF·ON 모두 39/42다. 위조 인용은 둘 다 0이다.
- ON에서 실제 재검색은 1문항(q30)뿐이며 그 문항은 OFF에서도 통과했다. 판단은 40문항이 충분, 1문항(q28)이 출력 상한 잘림으로 실패했다.
- 복구 대상 문항이 0건이라 복구율은 미측정이다.
- 전체 비용은 OFF $1.220335, ON $2.030962로 66.4% 늘어 상한 50%를 넘는다. 총 지연 p95는 20.973초에서 22.156초다.
- 채택 판정은 **불채택**이다(답변 복구·통과 증가·비용 상한 미충족). 기본 설정은 OFF로 유지한다. 반복 안정성은 미측정이다.

원본은 Git 밖 `.worktrees/research-fix-20261109/`에 있고 sha256과 실제 지출($3.309429)은 change의 `verification.md`에 있다. 그 전의 v4 쌍은 한 ON 안에 판단 설정이 섞였고(`measurement-audit.md`), 2026-11-08 최종 실행의 ON은 q28 잘림으로 중단돼 둘 다 비교 근거로 쓰지 않는다.

ON 실행 중 OpenRouter 크레딧이 소진되면 워커가 응답 헤더를 보낸 뒤라 402가 연결 끊김으로 전달된다. 평가기는 이를 측정 장애로 잡고 중단하므로, 충전 뒤 서버를 재시작하지 말고 `--resume-from <중단 기록>`으로 남은 문항만 이어서 실행한다. 코드를 바꾸면 실행 지문이 달라져 재개가 거부된다.

## 이전 측정 상태

2026-11-08, 합성 문서 8개를 한 번 수집해 만든 위키 13쪽에서 기존 30문항과 전용 12문항을 실행했다. 답변 모델은 `anthropic/claude-sonnet-4.6`, 검색 정책은 `hybrid-rrf-v1`이며 RRF 작업 브랜치의 미커밋 변경은 포함하지 않았다.

최초 OFF 42문항은 38개 통과, 위조 인용 0, 전체 호출 비용 $1.203720, 총 지연 p50 9.862초 / p95 18.883초였다. ON 1차는 27번째 문항의 답변 공급자 호출이 HTTP 403으로 실패했다. OpenRouter 키 상태 조회에서 한도 $5, 잔여 한도 0을 확인했다. 이후 임베딩 실패와 내부 rate limit이 이어져 나머지 반복 실행도 오염됐다.

**유효한 OFF/ON 3쌍 비교는 아직 완료되지 않았다.** 실패 기록의 통과율·짧은 지연·0원 비용을 성능 개선이나 기능 회귀로 해석하지 않는다. 공개 페이지는 이를 측정 장애로 표시하고 비교 요약을 숨긴다. 기본 기능 설정은 OFF다. 처음 ON에서 정상적으로 판단한 27턴은 모두 추가 검색 없이 충분하다고 판단했으며, 전용 12문항은 공급자 장애 이후라 복구 효과를 판단할 수 없다.

원본 파일과 스냅샷은 `/private/tmp/nexuswiki-research-eval/`에 있다. 이곳의 state에는 자격증명이 있고 실행 원본에는 문서·임베딩 사본이 있어 커밋하지 않는다. 공개 데이터는 합성 질문·허용된 요약·문항 판정·조건 해시만 포함하는 `apps/dashboard/content/evidence-research.json`이다. revision은 커밋 전 작업트리의 기준 HEAD로 표시한다.

## 재실행

키 한도를 조정한 뒤에도 문서는 재수집하지 않는다. 기존 실패 파일을 덮어쓰지 말고 새로운 결과 디렉터리를 사용한다. baseline과 동일한 서버 설정·문서 스냅샷·모델·프롬프트·RRF 정책·fixture를 유지한다. 아래의 state 경로는 기존 수집 결과를 가리킨다.

```bash
ASK_REPLAY_ENV_FILE=/Users/zorba/projects/NexusWiki/.env \
ASK_REPLAY_RESEARCH_API_PORT=8032 \
bash scripts/ask_replay_serve.sh /private/tmp/nexuswiki-evidence-research /tmp/research-rerun/logs

# 최초 실행 예시다. 현재는 pair 1이 완료돼 있으므로 아래 유료 호출은 다시 실행하지 않는다.
uv run python scripts/evidence_research_eval.py \
  --state /private/tmp/nexuswiki-research-eval/state.json \
  --out /tmp/research-rerun/off-1.json --mode off --pair 1 \
  --runtime-manifest /tmp/research-rerun/logs/evaluation-runtime.json \
  --model anthropic/claude-sonnet-4.6 --api http://127.0.0.1:8031
uv run python scripts/evidence_research_eval.py \
  --state /private/tmp/nexuswiki-research-eval/state.json \
  --out /tmp/research-rerun/on-1.json --mode on --pair 1 \
  --runtime-manifest /tmp/research-rerun/logs/evaluation-runtime.json \
  --model anthropic/claude-sonnet-4.6 --api http://127.0.0.1:8032

# 현재는 pair 1의 두 기록만 읽어 공개용 사본을 새 파일로 생성한다. 네트워크를 쓰지 않는다.
uv run python scripts/evidence_research_eval.py export /tmp/research-rerun /tmp/research-public.json
```

평가 도구는 실제 API 모드·답변 모델을 확인하고 첫 측정 장애 시 부분 기록을 저장한 뒤 중단한다. 기록된 모든 LLM 호출과 질의 임베딩의 비용·토큰을 합산한다. 일반 `ask_replay.py ask`의 기존 비용 필드 의미는 유지한다. 전체 호출을 포함하는 것은 재검색 평가 전용 실행이다.

서버 시작 시 키를 제외한 실제 모델 출력 상한·컨텍스트 예산·품질 모드·임베딩 설정·동시성 manifest를 남기고 이를 비교 조건으로 해시한다. 초기 실패 기록에는 이 manifest가 없으므로 조건 검증도 미완료로 표시한다. 정상 재실행에는 manifest가 필수다.

포트폴리오 경로는 `/showcase/evidence-research`다. 페이지는 버전 있는 공개 사본만 정적으로 읽으며 운영 API·DB·모델을 호출하지 않는다. 공개 JSON을 교체하기 전에 조건 일치·측정 완전성·허용 필드 export를 검사한다.
