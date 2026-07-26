# Executive Compass — mechanism code

**Owner:** Martin Gonzalez-Sayans · **Established:** 26 July 2026 (Stage-1–3 work under canonical document 05)

This repository holds the *deterministic* half of Executive Compass. The governing
principle (canonical document 01, principle 11; conversation of 25 Jul): **judgement
stays with the model, mechanism moves into code.** Anything here behaves identically
on every run, costs nothing to re-run, and is protected by the replay test suite.

## What lives here

| Path | What it is |
|---|---|
| `compass_mech/due_rules.py` | Mechanical due-date computation (doc 02) — overdue, activations, defaults, chase routing, data-quality flags. Pure function. |
| `compass_mech/dedup_check.py` | Dedup-against-closed-work candidate matcher (doc 02). Finds candidates; the model judges echo vs reopening. |
| `compass_mech/snapshot_render.py` | Morning snapshot renderer — the approved landscape four-column format, items.json → HTML (→ PNG via headless Chromium). |
| `tests/test_replay.py` | The canonical replay cases from live operation 24–25 Jul 2026 (JG INV-0005, Squarespace, Summerfield overdue, Retatrutide activation, BTL flag error). Must pass before any change to mechanism code or a live task prompt ships. |

## How the scheduled tasks use this

The cloud tasks cannot read Martin's machine. The **deployment copy** of this code
lives in SharePoint/OneDrive at `Desktop/Executive Compass/Code/`, which the tasks
fetch at run time. GitHub is the source of truth and history; OneDrive is the
deployment target. The deploy step is: tests pass → commit → copy to the OneDrive
`Code/` folder in the same pass.

## Rules (from the canonical set)

- No file here decides anything requiring judgement — classification, closure,
  priority, and interpretation belong to the model under the canonical documents.
- Changing behaviour here is change-controlled like a prompt change: run
  `python3 tests/test_replay.py` first; a failing suite blocks the change.
- The canonical documents govern; where code and canon disagree, that is a defect
  in the code.
