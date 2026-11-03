# 위키 청크 근거 백필 운영 절차 및 검증 기록

관련 이슈: #210 (`backfill-wiki-evidence`), 하위 이슈 #211 · #212 · #213
계약 정본: `openspec/changes/backfill-wiki-evidence/design.md` (아카이브 후 `openspec/specs/wiki-compilation/spec.md`)

## 1. 목적과 권한 경계

기존 위키 페이지(특히 `verification_status = 'verified'`인 검증 완료 페이지)를 재컴파일하지 않고, 페이지의 본문·제목·메타데이터·검증 상태·검색 색인(`search_tsv`, `wiki_embeddings`, `wiki_links`)과 기존 근거를 보존하면서 청크 근거(`wiki_page_evidence`)만 대조·추가한다.

⚠️ **운영 쓰기 금지 경계**
- 에이전트는 로컬 개발 스택에서의 코드·마이그레이션·합성 데이터 검증까지만 수행하며, **운영 DB 마이그레이션 적용, 운영 `apply` 실행, 재컴파일 잡 실행, PR 머지를 수행하지 않는다.**
- 운영 DB 마이그레이션(`0035_wiki_evidence_backfill.sql`) 선적용과 `supabase migration list --linked` 원장 확인, 실제 백필 검토 및 `apply` 실행은 **운영자가 별도로 승인·실행**한다.

## 2. 운영 적용 전 마이그레이션 게이트

`0035_wiki_evidence_backfill.sql`은 새 테이블이나 기존 테이블 DDL 변경 없이 `service_role` 전용 함수 3개(`wiki_evidence_backfill_token`, `wiki_evidence_backfill_candidates`, `apply_wiki_evidence_backfill`)만 추가하므로 현재 운영 애플리케이션 코드와 호환된다. `public` · `anon` · `authenticated` 실행 권한은 즉시 회수된다.

운영자는 PR 머지 및 백필 도구 실행 전에 다음 순서를 직접 확인한다.

1. 원격 마이그레이션 상태 조회 (`Supabase CLI 2.111.0` 기준):
   ```bash
   supabase migration list --linked
   ```
   - 2026-11-03 조회 기준 원격(`dajhhwbkfdaqnuenulsb`)은 `0001`~`0031`까지 적용되어 있고 `0032`~`0035`는 미적용 상태다.
   - 마이그레이션 번호 순서가 곧 적용 순서이므로, 선행 미적용 마이그레이션(`0032`~`0034`)과 `0035_wiki_evidence_backfill.sql`의 호환성을 확인한 뒤 순서대로 원격에 선적용한다.
2. 적용 후 `supabase migration list --linked` 재실행으로 `0035`까지 Local/Remote 원장이 일치하고 미적용 대상이 없음을 확인한 뒤에만 PR 머지 및 백필 절차를 진행한다.

## 3. 단계별 운영 절차

### 3.1 후보 보고서 생성 (`export` — 읽기 전용)

```bash
uv run --env-file .env.local python -m worker.evidence_backfill export \
  --workspace-id <WORKSPACE_UUID> \
  --output-dir .local/evidence-backfill/<run-id>
```

- `wiki_evidence_backfill_candidates` RPC를 UUID 커서(최대 50페이지 단위)로 순회해 해당 워크스페이스의 전체 페이지를 빠짐없이 수집한다.
- 후보 청크는 페이지의 기존 `sources` 배열에 포함된 동일 `workspace_id`의 `source_chunks`로만 제한된다.
- 원문 본문(`raw_sources.content`)의 슬라이스 좌표(`char_start`~`char_end`)가 청크 본문과 일치하지 않는 청크는 `valid_coordinates: false`(`좌표 불일치 · 승인 불가`)로 표시되어 승인 대상에서 제외된다.
- 저장소 내부 경로는 `.gitignore`에 등록된 `.local/evidence-backfill/` 하위만 허용되며, 기존 파일이 있으면 덮어쓰지 않고 `output_exists`로 거부한다. 생성된 `candidates.json`과 `review.html`은 운영 본문을 포함하므로 **절대 커밋하거나 외부에 공유하지 않는다.**

### 3.2 정적 보고서(`review.html`) 대조 및 수동 승인(`approvals.json`) 편집

1. 브라우저에서 `.local/evidence-backfill/<run-id>/review.html`을 열어 페이지 본문과 각 후보 청크 본문·원문 좌표를 대조한다 (스크립트·외부 네트워크 요청 없음).
2. 어휘 유사도 점수(`score`)는 검토 편의를 위한 정렬 순서일 뿐 **자동 승인 기준이 아니다.**
3. **미확정(Unresolved) 보존 원칙**:
   - 후보 청크가 아예 없는 페이지(`후보 없음 · 미확정`)이거나, 후보 청크는 있으나 페이지의 서술을 실제로 뒷받침한다고 확정할 수 없는 경우 **`approvals.json`에 추가하지 않고 비워 둔다.**
   - 연결률(예: 30/30)을 채우기 위해 추정 연결을 넣지 않는다. 근거가 불충분한 페이지는 미확정 상태로 남기는 것이 정상 결과다.
