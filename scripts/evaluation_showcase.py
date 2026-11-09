#!/usr/bin/env python3
"""보존된 반복 측정 기록에서 공개 평가 쇼케이스용 허용 필드 JSON을 만들고 검사한다.

계약: openspec/specs/evaluation-showcase/
설계: openspec/changes/archive/2026-11-09-evaluation-showcase/design.md (D1 · D2 · D3)

쓰는 순서:
    # 1. 보존된 report에서 공개 기록을 만든다. 네트워크 · DB · 모델 호출이 없다.
    uv run python scripts/evaluation_showcase.py export \\
        --report .worktrees/reliability-evidence-20261109/reliability-report.json \\
        --out apps/dashboard/content/evaluation.json

    # 2. 커밋된 공개 기록을 검사한다. CI의 pytest도 같은 검사를 돌린다.
    uv run python scripts/evaluation_showcase.py check apps/dashboard/content/evaluation.json

⚠️ 공개 기록은 허용 목록으로 닫는다. report에 새 필드가 생겨도 여기서 고른 필드만 나간다.
   금지 목록 방식으로 바꾸면 새 필드가 기본 공개가 된다.
⚠️ 숫자는 손으로 옮기지 않는다. 구간과 변동폭은 check가 회차 수치에서 다시 계산해 대조한다.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
DEFAULT_FIXTURE = _SCRIPTS / "fixtures" / "ask_replay.v1.json"
DEFAULT_LABELS = _SCRIPTS / "fixtures" / "ask_replay_labels.v1.json"
DEFAULT_CURATED = _SCRIPTS / "fixtures" / "evaluation_showcase.curated.v1.json"


def _load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"_showcase_{name}", _SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise SystemExit(f"evaluation_showcase: 스크립트를 불러오지 못했다: {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# 구간 · 안정성 정의는 반복 측정 스크립트의 것을 그대로 쓴다. 두 곳에 두면 공개 숫자가 어긋난다.
reliability = _load_script("ask_replay_reliability")
fingerprint = _load_script("eval_fingerprint")

SCHEMA = "evaluation-showcase-v1"
REPORT_SCHEMA = reliability.SCHEMA
PATHS = frozenset({"http", "harness"})

# --- 허용 목록 (설계 D2) --------------------------------------------------------------------

TOP_KEYS = frozenset(
    {"schema", "generated_at", "provenance", "synthetic", "series", "map", "ledger", "limitations"}
)
PROVENANCE_KEYS = frozenset({"report_sha256", "fixture_sha256", "labels_sha256", "curated_sha256"})
SYNTHETIC_KEYS = frozenset({"documents", "questions", "answerable", "unanswerable"})
SERIES_KEYS = frozenset(
    {"valid", "invalid_reason", "key", "runs", "questions", "spread", "stability_counts"}
)
KEY_KEYS = frozenset(
    {"snapshot_sha256", "fixture_sha256", "prompt_sha256", "model", "policy_version", "requested_k"}
)
RUN_KEYS = frozenset(
    {
        "label",
        "path",
        "planned",
        "asked",
        "answerable_passed",
        "answerable_asked",
        "interval_95",
        "refusal_correct",
        "refusal_asked",
        "false_refusals",
        "cost_usd",
    }
)
SPREAD_KEYS = frozenset({"all", "http_only"})
SPREAD_ITEM_KEYS = frozenset(
    {"runs", "paths", "answerable_passed", "min_rate", "max_rate", "mean_rate"}
)
STABILITY_NAMES = ("stable_pass", "stable_fail", "unstable", "not_run")
QUESTION_KEYS = frozenset(
    {
        "id",
        "query",
        "kind",
        "outcomes",
        "stability",
        "known_failure",
        "reported_stage",
        "automatic_stage",
        "note",
    }
)
MAP_KEYS = frozenset(
    {
        "surface",
        "status",
        "derived_from",
        "summary",
        "detail",
        "denominator",
        "measured_at",
        "source",
        "source_url",
        "reason",
    }
)
MAP_STATUSES = frozenset({"measured", "partial", "empty"})
# 반복 측정에서 값을 만드는 칸. 화면이 칸 이름으로 지표를 추측하지 않도록 지표를 이름으로 둔다.
DERIVED = frozenset({"series.answerable", "series.refusal"})
SUMMARY_MAX = 60
LEDGER_KEYS = frozenset({"date", "changed", "technique", "applied", "evidence", "evidence_url"})
CURATED_KEYS = frozenset({"version", "notice", "map", "ledger"})
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
OUTCOMES = frozenset({"pass", "fail", "not_run"})
KINDS = frozenset({"answerable", "refusal"})
# 실패한 회차들의 단계가 서로 다르면 하나를 고르지 않고 "회차마다 다름"으로 둔다.
MIXED_STAGE = "mixed"
STAGES = frozenset({*reliability.STAGE_NAMES, MIXED_STAGE})

# 허용 목록이 1차 방어다. 이 패턴은 누가 허용 목록에 식별자나 본문 필드를 잘못 더했을 때를 막는
# 보조 검사다. `answerable_*`처럼 정상 필드가 걸리지 않도록 본문 키는 이름 전체로만 잡는다.
FORBIDDEN_KEY = re.compile(
    r"(?:^|_)(?:workspace|user|generation|token|secret|password|email)(?:_|$)"
    r"|^(?:answer|answers|answer_text|answer_body|body|content|raw_text)$"
)


class ShowcaseError(SystemExit):
    """입력이나 공개 기록이 계약을 어겼다. 이유를 적고 0이 아닌 코드로 끝난다."""

    def __init__(self, message: str) -> None:
        super().__init__(f"evaluation_showcase: {message}")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ShowcaseError(f"{path}를 읽지 못했다: {exc}") from exc


# --- export ---------------------------------------------------------------------------------


def public_run_labels(runs: list[dict[str, Any]]) -> list[str]:
    """내부 실행 이름(`ablation-answer:bothxbody`)을 방문자용 이름으로 바꾼다."""
    labels: list[str] = []
    http = harness = 0
    for run in runs:
        if run.get("path") == "http":
            http += 1
            labels.append(f"HTTP {http}")
        else:
            harness += 1
            # #232 절제 실험 기록에서 온 회차다. 출처 번호를 이름에 남겨 원장과 이어지게 한다.
            if str(run.get("label", "")).startswith(f"{reliability.ABLATION_EXPERIMENT}"):
                labels.append("스크립트 재집계 #232")
            elif str(run.get("label", "")).startswith("ablation-answer"):
                labels.append("스크립트 재집계 #232")
            else:
                labels.append(f"스크립트 재집계 {harness}")
    return labels


def _public_run(run: dict[str, Any], label: str) -> dict[str, Any]:
    refusal_asked = int(run.get("refusal_asked") or 0)
    interval = run.get("answerable_interval_95")
    return {
        "label": label,
        "path": run["path"],
        "planned": int(run["planned"]),
        "asked": int(run["asked"]),
        "answerable_passed": int(run["answerable_passed"]),
        "answerable_asked": int(run["answerable_asked"]),
        "interval_95": list(interval) if interval else None,
        # 거절 문항이 없는 회차는 0이 아니라 없음(null)이다. 0으로 쓰면 "모두 틀림"으로 읽힌다.
        "refusal_correct": run.get("refusal_correct") if refusal_asked else None,
        "refusal_asked": refusal_asked,
        "false_refusals": int(run.get("false_refusals") or 0),
        "cost_usd": round(int(run.get("cost_micros") or 0) / 1_000_000, 6),
    }


def _public_spread(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if item is None:
        return None
    return {k: item[k] for k in sorted(SPREAD_ITEM_KEYS)}


def _one_stage(stages: list[Any]) -> str | None:
    found = list(dict.fromkeys(s for s in stages if s))
    if not found:
        return None
    return found[0] if len(found) == 1 else MIXED_STAGE


def _public_question(
    question: dict[str, Any], *, fixture: dict[str, Any], label: dict[str, Any] | None
) -> dict[str, Any]:
    return {
        "id": str(question["id"]),
        # 질문 문구는 커밋된 합성 fixture에서 가져온다. 답변 본문은 report에도 공개 기록에도 없다.
        "query": fixture["query"],
        "kind": "answerable" if fixture.get("answerable", True) else "refusal",
        "outcomes": list(question["outcomes"]),
        "stability": question["stability"],
        "known_failure": bool(question.get("known_failure")),
        "reported_stage": _one_stage(question.get("reported_stages") or []),
        "automatic_stage": _one_stage(question.get("automatic_stages") or []),
        "note": (label or {}).get("note"),
    }


def _invalid_reason(report: dict[str, Any]) -> str | None:
    if report.get("schema") != REPORT_SCHEMA:
        return f"반복 측정 기록 형식이 {REPORT_SCHEMA}가 아니다"
    key = report.get("series_key") or {}
    missing = [k for k in reliability.SERIES_KEYS if key.get(k) in (None, "", reliability.UNKNOWN)]
    if missing:
        return f"묶음 키 값이 없다: {', '.join(missing)}"
    if not report.get("runs"):
        return "회차가 하나도 없다"
    if not (report.get("spread") or {}).get("all"):
        return "답할 수 있는 문항을 실행한 회차가 없다"
    return None


def build_public(
    report: dict[str, Any],
    *,
    sample: dict[str, Any],
    labels: dict[str, dict[str, Any]],
    curated: dict[str, Any],
    provenance: dict[str, str],
) -> dict[str, Any]:
    questions = sample["questions"]
    answerable = sum(1 for q in questions if q.get("answerable", True))
    reason = _invalid_reason(report)
    key = report.get("series_key") or {}
    if reason is None and key.get("fixture_sha256") != fingerprint.fixture_sha256(sample):
        # 질문 문구를 다른 fixture에서 붙이면 격자의 질문과 실제로 잰 질문이 어긋난다.
        reason = "반복 측정의 fixture 지문이 현재 질문 fixture와 다르다"
    if reason is None:
        reported = [str(q.get("id")) for q in report.get("questions") or []]
        if sorted(reported) != sorted(str(q["id"]) for q in questions):
            reason = "반복 측정의 문항 결과가 질문 fixture의 문항과 다르다"
    limitations = list(report.get("limitations") or [])
    if report.get("not_run"):
        limitations.append(
            f"계획했지만 실행하지 않은 회차 {len(report['not_run'])}개는 결과에 넣지 않았다."
        )
    series: dict[str, Any]
    if reason is not None:
        series = {
            "valid": False,
            "invalid_reason": reason,
            "key": None,
            "runs": [],
            "questions": [],
            "spread": None,
            "stability_counts": None,
        }
    else:
        runs = report["runs"]
        by_id = {str(q["id"]): q for q in questions}
        series = {
            "valid": True,
            "invalid_reason": None,
            "key": {
                "snapshot_sha256": key["snapshot_sha256"],
                "fixture_sha256": key["fixture_sha256"],
                "prompt_sha256": key["answer_prompt_sha256"],
                "model": key["model"],
                "policy_version": key["policy_version"],
                "requested_k": key["requested_k"],
            },
            "runs": [
                _public_run(run, name)
                for run, name in zip(runs, public_run_labels(runs), strict=True)
            ],
            "questions": [
                _public_question(q, fixture=by_id[str(q["id"])], label=labels.get(str(q["id"])))
                for q in report["questions"]
            ],
            "spread": {
                "all": _public_spread(report["spread"].get("all")),
                "http_only": _public_spread(report["spread"].get("http_only")),
            },
            "stability_counts": {
                name: int(report["stability_counts"].get(name, 0)) for name in STABILITY_NAMES
            },
        }
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provenance": provenance,
        "synthetic": {
            "documents": len(sample["documents"]),
            "questions": len(questions),
            "answerable": answerable,
            "unanswerable": len(questions) - answerable,
        },
        "series": series,
        # 지도 · 원장은 curated 파일 하나가 원본이다. 손대지 않고 그대로 옮긴다(설계 D4).
        "map": copy.deepcopy(curated.get("map")),
        "ledger": copy.deepcopy(curated.get("ledger")),
        "limitations": limitations,
    }


# --- check (설계 D3) ------------------------------------------------------------------------


def _check_keys(where: str, value: Any, allowed: frozenset[str], problems: list[str]) -> bool:
    if not isinstance(value, dict):
        problems.append(f"{where}: 객체가 아니다")
        return False
    extra = sorted(set(value) - allowed)
    missing = sorted(allowed - set(value))
    if extra:
        problems.append(f"{where}: 허용 목록 밖 키 {', '.join(extra)}")
    if missing:
        problems.append(f"{where}: 빠진 키 {', '.join(missing)}")
    return not extra and not missing


def _forbidden_keys(value: Any, where: str, problems: list[str]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            if FORBIDDEN_KEY.search(str(k)):
                problems.append(f"{where}.{k}: 공개할 수 없는 필드 이름")
            _forbidden_keys(v, f"{where}.{k}", problems)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _forbidden_keys(v, f"{where}[{i}]", problems)


def _close(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(a, b, rel_tol=0, abs_tol=1e-9)


def _expected_spread(runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    rates = [r["answerable_passed"] / r["answerable_asked"] for r in runs if r["answerable_asked"]]
    if not rates:
        return None
    return {
        "runs": len(runs),
        "paths": sorted({r["path"] for r in runs}),
        "answerable_passed": [r["answerable_passed"] for r in runs],
        "min_rate": min(rates),
        "max_rate": max(rates),
        "mean_rate": sum(rates) / len(rates),
    }


def _same_spread(actual: Any, expected: dict[str, Any] | None) -> bool:
    if expected is None or actual is None:
        return actual is None and expected is None
    if not isinstance(actual, dict) or set(actual) != SPREAD_ITEM_KEYS:
        return False
    return (
        actual["runs"] == expected["runs"]
        and actual["paths"] == expected["paths"]
        and actual["answerable_passed"] == expected["answerable_passed"]
        and all(_close(actual[k], expected[k]) for k in ("min_rate", "max_rate", "mean_rate"))
    )


def _check_run(index: int, run: Any, problems: list[str]) -> bool:
    where = f"series.runs[{index}]"
    if not _check_keys(where, run, RUN_KEYS, problems):
        return False
    ok = True
    if run["path"] not in PATHS:
        problems.append(f"{where}.path: http 또는 harness가 아니다")
        ok = False
    if not 0 <= run["asked"] <= run["planned"]:
        problems.append(f"{where}: 실행 수가 계획 수를 넘거나 음수다")
        ok = False
    if not 0 <= run["answerable_passed"] <= run["answerable_asked"]:
        problems.append(f"{where}: 통과 수가 답할 수 있는 문항 수를 넘는다")
        ok = False
    if not 0 <= run["false_refusals"] <= run["answerable_asked"]:
        problems.append(f"{where}: 잘못된 거절 수가 답할 수 있는 문항 수를 넘는다")
        ok = False
    if run["refusal_asked"] == 0:
        if run["refusal_correct"] is not None:
            problems.append(f"{where}: 거절 문항이 없는데 정확한 거절 값이 있다(없음이어야 한다)")
            ok = False
    elif not (
        isinstance(run["refusal_correct"], int)
        and 0 <= run["refusal_correct"] <= run["refusal_asked"]
    ):
        problems.append(f"{where}: 정확한 거절 수가 거절 문항 수와 맞지 않는다")
        ok = False
    if not ok:
        # 통과 수가 분모를 넘으면 구간 공식이 음수 제곱근에서 예외를 던진다. 이미 실패로 보고했다.
        return False
    expected = reliability.wilson_interval(run["answerable_passed"], run["answerable_asked"])
    actual = run["interval_95"]
    if expected is None:
        if actual is not None:
            problems.append(f"{where}.interval_95: 답할 수 있는 문항이 없는데 구간이 있다")
            ok = False
    elif not (
        isinstance(actual, list)
        and len(actual) == 2
        and all(_close(a, e) for a, e in zip(actual, expected, strict=True))
    ):
        problems.append(f"{where}.interval_95: 통과 수에서 다시 계산한 Wilson 구간과 다르다")
        ok = False
    return ok


def check_public(record: Any) -> list[str]:
    """공개 기록의 문제를 모두 모아 돌려준다. 빈 목록이면 공개할 수 있다."""
    problems: list[str] = []
    _forbidden_keys(record, "$", problems)
    if not _check_keys("$", record, TOP_KEYS, problems):
        return problems
    if record["schema"] != SCHEMA:
        problems.append(f"schema: {SCHEMA}가 아니다")
    _check_keys("provenance", record["provenance"], PROVENANCE_KEYS, problems)
    synthetic = record["synthetic"]
    if _check_keys("synthetic", synthetic, SYNTHETIC_KEYS, problems) and (
        synthetic["answerable"] + synthetic["unanswerable"] != synthetic["questions"]
    ):
        problems.append("synthetic: 답할 수 있는 문항과 거절 문항의 합이 문항 수와 다르다")
    limitations = record["limitations"]
    if (
        not isinstance(limitations, list)
        or not limitations
        or not all(isinstance(x, str) and x.strip() for x in limitations)
    ):
        problems.append("limitations: 비어 있지 않은 문자열 목록이어야 한다")
    _check_map(record["map"], problems)
    _check_ledger(record["ledger"], problems)
    series = record["series"]
    if not _check_keys("series", series, SERIES_KEYS, problems):
        return problems
    if not series["valid"]:
        if not (isinstance(series["invalid_reason"], str) and series["invalid_reason"].strip()):
            problems.append("series: 무효인데 이유가 없다")
        if series["runs"] or series["questions"] or series["spread"] or series["stability_counts"]:
            problems.append("series: 무효 묶음에 수치가 남아 있다")
        return problems
    if series["invalid_reason"] is not None:
        problems.append("series: 유효한 묶음에 무효 이유가 있다")
    _check_keys("series.key", series["key"], KEY_KEYS, problems)
    runs = series["runs"]
    if not isinstance(runs, list) or not runs:
        problems.append("series.runs: 유효한 묶음에 회차가 없다")
        return problems
    if not all([_check_run(i, run, problems) for i, run in enumerate(runs)]):
        return problems
    spread = series["spread"]
    if _check_keys("series.spread", spread, SPREAD_KEYS, problems):
        if not _same_spread(spread["all"], _expected_spread(runs)):
            problems.append("series.spread.all: 회차 수치에서 다시 계산한 값과 다르다")
        http = [r for r in runs if r["path"] == "http"]
        mixed = len({r["path"] for r in runs}) > 1
        # 경로가 섞인 묶음만 HTTP 회차만의 값을 따로 낸다(반복 측정 스크립트와 같은 규칙).
        expected_http = _expected_spread(http) if mixed else None
        if not _same_spread(spread["http_only"], expected_http):
            problems.append("series.spread.http_only: HTTP 회차만으로 다시 계산한 값과 다르다")
    questions = series["questions"]
    if not _check_questions(questions, runs, synthetic, problems):
        return problems
    counts = series["stability_counts"]
    if _check_keys("series.stability_counts", counts, frozenset(STABILITY_NAMES), problems):
        expected = {n: sum(1 for q in questions if q["stability"] == n) for n in STABILITY_NAMES}
        if counts != expected:
            problems.append("series.stability_counts: 문항 안정성에서 다시 센 값과 다르다")
    return problems


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _url(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.startswith("https://"))


def _check_map(entries: Any, problems: list[str]) -> None:
    if not isinstance(entries, list) or not entries:
        problems.append("map: 측정면이 하나도 없다")
        return
    seen: set[str] = set()
    for index, e in enumerate(entries):
        where = f"map[{index}]"
        if not _check_keys(where, e, MAP_KEYS, problems):
            continue
        if not _text(e["surface"]) or e["surface"] in seen:
            problems.append(f"{where}.surface: 비었거나 중복된다")
        seen.add(e["surface"])
        if e["status"] not in MAP_STATUSES:
            problems.append(f"{where}.status: measured · partial · empty가 아니다")
            continue
        if e["derived_from"] is not None and e["derived_from"] not in DERIVED:
            problems.append(
                f"{where}.derived_from: {', '.join(sorted(DERIVED))} 또는 null이 아니다"
            )
            continue
        if e["measured_at"] is not None and not (
            isinstance(e["measured_at"], str) and DATE.match(e["measured_at"])
        ):
            problems.append(f"{where}.measured_at: YYYY-MM-DD가 아니다")
        if not _url(e["source_url"]):
            problems.append(f"{where}.source_url: https 링크가 아니다")
        if e["derived_from"] is not None:
            # 반복 측정에서 나오는 칸은 숫자를 갖지 않는다. 묶음이 무효일 때 큐레이션 문장이
            # 결과를 계속 말하는 것을 막는다.
            if e["status"] == "empty":
                problems.append(f"{where}: 비어 있음 칸은 반복 측정에서 파생될 수 없다")
            if any(e[k] is not None for k in ("summary", "detail", "denominator")):
                problems.append(f"{where}: 반복 측정 파생 칸에 직접 적은 값이 있다")
            continue
        if e["status"] == "empty":
            if not _text(e["reason"]):
                problems.append(f"{where}.reason: 비어 있음 칸에 이유가 없다")
            if e["summary"] is not None or e["denominator"] is not None:
                problems.append(f"{where}: 비어 있음 칸에 수치가 있다")
            continue
        for k in ("summary", "denominator", "measured_at", "source"):
            if not _text(e[k]):
                problems.append(f"{where}.{k}: 수치가 있는 칸에 {k}가 없다")
        if isinstance(e["summary"], str) and len(e["summary"]) > SUMMARY_MAX:
            problems.append(f"{where}.summary: {SUMMARY_MAX}자를 넘는다")


def _check_ledger(entries: Any, problems: list[str]) -> None:
    if not isinstance(entries, list) or not entries:
        problems.append("ledger: 항목이 하나도 없다")
        return
    dates: list[str] = []
    for index, e in enumerate(entries):
        where = f"ledger[{index}]"
        if not _check_keys(where, e, LEDGER_KEYS, problems):
            continue
        if not (isinstance(e["date"], str) and DATE.match(e["date"])):
            problems.append(f"{where}.date: YYYY-MM-DD가 아니다")
            continue
        dates.append(e["date"])
        for k in ("changed", "technique", "applied", "evidence"):
            if not _text(e[k]):
                # 측정이 바꾼 것이 없는 적용은 원장에 넣지 않는다(스펙).
                problems.append(f"{where}.{k}: 비어 있다")
        if not _url(e["evidence_url"]):
            problems.append(f"{where}.evidence_url: https 링크가 아니다")
    if dates != sorted(dates):
        problems.append("ledger: 날짜 오름차순이 아니다")


def _check_question(index: int, q: Any, n_runs: int, problems: list[str]) -> bool:
    where = f"series.questions[{index}]"
    if not _check_keys(where, q, QUESTION_KEYS, problems):
        return False
    ok = True
    outcomes = q["outcomes"]
    if not (isinstance(outcomes, list) and len(outcomes) == n_runs and set(outcomes) <= OUTCOMES):
        problems.append(f"{where}.outcomes: 회차 수만큼의 pass · fail · not_run이 아니다")
        return False
    if q["kind"] not in KINDS:
        problems.append(f"{where}.kind: answerable 또는 refusal이 아니다")
        ok = False
    # 미실행은 실패가 아니다. 안정성을 outcomes에서 다시 유도해 손으로 고친 값을 잡는다.
    if q["stability"] != reliability.stability(outcomes):
        problems.append(f"{where}.stability: 회차 결과에서 다시 유도한 값과 다르다")
        ok = False
    if not isinstance(q["known_failure"], bool):
        problems.append(f"{where}.known_failure: 참/거짓이 아니다")
        ok = False
    failed = "fail" in outcomes
    for field in ("reported_stage", "automatic_stage"):
        value = q[field]
        if not failed and value is not None:
            problems.append(f"{where}.{field}: 실패가 없는데 단계가 있다")
            ok = False
        elif value is not None and value not in STAGES:
            problems.append(f"{where}.{field}: 알 수 없는 단계 {value}")
            ok = False
    if failed and q["reported_stage"] is None:
        problems.append(f"{where}.reported_stage: 실패한 문항에 보고 단계가 없다")
        ok = False
    for field in ("query", "note"):
        if q[field] is not None and not isinstance(q[field], str):
            problems.append(f"{where}.{field}: 문자열이 아니다")
            ok = False
    return ok


def _check_questions(
    questions: Any, runs: list[dict[str, Any]], synthetic: Any, problems: list[str]
) -> bool:
    if not isinstance(questions, list) or not questions:
        problems.append("series.questions: 유효한 묶음에 문항 결과가 없다")
        return False
    if not all([_check_question(i, q, len(runs), problems) for i, q in enumerate(questions)]):
        return False
    ok = True
    ids = [q["id"] for q in questions]
    if len(set(ids)) != len(ids):
        problems.append("series.questions: 문항 id가 중복된다")
        ok = False
    if isinstance(synthetic, dict):
        if len(questions) != synthetic.get("questions"):
            problems.append("series.questions: 문항 수가 synthetic.questions와 다르다")
            ok = False
        refusals = sum(1 for q in questions if q["kind"] == "refusal")
        if refusals != synthetic.get("unanswerable"):
            problems.append("series.questions: 거절 문항 수가 synthetic.unanswerable과 다르다")
            ok = False
    for i, run in enumerate(runs):
        where = f"series.runs[{i}]"
        cells = [(q["kind"], q["outcomes"][i]) for q in questions]
        asked = [(kind, o) for kind, o in cells if o != "not_run"]
        answerable = [o for kind, o in asked if kind == "answerable"]
        refusal = [o for kind, o in asked if kind == "refusal"]
        if run["asked"] != len(asked):
            problems.append(f"{where}.asked: 문항 결과의 실행 수와 다르다")
            ok = False
        if run["answerable_asked"] != len(answerable) or run["answerable_passed"] != sum(
            1 for o in answerable if o == "pass"
        ):
            problems.append(f"{where}: 답할 수 있는 문항의 통과 · 실행 수가 문항 결과와 다르다")
            ok = False
        expected_refusal = sum(1 for o in refusal if o == "pass") if refusal else None
        if run["refusal_asked"] != len(refusal) or run["refusal_correct"] != expected_refusal:
            problems.append(f"{where}: 거절 문항의 정확한 거절 · 실행 수가 문항 결과와 다르다")
            ok = False
    return ok


# --- CLI ------------------------------------------------------------------------------------


def _write(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_curated(path: Path) -> dict[str, Any]:
    curated = _read_json(path)
    if not isinstance(curated, dict) or set(curated) != CURATED_KEYS:
        raise ShowcaseError(f"{path}: 키가 {', '.join(sorted(CURATED_KEYS))}가 아니다")
    return curated


def cmd_export(args: argparse.Namespace) -> int:
    report = _read_json(args.report)
    sample = reliability.replay._load_sample(args.fixture)
    record = build_public(
        report,
        sample=sample,
        labels={str(x["id"]): x for x in (_read_json(args.labels).get("labels") or [])},
        curated=_read_curated(args.curated),
        provenance={
            "report_sha256": _file_sha256(args.report),
            "fixture_sha256": _file_sha256(args.fixture),
            "labels_sha256": _file_sha256(args.labels),
            "curated_sha256": _file_sha256(args.curated),
        },
    )
    problems = check_public(record)
    if problems:
        raise ShowcaseError(
            "공개 기록이 검사를 통과하지 못해 쓰지 않는다\n  " + "\n  ".join(problems)
        )
    _write(args.out, record)
    print(f"evaluation_showcase: {args.out}에 공개 기록을 썼다 (유효: {record['series']['valid']})")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    problems = check_public(_read_json(args.record))
    if problems:
        print("evaluation_showcase: 검사 실패\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    print(f"evaluation_showcase: {args.record} 검사 통과")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="공개 평가 쇼케이스 기록 만들기와 검사")
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export", help="보존된 반복 측정 기록에서 공개 기록을 만든다")
    export.add_argument("--report", type=Path, required=True)
    export.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    export.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    export.add_argument("--curated", type=Path, default=DEFAULT_CURATED)
    export.add_argument("--out", type=Path, required=True)
    export.set_defaults(func=cmd_export)
    check = sub.add_parser("check", help="공개 기록의 허용 필드와 불변식을 검사한다")
    check.add_argument("record", type=Path)
    check.set_defaults(func=cmd_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
