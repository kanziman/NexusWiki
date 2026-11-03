# Tenant Isolation 리뷰 — ai-control-risk-policy r1

- 판정: needs_fix
- 대상: `git diff feat/ai-control-output-contract..HEAD` (`a22ea20..993c9d9`)
- 일시: 2026-11-02T23:14:13Z

테넌트 경계를 넘는 경로는 찾지 못했다. 고쳐야 할 것은 승인한 변경이 검색에 반영되지 않거나 승인 없이 메타데이터가 바뀌는, 조용한 실패 쪽이다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `apps/api/src`에 `service_client`와 secret key 사용이 없다. `control/risk`와 승인·거부 API는 전부 `_user_db`(요청자 JWT)다. |
| A-2 | 신규 테이블 RLS 동시 활성화 | 통과 | `0033:39`, `0033:84`. 생성과 같은 트랜잭션이다. 카탈로그로도 `relrowsecurity=t`, 정책 각 1개를 확인했다. |
| A-3 | anon 신규 GRANT·정책 | 통과 | 카탈로그 확인. 두 테이블에 anon 권한이 없고 신규 함수 3개의 anon EXECUTE도 `f`다. 정책은 `to authenticated`뿐이다. |
| A-4 | 워커의 workspace_id 명시 필터 | 통과 | 신규 헬퍼 5개와 `upsert_wiki_write_proposal`이 모두 `workspace_id`를 필수로 받아 필터나 인자로 쓴다. 호출부 값은 잡의 `workspace_id`이고, 페이지 id도 같은 워크스페이스 조회 결과다. |
| A-5 | 복합 FK | 통과 | `wiki_id`와 `raw_source_id`가 `(id, workspace_id)` 복합 FK다(`0033:31-33`, `0033:68-73`). `wiki_page_revisions.raw_source_id`·`job_id`는 FK가 없지만 워커만 쓰고 권한 판정에 쓰이지 않는다. `evidence_chunk_ids`는 `replace_wiki_page_evidence`가 워크스페이스와 원문으로 다시 거른다(`0030`). |
| B-6 | 0행 매핑 | 통과 | 승인 RPC는 definer라 RLS 0행이 아니다. 권한은 함수 머리의 검사가 42501로 막는다. 0행은 없는 제안, 처리된 제안, 다른 테넌트 제안에서 모두 409로 같아 존재 여부가 새지 않는다(`wiki.py:445`). `control/risk`의 빈 결과는 403이다. |
| B-7 | 42501 → 403 | 통과 | `errors.py:262` 단일 핸들러. viewer와 비멤버 403을 `test_wiki_proposals.py`가 실제 RLS로 검증한다. |
| C-8 | 핸들러 멱등성 | **위반** | 페이지 쓰기와 개정은 멱등이지만 `wiki_proposal_apply`의 재실행이 후속 체인을 잃는다. 지적 2. |
| C-9 | jobs 직접 UPDATE | 통과 | 승인 RPC는 INSERT만 하고 핸들러는 `complete_job_and_chain`만 쓴다. `0033:179` INSERT는 승인 UPDATE와 같은 함수 트랜잭션이다. |
| D-10 | iterative_scan | 해당 없음 | 벡터 검색 질의 변경 없음. |
| D-11 | 토크나이저 일치 | 통과 | 적용 핸들러가 컴파일과 같은 `bigram(normalize(content))`와 `TSV_TOKENIZER_VERSION`을 쓴다(`wiki_proposal_apply.py:98-103`). |
| D-12 | search_tsv 생성 컬럼 | 해당 없음 | 변경 없음. |
| D-13 | str.format | 통과 | 변경 파일에 없다. 정책 문구는 치환을 거치지 않는다. |
| D-14 | 인용 앵커 | 통과 | 분쟁 표시는 앵커 뒤에 붙고 앵커와 발급 맵은 그대로다(`ask.py` `_context_blocks`). |
| E-15 | 마이그레이션 번호 | 통과 | 베이스 최대 `0031`, 신규 `0032`~`0034`. `origin/main`은 `0028`까지라 스택 순서대로 병합해야 한다. |

### 요청받은 추가 점검

