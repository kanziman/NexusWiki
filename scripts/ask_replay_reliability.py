#!/usr/bin/env python3
"""같은 조건으로 여러 번 돌린 Ask 재생을 한 묶음으로 읽어 변동폭과 실패 원인을 보고한다.

계약: openspec/specs/ask-replay-reliability/
설계: openspec/changes/archive/2026-11-09-eval-reliability/design.md

쓰는 순서:
    # 1. 같은 수집 위에서 답변 재생을 회차만큼 돌린다. 총 지출 상한이 없으면 시작하지 않는다.
    uv run python scripts/ask_replay_reliability.py repeat --state state.json --runs 3 \\
        --label rel --out-dir runs/ --max-total-spend-micros 3000000

    # 2. 검색만 한 번 잰다(원인 판정의 검색 근거). 답변 모델을 부르지 않는다.
    uv run python scripts/ask_replay.py retrieval-eval --state state.json --label rel \\
        --out runs/retrieval.json

    # 3. 보고서를 만든다. 네트워크 · DB · 모델 호출이 없다.
    uv run python scripts/ask_replay_reliability.py report --repeat runs/repeat.json \\
        --ablation-answer answer.json --retrieval runs/retrieval.json --out reliability.json

⚠️ 회차는 같은 30문항의 반복이라 독립 표본이 아니다. 회차를 합친 신뢰 구간은 내지 않는다.
⚠️ 원인 판정의 검색 단계는 같은 수집 위의 별도 검색 호출로 정한다. 그 턴의 실제 컨텍스트가 아니다.
⚠️ 합성 문서로 잰 샘플 수치다. 운영 효과로 인용하지 않는다.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx

_SCRIPTS = Path(__file__).resolve().parent
DEFAULT_LABELS = _SCRIPTS / "fixtures" / "ask_replay_labels.v1.json"


def _load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"_reliability_{name}", _SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise SystemExit(f"ask_replay_reliability: 스크립트를 불러오지 못했다: {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# 판정 · 거절 수치 · 지문은 재생 스크립트의 것을 그대로 쓴다. 두 곳에 두면 판정이 어긋난다.
replay = _load_script("ask_replay")

SCHEMA = "ask-replay-reliability-v1"
REPEAT_SCHEMA = "ask-replay-repeat-v1"
ABLATION_EXPERIMENT = "retrieval-evidence-ablation"
# #232 기록에서 제품 기본 설정과 같은 조건은 이것 하나뿐이다. 진단 조건(원문만 · 위키만)은 이중
# 인용이 구조적으로 불가능하고, 제목 머리말 조건은 임베딩 입력이 제품과 다르다.
PRODUCT_CONDITION = "bothxbody"
UNKNOWN = replay.UNKNOWN

# 묶음 키. 하나라도 다르면 같은 조건의 반복이 아니다. 코드 revision은 기록만 하고 묶음을 막지
# 않는다(#232는 커밋되지 않은 작업 트리에서 돌았다).
SERIES_KEYS: tuple[str, ...] = (
    "snapshot_sha256",
    "fixture_sha256",
    "model",
    "policy_version",
    "requested_k",
    "answer_prompt_sha256",
)

CAUSES = frozenset({"question_ambiguity", "grader_error", "other"})
LABEL_FIELDS = frozenset({"id", "cause", "evidence", "known_failure", "note"})

# 자동 단계. 판정 순서는 설계 D8: 실행 장애 → 검색 미적중 → 작성.
EXECUTION_FAILURE = "execution_failure"
RETRIEVAL_MISS = "retrieval_miss"
COMPOSITION = "composition"
RETRIEVAL_UNAVAILABLE = "retrieval_evidence_unavailable"
STAGE_NAMES = {
    EXECUTION_FAILURE: "실행 장애",
    RETRIEVAL_MISS: "검색 미적중",
    COMPOSITION: "작성",
    RETRIEVAL_UNAVAILABLE: "검색 근거 없음",
    "question_ambiguity": "질문 모호성",
    "grader_error": "채점기 오류",
    "other": "기타",
}

LIMITATIONS = (
    "합성 샘플(가상 물류 문서 8건 · 고정 질문 30개)의 수치이며 운영 트래픽이 아니다.",
    "회차는 같은 질문의 반복이라 독립 표본이 아니다. 95% 구간은 회차마다 따로 낸다.",
    "변동폭은 같은 수집 위의 답변 변동만 뜻한다. 재수집에 따른 위키 컴파일 변동은 포함하지 않는다.",
    "검색 단계 판정은 같은 수집 위의 별도 검색 호출로 정했다. 그 턴의 실제 컨텍스트가 아니며, "
    "질의 임베딩을 새로 계산하므로 순위가 미세하게 다를 수 있다.",
    "검색은 맞았지만 컨텍스트 조립에서 빠진 경우는 판정할 수 없어 '작성'으로 묶인다.",
    "하네스 회차(#232)는 HTTP와 SSE를 거치지 않고 프로세스 안에서 답했다. 채널 장애는 행의 "
    "`failed_channels`로 읽으며, 그 필드를 남기기 전에 만든 #232 기록(2026-11-08)에는 턴별 채널 "
    "장애 정보가 없다. 같은 질의 벡터의 검색 6조건은 채널 장애 0건이었다.",
)


class ReliabilityError(SystemExit):
    """입력이 계약을 어겨 보고서를 만들 수 없다. 메시지에 이유를 적고 0이 아닌 코드로 끝난다."""

    def __init__(self, message: str) -> None:
        super().__init__(f"ask_replay_reliability: {message}")


# --- 회차 읽기 -----------------------------------------------------------------------------


def _single(values: Iterable[Any]) -> Any:
    found = {v for v in values if v not in (None, "", UNKNOWN)}
    return next(iter(found)) if len(found) == 1 else UNKNOWN


def http_run(result: dict[str, Any], source: str) -> dict[str, Any]:
    """`ask_replay ask` 결과 하나를 회차로 읽는다. 고정 입력이 없으면 값을 unknown으로 둔다."""
    fixed = result.get("fixed_inputs") or {}
    policies = fixed.get("policy_versions")
    key = {
        "snapshot_sha256": fixed.get("snapshot_sha256", UNKNOWN),
        "fixture_sha256": fixed.get("fixture_sha256", UNKNOWN),
        "model": fixed.get("model", UNKNOWN),
        # 회차 안에서 정책이 둘 이상이면 같은 조건이 아니다. 하나일 때만 그 값을 키로 쓴다.
        "policy_version": policies[0]
        if isinstance(policies, list) and len(policies) == 1
        else UNKNOWN,
        "requested_k": fixed.get("requested_k", UNKNOWN),
        "answer_prompt_sha256": fixed.get("answer_prompt_sha256", UNKNOWN),
    }
    return {
        "label": result.get("label") or source,
        "source": source,
        "path": result.get("execution_path") or "http",
        "revision": result.get("git_sha") or UNKNOWN,
        "planned": int(result.get("planned_questions") or len(result.get("rows") or [])),
        "planned_ids": result.get("planned_question_ids"),
        "stopped": result.get("stopped"),
        "rows": list(result.get("rows") or []),
        "key": key,
        "fingerprint_missing": not fixed,
    }


def ablation_run(
    record: dict[str, Any], source: str, condition: str = PRODUCT_CONDITION
) -> dict[str, Any]:
    """#232 답변 기록에서 제품 기본 조건만 하네스 회차로 읽는다. 다른 조건은 거부한다."""
    if record.get("experiment") != ABLATION_EXPERIMENT or record.get("phase") != "answer":
        raise ReliabilityError(
            f"{source}: #232 답변 기록이 아니다 "
            f"(experiment={record.get('experiment')}, phase={record.get('phase')})"
        )
    if condition != PRODUCT_CONDITION:
        raise ReliabilityError(
            f"{source}: 조건 {condition}은 제품 설정과 달라 회차로 쓸 수 없다. "
            f"{PRODUCT_CONDITION}만 받는다"
        )
    chosen = [
        c
        for c in record.get("conditions") or []
        if c.get("scope") == "both" and c.get("embedding_input") == "body"
    ]
    if len(chosen) != 1:
        raise ReliabilityError(f"{source}: {PRODUCT_CONDITION} 조건이 정확히 하나가 아니다")
    all_rows = chosen[0].get("rows") or []
    # 비용 상한으로 묻지 않은 행(`not_run`)은 회차 행에서 뺀다. 넣으면 실패와 분모로 센다.
    rows = [
        {k: v for k, v in row.items() if k not in {"verdict", "condition"}}
        for row in all_rows
        if row.get("status") != "not_run"
    ]
    fixed = record.get("fixed_inputs") or {}
    return {
        "label": f"{record.get('label') or 'ablation'}:{PRODUCT_CONDITION}",
        "source": source,
        "path": "harness",
        "revision": record.get("git_sha") or UNKNOWN,
        "planned": len(all_rows),
        "planned_ids": [str(row["id"]) for row in all_rows],
        "stopped": record.get("stopped"),
        "rows": rows,
        "key": {
            "snapshot_sha256": fixed.get("snapshot_sha256", UNKNOWN),
            "fixture_sha256": fixed.get("fixture_sha256", UNKNOWN),
            "model": _single(row.get("model") for row in rows),
            "policy_version": fixed.get("policy_version", UNKNOWN),
            "requested_k": fixed.get("requested_k", UNKNOWN),
            "answer_prompt_sha256": record.get("answer_prompt_sha256") or UNKNOWN,
        },
        "fingerprint_missing": not fixed,
    }


