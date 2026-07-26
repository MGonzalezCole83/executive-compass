"""Executive Compass — dedup-against-closed-work matcher.

Deterministic half of canonical document 02's dedup rule. Given a piece of
evidence and exports of (a) closed Items and (b) Chronicle entries (including
the "Phase 0 closure:" backfill), return candidate matches. The MODEL then
judges whether the evidence is an echo (suppress + label + log) or a genuine
reopening (ask, citing the closure). This module finds candidates; it never
decides.

Evidence shape:
    {"counterparty": str|None, "refs": [str, ...], "subject": str}
    refs = invoice numbers, order numbers, application refs, etc.

Match signals, strongest first:
  1. exact reference-number hit (e.g. "INV-0005") anywhere in the record text
  2. counterparty token + >=2 significant subject-word overlap
"""
from __future__ import annotations
import re

_STOP = {"the","a","an","and","or","for","from","your","of","to","in","on","is",
         "due","re","fw","fwd","invoice","payment","reminder","ltd","limited"}


def _tokens(s):
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-']+", (s or "").lower())
            if w not in _STOP and len(w) > 2}


def _norm_refs(refs):
    return {r.strip().upper() for r in (refs or []) if r and r.strip()}


def find_candidates(evidence: dict, closed_items: list[dict],
                    chronicle: list[dict]) -> list[dict]:
    """closed_items: {"id","title","closure_reason"}; chronicle: {"id","entry","interpretation"}"""
    refs = _norm_refs(evidence.get("refs"))
    cp = _tokens(evidence.get("counterparty") or "")
    subj = _tokens(evidence.get("subject") or "")
    hits = []

    def scan(records, kind, text_fields):
        for r in records:
            text = " ".join(str(r.get(f) or "") for f in text_fields)
            up, tk = text.upper(), _tokens(text)
            if refs and any(ref in up for ref in refs):
                hits.append({"kind": kind, "id": r["id"], "signal": "reference",
                             "matched": sorted(ref for ref in refs if ref in up),
                             "text": text[:200]})
                continue
            if cp and (cp & tk) and len(subj & tk) >= 2:
                hits.append({"kind": kind, "id": r["id"], "signal": "counterparty+subject",
                             "matched": sorted((cp & tk) | (subj & tk)),
                             "text": text[:200]})

    scan(closed_items, "closed_item", ("title", "closure_reason"))
    scan(chronicle, "chronicle", ("entry", "interpretation"))
    # strongest first, stable
    hits.sort(key=lambda h: 0 if h["signal"] == "reference" else 1)
    return hits
