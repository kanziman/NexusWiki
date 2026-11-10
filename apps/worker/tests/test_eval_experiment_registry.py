"""실험 기록이 저장 판정을 그대로 옮기고, 공개 스냅샷이 허용 필드와 공개 실험만 담는지 검사한다."""

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "eval_experiments", ROOT / "scripts/eval_experiments.py"
)
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)

RESEARCH = json.loads((ROOT / "apps/dashboard/content/evidence-research.json").read_text())


def late_commit(paths):
    # 실제 기록과 같은 순서: 기준 문서가 실행보다 늦게 커밋됐다.
    return ("0f9bbbe", "2026-11-09T02:00:01+00:00")


def records():
    return registry.research_records(copy.deepcopy(RESEARCH), late_commit)


def db_rows():
    """DB가 돌려주는 모양을 흉내 낸다. 생성 열과 내부 열이 함께 오고 키 순서로 정렬된다."""
    rec = registry.build_records(first_commit=late_commit)
    for table, key in registry.TABLES:
        rec[table].sort(key=lambda row, key=key: row[key])
    criteria = [{**row, "preregistered": False} for row in rec["eval_criteria_sets"]]
    decisions = [{**row, "experiment_kind": "adoption"} for row in rec["eval_decisions"]]
    return {**rec, "eval_criteria_sets": criteria, "eval_decisions": decisions}


def test_original_criteria_copy_stored_checks_without_recomputing():
    rec = records()
    conditions = {c["key"]: c for c in rec["eval_criteria_sets"][0]["conditions"]}
    assert {key: c["met"] for key, c in conditions.items()} == {
        key: RESEARCH["checks"][key] for key in conditions
    }
    missed = sorted(key for key, c in conditions.items() if not c["met"])
    assert missed == ["answer_recovered", "cost_within_limit", "total_pass_improved"]
    assert conditions["cost_within_limit"]["actual"] == "+66.4%"
    assert conditions["latency_within_limit"]["actual"] == "+1.18초"
    assert rec["eval_criteria_sets"][0]["adopted"] is False
    decision = rec["eval_decisions"][0]
    assert decision["status"] == "not_adopted"
    assert "3개 미충족" in decision["rationale"]


def test_criteria_limits_come_from_the_script_that_judged():
    evaluation = registry._load_research_eval()
    conditions = {c["key"]: c for c in records()["eval_criteria_sets"][0]["conditions"]}
    assert conditions["cost_within_limit"]["limit"] == (
        f"+{round((evaluation.COST_LIMIT_RATIO - 1) * 100)}%"
    )
    assert conditions["latency_within_limit"]["limit"] == f"+{evaluation.P95_LIMIT_MS / 1000:g}초"


def test_provenance_records_commit_and_earliest_run():
    criteria = records()["eval_criteria_sets"][0]
    assert criteria["source_commit"] == "0f9bbbe"
    assert criteria["earliest_run_at"] == "2026-11-08T23:26:20+00:00"
    # 사전 등록 여부는 DB 생성 열이 정한다. 등록 행이 값을 들고 가면 손으로 쓴 것과 같다.
    assert "preregistered" not in criteria


def test_real_git_history_puts_criteria_after_the_runs():
    sha, at = registry.git_first_commit(registry.RESEARCH_CRITERIA_PATHS)
    assert len(sha) >= 7
    assert at > min(registry.utc(run["created_at"]) for run in RESEARCH["runs"])


def test_missing_run_is_rejected():
    broken = copy.deepcopy(RESEARCH)
    broken["runs"] = [run for run in broken["runs"] if run["mode"] != "on"]
    with pytest.raises(registry.RegistryError, match="off/on"):
        registry.research_records(broken, late_commit)


def test_invalid_or_mismatched_record_is_rejected():
    invalid = copy.deepcopy(RESEARCH)
    invalid["conditions_match"] = False
    with pytest.raises(registry.RegistryError, match="유효하지"):
        registry.research_records(invalid, late_commit)
    lying = copy.deepcopy(RESEARCH)
    lying["adopted"] = True
    with pytest.raises(registry.RegistryError, match="adopted"):
        registry.research_records(lying, late_commit)


