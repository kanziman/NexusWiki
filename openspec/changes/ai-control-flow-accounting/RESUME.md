# 재개 안내: ai-control-flow-accounting

에이전트 메모리는 컴퓨터마다 따로 있어서, 재개에 필요한 내용을 여기에 옮겼다. 이 작업을 끝내고 PR을 만들기 전에 이 파일을 지운다.

## 현재 상태 (2026-11-02, Mac)

- 브랜치는 `feat/ai-control-flow-accounting`이고, 기준 커밋은 `79b68fe`다. 원격에 중간 저장 커밋 2개가 있고 PR은 아직 없다.
- 조치는 전부 **커밋하지 않은 작업 트리**에 있다. 남은 task는 7.3뿐이다. 클라우드에는 아무것도 적용하지 않았다.
- 코드 작업은 끝났다. 이 문서를 읽는 에이전트의 일은 아래 "다음에 할 일"뿐이다. 코드를 더 고치거나 리뷰를 다시 돌리지 않는다.

## 리뷰 게이트 경위 (PR 본문에 그대로 적는다)

프로젝트 규칙의 3라운드 안에 `pass`를 받지 못했고, 사용자가 승인해 진행한다.

| 라운드 | 스펙 | 격리 | 내용 |
| --- | --- | --- | --- |
| r1 | needs_fix | blocked | 로그인 없이 다른 워크스페이스에 비용 기록 (치명, 해소) |
| r2 | needs_fix | needs_fix | 깨진 프레임이 `resolved`로 저장 등 (해소) |
| r3 | needs_fix | needs_fix | trace 검사가 직접 INSERT로 우회됨. `blocked` 확정 후 사용자가 코드 수정과 확인 리뷰를 승인 |
| r4 | pass | needs_fix | `0023`이 `0025`의 컬럼에 의존 등 (해소) |
| r5 | (실행 안 함) | needs_fix | `design.md` 문장 1개가 사실과 다름. 코드 지적 없음. 사용자가 문장 수정 후 재리뷰 없이 진행을 승인 |

r5 뒤에 고친 문서와 r4 뒤의 스펙 문구(같은 워크스페이스 한정, 삭제된 턴의 trace)는 리뷰어가 다시 보지 않았다. 테넌트 경계를 넘는 경로와 불변 규칙 위반은 r2 이후 어느 라운드에서도 찾지 못했다.

## 다음에 할 일

순서를 지킨다. 커밋 메시지 형식은 `docs/reference/commit.md`, 범위와 안전 규칙은 `openspec/specs/pull-request-workflow/spec.md`를 따른다.

1. 관련 검증을 새로 실행한다. `reviews/` 보고서도 커밋 대상이다. 작업 트리에 이 change와 무관한 파일이 있으면 포함하지 말고 사용자에게 알린다.
2. 코드를 커밋한다.
3. task 7.3: 작업 트리의 측정 대상이 깨끗한 상태에서 증거를 다시 생성해 커밋하고 `- [x]`로 표시한다.
   - `uv run python apps/worker/tests/test_controlled_ai_evidence.py measure <out>`
   - `uv run python apps/worker/tests/test_controlled_ai_evidence.py write after <out>`
   - `uv run pytest apps/worker/tests/test_controlled_ai_evidence.py` 이때 스킵되던 방어 테스트가 실제로 돌아 통과해야 한다.
4. `/opsx:sync`와 `/opsx:archive`를 브랜치에서 실행해 PR에 포함한다. 머지 뒤로 미루지 않는다.
5. 이 파일을 지운다. 아카이브로 옮겨지기 전에 지운다.
6. `/create-pr`로 PR을 만들고 CI 결과를 명령 응답으로 확인한다. 머지하지 않는다.

PR 본문에 적을 것: 위 경위 표, 아래 "PR에 적을 알려진 한계", 후속 이슈 #170, #171, #172.

## PR에 적을 알려진 한계

- 최종 사용량 전에 끊긴 Ask 호출은 비용 0으로 기록되어, 끊기를 반복하면 Ask 비용이 월 상한을 비켜 갈 수 있다 (#172). 실제 청구액은 확인하지 않았다.
- 턴이 끝나기 전에 클라이언트가 끊으면 턴이 `streaming`에 남는다 (#170).
- 위조 토큰의 401은 로컬에서만 확인했다. 클라우드 게이트웨이의 응답 코드가 `PGRST30x`가 아니면 500이 되며, 이때도 임베딩 호출과 비용은 생기지 않는다. 적용 뒤 확인 절차는 `docs/ops/migration-0023-0026-record.md`에 있다.
- 병합 후 `after.commit`을 `main` 해시로 바꾸는 후속 PR이 필요하다 (#171).
- 실제 공급자, 실제 Langfuse 서버, 실제 워커 프로세스로 끝까지 돈 적이 없고, 화면을 실제 브라우저로 확인하지 않았다.
- `0025`, `0026`을 첫 로컬 적용 뒤 직접 수정했으므로, 이전 내용이 적용된 다른 로컬 DB(Windows 포함)는 `supabase db reset`이 필요하다.

## 이미 아는 실패

- `next build`: Windows에서 `next/font` 로더의 파싱 오류로 한 번 실패했고 재시도에서 통과했다. Mac에서는 통과했다.
- `test_tenant_isolation_full_path.py`: Windows에서 간헐적으로 실패했고 원인을 모른다. Mac에서는 여러 번의 전체 실행과 3회 연속 단독 실행에서 나타나지 않았다.
- 대시보드 전체 테스트는 `vitest run --testTimeout=30000`으로 돌린다. 기본 5초에서는 부하로 시간 초과가 날 수 있다.

## 환경에서 알아둘 점

- 대시보드의 한 파일만 돌릴 때는 `./node_modules/.bin/vitest run tests/X.test.tsx`를 쓴다. `pnpm test -- X`는 필터가 먹지 않고 전체를 돈다.
- `service_role`은 `ask_messages`를 조회할 수 없다. 테스트에서는 작성자 JWT로 읽는다.
- 누출 검사 표식은 ASCII여야 한다. 한글은 JSON 직렬화와 콘솔 인코딩에서 형태가 바뀌어 유출되어도 검사를 통과한다.
