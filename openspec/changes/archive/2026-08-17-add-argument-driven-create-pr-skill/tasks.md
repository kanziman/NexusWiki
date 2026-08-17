## 1. Canonical create-pr workflow

- [x] 1.1 Add and register the canonical `create-pr` skill with `$ARGUMENTS` issue resolution, explicit manifest and index guards, approval, fresh validation, commit, non-force push, duplicate-PR reuse, and verified issue linkage. Acceptance: Given a dirty worktree with unrelated changes, when the skill plans `/create-pr #9`, then it exposes only requested paths, blocks unapproved staged or mixed-scope content, and describes no destructive git operation. GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/10

## 2. Claude command adapter

- [x] 2.1 Add a Claude `/create-pr` thin adapter that loads the canonical skill and passes `$ARGUMENTS` unchanged, then update project discovery and workflow documentation. Acceptance: Given `/create-pr https://github.com/kanziman/NexusWiki/issues/9`, when Claude loads the command, then the canonical workflow receives the full URL without a duplicated implementation. GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/11

## 3. Validation and regression scenarios

- [x] 3.1 Validate the skill package and run fresh read-only GREEN scenarios covering numeric, hash-prefixed, URL, omitted, invalid, dirty-index, mixed-scope, validation-failure, and existing-PR cases; run strict OpenSpec validation. Acceptance: Given the completed skill and adapter, when validators and independent scenario reviews run, then required safety guarantees pass without creating a commit, push, PR, merge, or destructive worktree change. GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/12