def test_upsert_is_idempotent_and_runs_as_service_role():
    sql = registry.upsert_sql(records())
    assert sql.startswith("begin;\nset local role service_role;")
    for table, key in registry.TABLES:
        assert f"insert into public.{table} " in sql
        assert f"on conflict ({key}) do update set" in sql
    # 생성 열은 쓰지 않는다.
    assert "preregistered" not in sql


def test_upsert_payload_cannot_close_its_dollar_quote(monkeypatch):
    rec = records()
    tags = iter(["jcollide", "jcollide", "jsafe1", "jsafe2", "jsafe3", "jsafe4"])
    monkeypatch.setattr(registry, "_tag", lambda: next(tags))
    rec["eval_experiments"][0]["title"] = "제목 $jcollide$ 끝"
    sql = registry.upsert_sql(rec)
    assert "$jsafe1$" in sql or "$jsafe2$" in sql


def test_snapshot_has_public_experiments_with_run_identity():
    snapshot = registry.build_snapshot(db_rows())
    assert [e["id"] for e in snapshot["experiments"]] == [
        "ask-evidence-research",
        "ask-replay-reliability",
    ]
    runs = snapshot["experiments"][0]["runs"]
    assert runs["baseline"]["id"] == "off" and runs["candidate"]["id"] == "on"
    assert runs["candidate"]["dirty"] is True
    assert "public" not in snapshot["experiments"][0]
    assert "experiment_kind" not in snapshot["decisions"][0]
    assert snapshot["criteria_sets"][0]["preregistered"] is False


def test_local_only_experiment_and_decision_are_excluded():
    rows = db_rows()
    hidden = {**rows["eval_experiments"][0], "id": "local-grader", "public": False}
    rows["eval_experiments"].append(hidden)
    rows["eval_decisions"].append({**rows["eval_decisions"][0], "experiment_id": "local-grader"})
    snapshot = registry.build_snapshot(rows)
    assert "local-grader" not in [e["id"] for e in snapshot["experiments"]]
    assert [d["experiment_id"] for d in snapshot["decisions"]] == ["ask-evidence-research"]


@pytest.mark.parametrize("field", ["workspace_id", "answer"])
def test_forbidden_field_stops_export(field):
    rows = db_rows()
    rows["eval_decisions"][0][field] = "x"
    with pytest.raises(registry.RegistryError, match="금지 필드"):
        registry.build_snapshot(rows)


def test_unknown_field_stops_export():
    rows = db_rows()
    rows["eval_criteria_sets"][0]["conditions"][0]["note"] = "x"
    with pytest.raises(registry.RegistryError, match="허용 목록 밖"):
        registry.build_snapshot(rows)


def test_unknown_run_stops_export():
    rows = db_rows()
    rows["eval_experiments"][0]["candidate_run_id"] = "maybe"
    with pytest.raises(registry.RegistryError, match="없는 실행"):
        registry.build_snapshot(rows)


def test_export_is_byte_identical_and_matches_committed_snapshot():
    first = registry.serialize(registry.build_snapshot(db_rows()))
    second = registry.serialize(registry.build_snapshot(db_rows()))
    assert first == second
    committed = json.loads(registry.SNAPSHOT.read_text())
    assert committed["experiments"] == json.loads(first)["experiments"]
    assert committed["decisions"] == json.loads(first)["decisions"]


def test_committed_snapshot_thresholds_match_their_single_sources():
    """기준값이 정본과 어긋나면 실패한다(design.md D6). 화면 쪽은 regression-policy.test.ts."""
    evaluation = registry._load_research_eval()
    committed = json.loads(registry.SNAPSHOT.read_text())
    original = {c["key"]: c for c in committed["criteria_sets"][0]["conditions"]}
    cost_pct = round((evaluation.COST_LIMIT_RATIO - 1) * 100)
    assert original["cost_within_limit"]["limit"] == f"+{cost_pct}%"
    assert original["latency_within_limit"]["limit"] == (f"+{evaluation.P95_LIMIT_MS / 1000:g}초")
    policies = {p["version"]: p for p in committed["policies"]}
    assert policies["adoption-v1"] == registry.POLICY_V1


