## Context

동기는 proposal.md를 따른다. Storage 1.44.11에서 RLS `42501`은 HTTP 400, 본문 `statusCode: "403"`, `error: "Unauthorized"`이고 `code`는 없다.

## Goals / Non-Goals

**Goals:** 업로드·삭제의 기존 예외 경계를 유지하며 공급자 응답 호환성을 복구한다.

**Non-Goals:** 권한 정책·Storage 서비스·스키마 변경, 오류 본문 공개.

## Decisions

본문 `statusCode`의 정수 또는 문자열 401/403만 추가 거부 신호로 사용한다. HTTP 상태와 기존 `code` 판정은 유지한다. 모든 400을 거부로 분류하면 실제 장애를 숨기므로 기각한다. 메시지 문자열 비교는 공급자 문구 변화에 약해 기각한다.

사용자의 2026-11-03 별도 change 수정 진행 승인으로 범위와 실행을 확정했다. 기존 어댑터의 작은 호환성 수정으로 새로운 아키텍처 선택은 없다.

## Risks / Trade-offs

- 잘못된 본문 상태 → 허용 목록 401/403 외 값은 기존 장애 처리로 남긴다.

## Migration Plan

DB 변경 없이 API 배포로 적용한다. 원복은 해당 커밋의 되돌리기다.
