#!/usr/bin/env python3
"""실제 합성 답변의 고정 판정을 재채점한다. #245 · offline-eval-regression-gate.

모델 출력 생성은 하지 않는다. 소비자는 PR CI와 로컬 검증이다.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from ask_replay import DEFAULT_SAMPLE, verdict

DEFAULT_FIXTURE = Path(__file__).with_name("fixtures") / "eval_regression.v1.json"
ROW_FIELDS = {
    "id",
    "doc",
    "status",
    "answer",
    "keyword_hit",
    "fabricated_anchor_count",
    "cited_wiki_count",
    "cited_source_count",
    "dual_citation_rate",
    "expected",
}


def require_fields(value: object, allowed: set[str], label: str) -> None:
    """필드 이름만 보고한다. 알 수 없는 값에 포함된 비밀은 출력하지 않는다."""
    if not isinstance(value, dict):
        raise ValueError(f"{label}: 객체가 아니다")
    if set(value) != allowed:
        extra = sorted(set(value) - allowed)
        missing = sorted(allowed - set(value))
        raise ValueError(f"{label}: 알 수 없는 필드 {extra}, 누락 필드 {missing}")


def check(data: dict) -> list[str]:
    """손상된 입력은 예외, 정상 입력의 판정 차이는 문항별 목록으로 반환한다."""
    require_fields(
        data,
        {
            "version",
            "source",
            "source_sha256",
            "question_ids",
            "rows",
        },
        "fixture",
    )
    if type(data["version"]) is not int or data["version"] != 1:
        raise ValueError("지원하지 않는 fixture 버전")
    if not isinstance(data["source"], str) or not data["source"].strip():
        raise ValueError("원본 출처가 없다")
    if not isinstance(data["source_sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", data["source_sha256"]
    ):
        raise ValueError("원본 sha256이 잘못됐다")
    ids, rows = data["question_ids"], data["rows"]
    if (
        not isinstance(ids, list)
        or not ids
        or not all(isinstance(q, str) and re.fullmatch(r"q\d{2}", q) for q in ids)
        or len(set(ids)) != len(ids)
    ):
        raise ValueError("계획 문항이 비었거나 잘못됐거나 중복됐다")
    if not isinstance(rows, list) or len(rows) != len(ids):
        raise ValueError("결과 문항 수가 계획과 다르다")
    sample = json.loads(DEFAULT_SAMPLE.read_text())
    canonical = {q["id"]: q["doc"] for q in sample["questions"]}
    if set(ids) != set(canonical):
        raise ValueError("고정 질문 fixture와 계획 문항이 다르다")
    seen, differences = set(), []
    for row in rows:
        require_fields(row, ROW_FIELDS, "행")
        qid = row["id"]
        if not isinstance(qid, str) or qid not in ids or qid in seen:
            raise ValueError("계획 밖 문항 또는 중복 문항")
        seen.add(qid)
        if row["doc"] != canonical[qid]:
            raise ValueError(f"{qid}: 질문의 정답 문서 분류가 바뀌었다")
        if not all(isinstance(row[k], str) for k in ("doc", "status", "answer")):
            raise ValueError(f"{qid}: 문자열 필드가 잘못됐다")
        if row["doc"] != "none" and row["answer"]:
            raise ValueError(f"{qid}: 일반 문항의 답변 본문은 저장하지 않는다")
        if row["keyword_hit"] is not None and type(row["keyword_hit"]) is not bool:
            raise ValueError(f"{qid}: 정답 판정이 잘못됐다")
        for key in ("fabricated_anchor_count", "cited_wiki_count", "cited_source_count"):
            if type(row[key]) is not int or row[key] < 0:
                raise ValueError(f"{qid}: {key}는 음이 아닌 정수여야 한다")
        rate = row["dual_citation_rate"]
        if type(rate) not in (int, float) or not 0 <= rate <= 1:
            raise ValueError(f"{qid}: 이중 인용 비율이 잘못됐다")
        expected = row["expected"]
        require_fields(expected, {"pass", "reason"}, f"{qid} 기대 판정")
        if type(expected["pass"]) is not bool or not (
            expected["reason"] is None or isinstance(expected["reason"], str)
        ):
            raise ValueError(f"{qid}: 기대 판정 자료형이 잘못됐다")
        actual = verdict(row)
        if actual != expected:
            differences.append(f"{qid}: 기대 {expected!r} / 현재 {actual!r}")
    return differences


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", nargs="?", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    try:
        data = json.loads(args.fixture.read_text())
        differences = check(data)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"회귀 관문 입력 오류: {exc}")
        return 2
    if differences:
        print("\n".join(differences))
        return 1
    print(f"합성 답변 {len(data['rows'])}문항의 고정 판정 일치")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
