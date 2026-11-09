#!/usr/bin/env python3
"""같은 수집 위에서 답변 모델 × 근거 범위(원문만 · 둘 다)를 반복 재생해 위키 기여를 모델별로 잰다.

계약: openspec/specs/model-evidence-ablation/spec.md,
     설계: openspec/changes/archive/2026-11-09-cheap-model-evidence-ablation/design.md

쓰는 순서 (모든 명령은 --dir 하나의 실험 디렉터리를 공유한다):
    # 0. 첫 유료 호출보다 먼저 모델 · 조건 · 회차 · 상한 · 규칙을 등록한다(설계 D3).
    uv run python scripts/model_evidence_eval.py register --dir D \\
        --state state.json --query-vectors query-vectors.json --reference-retrieval retrieve.json

    # 1~2. 모델마다 워커를 띄워 점검하고, 점검 비용만으로 회차를 정한 뒤 회차 우선으로 재생한다.
    bash scripts/model_evidence_run.sh D probe
    uv run python scripts/model_evidence_eval.py plan --dir D
    bash scripts/model_evidence_run.sh D runs

    # 3. #237 Sonnet 기록을 참조 줄로 싣고 성적표를 본다.
    uv run python scripts/model_evidence_eval.py import-reference --dir D --answer answer.json
    uv run python scripts/model_evidence_eval.py scoreboard --dir D   # http://127.0.0.1:8801
    uv run python scripts/model_evidence_eval.py scoreboard --dir D --html scoreboard.html

⚠️ 로컬 재생 스택 전용이다. 루프백이 아닌 주소는 요청 전에 거부한다.
⚠️ 원문만 조건은 진단이다. 이중 인용이 구조적으로 불가능하므로 제품 통과율과 나란히 놓지 않는다.
⚠️ 합성 문서 8개 · 고정 30문항의 샘플 수치다. 운영 효과로 인용하지 않는다.
"""

from __future__ import annotations

import argparse
import asyncio
import html
import importlib.util
import json
import re
import sys
import time
from collections.abc import Awaitable, Callable, Iterable, Mapping
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import UUID, uuid4

import httpx

_SCRIPTS = Path(__file__).resolve().parent