4. 근거가 확인된 쌍만 `.local/evidence-backfill/<run-id>/approvals.json`의 `"approved"` 배열에 기록한다:
   ```json
   {
     "schema": "wiki-evidence-backfill-v1",
     "workspace_id": "<WORKSPACE_UUID>",
     "candidates_sha256": "<candidates.json 원본 바이트 SHA-256>",
     "approved": [
       {
         "wiki_id": "<WIKI_UUID>",
         "raw_source_id": "<RAW_SOURCE_UUID>",
         "chunk_id": "<CHUNK_UUID>"
       }
     ]
   }
   ```

### 3.3 로컬 검증 (`validate` — DB 호출 없음)

```bash
uv run python -m worker.evidence_backfill validate \
  --candidates .local/evidence-backfill/<run-id>/candidates.json \
  --approvals .local/evidence-backfill/<run-id>/approvals.json
```

- DB에 접속하지 않고 `candidates_sha256` 바이트 해시 일치, 스키마 버전, `workspace_id` 일치, 중복 여부, 배치 상한(최대 500쌍), 각 승인 쌍이 유효 좌표(`valid_coordinates: true`) 후보 목록에 존재하는지를 검사한다.
- 승인 목록이 비어 있으면(`"approved": []`) 유효한 무작업(`approved: 0`)으로 통과한다.
- 잘못된 항목이 있으면 원문 노출 없이 고정 오류 코드와 행 번호(`selection_not_available:row_1` 등)를 반환한다.

### 3.4 원자적 추가 적용 (`apply` — 운영자 전용)

```bash
uv run --env-file <운영-또는-로컬-env> python -m worker.evidence_backfill apply \
  --candidates .local/evidence-backfill/<run-id>/candidates.json \
  --approvals .local/evidence-backfill/<run-id>/approvals.json \
  --confirm-workspace-id <WORKSPACE_UUID>
```

- `--confirm-workspace-id`가 파일의 `workspace_id`와 정확히 일치해야 실행된다.
- 승인 0건이면 DB RPC를 호출하지 않고 종료한다.
- `apply_wiki_evidence_backfill` RPC는 단일 트랜잭션 안에서 원문 → 페이지 → 청크 순서(UUID 오름차순)로 `FOR SHARE` 잠금을 획득한 뒤, 소속 워크스페이스·`page.sources` 포함 여부·원문 좌표 일치·스냅샷 토큰(`page_token`, `source_token`, `chunk_token`) 일치를 재검증한다.
- 단 하나의 쌍이라도 누락·범위 이탈·토큰 불일치(`backfill_stale`)이면 **배치 전체를 롤백**한다.
- 모든 검증을 통과하면 `wiki_page_evidence`에만 `INSERT ... ON CONFLICT (wiki_id, chunk_id) DO NOTHING`을 수행하고, 로컬에 `apply-result.json`(재실행 시 `apply-result-<hex>.json`)을 저장한다.

### 3.5 재실행 및 품질 집계 확인

- 동일 파일로 `apply`를 다시 실행하면 원본이 바뀌지 않은 한 `inserted: 0, existing: N, inserted_pairs: []`를 반환하며 중복 행을 만들지 않는다.
- 적용 후 Control Room 품질 탭 또는 `control_quality_snapshot` RPC로 `wiki_pages_with_evidence`가 실제 승인된 페이지 수만큼만 증가했는지 확인한다.

## 4. 실패(Stale) 재검토 및 오승인 복구 절차

### 4.1 검토 후 원본 변경(`backfill_stale`) 시 재검토 절차

- `export` 이후 페이지 본문·메타데이터·`sources` 배열, 원문 본문, 또는 청크 본문·좌표가 변경되면 `apply`는 `backfill_error:apply_rejected`(DB `backfill_stale`)로 배치 전체를 거부한다 (임베딩·`search_tsv`·`tsv_tokenizer_version` 등 검색 파생 컬럼 변경은 토큰에서 제외되어 검토를 무효화하지 않는다).
- 이때 낡은 `approvals.json`을 강제로 밀어 넣거나 재컴파일을 실행하지 않는다.
- **반드시 새 하위 디렉터리에 `export`를 다시 실행**해 새 `candidates.json`·`review.html`·`approvals.json`을 생성하고, 변경된 본문을 사람이 다시 대조해 선택한 뒤 `validate` → `apply`를 수행한다.

### 4.2 DB 커밋 후 결과 파일 쓰기 실패(`committed_but_result_write_failed`)

- DB 트랜잭션은 커밋되었으나 로컬 디스크 오류로 `apply-result.json` 기록만 실패하면 `backfill_error:committed_but_result_write_failed`를 출력한다.
- 이는 **DB 롤백이 아니므로** 이미 적용된 상태로 취급한다. 디스크 상태를 복구한 뒤 동일 파일로 `apply`를 재실행하면 `existing` 건수로 반영 여부를 안전하게 확인할 수 있다.

