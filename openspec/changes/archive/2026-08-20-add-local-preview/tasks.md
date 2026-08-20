## 1. 개발 전용 목업 미리보기 (#50)

- [x] 1.1 Given 개발 서버, When 검토자가 `/preview`와 하위 화면을 열면, Then
      인증·Supabase·API 없이 결정적 목업 사용자와 워크스페이스를 탐색할 수 있고
      production에서는 not-found 결과를 받는다.
- [x] 1.2 Given 검토자가 미리보기에서 질문·인용·탭·필터를 사용하면, When 화면
      상태가 바뀌면, Then 결정적 목업 결과를 표시하고 모든 탐색은 `/preview/*` 안에
      남는다.
- [x] 1.3 Given 검토자가 업로드·초대·저장·로그아웃을 시도하면, When 해당 제어를
      사용하면, Then 외부 요청 없이 저장되지 않는다는 한국어 안내를 표시한다.
- [x] 1.4 Given dashboard 검증, When preview 경계와 상호작용을 실행하면, Then
      Vitest·typecheck·lint와 OpenSpec strict validation이 통과한다.
