## Why

워크스페이스에는 안정적인 URL 식별자가 없고, 운영 데이터베이스에는 이를 추가하는 migration도 아직 적용되지 않았다. Google OAuth 기반 워크스페이스 생성을 안전하게 완료하려면 모든 워크스페이스의 전역 고유 슬러그 정본을 운영에 반영해야 한다.

GitHub umbrella: https://github.com/kanziman/NexusWiki/issues/13

## What Changes

- `workspaces.slug`를 모든 워크스페이스의 전역 고유 정본으로 추가한다.
- 기존 행을 결정적인 `ws-<UUID 앞 8자>` 값으로 백필하고, 새 값에 NOT NULL·UNIQUE·허용 문자/길이 제약을 적용한다.
- 슬러그 없는 SQL fixture와 spike 입력을 갱신한다.

## Capabilities

### New Capabilities

- `workspace-slug`: 워크스페이스의 전역 고유 슬러그 저장과 생성 계약을 제공한다.

### Modified Capabilities

- 없음.

## Impact

- `supabase/migrations/0015_workspace_slug.sql`와 로컬·클라우드 마이그레이션 순서 검증에 영향을 준다.
- Google OAuth personal 워크스페이스 생성의 선행 데이터 계약이다.
