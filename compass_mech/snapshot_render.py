#!/usr/bin/env python3
"""Executive Compass — morning snapshot renderer.

Deterministic renderer for the landscape four-column snapshot (format approved
by Martin, 25 Jul 2026). The scheduled task exports open Items to items.json,
runs this script, and delivers snapshot.png as its output file. Layout and
grouping are code; nothing about the picture is left to model improvisation.

Usage:
    python3 snapshot_render.py items.json out.html "Saturday 25 July" "08:30" \
        [--next-deadline "Appromatt invoices, Mon 27 Jul"]
    <chromium headless_shell> --headless --disable-gpu --no-sandbox \
        --screenshot=out.png --window-size=1760,1500 --hide-scrollbars \
        --force-device-scale-factor=2 file://$PWD/out.html

items.json: list of due_rules-shaped items (see due_rules.py) with extra
optional keys: "hard_deadline_note", "extra".
"""
from __future__ import annotations
import datetime as _dt, html as H, json, sys
from due_rules import compute, NOW, HOLDING, UPCOMING

ENTITY = {  # validated categorical palette (dataviz-checked 25 Jul 2026)
    "ProBuild Management Ltd": ("#2a78d6", "ProBuild"),
    "Locksbridge Land Ltd": ("#eb6834", "Locksbridge"),
    "Personal": ("#1baf7a", "Personal"),
    "Emerging/Dormant Ventures": ("#4a3aa7", "Ventures"),
    "Spain": ("#eda100", "Spain"),
    "Gabrion Holdings": ("#008300", "Gabrion"),
}
CRIT, WARN_BG, WARN_INK = "#d03b3b", "#fdf3dd", "#8a5b00"
WEEK = 7


def _d(iso): return _dt.date.fromisoformat(iso)


def _fmt(iso): return _d(iso).strftime("%a %d").replace(" 0", " ")


def _dot(e):
    c = ENTITY.get(e, ("#898781", e or "?"))[0]
    return f'<span class="dot" style="background:{c}"></span>'


def _row(it, date_label, crit=False, extra=""):
    tag = it.get("project") or ENTITY.get(it.get("entity"), (None, it.get("entity") or ""))[1]
    x = ""
    if extra:
        cls = "extra-crit" if crit or extra.startswith("⚑") else "extra"
        x = f'<div class="{cls}">{H.escape(extra)}</div>'
    dc = "date crit" if crit else "date"
    return (f'<div class="row"><div class="left">{_dot(it.get("entity"))}<div class="tt">'
            f'<div class="t">{H.escape(it["title"])}</div>'
            f'<div class="meta"><span class="tag">{H.escape(tag)}</span></div>{x}</div></div>'
            f'<div class="{dc}">{H.escape(date_label)}</div></div>')


