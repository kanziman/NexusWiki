## 1. 로컬 대시보드 설정 정합성 복구

- [x] 1.1 루트·대시보드 환경변수 예시와 로컬 실행 안내를 현재 `NEXT_PUBLIC_API_URL` 및 FastAPI 8000 포트 계약에 맞춘다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/63) **AC:** Given 새 로컬 개발자가 추적된 예시만 참고할 때, When 대시보드 전용 `.env.local`을 준비하면, Then Supabase는 54421로, FastAPI는 8000으로 분리되어 업로드 요청이 API로 전달된다.
- [x] 1.2 대시보드 환경변수·API 클라이언트·Dropzone 테스트와 typecheck·lint를 실행한다. **AC:** Given 수정된 로컬 설정 예시와 기존 업로드 UI, When 프런트 검증을 새로 실행하면, Then 공개 환경변수 계약과 소스 업로드 요청 조립이 모두 통과한다.

## 2. 워크스페이스 slug 테스트 데이터 회귀 복구

- [x] 2.1 API·worker 통합 픽스처와 검색 벤치마크 시드의 워크스페이스 INSERT에 결정적이고 유효한 slug를 추가한다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/64) **AC:** Given `workspaces.slug`가 필수인 최신 로컬 스키마, When 각 테스트·벤치마크 경로가 워크스페이스를 생성하면, Then not-null·형식·고유성 제약을 만족해 준비 단계가 완료된다.
- [x] 2.2 로컬 Supabase에서 API 소스 통합 테스트와 worker 큐 테스트를 실행하고 실제 Markdown 업로드의 202·원문 행·parse 잡 생성을 확인한다. **AC:** Given 로컬 Supabase와 수정된 시드 경로, When 소스 업로드 검증을 새로 실행하면, Then 준비 오류 없이 테스트가 통과하고 업로드가 큐에 등록된다.

## 3. 변경 검증

- [x] 3.1 관련 Python lint와 OpenSpec strict validation을 실행하고 모든 검증 결과를 확인한다. **AC:** Given 변경된 문서·테스트·스크립트와 완료된 관련 테스트, When 최종 검증을 실행하면, Then 실패 없이 change를 아카이브할 수 있다.