| 대상 | 결과 | 근거 |
| --- | --- | --- |
| `0033` RLS·권한 | 통과 | `wiki_write_proposals`는 editor 이상만 SELECT, 사용자 쓰기 없음. `wiki_page_revisions`는 멤버 SELECT만. `supabase/tests/wiki_write_control.sql` 오류 없음. |
| `decide_wiki_write_proposal` | 통과 | 역할 검사가 UPDATE보다 먼저이고 UPDATE가 `workspace_id`로 한정된다. 자기 워크스페이스 경로로 남의 제안을 지목해도 0행이다. `pending` 술어로 경합 시 한쪽만 성공한다. service_role EXECUTE는 회수됐다. |
| 승인과 잡 등록의 원자성 | 통과 | 한 함수 호출 안이라 잡 INSERT가 실패하면 승인도 롤백된다. `jobs_source_reference_guard`도 통과한다. |
| `upsert_wiki_write_proposal` | 통과 | invoker이고 service_role만 EXECUTE(`t`), authenticated·anon은 `f`. 복합 FK가 페이지와 원문의 테넌트 불일치를 막는다. |
| `wiki_page_publications` 컬럼 권한 | 통과 | service_role SELECT는 `wiki_page_id`, `workspace_id`뿐이다. 발행본 본문은 열리지 않는다. |
| `control_risk_snapshot` | 통과 | viewer 미만 42501, 전 집계가 `workspace_id`로 한정, viewer에게 `policy_versions`는 `[]`. 본문과 사용자 식별자를 돌려주지 않는다. |
| viewer의 제안 본문 | 통과 | API는 `can_view`일 때만 조회하고 RLS도 막는다. 직접 PostgREST 조회도 `[]`임을 테스트가 확인한다. 잡 응답은 payload를 내보내지 않고 로그에도 본문이 없다. |
| 컴파일 개정 순서·재실행 | 통과 | 개정 INSERT가 덮어쓰기보다 먼저다(`compile.py:454`, `:471`). 재실행은 `(wiki_id, job_id)` 충돌로 최초 이전 본문을 유지한다. 지문은 성공한 잡만 보므로 실패한 재실행이 건너뛰기로 단락되지 않는다. |
| 정책·`data_collection` 누락 경로 | 통과 | `/chat/completions` POST는 `llm.py:228`, `:464` 두 곳뿐이고 각각 `_chat_stream_body`, `_chat_body`를 거친다. 프롬프트 전용 재요청도 `_chat_body`다. API에는 공급자 키와 호출이 없다. |
| 적용 핸들러 부분 실패 | **위반** | 개정·업서트·색인 사이 중단은 안전하다. 적용 표시 뒤 중단은 지적 2다. |
| 적용 핸들러의 조용한 실패 | **위반** | 지적 1, 2, 5. |

### 실행한 검증

- `uv run pytest apps/api/tests/test_wiki_proposals.py apps/worker/tests/test_risk_policy.py apps/api/tests/test_tenant_isolation_full_path.py`: 69 passed
- `uv run pytest apps/worker/tests/test_service_client.py apps/worker/tests/test_llm.py apps/worker/tests/test_llm_gateway.py apps/worker/tests/test_llm_stream.py apps/api/tests/test_control_router.py`: 99 passed
- `supabase/tests/wiki_write_control.sql`: 오류 없음
- 지적 1, 2, 3은 실제 핸들러 함수에 스텁 DB를 넣어 재현했다. 저장소 밖 임시 스크립트이며 관측값은 각 항목에 적었다.

기존 테스트가 모두 통과하는데도 아래 결함이 남아 있다. 지적 2의 동작은 오히려 기존 테스트가 정답으로 고정하고 있다.

## 조치가 필요한 항목

1. **승인한 본문이 벡터 색인에 반영되지 않는다** (심각도: 높음)
   - 위치: `apps/worker/src/worker/handlers/embed.py:73-79`, `apps/worker/src/worker/handlers/wiki_proposal_apply.py:112`
   - 깨지는 것: `embed`의 wiki 범위는 `chunk_index`가 이미 있으면 내용과 무관하게 건너뛴다. `wiki_embeddings`를 지우는 트리거나 코드도 없다. 그래서 승인 적용 뒤 같은 번호의 청크는 옛 본문의 임베딩과 `chunk_content`로 남는다. 새 본문에만 있는 내용은 벡터 채널과 임베딩 기반 충돌 검사에서 보이지 않고, 옛 본문으로 페이지가 검색된다. 재현에서 본문이 완전히 바뀐 페이지의 재임베딩 행 수는 0이었고 잡은 정상으로 `conflict_check`까지 이어졌다. 어휘 색인만 갱신되므로 오류가 드러나지 않는다. 핸들러 주석의 "임베딩을 새 본문으로 다시 맞춘다"와 스펙의 "검색 색인까지 갱신한다"가 지켜지지 않는다. `embed.py`의 동작 자체는 이번 change 이전부터 있었고 컴파일 덮어쓰기도 같은 영향을 받지만, 이 change의 새 계약이 여기에 의존한다.
   - 조치: `list_wiki_embeddings`가 `chunk_content`도 읽게 하고, 내용이 다른 청크를 재임베딩 대상에 넣는다. 적용 뒤 `embed`를 실행해 `chunk_content`가 새 본문으로 바뀌는지 보는 테스트를 추가한다.

