## 1. 워크스페이스 슬러그 데이터 계약

- [x] 1.1 `workspaces.slug` 정본 migration과 기존 fixture를 구현하고, 로컬 reset·SQL 계약 검증 및 운영 DB 적용을 확인한다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/14)
  - Given: 슬러그가 없는 기존 워크스페이스와 기존 test·spike INSERT가 있다.
  - When: migration `0015_workspace_slug.sql`을 적용하고 전체 로컬 스키마를 reset한 뒤 운영 DB에도 적용한다.
  - Then: 기존 행은 결정적 `ws-<UUID 앞 8자>` 슬러그를 받고, 새 쓰기는 전역 UNIQUE·형식·NOT NULL 제약을 따르며, 개인 워크스페이스 생성이 성공한다.