def test_dashboard_has_no_hardcoded_adoption_thresholds():
    """화면 코드에 예전 기본값(50%·15초) 상태가 남으면 정책과 따로 놀 수 있다."""
    source = (ROOT / "apps/dashboard/components/RegressionDashboard.tsx").read_text()
    for needle in ('useState("50")', 'useState("15")', "localStorage"):
        assert needle not in source


def test_reliability_is_a_stability_measurement_without_adoption_refs():
    rec = registry.build_records(first_commit=late_commit)
    experiments = {e["id"]: e for e in rec["eval_experiments"]}
    stability = experiments["ask-replay-reliability"]
    assert stability["kind"] == "stability"
    assert stability["criteria_set_id"] is None and stability["policy_version"] is None
    assert [d["experiment_id"] for d in rec["eval_decisions"]] == ["ask-evidence-research"]


def test_reliability_missing_run_is_rejected():
    runs = json.loads(registry.RELIABILITY.read_text())
    runs["runs"] = [run for run in runs["runs"] if run["id"] != "run-2"]
    with pytest.raises(registry.RegistryError, match="run-1/run-2"):
        registry.reliability_records(runs)


def test_reliability_identity_does_not_invent_a_run_time():
    identity = registry.run_identity("reliability", "run-1")
    assert identity == {"id": "run-1", "revision": "9ae4244", "dirty": True, "created_at": None}
    with pytest.raises(registry.RegistryError, match="없는 실행"):
        registry.run_identity("reliability", "run-9")


def _local_dir(tmp_path, ids, baseline):
    for i, run_id in enumerate(ids):
        (tmp_path / f"run-{i:03d}.json").write_text(json.dumps({"id": run_id}))
    (tmp_path / "baseline.json").write_text(json.dumps({"id": baseline}))
    return tmp_path


def test_local_history_is_a_private_grader_check(tmp_path):
    rec = registry.local_records(_local_dir(tmp_path, ["seed", "a", "b"], "seed"))
    experiment = rec["eval_experiments"][0]
    assert experiment["kind"] == "grader" and experiment["public"] is False
    assert (experiment["baseline_run_id"], experiment["candidate_run_id"]) == ("seed", "b")


def test_local_history_absent_or_single_run_registers_nothing(tmp_path):
    assert registry.local_records(tmp_path / "missing") == {}
    assert registry.local_records(_local_dir(tmp_path, ["seed"], "seed")) == {}


def test_local_baseline_must_exist(tmp_path):
    with pytest.raises(registry.RegistryError, match="기준선"):
        registry.local_records(_local_dir(tmp_path, ["a", "b"], "gone"))


def test_local_experiment_matches_dashboard_definition():
    source = (ROOT / "apps/dashboard/lib/experiments.ts").read_text()
    start = source.index("export const localGraderExperiment")
    block = source[start : source.index("} as const;", start)]
    for key in (
        "id",
        "kind",
        "title",
        "question",
        "run_source",
        "baseline_role",
        "candidate_role",
        "reference",
    ):
        assert f'{key}: "{registry.LOCAL_EXPERIMENT[key]}"' in block, key


def test_unknown_criteria_commit_is_recorded_not_invented():
    def no_history(paths):
        if "evidence-research.json" in paths[0]:
            return late_commit(paths)
        return (None, None)

    criteria = registry.research_records(copy.deepcopy(RESEARCH), no_history)["eval_criteria_sets"][
        0
    ]
    assert criteria["source_commit"] is None
    assert criteria["source_first_commit_at"] is None


def test_registration_checks_each_experiment_run_against_stored_results(monkeypatch):
    original = registry.reliability_records

    def renamed(runs):
        rec = original(runs)
        rec["eval_experiments"][0]["candidate_run_id"] = "run-9"
        return rec

    monkeypatch.setattr(registry, "reliability_records", renamed)
    with pytest.raises(registry.RegistryError, match="없는 실행"):
        registry.build_records(first_commit=late_commit)


def test_grader_check_points_at_the_pr_gate_contract():
    reference = registry.LOCAL_EXPERIMENT["reference"]
    assert reference == "openspec/specs/offline-eval-regression-gate/spec.md"
    assert (ROOT / reference).exists()
