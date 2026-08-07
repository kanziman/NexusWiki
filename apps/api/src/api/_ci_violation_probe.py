"""CI 게이트 red 관측용 위반 픽스처 — 02-09 Task 3.

이 모듈은 `service-usage` 잡이 실제로 실패하는지 관측하기 위해서만 존재하며
`main`에 병합되지 않는다. 관측이 끝나면 브랜치와 함께 사라진다.

⚠️ 이것이 왜 위반인가: `service_role`은 BYPASSRLS다. api 프로세스가 이 클라이언트를
만들 수 있으면 사용자 요청 경로가 RLS를 우회할 수 있고, 그 순간
`0004_rls_policies.sql`의 정책 20여 개가 전부 장식이 된다
— `checklists.json > decisions.db_access`.
"""

from worker.db.service import service_client

__all__ = ["service_client"]