### 4.3 성공 후 잘못 승인한 연결 발견 시 복구 절차

- 이 도구는 자동 전체 삭제 명령이나 `replace_wiki_page_evidence`를 사용하지 않는다. 되돌림 명목으로 페이지의 기존 근거 전체를 삭제해서는 안 된다.
- 잘못 승인한 연결을 제거해야 할 때는 해당 실행의 `apply-result*.json`에 기록된 **`inserted_pairs` 목록(`wiki_id`, `raw_source_id`, `chunk_id`)을 근거로 실제 신규 삽입된 행만 특정**한다.
- 기존에 존재하던 근거(`existing`)나 다른 원문의 근거는 건드리지 않고, 잘못 추가된 `(workspace_id, wiki_id, chunk_id)` 행에 대해서만 별도 검토된 선택 삭제 SQL을 계획·실행한다.

## 5. 로컬 합성 데이터 End-to-End 검증 기록 (비민감 요약)

측정 일시: 2026-11-03 (KST)
검증 환경: 로컬 Supabase (`127.0.0.1:54421` / PostgreSQL 17, `0001`~`0035` 적용)
검증 스위트: `apps/worker/tests/test_evidence_backfill.py` (`test_cli_end_to_end_partial_approval_coordinates_and_re_review` 외 33개 테스트)

### 5.1 시나리오 구성 (합성 워크스페이스)

- 검증 완료(`verified`) 위키 페이지 3개 생성:
  - 페이지 A: 연결된 원문 청크 2개(정상 좌표) + 좌표 불일치 청크 1개(`valid_coordinates: false`) → **정상 청크 1개만 수동 승인**
  - 페이지 B: 연결된 원문 청크 2개가 존재하나 뒷받침 근거 불충분으로 가정 → **미승인(미확정 유지)**
  - 페이지 C: 연결된 원문 없음(후보 0개) → **미확정 유지**
- 동일 워크스페이스의 미연결 원문 1개 및 타 워크스페이스 원문·청크를 함께 배치해 후보 누출 여부를 함께 검증했다.
- `source_chunks.tsv_tokenizer_version` 변경이 `chunk_token`을 무효화하지 않는지 함께 검증했다.

### 5.2 단계별 실행 결과 요약

| 단계 | 실행 명령 / 동작 | 결과 요약 (본문·비밀 제외) |
| --- | --- | --- |
| 1. `export` (`run-1`) | `python -m worker.evidence_backfill export` | `{"pages": 3, "candidate_pairs": 6, "pages_without_candidates": 1}` 출력. 미연결 원문·타 워크스페이스 청크 0건, 좌표 불일치 청크는 `좌표 불일치 · 승인 불가` 표시, `approvals.json` 초기 승인 0건 |
| 2. 부적격 후보 선택 거부 | 좌표 불일치 청크를 `approvals.json`에 넣고 `validate` | DB 호출 전 `selection_not_available:row_1`로 거부 |
| 3. 수동 승인 및 `validate` | 페이지 A의 유효 청크 1개만 승인 후 `validate` | `{"approved": 1}` 통과 (페이지 B·C는 미승인 유지) |
| 4. 1차 `apply` | `--confirm-workspace-id` 지정 실행 | `{"requested": 1, "inserted": 1, "existing": 0}` — 페이지 A에만 근거 1건 추가, `apply-result.json` 생성 |
| 5. 2차 `apply` (멱등 재실행) | 동일 파일로 재실행 | `{"requested": 1, "inserted": 0, "existing": 1, "inserted_pairs": []}` — 중복 행 생성 없음 |
| 6. 품질 집계 대조 | `control_quality_snapshot` RPC vs 직접 조회 | `wiki_pages_total: 3`, `wiki_pages_with_evidence: 1` (승인한 페이지 A만 반영, 미확정 페이지 B·C는 0건 유지) |
| 7. 불변성 스냅샷 비교 | 전후 테이블 전체 비교 | `wiki_pages`(본문·제목·`verification_status`·`sources`·`search_tsv`), `wiki_embeddings`, `wiki_links`, `raw_sources`, `source_chunks`, `jobs`, `usage_events`, `wiki_page_revisions`, `wiki_write_proposals` 전후 100% 동일 |
| 8. 원본 변경 후 Stale 거부 | 페이지 B 본문 수정 후 `run-1` 파일로 `apply` | `backfill_error:apply_rejected` (`backfill_stale`, exit code 1)로 거부 및 무변경 확인 |
| 9. 새 보고서 재검토 (`run-2`) | `run-2`로 재-`export` → 재승인 → `apply` | `{"requested": 1, "inserted": 1, "existing": 0}` 정상 반영, 누적 근거 연결 페이지 2개 확인 |
| 10. 비민감 출력 검증 | CLI 표준 출력 전체 검사 | 원문·위키 본문 문자열 및 `SUPABASE_SECRET_KEY` 노출 0건 |

