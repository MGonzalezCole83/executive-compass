"""Executive Compass — mechanical due-date computation.

Pure, deterministic implementation of canonical document 02's
"Mechanical due-date computation" section. This module decides NOTHING
that requires judgement: it classifies open items against today's date
and reports what is mechanically due. The model consumes this output;
it never re-derives it.

Input item shape (plain dicts, as exported from Airtable):
    {
      "id": "rec...", "title": str,
      "status": "Now" | "Holding" | "Upcoming",
      "priority": bool, "priority_reason": str | None,
      "review_date": "YYYY-MM-DD" | None,
      "hard_deadline": "YYYY-MM-DD" | None,
      "owed_by_email": str | None,      # contact email if Owed By has one
      "entity": str | None, "project": str | None,
    }

Canonical rules implemented (doc 02, v2.0, approved 25 Jul 2026):
  * Hard Deadline is never defaulted or inferred (reported, never written).
  * Now with no Review Date  -> default today+7 (flagged as fallback).
  * Holding with no Review Date -> default today+14 (flagged as fallback).
  * Upcoming with no Review Date -> NO default; classification question.
  * Overdue Now (review_date <= today) -> never rolled, NEVER Priority-flagged;
    reported under 'overdue' until Martin resolves it.
  * Upcoming reaching review_date -> activates: status change to Now (reported
    as an activation for the caller to write).
  * Holding reaching review_date -> chase draft if owed_by_email present,
    else a "still Holding, or yours to do now?" question.
"""
from __future__ import annotations
import datetime as _dt

NOW, HOLDING, UPCOMING = "Now", "Holding", "Upcoming"
DEFAULT_DAYS = {NOW: 7, HOLDING: 14}


def _d(iso):
    return _dt.date.fromisoformat(iso) if iso else None


def compute(items: list[dict], today: str) -> dict:
    """Return the full mechanical result for one run. Pure function."""
    t = _dt.date.fromisoformat(today)
    out = {
        "overdue": [],            # Now items at/past review date: {item, days_over}
        "activations": [],        # Upcoming at/past date: write status -> Now
        "holding_chase": [],      # Holding due, owed_by_email present: draft chase
        "holding_question": [],   # Holding due, no email: ask Martin
        "defaults_to_assign": [], # {id, status, new_review_date} to write back
        "classification_questions": [],  # Upcoming with no date: belongs in Holding?
        "hard_deadlines_soon": [],       # within 7 days, informational
        "errors": [],             # data-quality violations found (never "fixed" here)
    }
    for it in items:
        st = it.get("status")
        rd = _d(it.get("review_date"))
        hd = _d(it.get("hard_deadline"))

        # data-quality flags (doc 02) — reported, never auto-corrected
        if it.get("priority") and st != NOW:
            out["errors"].append({"id": it["id"], "error": "Priority set on non-Now item"})
        if it.get("priority") and not (it.get("priority_reason") or "").strip():
            out["errors"].append({"id": it["id"], "error": "Priority without a stated reason"})

        if hd and (hd - t).days <= 7:
            out["hard_deadlines_soon"].append({"id": it["id"], "title": it["title"],
                                               "hard_deadline": hd.isoformat(),
                                               "days_left": (hd - t).days})
        if rd is None:
            if st in DEFAULT_DAYS:
                out["defaults_to_assign"].append({
                    "id": it["id"], "status": st,
                    "new_review_date": (t + _dt.timedelta(days=DEFAULT_DAYS[st])).isoformat(),
                    "fallback": True})
            elif st == UPCOMING:
                out["classification_questions"].append({
                    "id": it["id"], "title": it["title"],
                    "question": "Upcoming with no statable activation date — belongs in Holding. "
                                "Now, Holding, or Upcoming? If Holding, when back as Now?"})
            continue

        if rd > t:
            continue  # not yet due — nothing mechanical to do

        if st == NOW:
            out["overdue"].append({"id": it["id"], "title": it["title"],
                                   "review_date": rd.isoformat(),
                                   "days_over": (t - rd).days,
                                   "priority": bool(it.get("priority")),
                                   "priority_reason": it.get("priority_reason")})
        elif st == UPCOMING:
            out["activations"].append({"id": it["id"], "title": it["title"],
                                       "write": {"status": NOW}})
        elif st == HOLDING:
            bucket = "holding_chase" if it.get("owed_by_email") else "holding_question"
            out[bucket].append({"id": it["id"], "title": it["title"],
                                "review_date": rd.isoformat(),
                                "owed_by_email": it.get("owed_by_email")})
    return out
