#!/usr/bin/env python3
"""보존한 합성 재생 3회를 공개 성적표로 추린다. 네트워크·모델 호출은 없다.

질문 fixture, 수집 지문, 모델, 회차별 비용과 판정이 공개 평가와 일치해야 내보낸다.
운영 식별자·경로·프롬프트를 복사하지 않고 합성 답변은 일반 텍스트로만 공개한다.
사용: uv run python scripts/evaluation_run_export.py --out /tmp/evaluation-runs.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from ask_replay import is_refusal, keyword_hit, verdict
from eval_fingerprint import fixture_sha256

ROOT = Path(__file__).resolve().parent.parent
SENSITIVE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    r"|[\w.+-]+@[\w.-]+\.[a-z]{2,}"
    r"|(?:sk-|sk_)[a-z0-9_-]{16,}"
    r"|(?:Bearer\s+)[a-z0-9._-]+",
    re.IGNORECASE,
)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def export_run(result: dict, public: dict, fixture: dict, key: dict, index: int) -> dict:
    """고정 입력과 공개 회차에 맞는 결과의 허용 필드만 반환한다."""
    fixed = result["fixed_inputs"]
    for field in ("fixture_sha256", "snapshot_sha256", "model"):
        if fixed.get(field) != key[field]:
            raise ValueError(f"고정 입력 불일치: {field}")
    if fixed.get("answer_prompt_sha256") != key["prompt_sha256"]:
        raise ValueError("답변 프롬프트 불일치")
    if fixed.get("requested_k") != key["requested_k"]:
        raise ValueError("검색 근거 수 불일치")
    policies = fixed.get("policy_versions") or [fixed.get("policy_version")]
    if policies != [key["policy_version"]]:
        raise ValueError("검색 정책 불일치")
    questions = {q["id"]: q for q in fixture["questions"]}
    source = result["rows"]
    if len(source) != len(questions) or {r["id"] for r in source} != set(questions):
        raise ValueError("문항 집합 불일치")
    rows = []
    for row in source:
        q = questions[row["id"]]
        if row.get("doc") != q["doc"] or row.get("model") != key["model"]:
            raise ValueError("문항 또는 모델 불일치")
        answer = row.get("answer")
        if not isinstance(answer, str) or SENSITIVE.search(answer):
            raise ValueError("공개할 수 없는 답변 본문")
        expected_hit = (
            None
            if q["doc"] == "none"
            else all(keyword_hit(answer, group) for group in q["expect_all"])
            if q.get("expect_all")
            else keyword_hit(answer, q.get("expect_any", []))
        )
        # 저장된 불리언만 믿으면 본문을 바꿔도 이전 통과 판정이 남는다.
        if row.get("keyword_hit") is not expected_hit:
            raise ValueError("실제 답변의 기대 표현 판정 불일치")
        decision = verdict(row)
        route = row.get("route") or {}
        rows.append(
            {
                "id": q["id"],
                "query": q["query"],
                "kind": "refusal" if q["doc"] == "none" else "answerable",
                "expected": {"any": q.get("expect_any", []), "all": q.get("expect_all", [])},
                "response_text": answer,
                "status": row["status"],
                "passed": decision["pass"],
                "reason": decision["reason"],
                "keyword_hit": expected_hit,
                "refused": is_refusal(answer) or row["status"] == "no-evidence",
                "cited_wiki": row.get("cited_wiki_count"),
                "cited_source": row.get("cited_source_count"),
                "fabricated": row.get("fabricated_anchor_count"),
                "prompt_tokens": row.get("prompt_tokens"),
                "completion_tokens": row.get("completion_tokens"),
                "cost_micros": row.get("cost_micros"),
                "elapsed_ms": row.get("elapsed_ms"),
                "route": route.get("decision"),
            }
        )
    asked = sum(r["kind"] == "answerable" for r in rows)
    passed = sum(r["passed"] and r["kind"] == "answerable" for r in rows)
    cost = sum(r["cost_micros"] for r in rows)
    if (asked, passed, cost) != (
        public["answerable_asked"],
        public["answerable_passed"],
        round(public["cost_usd"] * 1e6),
    ):
        raise ValueError("공개 성적표와 원본 결과 불일치")
    elapsed = sorted(r["elapsed_ms"] for r in rows if r["elapsed_ms"] is not None)
    return {
        "id": f"run-{index + 1}",
        "label": public["label"],
        "path": public["path"],
        "model": key["model"],
        "revision": result.get("git_sha"),
        "answerable_asked": asked,
        "answerable_passed": passed,
        "refusal_asked": sum(r["kind"] == "refusal" for r in rows),
        "refusal_passed": sum(r["kind"] == "refusal" and r["passed"] for r in rows),
        "cost_micros": cost,
        "total_tokens": sum(
            (r["prompt_tokens"] or 0) + (r["completion_tokens"] or 0) for r in rows
        ),
        "latency_p50_ms": elapsed[min(int(0.5 * len(elapsed)), len(elapsed) - 1)]
        if elapsed
        else None,
        "latency_p95_ms": elapsed[min(int(0.95 * len(elapsed)), len(elapsed) - 1)]
        if elapsed
        else None,
        "rows": rows,
    }


def check_public(data: dict, root: Path = ROOT) -> None:
    """원본 실행 파일 없이도 공개 사본의 허용 필드·판정·합계를 CI에서 검증한다."""
    if set(data) != {"schema", "synthetic", "evaluation_sha256", "source_sha256", "runs"}:
        raise ValueError("공개 최상위 허용 필드 위반")
    if data["schema"] != "synthetic-execution-records-v1" or data["synthetic"] is not True:
        raise ValueError("합성 기록이 아니다")
    path = root / "apps/dashboard/content/evaluation.json"
    public = read(path)
    if data["evaluation_sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError("현재 평가와 실행 기록의 지문 불일치")
    fixture = read(root / "scripts/fixtures/ask_replay.v1.json")
    if len(data["runs"]) != len(public["series"]["runs"]):
        raise ValueError("공개 회차 수 불일치")
    run_keys = {
        "id",
        "label",
        "path",
        "model",
        "revision",
        "answerable_asked",
        "answerable_passed",
        "refusal_asked",
        "refusal_passed",
        "cost_micros",
        "total_tokens",
        "latency_p50_ms",
        "latency_p95_ms",
        "rows",
    }
    row_keys = {
        "id",
        "query",
        "kind",
        "expected",
        "response_text",
        "status",
        "passed",
        "reason",
        "keyword_hit",
        "refused",
        "cited_wiki",
        "cited_source",
        "fabricated",
        "prompt_tokens",
        "completion_tokens",
        "cost_micros",
        "elapsed_ms",
        "route",
    }
    for index, (run, summary) in enumerate(
        zip(data["runs"], public["series"]["runs"], strict=True)
    ):
        if set(run) != run_keys or any(set(r) != row_keys for r in run["rows"]):
            raise ValueError("공개 실행 허용 필드 위반")
        source_rows = []
        questions = {q["id"]: q for q in fixture["questions"]}
        for r in run["rows"]:
            q = questions[r["id"]]
            if r["query"] != q["query"] or r["expected"] != {
                "any": q.get("expect_any", []),
                "all": q.get("expect_all", []),
            }:
                raise ValueError("질문·기대 표현 불일치")
            source_rows.append(
                {
                    "id": r["id"],
                    "doc": q["doc"],
                    "answer": r["response_text"],
                    "model": run["model"],
                    "status": r["status"],
                    "keyword_hit": r["keyword_hit"],
                    "cited_wiki_count": r["cited_wiki"],
                    "cited_source_count": r["cited_source"],
                    "fabricated_anchor_count": r["fabricated"],
                    "prompt_tokens": r["prompt_tokens"],
                    "completion_tokens": r["completion_tokens"],
                    "cost_micros": r["cost_micros"],
                    "elapsed_ms": r["elapsed_ms"],
                    "route": {"decision": r["route"]},
                }
            )
        rebuilt = export_run(
            {
                "fixed_inputs": {
                    **public["series"]["key"],
                    "answer_prompt_sha256": public["series"]["key"]["prompt_sha256"],
                    "policy_version": public["series"]["key"]["policy_version"],
                },
                "rows": source_rows,
                "git_sha": run["revision"],
            },
            summary,
            fixture,
            public["series"]["key"],
            index,
        )
        if rebuilt != run:
            raise ValueError("공개 문항 판정 또는 집계 불일치")
    if SENSITIVE.search(json.dumps(data, ensure_ascii=False)):
        raise ValueError("공개 기록에 민감 식별자 포함")


def build(root: Path = ROOT) -> dict:
    public_path = root / "apps/dashboard/content/evaluation.json"
    public = read(public_path)
    fixture_path = root / "scripts/fixtures/ask_replay.v1.json"
    fixture = read(fixture_path)
    key = public["series"]["key"]
    if fixture_sha256(fixture) != key["fixture_sha256"]:
        raise ValueError("합성 fixture 지문 불일치")
    if not public["series"]["valid"]:
        raise ValueError("무효 반복 측정은 공개하지 않는다")
    base = root / ".worktrees/reliability-evidence-20261109/runs"
    ablation = read(root / ".worktrees/ablation-evidence-20261108/answer.json")
    condition = next(c for c in ablation["conditions"] if c["condition"] == "bothxbody")
    harness = {**ablation, "rows": condition["rows"]}
    # 하네스 기록은 프롬프트 지문을 최상위에 보존했다.
    harness["fixed_inputs"] = {
        **ablation["fixed_inputs"],
        "model": condition["rows"][0]["model"],
        "answer_prompt_sha256": ablation["answer_prompt_sha256"],
    }
    sources = [read(base / "reliability-1.json"), read(base / "reliability-2.json"), harness]
    if len(public["series"]["runs"]) != len(sources):
        raise ValueError("회차 수 불일치")
    return {
        "schema": "synthetic-execution-records-v1",
        "synthetic": True,
        "evaluation_sha256": hashlib.sha256(public_path.read_bytes()).hexdigest(),
        "source_sha256": [
            hashlib.sha256(json.dumps(s, sort_keys=True).encode()).hexdigest() for s in sources
        ],
        "runs": [
            export_run(s, p, fixture, key, i)
            for i, (s, p) in enumerate(zip(sources, public["series"]["runs"], strict=True))
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out", type=Path)
    group.add_argument("--check", type=Path)
    args = parser.parse_args()
    if args.check:
        check_public(read(args.check))
        print("공개 합성 실행 기록 검증 완료")
    else:
        data = build()
        check_public(data)
        args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("합성 실행 3회 · 90문항 공개 기록 생성 완료")
