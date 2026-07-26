"""Executive Compass — replay test suite.

The canonical cases from live operation, 24–25 Jul 2026, encoded as runnable
fixtures. Document 05's rule: before any material change to mechanism code or
a live task prompt, this suite must pass — it proves the change hasn't
silently altered established, correct behaviour.

Run:  python3 -m pytest tests/ -q     (or plain: python3 tests/test_replay.py)
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "compass_mech"))

from due_rules import compute
from dedup_check import find_candidates

TODAY = "2026-07-25"


def _item(id, title, status, review=None, priority=False, reason=None,
          hard=None, email=None, entity="ProBuild Management Ltd", project=None):
    return {"id": id, "title": title, "status": status, "review_date": review,
            "priority": priority, "priority_reason": reason, "hard_deadline": hard,
            "owed_by_email": email, "entity": entity, "project": project}


# ---------- due_rules: the overdue / priority separation (Martin's rule, 25 Jul)

def test_overdue_now_is_reported_but_never_flagged():
    """Summerfield case: review date passed -> overdue, Priority untouched."""
    r = compute([_item("a", "Build Summerfield programme", "Now", review="2026-07-24")], TODAY)
    assert len(r["overdue"]) == 1 and r["overdue"][0]["days_over"] == 1
    assert r["overdue"][0]["priority"] is False          # never auto-flagged
    assert not r["defaults_to_assign"]                    # never rolled


def test_due_today_counts_as_overdue_day_zero():
    """Plumber case: review date == today -> overdue with days_over 0."""
    r = compute([_item("b", "Chase plumber", "Now", review="2026-07-25",
                       priority=True, reason="tiler starts Wed")], TODAY)
    assert r["overdue"][0]["days_over"] == 0
    assert r["overdue"][0]["priority_reason"] == "tiler starts Wed"


# ---------- due_rules: Holding vs Upcoming semantics (Martin's rule, 25 Jul)

def test_upcoming_activates_on_its_date():
    """Retatrutide case: Upcoming reaching its date -> status write to Now."""
    r = compute([_item("c", "Retatrutide dose", "Upcoming", review="2026-07-25",
                       entity="Personal")], TODAY)
    assert r["activations"] == [{"id": "c", "title": "Retatrutide dose",
                                 "write": {"status": "Now"}}]


def test_upcoming_without_date_gets_question_not_default():
    r = compute([_item("d", "Some future obligation", "Upcoming")], TODAY)
    assert not r["defaults_to_assign"]
    assert len(r["classification_questions"]) == 1


def test_now_and_holding_defaults():
    r = compute([_item("e", "New now item", "Now"),
                 _item("f", "New holding item", "Holding")], TODAY)
    d = {x["id"]: x["new_review_date"] for x in r["defaults_to_assign"]}
    assert d == {"e": "2026-08-01", "f": "2026-08-08"}
    assert all(x["fallback"] for x in r["defaults_to_assign"])


def test_holding_due_routes_by_owed_by_email():
    r = compute([_item("g", "Chaseable", "Holding", review="2026-07-25", email="x@y.com"),
                 _item("h", "Martins own", "Holding", review="2026-07-25")], TODAY)
    assert [x["id"] for x in r["holding_chase"]] == ["g"]
    assert [x["id"] for x in r["holding_question"]] == ["h"]


def test_priority_on_holding_is_a_reported_error():
    """BTL case: Priority on non-Now is a data-quality flag, never silently fixed."""
    r = compute([_item("i", "BTL mortgage", "Holding", review="2026-07-28",
                       priority=True, reason="blocking underwriting")], TODAY)
    assert any(e["error"].startswith("Priority set on non-Now") for e in r["errors"])


# ---------- dedup: the resurrection incidents, 25 Jul 2026

CLOSED = [
    {"id": "jg", "title": "Pay JG Contracting invoice INV-0005 (£1,980), due 24 Jul",
     "closure_reason": "Paid — confirmed by Martin via Slack 24 Jul"},
    {"id": "sq", "title": "Renew Squarespace website subscription — probuildmanagement.co.uk",
     "closure_reason": "Intentionally cancelled — website migrated to Webflow; no renewal needed"},
]
CHRON = [
    {"id": "c1", "entry": "Phase 0 closure: Pay JG Contracting invoice INV-0005 (£1,980), due 24 Jul",
     "interpretation": "Closed 24 Jul in Phase 0. Any further INV-0005 reminders are echoes."},
]


def test_jg_reminder_matches_closed_invoice():
    ev = {"counterparty": "JG Contracting Ltd", "refs": ["INV-0005"],
          "subject": "Invoice #INV-0005 from JG Contracting Ltd is due"}
    hits = find_candidates(ev, CLOSED, CHRON)
    assert hits and hits[0]["signal"] == "reference"
    assert {h["kind"] for h in hits} == {"closed_item", "chronicle"}


def test_squarespace_expiry_matches_closure():
    ev = {"counterparty": "Squarespace", "refs": [],
          "subject": "Your website subscription has expired"}
    hits = find_candidates(ev, CLOSED, CHRON)
    assert any(h["id"] == "sq" for h in hits)


def test_genuinely_new_invoice_matches_nothing():
    ev = {"counterparty": "Nigel Belcher Stone", "refs": ["INV-0006"],
          "subject": "Quotation for coping stones"}
    assert find_candidates(ev, CLOSED, CHRON) == []


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print(f"PASS {name}")
            except AssertionError as e:
                fails += 1; print(f"FAIL {name}: {e}")
    sys.exit(1 if fails else print(f"\nAll tests passed.") or 0)
