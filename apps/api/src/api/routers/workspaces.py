"""테넌트 격리를 실제 HTTP 왕복으로 증명하기 위한 최소 workspaces 라우터.

관련 태스크: P2-BE-01
설계 근거: 02-CONTEXT.md > D-11, D-12, D-13

⚠️ 이 라우터는 제품 기능이 아니라 **격리 증명 표면**이다. 도메인 라우터가 하나도 없으면
"애플리케이션 경로에서의 교차 테넌트 시도가 Forbidden으로 돌아온다"를 확인할 표면 자체가
없다. 실제 도메인 라우터는 Phase 3~5가 세운다 (02-SPEC.md Boundaries).

소비자: apps/api/tests/test_workspaces_isolation.py (SEC-06)
"""
