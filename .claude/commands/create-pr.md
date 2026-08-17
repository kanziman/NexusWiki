---
description: 승인된 변경만 안전하게 commit하고 GitHub PR을 생성하거나 갱신합니다.
argument-hint: "[issue-number | #issue-number | issue-url]"
---

먼저 `.agents/skills/create-pr/SKILL.md`를 끝까지 읽고 그 workflow를 그대로 따른다.

사용자가 전달한 원문 인자는 다음과 같다.

```text
$ARGUMENTS
```

이 값을 canonical skill의 `$ARGUMENTS`로 변경 없이 전달한다. 이 adapter에 별도 staging, commit, push, PR 생성 규칙을 복제하지 않는다.
