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

    # 4. 실행마다 scorecard.jsonl에 한 줄이 쌓인다. 눈으로 볼 정적 HTML을 만든다(네트워크 불필요).
    uv run python scripts/ask_replay.py report --scorecard scorecard.jsonl --html scorecard.html

⚠️ 로컬 스택 전용이다. `.env`의 SUPABASE_URL은 클라우드를 가리키므로 읽지 않으며,
   루프백이 아닌 주소는 거부한다. service_role 키를 쓰는 조회가 운영으로 나가면 안 된다.
⚠️ 이 값은 합성 문서로 잰 샘플 수치다. 운영 트래픽의 효과로 인용하면 안 된다.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import statistics
import sys
import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx

_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = _ROOT / "scripts" / "fixtures" / "ask_replay.v1.json"


def _load_fingerprint() -> ModuleType:
    """같은 폴더의 지문 모듈. 스크립트 폴더는 패키지가 아니라 경로로 불러온다."""
    name = "_ask_replay_eval_fingerprint"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).with_name("eval_fingerprint.py")
    )
    if spec is None or spec.loader is None:
        raise SystemExit("ask_replay: eval_fingerprint.py를 불러오지 못했다")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fingerprint = _load_fingerprint()
# 값을 얻지 못한 고정 입력. 묶음에서는 어떤 값과도 같지 않은 것으로 본다
# (빈 값을 같다고 가정하지 않는다).
UNKNOWN = "unknown"

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


def fact_hit(answer: str, question: dict[str, Any]) -> bool | None:
    """질문의 기대 사실 판정. `expect_all`이 있으면 묶음마다 하나 이상, 없으면 `expect_any`.

    재생 · 6조건 · 모델 비교가 이 함수 하나를 쓴다. 두 곳에 두면 같은 답을 다르게 채점한다.
    """
    if question.get("expect_all"):
        return all(keyword_hit(answer, list(group)) for group in question["expect_all"])
    return keyword_hit(answer, list(question.get("expect_any") or []))


def forbidden_hit(answer: str, expect_none: list[str]) -> bool | None:
    """답변이 금지 사실(옛 규정 값 · 다른 문서 값)을 말했는지. 정의가 없으면 None이다.

    ⚠️ 기대 사실과 같은 정규화를 쓴다. 다르면 같은 값을 한쪽은 잡고 한쪽은 놓친다.
    """
    if not expect_none:
        return None
    return bool(keyword_hit(answer, expect_none))


def _mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]


def _ratio(flags: list[bool]) -> float | None:
    return sum(flags) / len(flags) if flags else None


# 답변 프롬프트가 "컨텍스트로 답할 수 없으면" 쓰라고 지시하는 거절 문구다.
# 출처: supabase/migrations/0006_seed_prompts.sql (151행, 184행). 재생은 이 전역 시드 템플릿을 쓴다.
# ⚠️ 프롬프트의 문구를 바꾸면 이 상수도 함께 바꿔야 한다. 어긋나면 정확한 거절이 실패로 센다.
REFUSAL_STATEMENT = "제공된 자료로는 알 수 없습니다"


