#!/usr/bin/env python3
"""Build dashboard/index.html and 99-status.md from dashboard/register.toml.

Usage:
    build_dashboard.py                       Write dashboard/index.html and 99-status.md
    build_dashboard.py --check               Validate invariants and verify generated files are fresh
    build_dashboard.py list [kind] [--status open]
    build_dashboard.py show <ID>
    build_dashboard.py add <kind> key=value key:=json ...   (kind: decision question package gate work spend rejected)
    build_dashboard.py set <ID> key=value key:=json ...
    build_dashboard.py set-package <ID> <open|"in progress"|done>
    build_dashboard.py add-work --date YYYY-MM-DD --title "..." --detail "..." [--package WP-xx] [--ref path]
    build_dashboard.py add-spend --date YYYY-MM-DD --item "..." --eur 0.00
    build_dashboard.py answer-question <Q-ID> --date YYYY-MM-DD --answer "..."

key=value stores a string; key:=json stores a number, bool, list, or inline table,
e.g. rejected:='[{"option": "X", "why": "Y"}]'. Every edit is validated before it is
written, so a bad edit leaves register.toml untouched.

Standard library only (Python 3.11+ tomllib). Output is deterministic.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:
    sys.exit("build_dashboard.py needs Python 3.11 or newer (tomllib)")
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / "dashboard" / "register.toml"
OUTPUT_HTML = ROOT / "dashboard" / "index.html"
OUTPUT_STATUS = ROOT / "99-status.md"

DECISION_STATUS = {
    "implemented": "Implemented",
    "specified": "Specified, not built",
    "pending": "Proposed, awaiting you",
}
PACKAGE_STATUS = {"open": "Open", "in progress": "In progress", "done": "Done"}
GATE_STATUS = {"open": "Open", "passed": "Passed"}
EM_DASH = chr(0x2014)


class RegisterError(ValueError):
    pass


def _need(entry: dict[str, Any], keys: tuple[str, ...], where: str) -> None:
    for key in keys:
        value = entry.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise RegisterError(f"{where}: missing '{key}'")


def newest_entry_date(reg: dict[str, Any]) -> str | None:
    dates: list[str] = []
    for d in reg.get("decision", []):
        if d.get("date"):
            dates.append(str(d["date"]))
    for w in reg.get("work", []):
        if w.get("date"):
            dates.append(str(w["date"]))
    for q in reg.get("question", []):
        if q.get("opened"):
            dates.append(str(q["opened"]))
        if q.get("answered_on"):
            dates.append(str(q["answered_on"]))
    for s in reg.get("spend", []):
        if s.get("date"):
            dates.append(str(s["date"]))
    return max(dates) if dates else None


def sync_updated_in_toml_text(raw: str, target_date: str) -> str:
    return re.sub(
        r'(?m)^(\s*updated\s*=\s*)"[^"]*"',
        rf'\g<1>"{target_date}"',
        raw,
        count=1,
    )


def validate(reg: dict[str, Any], *, check_date_sync: bool = True) -> None:
    project = reg.get("project", {})
    _need(project, ("name", "phase", "updated", "launch_target"), "[project]")
    seen: set[str] = set()

    for d in reg.get("decision", []):
        where = f"[[decision]] {d.get('id', '?')}"
        _need(d, ("id", "date", "by", "area", "title", "decided", "status", "implementation"), where)
        if d["id"] in seen:
            raise RegisterError(f"{where}: duplicate id")
        seen.add(d["id"])
        if d["status"] not in DECISION_STATUS:
            raise RegisterError(f"{where}: status must be one of {sorted(DECISION_STATUS)}")
        if d["by"] not in ("owner", "coordinator"):
            raise RegisterError(f"{where}: by must be 'owner' or 'coordinator'")
        for r in d.get("rejected", []):
            _need(r, ("option", "why"), f"{where} rejected")

    for r in reg.get("rejected", []):
        _need(r, ("date", "area", "title", "why", "implication"), f"[[rejected]] {r.get('title', '?')}")

    for q in reg.get("question", []):
        where = f"[[question]] {q.get('id', '?')}"
        _need(q, ("id", "opened", "title", "needed_by", "recommendation", "default", "status"), where)
        if q["id"] in seen:
            raise RegisterError(f"{where}: duplicate id")
        seen.add(q["id"])
        if q["status"] not in ("open", "answered"):
            raise RegisterError(f"{where}: status must be 'open' or 'answered'")
        if q["status"] == "answered":
            _need(q, ("answer", "answered_on"), where)
        brief_path = q.get("brief")
        if brief_path and not (ROOT / brief_path).exists():
            raise RegisterError(f"{where}: brief path '{brief_path}' does not exist")

    gate_ids: set[str] = set()
    for g in reg.get("gate", []):
        _need(g, ("id", "name", "target", "status", "criteria"), f"[[gate]] {g.get('id', '?')}")
        if g["id"] in seen:
            raise RegisterError(f"[[gate]] {g['id']}: duplicate id")
        seen.add(g["id"])
        gate_ids.add(g["id"])
        if g["status"] not in GATE_STATUS:
            raise RegisterError(f"[[gate]] {g['id']}: status must be one of {sorted(GATE_STATUS)}")

    pkg_by_id: dict[str, dict[str, Any]] = {}
    for p in reg.get("package", []):
        _need(p, ("id", "name", "stream", "gate", "status"), f"[[package]] {p.get('id', '?')}")
        if p["id"] in seen:
            raise RegisterError(f"[[package]] {p['id']}: duplicate id")
        seen.add(p["id"])
        if p["status"] not in PACKAGE_STATUS:
            raise RegisterError(f"[[package]] {p['id']}: status must be one of {sorted(PACKAGE_STATUS)}")
        if p["gate"] not in gate_ids:
            raise RegisterError(f"[[package]] {p['id']}: gate '{p['gate']}' is not a [[gate]] id")
        pkg_by_id[p["id"]] = p

    for w in reg.get("work", []):
        where = f"[[work]] {w.get('title', '?')}"
        _need(w, ("date", "title", "detail"), where)
        for ref in w.get("refs", []):
            if not (ROOT / ref).exists():
                raise RegisterError(f"{where}: referenced file '{ref}' does not exist")
        wp_id = w.get("package")
        if wp_id and wp_id not in pkg_by_id:
            raise RegisterError(f"{where}: package '{wp_id}' is not a [[package]] id")
        if wp_id and pkg_by_id[wp_id]["status"] == "open":
            raise RegisterError(
                f"{where}: cites package '{wp_id}', so [[package]] {wp_id} cannot remain status = 'open'"
            )

    for s in reg.get("spend", []):
        _need(s, ("date", "item"), "[[spend]]")
        if not isinstance(s.get("eur"), (int, float)):
            raise RegisterError("[[spend]]: 'eur' must be a number")

    max_date = newest_entry_date(reg)
    if check_date_sync and max_date and str(project["updated"]) != max_date:
        raise RegisterError(
            f"[project].updated is '{project['updated']}', expected newest entry date '{max_date}'"
        )


def e(text: object) -> str:
    return escape(str(text), quote=True)


def anchor(ident: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in ident.lower())


def chip(label: str, kind: str) -> str:
    return f'<span class="chip chip-{kind}">{e(label)}</span>'


def refs_html(refs: list[str]) -> str:
    if not refs:
        return ""
    items = "".join(f"<code>{e(r)}</code>" for r in refs)
    return f'<p class="refs">{items}</p>'


CSS = """
:root {
  --bg: #f3f6f8; --surface: #ffffff; --ink: #13212c; --muted: #566877; --line: #d3dce3;
  --line-strong: #9fb0bc; --warm: #b23f1c; --warm-soft: #f7e3da; --cool: #1c5d8a; --cool-soft: #dcebf5;
  --ok: #17694d; --ok-soft: #d9efe6; --hold: #6a5a12; --hold-soft: #f3ecc9;
  --font-ui: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  --font-num: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0d151b; --surface: #141f27; --ink: #e4ecf1; --muted: #93a5b2; --line: #273641;
    --line-strong: #4b6170; --warm: #f08a63; --warm-soft: #3a2018; --cool: #77b6e0; --cool-soft: #16303f;
    --ok: #62c9a2; --ok-soft: #15332a; --hold: #dcc76a; --hold-soft: #33300f; color-scheme: dark;
  }
}
body { background: var(--bg); color: var(--ink); font-family: var(--font-ui); font-size: 15px; line-height: 1.5; margin: 0; }
.pd-wrap { max-width: 1120px; margin: 0 auto; padding: 28px 16px 64px; display: flex; flex-direction: column; gap: 28px; }
.pd-wrap h1 { font-size: 28px; line-height: 1.15; font-weight: 600; margin: 0; }
.pd-wrap h2 { font-size: 20px; font-weight: 600; margin: 0; }
.pd-wrap h3 { font-size: 15px; font-weight: 600; margin: 0; }
.pd-wrap p { margin: 0; }
.pd-wrap code, .num { font-family: var(--font-num); font-size: 0.87em; font-variant-numeric: tabular-nums; }
.eyebrow { font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.14em; color: var(--muted); }
.head { display: flex; flex-direction: column; gap: 8px; }
.head .phase { color: var(--muted); max-width: 70ch; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
.tile { background: var(--surface); border: 1px solid var(--line); border-radius: 4px; padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }
.tile .big { font-family: var(--font-num); font-size: 26px; line-height: 1.1; }
.tile.attn { border-color: var(--warm); }
.tile.attn .big { color: var(--warm); }
.tile .sub { font-size: 13px; color: var(--muted); }
.gates { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); border: 1px solid var(--line); border-radius: 4px; background: var(--surface); }
.gate { padding: 12px 14px; border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); display: flex; flex-direction: column; gap: 4px; }
.gate .gid { font-family: var(--font-num); font-size: 13px; color: var(--cool); }
.gate .crit { font-size: 13px; color: var(--muted); }
.pd-nav { position: sticky; top: 0; z-index: 5; background: var(--bg); border-bottom: 1px solid var(--line); padding: 10px 0; display: flex; flex-wrap: wrap; gap: 6px 14px; align-items: center; }
.pd-nav a { color: var(--ink); text-decoration: none; font-size: 14px; font-weight: 500; padding: 4px 0; }
.pd-nav .count { font-family: var(--font-num); font-size: 12px; color: var(--muted); margin-left: 4px; }
.pd-nav input { margin-left: auto; flex: 1 1 180px; max-width: 280px; font: inherit; font-size: 14px; padding: 6px 10px; border: 1px solid var(--line-strong); border-radius: 6px; background: var(--surface); color: var(--ink); }
.pd-sec { display: flex; flex-direction: column; gap: 14px; scroll-margin-top: 64px; }
.sec-head p { color: var(--muted); max-width: 78ch; }
.rows { display: flex; flex-direction: column; border: 1px solid var(--line); border-radius: 4px; background: var(--surface); }
.row { padding: 14px 16px; border-bottom: 1px solid var(--line); display: flex; flex-direction: column; gap: 8px; }
.row:last-child { border-bottom: 0; }
.row-top { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: baseline; }
.row-top h3 { flex: 1 1 260px; }
.rid { font-family: var(--font-num); font-size: 13px; color: var(--cool); }
.meta { font-size: 13px; color: var(--muted); }
.kv { display: grid; grid-template-columns: 124px minmax(0, 1fr); gap: 4px 12px; font-size: 14px; }
.kv dt { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.1em; padding-top: 2px; }
.kv dd { margin: 0; overflow-wrap: anywhere; }
.chip { display: inline-block; font-size: 12px; font-weight: 500; line-height: 1; padding: 4px 8px; border-radius: 999px; border: 1px solid transparent; white-space: nowrap; }
.chip-implemented, .chip-done, .chip-passed { background: var(--ok-soft); color: var(--ok); }
.chip-specified, .chip-in-progress { background: var(--cool-soft); color: var(--cool); }
.chip-pending, .chip-attn { background: var(--warm-soft); color: var(--warm); }
.chip-open, .chip-area { border-color: var(--line-strong); color: var(--muted); }
.refs { display: flex; flex-wrap: wrap; gap: 4px 10px; }
.refs code { color: var(--muted); }
.tbl-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 4px; background: var(--surface); }
.tbl-wrap table { border-collapse: collapse; width: 100%; font-size: 14px; }
.tbl-wrap th { text-align: left; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); padding: 10px 14px; border-bottom: 1px solid var(--line-strong); }
.tbl-wrap td { padding: 10px 14px; border-bottom: 1px solid var(--line); vertical-align: top; }
.tbl-wrap tr:last-child td { border-bottom: 0; }
.group-label { padding: 8px 14px; background: var(--bg); font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); }
.empty { padding: 16px; color: var(--muted); }
.foot { font-size: 13px; color: var(--muted); border-top: 1px solid var(--line); padding-top: 14px; }
"""

JS = """
(function () {
  var q = document.getElementById('pd-filter');
  var items = Array.prototype.slice.call(document.querySelectorAll('[data-text]'));
  function apply() {
    var needle = (q.value || '').trim().toLowerCase();
    items.forEach(function (el) { el.hidden = needle !== '' && el.getAttribute('data-text').indexOf(needle) === -1; });
  }
  if (q) { q.addEventListener('input', apply); }
})();
"""


def search_text(*parts: object) -> str:
    return e(" ".join(str(p) for p in parts if p).lower())


def render_html(reg: dict[str, Any]) -> str:
    project = reg["project"]
    decisions = reg.get("decision", [])
    questions = reg.get("question", [])
    open_q = [q for q in questions if q["status"] == "open"]
    answered_q = [q for q in questions if q["status"] == "answered"]
    work = sorted(reg.get("work", []), key=lambda w: w["date"], reverse=True)
    packages = reg.get("package", [])
    gates = reg.get("gate", [])
    spend = sum(float(s["eur"]) for s in reg.get("spend", []))

    counts = {k: sum(1 for d in decisions if d["status"] == k) for k in DECISION_STATUS}
    done_pk = sum(1 for p in packages if p["status"] == "done")
    active_pk = sum(1 for p in packages if p["status"] == "in progress")

    against: list[dict[str, str]] = []
    for d in decisions:
        for r in d.get("rejected", []):
            against.append(
                {
                    "option": r["option"],
                    "why": r["why"],
                    "area": d["area"],
                    "from": d["id"],
                    "from_title": d["title"],
                    "implication": "",
                }
            )
    for r in reg.get("rejected", []):
        against.append(
            {
                "option": r["title"],
                "why": r["why"],
                "area": r["area"],
                "from": "",
                "from_title": r.get("ref", ""),
                "implication": r["implication"],
            }
        )

    out: list[str] = []
    w = out.append
    w("<!doctype html><html lang='en'><head><meta charset='utf-8'>")
    w("<meta name='viewport' content='width=device-width, initial-scale=1'>")
    w(f"<title>{e(project['name'])} Project Dashboard</title>")
    w(f"<style>{CSS}</style></head><body>")
    w('<div class="pd-wrap">')
    w('<header class="head"><span class="eyebrow">Project dashboard</span>')
    w(f"<h1>{e(project['name'])}</h1>")
    w(f'<p class="phase">{e(project["phase"])}. Register updated <span class="num">{e(project["updated"])}</span>.</p>')
    w("</header>")

    w('<section class="tiles" aria-label="Summary">')
    attn = " attn" if open_q else ""
    w(f'<div class="tile{attn}"><span class="eyebrow">Needs your decision</span><span class="big">{len(open_q)}</span><span class="sub">open questions</span></div>')
    w(f'<div class="tile"><span class="eyebrow">Decisions</span><span class="big">{len(decisions)}</span><span class="sub">{counts["implemented"]} implemented, {counts["specified"]} specified, {counts["pending"]} proposed</span></div>')
    w(f'<div class="tile"><span class="eyebrow">Decided against</span><span class="big">{len(against)}</span><span class="sub">options rejected</span></div>')
    w(f'<div class="tile"><span class="eyebrow">Work packages</span><span class="big">{done_pk}/{len(packages)}</span><span class="sub">done, {active_pk} in progress</span></div>')
    w(f'<div class="tile"><span class="eyebrow">Spent</span><span class="big">EUR {spend:.2f}</span><span class="sub">logged spend</span></div>')
    w(f'<div class="tile"><span class="eyebrow">Target</span><span class="big">{e(project["launch_target"])}</span><span class="sub">milestone target</span></div>')
    w("</section>")

    if gates:
        w('<section class="gates" aria-label="Gates">')
        for g in gates:
            w(
                f'<div class="gate"><div class="row-top"><span class="gid">{e(g["id"])}</span>'
                f"{chip(GATE_STATUS[g['status']], anchor(g['status']))}</div>"
                f'<h3>{e(g["name"])}</h3><span class="meta">{e(g["target"])}</span>'
                f'<span class="crit">{e(g["criteria"])}</span></div>'
            )
        w("</section>")

    w('<nav class="pd-nav" aria-label="Sections">')
    w(f'<a href="#open">Needs your decision<span class="count">{len(open_q)}</span></a>')
    w(f'<a href="#done">Done<span class="count">{len(work)}</span></a>')
    w(f'<a href="#decisions">Decisions<span class="count">{len(decisions)}</span></a>')
    w(f'<a href="#against">Decided against<span class="count">{len(against)}</span></a>')
    w(f'<a href="#packages">Work packages<span class="count">{len(packages)}</span></a>')
    w('<input id="pd-filter" type="search" placeholder="Filter all sections" aria-label="Filter all sections">')
    w("</nav>")

    w('<section class="pd-sec" id="open"><div class="sec-head"><h2>Needs your decision</h2></div><div class="rows">')
    if not open_q:
        w('<p class="empty">No open questions.</p>')
    for q in open_q:
        w(f'<article class="row" id="{anchor(q["id"])}" data-text="{search_text(q["id"], q["title"], q["recommendation"])}">')
        w(f'<div class="row-top"><span class="rid">{e(q["id"])}</span><h3>{e(q["title"])}</h3>{chip("Open", "attn")}</div>')
        w('<dl class="kv">')
        w(f"<dt>Needed by</dt><dd>{e(q['needed_by'])}</dd>")
        w(f"<dt>Recommended</dt><dd>{e(q['recommendation'])}</dd>")
        w(f"<dt>If no answer</dt><dd>{e(q['default'])}</dd>")
        if q.get("brief"):
            w(f'<dt>Brief</dt><dd><a href="../{e(q["brief"])}">{e(q["brief"])}</a></dd>')
        w("</dl></article>")
    for q in answered_q:
        w(f'<article class="row" id="{anchor(q["id"])}" data-text="{search_text(q["id"], q["title"], q["answer"])}">')
        w(f'<div class="row-top"><span class="rid">{e(q["id"])}</span><h3>{e(q["title"])}</h3>{chip("Answered", "done")}</div>')
        w(f'<dl class="kv"><dt>Answer</dt><dd>{e(q["answer"])} <span class="meta num">{e(q["answered_on"])}</span></dd></dl></article>')
    w("</div></section>")

    w('<section class="pd-sec" id="done"><div class="sec-head"><h2>What has been done</h2></div><div class="rows">')
    if not work:
        w('<p class="empty">No work logged yet.</p>')
    for item in work:
        w(f'<article class="row" data-text="{search_text(item["title"], item["detail"], item.get("package", ""))}">')
        w(f'<div class="row-top"><span class="rid">{e(item["date"])}</span><h3>{e(item["title"])}</h3>{chip(item.get("package", ""), "area") if item.get("package") else ""}</div>')
        w(f"<p>{e(item['detail'])}</p>{refs_html(item.get('refs', []))}</article>")
    w("</div></section>")

    w('<section class="pd-sec" id="decisions"><div class="sec-head"><h2>Decisions</h2></div><div class="rows">')
    if not decisions:
        w('<p class="empty">No decisions recorded yet.</p>')
    for d in decisions:
        who = "Owner" if d["by"] == "owner" else "Coordinator"
        w(f'<article class="row" id="{anchor(d["id"])}" data-text="{search_text(d["id"], d["title"], d["decided"], d["implementation"], d["area"])}">')
        w(f'<div class="row-top"><span class="rid">{e(d["id"])}</span><h3>{e(d["title"])}</h3>{chip(d["area"], "area")}{chip(DECISION_STATUS[d["status"]], d["status"])}</div>')
        w(f'<dl class="kv"><dt>Decided</dt><dd>{e(d["decided"])} <span class="meta">({who}, {e(d["date"])})</span></dd><dt>Implemented in</dt><dd>{e(d["implementation"])}</dd></dl></article>')
    w("</div></section>")

    w('<section class="pd-sec" id="against"><div class="sec-head"><h2>Decided against</h2></div>')
    w('<div class="tbl-wrap"><table><thead><tr><th>Option rejected</th><th>Why not</th><th>Context</th></tr></thead><tbody>')
    for a in against:
        src = f"{e(a['from'])} {e(a['from_title'])}".strip() or e(a["implication"])
        w(f'<tr data-text="{search_text(a["option"], a["why"], a["area"])}"><td>{e(a["option"])}</td><td>{e(a["why"])}</td><td>{src}</td></tr>')
    w("</tbody></table></div></section>")

    w('<section class="pd-sec" id="packages"><div class="sec-head"><h2>Work packages</h2></div>')
    w('<div class="tbl-wrap"><table><thead><tr><th>Id</th><th>Package</th><th>Stream</th><th>Gate</th><th>Status</th></tr></thead><tbody>')
    for p in packages:
        w(
            f'<tr data-text="{search_text(p["id"], p["name"], p["stream"], p["gate"], p["status"])}">'
            f'<td class="num">{e(p["id"])}</td><td>{e(p["name"])}</td><td>{e(p["stream"])}</td>'
            f'<td class="num">{e(p["gate"])}</td><td>{chip(PACKAGE_STATUS[p["status"]], anchor(p["status"]))}</td></tr>'
        )
    w("</tbody></table></div></section>")

    w('<p class="foot">Built deterministically from <code>dashboard/register.toml</code> by <code>tools/build_dashboard.py</code>.</p>')
    w(f"</div><script>{JS}</script></body></html>\n")
    html = "\n".join(out)
    if EM_DASH in html:
        raise RegisterError("register.toml contains an em dash (U+2014)")
    return html


def render_status_md(reg: dict[str, Any]) -> str:
    project = reg["project"]
    questions = reg.get("question", [])
    open_q = [q for q in questions if q["status"] == "open"]
    packages = reg.get("package", [])
    gates = reg.get("gate", [])
    work = sorted(reg.get("work", []), key=lambda w: w["date"], reverse=True)
    spend = sum(float(s["eur"]) for s in reg.get("spend", []))

    lines: list[str] = [
        "# 99 - Status",
        "",
        "Generated deterministically from `dashboard/register.toml` by `tools/build_dashboard.py`. Do not hand-edit.",
        "",
        f"- **Project**: {project['name']}",
        f"- **Phase**: {project['phase']}",
        f"- **Updated**: {project['updated']}",
        f"- **Target**: {project['launch_target']}",
        f"- **Logged spend**: EUR {spend:.2f}",
        "",
        "## Gates",
        "",
        "| Gate | Name | Target | Status | Criteria |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for g in gates:
        lines.append(f"| `{g['id']}` | {g['name']} | {g['target']} | {g['status']} | {g['criteria']} |")

    lines.extend(
        [
            "",
            "## Open Owner Questions",
            "",
        ]
    )
    if not open_q:
        lines.append("None.")
    else:
        lines.append("| ID | Question | Needed by | Recommendation | Brief |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for q in open_q:
            brief = f"`{q['brief']}`" if q.get("brief") else "n/a"
            lines.append(f"| `{q['id']}` | {q['title']} | {q['needed_by']} | {q['recommendation']} | {brief} |")

    lines.extend(
        [
            "",
            "## Work Packages",
            "",
            "| ID | Name | Stream | Gate | Status |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
    )
    for p in packages:
        lines.append(f"| `{p['id']}` | {p['name']} | {p['stream']} | `{p['gate']}` | {p['status']} |")

    lines.extend(
        [
            "",
            "## Recent Work (Latest 15)",
            "",
        ]
    )
    if not work:
        lines.append("No completed work entries yet.")
    else:
        for w in work[:15]:
            pkg = f" ({w['package']})" if w.get("package") else ""
            lines.append(f"- **{w['date']}{pkg} - {w['title']}**: {w['detail']}")

    status_md = "\n".join(lines) + "\n"
    if EM_DASH in status_md:
        raise RegisterError("register.toml contains an em dash (U+2014)")
    return status_md


# ---------------------------------------------------------------------------
# CLI edits. register.toml is edited as text so comments and layout survive.
# Every edit is re-parsed and validated before anything is written to disk.

KINDS = ("decision", "question", "package", "gate", "work", "spend", "rejected")
ID_KINDS = ("decision", "question", "package", "gate")
HEADER_RE = re.compile(r"^\[\[?([A-Za-z0-9_.-]+)\]\]?\s*(#.*)?$")
BARE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise RegisterError(f"number must be finite, got {value}")
        return repr(value)
    if isinstance(value, str):
        out: list[str] = []
        for ch in value:
            if ch == "\\":
                out.append("\\\\")
            elif ch == '"':
                out.append('\\"')
            elif ch == "\n":
                out.append("\\n")
            elif ch == "\r":
                out.append("\\r")
            elif ch == "\t":
                out.append("\\t")
            elif ord(ch) < 0x20 or ord(ch) == 0x7F:
                out.append(f"\\u{ord(ch):04x}")
            else:
                out.append(ch)
        return '"' + "".join(out) + '"'
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(v) for v in value) + "]"
    if isinstance(value, dict):
        for key in value:
            if not BARE_KEY_RE.match(str(key)):
                raise RegisterError(f"invalid key '{key}'")
        return "{ " + ", ".join(f"{k} = {toml_value(v)}" for k, v in value.items()) + " }"
    raise RegisterError(f"unsupported value type {type(value).__name__}")


def split_blocks(raw: str) -> list[tuple[str, list[str]]]:
    """Split into [(table name, lines)] in file order. Lines include the header."""
    blocks: list[tuple[str, list[str]]] = [("", [])]
    for line in raw.splitlines():
        match = HEADER_RE.match(line)
        if match:
            blocks.append((match.group(1), [line]))
        else:
            blocks[-1][1].append(line)
    return blocks


def join_blocks(blocks: list[tuple[str, list[str]]]) -> str:
    return "\n".join(line for _, lines in blocks for line in lines).rstrip() + "\n"


def find_item(raw: str, item_id: str) -> tuple[list[tuple[str, list[str]]], int, str, dict[str, Any]]:
    """Locate an id'd entry. The n-th [[kind]] header is the n-th parsed item."""
    reg = tomllib.loads(raw)
    blocks = split_blocks(raw)
    for kind in ID_KINDS:
        items = reg.get(kind, [])
        ids = [item.get("id") for item in items]
        if item_id in ids:
            n = ids.index(item_id)
            positions = [i for i, (name, _) in enumerate(blocks) if name == kind]
            return blocks, positions[n], kind, items[n]
    raise RegisterError(f"id '{item_id}' not found in register.toml")


