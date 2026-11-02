#!/usr/bin/env bash
# 재생 전용 로컬 스택을 544xx와 분리해 546xx에 띄운다.
#
# ⚠️ 왜 분리하나: 워커는 큐에서 잡을 워크스페이스 구분 없이 claim한다. 공유 스택에 재생용
#    워커를 붙이면 다른 세션의 테스트가 넣은 잡을 가져가 그 테스트를 깨뜨린다.
# ⚠️ 저장소의 config.toml은 고치지 않는다. 사본을 임시 디렉터리에 만들어 그쪽으로 띄운다.
#
# 사용법: scripts/ask_replay_stack.sh start|stop <작업 디렉터리>
set -euo pipefail

action="${1:?start 또는 stop}"
workdir="${2:?작업 디렉터리}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

case "${action}" in
  start)
    mkdir -p "${workdir}/supabase"
    cp -R "${root}/supabase/migrations" "${workdir}/supabase/"
    [[ -f "${root}/supabase/seed.sql" ]] && cp "${root}/supabase/seed.sql" "${workdir}/supabase/"
    # ⚠️ macOS sed는 `\b`를 지원하지 않아 조용히 치환을 건너뛴다. perl을 쓴다.
    perl -pe 's/\b544(\d{2})\b/546$1/g; s/^project_id = .*/project_id = "NexusWikiReplay"/' \
      "${root}/supabase/config.toml" >"${workdir}/supabase/config.toml"
    if grep -qE '\b544[0-9]{2}\b' "${workdir}/supabase/config.toml"; then
      echo "ask_replay_stack: 포트 치환이 끝나지 않았다" >&2
      exit 1
    fi
    supabase start --workdir "${workdir}" -x studio,imgproxy,inbucket,vector,logflare,edge-runtime
    ;;
  stop)
    supabase stop --workdir "${workdir}" --no-backup
    ;;
  *)
    echo "ask_replay_stack: 알 수 없는 동작: ${action}" >&2
    exit 2
    ;;
esac