def _load_script(name: str) -> ModuleType:
    module_name = f"_model_evidence_{name}"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise SystemExit(f"model_evidence: 스크립트를 불러오지 못했다: {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# 판정 · 고정 입력 · 프로세스 내 답변 경로는 6조건 실험의 것을 그대로 쓴다(설계 D1).
# 두 곳에 두면 같은 답을 다르게 채점한다.
ablation = _load_script("retrieval_ablation")
replay = ablation.replay
canonical_sha256 = ablation.canonical_sha256

EXPERIMENT = "model-evidence-ablation"
REGISTRATION_SCHEMA = "model-evidence-registration-v1"
PROBE_SCHEMA = "model-evidence-probe-v1"
PLAN_SCHEMA = "model-evidence-plan-v1"
RUN_SCHEMA = "model-evidence-run-v1"
SCOREBOARD_NAME = "scoreboard.jsonl"
# 이름이 곧 순서다. 원문만을 먼저 돌려 같은 회차 안의 짝 비교가 같은 시간대에 놓이게 한다.
CONDITIONS: dict[str, str] = {"source_onlyxbody": "source_only", "bothxbody": "both"}
DEFAULT_MODELS = (
    "anthropic/claude-haiku-5.5",
    "openai/gpt-6-luna",
    "deepseek/deepseek-v4.1-flash",
)
DEFAULT_CAP_MICROS = 1_000_000
# 2026-11-09 공개 가격으로 저가 3종의 문항당 추정은 약 $0.0006~$0.0008이다. 첫 턴 전 검사용 여유값.
DEFAULT_PROBE_ESTIMATE_MICROS = 20_000
DEFAULT_SAFETY = 1.5
# 이만큼 연달아 실행 장애면 그 실행을 멈춘다. 한두 번은 일시 장애일 수 있어 1로 두지 않는다.
MAX_CONSECUTIVE_EXECUTION_FAILURES = 3
# 예약이 정산될 때까지 잠시 기다린다. 스트림이 끝난 뒤 정산이 비동기로 따라온다.
_SETTLE_WAIT_SECONDS = 10.0
_PENDING_STATUSES = {"reserved", "in_flight"}
# 점검 기록에서 `plan`이 읽어도 되는 필드. 정답 여부를 보고 회차를 고르지 못하게 막는다(스펙).
_PROBE_PLAN_FIELDS = (
    "schema",
    "experiment",
    "registration_sha256",
    "created_at",
    "model",
    "ok",
    "failure_reason",
    "cost_micros",
    "truncated",
)


# ---------------------------------------------------------------------------
# 경로 · 기록 입출력
# ---------------------------------------------------------------------------


def model_slug(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model)


def registration_path(root: Path) -> Path:
    return root / "registration.json"


def probe_path(root: Path, model: str) -> Path:
    return root / "probes" / f"{model_slug(model)}.json"


def plan_path(root: Path) -> Path:
    return root / "plan.json"


def run_path(root: Path, round_no: int, model: str) -> Path:
    return root / "runs" / f"r{round_no}-{model_slug(model)}.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path: Path, value: Mapping[str, Any]) -> None:
    """append-only 기록. 같은 경로가 있으면 쓰지 않고 멈춘다(설계 D5)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2))
    except FileExistsError:
        raise SystemExit(f"model_evidence: 이미 있는 기록은 덮어쓰지 않는다: {path}") from None


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# 사전 등록 (설계 D3)
# ---------------------------------------------------------------------------


def build_registration(
    *,
    models: list[str],
    rounds_max: int,
    rounds_min: int,
    cap_micros: int,
    probe_question: str,
    probe_estimate_micros: int,
    safety: float,
    fixed_inputs: Mapping[str, Any],
    reference_retrieval_sha256: str,
    paths: Mapping[str, str],
    effect_criterion: Mapping[str, int] | None = None,
    budget: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if budget is not None and budget.get("compile_model") in models:
        raise SystemExit(
            f"model_evidence: 컴파일 모델이 답변 모델과 같다: {budget.get('compile_model')}"
        )
    if cap_micros <= 0:
        raise SystemExit("model_evidence: 비용 상한이 없는 실험은 등록하지 않는다")
    if not models or len(set(models)) != len(models):
        raise SystemExit("model_evidence: 모델 목록이 비었거나 중복이 있다")
    if not 1 <= rounds_min <= rounds_max:
        raise SystemExit("model_evidence: 회차는 1 ≤ 최소 ≤ 최대여야 한다")
    if probe_estimate_micros <= 0 or safety < 1:
        raise SystemExit("model_evidence: 점검 추정은 양수, 안전계수는 1 이상이어야 한다")
    body = {
        "schema": REGISTRATION_SCHEMA,
        "experiment": EXPERIMENT,
        "created_at": _now(),
        "models": list(models),
        "conditions": list(CONDITIONS),
        "rounds_max": rounds_max,
        "rounds_min": rounds_min,
        "cap_micros": cap_micros,
        "probe": {
            "question": probe_question,
            "condition": "bothxbody",
            "estimate_micros": probe_estimate_micros,
            "exclusion_rule": (
                "상태가 resolved·fallback이 아니거나, 채널 실패·측정 장애가 있으면 제외"
            ),
        },
        "round_rule": {
            "safety": safety,
            "rule": (
                "rounds = max{r ∈ [min, max] : spent + r × 남은 모델 수 × 조건 수 × 문항 수 × "
                "max(점검 턴 비용) × safety ≤ cap}. 정답 필드는 읽지 않는다"
            ),
        },
        "fixed_inputs": dict(fixed_inputs),
        "reference_retrieval_sha256": reference_retrieval_sha256,
        "paths": dict(paths),
    }
    # 두 필드는 위키 유리 시험지 실험(wiki-advantage-eval)에서만 쓴다. 없으면 넣지 않아
    # 이전 실험의 등록 모양이 그대로다.
    if effect_criterion is not None:
        body["effect_criterion"] = dict(effect_criterion)
    if budget is not None:
        body["budget"] = dict(budget)
    return {**body, "content_sha256": canonical_sha256(body)}


# ---------------------------------------------------------------------------
# 전 단계 상한 (wiki-advantage-eval 설계 D5)
# ---------------------------------------------------------------------------

BUDGET_SCHEMA = "model-evidence-budget-v1"
INGESTION_SCHEMA = "model-evidence-ingestion-v1"
EPOCH = "1970-01-01T00:00:00+00:00"
DEFAULT_EFFECT_CRITERION = {"min_net_recovered": 3, "min_models": 2}


def budget_path(root: Path) -> Path:
    return root / "budget.json"


def ingestion_path(root: Path) -> Path:
    return root / "ingestion.json"


def build_budget(
    *,
    total_cap_micros: int,
    compile_model: str,
    answer_models: list[str],
    sample: Mapping[str, Any],
    sample_path: str,
) -> dict[str, Any]:
    """수집 전에 쓰는 총 상한 기록. 시험지 해시도 여기서 고정한다(설계 D9)."""
    if total_cap_micros <= 0:
        raise SystemExit("model_evidence: 총 상한이 양수여야 한다")
    if compile_model in answer_models:
        raise SystemExit(f"model_evidence: 컴파일 모델이 답변 모델과 같다: {compile_model}")
    if replay.is_typed_sample(dict(sample)):
        errors = replay.check_typed_sample(dict(sample))
        if errors:
            raise SystemExit(f"model_evidence: 시험지가 구성 조건을 어긴다: {errors}")
    return {
        "schema": BUDGET_SCHEMA,
        "experiment": EXPERIMENT,
        "created_at": _now(),
        "total_cap_micros": total_cap_micros,
        "compile_model": compile_model,
        "answer_models": list(answer_models),
        "fixture_sha256": ablation.fingerprint.fixture_sha256(sample),
        "sample": sample_path,
    }


def build_ingestion(
    *,
    budget: Mapping[str, Any],
    jobs: list[Mapping[str, Any]],
    pages: int,
    documents: int,
    compile_models: list[str],
    spent_micros: int,
    workspace_id: str | None = None,
    recovered: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """수집 결과. 잡 실패 · 미완료 · 위키 0쪽 · 다른 컴파일 모델이면 재생을 막는다(스펙).

    ⚠️ 끝나지 않은 잡도 막는다. 제품 재시도 API로 되돌린 잡은 `queued`로 돌아가 실패 흔적이
       지워지므로, 끝나기 전에 기록하면 다시 죽어도 `ok`로 남는다(리뷰 r1).
    """
    # 최종 상태 기준: `dead` · `canceled`만 실패다. `failed`는 워커 자동 재시도 대기라
    # 아직 끝나지 않은 잡으로 센다(사용자 결정 · 리뷰 r2).
    failed = [dict(j) for j in jobs if j.get("status") in FINAL_FAILURE_STATES]
    pending = [dict(j) for j in jobs if j.get("status") not in FINAL_FAILURE_STATES | {"succeeded"}]
    used = sorted(set(compile_models))
    reasons = []
    if failed:
        reasons.append(f"실패한 잡 {len(failed)}개")
    if pending:
        reasons.append(f"끝나지 않은 잡 {len(pending)}개")
    if pages <= 0:
        reasons.append("컴파일된 위키가 없다")
    if used != [budget["compile_model"]]:
        reasons.append(f"컴파일 모델이 등록과 다르다: {used}")
    return {
        "schema": INGESTION_SCHEMA,
        "experiment": EXPERIMENT,
        "created_at": _now(),
        "budget_created_at": budget["created_at"],
        # 등록이 다른 state(다른 워크스페이스)의 지출로 상한을 계산하지 못하게 묶는다.
        "workspace_id": workspace_id,
        "compile_model": budget["compile_model"],
        "compile_models_used": used,
        "documents": documents,
        "wiki_pages": pages,
        "jobs": len(jobs),
        "failed_jobs": [
            {"type": j.get("type"), "status": j.get("status"), "last_error": j.get("last_error")}
            for j in failed
        ],
        # 실패는 최종 상태로 판정하고, 재시도로 복구한 잡은 따로 남긴다(스펙).
        "recovered_jobs": [dict(r) for r in recovered or []],
        "spent_micros": spent_micros,
        "ok": not reasons,
        "reasons": reasons,
    }


RETRIES_NAME = "job-retries.jsonl"
FINAL_FAILURE_STATES = frozenset({"dead", "canceled"})


def recovered_jobs(
    retries: list[Mapping[str, Any]], jobs: list[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """한 번 실패했다가 최종 성공한 잡. 두 경로를 모두 센다(스펙: recovered jobs).

    - 제품 재시도 API: 그 함수가 `attempts` · `last_error`를 지워 DB로는 알 수 없으므로
      `retry-dead`가 남긴 기록을 쓴다. 받아들여진(2xx) 재시도 호출만 센다.
    - 워커 자동 재시도: `failed`가 됐다가 워커가 다시 잡아 성공하면 `attempts > 1`로 남는다.
    """
    final = {str(j.get("id")): j for j in jobs}
    seen: dict[str, dict[str, Any]] = {}
    for item in retries:
        if not 200 <= int(item.get("status_code") or 0) < 300:
            continue
        job_id = str(item.get("job_id"))
        entry = seen.setdefault(
            job_id, {"job_id": job_id, "type": item.get("type"), "api_retries": 0}
        )
        entry["api_retries"] += 1
    for job_id, job in final.items():
        if int(job.get("attempts") or 0) > 1:
            entry = seen.setdefault(
                job_id, {"job_id": job_id, "type": job.get("type"), "api_retries": 0}
            )
            entry["worker_attempts"] = int(job["attempts"])
    return [
        {**entry, "final_status": final[job_id].get("status")}
        for job_id, entry in seen.items()
        if job_id in final and final[job_id].get("status") == "succeeded"
    ]


def replay_cap(budget: Mapping[str, Any], ingestion: Mapping[str, Any], spent_now: int) -> int:
    """재생 상한 = 총 상한 − 실험 워크스페이스가 지금까지 쓴 돈(수집 · 컴파일 · 임베딩)."""
    if not ingestion.get("ok"):
        raise SystemExit(
            f"model_evidence: 수집이 실패해 재생하지 않는다: {ingestion.get('reasons')}"
        )
    cap = int(budget["total_cap_micros"]) - spent_now
    if cap <= 0:
        raise SystemExit(f"model_evidence: 총 상한이 남지 않았다: 지출 {spent_now} micros")
    return cap


def check_registration(registration: Mapping[str, Any]) -> None:
    """등록이 바뀌지 않았고 상한이 있는지 본다. 어긋나면 유료 호출 전에 멈춘다."""
    if registration.get("schema") != REGISTRATION_SCHEMA:
        raise SystemExit("model_evidence: 사전 등록 파일 형식이 아니다")
    body = {k: v for k, v in registration.items() if k != "content_sha256"}
    if registration.get("content_sha256") != canonical_sha256(body):
        raise SystemExit("model_evidence: 사전 등록 내용이 등록 뒤에 바뀌었다. 진행하지 않는다")
    cap = registration.get("cap_micros")
    if not isinstance(cap, int) or cap <= 0:
        raise SystemExit("model_evidence: 비용 상한이 없는 실행은 하지 않는다")


def _require_after_registration(registration: Mapping[str, Any], created_at: str) -> None:
    if datetime.fromisoformat(created_at) <= datetime.fromisoformat(
        str(registration["created_at"])
    ):
        raise SystemExit("model_evidence: 사전 등록보다 이르거나 같은 시각의 기록이다")


def load_registration(root: Path) -> dict[str, Any]:
    path = registration_path(root)
    if not path.exists():
        raise SystemExit(f"model_evidence: 사전 등록이 없다: {path}")
    registration = _read_json(path)
    check_registration(registration)
    return registration


def differing_fixed_inputs(expected: Mapping[str, Any], actual: Mapping[str, Any]) -> list[str]:
    keys = ("snapshot_sha256", "query_vectors_sha256", "fixture_sha256", "chunk_boundaries_sha256")
    return [k for k in keys if expected.get(k) != actual.get(k)]


# ---------------------------------------------------------------------------
# 점검과 계획 (설계 D3 · D4)
# ---------------------------------------------------------------------------


def probe_ok(row: Mapping[str, Any]) -> tuple[bool, str | None]:
    if row.get("measurement_failure"):
        return False, f"측정 장애 {row['measurement_failure']}"
    if row.get("failed_channels"):
        return False, f"검색 채널 실패 {row['failed_channels']}"
    status = str(row.get("status"))
    if status not in {"resolved", "fallback"}:
        return False, f"상태 {status}"
    return True, None


def build_probe_record(
    registration: Mapping[str, Any], model: str, row: Mapping[str, Any]
) -> dict[str, Any]:
    ok, reason = probe_ok(row)
    return {
        "schema": PROBE_SCHEMA,
        "experiment": EXPERIMENT,
        "registration_sha256": registration["content_sha256"],
        "created_at": _now(),
        "model": model,
        "ok": ok,
        "failure_reason": reason,
        "cost_micros": int(row.get("cost_micros") or 0),
        "truncated": bool(row.get("truncated")),
        "row": {k: v for k, v in row.items() if k != "answer"},
    }


def plan_view(probe: Mapping[str, Any]) -> dict[str, Any]:
    """`plan`이 보는 점검 기록. 허용 필드 밖(턴 행 · 판정)은 넘기지 않는다."""
    return {k: probe.get(k) for k in _PROBE_PLAN_FIELDS}


def plan_rounds(
    registration: Mapping[str, Any],
    probes: Mapping[str, Mapping[str, Any]],
    *,
    spent_micros: int,
    question_count: int,
) -> dict[str, Any]:
    models: list[str] = []
    excluded: list[dict[str, Any]] = []
    costs: list[int] = []
    for model in registration["models"]:
        probe = probes.get(model)
        if probe is None:
            excluded.append({"model": model, "reason": "점검 기록 없음"})
            continue
        view = plan_view(probe)
        if view["registration_sha256"] != registration["content_sha256"]:
            raise SystemExit(f"model_evidence: 다른 등록의 점검 기록이다: {model}")
        _require_after_registration(registration, str(view["created_at"]))
        if not view["ok"]:
            excluded.append({"model": model, "reason": view["failure_reason"]})
            continue
        models.append(model)
        costs.append(int(view["cost_micros"] or 0))
    cap = int(registration["cap_micros"])
    safety = float(registration["round_rule"]["safety"])
    unit = max([*costs, 1]) * safety
    per_round = len(models) * len(registration["conditions"]) * question_count
    rounds = 0
    projections: dict[str, int] = {}
    for r in range(int(registration["rounds_max"]), int(registration["rounds_min"]) - 1, -1):
        projected = spent_micros + round(r * per_round * unit)
        projections[str(r)] = projected
        if projected <= cap and models:
            rounds = r
            break
    reason = None
    if not models:
        reason = "점검을 통과한 모델이 없다"
    elif rounds == 0:
        reason = f"최소 {registration['rounds_min']}회차도 상한 {cap} micros 안에 들어가지 않는다"
    return {
        "schema": PLAN_SCHEMA,
        "experiment": EXPERIMENT,
        "registration_sha256": registration["content_sha256"],
        "created_at": _now(),
        "models": models,
        "excluded": excluded,
        "rounds": rounds,
        "reason": reason,
        "spent_micros_at_plan": spent_micros,
        "turn_unit_micros": round(unit),
        "turns_per_round": per_round,
        "projections": projections,
    }


def run_order(plan: Mapping[str, Any]) -> list[tuple[int, str]]:
    """회차 우선 순서. 한 회차의 모든 모델이 끝나야 다음 회차로 간다(설계 D5)."""
    return [(r, m) for r in range(1, int(plan["rounds"]) + 1) for m in plan["models"]]


def check_run_order(root: Path, plan: Mapping[str, Any], round_no: int, model: str) -> None:
    order = run_order(plan)
    if (round_no, model) not in order:
        raise SystemExit(f"model_evidence: 계획에 없는 실행이다: {round_no}회차 {model}")
    for earlier in order[: order.index((round_no, model))]:
        if not run_path(root, *earlier).exists():
            raise SystemExit(
                f"model_evidence: 앞선 실행의 기록이 없다: {earlier[0]}회차 {earlier[1]}"
            )


# ---------------------------------------------------------------------------
# 턴 판정 (설계 D6)
# ---------------------------------------------------------------------------


def enrich_turn(
    row: Mapping[str, Any],
    calls: list[Mapping[str, Any]],
    *,
    model: str,
    max_tokens: int,
) -> dict[str, Any]:
    """비용 회계 호출 행으로 수리 · 잘림 · 모델 일치를 판정한다.

    ⚠️ 정산 상태가 `settled`가 아니면 공급자가 돌려준 모델이 요청과 다르거나 최종 비용을 못 얻은
       것이다. 그 턴은 맞든 틀리든 등록 모델을 잰 것이 아니므로 측정 장애로 둔다(스펙).
    """
    status = str(row.get("status"))
    failure: str | None = None
    if status not in {"no-evidence", "error"} and not calls:
        failure = "usage_missing"
    for call in calls:
        if call.get("model") != model:
            failure = f"model_mismatch:{call.get('model')}"
            break
        if call.get("accounting_status") not in {"settled"}:
            failure = f"cost_{call.get('accounting_status')}"
    completion = [int(c.get("completion_tokens") or 0) for c in calls]
    enriched = {
        **row,
        "model": model,
        "llm_calls": len(calls),
        "repair_attempted": len(calls) > 1,
        "fallback": status == "fallback",
        "truncated": any(tokens >= max_tokens for tokens in completion),
        "prompt_tokens": sum(int(c.get("prompt_tokens") or 0) for c in calls),
        "completion_tokens": sum(completion),
        # 예약이 정산되기 전이면 예약액이 남는다. 상한 집행과 같은 보수적 값이다(설계 D4).
        "cost_micros": sum(int(c.get("budget_micros") or 0) for c in calls),
        "measurement_failure": failure,
    }
    return enriched


def judge(row: Mapping[str, Any], scope: str) -> dict[str, Any]:
    if row.get("status") == "not_run":
        return {"pass": None, "classification": "not_run", "reason": row.get("not_run_reason")}
    if row.get("measurement_failure"):
        return {
            "pass": None,
            "classification": "measurement_failure",
            "reason": row["measurement_failure"],
        }
    # ⚠️ 장애는 문항 종류보다 먼저 거른다. 공용 판정은 거절 문항(doc == "none")을 상태 · 채널을
    #    보기 전에 거절 규칙으로 보내서, 402 `error`는 잘못된 거절로, 채널 실패 뒤 `no-evidence`는
    #    정확한 거절로 세어 장애가 난 회차가 완료 회차로 들어간다(리뷰 r2).
    status = str(row.get("status"))
    if row.get("failed_channels"):
        return {
            "pass": None,
            "classification": "execution_failure",
            "reason": f"검색 채널 실패 {row['failed_channels']}",
        }
    if status not in {"resolved", "fallback", "no-evidence"}:
        return {"pass": None, "classification": "execution_failure", "reason": f"상태 {status}"}
    return ablation.answer_verdict(row, scope)


def fact_correct(row: Mapping[str, Any]) -> bool | None:
    """사실 정답: 기대 사실을 포함하고 금지 사실은 말하지 않았다(스펙: Per-turn verdicts).

    금지 사실 필드가 없는 옛 행은 기대 사실 포함과 같다.
    """
    if row.get("keyword_hit") is None:
        return None
    return bool(row["keyword_hit"]) and row.get("forbidden_hit") is not True


def counts_for_fact(row: Mapping[str, Any]) -> bool:
    """사실 포함 분모에 드는 턴: 답할 수 있고, 실행됐고, 장애가 없는 턴."""
    if row.get("doc") == "none":
        return False
    return row["verdict"]["classification"] not in {
        "not_run",
        "measurement_failure",
        "execution_failure",
    }


def summarize_rows(rows: list[Mapping[str, Any]], scope: str) -> dict[str, Any]:
    answerable = [r for r in rows if r.get("doc") != "none"]
    fact_rows = [r for r in rows if counts_for_fact(r)]
    # 거절 분모도 장애 턴을 뺀다. 장애는 거절 성공도 실패도 아니다.
    refusals = [
        r
        for r in rows
        if r.get("doc") == "none"
        and r["verdict"]["classification"]
        not in {"not_run", "measurement_failure", "execution_failure"}
    ]
    run = [r for r in rows if r.get("status") != "not_run"]
    elapsed = [float(r["elapsed_ms"]) for r in run if r.get("elapsed_ms") is not None]
    cost = sum(int(r.get("cost_micros") or 0) for r in rows)
    classes = [r["verdict"]["classification"] for r in rows]
    return {
        "diagnostic": scope != "both",
        "planned": len(rows),
        "asked": len(run),
        "answerable": len(answerable),
        "fact_denominator": len(fact_rows),
        "fact_included": sum(1 for r in fact_rows if r.get("keyword_hit")),
        "fact_correct": sum(1 for r in fact_rows if fact_correct(r)),
        "forbidden_hits": sum(1 for r in fact_rows if r.get("forbidden_hit") is True),
        # 제품 성적표 규칙(이중 인용 포함)은 `both`에만 묻는다.
        "product_passed": (
            sum(1 for r in answerable if r["verdict"].get("pass")) if scope == "both" else None
        ),
        "execution_failures": classes.count("execution_failure"),
        "measurement_failures": classes.count("measurement_failure"),
        "not_run": classes.count("not_run"),
        "refusal_correct": sum(1 for r in refusals if r["verdict"].get("pass")),
        "refusal_total": len(refusals),
        "fabricated_anchors": sum(int(r.get("fabricated_anchor_count") or 0) for r in rows),
        "repairs": sum(1 for r in rows if r.get("repair_attempted")),
        "fallbacks": sum(1 for r in rows if r.get("fallback")),
        "truncations": sum(1 for r in rows if r.get("truncated")),
        "prompt_tokens": sum(int(r.get("prompt_tokens") or 0) for r in rows),
        "completion_tokens": sum(int(r.get("completion_tokens") or 0) for r in rows),
        "cost_micros": cost,
        "cost_micros_per_question": round(cost / len(run)) if run else None,
        "latency_p50_ms": replay._percentile(elapsed, 0.5),
        "latency_p95_ms": replay._percentile(elapsed, 0.95),
    }


async def run_condition_turns(
    *,
    questions: list[dict[str, Any]],
    run_turn: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    spent: Callable[[], Awaitable[int]],
    cap_micros: int,
    estimate_micros: int,
    safety: float,
    stopped: list[str],
    rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """턴 직전마다 재생 DB 지출 + 다음 턴 추정이 상한 안인지 본다. 넘으면 남은 턴을 미실행으로 둔다.

    `stopped`는 조건 사이에 공유된다. 앞 조건에서 멈췄으면 뒤 조건은 돌지 않는다.
    `rows`를 넘기면 그 목록에 바로 쌓는다. 중간에 예외가 나도 이미 과금된 턴이 기록에 남는다.
    """
    rows = [] if rows is None else rows
    unit = estimate_micros
    consecutive_failures = 0
    for question in questions:
        if not stopped:
            current = await spent()
            if current + round(unit * safety) > cap_micros:
                stopped.append(
                    f"cap {cap_micros} micros: spent {current}, next turn estimate "
                    f"{round(unit * safety)}"
                )
        if stopped:
            rows.append(not_run_row(question, stopped[0]))
            continue
        try:
            row = await run_turn(question)
        except BaseException:
            # 공급자 호출 뒤 결과 조회에서 죽었을 수 있다. 묻지 않은 턴(not_run)과 구분해 남긴다.
            # 실제 지출은 재생 DB가 센다(설계 D4).
            rows.append(
                {
                    "id": question["id"],
                    "doc": question.get("doc"),
                    "status": "interrupted",
                    "cost_micros": 0,
                    "measurement_failure": "interrupted",
                    "verdict": {
                        "pass": None,
                        "classification": "measurement_failure",
                        "reason": "interrupted",
                    },
                }
            )
            raise
        unit = max(unit, int(row.get("cost_micros") or 0))
        rows.append(row)
        if row.get("measurement_failure"):
            # 등록 모델을 재지 못한 턴 뒤로는 같은 워커에서 계속해도 같은 장애다(스펙).
            stopped.append(f"measurement failure {row['id']}: {row['measurement_failure']}")
            continue
        failed = (row.get("verdict") or {}).get("classification") == "execution_failure"
        consecutive_failures = consecutive_failures + 1 if failed else 0
        if consecutive_failures >= MAX_CONSECUTIVE_EXECUTION_FAILURES:
            # 402 · 워커 다운처럼 이어지는 장애다. 계속 돌면 분모만 조용히 줄어든 회차가
            # 완료 회차로 집계된다. 멈춰서 그 회차를 부분으로 남긴다(설계 D5).
            stopped.append(f"execution failures {consecutive_failures} in a row at {row['id']}")
    return rows


def not_run_row(question: Mapping[str, Any], reason: str) -> dict[str, Any]:
    """돌지 않은 턴. 판정까지 붙여야 요약이 다른 턴과 같은 모양으로 읽는다."""
    return {
        "id": question["id"],
        "doc": question.get("doc"),
        "status": "not_run",
        "not_run_reason": reason,
        "cost_micros": 0,
        "verdict": {"pass": None, "classification": "not_run", "reason": reason},
    }


def fill_not_run(
    rows: list[dict[str, Any]], questions: list[dict[str, Any]], reason: str
) -> list[dict[str, Any]]:
    """예외로 끊긴 조건의 남은 문항을 미실행으로 채운다. 이미 돈 턴은 그대로 둔다."""
    done = {str(r["id"]) for r in rows}
    rows.extend(not_run_row(q, reason) for q in questions if str(q["id"]) not in done)
    return rows


def condition_entries(
    started: Mapping[str, list[dict[str, Any]]],
    questions: list[dict[str, Any]],
    reason: str | None,
) -> list[dict[str, Any]]:
    """두 조건 모두를 기록 모양으로 만든다. 시작 못 한 조건과 끊긴 조건의 남은 문항은 미실행이다.

    ⚠️ 시작한 조건만 남기면, 첫 조건에서 죽은 실행은 성적표에 한 줄도 남지 않는다(설계 D5).
    """
    entries = []
    for condition, scope in CONDITIONS.items():
        rows = list(started.get(condition, []))
        if reason is not None:
            fill_not_run(rows, questions, reason)
        entries.append(
            {
                "condition": condition,
                "scope": scope,
                "diagnostic": scope != "both",
                "rows": rows,
                "summary": summarize_rows(rows, scope),
            }
        )
    return entries


def build_run_record(
    *,
    registration: Mapping[str, Any],
    plan: Mapping[str, Any],
    round_no: int,
    model: str,
    conditions: list[dict[str, Any]],
    prompt_sha256: str | None,
    git_sha: str | None,
    stopped: str | None,
    spent_delta_micros: int | None,
    runtime: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": RUN_SCHEMA,
        "experiment": EXPERIMENT,
        "registration_sha256": registration["content_sha256"],
        "plan_sha256": canonical_sha256(plan),
        "created_at": _now(),
        "round": round_no,
        "model": model,
        "fixed_inputs": registration["fixed_inputs"],
        "fixed_inputs_sha256": canonical_sha256(registration["fixed_inputs"]),
        "answer_prompt_sha256": prompt_sha256,
        "git_sha": git_sha,
        "runtime": dict(runtime),
        "stopped": stopped,
        "spent_delta_micros": spent_delta_micros,
        "conditions": conditions,
        "limitations": [
            "합성 문서 8개 · 고정 30문항의 샘플 수치다",
            "위키는 이전 수집(Sonnet 컴파일)을 고정해 쓴다. 답변 모델만 다르다",
            "원문만은 진단 조건이며 이중 인용으로 판정하지 않는다",
            "회차는 독립 표본이 아니다",
        ],
    }


# ---------------------------------------------------------------------------
# JSONL 성적표 (설계 D7)
# ---------------------------------------------------------------------------

_LINE_SUMMARY_KEYS = (
    "planned",
    "asked",
    "answerable",
    "fact_denominator",
    "fact_included",
    "fact_correct",
    "forbidden_hits",
    "product_passed",
    "execution_failures",
    "measurement_failures",
    "not_run",
    "refusal_correct",
    "refusal_total",
    "fabricated_anchors",
    "repairs",
    "fallbacks",
    "truncations",
    "prompt_tokens",
    "completion_tokens",
    "cost_micros",
    "cost_micros_per_question",
    "latency_p50_ms",
    "latency_p95_ms",
)


def scoreboard_line(
    *,
    record: Mapping[str, Any],
    condition: Mapping[str, Any],
    run_file: str,
    reference: bool = False,
) -> dict[str, Any]:
    """실행 한 조건을 성적표 한 줄로 줄인다. 질문 · 답변 본문과 키는 넣지 않는다.

    ⚠️ 한 줄은 한 번 쓰면 고치지 않는다. 필드 이름을 바꾸면 옛 줄을 읽는 화면이 깨진다.
    """
    summary = condition["summary"]
    return {
        "experiment": EXPERIMENT,
        "reference": reference,
        "round": None if reference else record.get("round"),
        "model": record.get("model"),
        "condition": condition["condition"],
        "diagnostic": bool(summary.get("diagnostic")),
        **{k: summary.get(k) for k in _LINE_SUMMARY_KEYS},
        "stopped": record.get("stopped"),
        "git_sha": record.get("git_sha"),
        "registration_sha256": record.get("registration_sha256"),
        "fixed_inputs_sha256": record.get("fixed_inputs_sha256"),
        "answer_prompt_sha256": record.get("answer_prompt_sha256"),
        "run_file": run_file,
        "date": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def append_line(path: Path, line: Mapping[str, Any]) -> None:
    """한 줄을 덧붙인다. 앞선 줄은 읽지도 고치지도 않는다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, ensure_ascii=False) + "\n")


