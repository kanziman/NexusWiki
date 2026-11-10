#!/usr/bin/env python3
"""저장된 평가 결과를 실험 기록으로 등록하고, 공개 실험만 허용 필드 스냅샷으로 내보낸다.

사용:
  .venv/bin/python scripts/eval_experiments.py register   # 로컬 DB에 upsert
  .venv/bin/python scripts/eval_experiments.py export     # apps/dashboard/content/experiments.json

새 실행·재채점·모델 호출은 하지 않는다. 로컬 DB 컨테이너의 psql로 접속해 트랜잭션 안에서
service_role로 전환하므로 REST 키를 읽지 않는다.
설계: openspec/changes/archive/2026-11-10-evaluation-experiment-registry/design.md
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import secrets
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "apps/dashboard/content"
SNAPSHOT = CONTENT / "experiments.json"
RESEARCH = CONTENT / "evidence-research.json"
RELIABILITY = CONTENT / "evaluation-runs.json"
CONTAINER = os.environ.get("NEXUSWIKI_DB_CONTAINER", "supabase_db_NexusWiki")
# 로컬 실행기가 쓰는 gitignore 디렉터리. worktree에서 돌릴 때는 원본 체크아웃 경로를 넘긴다.
LOCAL_RUNS = Path(
    os.environ.get("NEXUSWIKI_LOCAL_EVAL_DIR", ROOT / ".worktrees/evaluation-dashboard")
)

# apps/dashboard/lib/experiments.ts의 localGraderExperiment와 같아야 한다(테스트가 대조한다).
LOCAL_EXPERIMENT = {
    "id": "local-grader-check",
    "kind": "grader",
    "title": "채점 규칙 변경 확인",
    "question": "새 검증은 기준선과 무엇이 달라졌나요?",
    "run_source": "local",
    "baseline_role": "지정한 기준 기록",
    "candidate_role": "새 검증",
    "criteria_set_id": None,
    "policy_version": None,
    "public": False,
    "reference": "openspec/specs/offline-eval-regression-gate/spec.md",
}

# 원래 경로에서 처음 커밋됐고 아카이브로 옮겨졌다. 두 경로 중 가장 이른 커밋이 기록 시각이다.
# HEAD 이력만 본다. 다른 로컬 브랜치(squash 전 커밋)까지 보면 클론마다 결과가 달라진다.
RESEARCH_CRITERIA_PATHS = (
    "openspec/changes/ask-evidence-research/design.md",
    "openspec/changes/archive/2026-11-09-ask-evidence-research/design.md",
)

POLICY_V1 = {
    "version": "adoption-v1",
    "regression_rule": "per_question",
    "require_improvement": True,
    "max_excluded": 0,
    "max_cost_increase_pct": 50,
    "max_p95_increase_ms": 15000,
    "limitation": (
        "기준선과 후보를 한 번씩만 실행해 판정한다. 같은 질문을 다시 답할 때 생기는 흔들림과 "
        "실제 회귀를 구분하지 못한다."
    ),
    "defined_on": "2026-11-10",
}

TABLES = (
    ("eval_policies", "version"),
    ("eval_criteria_sets", "id"),
    ("eval_experiments", "id"),
    ("eval_decisions", "experiment_id"),
)

# 공개 스냅샷에 실을 수 있는 필드. 목록 밖 필드가 생기면 내보내기를 멈춘다.
ALLOWED = {
    "root": {"schema", "synthetic", "policies", "criteria_sets", "experiments", "decisions"},
    "policies": {
        "version",
        "regression_rule",
        "require_improvement",
        "max_excluded",
        "max_cost_increase_pct",
        "max_p95_increase_ms",
        "limitation",
        "defined_on",
    },
    "criteria_sets": {
        "id",
        "name",
        "source_path",
        "source_commit",
        "source_first_commit_at",
        "earliest_run_at",
        "preregistered",
        "conditions",
        "adopted",
    },
    "conditions": {"key", "label", "limit", "actual", "met"},
    "experiments": {
        "id",
        "kind",
        "title",
        "question",
        "run_source",
        "baseline_run_id",
        "candidate_run_id",
        "baseline_role",
        "candidate_role",
        "criteria_set_id",
        "policy_version",
        "reference",
        "runs",
    },
    "runs": {"id", "revision", "dirty", "created_at"},
    "decisions": {"experiment_id", "status", "rationale", "decided_on", "criteria_set_id"},
}
FORBIDDEN = {"workspace_id", "user_id", "email", "answer", "response_text", "token", "api_key"}


class RegistryError(RuntimeError):
    """등록·내보내기를 멈춰야 하는 기록 문제."""


def _load_research_eval():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "evidence_research_eval", ROOT / "scripts/evidence_research_eval.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def utc(value: str) -> str:
    """시각 표기를 한 가지로 맞춘다. 같은 시각이 다른 문자열이 되면 내보내기가 결정적이지 않다."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RegistryError(f"시간대 없는 시각: {value}")
    return parsed.astimezone(UTC).isoformat(timespec="seconds")