def is_refusal(answer: str | None) -> bool:
    """답변이 표준 거절 문구로 시작하는지. 제목 줄(`#`)과 빈 줄을 건너뛴 첫 본문 줄만 본다.

    문구가 본문 중간에 나오는 답("영업이익은 1조원입니다. ... 알 수 없습니다")은 거절이 아니다.
    공백 차이는 `keyword_hit`과 같은 방식으로 무시한다.
    """
    for line in (answer or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return "".join(stripped.split()).startswith("".join(REFUSAL_STATEMENT.split()))
    return False


def verdict(row: dict[str, Any], answerable: bool | None = None) -> dict[str, Any]:
    """질문 한 개의 통과 여부와 실패 이유 한 줄. 행에 이미 있는 필드만 읽는다.

    저장된 값이 아니라 행에서 매번 다시 계산하므로, 기준을 고쳐도 옛 결과 파일을 재채점할 수 있다.
    이유는 아래 고정 순서의 첫 실패만 적는다: 상태 → 위조 앵커 → 기대 사실 → 금지 사실 → 이중 인용.
    금지 사실 필드가 없는 옛 행(`forbidden_hit` 없음 · None)은 그 기준을 건너뛰어 판정이 그대로다.

    ⚠️ 답할 수 없는 질문(`doc == "none"`)은 거절이 정답이다. 거절은 두 모양이다: 검색이 근거를 못
       찾아 `no-evidence`로 끝나거나, 무관한 근거가 잡혀 모델까지 갔다가 표준 문구로 거절한
       `resolved`다. `no-evidence`만 인정하면 모델의 정확한 거절이 실패로 센다(#224).
       알려진 한계: 질의 임베딩 일시 실패 같은 장애의 `no-evidence`도 통과로 세고, 거절 문구로
       시작한 뒤 이어서 답하는 혼합 답변도 통과할 수 있다(위조 앵커만 잡는다).
    """
    if answerable is None:
        answerable = row.get("doc") != "none"
    status = str(row.get("status"))
    fabricated = int(row.get("fabricated_anchor_count") or 0)

    if not answerable:
        refused = status == "no-evidence" or (
            status == "resolved" and is_refusal(row.get("answer"))
        )
        if not refused:
            return {"pass": False, "reason": f"답하면 안 되는 질문에 답했다 (상태 {status})"}
        if fabricated:
            return {"pass": False, "reason": f"위조 앵커 {fabricated}건"}
        return {"pass": True, "reason": None}

    if status == "fallback":
        # 인용 계약 수리에 실패해 근거 목록으로 끝난 답이다. 정상 완료로 치지 않는다.
        return {"pass": False, "reason": "수리 후 fallback으로 끝났다"}
    if status != "resolved":
        return {"pass": False, "reason": f"정상 완료가 아니다 (상태 {status})"}
    if fabricated:
        return {"pass": False, "reason": f"위조 앵커 {fabricated}건"}
    if row.get("keyword_hit") is False:
        return {"pass": False, "reason": "기대 사실이 답변에 없다"}
    if row.get("forbidden_hit") is True:
        # 새 값과 옛 값을 함께 늘어놓은 답은 어느 쪽이 맞는지 사용자가 가릴 수 없다.
        return {"pass": False, "reason": "금지 사실(옛 값이나 다른 문서 값)을 말했다"}
    # 기대값이 없으면(None) 이 기준은 건너뛴다.
    wiki, source = row.get("cited_wiki_count"), row.get("cited_source_count")
    if wiki is not None and source is not None:
        # 답변 단위: 위키와 원문을 각각 한 번 이상 인용하면 된다(서로 다른 문장이어도 된다).
        if wiki < 1 or source < 1:
            return {
                "pass": False,
                "reason": f"위키 또는 원문 인용이 없다 (위키 {wiki}, 원문 {source})",
            }
    elif not (row.get("dual_citation_rate") or 0) > 0:
        # ⚠️ 옛 결과 파일에는 종류별 개수가 없다. 한 문장에 둘 다 있는 문장 비율로 대체하므로
        #    답변 단위보다 엄격하다(위키와 원문을 다른 문장에서 인용한 답은 불통과로 나온다).
        return {
            "pass": False,
            "reason": "위키와 원문을 함께 인용한 문장이 없다 (옛 결과, 문장 기준)",
        }
    return {"pass": True, "reason": None}


def is_answerable(row: dict[str, Any]) -> bool:
    """`verdict`와 같은 기준. `doc`이 없는 옛 행은 답할 수 있는 질문으로 본다."""
    return row.get("doc") != "none"


def is_false_refusal(row: dict[str, Any]) -> bool:
    """답할 수 있는 질문을 거절했는지. 근거 없음 단락과 표준 문구 거절을 모두 센다.

    `verdict`는 이 행을 이미 실패로 센다. 여기서는 실패 중 "거절해서 틀린" 것만 따로 드러낸다.
    """
    status = str(row.get("status"))
    return is_answerable(row) and (
        status == "no-evidence" or (status == "resolved" and is_refusal(row.get("answer")))
    )


def refusal_split(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """통과율 안에 섞인 거절 성능을 세 수치로 나눈다. 판정은 `verdict`를 그대로 쓴다.

    ⚠️ 거절 문항이 없으면 정확한 거절은 0이 아니라 None이다. 0/0을 0으로 쓰면 "거절을 하나도
       못 했다"로 읽힌다.
    """
    answerable = [row for row in rows if is_answerable(row)]
    unanswerable = [row for row in rows if not is_answerable(row)]
    return {
        "answerable_asked": len(answerable),
        "answerable_passed": sum(1 for row in answerable if verdict(row)["pass"]),
        "refusal_asked": len(unanswerable),
        "refusal_correct": (
            sum(1 for row in unanswerable if verdict(row)["pass"]) if unanswerable else None
        ),
        "false_refusals": sum(1 for row in answerable if is_false_refusal(row)),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """질문별 결과를 집계한다. 인용 지표는 LLM이 답한 턴만 본다.

    근거 없음으로 단락한 턴을 넣으면 인용률이 0으로 희석되어 전후 비교가 왜곡된다.
    """
    llm_rows = [row for row in rows if row.get("prompt_tokens") is not None]
    elapsed = [float(r["elapsed_ms"]) for r in rows if r.get("elapsed_ms") is not None]
    passed = sum(1 for row in rows if verdict(row)["pass"])
    models = [str(r["model"]) for r in rows if r.get("model")]
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
        "asked": len(rows),
        "passed": passed,
        "pass_rate": passed / len(rows) if rows else None,
        # 통과율은 거절 문항을 포함한 전체 기준 그대로 두고, 거절 성능은 따로 센다.
        **refusal_split(rows),
        # 클라이언트가 잰 시간이다: 큐 대기와 네트워크가 섞이고 서버 처리 시간이 아니다.
        # n이 작아 p95는 최댓값 가까이에 붙는다(기존 `_percentile`의 인덱스 방식 그대로).
        "latency_p50_ms": _percentile(elapsed, 0.5),
        "latency_p95_ms": _percentile(elapsed, 0.95),
        "model": models[0] if models else "unknown",
        "prompt_tokens_total": sum(int(r["prompt_tokens"]) for r in llm_rows),
        "completion_tokens_total": sum(int(r.get("completion_tokens") or 0) for r in llm_rows),
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


def scorecard_line(result: dict[str, Any], result_file: str | None) -> dict[str, Any]:
    """실행 한 번을 성적표 한 줄로 줄인다. 질문·답변 본문과 키는 넣지 않는다.

    ⚠️ 한 줄은 한 번 쓰면 고치지 않는다. 필드를 줄이거나 이름을 바꾸면 옛 줄을 읽는 화면이 깨진다.
    """
    summary = result.get("summary") or summarize(result.get("rows") or [])
    asked = int(summary.get("asked") or 0)
    cost_total = int(summary.get("cost_micros_total") or 0)
    # 거절 수치가 없는 옛 요약이면 행에서 다시 센다. 행도 없으면 줄에 넣지 않는다(0과 구분).
    split = {key: summary[key] for key in _REFUSAL_KEYS if key in summary}
    if len(split) != len(_REFUSAL_KEYS) and result.get("rows"):
        split = refusal_split(result["rows"])
    return {
        "label": result.get("label") or "unknown",
        "git_sha": result.get("git_sha") or "unknown",
        "model": summary.get("model") or "unknown",
        "date": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "asked": asked,
        # 지출 상한으로 일찍 멈춘 실행이 전체 실행처럼 읽히지 않게 계획 문항 수를 같이 남긴다.
        "planned": int(result.get("planned_questions") or asked),
        "passed": int(summary.get("passed") or 0),
        "pass_rate": summary.get("pass_rate"),
        "prompt_tokens_total": int(summary.get("prompt_tokens_total") or 0),
        "completion_tokens_total": int(summary.get("completion_tokens_total") or 0),
        "cost_micros_total": cost_total,
        "cost_micros_per_question": round(cost_total / asked) if asked else None,
        "latency_p50_ms": summary.get("latency_p50_ms"),
        "latency_p95_ms": summary.get("latency_p95_ms"),
        "result_file": result_file,
        **split,
    }


_REFUSAL_KEYS = (
    "answerable_asked",
    "answerable_passed",
    "refusal_asked",
    "refusal_correct",
    "false_refusals",
)


def append_scorecard(path: Path, line: dict[str, Any]) -> None:
    """한 줄을 덧붙인다. 앞선 줄은 읽지도 고치지도 않는다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, ensure_ascii=False) + "\n")


def read_scorecard(path: Path) -> tuple[list[dict[str, Any]], int]:
    """줄 단위로 읽는다. 깨진 줄은 건너뛰고 개수를 돌려줘 화면이 알리게 한다."""
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


def _run_for_report(line: dict[str, Any], rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    """화면에 실을 실행 한 개. 판정은 여기서 행마다 다시 계산한다(저장된 값을 믿지 않는다)."""
    detail = None
    split = {key: line[key] for key in _REFUSAL_KEYS if key in line}
    if rows is not None:
        detail = [{**row, "verdict": verdict(row)} for row in rows]
        # 판정처럼 거절 수치도 행에서 다시 센다. 필드가 없는 옛 줄도 같은 값을 얻는다.
        split = refusal_split(rows)
    return {**line, **split, "rows": detail}


def build_report_data(
    scorecard: Path, extra_results: list[Path]
) -> tuple[list[dict[str, Any]], int, list[str]]:
    """성적표 줄과 결과 파일을 읽어 화면용 실행 목록을 만든다. 네트워크·DB에 닿지 않는다."""
    lines, broken = read_scorecard(scorecard)
    runs: list[dict[str, Any]] = []
    notes: list[str] = []
    for line in lines:
        rows = None
        relative = line.get("result_file")
        if relative:
            candidate = scorecard.parent / str(relative)
            if candidate.exists():
                try:
                    rows = json.loads(candidate.read_text(encoding="utf-8")).get("rows")
                except (json.JSONDecodeError, OSError):
                    notes.append(f"{relative}: 결과 파일을 읽지 못했다")
        runs.append(_run_for_report(line, rows))
    for path in extra_results:
        # 성적표 줄이 생기기 전에 만든 결과 파일도 행 필드만으로 그린다.
        result = json.loads(path.read_text(encoding="utf-8"))
        rows = result.get("rows") or []
        runs.append(_run_for_report(scorecard_line(result, path.name), rows))
    return runs, broken, notes


def _json_for_script(value: Any) -> str:
    """<script> 안에 안전하게 넣을 JSON. `</script>`나 줄 구분자가 문서를 깨뜨리지 못하게 한다."""
    text = json.dumps(value, ensure_ascii=False)
    return (
        text.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )


_REPORT_HTML = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ask 성적표</title>
<style>
:root{--bg:#fafaf8;--fg:#1c1d21;--muted:#62666f;--line:#dcdde2;--card:#fff;--accent:#3b5bdb;--bad:#b42318;--badbg:#fdecea;--ok:#146c43}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111317;--fg:#e8eaf0;--muted:#9aa1b2;--line:#2c313c;--card:#181b22;--accent:#7b9bff;--bad:#ff8a80;--badbg:#3a1c1c;--ok:#6fd49b}}
:root[data-theme="dark"]{--bg:#111317;--fg:#e8eaf0;--muted:#9aa1b2;--line:#2c313c;--card:#181b22;--accent:#7b9bff;--bad:#ff8a80;--badbg:#3a1c1c;--ok:#6fd49b}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 "Apple SD Gothic Neo",system-ui,sans-serif;padding:24px 16px 64px}
main{max-width:1100px;margin:0 auto}
h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:32px 0 8px}
.notice{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);padding:10px 14px;border-radius:6px;color:var(--muted);margin:12px 0 20px}
.wrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--card)}
table{border-collapse:collapse;width:100%;min-width:640px}
th{text-align:left;color:var(--muted);font-weight:600;padding:10px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.bar{display:inline-block;width:90px;height:10px;background:var(--line);border-radius:5px;margin-right:8px;vertical-align:middle;overflow:hidden}
.bar i{display:block;height:100%;background:var(--accent)}
button.run{all:unset;cursor:pointer;color:var(--accent);font-weight:600;text-decoration:underline}
button.run:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
tr.sel td{background:color-mix(in srgb,var(--accent) 10%,transparent)}
tr.fail td{background:var(--badbg)}
.v-fail{color:var(--bad);font-weight:700}.v-ok{color:var(--ok)}.v-fail,.v-ok{white-space:nowrap}
.mono{font-family:ui-monospace,Menlo,monospace;font-size:13px}
details summary{cursor:pointer;color:var(--muted)}
details pre{white-space:pre-wrap;margin:6px 0 0;font:inherit;color:var(--fg)}
.muted{color:var(--muted)}
</style>
</head>
<body>
<main>
<h1>Ask 성적표</h1>
<div class="notice">합성 샘플 수치이며 운영 트래픽이 아닙니다. 질문 수가 적고 LLM 답변이 매번 달라 작은 차이는 의미가 없습니다.
기대 사실은 키워드 포함 여부일 뿐이고, 지연은 클라이언트가 잰 시간(큐 대기·네트워크 포함)입니다.
n이 작아 p95는 최댓값에 가깝습니다.
통과율은 답하면 안 되는 문항을 포함한 전체 기준입니다. 거절 성능은 옆 칸에 분모와 함께 따로 적으며, 거절 문항이 적으면 그 수치는 의미가 작습니다.</div>
<div id="problems" class="muted"></div>
<h2>실행별 성적표</h2>
<div id="runs"></div>
<h2 id="detail-title"></h2>
<div id="detail"></div>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
(function(){
var data=JSON.parse(document.getElementById("data").textContent);
var runs=data.runs,sel=runs.length-1;
function el(tag,text,cls){var e=document.createElement(tag);if(text!=null)e.textContent=text;if(cls)e.className=cls;return e}
function fmt(n){return n==null?"-":Number(n).toLocaleString("ko-KR")}
function sec(ms){return ms==null?"-":(ms/1000).toFixed(1)+"초"}
function usd(m){return m==null?"-":"$"+(m/1e6).toFixed(4)}
function pct(r){return r==null?"-":Math.round(r*100)+"%"}
function frac(a,b){return a==null||b==null?"-":a+"/"+b}
function refusal(r){if(r.refusal_asked==null)return"-";if(r.refusal_asked===0)return"없음 (거절 문항 0개)";return frac(r.refusal_correct,r.refusal_asked)}
function th(row,labels){var tr=document.createElement("tr");labels.forEach(function(l){tr.appendChild(el("th",l))});row.appendChild(tr)}
var problems=document.getElementById("problems");
if(data.broken)problems.appendChild(el("p","읽지 못한 성적표 줄 "+data.broken+"개는 건너뛰었습니다."));
data.notes.forEach(function(n){problems.appendChild(el("p",n))});
function renderRuns(){
 var box=document.getElementById("runs");box.textContent="";
 if(!runs.length){
  box.appendChild(el("p","아직 기록된 실행이 없습니다. 먼저 한 번 돌리세요:"));
  box.appendChild(el("p","uv run python scripts/ask_replay.py ask --state state.json --label 이름 --out 결과.json","mono"));
  return}
 var wrap=el("div",null,"wrap"),t=document.createElement("table"),head=document.createElement("thead");
 th(head,["실행","모델","통과율","답할 수 있는 문항 통과","정확한 거절 (거절 문항)","잘못된 거절","문항","입력 토큰","$/문항","p50","p95","날짜"]);t.appendChild(head);
 var body=document.createElement("tbody");
 runs.forEach(function(r,i){
  var tr=document.createElement("tr");if(i===sel)tr.className="sel";
  var c=document.createElement("td"),b=el("button",r.label+(r.git_sha&&r.git_sha!=="unknown"?" ("+String(r.git_sha).slice(0,7)+")":""),"run");
  b.type="button";b.addEventListener("click",function(){sel=i;renderRuns();renderDetail()});c.appendChild(b);tr.appendChild(c);
  tr.appendChild(el("td",r.model));
  var p=document.createElement("td"),bar=el("span",null,"bar"),fill=document.createElement("i");fill.style.width=Math.round((r.pass_rate||0)*100)+"%";bar.appendChild(fill);
  p.appendChild(bar);p.appendChild(el("span",pct(r.pass_rate)+" ("+r.passed+"/"+r.asked+")"));tr.appendChild(p);
  tr.appendChild(el("td",frac(r.answerable_passed,r.answerable_asked),"num"));
  tr.appendChild(el("td",refusal(r),"num"));
  tr.appendChild(el("td",frac(r.false_refusals,r.answerable_asked),"num"));
  var q=r.asked<r.planned?r.asked+"/"+r.planned+" (중단)":String(r.asked);tr.appendChild(el("td",q,"num"));
  tr.appendChild(el("td",fmt(r.prompt_tokens_total),"num"));
  tr.appendChild(el("td",usd(r.cost_micros_per_question),"num"));
  tr.appendChild(el("td",sec(r.latency_p50_ms),"num"));tr.appendChild(el("td",sec(r.latency_p95_ms),"num"));
  tr.appendChild(el("td",r.date||"-","muted"));body.appendChild(tr)});
 t.appendChild(body);wrap.appendChild(t);box.appendChild(wrap)}
function renderDetail(){
 var box=document.getElementById("detail"),title=document.getElementById("detail-title");box.textContent="";
 if(sel<0||!runs[sel]){title.textContent="";return}
 var r=runs[sel];title.textContent="문항 상세: "+r.label;
 if(!r.rows){box.appendChild(el("p","이 실행의 결과 파일을 찾지 못해 상세를 볼 수 없습니다.","muted"));return}
 var wrap=el("div",null,"wrap"),t=document.createElement("table"),head=document.createElement("thead");
 th(head,["문항","판정","이유","상태","입력 토큰","지연","답변"]);t.appendChild(head);
 var body=document.createElement("tbody");
 r.rows.forEach(function(row){
  var ok=row.verdict.pass,tr=document.createElement("tr");if(!ok)tr.className="fail";
  tr.appendChild(el("td",row.id,"mono"));
  tr.appendChild(el("td",ok?"✓ 통과":"✗ 실패",ok?"v-ok":"v-fail"));
  tr.appendChild(el("td",row.verdict.reason||""));
  tr.appendChild(el("td",row.status));
  tr.appendChild(el("td",fmt(row.prompt_tokens),"num"));
  tr.appendChild(el("td",sec(row.elapsed_ms),"num"));
  var a=document.createElement("td");
  if(row.answer){var d=document.createElement("details");d.appendChild(el("summary","보기"));d.appendChild(el("pre",row.answer));a.appendChild(d)}
  tr.appendChild(a);body.appendChild(tr)});
 t.appendChild(body);wrap.appendChild(t);box.appendChild(wrap)}
renderRuns();renderDetail();
})();
</script>
</body>
</html>
"""  # noqa: E501 — 화면 코드는 한 줄이 길다


def render_report(runs: list[dict[str, Any]], broken: int, notes: list[str]) -> str:
    payload = {"runs": runs, "broken": broken, "notes": notes}
    return _REPORT_HTML.replace("__DATA__", _json_for_script(payload))


# --- 검색만 따로 채점 (강의 32편) -------------------------------------------------------

RETRIEVAL_K = 8
RETRIEVAL_METRIC_DEFINITION = (
    "hit@k = 정답 문서의 근거가 하나라도 상위 k에 있는 질문의 비율(hit rate). "
    "MRR = 첫 적중 순위의 역수 평균(적중 없음은 0). 이중 적중@8 = 상위 8 안에 정답 원문과 "
    "정답 위키(정답 문서로 컴파일된 페이지)가 둘 다 있음. 답할 수 있는 질문만 센다."
)


def evidence_origins(
    item: dict[str, Any],
    wiki_sources: dict[str, set[str]],
    chunk_sources: dict[str, str],
) -> set[str]:
    """근거 한 개가 어느 raw_source에서 왔는지.

    ⚠️ 원문 근거의 `document_id`는 raw_source id가 아니라 **청크 id**다(`EvidenceHit.source`).
       raw_source id는 `metadata.raw_source_id`에 있고, 없으면 청크 id로 조회한 값을 쓴다.
       위키 근거는 그 페이지를 만든 원문 목록(`wiki_pages.sources`)이다.
    """
    if item.get("kind") == "wiki":
        return set(wiki_sources.get(str(item.get("document_id")), set()))
    metadata = item.get("metadata") or {}
    raw = metadata.get("raw_source_id") or chunk_sources.get(str(item.get("id")))
    return {str(raw)} if raw else set()


def channel_failures(meta: dict[str, Any]) -> list[str]:
    """검색 응답 `meta`에서 실패한 채널 이름.

    ⚠️ 검색 API는 임베딩이나 RPC가 실패해도 200을 돌려주고 장애는 `meta`의 채널 상태에만
       남긴다. 이걸 읽지 않으면 장애로 낮아진 지표가 정상 측정처럼 기준선에 남는다.
    """
    return sorted(
        name
        for name, value in meta.items()
        if isinstance(value, dict) and value.get("status") == "failed"
    )


def retrieval_question_result(
    evidence: list[dict[str, Any]],
    expected: set[str],
    wiki_sources: dict[str, set[str]],
    chunk_sources: dict[str, str],
) -> dict[str, Any]:
    """질문 한 개의 순위별 적중과 첫 적중 순위. `expected`는 정답 raw_source id 집합이다."""
    ranked = []
    for rank, item in enumerate(evidence[:RETRIEVAL_K], start=1):
        origins = evidence_origins(item, wiki_sources, chunk_sources)
        ranked.append(
            {
                "rank": rank,
                "kind": item.get("kind"),
                "relevant": bool(origins & expected),
                # 순위 차이를 만든 채널을 기록에서 되짚기 위해 응답의 기여도를 그대로 남긴다.
                # 근거 본문은 담지 않는다.
                "channels": list(item.get("channels") or []),
                "contributions": dict(item.get("contributions") or {}),
            }
        )
    first = next((r["rank"] for r in ranked if r["relevant"]), None)
    found = set()
    for item in evidence[:RETRIEVAL_K]:
        found |= evidence_origins(item, wiki_sources, chunk_sources) & expected
    source_hit = any(r["relevant"] and r["kind"] == "source" for r in ranked)
    wiki_hit = any(r["relevant"] and r["kind"] == "wiki" for r in ranked)
    return {
        "ranked": ranked,
        "first_relevant_rank": first,
        "source_hit": source_hit,
        "wiki_hit": wiki_hit,
        "dual_hit": source_hit and wiki_hit,
        "expected_count": len(expected),
        "found_count": len(found),
    }


def summarize_retrieval(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """답할 수 있는 질문만으로 지표를 낸다.

    측정이 정상(`status == "ok"`)이 아닌 질문은 빼지 않고 모든 지표에서 미적중으로 센다.
    HTTP 실패, 채널 장애, 정답 문서 매핑 실패, 근거 원문 확인 실패가 여기에 든다. 빼면 분모가
    줄어 지표가 실제보다 좋아 보인다. 여러 문서 질문의 정답 문서 수도 결과가 아니라 질문의
    `doc`에서 센다. 결과에서 세면 실패한 질문이 분모에서 사라진다.
    """
    answerable = [r for r in rows if r.get("doc") != "none"]
    n = len(answerable)

    def result(row: dict[str, Any]) -> dict[str, Any]:
        return (row.get("result") or {}) if row.get("status") == "ok" else {}

    def share(flags: list[bool]) -> float | None:
        return sum(flags) / len(flags) if flags else None

    def first(row: dict[str, Any]) -> int | None:
        return result(row).get("first_relevant_rank")

    def flag(row: dict[str, Any], key: str) -> bool:
        return bool(result(row).get(key))

    def expected_docs(row: dict[str, Any]) -> int:
        return len(str(row.get("doc")).split("+"))

    multi = [r for r in answerable if expected_docs(r) > 1]
    statuses: dict[str, int] = {}
    for row in rows:
        statuses[str(row.get("status"))] = statuses.get(str(row.get("status")), 0) + 1
    return {
        "definition": RETRIEVAL_METRIC_DEFINITION,
        "answerable": n,
        "failed_requests": sum(1 for r in rows if r.get("status") != "ok"),
        "status_counts": statuses,
        "hit_at_1": share([(first(r) or 99) <= 1 for r in answerable]),
        "hit_at_3": share([(first(r) or 99) <= 3 for r in answerable]),
        "hit_at_8": share([first(r) is not None for r in answerable]),
        "mrr": share([1 / first(r) if first(r) else 0.0 for r in answerable]) if n else None,
        "source_hit_at_8": share([flag(r, "source_hit") for r in answerable]),
        "wiki_hit_at_8": share([flag(r, "wiki_hit") for r in answerable]),
        "dual_hit_at_8": share([flag(r, "dual_hit") for r in answerable]),
        "multi_doc_questions": len(multi),
        "multi_doc_any_found": sum(1 for r in multi if result(r).get("found_count", 0) >= 1),
        "multi_doc_all_found": sum(
            1 for r in multi if result(r).get("found_count", 0) == expected_docs(r)
        ),
        "unanswerable_evidence_counts": {
            str(r.get("id")): int(r.get("evidence_count") or 0)
            for r in rows
            if r.get("doc") == "none"
        },
    }


_RETRIEVAL_COMPARE_ROWS: tuple[tuple[str, str], ...] = (
    ("hit_at_1", "hit@1"),
    ("hit_at_3", "hit@3"),
    ("hit_at_8", "hit@8"),
    ("mrr", "MRR"),
    ("source_hit_at_8", "원문만 hit@8"),
    ("wiki_hit_at_8", "위키만 hit@8"),
    ("dual_hit_at_8", "이중 적중@8"),
    ("failed_requests", "측정 실패 질문"),
)


def retrieval_compare_table(before: dict[str, Any], after: dict[str, Any]) -> str:
    """두 검색 기록을 공통 질문으로만 비교한다. 한쪽에만 있는 질문은 평균을 왜곡한다."""
    after_ids = {row["id"] for row in after["rows"]}
    keep = {row["id"] for row in before["rows"] if row["id"] in after_ids}
    left = summarize_retrieval([r for r in before["rows"] if r["id"] in keep])
    right = summarize_retrieval([r for r in after["rows"] if r["id"] in keep])
    lines = [
        f"합성 샘플 공통 문항 {len(keep)}개(답할 수 있는 질문 {left['answerable']}개) 기준이며 "
        "운영 트래픽 수치가 아니다.",
        RETRIEVAL_METRIC_DEFINITION,
        f"검색 정책: `{before['label']}` {before.get('policy_versions') or '알 수 없음'} / "
        f"`{after['label']}` {after.get('policy_versions') or '알 수 없음'}",
        "",
        f"| 지표 | {before['label']} | {after['label']} |",
        "| --- | --- | --- |",
    ]
    for key, label in _RETRIEVAL_COMPARE_ROWS:
        lines.append(f"| {label} | {_format(left.get(key))} | {_format(right.get(key))} |")
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
    sample = json.loads(path.read_text(encoding="utf-8"))
    if sample.get("base"):
        base = _load_sample(path.parent / sample["base"])
        return {**base, "questions": base["questions"] + sample["questions"]}
    return sample


# PostgREST 기본 max_rows. 이 수에 닿으면 오류 없이 잘린 것일 수 있다.
POSTGREST_MAX_ROWS = 1000

# 수집 스냅샷 지문의 입력 열. ⚠️ 열 목록이 곧 해시 대상이다. 바꾸면 #232 기록과 지문이 달라진다.
SNAPSHOT_COLUMNS: dict[str, tuple[str, str]] = {
    "raw_sources": ("raw_sources", "id,title"),
    "source_chunks": (
        "source_chunks",
        "id,raw_source_id,chunk_index,content,char_start,char_end,embedding_version",
    ),
    "wiki_pages": ("wiki_pages", "id,title,content,sources"),
    "wiki_chunks": ("wiki_embeddings", "id,wiki_id,chunk_index,chunk_content,embedding_version"),
}


def select_all(
    client: httpx.Client, stack: str, table: str, workspace: str, columns: str, token: str
) -> list[dict[str, Any]]:
    """워크스페이스의 행 전부를 요청자 JWT로 읽는다."""
    rows = _select(
        client,
        stack,
        table,
        {"workspace_id": f"eq.{workspace}", "select": columns, "order": "id"},
        token=token,
    )
    # ⚠️ PostgREST는 max_rows(1000)에서 오류 없이 자른다. 잘린 스냅샷의 해시는 조용히 틀린다.
    if len(rows) >= POSTGREST_MAX_ROWS:
        raise SystemExit(f"ask_replay: {table}가 {POSTGREST_MAX_ROWS}행 이상이라 잘렸을 수 있다")
    return rows


def snapshot_tables(
    client: httpx.Client, stack: str, workspace: str, token: str
) -> dict[str, list[dict[str, Any]]]:
    """수집 스냅샷 지문의 입력 테이블. 재생 · 검색 채점 · #232 실험이 모두 이 함수로 읽는다."""
    return {
        key: select_all(client, stack, table, workspace, columns, token)
        for key, (table, columns) in SNAPSHOT_COLUMNS.items()
    }


def answer_prompt_sha256(
    client: httpx.Client, stack: str, workspace: str, token: str
) -> str | None:
    """답변에 쓰인 기본 Ask 템플릿의 해시. 워크스페이스 템플릿이 없으면 전역 시드 템플릿이다.

    회차 사이에 프롬프트가 바뀌면 같은 조건의 반복이 아니다.
    """
    for scope in (f"eq.{workspace}", "is.null"):
        rows = _select(
            client,
            stack,
            "prompt_templates",
            {
                "workspace_id": scope,
                "target_type": "eq.ask",
                "is_default": "eq.true",
                "select": "id,system_prompt,template",
            },
            token=token,
        )
        if rows:
            return fingerprint.canonical_sha256(rows[0])
    return None


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


def select_capped(
    client: httpx.Client, stack: str, table: str, params: dict[str, str]
) -> list[dict[str, Any]]:
    """service_role 집계 조회. max_rows에 닿으면 멈춘다.

    ⚠️ PostgREST는 1000행에서 오류 없이 자른다. 집계(잡 실패 · 지출 · 컴파일 모델)가 잘리면
       실패 잡이나 지출이 조용히 빠진다.
    """
    rows = _select(client, stack, table, params)
    if len(rows) >= POSTGREST_MAX_ROWS:
        raise SystemExit(f"ask_replay: {table}가 {POSTGREST_MAX_ROWS}행 이상이라 잘렸을 수 있다")
    return rows


def _wait_for_jobs(
    client: httpx.Client, stack: str, workspace_id: str, timeout: float
) -> list[dict[str, Any]]:
    """체인 전체가 끝날 때까지 기다린다. 실패 잡을 조용히 넘기면 샘플이 비어 수치가 왜곡된다."""
    deadline = time.monotonic() + timeout
    while True:
        jobs = select_capped(
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
    rows = select_capped(
        client,
        stack,
        "usage_events",
        {"workspace_id": f"eq.{workspace_id}", "select": "cost_micros"},
    )
    return sum(int(row.get("cost_micros") or 0) for row in rows)


QUESTION_TYPES = ("multi_doc", "conflict", "long_noisy", "distractor", "refusal")
MIN_PER_ANSWERABLE_TYPE = 8
MIN_REFUSAL = 3
LONG_NOISY_MIN_CHARS = 4000


def is_typed_sample(sample: dict[str, Any]) -> bool:
    """질문에 유형이 하나라도 있으면 유형 시험지다. 기존 30문항 시험지는 검사 대상이 아니다."""
    return any("type" in q for q in sample.get("questions") or [])


def check_typed_sample(sample: dict[str, Any]) -> list[str]:
    """위키 유리 시험지의 구성 조건을 검사해 어긴 항목을 돌려준다(wiki-advantage-eval 설계 D3).

    ⚠️ 이 검사를 통과하지 않은 시험지로 수집하면, 원문 하나로 풀리는 "여러 문서" 문항이나
       옛 값이 금지되지 않은 충돌 문항이 섞여 위키 효과가 조용히 희석된다.
    """
    docs = {str(d["id"]): d for d in sample.get("documents") or []}
    errors: list[str] = []
    counts = dict.fromkeys(QUESTION_TYPES, 0)
    for q in sample.get("questions") or []:
        qid, qtype = str(q.get("id")), q.get("type")
        if qtype not in QUESTION_TYPES:
            errors.append(f"{qid}: 유형이 없거나 허용 밖이다 ({qtype})")
            continue
        counts[qtype] += 1
        doc_field = str(q.get("doc"))
        if qtype == "refusal":
            if doc_field != "none":
                errors.append(f"{qid}: 거절 문항의 doc은 none이어야 한다")
            continue
        ids = doc_field.split("+")
        missing = [d for d in ids if d not in docs]
        if missing:
            errors.append(f"{qid}: 없는 문서 {missing}")
            continue
        texts = {d: str(docs[d]["text"]) for d in ids}
        forbidden = list(q.get("expect_none") or [])
        if not (q.get("expect_any") or q.get("expect_all")):
            errors.append(f"{qid}: 기대 사실이 없다")
            continue
        if qtype == "multi_doc":
            if len(ids) < 2:
                errors.append(f"{qid}: 여러 문서 문항은 문서가 둘 이상이어야 한다")
            for d, text in texts.items():
                if fact_hit(text, q):
                    errors.append(f"{qid}: 기대 사실이 한 문서({d})에 그대로 있다")
        elif qtype == "conflict":
            dated = [d for d in ids if docs[d].get("effective_date")]
            if len(ids) != 2 or len(dated) != 2:
                errors.append(f"{qid}: 충돌 문항은 시행일 있는 문서 두 개여야 한다")
                continue
            older, newer = sorted(ids, key=lambda d: str(docs[d]["effective_date"]))
            if docs[older]["effective_date"] == docs[newer]["effective_date"]:
                errors.append(f"{qid}: 두 문서의 시행일이 같다")
            if not fact_hit(texts[newer], q) or fact_hit(texts[older], q):
                errors.append(f"{qid}: 기대 사실은 새 문서({newer})에만 있어야 한다")
            if not forbidden or not forbidden_hit(texts[older], forbidden):
                errors.append(f"{qid}: 옛 문서({older})의 값이 금지 사실에 없다")
            if forbidden and forbidden_hit(texts[newer], forbidden):
                errors.append(f"{qid}: 금지 사실이 새 문서({newer})에 나온다")
            continue
        elif qtype == "long_noisy":
            if len(ids) != 1 or len(texts[ids[0]]) < LONG_NOISY_MIN_CHARS:
                errors.append(f"{qid}: 답 문서가 {LONG_NOISY_MIN_CHARS}자 이상 한 개여야 한다")
        elif qtype == "distractor":
            family = docs[ids[0]].get("family") if len(ids) == 1 else None
            siblings = [
                str(d["text"])
                for key, d in docs.items()
                if family and d.get("family") == family and key != ids[0]
            ]
            if len(siblings) < 2:
                errors.append(f"{qid}: 같은 family의 다른 문서가 둘 이상이어야 한다")
            if not forbidden:
                errors.append(f"{qid}: 형제 문서의 값이 금지 사실에 없다")
            for value in forbidden:
                if not any(keyword_hit(text, [value]) for text in siblings):
                    errors.append(f"{qid}: 금지 사실 {value!r}이 형제 문서에 없다")
        if qtype != "multi_doc" and not fact_hit("\n".join(texts.values()), q):
            errors.append(f"{qid}: 기대 사실이 답 문서에 없다")
        if forbidden and any(forbidden_hit(text, forbidden) for text in texts.values()):
            errors.append(f"{qid}: 금지 사실이 답 문서에 나온다")
    for qtype, count in counts.items():
        need = MIN_REFUSAL if qtype == "refusal" else MIN_PER_ANSWERABLE_TYPE
        if count < need:
            errors.append(f"유형 {qtype}: {count}문항 < 최소 {need}")
    return errors


def typed_sample_warnings(sample: dict[str, Any]) -> list[str]:
    """실패는 아니지만 사람이 알아야 할 겹침. `multi_doc` 기대 사실이 근거로 지정하지 않은 다른
    문서에 우연히 그대로 있는 경우다(스펙: 근거 문서 단일 포함만 실패, 나머지는 경고)."""
    docs = {str(d["id"]): str(d["text"]) for d in sample.get("documents") or []}
    warnings = []
    for q in sample.get("questions") or []:
        if q.get("type") != "multi_doc":
            continue
        own = set(str(q.get("doc")).split("+"))
        for doc_id, text in docs.items():
            if doc_id not in own and fact_hit(text, q):
                warnings.append(f"{q['id']}: 기대 사실이 근거 밖 문서({doc_id})에 있다")
    return warnings


def cmd_check_sample(args: argparse.Namespace) -> int:
    sample = _load_sample(Path(args.sample))
    if not is_typed_sample(sample):
        raise SystemExit("ask_replay: 유형이 없는 시험지다. 검사 대상이 아니다")
    errors = check_typed_sample(sample)
    for error in errors:
        print(f"ask_replay: 시험지 위반 {error}")
    for warning in typed_sample_warnings(sample):
        print(f"ask_replay: 시험지 경고 {warning}")
    counts = {t: sum(1 for q in sample["questions"] if q.get("type") == t) for t in QUESTION_TYPES}
    print(f"ask_replay: 유형별 문항 {counts}, 문서 {len(sample['documents'])}개")
    return 1 if errors else 0


def _set_monthly_budget(container: str, workspace_id: str, micros: int) -> None:
    """실험 워크스페이스의 월 한도를 실험 총 상한으로 낮춘다. 로컬 재생 DB 컨테이너 전용이다.

    `workspaces`는 service_role에도 UPDATE 권한이 없어서(REST 403) 재생 DB에 psql로 직접 쓴다.
    지난 실험들의 월 한도 조정과 같은 경로다.
    ⚠️ SQL 문자열에 값을 넣으므로 UUID와 정수만 받는다. 바뀐 행이 정확히 1이 아니면 멈춘다.
    """
    import subprocess

    workspace = str(UUID(workspace_id))
    if not isinstance(micros, int) or micros < 0:
        raise SystemExit("ask_replay: 월 한도는 0 이상의 정수여야 한다")
    # UUID 정규화와 int 검사를 거친 값만 넣는다.
    sql = f"update public.workspaces set monthly_budget_micros = {micros} where id = '{workspace}' returning monthly_budget_micros;"  # noqa: E501, S608
    result = subprocess.run(  # noqa: S603 - 고정 인자, 값은 위에서 형식 검증
        ["docker", "exec", container, "psql", "-U", "postgres", "-d", "postgres", "-At", "-c", sql],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or result.stdout.strip().splitlines()[:1] != [str(micros)]:
        raise SystemExit("ask_replay: 워크스페이스 월 한도를 바꾸지 못했다. 수집하지 않는다")


def cmd_seed(args: argparse.Namespace) -> int:
    stack = assert_loopback(args.stack_url)
    api = assert_loopback(args.api_url)
    sample = _load_sample(Path(args.sample))
    if is_typed_sample(sample):
        errors = check_typed_sample(sample)
        if errors:
            raise SystemExit(f"ask_replay: 시험지가 구성 조건을 어긴다. 수집하지 않는다: {errors}")
    documents = sample["documents"][: args.limit_docs] if args.limit_docs else sample["documents"]
    with httpx.Client(timeout=60) as client:
        state = {
            **_actor(client, stack),
            "stack_url": stack,
            "documents": [d["id"] for d in documents],
        }
        if args.monthly_budget_micros is not None:
            # 문서를 넣기 전에 낮춰야 컴파일 잡 인큐부터 이 한도가 막는다(설계 D5).
            _set_monthly_budget(
                args.db_container, state["workspace_id"], args.monthly_budget_micros
            )
            state["monthly_budget_micros"] = args.monthly_budget_micros
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


def _count_kind(citations: dict[str, Any], kind: str) -> int | None:
    """답변이 실제로 인용한 앵커 중 종류별 개수. 인용 이벤트가 없으면 None(0과 구분)."""
    resolved = citations.get("resolved")
    if not isinstance(resolved, list):
        return None
    return sum(1 for item in resolved if isinstance(item, dict) and item.get("kind") == kind)


def _ask_once(
    client: httpx.Client,
    api: str,
    stack: str,
    workspace_id: str,
    token: str,
    question: dict[str, Any],
    *,
    include_embeddings: bool = False,
) -> dict[str, Any]:
    turn_id = str(uuid4())
    started = time.monotonic()
    with client.stream(
        "POST",
        f"{api}/workspaces/{workspace_id}/ask",
        headers={"Authorization": f"Bearer {token}"},
        # k를 서버 기본값에 맡기지 않고 보낸 값을 고정 입력으로 기록한다.
        json={"query": question["query"], "client_turn_id": turn_id, "requested_k": RETRIEVAL_K},
    ) as response:
        if response.status_code != 200:
            response.read()
            return {
                "id": question["id"],
                # 거절 문항이 HTTP 오류로 끝나도 답할 수 있는 문항으로 잘못 세지 않게 남긴다.
                "doc": question.get("doc"),
                "status": f"http_{response.status_code}",
                "error": response.text[:300],
                "prompt_tokens": None,
            }
        first_delta_ms: int | None = None

        def measured_lines() -> Iterable[str]:
            nonlocal first_delta_ms
            for line in response.iter_lines():
                if line.strip() == "event: delta" and first_delta_ms is None:
                    first_delta_ms = round((time.monotonic() - started) * 1000)
                yield line

        events = parse_sse(measured_lines())
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
                **({} if include_embeddings else {"kind": "neq.embedding"}),
                "select": "prompt_tokens,completion_tokens,cost_micros,model,kind,metadata",
            },
        )
    report = message.get("control_report") or {}
    meta = next((payload for name, payload in events if name == "meta"), {})
    stored_retrieval = report.get("retrieval") or {}
    return {
        "id": question["id"],
        "doc": question.get("doc"),
        "status": message.get("status") or "unknown",
        # 근거 없음 경로의 meta에는 정책 버전이 없어 저장된 control_report로 보탠다.
        "policy_version": meta.get("policy_version") or stored_retrieval.get("policy_version"),
        # 검색 API처럼 Ask도 채널 장애를 200 안에 숨긴다. 원인 판정의 실행 장애가 이 값을 읽는다.
        "missing_channels": sorted(
            meta.get("missing_channels") or stored_retrieval.get("missing_channels") or []
        ),
        "model": next(
            (u["model"] for u in usage if u.get("model") and u.get("kind") != "embedding"), None
        ),
        "elapsed_ms": elapsed_ms,
        "first_delta_ms": first_delta_ms,
        "prompt_tokens": sum(int(u.get("prompt_tokens") or 0) for u in usage) if usage else None,
        "completion_tokens": sum(int(u.get("completion_tokens") or 0) for u in usage)
        if usage
        else None,
        "cost_micros": sum(int(u.get("cost_micros") or 0) for u in usage),
        "dual_citation_rate": citations.get("dual_citation_rate"),
        "unsourced_sentence_ratio": citations.get("unsourced_sentence_ratio"),
        "fabricated_anchor_count": citations.get("fabricated_anchor_count"),
        "cited_anchor_count": citations.get("cited_anchor_count"),
        "cited_wiki_count": _count_kind(citations, "wiki"),
        "cited_source_count": _count_kind(citations, "source"),
        "keyword_hit": fact_hit(answer, question),
        "forbidden_hit": forbidden_hit(answer, list(question.get("expect_none") or [])),
        "research": report.get("research"),
        "retrieval": report.get("retrieval"),
        "usage_incomplete": not usage
        or any((u.get("metadata") or {}).get("incomplete") for u in usage),
        "budget": report.get("budget"),
        "route": report.get("route"),
        "answer": answer,
    }


def _api_sha(client: httpx.Client, api: str) -> str | None:
    try:
        return client.get(f"{api}/health").json().get("git_sha")
    except (httpx.HTTPError, ValueError):
        return None


def select_questions(
    sample: dict[str, Any], state: dict[str, Any], limit: int = 0
) -> list[dict[str, Any]]:
    """재생할 질문. 수집하지 않은 문서를 묻는 질문은 기대 사실 포함률을 깎아 비교를 흐려 뺀다."""
    seeded = set(state["documents"])
    questions = [
        q
        for q in sample["questions"]
        if q.get("doc") == "none" or set(str(q.get("doc")).split("+")) <= seeded
    ]
    return questions[:limit] if limit else questions


def collect_fixed_inputs(
    client: httpx.Client,
    stack: str,
    workspace: str,
    token: str,
    sample: dict[str, Any],
    *,
    with_prompt: bool = True,
) -> dict[str, Any]:
    """회차 시작 시 고정 입력을 잰다. 얻지 못한 값은 `unknown`으로 남기고 회차는 계속한다.

    ⚠️ 지문은 #232 실험과 같은 정의(`eval_fingerprint`)다. 같은 수집이면 #232 기록의
       `fixed_inputs.snapshot_sha256`과 같은 값이 나와야 한 묶음으로 읽힌다.
    """
    fixed: dict[str, Any] = {
        "fixture_sha256": fingerprint.fixture_sha256(sample),
        "requested_k": RETRIEVAL_K,
        "snapshot_sha256": UNKNOWN,
    }
    try:
        tables = snapshot_tables(client, stack, workspace, token)
        fixed["snapshot_sha256"] = fingerprint.snapshot_inputs(**tables)["snapshot_sha256"]
    # 잘린 조회는 select_all이 SystemExit로 알린다. 재생은 멈추지 않고 지문만 unknown으로 둔다.
    except (httpx.HTTPError, ValueError, KeyError, SystemExit) as exc:
        print(f"ask_replay: 수집 스냅샷 지문을 얻지 못해 unknown으로 둔다: {exc}")
    if not with_prompt:
        return fixed
    fixed["answer_prompt_sha256"] = UNKNOWN
    try:
        fixed["answer_prompt_sha256"] = (
            answer_prompt_sha256(client, stack, workspace, token) or UNKNOWN
        )
    except (httpx.HTTPError, ValueError) as exc:
        print(f"ask_replay: 답변 프롬프트 해시를 얻지 못해 unknown으로 둔다: {exc}")
    return fixed


def finalize_fixed_inputs(fixed: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """턴에서만 알 수 있는 값(모델 · 정책 버전)을 더한다.

    정책 버전은 회차 안에서 관측한 값 전부를 남긴다. 둘 이상이면 같은 조건의 회차가 아니다.
    """
    models = sorted({str(r["model"]) for r in rows if r.get("model")})
    policies = sorted({str(r["policy_version"]) for r in rows if r.get("policy_version")})
    return {
        **fixed,
        "model": models[0] if len(models) == 1 else UNKNOWN,
        # 하나도 관측하지 못하면 빈 목록이 아니라 unknown이다(얻지 못한 값을 0과 구분).
        "policy_versions": policies or UNKNOWN,
    }


# 질문을 하나 끝낼 때마다 불린다. 멈출 이유를 돌려주면 남은 질문을 묻지 않는다.
StopCheck = Callable[[int, dict[str, Any] | None], str | None]


def run_replay(
    client: httpx.Client,
    api: str,
    stack: str,
    workspace: str,
    token: str,
    questions: list[dict[str, Any]],
    *,
    before_question: StopCheck | None = None,
    after_question: StopCheck | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """질문들을 한 회차로 재생한다. (행, 멈춘 이유)를 돌려준다.

    `before_question`은 질문을 시작하기 전(지금까지의 지출, 직전 행), `after_question`은 끝난 뒤에
    불린다. 반복 재생은 앞의 것으로 상한을 넘기 전에 멈추고, `ask`는 기존대로 뒤의 것을 쓴다.
    """
    rows: list[dict[str, Any]] = []
    spent = 0
    for question in questions:
        if before_question is not None:
            reason = before_question(spent, rows[-1] if rows else None)
            if reason:
                return rows, reason
        row = _ask_once(client, api, stack, workspace, token, question)
        rows.append(row)
        spent += int(row.get("cost_micros") or 0)
        print(
            f"ask_replay: {row['id']} {row['status']} prompt={row.get('prompt_tokens')} "
            f"hit={row.get('keyword_hit')} 누적={spent} micros"
        )
        if after_question is not None:
            reason = after_question(spent, row)
            if reason:
                return rows, reason
    return rows, None


def build_result(
    *,
    label: str,
    sha: str | None,
    questions: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    fixed: dict[str, Any],
    stopped: str | None,
    path: str = "http",
) -> dict[str, Any]:
    for row in rows:
        row["verdict"] = verdict(row)
    return {
        "label": label,
        "git_sha": sha,
        # 반복 묶음이 HTTP 회차와 #232 하네스 회차를 구분하는 값이다.
        "execution_path": path,
        "planned_questions": len(questions),
        # 개수만으로는 일찍 멈춘 회차에서 어떤 문항을 묻지 못했는지 알 수 없다(일부 문서만 수집하면
        # 계획이 fixture 앞부분과 다르다). 반복 보고서가 미실행 문항을 정확히 세려고 남긴다.
        "planned_question_ids": [str(q["id"]) for q in questions],
        "stopped": {"reason": stopped, "asked": len(rows)} if stopped else None,
        "fixed_inputs": finalize_fixed_inputs(fixed, rows),
        "rows": rows,
        "summary": summarize(rows),
    }


def write_result(result: dict[str, Any], out: Path, scorecard_path: str | None) -> Path:
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    # 성적표 한 줄을 쌓는다. 결과 파일은 성적표 옆 상대 경로로 가리켜 디렉터리를 옮겨도 이어진다.
    scorecard = Path(scorecard_path) if scorecard_path else out.with_name("scorecard.jsonl")
    relative = os.path.relpath(out.resolve(), scorecard.resolve().parent)
    append_scorecard(scorecard, scorecard_line(result, relative))
    print(f"ask_replay: 성적표에 한 줄을 더했다 → {scorecard}")
    return scorecard


def cmd_ask(args: argparse.Namespace) -> int:
    api = assert_loopback(args.api_url)
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    stack = assert_loopback(state["stack_url"])
    sample = _load_sample(Path(args.sample))
    questions = select_questions(sample, state, args.limit)

    def over_cap(spent: int, _row: dict[str, Any] | None) -> str | None:
        if spent > args.max_spend_micros:
            print(f"ask_replay: 지출 상한 {args.max_spend_micros} micros를 넘어 중단한다")
            return "spend_cap"
        return None

    with httpx.Client(timeout=180) as client:
        token = _login(client, stack, state)
        sha = _api_sha(client, api)
        fixed = collect_fixed_inputs(client, stack, state["workspace_id"], token, sample)
        rows, stopped = run_replay(
            client, api, stack, state["workspace_id"], token, questions, after_question=over_cap
        )
    result = build_result(
        label=args.label, sha=sha, questions=questions, rows=rows, fixed=fixed, stopped=stopped
    )
    write_result(result, Path(args.out), args.scorecard)
    return 0 if len(rows) == len(questions) else 1


def cmd_report(args: argparse.Namespace) -> int:
    runs, broken, notes = build_report_data(
        Path(args.scorecard), [Path(p) for p in args.result or []]
    )
    html = render_report(runs, broken, notes)
    Path(args.html).write_text(html, encoding="utf-8")
    print(f"ask_replay: 실행 {len(runs)}개로 성적표를 만들었다 → {args.html}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after).read_text(encoding="utf-8"))
    print(compare_table(before, after))
    return 0


def cmd_retrieval_eval(args: argparse.Namespace) -> int:
    out = Path(args.out)
    # ⚠️ 기록은 append-only다. 덮어쓰면 비교의 기준선이 조용히 사라진다.
    if out.exists():
        raise SystemExit(f"ask_replay: 이미 있는 기록은 덮어쓰지 않는다: {out}")
    api = assert_loopback(args.api_url)
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    stack = assert_loopback(state["stack_url"])
    sample = _load_sample(Path(args.sample))
    seeded = set(state["documents"])
    questions = [
        q
        for q in sample["questions"]
        if q.get("doc") == "none" or set(str(q.get("doc")).split("+")) <= seeded
    ]
    if args.limit:
        questions = questions[: args.limit]
    workspace = state["workspace_id"]
    titles = {d["id"]: d["title"] for d in sample["documents"]}
    rows: list[dict[str, Any]] = []
    policies: set[str] = set()
    with httpx.Client(timeout=60) as client:
        token = _login(client, stack, state)
        sha = _api_sha(client, api)
        # 답변 재생과 같은 정의의 지문을 남겨, 원인 판정이 같은 수집의 검색 기록만 쓰게 한다.
        # 검색 채점은 답변 프롬프트를 쓰지 않으므로 그 해시는 남기지 않는다.
        fixed = collect_fixed_inputs(client, stack, workspace, token, sample, with_prompt=False)
        # 조회는 모두 요청자 토큰으로 한다. RLS 아래에서 읽으므로 service_role이 필요 없다.
        sources = _select(
            client,
            stack,
            "raw_sources",
            {"workspace_id": f"eq.{workspace}", "select": "id,title"},
            token=token,
        )
        raw_by_title: dict[str, str] = {}
        for source in sources:
            title = str(source["title"])
            # 같은 제목이 둘이면 정답 문서를 하나로 정할 수 없다. 조용히 하나만 남기지 않는다.
            if title in raw_by_title:
                raise SystemExit(f"ask_replay: 제목이 같은 원문이 둘 이상이다: {title}")
            raw_by_title[title] = str(source["id"])
        pages = _select(
            client,
            stack,
            "wiki_pages",
            {"workspace_id": f"eq.{workspace}", "select": "id,sources"},
            token=token,
        )
        wiki_sources = {str(p["id"]): {str(x) for x in (p.get("sources") or [])} for p in pages}
        for question in questions:
            doc = str(question.get("doc"))
            unmapped = [
                d
                for d in ([] if doc == "none" else doc.split("+"))
                if titles.get(d) not in raw_by_title
            ]
            if unmapped:
                # 정답 문서를 못 찾은 채 재면 미적중이 검색 탓처럼 보인다. 측정 실패로 남긴다.
                rows.append(
                    {
                        "id": question["id"],
                        "doc": doc,
                        "status": "unmapped_expected",
                        "unmapped": unmapped,
                        "evidence_count": 0,
                        "result": None,
                    }
                )
                continue
            expected = set() if doc == "none" else {raw_by_title[titles[d]] for d in doc.split("+")}
            response = client.post(
                f"{api}/workspaces/{workspace}/retrieval",
                headers={"Authorization": f"Bearer {token}"},
                json={"query": question["query"], "requested_k": RETRIEVAL_K},
            )
            if response.status_code != 200:
                rows.append(
                    {
                        "id": question["id"],
                        "doc": doc,
                        "status": f"http_{response.status_code}",
                        "evidence_count": 0,
                        "result": None,
                    }
                )
                continue
            body = response.json()
            evidence = list(body.get("evidence") or [])
            meta = body.get("meta") or {}
            if meta.get("policy_version"):
                policies.add(str(meta["policy_version"]))
            failed_channels = channel_failures(meta)
            missing = [
                str(e.get("id"))
                for e in evidence
                if e.get("kind") == "source" and not (e.get("metadata") or {}).get("raw_source_id")
            ]
            chunk_sources: dict[str, str] = {}
            if missing:
                found = _select(
                    client,
                    stack,
                    "source_chunks",
                    {
                        "workspace_id": f"eq.{workspace}",
                        "id": f"in.({','.join(missing)})",
                        "select": "id,raw_source_id",
                    },
                    token=token,
                )
                chunk_sources = {str(r["id"]): str(r["raw_source_id"]) for r in found}
            unresolved = [chunk for chunk in missing if chunk not in chunk_sources]
            result = retrieval_question_result(evidence, expected, wiki_sources, chunk_sources)
            # 채널 장애나 원문을 확인하지 못한 근거가 있으면 결과는 남기되 측정 실패로 센다.
            if failed_channels:
                status = "channel_failed"
            elif unresolved:
                status = "unresolved_evidence"
            else:
                status = "ok"
            rows.append(
                {
                    "id": question["id"],
                    "doc": doc,
                    "status": status,
                    "failed_channels": failed_channels,
                    "unresolved_evidence": len(unresolved),
                    "evidence_count": len(evidence),
                    "result": result,
                }
            )
            print(
                f"ask_replay: {question['id']} 첫 적중={result['first_relevant_rank']} "
                f"이중={result['dual_hit']}"
            )
    record = {
        "label": args.label,
        "git_sha": sha,
        "k": RETRIEVAL_K,
        # 두 기록을 비교할 때 같은 검색 정책에서 잰 것인지 확인하는 값이다.
        "policy_versions": sorted(policies),
        "fixed_inputs": fixed,
        "rows": rows,
        "summary": summarize_retrieval(rows),
    }
    # "x" 모드: 실행 중에 같은 경로가 생겼어도 덮어쓰지 않는다.
    with out.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, indent=2))
    print(json.dumps(record["summary"], ensure_ascii=False, indent=2))
    return 0


def cmd_retrieval_compare(args: argparse.Namespace) -> int:
    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after).read_text(encoding="utf-8"))
    print(retrieval_compare_table(before, after))
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
    seed.add_argument(
        "--monthly-budget-micros",
        type=int,
        default=None,
        help="새 워크스페이스 월 한도. 실험 총 상한으로 낮춰 제품 예산 관문이 지출을 막게 한다",
    )
    seed.add_argument("--db-container", default="supabase_db_NexusWikiReplay")
    seed.set_defaults(func=cmd_seed)

    check_sample = sub.add_parser("check-sample", help="유형 시험지의 구성 조건을 검사한다")
    check_sample.add_argument("--sample", required=True)
    check_sample.set_defaults(func=cmd_check_sample)

    ask = sub.add_parser("ask", help="고정 질문을 재생한다")
    ask.add_argument("--state", required=True)
    ask.add_argument("--label", required=True)
    ask.add_argument("--out", required=True)
    ask.add_argument("--api-url", default="http://127.0.0.1:8031")
    ask.add_argument("--sample", default=str(DEFAULT_SAMPLE))
    ask.add_argument("--limit", type=int, default=0)
    # 기본 3달러. 이 값을 넘으면 남은 질문을 포기하고 부분 결과로 끝낸다.
    ask.add_argument("--max-spend-micros", type=int, default=3_000_000)
    ask.add_argument("--scorecard", help="성적표 파일. 기본은 --out 옆의 scorecard.jsonl")
    ask.set_defaults(func=cmd_ask)

    report = sub.add_parser("report", help="성적표를 정적 HTML로 만든다(네트워크 불필요)")
    report.add_argument("--scorecard", required=True)
    report.add_argument("--html", required=True)
    report.add_argument(
        "--result", action="append", help="성적표 줄이 없는 옛 결과 파일을 더한다(여러 번 가능)"
    )
    report.set_defaults(func=cmd_report)

    reval = sub.add_parser("retrieval-eval", help="답변 없이 검색만 채점한다(LLM 호출 없음)")
    reval.add_argument("--state", required=True)
    reval.add_argument("--label", required=True)
    reval.add_argument("--out", required=True)
    reval.add_argument("--api-url", default="http://127.0.0.1:8031")
    reval.add_argument("--sample", default=str(DEFAULT_SAMPLE))
    reval.add_argument("--limit", type=int, default=0)
    reval.set_defaults(func=cmd_retrieval_eval)

    rcompare = sub.add_parser("retrieval-compare", help="두 검색 기록을 공통 질문으로 비교한다")
    rcompare.add_argument("before")
    rcompare.add_argument("after")
    rcompare.set_defaults(func=cmd_retrieval_compare)

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
