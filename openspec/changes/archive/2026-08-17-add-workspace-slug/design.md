## Context

현재 운영 `public.workspaces`에는 URL 식별자가 없다. `slugify`는 80자 제한과 허용 문자 집합을 이미 소유하며, migration 제약은 그 계약과 일치해야 한다.

## Decisions

### ADR-1: 정본을 `workspaces.slug`에 둔다

`workspaces.slug`를 전역 UNIQUE 정본으로 추가하고, 기존 행에는 `ws-<UUID 앞 8자>`를 백필한 뒤 NOT NULL·UNIQUE·형식 CHECK를 적용한다.

### ADR-2: 데이터 제약과 slug 생성의 문자 계약을 일치시킨다

PostgreSQL CHECK는 소문자 영숫자·한글 음절·하이픈과 1~80자 제한을 강제한다. DB UNIQUE는 동시 생성 충돌의 최종 방어선이다.

## Migration Plan

1. nullable `slug` 컬럼을 추가한다.
2. 기존 행을 UUID 기반 값으로 백필한다.
3. NOT NULL·UNIQUE·형식 CHECK를 적용한다.
4. slug 없는 fixture와 spike 삽입문을 유효 슬러그로 갱신한다.
5. 로컬 reset과 SQL 계약 검증 후 운영 DB에 적용한다.
