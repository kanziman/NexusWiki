## 1. 보안·품질·운영 계약 반영

- [x] 1.1 `tenant-data-isolation`, `knowledge-quality`, `usage-guardrails` delta를 canonical spec으로 반영하고 개별 요구사항 구조를 검증한다. (GitHub issue: [#56](https://github.com/kanziman/NexusWiki/issues/56), native sub-issue 연결 보류)
  - **Given:** v1.0 검증 기록과 현재 격리·검증·비용 구현이 존재한다.
  - **When:** 세 capability spec을 `openspec/specs/`에 반영한다.
  - **Then:** 요청자/특권 경계, 검증 감사, 비용 상한 시나리오가 strict validation 가능한 정본 계약으로 존재한다.

## 2. 수집·컴파일·잡 계약 반영

- [x] 2.1 `source-ingestion`, `wiki-compilation`, `background-job-lifecycle` delta를 canonical spec으로 반영하고 기존 소스 UI spec과 책임 중복을 점검한다. (GitHub issue: [#57](https://github.com/kanziman/NexusWiki/issues/57), native sub-issue 연결 보류)
  - **Given:** 비동기 수집부터 임베딩까지의 현재 파이프라인과 검증 근거가 존재한다.
  - **When:** 세 capability spec을 `openspec/specs/`에 반영한다.
  - **Then:** 중복·OCR·재처리·단계 전이·재시도 경계가 구현 세부 복제 없이 정본 계약으로 존재한다.

## 3. 검색·근거 답변 계약 반영

- [x] 3.1 `hybrid-retrieval`, `grounded-answering` delta를 canonical spec으로 반영하고 기존 Ask UI spec과 책임 중복을 점검한다. (GitHub issue: [#58](https://github.com/kanziman/NexusWiki/issues/58), native sub-issue 연결 보류)
  - **Given:** 5채널 검색, RRF, 서버 발급 인용 및 SSE 구현과 품질 기록이 존재한다.
  - **When:** 두 capability spec을 `openspec/specs/`에 반영한다.
  - **Then:** 부분 장애 검색과 인용 무결성의 입력·출력·실패 시나리오가 strict validation 가능한 정본 계약으로 존재한다.

## 4. 통합 문서 검증

- [x] 4.1 change와 canonical specs 전체에 strict validation을 새로 실행하고 문서 외 파일이 변경되지 않았음을 확인한다.
  - **Given:** 신규 capability 8개가 canonical spec으로 반영되어 있다.
  - **When:** change validation, canonical spec validation, Git diff 범위 검사를 실행한다.
  - **Then:** 모든 검증이 통과하고 변경 범위가 OpenSpec 문서와 추적 산출물로 제한된다.
