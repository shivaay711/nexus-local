"""Answer-grounding heuristics. Explicitly heuristic — token-overlap
faithfulness is a proxy, not ground truth, and every report says so."""
from __future__ import annotations

import re


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 20]


def _terms(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def grounding_report(answer: str, evidence_excerpts: list[str],
                     support_threshold: float = 0.5) -> dict:
    """Per-sentence support: fraction of a sentence's content terms found in
    any single evidence excerpt. Sentences below threshold are flagged as
    potentially unsupported for human review."""
    evidence_term_sets = [_terms(e) for e in evidence_excerpts]
    sentences = _sentences(answer)
    supported, flagged = [], []
    for s in sentences:
        st = _terms(s)
        if not st:
            continue
        best = max((len(st & ev) / len(st) for ev in evidence_term_sets), default=0.0)
        (supported if best >= support_threshold else flagged).append(
            {"sentence": s, "support_score": round(best, 3)})
    total = len(supported) + len(flagged)
    return {
        "method": "heuristic-token-overlap-v1 (NOT ground truth)",
        "sentences_evaluated": total,
        "supported": len(supported),
        "potentially_unsupported": flagged,
        "faithfulness_score": round(len(supported) / total, 3) if total else None,
        "human_review": {"reviewed": False, "reviewer_notes": ""},
    }


def citation_coverage(answer: str, num_evidences: int) -> dict:
    """How many bracketed citation markers appear and whether they point at
    real evidence indices."""
    cited = {int(m) for m in re.findall(r"\[(\d+)\]", answer)}
    valid = {c for c in cited if 1 <= c <= num_evidences}
    return {
        "citations_found": sorted(cited),
        "valid_citations": sorted(valid),
        "invalid_citations": sorted(cited - valid),
        "evidence_available": num_evidences,
        "coverage": round(len(valid) / num_evidences, 3) if num_evidences else None,
    }
