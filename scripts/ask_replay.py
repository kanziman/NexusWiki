#!/usr/bin/env python3
"""합성 샘플 문서와 고정 질문으로 Ask를 재생해 통제 전후를 비교한다.

쓰는 순서:
    # 1. 샘플 문서를 수집한다. 워크스페이스 식별자와 토큰은 state 파일에 남는다.
    uv run python scripts/ask_replay.py seed --state state.json

    # 2. 비교할 코드로 API와 워커를 띄운 뒤 각각 재생한다. 수집은 다시 하지 않는다.
    uv run python scripts/ask_replay.py ask --state state.json --label before --out before.json
    uv run python scripts/ask_replay.py ask --state state.json --label after --out after.json

    # 3. 표로 비교한다.
    uv run python scripts/ask_replay.py compare before.json after.json

⚠️ 로컬 스택 전용이다. `.env`의 SUPABASE_URL은 클라우드를 가리키므로 읽지 않으며,
   루프백이 아닌 주소는 거부한다. service_role 키를 쓰는 조회가 운영으로 나가면 안 된다.
⚠️ 이 값은 합성 문서로 잰 샘플 수치다. 운영 트래픽의 효과로 인용하면 안 된다.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import httpx

_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = _ROOT / "scripts" / "fixtures" / "ask_replay.v1.json"

# Supabase CLI가 모든 로컬 스택에 동일하게 발급하는 공개 데모 키다 (apps/api/tests/conftest.py).
LOCAL_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9"
    ".CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
)
LOCAL_SERVICE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0"
    ".EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
)

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_TERMINAL_JOB_STATES = frozenset({"succeeded", "dead", "failed", "canceled"})
_FAILED_JOB_STATES = frozenset({"dead", "failed", "canceled"})


def assert_loopback(url: str) -> str:
    """루프백이 아니면 멈춘다. 운영 프로젝트에 사용자와 잡을 만드는 사고를 막는다."""
    host = urlparse(url).hostname
    if host not in _LOOPBACK_HOSTS:
        raise SystemExit(f"ask_replay: 루프백이 아닌 주소라 중단한다: {url}")
    return url.rstrip("/")


def parse_sse(lines: Iterable[str]) -> list[tuple[str, dict[str, Any]]]:
    """`event:`/`data:` 줄을 이벤트 목록으로 묶는다. 깨진 프레임은 예외로 드러낸다."""
    events: list[tuple[str, dict[str, Any]]] = []
    name: str | None = None
    data: list[str] = []
    for raw in [*lines, ""]:
        line = raw.rstrip("\r\n")
        if line.startswith("event:"):
            name = line[len("event:") :].strip()
        elif line.startswith("data:"):
            data.append(line[len("data:") :].strip())
        elif not line and name is not None:
            events.append((name, json.loads("\n".join(data)) if data else {}))
            name, data = None, []
    return events


def answer_text(events: list[tuple[str, dict[str, Any]]]) -> str:
    """최종 답변. 프런트와 같게 `citations.text`가 있으면 누적 delta를 대체한다."""
    deltas: list[str] = []
    final: str | None = None
    for name, payload in events:
        if name == "delta":
            deltas.append(str(payload.get("text") or ""))
        elif name == "citations" and isinstance(payload.get("text"), str):
            final = payload["text"]
    return final if final is not None else "".join(deltas)


def keyword_hit(answer: str, expect_any: list[str]) -> bool | None:
    """기대 사실이 답변에 있는지. 공백 차이만 무시한다. 기대값이 없는 질문은 None이다."""
    if not expect_any:
        return None
    normalized = "".join(answer.split())
    return any("".join(item.split()) in normalized for item in expect_any)


def _mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]


def _ratio(flags: list[bool]) -> float | None:
    return sum(flags) / len(flags) if flags else None


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """질문별 결과를 집계한다. 인용 지표는 LLM이 답한 턴만 본다.

    근거 없음으로 단락한 턴을 넣으면 인용률이 0으로 희석되어 전후 비교가 왜곡된다.
    """
    llm_rows = [row for row in rows if row.get("prompt_tokens") is not None]
    prompts = [float(row["prompt_tokens"]) for row in llm_rows]
    answerable = [row for row in rows if row.get("keyword_hit") is not None]
    budgets = [row["budget"] for row in rows if isinstance(row.get("budget"), dict)]
    statuses: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status"))
        statuses[status] = statuses.get(status, 0) + 1
    return {
        "questions": len(rows),
        "llm_turns": len(llm_rows),
        "statuses": statuses,
        "prompt_tokens_mean": _mean(prompts),
        "prompt_tokens_p95": _percentile(prompts, 0.95),
        "prompt_tokens_max": max(prompts) if prompts else None,
        "completion_tokens_mean": _mean([float(r["completion_tokens"] or 0) for r in llm_rows]),
        "cost_micros_total": sum(int(row.get("cost_micros") or 0) for row in rows),
        "dual_citation_rate_mean": _mean(
            [
                float(r["dual_citation_rate"])
                for r in llm_rows
                if r.get("dual_citation_rate") is not None
            ]
        ),
        "unsourced_sentence_ratio_mean": _mean(
            [
                float(r["unsourced_sentence_ratio"])
                for r in llm_rows
                if r.get("unsourced_sentence_ratio") is not None
            ]
        ),
        "fabricated_anchors_total": sum(int(r.get("fabricated_anchor_count") or 0) for r in rows),
        "keyword_recall": _ratio([bool(row["keyword_hit"]) for row in answerable]),
        "budget_reported_turns": len(budgets),
        "budget_truncated_turns": sum(1 for b in budgets if b.get("truncated")),
        "budget_dropped_blocks_total": sum(int(b.get("dropped_blocks") or 0) for b in budgets),
    }


_COMPARE_ROWS: tuple[tuple[str, str], ...] = (
    ("prompt_tokens_mean", "평균 입력 토큰"),
    ("prompt_tokens_p95", "p95 입력 토큰"),
    ("prompt_tokens_max", "최대 입력 토큰"),
    ("completion_tokens_mean", "평균 출력 토큰"),
    ("cost_micros_total", "총 비용 (USD micros)"),
    ("dual_citation_rate_mean", "평균 이중 인용률"),
    ("unsourced_sentence_ratio_mean", "평균 무근거 문장 비율"),
    ("fabricated_anchors_total", "위조 앵커 합계"),
    ("keyword_recall", "기대 사실 포함률"),
    ("budget_truncated_turns", "예산 절단 턴"),
    ("budget_dropped_blocks_total", "예산 제외 블록"),
)


def _format(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:,.3f}" if abs(value) < 10 else f"{value:,.0f}"
    return f"{value:,}" if isinstance(value, int) else str(value)


def compare_table(before: dict[str, Any], after: dict[str, Any]) -> str:
    """같은 질문만 비교한 Markdown 표. 한쪽에만 있는 질문은 평균을 왜곡하므로 뺀다."""
    after_ids = {row["id"] for row in after["rows"]}
    common = [row["id"] for row in before["rows"] if row["id"] in after_ids]
    keep = set(common)
    left = summarize([row for row in before["rows"] if row["id"] in keep])
    right = summarize([row for row in after["rows"] if row["id"] in keep])
    lines = [
        f"합성 샘플 문항 {len(common)}개 기준이며 운영 트래픽 수치가 아니다.",
        f"`{before['label']}`: {before.get('git_sha') or '알 수 없음'} / "
        f"`{after['label']}`: {after.get('git_sha') or '알 수 없음'}",
        "",
        f"| 지표 | {before['label']} | {after['label']} | 변화 |",
        "| --- | --- | --- | --- |",
    ]
    for key, label in _COMPARE_ROWS:
        a, b = left.get(key), right.get(key)
        change = "-"
        if isinstance(a, int | float) and isinstance(b, int | float) and a:
            change = f"{(b - a) / a * 100:+.1f}%"
        lines.append(f"| {label} | {_format(a)} | {_format(b)} | {change} |")
    return "\n".join(lines)


def _service_headers() -> dict[str, str]:
    return {"apikey": LOCAL_SERVICE_KEY, "Authorization": f"Bearer {LOCAL_SERVICE_KEY}"}


def _select(
    client: httpx.Client,
    stack: str,
    table: str,
    params: dict[str, str],
    *,
    token: str | None = None,
) -> list[dict[str, Any]]:
    """집계용 조회. `token`이 있으면 요청자 JWT로, 없으면 service_role로 읽는다.

    ⚠️ service_role은 BYPASSRLS이므로 호출부가 workspace_id를 반드시 건다. `ask_messages`는
    service_role 권한이 없고 작성자 RLS 아래에 있어 `token`을 넘겨야 한다.
    """
    if "workspace_id" not in params:
        raise ValueError("workspace_id 필터가 없는 조회는 허용하지 않는다")
    headers = (
        {"apikey": LOCAL_ANON_KEY, "Authorization": f"Bearer {token}"}
        if token
        else _service_headers()
    )
    response = client.get(f"{stack}/rest/v1/{table}", headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def _load_sample(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _actor(client: httpx.Client, stack: str) -> dict[str, str]:
    """일회용 사용자와 워크스페이스를 만든다. 워크스페이스는 요청자 JWT로 만든다."""
    tag = uuid4().hex[:12]
    email = f"ask-replay-{tag}@example.com"
    credential = uuid4().hex
    created = client.post(
        f"{stack}/auth/v1/admin/users",
        headers=_service_headers(),
        json={"email": email, "password": credential, "email_confirm": True},
    )
    created.raise_for_status()
    user_id = created.json()["id"]
    token = client.post(
        f"{stack}/auth/v1/token",
        params={"grant_type": "password"},
        headers={"apikey": LOCAL_ANON_KEY},
        json={"email": email, "password": credential},
    )
    token.raise_for_status()
    access_token = token.json()["access_token"]
    workspace = client.post(
        f"{stack}/rest/v1/workspaces",
        headers={
            "apikey": LOCAL_ANON_KEY,
            "Authorization": f"Bearer {access_token}",
            "Prefer": "return=representation",
        },
        json={"name": f"ask-replay-{tag}", "slug": f"ask-replay-{tag}", "owner_id": user_id},
    )
    workspace.raise_for_status()
    return {
        "email": email,
        "credential": credential,
        "user_id": user_id,
        "workspace_id": workspace.json()[0]["id"],
    }


def _login(client: httpx.Client, stack: str, state: dict[str, Any]) -> str:
    """토큰은 재생 사이에 만료될 수 있으므로 저장하지 않고 매번 받는다."""
    response = client.post(
        f"{stack}/auth/v1/token",
        params={"grant_type": "password"},
        headers={"apikey": LOCAL_ANON_KEY},
        json={"email": state["email"], "password": state["credential"]},
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _wait_for_jobs(
    client: httpx.Client, stack: str, workspace_id: str, timeout: float
) -> list[dict[str, Any]]:
    """체인 전체가 끝날 때까지 기다린다. 실패 잡을 조용히 넘기면 샘플이 비어 수치가 왜곡된다."""
    deadline = time.monotonic() + timeout
    while True:
        jobs = _select(
            client,
            stack,
            "jobs",
            {"workspace_id": f"eq.{workspace_id}", "select": "type,status,last_error"},
        )
        states = {job["status"] for job in jobs}
        if states & _FAILED_JOB_STATES:
            failed = [job for job in jobs if job["status"] in _FAILED_JOB_STATES]
            raise SystemExit(f"ask_replay: 잡이 실패했다: {json.dumps(failed, ensure_ascii=False)}")
        if jobs and states <= _TERMINAL_JOB_STATES:
            return jobs
        if time.monotonic() > deadline:
            raise SystemExit(
                f"ask_replay: {timeout:.0f}초 안에 체인이 끝나지 않았다: {sorted(states)}"
            )
        time.sleep(3)


def _usage_total(client: httpx.Client, stack: str, workspace_id: str) -> int:
    rows = _select(
        client,
        stack,
        "usage_events",
        {"workspace_id": f"eq.{workspace_id}", "select": "cost_micros"},
    )
    return sum(int(row.get("cost_micros") or 0) for row in rows)


def cmd_seed(args: argparse.Namespace) -> int:
    stack = assert_loopback(args.stack_url)
    api = assert_loopback(args.api_url)
    sample = _load_sample(Path(args.sample))
    documents = sample["documents"][: args.limit_docs] if args.limit_docs else sample["documents"]
    with httpx.Client(timeout=60) as client:
        state = {
            **_actor(client, stack),
            "stack_url": stack,
            "documents": [d["id"] for d in documents],
        }
        Path(args.state).write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        token = _login(client, stack, state)
        for document in documents:
            response = client.post(
                f"{api}/workspaces/{state['workspace_id']}/sources/text",
                headers={"Authorization": f"Bearer {token}"},
                json={"title": document["title"], "text": document["text"], "source_type": "text"},
            )
            if response.status_code != 202:
                raise SystemExit(
                    f"ask_replay: 수집 실패 {document['id']} "
                    f"{response.status_code}: {response.text[:300]}"
                )
            print(f"ask_replay: 수집 등록 {document['id']}")
        jobs = _wait_for_jobs(client, stack, state["workspace_id"], args.job_timeout)
        pages = _select(
            client,
            stack,
            "wiki_pages",
            {"workspace_id": f"eq.{state['workspace_id']}", "select": "slug"},
        )
        spent = _usage_total(client, stack, state["workspace_id"])
    print(f"ask_replay: 잡 {len(jobs)}개 완료, 위키 {len(pages)}쪽, 수집 비용 {spent} micros")
    if not pages:
        raise SystemExit("ask_replay: 위키가 하나도 없어 이중 인용을 잴 수 없다")
    return 0


def _ask_once(
    client: httpx.Client,
    api: str,
    stack: str,
    workspace_id: str,
    token: str,
    question: dict[str, Any],
) -> dict[str, Any]:
    turn_id = str(uuid4())
    started = time.monotonic()
    with client.stream(
        "POST",
        f"{api}/workspaces/{workspace_id}/ask",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": question["query"], "client_turn_id": turn_id},
    ) as response:
        if response.status_code != 200:
            response.read()
            return {
                "id": question["id"],
                "status": f"http_{response.status_code}",
                "error": response.text[:300],
                "prompt_tokens": None,
            }
        events = parse_sse(response.iter_lines())
    elapsed_ms = round((time.monotonic() - started) * 1000)
    answer = answer_text(events)
    citations = next((payload for name, payload in reversed(events) if name == "citations"), {})
    # 마지막 프레임이 나간 뒤에 저장이 끝날 수 있어 잠시 기다린다.
    message: dict[str, Any] = {}
    for _ in range(10):
        rows = _select(
            client,
            stack,
            "ask_messages",
            {
                "workspace_id": f"eq.{workspace_id}",
                "client_turn_id": f"eq.{turn_id}",
                "select": "status,trace_id,control_report",
            },
            token=token,
        )
        if rows:
            message = rows[0]
            break
        time.sleep(0.5)
    usage: list[dict[str, Any]] = []
    if message.get("trace_id"):
        usage = _select(
            client,
            stack,
            "usage_events",
            {
                "workspace_id": f"eq.{workspace_id}",
                "trace_id": f"eq.{message['trace_id']}",
                "kind": "neq.embedding",
                "select": "prompt_tokens,completion_tokens,cost_micros",
            },
        )
    report = message.get("control_report") or {}
    return {
        "id": question["id"],
        "doc": question.get("doc"),
        "status": message.get("status") or "unknown",
        "elapsed_ms": elapsed_ms,
        "prompt_tokens": sum(int(u.get("prompt_tokens") or 0) for u in usage) if usage else None,
        "completion_tokens": sum(int(u.get("completion_tokens") or 0) for u in usage)
        if usage
        else None,
        "cost_micros": sum(int(u.get("cost_micros") or 0) for u in usage),
        "dual_citation_rate": citations.get("dual_citation_rate"),
        "unsourced_sentence_ratio": citations.get("unsourced_sentence_ratio"),
        "fabricated_anchor_count": citations.get("fabricated_anchor_count"),
        "cited_anchor_count": citations.get("cited_anchor_count"),
        "keyword_hit": keyword_hit(answer, list(question.get("expect_any") or [])),
        "budget": report.get("budget"),
        "route": report.get("route"),
        "answer": answer,
    }


def _api_sha(client: httpx.Client, api: str) -> str | None:
    try:
        return client.get(f"{api}/health").json().get("git_sha")
    except (httpx.HTTPError, ValueError):
        return None


def cmd_ask(args: argparse.Namespace) -> int:
    api = assert_loopback(args.api_url)
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    stack = assert_loopback(state["stack_url"])
    sample = _load_sample(Path(args.sample))
    seeded = set(state["documents"])
    # 수집하지 않은 문서를 묻는 질문은 기대 사실 포함률을 깎아 비교를 흐린다.
    questions = [
        q
        for q in sample["questions"]
        if q.get("doc") == "none" or set(str(q.get("doc")).split("+")) <= seeded
    ]
    if args.limit:
        questions = questions[: args.limit]
    rows: list[dict[str, Any]] = []
    spent = 0
    with httpx.Client(timeout=180) as client:
        token = _login(client, stack, state)
        sha = _api_sha(client, api)
        for question in questions:
            row = _ask_once(client, api, stack, state["workspace_id"], token, question)
            rows.append(row)
            spent += int(row.get("cost_micros") or 0)
            print(
                f"ask_replay: {row['id']} {row['status']} prompt={row.get('prompt_tokens')} "
                f"hit={row.get('keyword_hit')} 누적={spent} micros"
            )
            if spent > args.max_spend_micros:
                print(f"ask_replay: 지출 상한 {args.max_spend_micros} micros를 넘어 중단한다")
                break
    result = {
        "label": args.label,
        "git_sha": sha,
        "planned_questions": len(questions),
        "rows": rows,
        "summary": summarize(rows),
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0 if len(rows) == len(questions) else 1


def cmd_compare(args: argparse.Namespace) -> int:
    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after).read_text(encoding="utf-8"))
    print(compare_table(before, after))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="합성 샘플로 Ask 전후를 재생한다")
    sub = parser.add_subparsers(dest="command", required=True)

    seed = sub.add_parser("seed", help="일회용 워크스페이스에 샘플 문서를 수집한다")
    seed.add_argument("--state", required=True)
    seed.add_argument("--stack-url", default="http://127.0.0.1:54621")
    seed.add_argument("--api-url", default="http://127.0.0.1:8031")
    seed.add_argument("--sample", default=str(DEFAULT_SAMPLE))
    seed.add_argument("--limit-docs", type=int, default=0)
    seed.add_argument("--job-timeout", type=float, default=900)
    seed.set_defaults(func=cmd_seed)

    ask = sub.add_parser("ask", help="고정 질문을 재생한다")
    ask.add_argument("--state", required=True)
    ask.add_argument("--label", required=True)
    ask.add_argument("--out", required=True)
    ask.add_argument("--api-url", default="http://127.0.0.1:8031")
    ask.add_argument("--sample", default=str(DEFAULT_SAMPLE))
    ask.add_argument("--limit", type=int, default=0)
    # 기본 3달러. 이 값을 넘으면 남은 질문을 포기하고 부분 결과로 끝낸다.
    ask.add_argument("--max-spend-micros", type=int, default=3_000_000)
    ask.set_defaults(func=cmd_ask)

    compare = sub.add_parser("compare", help="두 결과를 Markdown 표로 비교한다")
    compare.add_argument("before")
    compare.add_argument("after")
    compare.set_defaults(func=cmd_compare)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