def git_first_commit(
    paths: tuple[str, ...], root: Path = ROOT
) -> tuple[str, str] | tuple[None, None]:
    """경로들의 가장 이른 커밋. 찾지 못하면 (None, None)이다. 시각을 추측해 넣지 않는다."""
    found: list[tuple[str, str]] = []
    for path in paths:
        out = subprocess.run(  # noqa: S603 - 고정 git 명령, 경로는 코드 상수다
            ["git", "log", "--reverse", "--format=%h %aI", "--", path],  # noqa: S607
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split("\n")
        if out[0].strip():
            sha, at = out[0].split()
            found.append((sha, utc(at)))
    if not found:
        return (None, None)
    return min(found, key=lambda item: item[1])


def _pct(before: float, after: float) -> float:
    return round((after / before - 1) * 100, 1)


def research_records(record: dict[str, Any], first_commit=git_first_commit) -> dict[str, list]:
    """재검색 OFF/ON을 원래 기준과 저장 판정으로 등록할 행을 만든다. 판정을 다시 계산하지 않는다."""
    evaluation = _load_research_eval()
    if not (record.get("valid") and record.get("conditions_match")):
        raise RegistryError("재검색 기록이 유효하지 않거나 비교 조건이 다르다")
    runs = {run["mode"]: run for run in record["runs"]}
    if not {"off", "on"} <= set(runs):
        raise RegistryError("재검색 기록에 off/on 실행이 모두 있어야 한다")
    checks, off, on = record["checks"], record["summary"]["off"], record["summary"]["on"]
    recovery = record["recovery"]
    cost_limit = round((evaluation.COST_LIMIT_RATIO - 1) * 100)
    p95_limit = evaluation.P95_LIMIT_MS / 1000
    conditions = [
        {
            "key": "answer_recovered",
            "label": "답변 복구 1건 이상",
            "limit": "1건 이상",
            "actual": f"{recovery['answer']}건 (복구 대상 {recovery['eligible']}개)",
            "met": checks["answer_recovered"],
        },
        {
            "key": "total_pass_improved",
            "label": "전체 통과 수 증가",
            "limit": "기준선보다 많음",
            "actual": f"{off['passed']} → {on['passed']}",
            "met": checks["total_pass_improved"],
        },
        {
            "key": "no_regression",
            "label": "기존 30문항 통과 수 감소 없음",
            "limit": "감소 없음 (합계)",
            "actual": f"{off['regression_passed']} → {on['regression_passed']}",
            "met": checks["no_regression"],
        },
        {
            "key": "no_fabrication_increase",
            "label": "위조 인용 증가 없음",
            "limit": "증가 없음",
            "actual": f"{off['fabricated']} → {on['fabricated']}",
            "met": checks["no_fabrication_increase"],
        },
        {
            "key": "cost_within_limit",
            "label": f"총비용 증가 {cost_limit}% 이하",
            "limit": f"+{cost_limit}%",
            "actual": f"{_pct(off['cost_micros'], on['cost_micros']):+.1f}%",
            "met": checks["cost_within_limit"],
        },
        {
            "key": "latency_within_limit",
            "label": f"p95 응답 시간 증가 {p95_limit:g}초 이하",
            "limit": f"+{p95_limit:g}초",
            "actual": f"{(on['latency_p95'] - off['latency_p95']) / 1000:+.2f}초",
            "met": checks["latency_within_limit"],
        },
    ]
    # 비교 조건 일치·측정 완료까지 모두 참이어야 당시 채택이었다.
    # 판정을 옮겨 쓸 때 이 관계가 깨지면 멈춘다.
    if record["adopted"] != all(checks.values()):
        raise RegistryError("저장된 adopted가 조건별 판정과 맞지 않는다")
    sha, first_at = first_commit(RESEARCH_CRITERIA_PATHS)
    _, decided_at = first_commit(("apps/dashboard/content/evidence-research.json",))
    if decided_at is None:
        # 결정 날짜는 결과 기록이 처음 커밋된 날이다. 이력이 없으면 날짜를 지어내지 않고 멈춘다.
        raise RegistryError("재검색 결과 기록의 커밋을 찾지 못해 결정 날짜를 정할 수 없다")
    criteria = {
        "id": "ask-evidence-research-d4",
        "name": "재검색 도입 원래 기준 (D4)",
        "source_path": RESEARCH_CRITERIA_PATHS[-1],
        "source_commit": sha,
        "source_first_commit_at": first_at,
        "earliest_run_at": min(utc(run["created_at"]) for run in record["runs"]),
        "conditions": conditions,
        "adopted": record["adopted"],
    }
    missed = [item["label"] for item in conditions if not item["met"]]
    experiment = {
        "id": "ask-evidence-research",
        "kind": "adoption",
        "title": "재검색 도입",
        "question": "한 번 더 검색하면 답변이 좋아질까요?",
        "run_source": "research",
        "baseline_run_id": "off",
        "candidate_run_id": "on",
        "baseline_role": "현재 방식",
        "candidate_role": "도입 검토안",
        "criteria_set_id": criteria["id"],
        "policy_version": POLICY_V1["version"],
        "public": True,
        "reference": None,
    }
    decision = {
        "experiment_id": experiment["id"],
        "status": "adopted" if record["adopted"] else "not_adopted",
        "rationale": (
            f"원래 기준 {len(conditions)}개 중 {len(missed)}개 미충족({', '.join(missed)}). "
            "기준 미달 시 결과를 공개하고 기본 OFF를 유지한다는 사전 결정에 따라 미채택."
            if missed
            else "원래 기준을 모두 충족했다."
        ),
        "decided_on": decided_at[:10],
        "criteria_set_id": criteria["id"],
    }
    return {
        "eval_policies": [POLICY_V1],
        "eval_criteria_sets": [criteria],
        "eval_experiments": [experiment],
        "eval_decisions": [decision],
    }


def reliability_records(runs: dict[str, Any]) -> dict[str, list]:
    """Ask 반복 측정은 채택할 대상이 없는 안정성 측정이다. 기준·정책·결정을 붙이지 않는다."""
    ids = {run["id"] for run in runs["runs"]}
    if not {"run-1", "run-2"} <= ids:
        raise RegistryError("반복 측정 기록에 run-1/run-2가 모두 있어야 한다")
    return {
        "eval_experiments": [
            {
                "id": "ask-replay-reliability",
                "kind": "stability",
                "title": "같은 질문의 반복 결과",
                "question": "같은 질문에 다시 답해도 결과가 유지될까요?",
                "run_source": "reliability",
                "baseline_run_id": "run-1",
                "candidate_run_id": "run-2",
                "baseline_role": "기준 반복",
                "candidate_role": "비교 반복",
                "criteria_set_id": None,
                "policy_version": None,
                "public": True,
                "reference": None,
            }
        ]
    }


def local_records(directory: Path | None = None) -> dict[str, list]:
    """로컬 재채점 이력을 비공개 채점 검증으로 등록한다. 기록이 없는 클론에서는 등록하지 않는다."""
    directory = LOCAL_RUNS if directory is None else directory
    if not directory.is_dir():
        return {}
    runs = [json.loads(path.read_text())["id"] for path in sorted(directory.glob("run-*.json"))]
    baseline_path = directory / "baseline.json"
    if len(runs) < 2 or not baseline_path.exists():
        return {}
    baseline = json.loads(baseline_path.read_text())["id"]
    if baseline not in runs:
        raise RegistryError(f"로컬 기준선이 실행 목록에 없다: {baseline}")
    candidate = next(run for run in reversed(runs) if run != baseline)
    return {
        "eval_experiments": [
            {**LOCAL_EXPERIMENT, "baseline_run_id": baseline, "candidate_run_id": candidate}
        ]
    }


def _merge(*parts: dict[str, list]) -> dict[str, list]:
    merged: dict[str, list] = {table: [] for table, _ in TABLES}
    for part in parts:
        for table, rows in part.items():
            merged[table].extend(rows)
    return merged


def build_records(root: Path = ROOT, first_commit=git_first_commit) -> dict[str, list]:
    content = root / "apps/dashboard/content"
    research = json.loads((content / "evidence-research.json").read_text())
    reliability = json.loads((content / "evaluation-runs.json").read_text())
    records = _merge(
        research_records(research, first_commit),
        reliability_records(reliability),
        local_records(),
    )
    for table, key in TABLES:
        ids = [row[key] for row in records[table]]
        if len(ids) != len(set(ids)):
            raise RegistryError(f"{table}에 중복 키가 있다")
    validate_run_refs(records, root)
    return records


def validate_run_refs(records: dict[str, list], root: Path = ROOT) -> None:
    """실험 행이 가리키는 실행이 저장 결과에 실제로 있는지 등록 전에 확인한다."""
    for row in records["eval_experiments"]:
        if row["run_source"] == "local":
            continue  # local_records가 실행기 디렉터리에서 직접 고른 id다.
        for role in ("baseline_run_id", "candidate_run_id"):
            run_identity(row["run_source"], row[role], root)


def _tag() -> str:
    return "j" + secrets.token_hex(8)


def upsert_sql(records: dict[str, list]) -> str:
    """psql에 넘길 upsert SQL. 값은 JSON 한 덩어리로 넘겨 인용 오류와 주입을 피한다."""
    parts = ["begin;", "set local role service_role;"]
    for table, key in TABLES:
        rows = records.get(table, [])
        if not rows:
            continue
        payload = json.dumps(rows, ensure_ascii=False, sort_keys=True)
        tag = _tag()
        while f"${tag}$" in payload:
            tag = _tag()
        columns = sorted(rows[0])
        cols = ", ".join(columns)
        updates = ", ".join(f"{c} = excluded.{c}" for c in columns if c != key)
        # 테이블·열 이름은 코드 상수(TABLES)와 등록 행의 키뿐이고, 값은 달러 인용 JSON으로만 넘긴다.
        parts.append(
            f"insert into public.{table} ({cols}) "  # noqa: S608
            f"select {cols} from jsonb_populate_recordset("
            f"null::public.{table}, ${tag}${payload}${tag}$) "
            f"on conflict ({key}) do update set {updates};"
        )
    parts.append("commit;")
    return "\n".join(parts)


def select_sql() -> str:
    tables = ", ".join(
        f"'{table}', coalesce((select jsonb_agg(to_jsonb(t) order by t.{key}) "  # noqa: S608
        f"from public.{table} t), '[]'::jsonb)"
        for table, key in TABLES
    )
    return f"begin; set local role service_role; select jsonb_build_object({tables}); commit;"


def psql(sql: str) -> str:
    result = subprocess.run(  # noqa: S603 - 고정 인자, SQL은 표준 입력으로만 넘긴다
        [  # noqa: S607 - 로컬 docker CLI
            "docker",
            "exec",
            "-i",
            CONTAINER,
            "psql",
            "-U",
            "postgres",
            "-d",
            "postgres",
            "-v",
            "ON_ERROR_STOP=1",
            "-qtA",
        ],
        input=sql,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RegistryError(f"psql 실패: {result.stderr.strip()}")
    return result.stdout


def run_identity(source: str, run_id: str, root: Path = ROOT) -> dict[str, Any]:
    if source == "research":
        record = json.loads((root / "apps/dashboard/content/evidence-research.json").read_text())
        runs = {run["mode"]: run for run in record["runs"]}
        if run_id not in runs:
            raise RegistryError(f"재검색 기록에 없는 실행: {run_id}")
        run = runs[run_id]
        return {
            "id": run_id,
            "revision": run["revision"],
            "dirty": "작업트리" in run.get("source_state", ""),
            "created_at": utc(run["created_at"]),
        }
    if source == "reliability":
        record = json.loads((root / "apps/dashboard/content/evaluation-runs.json").read_text())
        runs = {run["id"]: run for run in record["runs"]}
        if run_id not in runs:
            raise RegistryError(f"반복 측정 기록에 없는 실행: {run_id}")
        revision = runs[run_id]["revision"] or ""
        return {
            "id": run_id,
            "revision": revision.removesuffix("+dirty"),
            "dirty": revision.endswith("+dirty"),
            # 이 기록은 실행 시각을 남기지 않았다. 추측한 시각을 넣지 않는다.
            "created_at": None,
        }
    raise RegistryError(f"공개할 수 없는 실행 출처: {source}")


def _check_fields(value: Any, section: str, path: str) -> None:
    allowed = ALLOWED[section]
    if not isinstance(value, dict):
        raise RegistryError(f"{path}는 객체여야 한다")
    for key, item in value.items():
        if key in FORBIDDEN:
            raise RegistryError(f"금지 필드: {path}.{key}")
        if key not in allowed:
            raise RegistryError(f"허용 목록 밖 필드: {path}.{key}")
        if section == "criteria_sets" and key == "conditions":
            for i, condition in enumerate(item):
                _check_fields(condition, "conditions", f"{path}.conditions[{i}]")
        if section == "experiments" and key == "runs":
            for role, run in item.items():
                if role not in {"baseline", "candidate"}:
                    raise RegistryError(f"허용 목록 밖 필드: {path}.runs.{role}")
                _check_fields(run, "runs", f"{path}.runs.{role}")


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    _check_fields(snapshot, "root", "snapshot")
    for section in ("policies", "criteria_sets", "experiments", "decisions"):
        for i, row in enumerate(snapshot[section]):
            _check_fields(row, section, f"{section}[{i}]")


def build_snapshot(rows: dict[str, list], root: Path = ROOT) -> dict[str, Any]:
    """공개 실험과 그 참조만 고른다. 로컬 전용 실험과 그 결정은 들어가지 않는다."""
    experiments = [row for row in rows["eval_experiments"] if row.get("public") is True]
    ids = {row["id"] for row in experiments}
    criteria_ids = {row["criteria_set_id"] for row in experiments if row["criteria_set_id"]}
    policy_ids = {row["policy_version"] for row in experiments if row["policy_version"]}
    snapshot = {
        "schema": "eval-experiments.v1",
        "synthetic": True,
        "policies": [
            {key: value for key, value in row.items()}
            for row in rows["eval_policies"]
            if row["version"] in policy_ids
        ],
        "criteria_sets": [
            {
                **row,
                "source_first_commit_at": row["source_first_commit_at"]
                and utc(row["source_first_commit_at"]),
                "earliest_run_at": utc(row["earliest_run_at"]),
            }
            for row in rows["eval_criteria_sets"]
            if row["id"] in criteria_ids
        ],
        "experiments": [
            {
                **{key: value for key, value in row.items() if key != "public"},
                "runs": {
                    "baseline": run_identity(row["run_source"], row["baseline_run_id"], root),
                    "candidate": run_identity(row["run_source"], row["candidate_run_id"], root),
                },
            }
            for row in experiments
        ],
        # experiment_kind는 측정 실험 결정을 막는 DB 내부 열이라 공개하지 않는다.
        "decisions": [
            {key: value for key, value in row.items() if key != "experiment_kind"}
            for row in rows["eval_decisions"]
            if row["experiment_id"] in ids
        ],
    }
    validate_snapshot(snapshot)
    return snapshot


def serialize(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["register", "export"])
    args = parser.parse_args(argv)
    if args.command == "register":
        records = build_records()
        psql(upsert_sql(records))
        print(json.dumps({table: len(rows) for table, rows in records.items()}))
        return
    rows = json.loads(psql(select_sql()).strip())
    text = serialize(build_snapshot(rows))
    SNAPSHOT.write_text(text, encoding="utf-8")
    print(json.dumps({"written": str(SNAPSHOT.relative_to(ROOT)), "bytes": len(text.encode())}))


if __name__ == "__main__":
    try:
        main()
    except RegistryError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        sys.exit(1)
