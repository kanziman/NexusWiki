#!/usr/bin/env python3
"""루프백 전용 평가 실행기. 저장 답변 재채점 또는 예산을 지정한 실제 모델 재생을 실행한다.

사용: .venv/bin/python scripts/local_evaluation_server.py
유료 실행 준비: 위 명령에 --state <로컬 재생 state.json> --api-url http://127.0.0.1:8031 추가.
상태·원본은 gitignore된 .worktrees/evaluation-dashboard에 보존한다. 토큰은 콘솔에 출력하지 않는다.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import secrets
import threading
import uuid
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import ask_replay as replay
import httpx
from ask_replay import assert_loopback, build_result, keyword_hit
from evaluation_run_export import SENSITIVE
from golden_answer_judge import Conflict, JudgeStore

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STORE = ROOT / ".worktrees/evaluation-dashboard"
FIXTURE = ROOT / "scripts/fixtures/ask_replay.v1.json"


def now():
    return datetime.now(UTC).isoformat()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.chmod(0o600)
    temp.replace(path)


def rescore(result):
    """현재 기대 표현·채점 규칙을 적용한다. 원본 파일은 바꾸지 않는다."""
    sample = read(FIXTURE)
    by_id = {q["id"]: q for q in sample["questions"]}
    rows = []
    for original in result["rows"]:
        row = dict(original)
        q = by_id[row["id"]]
        if q["doc"] == "none":
            row["keyword_hit"] = None
        else:
            answer = row.get("answer") or ""
            row["keyword_hit"] = (
                all(keyword_hit(answer, group) for group in q["expect_all"])
                if q.get("expect_all")
                else keyword_hit(answer, q.get("expect_any", []))
            )
        rows.append(row)
    return build_result(
        label="저장 답변 재채점",
        sha=result.get("git_sha"),
        questions=[by_id[r["id"]] for r in rows],
        rows=rows,
        fixed=result["fixed_inputs"],
        stopped=None,
        path="offline-rescore",
    )


def analysis_run(result, run_id, label, mode):
    """로컬 API도 허용 필드만 반환한다. 인증 정보·워크스페이스 식별자를 복사하지 않는다."""
    questions = {q["id"]: q for q in read(FIXTURE)["questions"]}
    fixed = result["fixed_inputs"]
    conditions = {
        "fixture_sha256": str(fixed.get("fixture_sha256", "")),
        "snapshot_sha256": str(fixed.get("snapshot_sha256", "")),
        "prompt_sha256": str(fixed.get("answer_prompt_sha256", "")),
        "model": str(fixed.get("model", "")),
        "requested_k": str(fixed.get("requested_k", "")),
        "policy_version": ",".join(fixed.get("policy_versions", [])),
    }
    rows = []
    for row in result["rows"]:
        answer = row.get("answer") or ""
        if SENSITIVE.search(answer):
            answer = "민감 식별자가 포함되어 이 답변을 숨겼습니다."
        q = questions[row["id"]]
        verdict = row["verdict"]
        rows.append(
            {
                "id": q["id"],
                "query": q["query"],
                "passed": verdict["pass"],
                "reason": verdict["reason"],
                "cost": row.get("cost_micros"),
                "latency": row.get("elapsed_ms"),
                "answer": answer,
                "failed": row.get("status") in {"error", "not-run"},
                "kind": "refusal" if q["doc"] == "none" else "answerable",
                "expected": "자료에 없는 질문 거절"
                if q["doc"] == "none"
                else " / ".join(q.get("expect_any", [])),
            }
        )
    summary = result["summary"]
    return {
        "id": run_id,
        "label": label,
        "mode": mode,
        "path": "저장 답변 재채점" if mode == "rescore" else "HTTP · SSE",
        "model": conditions["model"],
        "revision": result.get("git_sha"),
        "conditions": conditions,
        "rows": rows,
        "cost": summary.get("cost_micros_total", 0),
        "tokens": summary.get("prompt_tokens_total", 0) + summary.get("completion_tokens_total", 0),
        "p50": summary.get("latency_p50_ms"),
        "p95": summary.get("latency_p95_ms"),
    }


class Store:
    def __init__(self, root, state=None, api="http://127.0.0.1:8031", max_budget=2_000_000):
        self.root, self.state, self.api, self.max_budget = (
            root,
            state,
            assert_loopback(api),
            max_budget,
        )
        root.mkdir(parents=True, exist_ok=True)
        root.chmod(0o700)
        self.lock_file = (root / "server.lock").open("a")
        fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.guard = threading.Lock()
        self.token = secrets.token_urlsafe(32)
        (root / "token").write_text(self.token, encoding="utf-8")
        (root / "token").chmod(0o600)
        if state:
            assert_loopback(read(state)["stack_url"])
        for path in root.glob("job-*.json"):
            job = read(path)
            if job["status"] in {"queued", "running"}:
                checkpoint = root / f"raw-{job['id']}.json"
                if checkpoint.exists():
                    partial = read(checkpoint)
                    job["asked"] = len(partial["rows"])
                    partial["stopped"] = {"reason": "interrupted", "asked": job["asked"]}
                    atomic(checkpoint, partial)
                job.update(
                    status="interrupted", error="실행기 재시작으로 중단됨", finished_at=now()
                )
                atomic(path, job)
        source = ROOT / ".worktrees/reliability-evidence-20261109/runs/reliability-1.json"
        if not list(root.glob("run-*.json")) and source.exists():
            seed = analysis_run(
                read(source), "seed-http-1", "보존된 HTTP 1 · 초기 기준", "imported"
            )
            atomic(root / "run-000-seed.json", seed)
            atomic(root / "baseline.json", {"id": seed["id"]})
        self.judge = JudgeStore(self)

    def snapshot(self):
        runs = [read(path) for path in sorted(self.root.glob("run-*.json"))]
        baseline_path = self.root / "baseline.json"
        baseline = read(baseline_path).get("id") if baseline_path.exists() else None
        jobs = [read(path) for path in self.root.glob("job-*.json")]
        jobs.sort(key=lambda item: item["created_at"], reverse=True)
        ready = False
        if self.state and self.state.exists():
            try:
                response = httpx.get(f"{self.api}/health", timeout=0.5)
                ready = response.status_code == 200
            except (httpx.HTTPError, OSError):
                pass
        return {
            "runs": runs,
            "baseline_id": baseline,
            "jobs": jobs[:30],
            "model_ready": ready,
            "max_budget_micros": self.max_budget,
        }

    def start(self, payload):
        if not isinstance(payload, dict) or set(payload) - {
            "mode",
            "label",
            "budget_micros",
            "limit",
        }:
            raise ValueError("알 수 없는 실행 요청")
        if not isinstance(payload.get("label"), str):
            raise ValueError("실행 이름은 문자열이어야 합니다")
        mode, label = payload.get("mode"), payload.get("label", "").strip()
        if mode not in {"rescore", "model"} or not 1 <= len(label) <= 60:
            raise ValueError("실행 종류와 이름을 확인하세요")
        budget, limit = payload.get("budget_micros"), payload.get("limit", 30)
        if type(limit) is not int or not 1 <= limit <= 30:
            raise ValueError("문항 수는 1~30이어야 합니다")
        if mode == "model" and (
            not self.state or type(budget) is not int or not 200_000 <= budget <= self.max_budget
        ):
            raise ValueError("로컬 재생 설정과 0.20달러 이상 서버 상한 이하 예산이 필요합니다")
        with self.guard:
            if self.judge.busy():
                raise ValueError("진행 중인 실행이 있습니다")
            job_id = uuid.uuid4().hex
            job = {
                "id": job_id,
                "label": label,
                "mode": mode,
                "status": "queued",
                "asked": 0,
                "planned": 30 if mode == "rescore" else limit,
                "budget_micros": budget if mode == "model" else 0,
                "created_at": now(),
                "error": None,
            }
            atomic(self.root / f"job-{job_id}.json", job)
            threading.Thread(target=self.execute, args=(job,), daemon=True).start()
            return job

    def execute(self, job):
        job_path = self.root / f"job-{job['id']}.json"
        job["status"] = "running"
        atomic(job_path, job)
        try:
            if job["mode"] == "rescore":
                source = ROOT / ".worktrees/reliability-evidence-20261109/runs/reliability-1.json"
                result = rescore(read(source))
                result["label"] = job["label"]
                atomic(self.root / f"raw-{job['id']}.json", result)
            else:
                result = self.model_run(job, job_path)
            job["asked"] = len(result["rows"])
            if (
                result.get("stopped")
                or len(result["rows"]) != job["planned"]
                or (
                    job["mode"] == "model"
                    and any(row.get("cost_micros") is None for row in result["rows"])
                )
                or any(
                    row.get("status") not in {"resolved", "no-evidence", "fallback"}
                    for row in result["rows"]
                )
            ):
                job["status"] = "partial"
                job["error"] = "일부 문항만 실행됐습니다. 완전한 실행만 비교 후보에 추가합니다."
            else:
                run = analysis_run(result, job["id"], job["label"], job["mode"])
                atomic(
                    self.root / f"run-{job['created_at'].replace(':', '-')}-{job['id']}.json", run
                )
                if not (self.root / "baseline.json").exists():
                    atomic(self.root / "baseline.json", {"id": job["id"]})
                job["status"] = "completed"
        except Exception:
            job.update(
                status="failed", error="실행하지 못했습니다. 로컬 설정과 실행 로그를 확인하세요."
            )
        job["finished_at"] = now()
        atomic(job_path, job)

    def model_run(self, job, job_path):
        state, sample = read(self.state), read(FIXTURE)
        stack = assert_loopback(state["stack_url"])
        questions = replay.select_questions(sample, state, job["planned"])
        job["planned"] = len(questions)
        largest = 200_000

        def before(spent, last):
            nonlocal largest
            if last and last.get("cost_micros") is None:
                return "unknown_cost"
            if last:
                largest = max(largest, last.get("cost_micros") or 0)
            return "spend_cap" if spent + largest > job["budget_micros"] else None

        completed = []

        def after(spent, last):
            completed.append(last)
            job["asked"] += 1
            job["spent_micros"] = spent
            checkpoint = build_result(
                label=job["label"],
                sha=sha,
                questions=questions,
                rows=list(completed),
                fixed=fixed,
                stopped="running",
            )
            atomic(self.root / f"raw-{job['id']}.json", checkpoint)
            atomic(job_path, job)
            return "unknown_cost" if last.get("cost_micros") is None else None

        with httpx.Client(timeout=180) as client:
            token = replay._login(client, stack, state)
            fixed = replay.collect_fixed_inputs(client, stack, state["workspace_id"], token, sample)
            sha = replay._api_sha(client, self.api)
            rows, stopped = replay.run_replay(
                client,
                self.api,
                stack,
                state["workspace_id"],
                token,
                questions,
                before_question=before,
                after_question=after,
            )
        result = build_result(
            label=job["label"],
            sha=sha,
            questions=questions,
            rows=rows,
            fixed=fixed,
            stopped=stopped,
        )
        atomic(self.root / f"raw-{job['id']}.json", result)
        return result

    def baseline(self, run_id):
        if run_id not in {read(p)["id"] for p in self.root.glob("run-*.json")}:
            raise ValueError("완료된 실행만 기준으로 지정할 수 있습니다")
        atomic(self.root / "baseline.json", {"id": run_id})


def handler(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def handle_request(self):
            if not secrets.compare_digest(self.headers.get("X-Evaluation-Token", ""), store.token):
                self.reply(403, {"error": "로컬 실행 인증이 필요합니다"})
                return
            try:
                if self.command == "GET" and self.path == "/status":
                    self.reply(200, store.snapshot())
                    return
                if self.command == "GET" and self.path == "/judge/status":
                    self.reply(200, store.judge.snapshot())
                    return
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 4096:
                    raise ValueError("요청 크기를 확인하세요")
                payload = json.loads(self.rfile.read(length))
                if self.command == "POST" and self.path == "/jobs":
                    self.reply(202, store.start(payload))
                elif self.command == "POST" and self.path == "/baseline":
                    store.baseline(payload.get("run_id"))
                    self.reply(200, {"saved": True})
                elif self.command == "POST" and self.path == "/judge/jobs":
                    self.reply(202, store.judge.start(payload))
                elif self.command == "POST" and self.path == "/judge/reviews":
                    self.reply(200, store.judge.review(payload))
                else:
                    self.reply(404, {"error": "없는 경로입니다"})
            except Conflict as exc:
                self.reply(409, {"error": str(exc)})
            except (ValueError, TypeError, KeyError):
                self.reply(
                    400,
                    {"error": "요청·실행 설정과 진행 중인 실행을 확인하세요."},
                )

        do_GET = handle_request
        do_POST = handle_request

        def reply(self, status, value):
            body = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--api-url", default="http://127.0.0.1:8031")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    args = parser.parse_args()
    store = Store(args.store, args.state, args.api_url)
    server = ThreadingHTTPServer(("127.0.0.1", 54411), handler(store))
    print("로컬 평가 실행기: 127.0.0.1:54411 (대시보드에서만 실행 요청)", flush=True)
    server.serve_forever()