def set_keys(lines: list[str], values: dict[str, Any]) -> list[str]:
    lines = list(lines)
    for key, value in values.items():
        new_line = f"{key} = {toml_value(value)}"
        key_re = re.compile(rf"^\s*{re.escape(key)}\s*=")
        idx = next((i for i, line in enumerate(lines) if key_re.match(line)), None)
        if idx is None:
            end = len(lines)
            while end > 1 and not lines[end - 1].strip():
                end -= 1
            lines.insert(end, new_line)
            continue
        try:
            tomllib.loads(lines[idx])
        except tomllib.TOMLDecodeError:
            raise RegisterError(f"'{key}' spans several lines; edit it by hand") from None
        lines[idx] = new_line
    return lines


def edit_item(raw: str, item_id: str, values: dict[str, Any]) -> str:
    blocks, idx, _, _ = find_item(raw, item_id)
    name, lines = blocks[idx]
    blocks[idx] = (name, set_keys(lines, values))
    return join_blocks(blocks)


def append_block(raw: str, kind: str, values: dict[str, Any]) -> str:
    if kind not in KINDS:
        raise RegisterError(f"kind must be one of {list(KINDS)}")
    body = [f"[[{kind}]]"] + [f"{k} = {toml_value(v)}" for k, v in values.items()]
    return raw.rstrip() + "\n\n" + "\n".join(body) + "\n"


