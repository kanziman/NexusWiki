#!/usr/bin/env bash
# 모델 비교 실험(cheap-model-evidence-ablation)의 점검 또는 재생을 순서대로 돈다.
# 모델마다 재생 워커를 그 답변 모델로 다시 띄우고, 한 단계가 끝나면 내린다(설계 D2 · D5).
#
# ⚠️ 워커 리스너는 8081 고정이라 한 번에 한 모델만 뜬다. 다른 재생 서버를 먼저 내린다.
# ⚠️ 유료 호출을 한다. 상한은 사전 등록의 cap_micros이고 `model_evidence_eval.py`가 턴마다 집행한다.
#
# 사용법: scripts/model_evidence_run.sh <실험 디렉터리> probe|runs
set -euo pipefail

dir="${1:?실험 디렉터리}"
kind="${2:?probe|runs}"
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ASK_REPLAY_ENV_FILE="${ASK_REPLAY_ENV_FILE:-${repo}/.env}"
export LLM_STREAM_INTERNAL_TOKEN="ask-replay-llm-token"
listener="http://127.0.0.1:8081"

if curl -s -o /dev/null "${listener}/" 2>/dev/null; then
  echo "model_evidence_run: 8081에 이미 다른 워커가 떠 있다. 먼저 내린다" >&2
  exit 1
fi

wait_listener() {
  for _ in $(seq 1 120); do
    if curl -s -o /dev/null "${listener}/" 2>/dev/null; then
      return 0
    fi
    sleep 1
  done
  return 1
}

steps="$(cd "${repo}" && uv run python scripts/model_evidence_eval.py order --dir "${dir}" "${kind}")"
if [[ -z "${steps}" ]]; then
  echo "model_evidence_run: 남은 ${kind} 단계가 없다"
  exit 0
fi

while read -r round model; do
  [[ -z "${model}" ]] && continue
  slug="$(printf '%s' "${model}" | tr -c 'A-Za-z0-9._-' '_')"
  logs="${dir}/logs/${kind}-r${round}-${slug}"
  mkdir -p "${logs}"
  echo "model_evidence_run: ${kind} ${round} ${model} 워커 기동"
  ASK_REPLAY_LLM_MODEL="${model}" ASK_REPLAY_WORKER_ONLY=1 \
    bash "${repo}/scripts/ask_replay_serve.sh" "${repo}" "${logs}" &
  serve_pid=$!
  if ! wait_listener; then
    kill "${serve_pid}" 2>/dev/null || true
    echo "model_evidence_run: 워커가 뜨지 않았다. ${logs}/worker.log를 본다" >&2
    exit 1
  fi
  status=0
  if [[ "${kind}" == "probe" ]]; then
    (cd "${repo}" && uv run python scripts/model_evidence_eval.py probe --dir "${dir}" \
      --model "${model}" --runtime-manifest "${logs}/evaluation-runtime.json") || status=$?
  else
    (cd "${repo}" && uv run python scripts/model_evidence_eval.py run --dir "${dir}" \
      --round "${round}" --model "${model}" \
      --runtime-manifest "${logs}/evaluation-runtime.json") || status=$?
  fi
  kill "${serve_pid}" 2>/dev/null || true
  wait "${serve_pid}" 2>/dev/null || true
  # ⚠️ 리스너가 완전히 내려간 뒤에만 다음 모델을 띄운다. 겹치면 이전 모델 워커가 다음 모델의
  #    준비 확인에 대신 답하고, 그 모델은 model_mismatch로 덮어쓸 수 없는 제외 기록을 남긴다.
  down=0
  for _ in $(seq 1 30); do
    if ! curl -s -o /dev/null "${listener}/" 2>/dev/null; then
      down=1
      break
    fi
    sleep 1
  done
  if [[ "${down}" -ne 1 ]]; then
    echo "model_evidence_run: ${model} 워커가 30초 안에 내려가지 않았다. 다음 단계로 가지 않는다" >&2
    exit 1
  fi
  if [[ "${status}" -ne 0 ]]; then
    # 2는 상한 · 측정 장애 · 연속 실행 장애로 멈춘 실행이다. 남은 계획 실행을 미실행으로 남기고 끝낸다.
    echo "model_evidence_run: ${kind} ${round} ${model} 종료 코드 ${status}. 중단한다" >&2
    if [[ "${kind}" == "runs" && "${status}" -eq 2 ]]; then
      (cd "${repo}" && uv run python scripts/model_evidence_eval.py close --dir "${dir}") || true
    fi
    exit "${status}"
  fi
done <<<"${steps}"