def read_lines(path: Path) -> tuple[list[dict[str, Any]], int]:
    """깨진 줄은 건너뛰고 개수를 돌려줘 화면이 알리게 한다."""
    if not path.exists():
        return [], 0
    lines: list[dict[str, Any]] = []
    broken = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            broken += 1
            continue
        if isinstance(parsed, dict):
            lines.append(parsed)
        else:
            broken += 1
    return lines, broken


def reference_conditions(
    answer_record: Mapping[str, Any], registration: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """#237 Sonnet 기록에서 두 조건만 골라 이 실험의 판정으로 다시 요약한다."""
    differing = differing_fixed_inputs(
        registration["fixed_inputs"], answer_record.get("fixed_inputs") or {}
    )
    if differing:
        raise SystemExit(f"model_evidence: 참조 기록의 고정 입력이 다르다: {differing}")
    out: list[dict[str, Any]] = []
    by_name = {str(c["condition"]): c for c in answer_record["conditions"]}
    for name, scope in CONDITIONS.items():
        source = by_name.get(name)
        if source is None:
            raise SystemExit(f"model_evidence: 참조 기록에 조건이 없다: {name}")
        rows = []
        for row in source["rows"]:
            # 옛 기록에는 정산 상태 · 호출 수가 없다. 수리 · 잘림은 모름(None)으로 둔다.
            item = {
                **row,
                "measurement_failure": None,
                "repair_attempted": None,
                "fallback": row.get("status") == "fallback",
                "truncated": None,
            }
            item["verdict"] = judge(item, scope)
            rows.append(item)
        summary = summarize_rows(rows, scope)
        summary["repairs"] = None
        summary["truncations"] = None
        out.append({"condition": name, "scope": scope, "rows": rows, "summary": summary})
    return out


# ---------------------------------------------------------------------------
# 성적표 화면 (설계 D7)
# ---------------------------------------------------------------------------


def _complete(line: Mapping[str, Any]) -> bool:
    return (
        not line.get("stopped")
        and line.get("planned") is not None
        and line.get("planned") == line.get("asked")
        and not line.get("measurement_failures")
    )


def complete_rounds(lines: list[Mapping[str, Any]], models: list[str]) -> list[int]:
    """모든 모델 · 조건이 끝난 회차만. 부분 회차는 모델 간 수치에서 뺀다(스펙)."""
    done: dict[int, set[tuple[str, str]]] = {}
    for line in lines:
        if line.get("reference") or line.get("round") is None or not _complete(line):
            continue
        done.setdefault(int(line["round"]), set()).add((str(line["model"]), str(line["condition"])))
    need = {(m, c) for m in models for c in CONDITIONS}
    return sorted(r for r, have in done.items() if need and need <= have)


def _fact_hits(rows: Iterable[Mapping[str, Any]]) -> dict[str, bool]:
    # 사실 정답 기준이다. 금지 사실이 없는 옛 기록은 기대 사실 포함과 같아 결과가 그대로다.
    return {str(r["id"]): bool(fact_correct(r)) for r in rows if counts_for_fact(r)}


def _types(rows: Iterable[Mapping[str, Any]]) -> dict[str, str | None]:
    return {str(r["id"]): r.get("qtype") for r in rows}


def load_condition_rows(root: Path, line: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    raw = str(line.get("run_file") or "")
    if not raw:
        return None
    path = Path(raw) if Path(raw).is_absolute() else root / raw
    if not path.exists():
        return None
    record = _read_json(path)
    conditions = record.get("conditions") or []
    if record.get("schema") != RUN_SCHEMA and line.get("reference"):
        registration = load_registration(root)
        conditions = reference_conditions(record, registration)
    for condition in conditions:
        if condition.get("condition") == line.get("condition"):
            return list(condition["rows"])
    return None


def model_summary(
    hits: Mapping[int, Mapping[str, Mapping[str, bool]]],
    types: Mapping[str, str | None] | None = None,
) -> dict[str, Any]:
    """회차 → 조건 → 문항 → 사실 정답. 모든 회차에 있는 문항만 짝 비교한다.

    `types`(문항 → 유형)가 있으면 유형별로도 나눈다. 거절 문항은 `hits`에 들어오지 않는다.
    """
    rounds = sorted(hits)
    per_condition: dict[str, list[int]] = {c: [] for c in CONDITIONS}
    for r in rounds:
        for c in CONDITIONS:
            per_condition[c].append(sum(1 for v in hits[r].get(c, {}).values() if v))
    shared: set[str] | None = None
    for r in rounds:
        for c in CONDITIONS:
            ids = set(hits[r].get(c, {}))
            shared = ids if shared is None else shared & ids
    shared = shared or set()
    stability: dict[str, dict[str, int]] = {}
    for c in CONDITIONS:
        stable_pass = stable_fail = flaky = 0
        for qid in shared:
            values = {hits[r][c][qid] for r in rounds}
            if values == {True}:
                stable_pass += 1
            elif values == {False}:
                stable_fail += 1
            else:
                flaky += 1
        stability[c] = {"stable_pass": stable_pass, "stable_fail": stable_fail, "flaky": flaky}
    recovered = sorted(
        q
        for q in shared
        if all(not hits[r]["source_onlyxbody"][q] and hits[r]["bothxbody"][q] for r in rounds)
    )
    regressed = sorted(
        q
        for q in shared
        if all(hits[r]["source_onlyxbody"][q] and not hits[r]["bothxbody"][q] for r in rounds)
    )
    diff = [
        b - s
        for s, b in zip(per_condition["source_onlyxbody"], per_condition["bothxbody"], strict=True)
    ]
    by_type: dict[str, dict[str, Any]] = {}
    # 짝 비교에 든 문항의 유형만 쓴다. 거절 문항은 `hits`에 없으니 여기서도 빠진다.
    for qtype in sorted({t for q in shared if (t := (types or {}).get(q))}):
        ids = {q for q in shared if (types or {}).get(q) == qtype}
        by_type[qtype] = {
            "denominator": len(ids),
            "source": [sum(1 for q in ids if hits[r]["source_onlyxbody"][q]) for r in rounds],
            "both": [sum(1 for q in ids if hits[r]["bothxbody"][q]) for r in rounds],
            "recovered": [q for q in recovered if q in ids],
            "regressed": [q for q in regressed if q in ids],
        }
    return {
        "rounds": rounds,
        "denominator": len(shared),
        "fact_by_condition": per_condition,
        "wiki_diff": diff,
        "stability": stability,
        "always_recovered": recovered,
        "always_regressed": regressed,
        "by_type": by_type,
    }


EFFECT_VERDICTS = ("supported", "not_supported", "inconclusive")
MIN_ROUNDS_FOR_VERDICT = 2


def model_verdict(
    summary: Mapping[str, Any], criterion: Mapping[str, int], *, measurement_failures: int
) -> str:
    """사전 등록 기준으로만 계산한다. 결과를 보고 기준을 고칠 길이 없게 등록 해시가 묶는다(스펙)."""
    if len(summary.get("rounds") or []) < MIN_ROUNDS_FOR_VERDICT or measurement_failures:
        return "inconclusive"
    net = len(summary["always_recovered"]) - len(summary["always_regressed"])
    return "supported" if net >= int(criterion["min_net_recovered"]) else "not_supported"


def overall_verdict(
    verdicts: Iterable[str], criterion: Mapping[str, int], *, measurement_failure: bool = False
) -> str:
    """스펙: 어느 모델이든 측정 장애가 있으면 전체도 판정 불가다. 지지 모델 수가 차도 그렇다."""
    values = list(verdicts)
    if measurement_failure:
        return "inconclusive"
    if values.count("supported") >= int(criterion["min_models"]):
        return "supported"
    if "inconclusive" in values:
        return "inconclusive"
    return "not_supported"


def _line_record(root: Path, line: Mapping[str, Any]) -> dict[str, Any] | None:
    raw = str(line.get("run_file") or "")
    path = Path(raw) if Path(raw).is_absolute() else root / raw
    return _read_json(path) if raw and path.exists() else None


def split_consistent(
    root: Path, lines: list[dict[str, Any]], registration: Mapping[str, Any] | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """같은 등록 · 고정 입력 · 답변 프롬프트로 만든 실행만 합산한다(스펙: Fixed ingestion).

    해시는 줄이 아니라 줄이 가리키는 실행 기록에서 읽는다. 옛 줄에는 해시 필드가 없을 수 있다.
    프롬프트 해시의 기준은 회차 순서상 첫 실행이다.
    """
    if registration is None:
        return lines, []
    fixed = canonical_sha256(registration["fixed_inputs"])
    records = [(line, _line_record(root, line)) for line in lines if not line.get("reference")]
    ordered = sorted(
        (r for _, r in records if r is not None),
        key=lambda r: (int(r.get("round") or 0), str(r.get("created_at"))),
    )
    prompt = ordered[0].get("answer_prompt_sha256") if ordered else None
    ok: list[dict[str, Any]] = [line for line in lines if line.get("reference")]
    mismatched: list[dict[str, Any]] = []
    for line, record in records:
        if (
            record is not None
            and record.get("registration_sha256") == registration["content_sha256"]
            and record.get("fixed_inputs_sha256") == fixed
            and record.get("answer_prompt_sha256") == prompt
        ):
            ok.append(line)
        else:
            mismatched.append(line)
    return ok, mismatched


def build_view(root: Path) -> dict[str, Any]:
    all_lines, broken = read_lines(root / SCOREBOARD_NAME)
    plan = _read_json(plan_path(root)) if plan_path(root).exists() else None
    registration = load_registration(root) if registration_path(root).exists() else None
    lines, mismatched = split_consistent(root, all_lines, registration)
    models = (
        list(plan["models"])
        if plan
        else sorted({str(x["model"]) for x in lines if not x.get("reference")})
    )
    rounds = complete_rounds(lines, models)
    have = {(x.get("round"), x.get("model")) for x in all_lines if not x.get("reference")}
    missing_runs = [
        {"round": r, "model": m} for r, m in (run_order(plan) if plan else []) if (r, m) not in have
    ]
    summaries: list[dict[str, Any]] = []
    criterion = (registration or {}).get("effect_criterion")
    for model in models:
        hits: dict[int, dict[str, dict[str, bool]]] = {}
        types: dict[str, str | None] = {}
        for line in lines:
            if line.get("reference") or line.get("model") != model:
                continue
            if line.get("round") not in rounds or not _complete(line):
                continue
            rows = load_condition_rows(root, line)
            if rows is not None:
                hits.setdefault(int(line["round"]), {})[str(line["condition"])] = _fact_hits(rows)
                types.update(_types(rows))
        complete = {r: v for r, v in hits.items() if set(v) >= set(CONDITIONS)}
        summary = (
            {"model": model, "reference": False, **model_summary(complete, types)}
            if complete
            else {"model": model, "reference": False, "rounds": []}
        )
        if criterion:
            failures = sum(
                int(x.get("measurement_failures") or 0)
                for x in lines
                if not x.get("reference") and x.get("model") == model
            )
            summary["verdict"] = model_verdict(summary, criterion, measurement_failures=failures)
            summary["measurement_failures"] = failures
        summaries.append(summary)
    effect = (
        {
            "criterion": criterion,
            "overall": overall_verdict(
                (s["verdict"] for s in summaries if not s.get("reference")),
                criterion,
                measurement_failure=any(s.get("measurement_failures") for s in summaries),
            ),
        }
        if criterion
        else None
    )
    ref_hits: dict[str, dict[str, bool]] = {}
    ref_model = None
    for line in lines:
        if line.get("reference"):
            rows = load_condition_rows(root, line)
            ref_model = line.get("model")
            if rows is not None:
                ref_hits[str(line["condition"])] = _fact_hits(rows)
    if set(ref_hits) >= set(CONDITIONS):
        summaries.append({"model": ref_model, "reference": True, **model_summary({0: ref_hits})})
    partial = sorted(
        {
            int(x["round"])
            for x in [*lines, *missing_runs]
            if not x.get("reference") and x.get("round") is not None and x["round"] not in rounds
        }
    )
    return {
        # 화면의 실행별 표는 해시가 어긋난 줄도 보여 준다. 합산에서만 뺀다.
        "lines": all_lines,
        "broken": broken,
        "plan": plan,
        "mismatched": mismatched,
        "missing_runs": missing_runs,
        "complete_rounds": rounds,
        "partial_rounds": partial,
        "summaries": summaries,
        "effect": effect,
    }


_CONDITION_LABEL = {"source_onlyxbody": "원문만 (진단)", "bothxbody": "원문+위키"}


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _usd(micros: Any, digits: int = 4) -> str:
    return "—" if micros is None else f"${int(micros) / 1_000_000:.{digits}f}"


def _secs(ms: Any) -> str:
    return "—" if ms is None else f"{float(ms) / 1000:.1f}s"


def _bar(numerator: Any, denominator: Any) -> str:
    if not denominator:
        return "—"
    pct = int(numerator or 0) / int(denominator) * 100
    return (
        f'<div class="bar"><i style="width:{pct:.0f}%"></i></div>'
        f"<b>{_e(numerator)}/{_e(denominator)}</b>"
    )


def _flag(value: Any) -> str:
    if value is None:
        return '<span class="muted">모름</span>'
    return f'<span class="warn">{_e(value)}</span>' if value else "0"


_STYLE = """
body{margin:0;background:#111317;color:#e8eaf0;padding:40px 48px;
  font:16px/1.5 "Apple SD Gothic Neo",system-ui,sans-serif}
h1{font-size:28px;margin:0 0 6px}h2{font-size:20px;margin:36px 0 10px}
p{color:#9aa1b2;margin:0 0 12px}table{border-collapse:collapse;width:100%}
th{text-align:left;color:#9aa1b2;font-weight:600;padding:10px 12px;
  border-bottom:1px solid #2c313c}
td{padding:12px;border-bottom:1px solid #2c313c}th,td{white-space:nowrap}
.bar{display:inline-block;width:110px;height:10px;background:#232733;
  border-radius:5px;margin-right:8px;vertical-align:middle}
.bar i{display:block;height:10px;background:#4f7cf0;border-radius:5px}
.tag{font-size:12px;padding:1px 6px;border:1px solid #3a4150;border-radius:4px;color:#9aa1b2}
.warn{color:#f0a04f}.muted{color:#6b7385}.wrap{overflow-x:auto}
"""
_SUMMARY_HEAD = (
    "모델",
    "원문만 (진단)",
    "원문+위키",
    "위키 차이",
    "늘 복구",
    "늘 회귀",
    "안정 통과·안정 실패·흔들림 (위키 / 원문)",
)
_RUN_HEAD = (
    "회차",
    "모델",
    "조건",
    "사실 정답",
    "제품 통과",
    "거절",
    "장애·측정·미실행",
    "위조 앵커",
    "수리·Fallback",
    "잘림",
    "토큰",
    "$/문항",
    "p50 · p95",
    "시각",
)


def _tr(cells: Iterable[str]) -> str:
    """셀 값은 이미 이스케이프된 HTML 조각이어야 한다."""
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def _table(head: Iterable[str], rows: str, empty: str) -> str:
    columns = list(head)
    header = "".join(f"<th>{_e(h)}</th>" for h in columns)
    body = rows or f'<tr><td colspan="{len(columns)}" class="muted">{_e(empty)}</td></tr>'
    return f'<div class="wrap"><table><tr>{header}</tr>{body}</table></div>'


def _summary_row(s: Mapping[str, Any]) -> str:
    tag = ' <span class="tag">참조 · 1회</span>' if s.get("reference") else ""
    if not s.get("rounds") and not s.get("reference"):
        return _tr([_e(s["model"]), '<span class="muted">완료 회차 없음</span>', *[""] * 5])
    facts, stab, denominator = s["fact_by_condition"], s["stability"], _e(s["denominator"])
    source = " · ".join(map(str, facts["source_onlyxbody"]))
    both = " · ".join(map(str, facts["bothxbody"]))
    diff = " · ".join(f"{d:+d}" for d in s["wiki_diff"])
    flaky = " / ".join(
        "·".join(str(stab[c][k]) for k in ("stable_pass", "stable_fail", "flaky"))
        for c in ("bothxbody", "source_onlyxbody")
    )
    return _tr(
        [
            _e(s["model"]) + tag,
            f"{_e(source)} / {denominator}",
            f"{_e(both)} / {denominator}",
            f"<b>{_e(diff)}</b>",
            _e(", ".join(s["always_recovered"]) or "-"),
            _e(", ".join(s["always_regressed"]) or "-"),
            _e(flaky),
        ]
    )


def _run_row(line: Mapping[str, Any]) -> str:
    tags = []
    if line.get("reference"):
        tags.append('<span class="tag">참조</span>')
    if line.get("stopped"):
        tags.append('<span class="tag warn">중단</span>')
    product = (
        "—"
        if line.get("product_passed") is None
        else f"{_e(line.get('product_passed'))}/{_e(line.get('answerable'))}"
    )
    condition = str(line.get("condition"))
    failures = " · ".join(
        _flag(line.get(k)) for k in ("execution_failures", "measurement_failures", "not_run")
    )
    tokens = int(line.get("prompt_tokens") or 0) + int(line.get("completion_tokens") or 0)
    return _tr(
        [
            _e("ref" if line.get("reference") else line.get("round")),
            f"{_e(line.get('model'))} {' '.join(tags)}",
            _e(_CONDITION_LABEL.get(condition, condition)),
            # 사실 정답이 있으면 그것을, 옛 줄이면 사실 포함을 그린다(금지 사실이 없으면 같다).
            _bar(line.get("fact_correct", line.get("fact_included")), line.get("fact_denominator")),
            product,
            f"{_e(line.get('refusal_correct'))}/{_e(line.get('refusal_total'))}",
            failures,
            _flag(line.get("fabricated_anchors")),
            f"{_flag(line.get('repairs'))} · {_flag(line.get('fallbacks'))}",
            _flag(line.get("truncations")),
            f"{tokens:,}",
            _usd(line.get("cost_micros_per_question"), 5),
            f"{_secs(line.get('latency_p50_ms'))} · {_secs(line.get('latency_p95_ms'))}",
            f'<span class="muted">{_e(line.get("date"))}</span>',
        ]
    )


_VERDICT_LABEL = {
    "supported": "지지",
    "not_supported": "지지 안 됨",
    "inconclusive": "판정 불가",
}
_TYPE_HEAD = ("모델", "유형", "원문만", "원문+위키", "위키 차이", "늘 복구", "늘 회귀")
_REFUSAL_HEAD = ("모델", "조건", "회차별 정확한 거절")


def _effect_section(view: Mapping[str, Any]) -> list[str]:
    """사전 등록한 효과 판정과 유형별 표. 등록에 기준이 없으면(이전 실험) 그리지 않는다."""
    effect = view.get("effect")
    if not effect:
        return []
    criterion = effect["criterion"]
    per_model = " · ".join(
        f"{s['model']} {_VERDICT_LABEL.get(s.get('verdict'), s.get('verdict'))}"
        for s in view["summaries"]
        if not s.get("reference")
    )
    type_rows = ""
    for s in view["summaries"]:
        if s.get("reference"):
            continue
        for qtype, t in (s.get("by_type") or {}).items():
            n = _e(t["denominator"])
            type_rows += _tr(
                [
                    _e(s["model"]),
                    _e(qtype),
                    f"{_e(' · '.join(map(str, t['source'])))} / {n}",
                    f"{_e(' · '.join(map(str, t['both'])))} / {n}",
                    # 스펙 · 설계 D8: 유형별로도 위키 차이(원문+위키 − 원문만)를 회차마다 보인다.
                    "<b>"
                    + _e(
                        " · ".join(
                            f"{b - s:+d}" for s, b in zip(t["source"], t["both"], strict=True)
                        )
                    )
                    + "</b>",
                    _e(", ".join(t["recovered"]) or "-"),
                    _e(", ".join(t["regressed"]) or "-"),
                ]
            )
    refusal_rows = ""
    for model in sorted({str(x["model"]) for x in view["lines"] if not x.get("reference")}):
        for condition in CONDITIONS:
            cells = [
                f"{x.get('round')}회: {x.get('refusal_correct')}/{x.get('refusal_total')}"
                for x in sorted(
                    (
                        x
                        for x in view["lines"]
                        if not x.get("reference")
                        and x.get("model") == model
                        and x.get("condition") == condition
                    ),
                    key=lambda x: int(x.get("round") or 0),
                )
            ]
            refusal_rows += _tr(
                [_e(model), _e(_CONDITION_LABEL[condition]), _e(" · ".join(cells) or "-")]
            )
    return [
        f"<h2>효과 판정: {_e(_VERDICT_LABEL.get(effect['overall'], effect['overall']))}</h2>",
        f"<p>사전 등록 기준: 모델마다 늘 복구 − 늘 회귀 ≥ {_e(criterion['min_net_recovered'])}"
        f"이면 지지, 지지 모델이 {_e(criterion['min_models'])}개 이상이면 전체 지지. "
        f"완료 회차가 {MIN_ROUNDS_FOR_VERDICT}개 미만이거나 측정 장애가 있으면 판정 불가.</p>",
        f"<p>{_e(per_model)}</p>",
        "<h2>유형별 위키 차이 (완료 회차, 사실 정답)</h2>",
        _table(_TYPE_HEAD, type_rows, "유형 정보가 없다"),
        "<h2>거절 문항 (효과 판정에서 제외)</h2>",
        "<p>⚠️ 채점기는 답이 표준 거절 문구로 시작할 때만 거절로 인정한다(#254 한계).</p>",
        _table(_REFUSAL_HEAD, refusal_rows, "기록이 없다"),
    ]


def render_html(view: Mapping[str, Any]) -> str:
    plan = view.get("plan")
    notes = []
    if plan:
        notes.append(f"계획 {plan.get('rounds')}회차 · 모델 {len(plan.get('models') or [])}종")
        excluded = ", ".join(f"{x['model']} ({x['reason']})" for x in plan.get("excluded") or [])
        if excluded:
            notes.append(f"제외: {excluded}")
    notes.append("완료 회차: " + (", ".join(map(str, view["complete_rounds"])) or "없음"))
    if view["partial_rounds"]:
        notes.append("부분 회차(비교 제외): " + ", ".join(map(str, view["partial_rounds"])))
    if view.get("missing_runs"):
        missing = ", ".join(f"{x['round']}회차 {x['model']}" for x in view["missing_runs"])
        notes.append(f"기록 없는 계획 실행: {missing}")
    if view.get("mismatched"):
        notes.append(f"해시가 달라 합산에서 뺀 줄 {len(view['mismatched'])}개")
    broken = (
        f'<p class="warn">읽지 못한 줄 {view["broken"]}개를 건너뛰었다</p>'
        if view["broken"]
        else ""
    )
    summary = "".join(_summary_row(s) for s in view["summaries"])
    runs = "".join(_run_row(line) for line in view["lines"])
    parts = [
        '<!doctype html><meta charset="utf-8"><title>모델별 위키 기여 성적표</title>',
        f"<style>{_STYLE}</style>",
        "<h1>모델별 위키 기여 성적표</h1>",
        "<p>같은 수집 · 같은 문항에서 답변 모델만 바꿔, 원문만과 원문+위키를 회차마다 "
        "비교한다. 합성 샘플 수치다.</p>",
        f"<p>{_e(' · '.join(notes))}</p>",
        broken,
        *_effect_section(view),
        "<h2>모델 요약 (완료 회차만)</h2>",
        '<p>사실 포함은 회차별 값이다. 위키 차이 = 원문+위키 − 원문만. "늘 복구"는 모든 완료 '
        "회차에서 원문만은 놓치고 원문+위키는 맞힌 문항이다.</p>",
        _table(_SUMMARY_HEAD, summary, "아직 완료 회차가 없다"),
        "<h2>실행별</h2>",
        "<p>실패 신호를 먼저 본다: 장애 · 측정 장애 · 미실행, 위조 앵커, 수리 · Fallback, "
        "출력 상한 잘림.</p>",
        _table(_RUN_HEAD, runs, "아직 기록이 없다"),
    ]
    return "\n".join(parts)


def assert_loopback_host(host: str) -> str:
    if host not in replay._LOOPBACK_HOSTS:
        raise SystemExit(f"model_evidence: 루프백이 아닌 주소에는 성적표를 열지 않는다: {host}")
    return host


# ---------------------------------------------------------------------------
# 재생 스택 조회
# ---------------------------------------------------------------------------


def spent_since(stack: str, workspace: str, since: str) -> int:
    """등록 시각 이후 재생 워크스페이스의 예산 지출. 미정산 예약도 예약액으로 센다(설계 D4).

    ⚠️ service_role(BYPASSRLS) 키로 부른다. 호출부가 이미 검사해도 여기서 루프백을 다시 강제한다.
    """
    stack = replay.assert_loopback(stack)
    with httpx.Client(timeout=30) as client:
        response = client.post(
            f"{stack}/rest/v1/rpc/sum_usage_events_since",
            headers=replay._service_headers(),
            json={"p_workspace_id": workspace, "p_since": since},
        )
        response.raise_for_status()
        return int(response.json() or 0)


def trace_calls(stack: str, workspace: str, token: str, trace_id: str) -> list[dict[str, Any]]:
    """요청자 JWT로 그 턴의 Ask 비용 호출 행. 정산이 끝날 때까지 잠시 기다린다."""
    deadline = time.monotonic() + _SETTLE_WAIT_SECONDS
    rows: list[dict[str, Any]] = []
    with httpx.Client(timeout=30) as client:
        while True:
            response = client.post(
                f"{stack}/rest/v1/rpc/ask_cost_trace_calls",
                headers={"apikey": replay.LOCAL_ANON_KEY, "Authorization": f"Bearer {token}"},
                json={"p_workspace_id": workspace, "p_trace_id": trace_id},
            )
            response.raise_for_status()
            rows = list(response.json() or [])
            pending = any(r.get("accounting_status") in _PENDING_STATUSES for r in rows)
            if not pending or time.monotonic() > deadline:
                return rows
            time.sleep(0.5)


def read_runtime(path: Path, model: str) -> dict[str, Any]:
    """서버 스크립트가 남긴 워커 설정. 다른 모델로 뜬 워커면 유료 호출 전에 멈춘다."""
    if not path.exists():
        raise SystemExit(f"model_evidence: 워커 런타임 manifest가 없다: {path}")
    runtime = _read_json(path)
    if runtime.get("model") != model:
        raise SystemExit(
            f"model_evidence: 워커 모델이 다르다: 기대 {model}, 실제 {runtime.get('model')}"
        )
    settings = runtime.get("model_settings") or {}
    if not isinstance(settings.get("max_tokens"), int):
        raise SystemExit("model_evidence: 워커 비용 정책에 max_tokens가 없다")
    return runtime


class Harness:
    """한 모델 워커에 붙어 조건별로 턴을 돌리는 프로세스 내 Ask.

    `retrieval_ablation answer`와 같은 경로다(설계 D1).
    """

    def __init__(self, registration: Mapping[str, Any], *, worker_url: str, llm_token: str) -> None:
        paths = registration["paths"]
        self.state = _read_json(Path(paths["state"]))
        self.stack = replay.assert_loopback(self.state["stack_url"])
        self.worker = replay.assert_loopback(worker_url)
        self.llm_token = llm_token
        self.sample = replay._load_sample(Path(paths["sample"]))
        self.questions = ablation._questions_for(self.state, self.sample, 0)
        self.workspace = str(self.state["workspace_id"])
        corpus = ablation.load_corpus(self.stack, self.state, self.sample, self.questions)
        self.token = corpus["token"]
        self.query_vectors = ablation.load_query_vectors(
            Path(paths["query_vectors"]), self.questions
        )
        actual = {
            "snapshot_sha256": corpus["snapshot"]["snapshot_sha256"],
            "chunk_boundaries_sha256": corpus["snapshot"]["chunk_boundaries_sha256"],
            "fixture_sha256": ablation.fingerprint.fixture_sha256(self.sample),
            "query_vectors_sha256": (
                ablation.query_vectors_sha256(self.query_vectors) if self.query_vectors else None
            ),
        }
        # ⚠️ 재수집된 스택이면 위키가 다시 컴파일된 것이다. 답변 모델만 바꾼 비교가 아니게 된다.
        differing = differing_fixed_inputs(registration["fixed_inputs"], actual)
        if differing:
            raise SystemExit(f"model_evidence: 고정 입력이 등록과 다르다: {differing}")
        self.prompt_sha = ablation._default_ask_prompt_sha256(
            self.stack, self.workspace, self.token
        )

    def spent(self, since: str) -> int:
        return spent_since(self.stack, self.workspace, since)

    async def run(
        self,
        model: str,
        max_tokens: int,
        work: Callable[
            [Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]], Awaitable[Any]
        ],
    ) -> Any:
        from api.db.user import UserDb
        from api.routers.ask import _start_ask_turn
        from api.services.ask import (
            AskService,
            HttpAskTurnExporter,
            HttpLlmStreamClient,
            drain_turn_exports,
        )
        from api.services.retrieval import RetrievalService
        from nexuswiki_core.trace import bind_trace, current_trace_id, new_trace_id

        async with httpx.AsyncClient(timeout=180) as http:
            user_db = UserDb(
                http,
                supabase_url=self.stack,
                publishable_key=replay.LOCAL_ANON_KEY,
                access_token=self.token,
            )
            embedder = ablation.FixedQueryEmbeddingClient(self.query_vectors)
            llm = HttpLlmStreamClient(
                http, url=self.worker, token=self.llm_token, timeout_seconds=130
            )
            exporter = HttpAskTurnExporter(http, url=self.worker, token=self.llm_token)
            services = {
                name: AskService(
                    RetrievalService(embedder, policy=ablation.scope_policy(scope)),
                    llm,
                    exporter,
                    quality_mode="enforce",
                )
                for name, scope in CONDITIONS.items()
            }

            async def run_turn(condition: str, question: dict[str, Any]) -> dict[str, Any]:
                turn_id = uuid4()
                bind_trace(new_trace_id())
                thread_id = await _start_ask_turn(
                    db=user_db,
                    workspace_id=UUID(self.workspace),
                    thread_id=None,
                    client_turn_id=turn_id,
                    query=str(question["query"]),
                )
                trace_id = current_trace_id() or ""
                started = time.monotonic()
                events = [
                    event
                    async for event in services[condition].ask(
                        workspace_id=UUID(self.workspace),
                        query=str(question["query"]),
                        requested_k=ablation.REQUESTED_K,
                        template_id=None,
                        user_db=user_db,
                        thread_id=thread_id,
                        client_turn_id=turn_id,
                    )
                ]
                elapsed = round((time.monotonic() - started) * 1000)
                message = await asyncio.to_thread(
                    ablation._turn_message, self.stack, self.workspace, self.token, str(turn_id)
                )
                calls = await asyncio.to_thread(
                    trace_calls, self.stack, self.workspace, self.token, trace_id
                )
                row = ablation.turn_row(question, events, message, [], elapsed)
                # 유형 시험지가 아니면 None이다(기존 30문항은 유형이 없다).
                row["qtype"] = question.get("type")
                row["fact_correct"] = fact_correct(row)
                row = enrich_turn(row, calls, model=model, max_tokens=max_tokens)
                row["verdict"] = judge(row, CONDITIONS[condition])
                print(
                    f"model_evidence: {model} {condition} {row['id']} {row['status']} "
                    f"fact={row.get('keyword_hit')} cost={row['cost_micros']} "
                    f"calls={row['llm_calls']} trunc={row['truncated']}"
                    + (
                        f" MEASUREMENT={row['measurement_failure']}"
                        if row["measurement_failure"]
                        else ""
                    )
                )
                return row

            try:
                return await work(run_turn)
            finally:
                await drain_turn_exports()


# ---------------------------------------------------------------------------
# 명령
# ---------------------------------------------------------------------------


def cmd_budget_open(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    out = budget_path(root)
    if out.exists():
        raise SystemExit(f"model_evidence: 이미 있는 예산 기록은 덮어쓰지 않는다: {out}")
    sample_path = Path(args.sample).resolve()
    budget = build_budget(
        total_cap_micros=args.cap_micros,
        compile_model=args.compile_model,
        answer_models=list(args.models),
        sample=replay._load_sample(sample_path),
        sample_path=str(sample_path),
    )
    write_new(out, budget)
    print(f"model_evidence: 예산 개시 {budget['total_cap_micros']} micros → {out}")
    return 0


def cmd_retry_dead(args: argparse.Namespace) -> int:
    """수집 잡이 모두 끝나길 기다린 뒤, `dead` 잡만 제품 재시도 API(요청자 JWT)로 다시 넣는다.

    ⚠️ `jobs`를 직접 고치지 않는다(CLAUDE.md Anti-Patterns). 재시도는 `retry_dead_job` RPC를 타는
       API뿐이다. 그 함수가 실패 흔적을 지우므로 재시도마다 `job-retries.jsonl`에 한 줄을 남긴다.
    ⚠️ `failed`는 자동 재시도 대기라 기다린다. 끝난 상태로 보면 아직 도는 잡을 기록하게 된다.
    """
    root = Path(args.dir)
    state = _read_json(Path(args.state))
    stack = replay.assert_loopback(state["stack_url"])
    api = replay.assert_loopback(args.api_url)
    workspace = str(state["workspace_id"])
    done = {"succeeded", "dead", "canceled"}

    def drain(client: httpx.Client) -> list[dict[str, Any]]:
        deadline = time.monotonic() + args.timeout
        while True:
            rows = replay.select_capped(
                client,
                stack,
                "jobs",
                {"workspace_id": f"eq.{workspace}", "select": "id,type,status"},
            )
            if all(r["status"] in done for r in rows):
                return rows
            if time.monotonic() > deadline:
                raise SystemExit("model_evidence: 수집 잡이 시간 안에 끝나지 않았다")
            time.sleep(5)

    with httpx.Client(timeout=60) as client:
        rows = drain(client)
        for attempt in range(1, args.rounds + 1):
            dead = [r for r in rows if r["status"] == "dead"]
            if not dead:
                break
            token = replay._login(client, stack, state)
            for row in dead:
                response = client.post(
                    f"{api}/workspaces/{workspace}/jobs/{row['id']}/retry",
                    headers={"Authorization": f"Bearer {token}"},
                )
                append_line(
                    root / RETRIES_NAME,
                    {
                        "job_id": row["id"],
                        "type": row["type"],
                        "attempt": attempt,
                        "status_code": response.status_code,
                        "at": _now(),
                    },
                )
                print(f"model_evidence: 재시도 {attempt}회 {row['type']} → {response.status_code}")
            time.sleep(10)
            rows = drain(client)
    left = [r for r in rows if r["status"] != "succeeded"]
    print(f"model_evidence: 남은 실패 잡 {len(left)}개")
    return 0 if not left else 1


def cmd_ingest_record(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    budget = _read_json(budget_path(root))
    out = ingestion_path(root)
    if out.exists():
        raise SystemExit(f"model_evidence: 이미 있는 수집 기록은 덮어쓰지 않는다: {out}")
    state = _read_json(Path(args.state))
    stack = replay.assert_loopback(state["stack_url"])
    workspace = str(state["workspace_id"])
    with httpx.Client(timeout=60) as client:
        # service_role 조회다. `_select`가 workspace_id 필터 없는 조회를 거부하고,
        # `select_capped`는 1000행에서 잘린 집계를 거부한다.
        jobs = replay.select_capped(
            client,
            stack,
            "jobs",
            {"workspace_id": f"eq.{workspace}", "select": "id,type,status,attempts,last_error"},
        )
        pages = replay.select_capped(
            client, stack, "wiki_pages", {"workspace_id": f"eq.{workspace}", "select": "id"}
        )
        sources = replay.select_capped(
            client, stack, "raw_sources", {"workspace_id": f"eq.{workspace}", "select": "id"}
        )
        usage = replay.select_capped(
            client,
            stack,
            "usage_events",
            {"workspace_id": f"eq.{workspace}", "kind": "eq.llm", "select": "model,metadata"},
        )
    compile_models = [
        str(u["model"]) for u in usage if (u.get("metadata") or {}).get("call") == "compile"
    ]
    record = build_ingestion(
        budget=budget,
        jobs=jobs,
        pages=len(pages),
        documents=len(sources),
        compile_models=compile_models,
        spent_micros=spent_since(stack, workspace, EPOCH),
        workspace_id=workspace,
        recovered=recovered_jobs(read_lines(root / RETRIES_NAME)[0], jobs),
    )
    write_new(out, record)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0 if record["ok"] else 1


def cmd_register(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    out = registration_path(root)
    if out.exists():
        raise SystemExit(f"model_evidence: 이미 있는 등록은 덮어쓰지 않는다: {out}")
    reference = Path(args.reference_retrieval)
    retrieval = _read_json(reference)
    if retrieval.get("phase") != "retrieval" or "fixed_inputs" not in retrieval:
        raise SystemExit("model_evidence: --reference-retrieval에는 검색 단계 기록을 준다")
    cap_micros = args.cap_micros
    budget_summary: dict[str, Any] | None = None
    effect_criterion: dict[str, int] | None = None
    if budget_path(root).exists():
        # 전 단계 상한 실험(설계 D5): 재생 상한은 총 상한에서 이미 쓴 돈을 뺀 값이다.
        budget = _read_json(budget_path(root))
        if not ingestion_path(root).exists():
            raise SystemExit("model_evidence: 수집 기록(ingestion.json)이 없다. 등록하지 않는다")
        ingestion = _read_json(ingestion_path(root))
        # 예산 개시 때 적은 답변 모델의 부분집합만 허용한다. 점검 비용으로 상한에 안 들어가는
        # 모델을 빼고 다시 등록할 수 있게 하되, 컴파일 모델과 겹치는 새 모델은 못 넣는다.
        if not args.models or not set(args.models) <= set(budget["answer_models"]):
            raise SystemExit("model_evidence: 답변 모델이 예산 개시 기록의 부분집합이 아니다")
        sample = replay._load_sample(Path(args.sample))
        if ablation.fingerprint.fixture_sha256(sample) != budget["fixture_sha256"]:
            raise SystemExit("model_evidence: 시험지가 예산 개시 뒤에 바뀌었다. 등록하지 않는다")
        state = _read_json(Path(args.state))
        recorded = ingestion.get("workspace_id")
        if recorded is not None and recorded != str(state["workspace_id"]):
            raise SystemExit("model_evidence: state의 워크스페이스가 수집 기록과 다르다")
        spent = spent_since(
            replay.assert_loopback(state["stack_url"]), str(state["workspace_id"]), EPOCH
        )
        cap_micros = replay_cap(budget, ingestion, spent)
        budget_summary = {
            "total_cap_micros": budget["total_cap_micros"],
            "compile_model": budget["compile_model"],
            "spent_before_registration_micros": spent,
            "fixture_sha256": budget["fixture_sha256"],
        }
        effect_criterion = {
            "min_net_recovered": args.min_net_recovered,
            "min_models": args.min_models,
        }
    registration = build_registration(
        models=list(args.models),
        rounds_max=args.rounds_max,
        rounds_min=args.rounds_min,
        cap_micros=cap_micros,
        effect_criterion=effect_criterion,
        budget=budget_summary,
        probe_question=args.probe_question,
        probe_estimate_micros=args.probe_estimate_micros,
        safety=args.safety,
        fixed_inputs=retrieval["fixed_inputs"],
        reference_retrieval_sha256=ablation.fingerprint.text_sha256(
            reference.read_text(encoding="utf-8")
        ),
        paths={
            "state": str(Path(args.state).resolve()),
            "query_vectors": str(Path(args.query_vectors).resolve()),
            "sample": str(Path(args.sample).resolve()),
        },
    )
    write_new(out, registration)
    print(f"model_evidence: 사전 등록 {registration['content_sha256'][:12]} → {out}")
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    registration = load_registration(root)
    model = args.model
    if model not in registration["models"]:
        raise SystemExit(f"model_evidence: 등록되지 않은 모델이다: {model}")
    out = probe_path(root, model)
    if out.exists():
        raise SystemExit(f"model_evidence: 이미 있는 점검 기록은 덮어쓰지 않는다: {out}")
    runtime = read_runtime(Path(args.runtime_manifest), model)
    max_tokens = int(runtime["model_settings"]["max_tokens"])
    harness = Harness(registration, worker_url=args.worker_url, llm_token=args.llm_token)
    question = next(
        (q for q in harness.questions if q["id"] == registration["probe"]["question"]), None
    )
    if question is None:
        raise SystemExit("model_evidence: 점검 문항이 질문 세트에 없다")
    spent = harness.spent(str(registration["created_at"]))
    estimate = int(registration["probe"]["estimate_micros"])
    if spent + estimate > int(registration["cap_micros"]):
        raise SystemExit(f"model_evidence: 점검이 상한을 넘길 수 있다: spent {spent}")

    async def work(run_turn: Callable[..., Awaitable[dict[str, Any]]]) -> dict[str, Any]:
        return await run_turn("bothxbody", question)

    row = asyncio.run(harness.run(model, max_tokens, work))
    record = build_probe_record(registration, model, row)
    write_new(out, record)
    print(
        f"model_evidence: 점검 {model} ok={record['ok']} cost={record['cost_micros']} "
        f"truncated={record['truncated']} → {out}"
    )
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    registration = load_registration(root)
    out = plan_path(root)
    if out.exists():
        raise SystemExit(f"model_evidence: 이미 있는 계획은 덮어쓰지 않는다: {out}")
    probes = {
        model: _read_json(probe_path(root, model))
        for model in registration["models"]
        if probe_path(root, model).exists()
    }
    state = _read_json(Path(registration["paths"]["state"]))
    stack = replay.assert_loopback(state["stack_url"])
    sample = replay._load_sample(Path(registration["paths"]["sample"]))
    questions = ablation._questions_for(state, sample, 0)
    spent = spent_since(stack, str(state["workspace_id"]), str(registration["created_at"]))
    plan = plan_rounds(registration, probes, spent_micros=spent, question_count=len(questions))
    write_new(out, plan)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0 if plan["rounds"] else 1


def cmd_order(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    if args.kind == "probe":
        for model in load_registration(root)["models"]:
            if not probe_path(root, model).exists():
                print(f"0 {model}")
        return 0
    plan = _read_json(plan_path(root))
    for round_no, model in run_order(plan):
        if not run_path(root, round_no, model).exists():
            print(f"{round_no} {model}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    registration = load_registration(root)
    plan = _read_json(plan_path(root))
    if plan.get("registration_sha256") != registration["content_sha256"]:
        raise SystemExit("model_evidence: 다른 등록의 계획이다")
    round_no, model = int(args.round), args.model
    check_run_order(root, plan, round_no, model)
    out = run_path(root, round_no, model)
    if out.exists():
        raise SystemExit(f"model_evidence: 이미 있는 실행 기록은 덮어쓰지 않는다: {out}")
    runtime = read_runtime(Path(args.runtime_manifest), model)
    max_tokens = int(runtime["model_settings"]["max_tokens"])
    harness = Harness(registration, worker_url=args.worker_url, llm_token=args.llm_token)
    since = str(registration["created_at"])
    cap = int(registration["cap_micros"])
    safety = float(registration["round_rule"]["safety"])
    probe = _read_json(probe_path(root, model))
    estimate = max(int(probe.get("cost_micros") or 0), 1)
    before = harness.spent(since)
    stopped: list[str] = []
    # 조건별 행은 턴마다 이 목록에 바로 쌓인다. 예외가 나도 과금된 턴이 기록에 남는다.
    started: dict[str, list[dict[str, Any]]] = {}

    async def spent() -> int:
        return await asyncio.to_thread(harness.spent, since)

    async def work(run_turn: Callable[..., Awaitable[dict[str, Any]]]) -> None:
        for condition in CONDITIONS:
            await run_condition_turns(
                questions=harness.questions,
                run_turn=lambda q, c=condition: run_turn(c, q),
                spent=spent,
                cap_micros=cap,
                estimate_micros=estimate,
                safety=safety,
                stopped=stopped,
                rows=started.setdefault(condition, []),
            )

    error: BaseException | None = None
    try:
        asyncio.run(harness.run(model, max_tokens, work))
    except BaseException as exc:  # noqa: BLE001 - 중간에 죽어도 부분 기록과 성적표 줄을 남긴다
        error = exc
        stopped.append(f"exception {type(exc).__name__}")
    finally:
        try:
            after = harness.spent(since)
        except Exception:  # noqa: BLE001 - 지출 조회 실패가 기록을 막으면 안 된다
            after = None
        conditions = condition_entries(started, harness.questions, stopped[0] if stopped else None)
        record = build_run_record(
            registration=registration,
            plan=plan,
            round_no=round_no,
            model=model,
            conditions=conditions,
            prompt_sha256=harness.prompt_sha,
            git_sha=ablation._git_sha(),
            stopped=stopped[0] if stopped else None,
            spent_delta_micros=None if after is None else after - before,
            runtime={k: runtime.get(k) for k in ("model", "model_settings", "execution_sha256")},
        )
        write_new(out, record)
        for condition in conditions:
            append_line(
                root / SCOREBOARD_NAME,
                scoreboard_line(
                    record=record,
                    condition=condition,
                    run_file=str(out.relative_to(root)),
                ),
            )
        print(f"model_evidence: 실행 기록 → {out} (stopped={record['stopped']})")
    if error is not None and not isinstance(error, SystemExit):
        raise error
    return 0 if not stopped else 2


def close_remaining(
    root: Path,
    registration: Mapping[str, Any],
    plan: Mapping[str, Any],
    questions: list[dict[str, Any]],
    reason: str | None,
) -> list[Path]:
    """시작하지 못한 계획 실행을 미실행 기록과 성적표 줄로 남긴다(스펙: remaining runs).

    이유를 주지 않으면 마지막으로 멈춘 실행의 이유를 쓴다. 그것도 없으면 아무것도 쓰지 않는다.
    """
    order = run_order(plan)
    existing = [run_path(root, r, m) for r, m in order if run_path(root, r, m).exists()]
    last = _read_json(existing[-1]) if existing else {}
    reason = reason or last.get("stopped")
    if not reason:
        raise SystemExit("model_evidence: 멈춘 실행이 없다. 닫을 이유를 --reason으로 준다")
    written: list[Path] = []
    for round_no, model in order:
        out = run_path(root, round_no, model)
        if out.exists():
            continue
        record = build_run_record(
            registration=registration,
            plan=plan,
            round_no=round_no,
            model=model,
            conditions=condition_entries({}, questions, f"not started: {reason}"),
            prompt_sha256=last.get("answer_prompt_sha256"),
            git_sha=ablation._git_sha(),
            stopped=f"not started: {reason}",
            spent_delta_micros=0,
            runtime={},
        )
        write_new(out, record)
        for condition in record["conditions"]:
            append_line(
                root / SCOREBOARD_NAME,
                scoreboard_line(
                    record=record, condition=condition, run_file=str(out.relative_to(root))
                ),
            )
        written.append(out)
    return written


def cmd_close(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    registration = load_registration(root)
    plan = _read_json(plan_path(root))
    state = _read_json(Path(registration["paths"]["state"]))
    sample = replay._load_sample(Path(registration["paths"]["sample"]))
    questions = ablation._questions_for(state, sample, 0)
    written = close_remaining(root, registration, plan, questions, args.reason)
    print(f"model_evidence: 시작하지 못한 실행 {len(written)}개를 미실행으로 기록했다")
    return 0


def cmd_import_reference(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    registration = load_registration(root)
    path = Path(args.answer).resolve()
    lines, _ = read_lines(root / SCOREBOARD_NAME)
    if any(x.get("reference") and x.get("run_file") == str(path) for x in lines):
        raise SystemExit("model_evidence: 이미 실은 참조 기록이다")
    answer = _read_json(path)
    conditions = reference_conditions(answer, registration)
    models = {str(r.get("model")) for c in conditions for r in c["rows"] if r.get("model")}
    record = {
        "model": next(iter(models)) if len(models) == 1 else "unknown",
        "git_sha": answer.get("git_sha"),
        "fixed_inputs_sha256": canonical_sha256(registration["fixed_inputs"]),
        "stopped": answer.get("stopped"),
    }
    for condition in conditions:
        append_line(
            root / SCOREBOARD_NAME,
            scoreboard_line(record=record, condition=condition, run_file=str(path), reference=True),
        )
    print(f"model_evidence: 참조 {record['model']} 두 줄을 실었다")
    return 0


def cmd_scoreboard(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    if args.html:
        out = Path(args.html)
        out.write_text(render_html(build_view(root)), encoding="utf-8")
        print(f"model_evidence: 성적표 → {out}")
        return 0
    host = assert_loopback_host(args.host)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - http.server 규약
            body = render_html(build_view(root)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_: Any) -> None:
            pass

    try:
        server = HTTPServer((host, args.port), Handler)
    except OSError as exc:
        raise SystemExit(
            f"model_evidence: {host}:{args.port}에서 들을 수 없다({exc.strerror}). --port로 바꾼다"
        ) from None
    print(f"model_evidence: 성적표 http://{host}:{args.port}")
    server.serve_forever()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    register = sub.add_parser("register", help="모델 · 회차 · 상한 · 규칙을 먼저 기록한다")
    register.add_argument("--dir", required=True)
    register.add_argument("--state", required=True)
    register.add_argument("--query-vectors", required=True)
    register.add_argument(
        "--reference-retrieval", required=True, help="고정 입력을 가져올 검색 기록"
    )
    register.add_argument("--sample", default=str(replay.DEFAULT_SAMPLE))
    register.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS))
    register.add_argument("--rounds-max", type=int, default=3)
    register.add_argument("--rounds-min", type=int, default=1)
    register.add_argument("--cap-micros", type=int, default=DEFAULT_CAP_MICROS)
    register.add_argument("--probe-question", default="q01")
    register.add_argument(
        "--probe-estimate-micros", type=int, default=DEFAULT_PROBE_ESTIMATE_MICROS
    )
    register.add_argument("--safety", type=float, default=DEFAULT_SAFETY)
    # 효과 기준은 예산 개시 기록이 있는 실험(wiki-advantage-eval)에서만 등록에 들어간다.
    register.add_argument(
        "--min-net-recovered", type=int, default=DEFAULT_EFFECT_CRITERION["min_net_recovered"]
    )
    register.add_argument("--min-models", type=int, default=DEFAULT_EFFECT_CRITERION["min_models"])
    register.set_defaults(func=cmd_register)

    budget_open = sub.add_parser("budget-open", help="수집 전에 총 상한과 시험지 해시를 고정한다")
    budget_open.add_argument("--dir", required=True)
    budget_open.add_argument("--sample", required=True)
    budget_open.add_argument("--compile-model", required=True)
    budget_open.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS))
    budget_open.add_argument("--cap-micros", type=int, default=DEFAULT_CAP_MICROS)
    budget_open.set_defaults(func=cmd_budget_open)

    ingest = sub.add_parser("ingest-record", help="수집 결과(잡 · 위키 · 지출)를 기록한다")
    ingest.add_argument("--dir", required=True)
    ingest.add_argument("--state", required=True)
    ingest.set_defaults(func=cmd_ingest_record)

    retry = sub.add_parser("retry-dead", help="수집 잡을 기다렸다가 dead 잡만 제품 API로 재시도")
    retry.add_argument("--dir", required=True)
    retry.add_argument("--state", required=True)
    retry.add_argument("--api-url", default="http://127.0.0.1:8031")
    retry.add_argument("--rounds", type=int, default=3)
    retry.add_argument("--timeout", type=float, default=1500)
    retry.set_defaults(func=cmd_retry_dead)

    for name, func, text in (
        ("probe", cmd_probe, "모델 하나를 한 문항으로 점검한다"),
        ("run", cmd_run, "한 회차 · 한 모델의 두 조건을 재생한다"),
    ):
        command = sub.add_parser(name, help=text)
        command.add_argument("--dir", required=True)
        command.add_argument("--model", required=True)
        command.add_argument("--worker-url", default="http://127.0.0.1:8081")
        command.add_argument("--llm-token", default=None)
        command.add_argument("--runtime-manifest", required=True)
        if name == "run":
            command.add_argument("--round", type=int, required=True)
        command.set_defaults(func=func)

    plan = sub.add_parser("plan", help="점검 비용만으로 회차를 정한다")
    plan.add_argument("--dir", required=True)
    plan.set_defaults(func=cmd_plan)

    order = sub.add_parser("order", help="남은 점검 또는 실행을 순서대로 한 줄씩 낸다")
    order.add_argument("--dir", required=True)
    order.add_argument("kind", choices=["probe", "runs"])
    order.set_defaults(func=cmd_order)

    close = sub.add_parser("close", help="시작하지 못한 계획 실행을 미실행으로 기록한다")
    close.add_argument("--dir", required=True)
    close.add_argument("--reason", default=None)
    close.set_defaults(func=cmd_close)

    reference = sub.add_parser("import-reference", help="#237 기록을 참조 줄로 싣는다")
    reference.add_argument("--dir", required=True)
    reference.add_argument("--answer", required=True)
    reference.set_defaults(func=cmd_import_reference)

    board = sub.add_parser("scoreboard", help="성적표 화면 (루프백) 또는 정적 HTML")
    board.add_argument("--dir", required=True)
    board.add_argument("--host", default="127.0.0.1")
    # 8800은 dart-workbench 성적표가 쓴다. 같은 머신에서 둘을 함께 띄울 수 있게 비켜 둔다.
    board.add_argument("--port", type=int, default=8801)
    board.add_argument("--html", default=None)
    board.set_defaults(func=cmd_scoreboard)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    import os

    if getattr(args, "llm_token", "unset") is None:
        args.llm_token = os.environ.get("LLM_STREAM_INTERNAL_TOKEN")
        if not args.llm_token:
            raise SystemExit("model_evidence: LLM_STREAM_INTERNAL_TOKEN이 필요하다")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
