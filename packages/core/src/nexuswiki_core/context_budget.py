"""Ask 컨텍스트 토큰 예산 할당기 및 텍스트 토큰 절단 순수 함수.

관련 이슈: #183, #184
설계 근거: openspec/changes/ai-context-budget/design.md > D1, D2
계약:
  - openspec/changes/ai-context-budget/specs/grounded-answering/spec.md
  - openspec/changes/ai-context-budget/specs/usage-guardrails/spec.md

소비자: `api.services.ask`, `worker.handlers.conflict`
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from nexuswiki_core.chunking import _encoding, count_tokens
from nexuswiki_core.rrf import EvidenceHit

__all__ = [
    "DEFAULT_ASK_MAX_CONTEXT_TOKENS",
    "AskContextBudgetResult",
    "allocate_ask_context_budget",
    "select_dual_evidence",
    "truncate_text_to_tokens",
]

DEFAULT_ASK_MAX_CONTEXT_TOKENS: Final[int] = 6000
_HEADER_OVERHEAD_TOKENS: Final[int] = 16
_MIN_PARTIAL_CONTENT_TOKENS: Final[int] = 24


@dataclass(frozen=True, slots=True)
class AskContextBudgetResult:
    """컨텍스트 토큰 예산 적용 결과.

    `as_report()`는 `ask_messages.control_report["budget"]`에 그대로 저장되므로
    본문·식별자·제목을 절대 포함하지 않고 정수와 불리언만 반환한다.
    """

    included_evidence: tuple[EvidenceHit, ...]
    content_by_id: Mapping[str, str]
    max_context_tokens: int
    estimated_context_tokens: int
    candidate_blocks: int
    included_blocks: int
    dropped_blocks: int
    truncated_blocks: int
    wiki_blocks: int
    source_blocks: int
    dual_evidence_preserved: bool
    truncated: bool

    def as_report(self) -> dict[str, Any]:
        return {
            "max_context_tokens": self.max_context_tokens,
            "estimated_context_tokens": self.estimated_context_tokens,
            "candidate_blocks": self.candidate_blocks,
            "included_blocks": self.included_blocks,
            "dropped_blocks": self.dropped_blocks,
            "truncated_blocks": self.truncated_blocks,
            "wiki_blocks": self.wiki_blocks,
            "source_blocks": self.source_blocks,
            "dual_evidence_preserved": self.dual_evidence_preserved,
            "truncated": self.truncated,
        }


def select_dual_evidence(
    candidates: Sequence[EvidenceHit], *, requested_k: int, per_source_limit: int = 3
) -> list[EvidenceHit]:
    """융합 후보에서 위키와 원문을 절반씩 고른다. 빈자리는 다른 종류로 채운다.

    ⚠️ RRF 상위 k개를 그대로 자르면 한 종류로 쏠릴 수 있다. 위키 페이지는 청크 임베딩이 여러
    개라 점수가 누적되어 상위를 독차지하고, 그러면 원문 근거가 프롬프트에 실리지 못해 이중
    Citation이 불가능해진다. 조립 단계의 쿼터는 이미 잘린 뒤라 이 쏠림을 되돌리지 못한다.

    같은 원문이 원문 몫을 독차지하지 않게 `per_source_limit`을 두되, 다른 원문이 없으면 그
    제한을 풀어 채운다. 결과 순서는 RRF 순서를 유지해 별칭 부여가 결정적이다.
    """
    wiki_quota = requested_k // 2
    source_quota = requested_k - wiki_quota
    selected: set[int] = set()
    taken = {"wiki": 0, "source": 0}
    quota = {"wiki": wiki_quota, "source": source_quota}
    per_source: dict[object, int] = {}

    # 1차: 종류별 몫을 채우되 한 원문이 원문 몫을 독차지하지 못하게 한다.
    for index, hit in enumerate(candidates):
        kind = "wiki" if hit.kind == "wiki" else "source"
        if taken[kind] >= quota[kind]:
            continue
        if kind == "source":
            raw_source_id = hit.metadata.get("raw_source_id")
            if per_source.get(raw_source_id, 0) >= per_source_limit:
                continue
            per_source[raw_source_id] = per_source.get(raw_source_id, 0) + 1
        selected.add(index)
        taken[kind] += 1

    # 2차: 원문 제한에 걸린 자리는 같은 종류로 먼저 채운다. 원문이 있는데 위키에 넘기면
    #      원문을 하나만 수집한 워크스페이스에서 절반 분배가 깨진다.
    for index, hit in enumerate(candidates):
        kind = "wiki" if hit.kind == "wiki" else "source"
        if index not in selected and taken[kind] < quota[kind]:
            selected.add(index)
            taken[kind] += 1

    # 3차: 한 종류가 정말 모자랄 때만 다른 종류로 채운다.
    for index in range(len(candidates)):
        if len(selected) >= requested_k:
            break
        selected.add(index)
    return [candidates[index] for index in sorted(selected)]


def truncate_text_to_tokens(text: str, max_tokens: int) -> tuple[str, bool]:
    """텍스트를 `cl100k_base` 기준 `max_tokens` 이하로 잘라 `(절단본, 절단여부)`를 돌려준다."""
    if not text:
        return "", False
    if max_tokens <= 0:
        return "", True
    enc = _encoding()
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text, False
    clipped = enc.decode(tokens[:max_tokens], errors="ignore")
    return clipped, True


def _hit_content_key(hit: EvidenceHit) -> str:
    return hit.document_id if hit.kind == "wiki" else hit.evidence_id


def allocate_ask_context_budget(
    evidence: Sequence[EvidenceHit],
    content_by_id: Mapping[str, str],
    *,
    max_context_tokens: int = DEFAULT_ASK_MAX_CONTEXT_TOKENS,
) -> AskContextBudgetResult:
    """Ask 근거 블록을 총 토큰 예산(`max_context_tokens`) 안에서 선택·절단한다.

    불변식:
    * 검색 결과에 `wiki`와 `source` 근거가 모두 존재하면, 상위 `wiki` 블록이 예산을
      초과하더라도 최상위 `wiki` 1개와 최상위 `source` 1개는 반드시 포함된다
      (`dual_evidence_preserved = True`).
    * 선택된 근거의 순서는 입력 RRF 순서를 그대로 유지하여 `build_issuance_map` 별칭
      부여 순서가 결정적으로 유지된다.
    """
    budget = max(1, max_context_tokens)
    candidate_count = len(evidence)
    if candidate_count == 0:
        return AskContextBudgetResult(
            included_evidence=(),
            content_by_id={},
            max_context_tokens=budget,
            estimated_context_tokens=0,
            candidate_blocks=0,
            included_blocks=0,
            dropped_blocks=0,
            truncated_blocks=0,
            wiki_blocks=0,
            source_blocks=0,
            dual_evidence_preserved=False,
            truncated=False,
        )

    first_wiki_idx = next((idx for idx, hit in enumerate(evidence) if hit.kind == "wiki"), None)
    first_source_idx = next((idx for idx, hit in enumerate(evidence) if hit.kind == "source"), None)
    has_both_kinds = first_wiki_idx is not None and first_source_idx is not None

    mandatory_indices: list[int] = []
    if has_both_kinds and first_wiki_idx is not None and first_source_idx is not None:
        mandatory_indices = sorted([first_wiki_idx, first_source_idx])
    else:
        mandatory_indices = [0]

    selected_content: dict[int, str] = {}
    selected_tokens: dict[int, int] = {}
    truncated_indices: set[int] = set()
    used_tokens = 0

    # 1단계: 필수 쿼터 블록(이중 근거 시 최상위 wiki + source, 단일 종류 시 최상위 1개) 배정
    mandatory_count = len(mandatory_indices)
    for pos, idx in enumerate(mandatory_indices):
        hit = evidence[idx]
        raw_text = content_by_id.get(_hit_content_key(hit), "")
        remaining_slots = mandatory_count - pos
        remaining_budget = max(1, budget - used_tokens)
        # 뒤에 남은 필수 블록을 위해 최소 반절(또는 균등 몫)을 남겨 두되,
        # 현재 블록이 짧으면 실제 쓴 만큼만 차감해 나머지 필수 블록이 여유를 쓰게 한다.
        slot_cap = (
            remaining_budget
            if remaining_slots == 1
            else max(1, remaining_budget // remaining_slots)
        )
        content_budget = max(1, slot_cap - _HEADER_OVERHEAD_TOKENS)
        clipped_text, was_clipped = truncate_text_to_tokens(raw_text, content_budget)
        block_tokens = min(slot_cap, count_tokens(clipped_text) + _HEADER_OVERHEAD_TOKENS)
        selected_content[idx] = clipped_text
        selected_tokens[idx] = block_tokens
        used_tokens += block_tokens
        if was_clipped:
            truncated_indices.add(idx)

    # 2단계: 만약 첫 필수 블록이 짧아서 두 번째 필수 블록이 잘렸는데 예산이 남았다면 보충
    if len(mandatory_indices) == 2 and used_tokens < budget:
        for idx in mandatory_indices:
            if idx not in truncated_indices:
                continue
            hit = evidence[idx]
            raw_text = content_by_id.get(_hit_content_key(hit), "")
            extra_budget = max(
                1, (budget - used_tokens) + selected_tokens[idx] - _HEADER_OVERHEAD_TOKENS
            )
            clipped_text, was_clipped = truncate_text_to_tokens(raw_text, extra_budget)
            new_tokens = min(
                budget - (used_tokens - selected_tokens[idx]),
                count_tokens(clipped_text) + _HEADER_OVERHEAD_TOKENS,
            )
            used_tokens = used_tokens - selected_tokens[idx] + new_tokens
            selected_content[idx] = clipped_text
            selected_tokens[idx] = new_tokens
            if not was_clipped:
                truncated_indices.discard(idx)

    # 3단계: 나머지 RRF 순위 블록을 순서대로 예산 안에서 수용
    mandatory_set = set(mandatory_indices)
    for idx, hit in enumerate(evidence):
        if idx in mandatory_set:
            continue
        remaining_budget = budget - used_tokens
        if remaining_budget <= _HEADER_OVERHEAD_TOKENS:
            break
        raw_text = content_by_id.get(_hit_content_key(hit), "")
        raw_tokens = count_tokens(raw_text) + _HEADER_OVERHEAD_TOKENS
        if raw_tokens <= remaining_budget:
            selected_content[idx] = raw_text
            selected_tokens[idx] = raw_tokens
            used_tokens += raw_tokens
            continue
        content_budget = remaining_budget - _HEADER_OVERHEAD_TOKENS
        if content_budget >= _MIN_PARTIAL_CONTENT_TOKENS:
            clipped_text, was_clipped = truncate_text_to_tokens(raw_text, content_budget)
            block_tokens = min(
                remaining_budget, count_tokens(clipped_text) + _HEADER_OVERHEAD_TOKENS
            )
            selected_content[idx] = clipped_text
            selected_tokens[idx] = block_tokens
            used_tokens += block_tokens
            if was_clipped:
                truncated_indices.add(idx)
        break

    ordered_indices = sorted(selected_content)
    included_hits = tuple(evidence[idx] for idx in ordered_indices)
    # 동일 문서/청크 키에 대해 선택된 본문 맵 구성
    bounded_content_by_id: dict[str, str] = dict(content_by_id)
    for idx in ordered_indices:
        bounded_content_by_id[_hit_content_key(evidence[idx])] = selected_content[idx]

    included_count = len(included_hits)
    dropped_count = candidate_count - included_count
    truncated_count = len(truncated_indices)
    wiki_count = sum(1 for hit in included_hits if hit.kind == "wiki")
    source_count = sum(1 for hit in included_hits if hit.kind == "source")
    dual_preserved = (wiki_count >= 1 and source_count >= 1) if has_both_kinds else False

    return AskContextBudgetResult(
        included_evidence=included_hits,
        content_by_id=bounded_content_by_id,
        max_context_tokens=budget,
        estimated_context_tokens=used_tokens,
        candidate_blocks=candidate_count,
        included_blocks=included_count,
        dropped_blocks=dropped_count,
        truncated_blocks=truncated_count,
        wiki_blocks=wiki_count,
        source_blocks=source_count,
        dual_evidence_preserved=dual_preserved,
        truncated=(dropped_count > 0 or truncated_count > 0),
    )