def start_package(raw: str, pkg_id: str) -> str:
    """Logging work against a package moves it from open to in progress, never to done."""
    packages = {p.get("id"): p for p in tomllib.loads(raw).get("package", [])}
    if pkg_id not in packages:
        raise RegisterError(f"[[package]] '{pkg_id}' does not exist")
    if packages[pkg_id].get("status") == "open":
        return edit_item(raw, pkg_id, {"status": "in progress"})
    return raw


def add_entry(raw: str, kind: str, values: dict[str, Any]) -> str:
    if kind == "work" and values.get("package"):
        raw = start_package(raw, str(values["package"]))
    return append_block(raw, kind, values)


def parse_pairs(pairs: list[str]) -> dict[str, Any]:
    """key=value stores a string; key:=json stores a number, bool, list, or table."""
    out: dict[str, Any] = {}
    for pair in pairs:
        key, sep, val = pair.partition("=")
        if not sep:
            raise RegisterError(f"expected key=value or key:=json, got '{pair}'")
        if key.endswith(":"):
            key = key[:-1]
            try:
                out_val: Any = json.loads(val)
            except json.JSONDecodeError as err:
                raise RegisterError(f"{key}: invalid JSON ({err})") from None
        else:
            out_val = val
        if not BARE_KEY_RE.match(key):
            raise RegisterError(f"invalid key '{key}'")
        out[key] = out_val
    return out


