## 1. 병합된 코드의 공개 증거

- [x] 1.1 main 측정값 불변을 확인하고 공개 증거의 수정 후 해시를 `184c5b4`로 갱신한다 (D1)
  - Given: #173이 squash merge되었고 측정 대상 코드가 깨끗하다
  - When: 합성 증거를 재측정해 기존 값과 비교하고 다시 생성한다
  - Then: 네 항목의 `after.values`는 같고 `after.commit`은 `184c5b4`다
  - 검증: `uv run python apps/worker/tests/test_controlled_ai_evidence.py measure /tmp/nexuswiki-main-after.json`, 기존 JSON과 값 비교, `write after`, `uv run pytest apps/worker/tests/test_controlled_ai_evidence.py`, 대시보드 `vitest run tests/ControlledAiShowcase.test.tsx --testTimeout=30000`
  - GitHub: https://github.com/kanziman/NexusWiki/issues/171

## 2. 복구 기록과 머지 전 운영 게이트

- [x] 2.1 클라우드 적용 기록을 정정하고 마이그레이션 운영 게이트를 체크리스트에 연결한다 (D2, D3)
  - Given: 사용자 제공 복구 보고와 main 자동 배포 동작이 있다
  - When: 마이그레이션 적용 기록과 Railway 체크리스트를 갱신한다
  - Then: `0021`에서 `0026`까지의 보고된 상태와 401 확인 출처가 명시되고, 직접 확인하지 않은 함수 권한·워커·실제 계정 흐름은 미확인으로 남으며, 호환성 확인과 DB 선적용·결과 확인이 머지보다 앞선다
  - 검증: 문서와 delta 시나리오 수동 대조, `git diff --check`, `openspec validate post-merge-control-ops --strict`
  - GitHub: https://github.com/kanziman/NexusWiki/issues/175 (umbrella #174)

## 3. 검증과 계약 정리

- [x] 3.1 관련 검증과 리뷰 게이트를 통과하고 정본 동기화·아카이브를 완료한다
  - Given: 증거와 운영 문서가 구현되어 있다
  - When: 관련 테스트·포맷 검사·strict 검증과 두 리뷰 게이트를 수행한다
  - Then: 검증된 task만 완료 처리되고, 정본 스펙에 운영 게이트가 반영되며, change와 리뷰 보고서가 아카이브에 남는다
  - 검증: 증거 Python 테스트, 쇼케이스 Vitest, 변경 JSON Prettier 검사, `openspec validate post-merge-control-ops --strict`, `openspec validate --specs --strict`, `git diff --check`
  - GitHub: https://github.com/kanziman/NexusWiki/issues/174