2. **적용 표시 뒤 실패하면 재실행이 링크·임베딩 체인을 영구히 잃는다** (심각도: 높음)
   - 위치: `apps/worker/src/worker/handlers/wiki_proposal_apply.py:53-56`, `:110-117`
   - 깨지는 것: `applied` 표시와 체인 등록은 별도 왕복이다. 그 사이에 워커가 죽거나 `complete_job_and_chain`이 일시 실패하면, 재실행은 `applied`를 보고 `next_type` 없이 잡을 완료한다. 재현 관측값은 1차 예외 뒤 제안 `applied`, 재실행 체인 호출 `[None]`이다. 잡은 `succeeded`인데 `link_sync` 이후 단계가 생기지 않아 `wiki_links`와 임베딩이 옛 본문에 머문다. 제안은 이미 `applied`라 다시 처리할 경로도 없다. 스테일 회수로 두 워커가 겹칠 때도 체인 없는 완료가 먼저 끝나면 같은 결과다. `test_risk_policy.py:410-419`가 `applied`에서 `chained == [{}]`를 단언해 이 동작을 고정하고 있다.
   - 조치: `applied` 상태의 재실행도 `link_sync`를 체인한다. 후속 잡은 멱등이고 체인 INSERT는 `on conflict do nothing`이다. `rejected`, `pending`, 제안 없음만 체인 없이 완료한다. 테스트의 `applied` 케이스를 함께 고친다.

3. **`enforce`에서도 본문이 같으면 검증·공개 페이지의 메타데이터가 승인 없이 바뀐다** (심각도: 보통)
   - 위치: `packages/core/src/nexuswiki_core/wiki_write_policy.py:48-49`, `apps/worker/src/worker/handlers/compile.py:433`, `:471`
   - 깨지는 것: 분류는 본문만 비교한다. 본문이 같으면 `changed=False`로 보류와 개정을 모두 건너뛰고, 업서트가 `title`, `category`, `aliases`, `confidence`를 덮어쓴다. 재현에서 검증 완료이자 공개된 페이지를 `enforce`로 처리했을 때 제안 0건, 개정 0건이었고 `category`, `aliases`, `confidence`가 모델 값으로 바뀌었다. `slugify`가 대소문자와 구두점을 접으므로(`Foo Bar`와 `FOO-BAR!`가 같은 슬러그) 제목도 같은 경로로 바뀐다. 스펙의 "`high` 쓰기는 페이지를 바꾸지 않고"에 어긋나고, 개정에 `previous_title`을 두는 의도와도 맞지 않는다.
   - 조치: 메타데이터까지 비교해 변경으로 판정하거나, 본문이 같은 `high` 대상에서는 `sources` 합집합만 쓰고 나머지를 보존한다. 스펙의 "본문이 같으면 개정을 남기지 않는다"와 어떻게 맞출지는 스펙에도 적는다.

4. **리스크 탭이 워크스페이스의 위키 전체를 제한 없이 읽어 검토 화면의 현재 본문이 빌 수 있다** (심각도: 보통)
   - 위치: `apps/api/src/api/routers/control.py:632-636`, 표시는 `apps/dashboard/components/ControlRoom.tsx`의 `<pre>{proposal.current_content}</pre>`
   - 깨지는 것: 대기 제안이 최대 20건인데 조회는 워크스페이스 전 페이지의 `content`를 `limit`과 `order` 없이 가져온다. `supabase/config.toml:18`의 `max_rows = 1000` 때문에 페이지가 1000개를 넘으면 결과가 오류 없이 잘린다. 그러면 대상 페이지의 `slug`, `current_title`, `current_content`가 `null`이 되고, 편집자는 빈 현재 본문을 보고 승인 여부를 정한다. 잘림이 없어도 탭을 열 때마다 위키 전문을 전송한다. 코드와 설정으로 판단했고 1001개 페이지로 실측하지는 않았다.
   - 조치: 제안의 `wiki_id`로 `id=in.(...)` 조회를 한다. `_fetch_evidence_content`의 방식과 같다. 대상 페이지를 찾지 못한 제안은 빈 본문으로 보여 주지 말고 구분해 표시한다.