def commit(raw: str) -> int:
    """Validate the edited text, then write it and rebuild. Nothing is written on error."""
    if EM_DASH in raw:
        raise RegisterError("edit contains an em dash (U+2014); nothing written")
    try:
        reg = tomllib.loads(raw)
    except tomllib.TOMLDecodeError as err:
        raise RegisterError(f"edit would produce invalid TOML ({err}); nothing written") from None
    validate(reg, check_date_sync=False)
    REGISTER.write_text(raw, encoding="utf-8", newline="\n")
    return build_and_write(check_only=False)


def label_of(item: dict[str, Any]) -> str:
    return str(item.get("title") or item.get("name") or item.get("item") or "")


def cmd_list(raw: str, kind: str | None, status: str | None) -> None:
    reg = tomllib.loads(raw)
    for k in [kind] if kind else list(ID_KINDS):
        for item in reg.get(k, []):
            if status and item.get("status") != status:
                continue
            key = item.get("id") or item.get("date") or ""
            print(f"{k:<9} {key:<12} {item.get('status', ''):<12} {label_of(item)}")


def cmd_show(raw: str, item_id: str) -> None:
    blocks, idx, _, _ = find_item(raw, item_id)
    print("\n".join(blocks[idx][1]).rstrip())


def build_and_write(*, check_only: bool) -> int:
    raw = REGISTER.read_text(encoding="utf-8")
    try:
        reg = tomllib.loads(raw)
    except tomllib.TOMLDecodeError as err:
        print(f"register error: dashboard/register.toml is not valid TOML ({err})", file=sys.stderr)
        return 1

    if not check_only:
        max_date = newest_entry_date(reg)
        if max_date and str(reg.get("project", {}).get("updated", "")) != max_date:
            raw = sync_updated_in_toml_text(raw, max_date)
            REGISTER.write_text(raw, encoding="utf-8", newline="\n")
            reg = tomllib.loads(raw)

    try:
        validate(reg, check_date_sync=True)
        html = render_html(reg)
        status_md = render_status_md(reg)
    except RegisterError as err:
        print(f"register error: {err}", file=sys.stderr)
        return 1

    if check_only:
        current_html = OUTPUT_HTML.read_text(encoding="utf-8") if OUTPUT_HTML.exists() else ""
        current_status = OUTPUT_STATUS.read_text(encoding="utf-8") if OUTPUT_STATUS.exists() else ""
        if current_html != html:
            print("dashboard/index.html is stale: run python3 tools/build_dashboard.py", file=sys.stderr)
            return 1
        if current_status != status_md:
            print("99-status.md is stale: run python3 tools/build_dashboard.py", file=sys.stderr)
            return 1
        print("dashboard and 99-status.md are current")
        return 0

    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(html, encoding="utf-8", newline="\n")
    OUTPUT_STATUS.write_text(status_md, encoding="utf-8", newline="\n")
    print(
        f"wrote {OUTPUT_HTML.relative_to(ROOT).as_posix()} ({len(html):,} bytes) "
        f"and {OUTPUT_STATUS.relative_to(ROOT).as_posix()} ({len(status_md):,} bytes)"
    )
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv == ["--check"]:
        return build_and_write(check_only=bool(argv))

    parser = argparse.ArgumentParser(prog="build_dashboard.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="one line per entry")
    p_list.add_argument("kind", nargs="?", choices=KINDS)
    p_list.add_argument("--status", default=None)

    p_show = sub.add_parser("show", help="print one entry by id")
    p_show.add_argument("id")

    p_add = sub.add_parser("add", help="append an entry: add <kind> key=value key:=json ...")
    p_add.add_argument("kind", choices=KINDS)
    p_add.add_argument("pairs", nargs="+")

    p_set = sub.add_parser("set", help="change fields of an entry: set <ID> key=value ...")
    p_set.add_argument("id")
    p_set.add_argument("pairs", nargs="+")

    p_pkg = sub.add_parser("set-package")
    p_pkg.add_argument("id")
    p_pkg.add_argument("status", choices=sorted(PACKAGE_STATUS))

    p_work = sub.add_parser("add-work")
    p_work.add_argument("--date", required=True)
    p_work.add_argument("--title", required=True)
    p_work.add_argument("--detail", required=True)
    p_work.add_argument("--package", default=None)
    p_work.add_argument("--ref", action="append", default=[])

    p_spend = sub.add_parser("add-spend")
    p_spend.add_argument("--date", required=True)
    p_spend.add_argument("--item", required=True)
    p_spend.add_argument("--eur", type=float, required=True)

    p_ans = sub.add_parser("answer-question")
    p_ans.add_argument("id")
    p_ans.add_argument("--date", required=True)
    p_ans.add_argument("--answer", required=True)

    args = parser.parse_args(argv)
    raw = REGISTER.read_text(encoding="utf-8")

    try:
        if args.cmd == "list":
            cmd_list(raw, args.kind, args.status)
            return 0
        if args.cmd == "show":
            cmd_show(raw, args.id)
            return 0
        if args.cmd == "add":
            raw = add_entry(raw, args.kind, parse_pairs(args.pairs))
        elif args.cmd == "set":
            raw = edit_item(raw, args.id, parse_pairs(args.pairs))
        elif args.cmd == "set-package":
            if find_item(raw, args.id)[2] != "package":
                raise RegisterError(f"'{args.id}' is not a [[package]]")
            raw = edit_item(raw, args.id, {"status": args.status})
        elif args.cmd == "add-work":
            values: dict[str, Any] = {"date": args.date}
            if args.package:
                values["package"] = args.package
            values.update({"title": args.title, "detail": args.detail})
            if args.ref:
                values["refs"] = args.ref
            raw = add_entry(raw, "work", values)
        elif args.cmd == "add-spend":
            raw = add_entry(raw, "spend", {"date": args.date, "item": args.item, "eur": args.eur})
        elif args.cmd == "answer-question":
            _, _, kind, item = find_item(raw, args.id)
            if kind != "question" or item.get("status") != "open":
                raise RegisterError(f"'{args.id}' is not an open [[question]]")
            raw = edit_item(
                raw, args.id, {"status": "answered", "answered_on": args.date, "answer": args.answer}
            )
        return commit(raw)
    except (RegisterError, tomllib.TOMLDecodeError) as err:
        print(f"register error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
