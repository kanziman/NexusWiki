#!/usr/bin/env python3
"""합성 재검색 평가의 조건과 실제 턴 결과를 변경 불가능한 실행 파일로 기록한다."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import ask_replay as replay
import httpx

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "scripts/fixtures/evidence_research.v1.json"
# 사용자 비용 절감 요청으로 완료된 첫 쌍만 사용한다. 추가 유료 반복은 실행하지 않는다.
EVALUATION_PAIRS = (1,)
# 재검색 실험의 원래 채택 기준(2026-11-09 design.md D4)에서 실제로 판정을 낸 값이다.
# 실험 기록의 원래 기준 세트가 이 값을 옮겨 쓰며, 둘이 어긋나면 테스트가 실패한다.
COST_LIMIT_RATIO = 1.5
P95_LIMIT_MS = 15000


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def execution_sha256(root: Path = ROOT) -> str:
    """판단 프롬프트·출력 상한을 포함한 API·워커·공유 코드의 실행 지문이다."""
    sources = {}
    for directory in ("apps/api/src", "apps/worker/src", "packages/core/src"):
        for path in sorted((root / directory).rglob("*.py")):
            sources[str(path.relative_to(root))] = path.read_text()
    if not sources:
        raise ValueError("실행 코드를 찾을 수 없다")
    return digest(sources)


def snapshot(client: httpx.Client, stack: str, workspace: str) -> dict:
    tables = {}
    for table in ("raw_sources", "source_chunks", "wiki_pages", "wiki_embeddings", "wiki_links"):
        rows = replay._select(
            client, stack, table, {"workspace_id": f"eq.{workspace}", "select": "*"}
        )
        if len(rows) >= 1000:
            raise SystemExit("스냅샷 페이지 상한 도달: 비교를 중단한다")
        tables[table] = sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))
    response = client.get(
        f"{stack}/rest/v1/prompt_templates",
        headers=replay._service_headers(),
        params={"select": "*", "or": f"(workspace_id.is.null,workspace_id.eq.{workspace})"},
    )
    response.raise_for_status()
    prompts = sorted(response.json(), key=lambda row: row["id"])
    return {"corpus": digest(tables), "prompts": digest(prompts), "tables": tables}


def _is_measurement_failure(row: dict) -> bool:
    return (
        row["status"] not in {"resolved", "no-evidence", "fallback"}
        or bool((row.get("retrieval") or {}).get("missing_channels"))
        or bool((row.get("research") or {}).get("missing_channels"))
        or bool(row.get("usage_incomplete"))
    )


def run(args: argparse.Namespace) -> None:
    out = Path(args.out)
    if out.exists():
        raise SystemExit("기존 실행 기록을 덮어쓸 수 없다")
    state = json.loads(Path(args.state).read_text())
    stack, api = replay.assert_loopback(state["stack_url"]), replay.assert_loopback(args.api)
    sample = replay._load_sample(SAMPLE)
    runtime = json.loads(Path(args.runtime_manifest).read_text())
    if runtime.get("model") != args.model:
        raise SystemExit("실제 서버 설정의 모델과 평가 모델이 다르다")
    execution = execution_sha256()
    if runtime.get("execution_sha256") != execution:
        raise SystemExit("서버 시작 시 실행 코드 지문이 없거나 현재 코드와 다르다")
    policy_digest = digest(
        {
            name: (ROOT / "packages/core/src/nexuswiki_core" / name).read_text()
            for name in ("retrieval_policy.py", "rrf.py", "llm_policy.py")
        }
    )
    with httpx.Client(timeout=180) as client:
        token = replay._login(client, stack, state)
        frozen = snapshot(client, stack, state["workspace_id"])
        conditions = {
            "corpus": frozen["corpus"],
            "prompts": frozen["prompts"],
            "fixture": digest(sample),
            "model": args.model,
            "settings": digest(runtime),
            "policy": policy_digest,
            "execution": execution,
        }
        rows = []
        if getattr(args, "resume_from", None):
            prior = json.loads(Path(args.resume_from).read_text())
            if (
                prior.get("mode") != args.mode
                or prior.get("pair") != args.pair
                or prior.get("conditions") != conditions
            ):
                raise SystemExit("재개 원본의 비교 조건이 현재 실행 조건과 다르다")
            rows = [r for r in prior.get("rows", []) if not _is_measurement_failure(r)]
        completed_ids = {r["id"] for r in rows}
        aborted_reason = None
        for question in sample["questions"]:
            if question["id"] in completed_ids:
                continue
            row = replay._ask_once(
                client,
                api,
                stack,
                state["workspace_id"],
                token,
                question,
                include_embeddings=True,
            )
            if _is_measurement_failure(row):
                time.sleep(2)
                row = replay._ask_once(
                    client,
                    api,
                    stack,
                    state["workspace_id"],
                    token,
                    question,
                    include_embeddings=True,
                )
            row["type"] = question.get("type", "regression")
            observed = row.get("research") or {}
            if observed.get("enabled") is not (args.mode == "on"):
                raise SystemExit("실제 API 모드가 실행 label과 다르다")
            if row.get("model") and row["model"] != args.model:
                raise SystemExit("실제 답변 모델이 고정 모델과 다르다")
            row["verdict"] = replay.verdict(row)
            rows.append(row)
            print(row["id"], row["status"], row["verdict"], flush=True)
            if _is_measurement_failure(row):
                aborted_reason = "measurement_failure"
                break
        after = snapshot(client, stack, state["workspace_id"])
        if execution_sha256() != execution:
            aborted_reason = "execution_changed"
        if any(frozen[key] != after[key] for key in ("corpus", "prompts")):
            aborted_reason = "conditions_changed"
    record = {
        "version": 1,
        "mode": args.mode,
        "pair": args.pair,
        "aborted_reason": aborted_reason,
        "planned_questions": len(sample["questions"]),
        "created_at": datetime.now(UTC).isoformat(),
        "revision": subprocess.check_output(  # noqa: S603 - 고정 git 명령만 실행한다.
            [shutil.which("git") or "/usr/bin/git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "conditions": conditions,
        "rows": rows,
        "summary": replay.summarize(rows),
        "snapshot": frozen["tables"],
    }
    with out.open("x") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    if aborted_reason:
        raise SystemExit("측정 장애를 기록하고 나머지 유료 평가를 중단했다")


def origins(record: dict, evidence: list[dict] | None) -> set[str] | None:
    if evidence is None:
        return None
    tables = record["snapshot"]
    mapping = {}
    for chunk in tables["source_chunks"]:
        mapping[("source", str(chunk["id"]))] = {str(chunk["raw_source_id"])}
    for page in tables["wiki_pages"]:
        mapping[("wiki", str(page["id"]))] = {str(x) for x in page["sources"]}
    hashed = {
        (kind, hashlib.sha256(key.encode()).hexdigest()): value
        for (kind, key), value in mapping.items()
    }
    found = set()
    for item in evidence:
        value = (
            hashed.get((item["kind"], item.get("document_hash")))
            if "document_hash" in item
            else mapping.get((item["kind"], item.get("document_id")))
        )
        if value is None:
            return None
        found |= value
    return found


def public_summary(rows: list[dict]) -> dict:
    def percentile(key, fraction):
        values = sorted(row[key] for row in rows if row.get(key) is not None)
        return values[min(int(len(values) * fraction), len(values) - 1)] if values else None

    return {
        "questions": len(rows),
        "passed": sum(row["verdict"]["pass"] for row in rows),
        "regression_passed": sum(
            row["verdict"]["pass"] for row in rows if row["id"].startswith("q")
        ),
        "cost_micros": sum(row.get("cost_micros") or 0 for row in rows),
        "prompt_tokens": sum(row.get("prompt_tokens") or 0 for row in rows),
        "completion_tokens": sum(row.get("completion_tokens") or 0 for row in rows),
        "fabricated": sum(row.get("fabricated_anchor_count") or 0 for row in rows),
        "latency_p50": percentile("elapsed_ms", 0.5),
        "latency_p95": percentile("elapsed_ms", 0.95),
        "first_token_p50": percentile("first_delta_ms", 0.5),
        "first_token_p95": percentile("first_delta_ms", 0.95),
    }


def build_public(records: list[dict]) -> dict:
    """합성 fixture의 허용 필드만 선택한다. private snapshot·응답은 공개하지 않는다."""
    sample = replay._load_sample(SAMPLE)
    questions = {q["id"]: q for q in sample["questions"]}
    grouped = {(r["pair"], r["mode"]): r for r in records}
    conditions_match = bool(records) and len({digest(r["conditions"]) for r in records}) == 1
    conditions_match = conditions_match and all(
        r["conditions"].get("fixture") == digest(sample)
        and all(
            r["conditions"].get(key)
            for key in ("corpus", "prompts", "model", "policy", "settings", "execution")
        )
        for r in records
    )
    valid = conditions_match and set(grouped) == {
        (p, m) for p in EVALUATION_PAIRS for m in ("off", "on")
    }
    valid = (
        valid
        and len(records) == len(EVALUATION_PAIRS) * 2
        and all(
            len(r["rows"]) == len(questions)
            and {row["id"] for row in r["rows"]} == set(questions)
            and not r.get("aborted_reason")
            for r in records
        )
    )
    rows, failures = [], 0
    for pair in EVALUATION_PAIRS:
        off, on = grouped.get((pair, "off")), grouped.get((pair, "on"))
        if off is None or on is None:
            valid = False
            continue
        before = {row["id"]: row for row in off["rows"]}
        raw_by_title = {r["title"]: str(r["id"]) for r in on["snapshot"]["raw_sources"]}
        docs = {d["id"]: raw_by_title.get(d["title"]) for d in sample["documents"]}
        for right in on["rows"]:
            question, left = questions[right["id"]], before.get(right["id"])
            if left is None:
                valid = False
                continue
            initial = origins(on, (right.get("research") or {}).get("initial_evidence"))
            final = origins(on, (right.get("research") or {}).get("final_evidence"))
            expected = {docs.get(d) for d in question["doc"].split("+")}
            measurement_failed = (
                right["status"] not in {"resolved", "no-evidence", "fallback"}
                or left["status"] not in {"resolved", "no-evidence", "fallback"}
                or bool((right.get("retrieval") or {}).get("missing_channels"))
                or bool((left.get("retrieval") or {}).get("missing_channels"))
                or bool((right.get("research") or {}).get("missing_channels"))
                or bool(right.get("usage_incomplete"))
                or bool(left.get("usage_incomplete"))
            )
            targeted = question.get("type") in {"comparison", "mismatch"}
            if targeted and (initial is None or final is None or None in expected):
                measurement_failed = True
            failures += measurement_failed
            eligible = targeted and not measurement_failed and not expected <= (initial or set())
            recovered = eligible and expected <= (final or set())
            answer_recovered = recovered and right["verdict"]["pass"]
            rows.append(
                {
                    "id": right["id"],
                    "pair": pair,
                    "query": question["query"],
                    "type": question.get("type", "regression"),
                    "before_pass": left["verdict"]["pass"],
                    "after_pass": right["verdict"]["pass"],
                    "before_reason": left["verdict"]["reason"],
                    "after_reason": right["verdict"]["reason"],
                    "eligible": eligible,
                    "evidence_recovered": recovered,
                    "answer_recovered": answer_recovered,
                    "measurement_failed": measurement_failed,
                    "initial_all_found": expected <= initial
                    if targeted and initial is not None
                    else None,
                    "final_all_found": expected <= final
                    if targeted and final is not None
                    else None,
                    "before_ms": left.get("elapsed_ms"),
                    "after_ms": right.get("elapsed_ms"),
                    "before_cost": left.get("cost_micros"),
                    "after_cost": right.get("cost_micros"),
                    "tool_calls": (right.get("research") or {}).get("executed_calls", 0),
                    "research_status": (right.get("research") or {}).get("status"),
                }
            )
    sides = {
        mode: public_summary([row for r in records if r["mode"] == mode for row in r["rows"]])
        for mode in ("off", "on")
    }
    off, on = sides["off"], sides["on"]
    checks = {
        "conditions_match": conditions_match,
        "measurements_complete": failures == 0,
        "answer_recovered": any(row["answer_recovered"] for row in rows),
        "total_pass_improved": on["passed"] > off["passed"],
        "no_regression": on["regression_passed"] >= off["regression_passed"],
        "no_fabrication_increase": on["fabricated"] <= off["fabricated"],
        "cost_within_limit": bool(off["cost_micros"])
        and on["cost_micros"] <= off["cost_micros"] * COST_LIMIT_RATIO,
        "latency_within_limit": off["latency_p95"] is not None
        and on["latency_p95"] is not None
        and on["latency_p95"] - off["latency_p95"] <= P95_LIMIT_MS,
    }
    eligible = sum(row["eligible"] for row in rows)
    return {
        "version": 1,
        "synthetic": True,
        "valid": valid and failures == 0,
        "conditions_match": conditions_match,
        "adopted": valid and failures == 0 and all(checks.values()),
        "checks": checks,
        "conditions": {
            key: records[0]["conditions"].get(key)
            for key in ("corpus", "prompts", "fixture", "model", "policy", "settings", "execution")
        }
        if records
        else {},
        "runs": [
            {
                "mode": r["mode"],
                "pair": r["pair"],
                "revision": r["revision"],
                "source_state": "커밋 전 작업트리 · revision은 기준 HEAD",
                "created_at": r["created_at"],
            }
            for r in records
        ],
        "summary": sides,
        "rows": rows,
        "measurement_failures": failures,
        "recovery": {
            "eligible": eligible,
            "evidence": sum(r["evidence_recovered"] for r in rows),
            "answer": sum(r["answer_recovered"] for r in rows),
            "rate": sum(r["answer_recovered"] for r in rows) / eligible if eligible else None,
        },
        "method": "합성 42문항(기존 30·비교형 6·표현 불일치 6), OFF/ON 1쌍. "
        "같은 수집 결과를 재사용. 복구율은 첫 문맥에 기대 문서 전체가 없었던 전용 문항 중 "
        "최종 문맥·필수 사실·이중 인용 통과 비율. "
        "사용자 비용 절감 요청으로 완료된 첫 쌍만 사용한다. 반복 안정성은 미측정이며 "
        "운영 품질이나 통계적 우월성을 의미하지 않는다. "
        "위키 정답은 페이지가 기대 원문에서 컴파일됐는지로 판정하므로 "
        "특정 문장 포함을 보장하지 않는다.",
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "export":
        folder, target = Path(sys.argv[2]), Path(sys.argv[3])
        records = [
            json.loads((folder / f"{mode}-{pair}.json").read_text())
            for pair in EVALUATION_PAIRS
            for mode in ("off", "on")
        ]
        with target.open("x") as stream:
            json.dump(build_public(records), stream, ensure_ascii=False, indent=2)
        raise SystemExit(0)
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--mode", choices=["off", "on"], required=True)
    parser.add_argument("--pair", type=int, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--runtime-manifest", required=True)
    parser.add_argument("--resume-from")
    parser.add_argument("--api", default="http://127.0.0.1:8031")
    run(parser.parse_args())