5. **승인 후 적용 잡이 끝내 실패하거나 취소되면 어디에도 보이지 않고 되돌릴 수 없다** (심각도: 보통)
   - 위치: `supabase/migrations/0034_control_risk_tab.sql:51-56`, `apps/api/src/api/routers/jobs.py:33-40`, `apps/worker/src/worker/handlers/wiki_proposal_apply.py:53`
   - 깨지는 것: 제안은 승인 즉시 `pending`에서 벗어나 목록에서 사라지는데, 집계는 `pending`, `applied`, `rejected`만 센다. 잡이 `dead`나 `canceled`로 끝나면 제안은 `approved`에 머물고 탭의 모든 수치에서 빠진다. 페이지는 그대로인데 승인한 사람은 반영됐다고 믿게 된다. 잡 패널에서는 `STEP_LABELS`에 없어 "알 수 없는 단계"로 나온다. `dead`는 `retry_dead_job`으로 살릴 수 있지만, 취소된 잡은 재시도도 재승인도 할 수 없다.
   - 조치: `approved` 건수를 집계와 화면에 "반영 대기"로 추가하고 `STEP_LABELS`에 라벨을 넣는다. 취소된 경우의 복구 경로(취소 금지 또는 재등록)를 정한다.

6. **화면의 쓰기 모드가 실제 쓰기 분기와 다른 설정을 읽는다** (심각도: 보통)
   - 위치: `apps/api/src/api/routers/control.py:660`, `apps/api/src/api/settings.py`, `apps/worker/src/worker/settings.py`
   - 깨지는 것: 실제 분기는 워커의 `AI_CONTROL_RISK_MODE`인데 화면은 API 서비스의 같은 이름 변수를 읽는다. 두 서비스는 환경변수가 따로다. API만 `enforce`로 두면 화면은 "보류"라고 표시하지만 워커는 검증 페이지를 계속 덮어쓴다. 반대로 워커만 올리면 화면은 `shadow`로 남는다. 어느 쪽도 오류가 나지 않는다.
   - 조치: 최소한 `docs/reference/stack.md`와 `.env.sample`에 두 서비스에 함께 설정해야 한다고 적는다. 가능하면 워커의 실제 모드를 사용량 메타데이터 등에 기록하고 그것을 표시한다.

## 참고 (이번 판정의 근거는 아니며, 수정 여부는 구현자가 정한다)

- `delete_raw_source`의 진행 중 잡 검사(`0021:387`)에 `wiki_proposal_apply`가 없다. 승인 직후 큐에 있는 동안 원문을 지우면 제안이 cascade로 사라지고 잡은 no-op으로 끝나 승인이 흔적 없이 사라진다. 실행 중인 경우는 `wiki_pages_source_reference_guard`가 막는다.
- 승인 RPC는 월 비용 상한을 보지 않는다. `enqueue_source_job`과 달리 상한을 넘긴 워크스페이스에서도 뒤따르는 `embed`, `conflict_check` 비용이 발생한다.
- 분류와 업서트가 한 트랜잭션이 아니다. 그 짧은 사이에 페이지가 검증되면 덮어쓰인다. 재현하지는 않았다.
- `llm.py:430` 주석은 재요청에서 `provider`를 뺀다고 적혀 있으나 코드는 `data_collection`을 유지한다. 코드가 맞고 주석이 낡았다.
- `tasks.md`가 검증 명령에 든 `test_tenant_isolation_full_path.py`에는 신규 두 테이블 행이 없다. 격리 자체는 `test_wiki_proposals.py`가 검증한다.

## 판정 근거

테넌트 경계와 관련된 A, B 항목과 요청받은 권한 점검은 코드, 실제 RLS 테스트, 카탈로그 조회에서 모두 통과했다. definer 함수의 역할 검사와 교차 테넌트 차단, viewer 경계, 승인과 잡 등록의 원자성에도 문제가 없다. 반면 지적 1과 2는 승인한 변경이 검색과 링크에 반영되지 않은 채 잡이 성공으로 기록되는 조용한 실패이고, 스펙의 "검색 색인까지 갱신한다"를 지키지 못한다. 지적 3은 `enforce` 보류의 우회다. 모두 코드 수정으로 해결되고 테넌트 경계를 넘지 않으므로 `blocked`가 아니라 `needs_fix`다. 지적 1~6을 고친 뒤 라운드를 올려 재리뷰한다.