def render(items, today, day_label, asof, next_deadline=""):
    t = _d(today)
    mech = compute(items, today)
    over_ids = {o["id"] for o in mech["overdue"]}
    horizon = t + _dt.timedelta(days=WEEK)
    by_id = {i["id"]: i for i in items}

    def indate(it):  # review date parsed or far-future sentinel
        return _d(it["review_date"]) if it.get("review_date") else _dt.date.max

    over_rows, now_rows, hold_rows, upc_rows = [], [], [], []
    for o in sorted(mech["overdue"], key=lambda x: x["review_date"]):
        it = by_id[o["id"]]
        lbl = "due today" if o["days_over"] == 0 else f'{o["days_over"]} day{"s"*(o["days_over"]>1)} over'
        ex = (lbl + (f' · ⚑ {o["priority_reason"]}' if o["priority"] else ""))
        over_rows.append(_row(it, _fmt(o["review_date"]), crit=True, extra=ex))

    nows = [i for i in items if i["status"] == NOW and i["id"] not in over_ids]
    nows.sort(key=lambda i: (not i.get("priority"), indate(i)))
    for it in nows:
        ex = f'⚑ {it.get("priority_reason","")}' if it.get("priority") else (it.get("extra") or "")
        now_rows.append(_row(it, _fmt(it["review_date"]) if it.get("review_date") else "—", extra=ex))

    holds = sorted((i for i in items if i["status"] == HOLDING and i.get("review_date")), key=indate)
    hold_week = [i for i in holds if indate(i) <= horizon]
    for it in hold_week:
        hold_rows.append(_row(it, _fmt(it["review_date"])))

    upcs = sorted((i for i in items if i["status"] == UPCOMING and i.get("review_date")), key=indate)
    upc_week = [i for i in upcs if indate(i) <= horizon]
    for it in upc_week:
        upc_rows.append(_row(it, _fmt(it["review_date"])))

    legend = "".join(f'<span class="leg">{_dot(e)}{ENTITY[e][1]}</span>'
                     for e in ENTITY if any(i.get("entity") == e for i in items))
    nd = f' · next hard deadline: {H.escape(next_deadline)}' if next_deadline else ""
    later_h, later_u = len(holds) - len(hold_week), len(upcs) - len(upc_week)

    def col(count, label, sub, rows, bar, num_style="", foot=""):
        f = f'<div class="colfoot">{H.escape(foot)}</div>' if foot else ""
        return (f'<div class="col"><div class="colh" style="border-color:{bar}">'
                f'<span class="n" style="{num_style}">{count}</span><div class="l">{label}</div>'
                f'<div class="s">{sub}</div></div>{"".join(rows)}{f}</div>')

    css = """*{margin:0;padding:0;box-sizing:border-box}body{width:1760px;background:#f9f9f7;
font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#0b0b0b;padding:26px}
.card{background:#fcfcfb;border:1px solid rgba(11,11,11,.10);border-radius:14px;padding:24px 28px}
.hdr{display:flex;justify-content:space-between;align-items:baseline}h1{font-size:22px;font-weight:700}
.sub{color:#52514e;font-size:13.5px}.legend{display:flex;gap:14px}
.leg{font-size:12.5px;color:#52514e;display:flex;align-items:center;gap:5px}
.cols{display:flex;gap:22px;margin-top:18px;align-items:flex-start}.col{flex:1;min-width:0}
.colh{border-top:4px solid;border-radius:2px 2px 0 0;padding:8px 2px 6px}
.colh .n{font-size:24px;font-weight:700;line-height:1}
.colh .l{font-size:12.5px;font-weight:700;letter-spacing:.7px;color:#52514e;margin-top:3px}
.colh .s{font-size:11.5px;color:#898781;margin-top:2px}
.row{display:flex;justify-content:space-between;align-items:flex-start;padding:7px 0;
border-bottom:1px solid #eeede8;gap:10px}.col .row:last-of-type{border-bottom:none}
.left{display:flex;gap:8px;min-width:0}.dot{width:9px;height:9px;border-radius:50%;flex:none;margin-top:5px}
.t{font-size:13.5px;line-height:1.3}.meta{margin-top:2px}
.tag{font-size:10.5px;color:#898781;background:#f0efec;border-radius:4px;padding:1px 6px}
.extra{font-size:11.5px;color:#52514e;margin-top:2px}
.extra-crit{font-size:11.5px;color:@WARN_INK;background:@WARN_BG;display:inline-block;border-radius:4px;padding:1px 6px;margin-top:3px}
.date{font-size:12px;color:#52514e;white-space:nowrap;font-variant-numeric:tabular-nums;margin-top:2px}
.date.crit{color:@CRIT;font-weight:700}.colfoot{padding-top:8px;color:#898781;font-size:11.5px}
.foot{margin-top:14px;padding-top:10px;border-top:1px solid #e1e0d9;color:#898781;font-size:12px;
display:flex;justify-content:space-between}""".replace("@WARN_INK", WARN_INK).replace("@WARN_BG", WARN_BG).replace("@CRIT", CRIT)

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head>
<body><div class="card">
<div class="hdr"><div><h1>Executive Compass — {H.escape(day_label)}</h1>
<div class="sub">Snapshot as of {H.escape(asof)} · {len(items)} open items{nd}</div></div>
<div class="legend">{legend}</div></div>
<div class="cols">
{col(len(over_rows), "OVERDUE", "decide or do — repeats daily until resolved", over_rows, CRIT, f"color:{CRIT}")}
{col(len(now_rows), "NOW", "yours to do · ⚑ priority first, then by target date", now_rows, "#2a78d6")}
{col(len(hold_rows), "HOLDING", "on hold — date shown is when each returns to Now", hold_rows, "#52514e",
     foot=(f"+ {later_h} more on hold with later dates — in Airtable" if later_h else ""))}
{col(len(upc_rows), "UPCOMING", "starts on the date shown — nothing to do before then", upc_rows, "#52514e",
     foot=(f"+ {later_u} more starting later — in Airtable" if later_u else ""))}
</div>
<div class="foot"><span>Generated fresh each morning from Airtable — a photograph, not a live view.</span>
<span>⚑ = priority, with its cost stated</span></div>
</div></body></html>"""


if __name__ == "__main__":
    items = json.load(open(sys.argv[1]))
    today = _dt.date.today().isoformat() if len(sys.argv) < 6 else sys.argv[5]
    nd = ""
    if "--next-deadline" in sys.argv:
        nd = sys.argv[sys.argv.index("--next-deadline") + 1]
    open(sys.argv[2], "w").write(render(items, today, sys.argv[3], sys.argv[4], nd))
    print(f"wrote {sys.argv[2]}")