def check_series(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """묶음 키가 모두 같으면 그 키를 돌려준다. 빠지거나 다른 값은 이름을 보이고 거부한다."""
    if not runs:
        raise ReliabilityError("회차가 하나도 없다")
    problems: list[str] = []
    for run in runs:
        if run["fingerprint_missing"]:
            problems.append(f"{run['label']}: 고정 입력 지문이 없다(이 변경 전의 결과 파일)")
            continue
        missing = [k for k in SERIES_KEYS if run["key"].get(k) in (None, "", UNKNOWN)]
        if missing:
            problems.append(f"{run['label']}: 값을 모르는 고정 입력 {', '.join(missing)}")
    if problems:
        raise ReliabilityError("묶음을 만들 수 없다\n  " + "\n  ".join(problems))
    differing = [k for k in SERIES_KEYS if len({str(r["key"][k]) for r in runs}) > 1]
    if differing:
        detail = "; ".join(
            f"{k}: " + ", ".join(f"{r['label']}={r['key'][k]}" for r in runs) for k in differing
        )
        raise ReliabilityError(f"고정 입력이 다른 회차는 묶지 않는다 — {detail}")
    return dict(runs[0]["key"])


# --- 안정성 · 변동폭 -----------------------------------------------------------------------


def wilson_interval(passed: int, asked: int, z: float = 1.959964) -> tuple[float, float] | None:
    """Wilson 95% 구간. 평가 지도의 기존 표기(28/30 → 78.7~98.2%)와 같은 방식이다."""
    if asked <= 0:
        return None
    p = passed / asked
    denom = 1 + z * z / asked
    center = (p + z * z / (2 * asked)) / denom
    half = z * math.sqrt(p * (1 - p) / asked + z * z / (4 * asked * asked)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def question_order(runs: list[dict[str, Any]], fixture_ids: list[str] | None = None) -> list[str]:
    """보고할 문항 순서. 회차가 남긴 계획 문항 id를 먼저 쓰고, 그다음 회차 행의 문항을 보탠다.

    ⚠️ 모든 회차가 상한으로 일찍 멈추면 뒤쪽 문항은 어느 회차 행에도 없다. 행에서만 모으면 그
       문항들이 미실행으로도 나오지 않고 보고서에서 사라진다. 계획 id가 없는 옛 결과에서만 fixture
       순서로 계획 문항 수까지 채운다. 이때 일부 문서만 수집한 계획은 fixture 앞부분과 다를 수 있다.
    """
    seen: list[str] = []
    for run in runs:
        for qid in [*(run.get("planned_ids") or []), *(str(r["id"]) for r in run["rows"])]:
            if qid not in seen:
                seen.append(qid)
    legacy = [run for run in runs if not run.get("planned_ids")]
    planned = max((int(run["planned"]) for run in legacy), default=0)
    for qid in fixture_ids or []:
        if len(seen) >= planned:
            break
        if qid not in seen:
            seen.append(qid)
    return seen


def stability(outcomes: list[str]) -> str:
    asked = [o for o in outcomes if o != "not_run"]
    if not asked:
        return "not_run"
    if all(o == "pass" for o in asked):
        return "stable_pass"
    if all(o == "fail" for o in asked):
        return "stable_fail"
    return "unstable"


def run_summary(run: dict[str, Any]) -> dict[str, Any]:
    split = replay.refusal_split(run["rows"])
    interval = wilson_interval(split["answerable_passed"], split["answerable_asked"])
    return {
        "label": run["label"],
        "path": run["path"],
        "revision": run["revision"],
        "planned": run["planned"],
        "asked": len(run["rows"]),
        "stopped": run["stopped"],
        "cost_micros": sum(int(r.get("cost_micros") or 0) for r in run["rows"]),
        **split,
        "answerable_pass_rate": (
            split["answerable_passed"] / split["answerable_asked"]
            if split["answerable_asked"]
            else None
        ),
        "answerable_interval_95": list(interval) if interval else None,
    }


def spread(summaries: list[dict[str, Any]]) -> dict[str, Any] | None:
    rates = [s["answerable_pass_rate"] for s in summaries if s["answerable_pass_rate"] is not None]
    if not rates:
        return None
    return {
        "runs": len(summaries),
        "paths": sorted({s["path"] for s in summaries}),
        "answerable_passed": [s["answerable_passed"] for s in summaries],
        "min_rate": min(rates),
        "max_rate": max(rates),
        "mean_rate": sum(rates) / len(rates),
    }


# --- 원인 판정 · 라벨 ----------------------------------------------------------------------


def load_labels(path: Path, sample: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """사람 원인 라벨을 읽는다. 하나라도 계약을 어기면 파일 전체를 거부한다."""
    data = json.loads(path.read_text(encoding="utf-8"))
    known_ids = {str(q["id"]) for q in sample["questions"]}
    labels: dict[str, dict[str, Any]] = {}
    problems: list[str] = []
    for index, entry in enumerate(data.get("labels") or []):
        where = f"labels[{index}]"
        qid = str(entry.get("id") or "")
        extra = sorted(set(entry) - LABEL_FIELDS)
        if extra:
            # 답변 본문 같은 필드가 끼어드는 것을 막는다. 라벨은 원인과 근거만 담는다.
            problems.append(f"{where}: 허용하지 않는 필드 {', '.join(extra)}")
        if qid not in known_ids:
            problems.append(f"{where}: fixture에 없는 문항 id {qid or '(빈 값)'}")
        if entry.get("cause") not in CAUSES:
            problems.append(f"{where}: 원인 {entry.get('cause')!r}은 {sorted(CAUSES)} 밖이다")
        if not str(entry.get("evidence") or "").strip():
            problems.append(f"{where}: 근거 참조가 비었다")
        if not isinstance(entry.get("known_failure"), bool):
            problems.append(f"{where}: known_failure는 true/false여야 한다")
        if qid in labels:
            problems.append(f"{where}: 문항 {qid}의 라벨이 둘 이상이다")
        labels[qid] = entry
    if problems:
        raise ReliabilityError(f"라벨 파일 {path}을 거부한다\n  " + "\n  ".join(problems))
    return labels


def retrieval_evidence(record: dict[str, Any], source: str) -> dict[str, Any]:
    """검색 기록을 문항별 정답 근거 적중으로 줄인다. `retrieval-eval`과 #232 검색 기록을 받는다.

    측정이 정상(`ok`)이 아닌 문항은 적중 여부를 모르는 것으로 둔다(None). 장애를 미적중으로 세면
    원인이 검색 탓으로 잘못 몰린다.
    """
    if record.get("experiment") == ABLATION_EXPERIMENT:
        if record.get("phase") != "retrieval":
            raise ReliabilityError(f"{source}: #232 검색 기록이 아니다")
        conditions = [
            c for c in record.get("conditions") or [] if c.get("condition") == PRODUCT_CONDITION
        ]
        if len(conditions) != 1:
            raise ReliabilityError(f"{source}: {PRODUCT_CONDITION} 검색 조건이 없다")
        rows = conditions[0].get("rows") or []
        kind = "ablation"
    else:
        rows = record.get("rows") or []
        kind = "retrieval-eval"
    found: dict[str, bool | None] = {}
    for row in rows:
        if row.get("doc") == "none":
            continue
        result = row.get("result") or {}
        found[str(row["id"])] = (
            result.get("first_relevant_rank") is not None if row.get("status") == "ok" else None
        )
    return {
        "source": source,
        "kind": kind,
        "snapshot_sha256": (record.get("fixed_inputs") or {}).get("snapshot_sha256", UNKNOWN),
        "found": found,
    }


def pick_evidence(
    records: list[dict[str, Any]], snapshot: str
) -> tuple[dict[str, bool | None] | None, list[dict[str, Any]], list[str]]:
    """지문이 같은 검색 기록만 쓴다. `retrieval-eval` 기록이 #232 기록보다 앞선다."""
    usage: list[dict[str, Any]] = []
    usable: list[dict[str, Any]] = []
    for record in records:
        same = record["snapshot_sha256"] == snapshot and snapshot != UNKNOWN
        usage.append(
            {
                "source": record["source"],
                "kind": record["kind"],
                "used": same,
                "reason": None if same else "수집 스냅샷 지문이 묶음과 다르다",
            }
        )
        if same:
            usable.append(record)
    if not usable:
        return None, usage, []
    usable.sort(key=lambda r: 0 if r["kind"] == "retrieval-eval" else 1)
    primary = usable[0]["found"]
    notes = []
    for other in usable[1:]:
        for qid, hit in other["found"].items():
            if (
                qid in primary
                and hit is not None
                and primary[qid] is not None
                and hit != primary[qid]
            ):
                notes.append(
                    f"{qid}: 검색 기록마다 정답 근거 적중이 다르다 "
                    f"({usable[0]['source']}={primary[qid]}, {other['source']}={hit})"
                )
    return primary, usage, notes


def automatic_stage(row: dict[str, Any], evidence: dict[str, bool | None] | None) -> str:
    """실패한 문항의 처음 틀어진 단계. 고정 순서: 실행 장애 → 검색 미적중 → 작성.

    `no-evidence`와 `fallback`은 장애가 아니라 다음 판정으로 넘긴다. 답할 수 없는 문항이 거절하지
    않은 실패는 찾을 정답 문서가 없으므로 바로 작성이다.
    """
    status = str(row.get("status"))
    # HTTP 재생은 `missing_channels`, #232 답변 기록은 같은 정보를 `failed_channels`로 남긴다.
    failed = row.get("missing_channels") or row.get("failed_channels")
    if status.startswith("http_") or status in {"error", "unknown"} or failed:
        return EXECUTION_FAILURE
    if not replay.is_answerable(row):
        return COMPOSITION
    hit = None if evidence is None else evidence.get(str(row["id"]))
    if hit is None:
        return RETRIEVAL_UNAVAILABLE
    return COMPOSITION if hit else RETRIEVAL_MISS


# --- 보고서 -------------------------------------------------------------------------------


def build_report(
    runs: list[dict[str, Any]],
    *,
    labels: dict[str, dict[str, Any]],
    retrieval_records: list[dict[str, Any]],
    not_run: list[dict[str, Any]] | None = None,
    fixture_ids: list[str] | None = None,
) -> dict[str, Any]:
    key = check_series(runs)
    evidence, retrieval_usage, notes = pick_evidence(retrieval_records, key["snapshot_sha256"])
    if not retrieval_records:
        notes.append("검색 기록을 받지 않아 실행 장애가 아닌 실패는 '검색 근거 없음'으로 둔다")
    elif evidence is None:
        notes.append(
            "지문이 같은 검색 기록이 없어 실행 장애가 아닌 실패는 '검색 근거 없음'으로 둔다"
        )
    order = question_order(runs, fixture_ids)
    by_run = [{str(r["id"]): r for r in run["rows"]} for run in runs]
    summaries = [run_summary(run) for run in runs]
    questions: list[dict[str, Any]] = []
    stage_counts: list[dict[str, int]] = [{} for _ in runs]
    known_failures: list[list[str]] = [[] for _ in runs]
    unexpected: list[list[str]] = [[] for _ in runs]
    known_passed: list[list[str]] = [[] for _ in runs]
    for qid in order:
        label = labels.get(qid)
        known = bool(label and label.get("known_failure"))
        outcomes: list[str] = []
        auto: list[str | None] = []
        reported: list[str | None] = []
        for index, rows in enumerate(by_run):
            row = rows.get(qid)
            if row is None:
                # 일찍 멈춘 회차에서 묻지 않은 문항은 실패가 아니다.
                outcomes.append("not_run")
                auto.append(None)
                reported.append(None)
                continue
            passed = replay.verdict(row)["pass"]
            outcomes.append("pass" if passed else "fail")
            if passed:
                auto.append(None)
                reported.append(None)
                if known:
                    known_passed[index].append(qid)
                continue
            stage = automatic_stage(row, evidence)
            final = label["cause"] if label else stage
            auto.append(stage)
            reported.append(final)
            stage_counts[index][final] = stage_counts[index].get(final, 0) + 1
            (known_failures if known else unexpected)[index].append(qid)
        asked = [o for o in outcomes if o != "not_run"]
        questions.append(
            {
                "id": qid,
                "outcomes": outcomes,
                "passed": sum(1 for o in asked if o == "pass"),
                "asked": len(asked),
                "stability": stability(outcomes),
                "known_failure": known,
                "label_cause": label["cause"] if label else None,
                "label_evidence": label["evidence"] if label else None,
                "automatic_stages": auto,
                "reported_stages": reported,
            }
        )
    for index, summary in enumerate(summaries):
        summary["stage_counts"] = stage_counts[index]
        summary["known_failures"] = known_failures[index]
        summary["unexpected_failures"] = unexpected[index]
        summary["known_failures_passed"] = known_passed[index]
    http = [s for s in summaries if s["path"] == "http"]
    paths = {s["path"] for s in summaries}
    return {
        "schema": SCHEMA,
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "series_key": key,
        "runs": summaries,
        "not_run": not_run or [],
        "spread": {
            "all": spread(summaries),
            # 경로가 섞이면 HTTP만의 값을 항상 함께 낸다. 하네스 경로 차이가 변동에 섞일 수 있다.
            "http_only": spread(http) if len(paths) > 1 else None,
        },
        "questions": questions,
        # 묶음 전체: 실패 횟수(회차 합)와 실패한 서로 다른 문항을 함께 둔다.
        "series_failures": {
            "known_failure_count": sum(len(s["known_failures"]) for s in summaries),
            "unexpected_failure_count": sum(len(s["unexpected_failures"]) for s in summaries),
            "known_failure_questions": sorted({q for s in summaries for q in s["known_failures"]}),
            "unexpected_failure_questions": sorted(
                {q for s in summaries for q in s["unexpected_failures"]}
            ),
            "known_failures_passed": sorted(
                {q for s in summaries for q in s["known_failures_passed"]}
            ),
        },
        "stability_counts": {
            name: sum(1 for q in questions if q["stability"] == name)
            for name in ("stable_pass", "stable_fail", "unstable", "not_run")
        },
        "retrieval_records": retrieval_usage,
        "notes": notes,
        "limitations": list(LIMITATIONS),
    }


def _pct(rate: float | None) -> str:
    return "-" if rate is None else f"{rate * 100:.1f}%"


def _frac(a: Any, b: Any) -> str:
    return "-" if a is None or b is None else f"{a}/{b}"


def render_markdown(report: dict[str, Any]) -> str:
    key = report["series_key"]
    lines = [
        "합성 샘플 반복 측정이며 운영 트래픽 수치가 아니다. 회차는 독립 표본이 아니다.",
        "",
        f"묶음 키: 스냅샷 `{key['snapshot_sha256'][:16]}…` · 모델 `{key['model']}` · "
        f"정책 `{key['policy_version']}` · k={key['requested_k']}",
        "",
        "| 회차 | 경로 | revision | 답할 수 있는 문항 통과 | 95% 구간 | 정확한 거절 | "
        "잘못된 거절 | 알려진 실패 | 예상 밖 실패 | 비용 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for run in report["runs"]:
        interval = run["answerable_interval_95"]
        band = "-" if not interval else f"{interval[0] * 100:.1f}~{interval[1] * 100:.1f}%"
        stopped = " (중단)" if run["stopped"] else ""
        lines.append(
            f"| {run['label']}{stopped} | {run['path']} | {str(run['revision'])[:12]} | "
            f"{_frac(run['answerable_passed'], run['answerable_asked'])} | {band} | "
            f"{_frac(run['refusal_correct'], run['refusal_asked'])} | "
            f"{_frac(run['false_refusals'], run['answerable_asked'])} | "
            f"{len(run['known_failures'])} | {len(run['unexpected_failures'])} | "
            f"${run['cost_micros'] / 1e6:.4f} |"
        )
    for item in report["not_run"]:
        lines.append(f"| {item['label']} (미실행) | - | - | - | - | - | - | - | - | - |")
    lines.append("")
    for name, title in (("all", "전체 회차"), ("http_only", "HTTP 회차만")):
        value = report["spread"].get(name)
        if value:
            lines.append(
                f"- 변동폭({title}, {value['runs']}회): 통과 {value['answerable_passed']} · "
                f"최소 {_pct(value['min_rate'])} · 최대 {_pct(value['max_rate'])} · "
                f"평균 {_pct(value['mean_rate'])}"
            )
    failures = report["series_failures"]
    lines.append(
        f"- 묶음 전체 실패: 알려진 실패 {failures['known_failure_count']}회 "
        f"({', '.join(failures['known_failure_questions']) or '-'}) · 예상 밖 실패 "
        f"{failures['unexpected_failure_count']}회 "
        f"({', '.join(failures['unexpected_failure_questions']) or '-'})"
    )
    counts = report["stability_counts"]
    lines.append(
        f"- 문항 안정성: 안정 통과 {counts['stable_pass']} · 안정 실패 {counts['stable_fail']} · "
        f"흔들림 {counts['unstable']} · 미실행 {counts['not_run']}"
    )
    lines += [
        "",
        "| 문항 | 통과 | 안정성 | 보고 단계 (자동) | 알려진 실패 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for q in report["questions"]:
        if q["stability"] == "stable_pass":
            continue
        stages = sorted({s for s in q["reported_stages"] if s})
        autos = sorted({s for s in q["automatic_stages"] if s})
        stage_text = ", ".join(STAGE_NAMES.get(s, s) for s in stages) or "-"
        if q["label_cause"]:
            stage_text += " (자동: " + ", ".join(STAGE_NAMES.get(s, s) for s in autos) + ")"
        lines.append(
            f"| {q['id']} | {q['passed']}/{q['asked']} | {q['stability']} | {stage_text} | "
            f"{'예' if q['known_failure'] else '아니오'} |"
        )
    passed_known = failures["known_failures_passed"]
    if passed_known:
        lines.append("")
        lines.append(f"- 통과한 알려진 실패: {', '.join(passed_known)} — 라벨을 다시 볼 것")
    for usage in report["retrieval_records"]:
        state = "사용" if usage["used"] else f"거부 ({usage['reason']})"
        lines.append(f"- 검색 근거 {usage['source']} ({usage['kind']}): {state}")
    for note in report["notes"]:
        lines.append(f"- 주의: {note}")
    lines += ["", "한계:"] + [f"- {text}" for text in report["limitations"]]
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def cmd_report(args: argparse.Namespace) -> int:
    out = Path(args.out)
    # ⚠️ 기록은 append-only다. 입력을 읽기 전에 거부해 기존 파일이 그대로 남게 한다.
    if out.exists():
        raise ReliabilityError(f"이미 있는 기록은 덮어쓰지 않는다: {out}")
    runs: list[dict[str, Any]] = []
    not_run: list[dict[str, Any]] = []
    for manifest_path in args.repeat or []:
        manifest = _read_json(Path(manifest_path))
        if manifest.get("schema") != REPEAT_SCHEMA:
            raise ReliabilityError(f"{manifest_path}: 반복 재생 기록이 아니다")
        base = Path(manifest_path).parent
        for item in manifest.get("runs") or []:
            if item.get("result_file"):
                runs.append(http_run(_read_json(base / item["result_file"]), item["result_file"]))
            else:
                not_run.append({"label": item.get("label"), "reason": item.get("reason")})
    for result_path in args.result or []:
        runs.append(http_run(_read_json(Path(result_path)), Path(result_path).name))
    if args.ablation_answer:
        path = Path(args.ablation_answer)
        runs.append(ablation_run(_read_json(path), path.name, args.ablation_condition))
    sample = replay._load_sample(Path(args.sample))
    labels = load_labels(Path(args.labels), sample) if args.labels else {}
    retrieval_records = [
        retrieval_evidence(_read_json(Path(p)), Path(p).name) for p in args.retrieval or []
    ]
    report = build_report(
        runs,
        labels=labels,
        retrieval_records=retrieval_records,
        not_run=not_run,
        fixture_ids=[str(q["id"]) for q in sample["questions"]],
    )
    # "x" 모드: 실행 중에 같은 경로가 생겼어도 덮어쓰지 않는다.
    with out.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2))
    print(render_markdown(report))
    return 0


# --- 반복 재생 (유료) ----------------------------------------------------------------------


def cmd_repeat(args: argparse.Namespace) -> int:
    api = replay.assert_loopback(args.api_url)
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    stack = replay.assert_loopback(state["stack_url"])
    if args.max_total_spend_micros <= 0:
        raise ReliabilityError("총 지출 상한은 0보다 커야 한다")
    if args.runs < 1:
        raise ReliabilityError("회차는 1 이상이어야 한다")
    out_dir = Path(args.out_dir)
    manifest_path = out_dir / "repeat.json"
    result_names = [f"{args.label}-{n}.json" for n in range(1, args.runs + 1)]
    existing = [p for p in [manifest_path, *(out_dir / n for n in result_names)] if p.exists()]
    if existing:
        raise ReliabilityError(f"이미 있는 기록은 덮어쓰지 않는다: {', '.join(map(str, existing))}")
    out_dir.mkdir(parents=True, exist_ok=True)
    sample = replay._load_sample(Path(args.sample))
    questions = replay.select_questions(sample, state, args.limit)
    cap = args.max_total_spend_micros
    spent_total = 0
    largest_turn = 0
    items: list[dict[str, Any]] = []
    stopped_reason: str | None = None

    def before(spent_in_run: int, last: dict[str, Any] | None) -> str | None:
        nonlocal largest_turn
        if last is not None:
            largest_turn = max(largest_turn, int(last.get("cost_micros") or 0))
        # ⚠️ 넘은 뒤가 아니라 시작하기 전에 멈춘다. 다음 턴의 비용은 모르므로 지금까지 본 최대
        #    턴 비용과 추정치 중 큰 값으로 가늠한다.
        estimate = max(args.turn_estimate_micros, largest_turn)
        if spent_total + spent_in_run + estimate > cap:
            print(
                f"ask_replay_reliability: 다음 턴이 총 상한 {cap} micros를 넘을 수 있어 멈춘다 "
                f"(누적 {spent_total + spent_in_run}, 추정 {estimate})"
            )
            return "spend_cap"
        return None

    for number, name in enumerate(result_names, start=1):
        label = f"{args.label}-{number}"
        if stopped_reason:
            items.append(
                {"label": label, "result_file": None, "status": "not_run", "reason": stopped_reason}
            )
            continue
        with httpx.Client(timeout=180) as client:
            token = replay._login(client, stack, state)
            sha = replay._api_sha(client, api)
            fixed = replay.collect_fixed_inputs(client, stack, state["workspace_id"], token, sample)
            rows, stopped = replay.run_replay(
                client, api, stack, state["workspace_id"], token, questions, before_question=before
            )
        cost = sum(int(r.get("cost_micros") or 0) for r in rows)
        spent_total += cost
        if rows:
            largest_turn = max([largest_turn, *(int(r.get("cost_micros") or 0) for r in rows)])
        if not rows and stopped:
            # 한 문항도 묻지 못한 회차는 결과 파일 없이 미실행으로 남긴다.
            stopped_reason = stopped
            items.append(
                {"label": label, "result_file": None, "status": "not_run", "reason": stopped}
            )
            continue
        result = replay.build_result(
            label=label, sha=sha, questions=questions, rows=rows, fixed=fixed, stopped=stopped
        )
        replay.write_result(result, out_dir / name, args.scorecard)
        items.append(
            {
                "label": label,
                "result_file": name,
                "status": "partial" if stopped else "complete",
                "reason": stopped,
                "cost_micros": cost,
            }
        )
        if stopped:
            stopped_reason = stopped
    manifest = {
        "schema": REPEAT_SCHEMA,
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "planned_runs": args.runs,
        "planned_questions": len(questions),
        "cap_micros": cap,
        "turn_estimate_micros": args.turn_estimate_micros,
        "spent_micros": spent_total,
        "runs": items,
    }
    with manifest_path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(
        f"ask_replay_reliability: {len(items)}회차 기록 → {manifest_path} "
        f"(지출 {spent_total} micros)"
    )
    return 0 if all(item["status"] == "complete" for item in items) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ask 재생 반복 측정과 실패 원인 보고")
    sub = parser.add_subparsers(dest="command", required=True)

    repeat = sub.add_parser("repeat", help="같은 조건으로 답변 재생을 여러 회 돌린다(유료)")
    repeat.add_argument("--state", required=True)
    repeat.add_argument("--label", required=True)
    repeat.add_argument("--runs", type=int, required=True)
    repeat.add_argument("--out-dir", required=True)
    # 기본값을 두지 않는다. 상한 없이 유료 재생을 여러 회 돌리는 사고를 막는다.
    repeat.add_argument("--max-total-spend-micros", type=int, required=True)
    # 2026-11-08 실측 문항당 약 27,000 micros에 여유를 둔 값이다.
    repeat.add_argument("--turn-estimate-micros", type=int, default=30_000)
    repeat.add_argument("--api-url", default="http://127.0.0.1:8031")
    repeat.add_argument("--sample", default=str(replay.DEFAULT_SAMPLE))
    repeat.add_argument("--limit", type=int, default=0)
    repeat.add_argument("--scorecard", help="성적표 파일. 기본은 결과 옆 scorecard.jsonl")
    repeat.set_defaults(func=cmd_repeat)

    report = sub.add_parser("report", help="반복 묶음 보고서를 만든다(네트워크 불필요)")
    report.add_argument("--out", required=True)
    report.add_argument("--repeat", action="append", help="repeat가 남긴 repeat.json")
    report.add_argument("--result", action="append", help="ask 결과 파일(여러 번 가능)")
    report.add_argument(
        "--ablation-answer", help="#232 답변 기록. 제품 조건만 하네스 회차로 읽는다"
    )
    report.add_argument("--ablation-condition", default=PRODUCT_CONDITION)
    report.add_argument(
        "--retrieval", action="append", help="검색 기록(retrieval-eval 또는 #232 retrieve.json)"
    )
    report.add_argument("--labels", default=str(DEFAULT_LABELS))
    report.add_argument("--sample", default=str(replay.DEFAULT_SAMPLE))
    report.set_defaults(func=cmd_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
