#!/usr/bin/env python3
"""Render a CT2 helm decision record into a self-contained canvas HTML page.

This module is the HTML provider format for the Decision Bridge. See
spec/helm-canvas.md. Standard library only; the output references no external
CSS, fonts, or scripts and works from file://.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any

PRIORITIES = ["low", "medium", "high", "critical"]
SCOPE_STATES = ("in", "out", "hold")
_SMART_QUOTES = "“”‘’"


def _excerpt(raw: str, pos: int, window: int = 40) -> str:
    start = max(0, pos - window)
    end = min(len(raw), pos + window)
    rel = pos - start
    body = raw[start:end].replace("\n", "⏎")
    return f"{body[:rel]}<<here>>{body[rel:]}"


def _diagnose_json(raw: str) -> list[str]:
    hints = []
    if any(ch in raw for ch in _SMART_QUOTES):
        hints.append(
            "spec contains smart quotes (“ ” ‘ ’) — "
            "replace with ASCII \" and ' (Claude heredocs sometimes auto-correct)"
        )
    if re.search(r",\s*[}\]]", raw):
        hints.append("possibly a trailing comma before } or ] (JSON forbids them)")
    if re.search(r"(?m)^\s*//", raw) or "/*" in raw:
        hints.append("possibly a // or /* comment (JSON has no comment syntax)")
    return hints


def parse_spec(raw: str) -> dict:
    """Parse a canvas spec JSON string with actionable error context.

    On JSONDecodeError, raises ValueError carrying line/column, an excerpt of
    the offending region, and named hints for common Claude-emitted mistakes
    (smart quotes, trailing commas, // comments). Strips a leading BOM.
    """
    if raw is None or not raw.strip():
        raise ValueError("empty spec — expected a JSON object")
    if raw.startswith("\ufeff"):
        raw = raw.lstrip("\ufeff")
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        snippet = _excerpt(raw, exc.pos)
        hints = _diagnose_json(raw)
        hint_text = ("\n  hint: " + "; ".join(hints)) if hints else ""
        raise ValueError(
            f"spec JSON malformed at line {exc.lineno} col {exc.colno}: {exc.msg}"
            f"\n  near: {snippet}{hint_text}"
        ) from exc
    if not isinstance(obj, dict):
        raise ValueError("spec must be a JSON object at the top level")
    return obj


def validate_spec(spec: dict) -> list[str]:
    """Return a list of 'path: message' validation errors. Empty list = valid.

    Catches the shapes the renderer assumes so a malformed spec fails fast at
    the boundary instead of producing a half-broken canvas where the AI's
    judgment never surfaces.
    """
    errors: list[str] = []
    if not isinstance(spec, dict):
        return ["root: must be a JSON object"]

    ticket = spec.get("ticket")
    if not ticket:
        errors.append("ticket: required (non-empty string)")
    elif not isinstance(ticket, str):
        errors.append("ticket: must be a string")

    canvas = spec.get("canvas")
    if canvas is None:
        errors.append("canvas: required (object)")
        return errors
    if not isinstance(canvas, dict):
        errors.append("canvas: must be an object")
        return errors

    rnd = canvas.get("round", 0)
    # bool is a subclass of int in Python, so the isinstance(rnd, bool) clause
    # is load-bearing: it rejects {"round": true/false} which would otherwise pass.
    if not isinstance(rnd, int) or isinstance(rnd, bool):
        errors.append("canvas.round: must be an integer")

    interp = canvas.get("interpretation")
    if interp is not None and not isinstance(interp, dict):
        errors.append("canvas.interpretation: must be an object")

    scope = canvas.get("scope")
    if scope is not None:
        if not isinstance(scope, list):
            errors.append("canvas.scope: must be a list")
        else:
            for i, item in enumerate(scope):
                if not isinstance(item, dict):
                    errors.append(f"canvas.scope[{i}]: must be an object")
                    continue
                state = item.get("state", "in")
                if state not in SCOPE_STATES:
                    errors.append(
                        f"canvas.scope[{i}].state: must be one of in|out|hold (got {state!r})"
                    )

    tickets = canvas.get("tickets")
    if tickets is not None:
        if not isinstance(tickets, list):
            errors.append("canvas.tickets: must be a list")
        else:
            for i, tk in enumerate(tickets):
                if not isinstance(tk, dict):
                    errors.append(f"canvas.tickets[{i}]: must be an object")
                    continue
                items = tk.get("items")
                if items is not None and not isinstance(items, list):
                    errors.append(f"canvas.tickets[{i}].items: must be a list")

    ac = canvas.get("acceptance_criteria")
    if ac is not None and not isinstance(ac, list):
        errors.append("canvas.acceptance_criteria: must be a list")

    priority = canvas.get("priority")
    if priority is not None and priority not in PRIORITIES:
        errors.append(
            f"canvas.priority: must be one of low|medium|high|critical (got {priority!r})"
        )

    constraints = canvas.get("constraints")
    if constraints is not None and not isinstance(constraints, list):
        errors.append("canvas.constraints: must be a list")

    return errors


def _safe_json_for_script(obj: Any) -> str:
    """JSON encoding safe to embed inline in a <script> tag.

    Replaces the characters that let JSON content break out of <script> — `<`,
    `>`, `&`, plus the line/paragraph separators that some browsers treat as
    JS line terminators — with their `\\uXXXX` form. The output stays valid
    JSON (these are all standard `\\uXXXX` escapes) and decodes byte-for-byte
    back to the input via JSON.parse on the client.
    """
    raw = json.dumps(obj, ensure_ascii=False)
    return (
        raw.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )

_CSS = """
:root{--bg:#f6f5f1;--surface:#fffefb;--raised:#fbfaf6;--ink:#1b1a17;--mut:#6e6a61;
--faint:#9a958a;--line:#e7e3d8;--accent:#1d4ed8;--accent-soft:#eaeefb;--in:#15803d;
--in-soft:#e7f2ea;--out:#b4332a;--out-soft:#f6e9e7;--hold:#b06f0d;--hold-soft:#f7efdf;
--r:12px;--shadow:0 1px 2px rgba(40,36,28,.05),0 8px 24px -12px rgba(40,36,28,.18)}
*{box-sizing:border-box;margin:0;padding:0}html,body{background:var(--bg)}
body{color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
-webkit-font-smoothing:antialiased;padding:32px 22px 60px}
.wrap{max-width:1180px;margin:0 auto}
code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.eyebrow{display:inline-flex;align-items:center;gap:7px;font-size:11px;font-weight:700;
letter-spacing:.11em;color:var(--accent);text-transform:uppercase}
.eyebrow::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--accent)}
h1.title{font-size:24px;font-weight:680;letter-spacing:-.02em;margin:8px 0 6px}
.lede{color:var(--mut);font-size:14px;max-width:66ch}.lede b{color:var(--ink);font-weight:600}
.cstate{margin-top:9px;font-size:11.5px;color:var(--mut)}
.cstate code{background:var(--raised);border:1px solid var(--line);padding:2px 7px;
border-radius:5px;font-size:11px}.cstate code b{color:var(--accent)}
.flow{display:flex;margin:16px 0 20px;border:1px solid var(--line);border-radius:10px;
overflow:hidden;background:var(--surface);box-shadow:var(--shadow)}
.step{flex:1;padding:9px 12px;border-right:1px solid var(--line)}.step:last-child{border-right:0}
.step .s{font:700 10px/1 ui-monospace,monospace;color:var(--faint);letter-spacing:.04em}
.step .t{font-size:11.5px;color:var(--mut);margin-top:3px;line-height:1.35}
.step.done{background:var(--in-soft)}.step.done .s{color:var(--in)}
.step.now{background:var(--accent-soft)}.step.now .s{color:var(--accent)}
.step.now .t{color:var(--ink);font-weight:600}
.grid{display:grid;grid-template-columns:1fr;gap:18px}
@media(min-width:920px){.grid{grid-template-columns:1.55fr 1fr;align-items:start}}
@media(min-width:920px){.right{position:sticky;top:24px}}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
margin-bottom:14px;box-shadow:var(--shadow);overflow:hidden}
.panel-hd{display:flex;align-items:baseline;gap:9px;padding:13px 16px 11px}
.panel-hd .num{font:700 11px/1 ui-monospace,monospace;color:var(--faint);
border:1px solid var(--line);border-radius:5px;padding:4px 6px}
.panel-hd h2{font-size:14px;font-weight:660}
.panel-hd .meta{margin-left:auto;font-size:11.5px;color:var(--faint)}
.panel-bd{padding:2px 16px 15px}
.resolved-tick{color:var(--in);font-weight:700}.open-tick{color:var(--hold);font-weight:700}
.edit{outline:none;border-radius:5px;padding:2px 5px;margin:-2px -2px;cursor:text;
transition:background .12s,box-shadow .12s;
overflow-wrap:anywhere;word-break:break-word;max-width:100%}
.edit:hover{background:var(--accent-soft)}
.edit:focus{background:#fff;box-shadow:0 0 0 2px var(--accent)}
.edit:empty::before{content:attr(data-ph);color:var(--faint)}
.chip .lbl{max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.t-title,.t-item .it,.ac .txt{overflow-wrap:anywhere;word-break:break-word}
.render-fail{margin:10px 15px;padding:9px 11px;border:1px solid var(--out);
background:var(--out-soft);border-radius:8px;font-size:12px;color:var(--out);display:none}
.render-fail.on{display:block}.render-fail b{display:block;margin-bottom:4px}
.edithint{font-size:11px;color:var(--faint);margin-top:7px}.edithint b{color:var(--mut)}
.quote{border-left:2.5px solid var(--accent);background:var(--accent-soft);padding:8px 13px;
border-radius:0 7px 7px 0;color:#33405e;font-size:13.5px;margin:9px 0}
.askrow{display:flex;gap:8px;margin-top:4px}
.pick{flex:1;cursor:pointer;border:1px solid var(--line);background:var(--raised);
border-radius:8px;padding:9px 11px;font-size:13px;text-align:left;color:var(--ink)}
.pick small{display:block;color:var(--mut);font-size:11.5px;margin-top:1px}
.pick[aria-pressed="true"]{border-color:var(--accent);background:var(--accent-soft);
box-shadow:inset 0 0 0 1px var(--accent)}
.pick.warn[aria-pressed="true"]{border-color:var(--hold);background:var(--hold-soft);
box-shadow:inset 0 0 0 1px var(--hold)}
textarea.free{width:100%;margin-top:9px;background:var(--raised);color:var(--ink);
border:1px solid var(--line);border-radius:8px;padding:9px 11px;font:13px/1.55 inherit;
resize:vertical;min-height:62px}
textarea.free:focus{outline:none;border-color:var(--accent);background:#fff}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin:4px 0 6px}
.chip{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line);
border-radius:8px;padding:6px 9px;font-size:13px;background:var(--raised)}
.chip .dot{width:8px;height:8px;border-radius:2px;background:var(--faint)}
.chip .st{font:700 10px/1 ui-monospace,monospace;color:var(--faint);cursor:pointer;
border:1px solid var(--line);border-radius:5px;padding:3px 5px;background:var(--surface);user-select:none}
.chip .x,.ac .x,.con .x,.tcard-top .x,.t-item .li-x{cursor:pointer;color:var(--faint);
font-size:13px;line-height:1.4;user-select:none}
.chip .x:hover,.ac .x:hover,.con .x:hover,.tcard-top .x:hover,.t-item .li-x:hover{color:var(--out)}
.chip[data-s="in"]{border-color:var(--in);background:var(--in-soft)}
.chip[data-s="in"] .dot{background:var(--in)}.chip[data-s="in"] .st{color:var(--in);border-color:var(--in)}
.chip[data-s="out"]{border-color:var(--out-soft);background:var(--out-soft);color:var(--mut)}
.chip[data-s="out"] .dot{background:var(--out)}.chip[data-s="out"] .st{color:var(--out);border-color:var(--out)}
.chip[data-s="out"] .lbl{text-decoration:line-through;text-decoration-color:var(--out)}
.chip[data-s="hold"]{border-color:var(--hold);background:var(--hold-soft)}
.chip[data-s="hold"] .dot{background:var(--hold);border-radius:50%}
.chip[data-s="hold"] .st{color:var(--hold);border-color:var(--hold)}
.addbtn{cursor:pointer;border:1px dashed var(--line);background:none;border-radius:7px;
padding:6px 11px;font-size:12px;color:var(--mut)}
.addbtn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-soft)}
.addbtn.mini{padding:3px 9px;font-size:11px;margin-top:7px}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:9px}
@media(max-width:560px){.cards{grid-template-columns:1fr}}
.tcard{border:1px solid var(--line);border-radius:9px;padding:11px 12px;background:var(--raised)}
.tcard-top{display:flex;align-items:flex-start;gap:6px}
.t-title{flex:1;font-size:13px;font-weight:640}
.t-size{font:700 10px/1.3 ui-monospace,monospace;color:var(--accent);background:var(--accent-soft);
padding:3px 6px;border-radius:4px;display:inline-block;margin-top:6px}
.t-items{list-style:none;margin:8px 0 0}
.t-item{display:flex;align-items:flex-start;gap:6px;padding:2px 0;color:var(--mut);font-size:12px}
.t-item .it{flex:1}
.ac{display:flex;align-items:flex-start;gap:9px;padding:9px 0;border-top:1px solid var(--line)}
.ac:first-child{border-top:0}
.ac input[type=checkbox]{margin-top:4px;width:15px;height:15px;accent-color:var(--in);cursor:pointer}
.ac .txt{flex:1;font-size:13px;min-height:20px}
.ac .flag{font:600 10.5px/1 ui-monospace,monospace;cursor:pointer;border:1px solid var(--line);
background:var(--surface);color:var(--faint);border-radius:5px;padding:4px 7px}
.ac .flag.on{border-color:var(--hold);background:var(--hold-soft);color:var(--hold)}
.prio{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
input[type=range]{flex:1 1 200px;accent-color:var(--accent)}
.prio-val{font:700 12px/1 ui-monospace,monospace;padding:6px 10px;border-radius:6px;
background:var(--accent-soft);color:var(--accent);min-width:78px;text-align:center}
.depgraph{margin-top:11px;overflow-x:auto}.depgraph:empty{display:none}
.depedit,.con{display:flex;gap:10px;font-size:13px}
.depedit{margin-top:10px}.con{padding:7px 0;border-top:1px solid var(--line)}
.con:first-child{border-top:0}
.depedit .k,.con .k{flex:none;width:64px;color:var(--faint);font-size:11.5px}
.depedit .v,.con .v{flex:1}
.summary{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
box-shadow:var(--shadow);overflow:hidden;margin-bottom:14px}
.summary .hd{padding:12px 15px 4px;font-size:11px;font-weight:700;letter-spacing:.1em;
text-transform:uppercase;color:var(--faint)}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line);
border-top:1px solid var(--line);margin-top:9px}
.stat{background:var(--surface);padding:12px 15px}
.stat .v{font-size:23px;font-weight:700}.stat .v.adv{color:var(--hold)}.stat .v.adv0{color:var(--in)}
.stat .l{font-size:11.5px;color:var(--mut);margin-top:1px}
.block{padding:11px 15px;border-top:1px solid var(--line)}
.block .lbl{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;
color:var(--faint);margin-bottom:7px}
.delta ul,.advis ul{list-style:none}
.delta li{font-size:12.5px;padding:5px 0;border-top:1px solid var(--line);display:flex;gap:7px}
.delta li:first-of-type{border-top:0}
.delta li .f{font:700 10px/1.4 ui-monospace,monospace;color:var(--accent);
background:var(--accent-soft);padding:3px 6px;border-radius:4px;height:fit-content}
.none{font-size:12.5px;color:var(--faint);font-style:italic}
.advis li{font-size:12.5px;padding:6px 0;border-top:1px solid var(--line);display:flex;gap:8px;color:var(--mut)}
.advis li:first-of-type{border-top:0}.advis li .ic{color:var(--hold)}
.advis .hint{font-size:11px;color:var(--faint);margin-top:7px;line-height:1.5}
pre.json{margin:0 15px 14px;background:#1c1b17;color:#e8e4d8;border-radius:8px;padding:12px 13px;
font:11.5px/1.55 ui-monospace,monospace;overflow:auto;max-height:280px;transition:box-shadow .4s}
pre.json.flash{box-shadow:0 0 0 2px var(--accent)}
pre.json .k{color:#9ecbff}pre.json .s{color:#c3e88d}pre.json .n{color:#f7a35c}pre.json .b{color:#c792ea}
.commit{padding:13px 15px;border-top:1px solid var(--line);background:var(--raised)}
button.go{width:100%;border:0;border-radius:9px;padding:12px;font-size:14px;font-weight:660;
cursor:pointer;background:var(--accent);color:#fff}
button.go:hover{filter:brightness(1.07)}
button.dl{width:100%;margin-top:8px;border:1px solid var(--line);border-radius:9px;padding:9px;
font-size:12.5px;cursor:pointer;background:var(--surface);color:var(--mut)}
button.dl:hover{border-color:var(--accent);color:var(--accent)}
.gatemsg{font-size:11.5px;color:var(--mut);margin-top:7px;text-align:center}
.gatemsg b{color:var(--hold)}
.donebox{display:none;margin-top:10px}
.donebox textarea{width:100%;background:#1c1b17;color:#e8e4d8;border:0;border-radius:8px;
padding:10px;font:11px/1.5 ui-monospace,monospace;min-height:92px;resize:vertical}
.donebox .copied{font-size:12px;color:var(--in);font-weight:600;margin-top:6px;display:block}
footer.note{margin-top:24px;color:var(--faint);font-size:11.5px;text-align:center;line-height:1.7}
"""


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _panel(num: str, title: str, meta_id: str, meta_text: str, body: str) -> str:
    meta = f'<span class="meta" data-meta="{meta_id}">{esc(meta_text)}</span>' if meta_id else (
        f'<span class="meta">{esc(meta_text)}</span>' if meta_text else "")
    return (f'<section class="panel" id="p-{meta_id or num}"><div class="panel-hd">'
            f'<span class="num">{num}</span><h2>{esc(title)}</h2>{meta}</div>'
            f'<div class="panel-bd">{body}</div></section>')


def _panel_interpret(canvas: dict) -> str:
    interp = canvas.get("interpretation") or {}
    body = (
        f'<p>{esc(interp.get("summary"))}</p>'
        f'<div class="quote">{esc(interp.get("quote"))}</div>'
        '<div class="askrow">'
        '<button class="pick" data-misread="ok" aria-pressed="false">Looks right<small>Proceed as-is</small></button>'
        '<button class="pick warn" data-misread="wrong" aria-pressed="false">Needs correction<small>Write below</small></button>'
        '</div>'
        '<textarea class="free" id="misreadNote" style="display:none" '
        'placeholder="How should helm interpret this? Write freely."></textarea>')
    return _panel("01", "helm's interpretation", "interpret", "Review suggested", body)


def _panel_scope(canvas: dict) -> str:
    chips = []
    for item in canvas.get("scope") or []:
        state = item.get("state", "in")
        chips.append(
            f'<span class="chip" data-s="{esc(state)}" data-key="{esc(item.get("key",""))}">'
            f'<span class="dot"></span><span class="lbl edit" contenteditable="true">{esc(item.get("label"))}</span>'
            f'<span class="st" role="button" tabindex="0">{esc(state.upper())}</span>'
            f'<span class="x" role="button" tabindex="0" aria-label="Delete">&#10005;</span></span>')
    body = (f'<div class="chips" id="scope">{"".join(chips)}</div>'
            '<button class="addbtn" id="addScope" type="button">+ Add scope item</button>'
            '<p class="edithint">Chip labels are <b>directly editable</b> · cycle state via the <b>IN/OUT/HOLD</b> badge · &#10005; to delete</p>')
    return _panel("02", "Scope", "scope", "Review HOLD items", body)


def _panel_split(canvas: dict) -> str:
    cards = []
    for tk in canvas.get("tickets") or []:
        items = "".join(
            f'<li class="t-item"><span class="it edit" contenteditable="true">{esc(it)}</span>'
            f'<span class="li-x" role="button" tabindex="0">&#10005;</span></li>'
            for it in (tk.get("items") or []))
        cards.append(
            '<div class="tcard"><div class="tcard-top">'
            f'<h3 class="t-title edit" contenteditable="true">{esc(tk.get("title"))}</h3>'
            '<span class="x" role="button" tabindex="0" aria-label="Delete ticket">&#10005;</span></div>'
            f'<span class="t-size edit" contenteditable="true">{esc(tk.get("size"))}</span>'
            f'<ul class="t-items">{items}</ul>'
            '<button class="addbtn mini add-item" type="button">+ Item</button></div>')
    body = (f'<div class="cards" id="cards">{"".join(cards)}</div>'
            '<button class="addbtn" id="addTicket" type="button">+ Add ticket</button>'
            '<p class="edithint">Title, size, and items are all <b>directly editable</b> · &#10005; to delete tickets or items · '
            'split or merge as you see fit</p>')
    return _panel("03", "Ticket split", "split", "Free shape — one PR each", body)


def _panel_ac(canvas: dict) -> str:
    rows = []
    for idx, ac in enumerate(canvas.get("acceptance_criteria") or []):
        ac_id = ac.get("id") or f"a{idx + 1}"
        checked = " checked" if ac.get("accepted", True) else ""
        flag_on = " on" if ac.get("flagged") else ""
        rows.append(
            f'<div class="ac" data-id="{esc(ac_id)}" data-orig="{esc(ac.get("text"))}">'
            f'<input type="checkbox"{checked}>'
            f'<span class="txt edit" contenteditable="true">{esc(ac.get("text"))}</span>'
            f'<button class="flag{flag_on}" type="button">&#9873; Ambiguous</button>'
            '<span class="x" role="button" tabindex="0" aria-label="Delete">&#10005;</span></div>')
    body = (f'<div id="aclist">{"".join(rows)}</div>'
            '<button class="addbtn" id="addAC" type="button" style="margin-top:10px">+ Add acceptance criterion</button>'
            '<p class="edithint"><b>&#9873; Ambiguous</b> marks criteria helm found vague to verify. '
            'Edit the wording and clear the flag, &#10005; to drop, or leave it as-is.</p>')
    return _panel("04", "Acceptance criteria", "ac", "Make them verifiable", body)


def _panel_prio(canvas: dict) -> str:
    priority = canvas.get("priority", "medium")
    idx = PRIORITIES.index(priority) if priority in PRIORITIES else 1
    body = (
        '<div class="prio"><span style="font-size:12px;color:var(--mut)">low</span>'
        f'<input type="range" id="prio" min="0" max="3" step="1" value="{idx}">'
        '<span style="font-size:12px;color:var(--mut)">critical</span>'
        f'<span class="prio-val" id="prioVal">{esc(priority)}</span></div>'
        '<div class="depgraph" id="depGraph"></div>'
        '<div class="depedit"><span class="k">Dependencies</span>'
        f'<span class="v edit" id="depText" contenteditable="true">{esc(canvas.get("dependency"))}</span></div>'
        '<p class="edithint">Describe dependencies freely.</p>')
    return _panel("05", "Priority &amp; dependencies", "prio", "Backlog position", body)


def _panel_con(canvas: dict) -> str:
    rows = []
    for con in canvas.get("constraints") or []:
        rows.append(
            '<div class="con">'
            f'<span class="k edit" contenteditable="true">{esc(con.get("label"))}</span>'
            f'<span class="v edit" contenteditable="true">{esc(con.get("text"))}</span>'
            '<span class="x" role="button" tabindex="0">&#10005;</span></div>')
    body = (f'<div id="conlist">{"".join(rows)}</div>'
            '<button class="addbtn" id="addCon" type="button" style="margin-top:9px">+ Add constraint</button>'
            '<p class="edithint">Both category label and content are editable · add any constraints helm missed.</p>')
    return _panel("06", "Constraints &amp; edge cases", "con", "helm guesses · edit freely", body)


def _panel_note() -> str:
    body = ('<p style="font-size:13px;color:var(--mut)">Anything that does not fit the panels — '
            'concerns, context, direction you want to change. Rides along in the token straight to helm.</p>'
            '<textarea class="free" id="freeNote" placeholder="Anything you want to tell helm — write freely."></textarea>')
    return _panel("07", "To helm — free notes", "note", "Optional", body)


def _header(record: dict, canvas: dict) -> str:
    ticket = record.get("ticket") or "ticket"
    rnd = canvas.get("round", 0)
    return (
        f'<div class="eyebrow">Helm Canvas · Decision record {esc(record.get("id"))}</div>'
        f'<h1 class="title">{esc(canvas.get("title") or ticket)}</h1>'
        '<p class="lede">A plan helm <b>proposed</b> — not a form. Edit any text directly and '
        'add or remove items. Even with review-suggested items still open, you can <b>confirm and copy at any time</b>.</p>'
        '<div class="cstate">This canvas file: '
        f'<code id="cstatePath">.ct2/plans/canvas/<b>open</b>/{esc(ticket)}-r{esc(rnd)}.canvas.html</code></div>')


def _flow() -> str:
    steps = [
        ("done", "S1 ✓", "User ↔ helm conversation drafts the plan"),
        ("done", "S2 ✓", "helm generates the canvas HTML"),
        ("now", "S3 ●", "Now — decide and copy"),
        ("", "S4", "helm reclaims the token → md ticket"),
        ("", "S5", "Ticket lands in the backlog for forge"),
    ]
    out = ['<div class="flow" id="flow">']
    for idx, (cls, label, text) in enumerate(steps, start=1):
        out.append(f'<div class="step {cls}" data-step="{idx}">'
                   f'<div class="s">{label}</div><div class="t">{esc(text)}</div></div>')
    out.append('</div>')
    return "".join(out)


def _right_column() -> str:
    return (
        '<div class="right"><div class="summary">'
        '<div class="hd">Plan at a glance</div>'
        '<div class="stats">'
        '<div class="stat"><div class="v" id="stTickets">0</div><div class="l">Tickets (PRs)</div></div>'
        '<div class="stat"><div class="v" id="stScope">0</div><div class="l">In-scope items</div></div>'
        '<div class="stat"><div class="v" id="stAC">0</div><div class="l">Acceptance criteria</div></div>'
        '<div class="stat"><div class="v adv" id="stAdv">0</div><div class="l">helm review suggested</div></div>'
        '</div>'
        '<div class="block delta"><div class="lbl">helm proposal → your decision</div>'
        '<ul id="deltaList"></ul></div>'
        '<div class="block advis"><div class="lbl">Items helm suggests reviewing</div>'
        '<ul id="advisList"></ul><p class="hint" id="advisHint"></p></div>'
        '<div class="block"><div class="lbl">Decision record (source of truth)</div>'
        '<div class="render-fail" id="renderFail" role="alert"></div>'
        '<pre class="json" id="json"></pre></div>'
        '<div class="commit">'
        '<button class="go" id="commitBtn">📋 Confirm decision → copy to helm</button>'
        '<button class="dl" id="dlBtn">Or download as decision.json</button>'
        '<div class="gatemsg" id="gateMsg"></div>'
        '<div class="donebox" id="doneBox"><textarea id="token" readonly></textarea>'
        '<span class="copied" id="copiedMsg"></span></div>'
        '</div></div></div>')


_JS = r"""
"use strict";
var C=window.CANVAS||{};
var PRIO=["low","medium","high","critical"];
var SCOPE_CYCLE={in:"out",out:"hold",hold:"in"};
var SKEY="ct2-canvas-"+(C.decision||"x");
var $=function(s,r){return (r||document).querySelector(s)};
var $$=function(s,r){return [].slice.call((r||document).querySelectorAll(s))};
var txt=function(el){return el?(el.textContent||"").trim():""};
function esc(t){return String(t==null?"":t).replace(/&/g,"&amp;").replace(/</g,"&lt;")}

function read(){
  var mr=$('.pick[aria-pressed="true"]');
  return {
    misread: mr?mr.dataset.misread:null,
    misreadNote: $('#misreadNote').value.trim(),
    scope: $$('#scope .chip').map(function(c){
      return {key:c.dataset.key||"",label:txt($('.lbl',c)),state:c.dataset.s}; }),
    tickets: $$('#cards .tcard').map(function(c){
      return {title:txt($('.t-title',c)),size:txt($('.t-size',c)),
        items:$$('.t-item .it',c).map(txt).filter(Boolean)}; }),
    ac: $$('#aclist .ac').map(function(a){
      return {id:a.dataset.id,orig:(a.dataset.orig!=null?a.dataset.orig:null),
        text:txt($('.txt',a)),accepted:$('input',a).checked,
        flagged:$('.flag',a).classList.contains('on')}; }),
    priority: PRIO[+$('#prio').value],
    dependency: txt($('#depText')),
    constraints: $$('#conlist .con').map(function(c){
      return {label:txt($('.k',c)),text:txt($('.v',c))}; }),
    note: $('#freeNote').value.trim()
  };
}

var BASELINE={scope:{},acFlags:{}};
(function(){
  var b=read();
  b.scope.forEach(function(x){BASELINE.scope[x.key||x.label]=x.state;});
  BASELINE.priority=b.priority;
  b.ac.forEach(function(a){BASELINE.acFlags[a.id]=a.flagged;});
  BASELINE.origAC=b.ac.map(function(a){return a.id;});
  BASELINE.ticketsSig=JSON.stringify(b.tickets);
  BASELINE.conSig=JSON.stringify(b.constraints);
  BASELINE.dependency=b.dependency;
})();

// ── DOM builders (shared by add-buttons and localStorage restore) ──
function chipNode(item){
  var c=document.createElement('span');
  c.className='chip'; c.dataset.s=item.state||'in';
  if(item.key) c.dataset.key=item.key;
  c.innerHTML='<span class="dot"></span>'
    +'<span class="lbl edit" contenteditable="true" data-ph="New scope item…"></span>'
    +'<span class="st" role="button" tabindex="0">'+((item.state||'in').toUpperCase())+'</span>'
    +'<span class="x" role="button" tabindex="0" aria-label="Delete">✕</span>';
  $('.lbl',c).textContent=item.label||'';
  return c;
}
function itemNode(text){
  var li=document.createElement('li'); li.className='t-item';
  li.innerHTML='<span class="it edit" contenteditable="true" data-ph="Sub-item…"></span>'
    +'<span class="li-x" role="button" tabindex="0">✕</span>';
  $('.it',li).textContent=text||'';
  return li;
}
function ticketNode(tk){
  var c=document.createElement('div'); c.className='tcard';
  c.innerHTML='<div class="tcard-top">'
    +'<h3 class="t-title edit" contenteditable="true" data-ph="New ticket title…"></h3>'
    +'<span class="x" role="button" tabindex="0" aria-label="Delete ticket">✕</span></div>'
    +'<span class="t-size edit" contenteditable="true" data-ph="Size · duration (e.g. small · ~1 day)"></span>'
    +'<ul class="t-items"></ul><button class="addbtn mini add-item" type="button">+ Item</button>';
  $('.t-title',c).textContent=(tk&&tk.title)||'';
  $('.t-size',c).textContent=(tk&&tk.size)||'';
  var ul=$('.t-items',c);
  ((tk&&tk.items)||[]).forEach(function(it){ ul.appendChild(itemNode(it)); });
  return c;
}
function acNode(ac){
  var row=document.createElement('div'); row.className='ac';
  row.dataset.id=ac.id||('new-'+Date.now()+'-'+Math.random().toString(16).slice(2,6));
  if(ac.orig!=null) row.dataset.orig=ac.orig;
  row.innerHTML='<input type="checkbox"'+(ac.accepted!==false?' checked':'')+'>'
    +'<span class="txt edit" contenteditable="true" data-ph="New acceptance criterion — make it verifiable…"></span>'
    +'<button class="flag'+(ac.flagged?' on':'')+'" type="button">⚑ Ambiguous</button>'
    +'<span class="x" role="button" tabindex="0" aria-label="Delete">✕</span>';
  $('.txt',row).textContent=ac.text||'';
  return row;
}
function conNode(con){
  var row=document.createElement('div'); row.className='con';
  row.innerHTML='<span class="k edit" contenteditable="true" data-ph="Category"></span>'
    +'<span class="v edit" contenteditable="true" data-ph="Constraint or edge case…"></span>'
    +'<span class="x" role="button" tabindex="0">✕</span>';
  $('.k',row).textContent=(con&&con.label)||'';
  $('.v',row).textContent=(con&&con.text)||'';
  return row;
}

// ── localStorage restore — survive a browser refresh (P-state) ──
function applyState(s){
  $$('.pick').forEach(function(p){p.setAttribute('aria-pressed','false')});
  if(s.misread){ var pb=$('.pick[data-misread="'+s.misread+'"]'); if(pb) pb.setAttribute('aria-pressed','true'); }
  $('#misreadNote').value=s.misreadNote||'';
  $('#misreadNote').style.display=(s.misread==="wrong")?"block":"none";
  var sc=$('#scope'); sc.innerHTML='';
  (s.scope||[]).forEach(function(x){ sc.appendChild(chipNode(x)); });
  var cd=$('#cards'); cd.innerHTML='';
  (s.tickets||[]).forEach(function(t){ cd.appendChild(ticketNode(t)); });
  var ac=$('#aclist'); ac.innerHTML='';
  (s.ac||[]).forEach(function(a){ ac.appendChild(acNode(a)); });
  var pi=PRIO.indexOf(s.priority); if(pi<0) pi=1;
  $('#prio').value=pi; $('#prioVal').textContent=PRIO[pi];
  $('#depText').textContent=s.dependency||'';
  var cl=$('#conlist'); cl.innerHTML='';
  (s.constraints||[]).forEach(function(c){ cl.appendChild(conNode(c)); });
  $('#freeNote').value=s.note||'';
}

function advisory(s){
  var a=[];
  if(s.misread===null) a.push({t:"helm's interpretation not yet confirmed",jump:"#p-interpret"});
  if(s.misread==="wrong"&&!s.misreadNote) a.push({t:"Marked needs-correction but the note is empty",jump:"#p-interpret"});
  s.scope.filter(function(x){return x.state==="hold"}).forEach(function(x){
    a.push({t:"Scope '"+x.label+"' is on HOLD",jump:"#p-scope"}); });
  s.ac.filter(function(x){return x.accepted&&x.flagged}).forEach(function(x){
    a.push({t:"Acceptance criterion '"+x.text.slice(0,20)+"…' flagged ambiguous",jump:"#p-ac"}); });
  return a;
}

function delta(s){
  var d=[],nm={in:"IN",out:"OUT",hold:"HOLD"};
  if(s.misread==="wrong") d.push({f:"Interpretation",t:"Corrected helm's interpretation"+(s.misreadNote?"":" (note empty)")});
  s.scope.forEach(function(x){
    var k=x.key||x.label,base=BASELINE.scope[k];
    if(base===undefined){ d.push({f:"Scope",t:"Added '"+(x.label||"(empty)")+"'"}); }
    else if(base!==x.state){ d.push({f:"Scope",t:"'"+x.label+"' "+nm[base]+"→"+nm[x.state]}); }
  });
  if(s.priority!==BASELINE.priority) d.push({f:"Priority",t:BASELINE.priority+" → "+s.priority});
  var seen={};
  s.ac.forEach(function(x){
    seen[x.id]=1;
    if(x.orig===null){ d.push({f:"AC",t:"Added '"+(x.text.slice(0,20)||"(empty)")+"…'"}); return; }
    if(!x.accepted){ d.push({f:"AC",t:"Dropped '"+x.orig.slice(0,18)+"…'"}); return; }
    if(x.text!==x.orig){ d.push({f:"AC",t:"Reworded '"+x.orig.slice(0,18)+"…'"}); }
    else if(x.flagged!==BASELINE.acFlags[x.id]){ d.push({f:"AC",t:"'"+x.text.slice(0,16)+"…' "+(x.flagged?"flagged ambiguous":"clarified")}); }
  });
  BASELINE.origAC.forEach(function(id){ if(!seen[id]) d.push({f:"AC",t:"Removed "+id}); });
  if(JSON.stringify(s.tickets)!==BASELINE.ticketsSig) d.push({f:"Tickets",t:"Edited split ("+s.tickets.length+" total)"});
  if(JSON.stringify(s.constraints)!==BASELINE.conSig) d.push({f:"Constraints",t:"Edited list ("+s.constraints.length+" total)"});
  if(s.dependency!==BASELINE.dependency) d.push({f:"Dependencies",t:"Edited dependency notes"});
  if(s.note) d.push({f:"Note",t:"Added free note"});
  return d;
}

function recordObj(s){
  var adv=advisory(s);
  return {
    kind:"ct2-decision-answer",decision:C.decision,ticket:C.ticket,nonce:C.nonce,round:C.round,
    answer:{
      interpretation: s.misread==="ok"?"confirmed":s.misread==="wrong"?"needs-fix":"unconfirmed",
      interpretation_fix: s.misread==="wrong"?(s.misreadNote||null):null,
      scope: s.scope.reduce(function(o,x){if(x.label)o[x.label]=x.state;return o},{}),
      tickets: s.tickets,
      acceptance_criteria: s.ac.filter(function(a){return a.accepted&&a.text})
        .map(function(a){return {text:a.text,verifiable:!a.flagged}}),
      priority: s.priority,
      dependency: s.dependency||null,
      constraints: s.constraints.filter(function(c){return c.label||c.text}),
      note: s.note||null
    },
    overrides: delta(s).map(function(x){return x.f+": "+x.t}),
    open_items: adv.map(function(x){return x.t}),
    answered_at:"<decision timestamp>"
  };
}

function colorJSON(obj){
  return JSON.stringify(obj,null,2)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/"([^"]+)":/g,'"<span class="k">$1</span>":')
    .replace(/: "([^"]*)"/g,': "<span class="s">$1</span>"')
    .replace(/: (true|false|null)/g,': <span class="b">$1</span>')
    .replace(/: (-?[0-9]+)/g,': <span class="n">$1</span>');
}

function renderDep(tickets){
  var el=$('#depGraph'); if(!el) return;
  var n=tickets.length;
  if(!n){ el.innerHTML=''; return; }
  var bw=118,gap=34,h=54,W=n*(bw+gap)-gap+8;
  var svg='<svg width="'+W+'" height="'+h+'" viewBox="0 0 '+W+' '+h+'" role="img" aria-label="Ticket order">';
  for(var i=0;i<n;i++){
    var x=i*(bw+gap)+4;
    if(i>0){
      svg+='<line x1="'+(x-gap)+'" y1="27" x2="'+(x-5)+'" y2="27" stroke="#9a958a" stroke-width="1.5"/>';
      svg+='<path d="M'+(x-4)+' 27 l-7 -4 l0 8 z" fill="#9a958a"/>';
    }
    svg+='<rect x="'+x+'" y="11" width="'+bw+'" height="32" rx="7" fill="#eaeefb" stroke="#1d4ed8"/>';
    var label=tickets[i].title||('#'+(i+1));
    if(label.length>15) label=label.slice(0,14)+'…';
    svg+='<text x="'+(x+bw/2)+'" y="31" font-size="11" fill="#1d4ed8" text-anchor="middle">'+esc(label)+'</text>';
  }
  el.innerHTML=svg+'</svg>';
}

var lastJSON="",committed=false;
function _renderImpl(){
  var s=read(),adv=advisory(s),d=delta(s);
  $('[data-meta="interpret"]').innerHTML = s.misread===null?"Review suggested"
    :s.misread==="ok"?'<span class="resolved-tick">✓ Confirmed</span>'
    :'<span class="open-tick">✎ Correction requested</span>';
  var holds=s.scope.filter(function(x){return x.state==="hold"}).length;
  $('[data-meta="scope"]').innerHTML = holds?'<span class="open-tick">'+holds+' on hold</span>'
    :'<span class="resolved-tick">✓ All decided</span>';
  var fl=s.ac.filter(function(x){return x.accepted&&x.flagged}).length;
  $('[data-meta="ac"]').innerHTML = fl?'<span class="open-tick">⚑ '+fl+' ambiguous</span>'
    :'<span class="resolved-tick">✓ All clear</span>';
  $('#stTickets').textContent=s.tickets.length;
  $('#stScope').textContent=s.scope.filter(function(x){return x.state==="in"}).length;
  $('#stAC').textContent=s.ac.filter(function(a){return a.accepted}).length;
  var sa=$('#stAdv'); sa.textContent=adv.length; sa.className="v "+(adv.length?"adv":"adv0");
  $('#deltaList').innerHTML = d.length
    ? d.map(function(x){return '<li><span class="f">'+x.f+'</span><span>'+esc(x.t)+'</span></li>'}).join("")
    : '<li class="none">Still matches helm\'s proposal</li>';
  var al=$('#advisList'),ah=$('#advisHint');
  if(adv.length){
    al.innerHTML=adv.map(function(x){
      return '<li data-jump="'+x.jump+'"><span class="ic">⚑</span><span>'+esc(x.t)+'</span></li>'; }).join("");
    ah.textContent="These do not block copying. Leave them as-is and they ride along in the token's open_items for helm to follow up on.";
  } else { al.innerHTML='<li class="none">No review-suggested items from helm ✓</li>'; ah.textContent=""; }
  renderDep(s.tickets);
  var pre=$('#json'),nj=JSON.stringify(recordObj(s));
  pre.innerHTML=colorJSON(recordObj(s));
  if(nj!==lastJSON&&lastJSON!==""){ pre.classList.add('flash');
    setTimeout(function(){pre.classList.remove('flash')},420); }
  lastJSON=nj;
  var gm=$('#gateMsg');
  if(committed) gm.innerHTML="";
  else if(adv.length) gm.innerHTML="Copying will also send <b>"+adv.length+" review-suggested item(s)</b> along to helm";
  else gm.innerHTML="Everything is tidy — ready for a clean handoff ✓";
  try{ localStorage.setItem(SKEY,JSON.stringify(s)); }catch(e){}
}

// render() guard: if any part of the render pipeline throws (a corrupted
// localStorage payload, a contenteditable in an unexpected state, a browser
// API gap), surface the error visibly instead of leaving the right-hand AI
// judgment panel blank. The decision token can still be copied — the data
// model in read() is independent of the right-panel preview.
function render(){
  var fail=$('#renderFail');
  try{
    _renderImpl();
    if(fail){ fail.classList.remove('on'); fail.innerHTML=''; }
  }catch(e){
    lastJSON='';
    var msg=(e&&(e.message||e.toString()))||'unknown render error';
    if(fail){
      fail.classList.add('on');
      fail.innerHTML='<b>⚠ Canvas render error</b>'+esc(msg)
        +'<br><span style="color:var(--mut);font-size:11px">'
        +'Decision-token copy still works — use the button above.</span>';
    }
    try{ if(window.console&&console.error) console.error('canvas render failed',e); }catch(_){}
  }
}

// Paste safety: contenteditable cells accept plain text only. Pasted rich
// HTML (Notion, Slack, web pages) can inject markup that breaks the canvas
// layout. Strip formatting on paste and collapse newlines for single-line
// fields so chip labels and ticket titles stay one row tall.
document.addEventListener('paste',function(e){
  var t=e.target;
  if(!t||!t.classList||!t.classList.contains('edit')) return;
  var data=e.clipboardData||window.clipboardData;
  if(!data) return;
  var text=data.getData('text/plain')||'';
  if(t.tagName!=='TEXTAREA') text=text.replace(/[\r\n\t]+/g,' ');
  e.preventDefault();
  // execCommand is deprecated by MDN but still universally supported and is the
  // only way to land a contenteditable paste in the browser's undo stack. The
  // Selection-API branch below is the long-term fallback.
  if(document.queryCommandSupported&&document.queryCommandSupported('insertText')){
    document.execCommand('insertText',false,text);
  } else {
    var sel=window.getSelection();
    if(sel&&sel.rangeCount){
      var r=sel.getRangeAt(0); r.deleteContents();
      r.insertNode(document.createTextNode(text));
      r.collapse(false); sel.removeAllRanges(); sel.addRange(r);
    } else { t.textContent=(t.textContent||'')+text; }
  }
  committed=false; render();
});

$('.askrow').addEventListener('click',function(e){
  var b=e.target.closest('.pick'); if(!b) return;
  var on=b.getAttribute('aria-pressed')==="true";
  $$('.pick').forEach(function(p){p.setAttribute('aria-pressed','false')});
  b.setAttribute('aria-pressed',on?"false":"true");
  $('#misreadNote').style.display=(b.dataset.misread==="wrong"&&!on)?"block":"none";
  committed=false; render();
});
$('#misreadNote').addEventListener('input',function(){committed=false;render()});
$('#freeNote').addEventListener('input',function(){committed=false;render()});

$('#scope').addEventListener('click',function(e){
  var chip=e.target.closest('.chip'); if(!chip) return;
  if(e.target.classList.contains('st')){
    chip.dataset.s=SCOPE_CYCLE[chip.dataset.s];
    e.target.textContent=chip.dataset.s.toUpperCase();
    committed=false; render();
  } else if(e.target.classList.contains('x')){
    chip.remove(); committed=false; render();
  }
});
$('#addScope').addEventListener('click',function(){
  var c=chipNode({state:'in'});
  $('#scope').appendChild(c); $('.lbl',c).focus(); committed=false; render();
});

var aclist=$('#aclist');
aclist.addEventListener('click',function(e){
  var row=e.target.closest('.ac'); if(!row) return;
  if(e.target.classList.contains('flag')){ e.target.classList.toggle('on'); committed=false; render(); }
  else if(e.target.classList.contains('x')){ row.remove(); committed=false; render(); }
});
aclist.addEventListener('change',function(){committed=false;render()});
$('#addAC').addEventListener('click',function(){
  var row=acNode({accepted:true});
  aclist.appendChild(row); $('.txt',row).focus(); committed=false; render();
});

$('#cards').addEventListener('click',function(e){
  var card=e.target.closest('.tcard'); if(!card) return;
  if(e.target.classList.contains('x')){ card.remove(); committed=false; render(); }
  else if(e.target.classList.contains('li-x')){ e.target.closest('.t-item').remove(); committed=false; render(); }
  else if(e.target.classList.contains('add-item')){
    var li=itemNode('');
    $('.t-items',card).appendChild(li); $('.it',li).focus(); committed=false; render();
  }
});
$('#addTicket').addEventListener('click',function(){
  var c=ticketNode({});
  $('#cards').appendChild(c); $('.t-title',c).focus(); committed=false; render();
});

$('#conlist').addEventListener('click',function(e){
  if(e.target.classList.contains('x')){ e.target.closest('.con').remove(); committed=false; render(); }
});
$('#addCon').addEventListener('click',function(){
  var row=conNode({label:'Other'});
  $('#conlist').appendChild(row); $('.v',row).focus(); committed=false; render();
});

var prio=$('#prio');
prio.addEventListener('input',function(){
  $('#prioVal').textContent=PRIO[+prio.value]; committed=false; render(); });

document.addEventListener('input',function(e){
  if(e.target.classList&&e.target.classList.contains('edit')){ committed=false; render(); }
});

// keyboard access: role=button spans (state badges, delete handles) respond to Enter/Space
document.addEventListener('keydown',function(e){
  var t=e.target;
  if((e.key==="Enter"||e.key===" ")&&t&&t.getAttribute&&t.getAttribute('role')==="button"){
    e.preventDefault(); t.click();
  }
});

$('#advisList').addEventListener('click',function(e){
  var li=e.target.closest('li[data-jump]'); if(!li) return;
  var el=$(li.dataset.jump);
  if(el){ el.scrollIntoView({behavior:'smooth',block:'center'});
    el.style.transition='box-shadow .3s'; el.style.boxShadow='0 0 0 2px var(--accent)';
    setTimeout(function(){el.style.boxShadow=''},900); }
});

function buildToken(){
  var rec=recordObj(read()); rec.answered_at=new Date().toISOString();
  return "CT2-DECISION "+JSON.stringify(rec);
}
$('#commitBtn').addEventListener('click',function(){
  var token=buildToken();
  $('#token').value=token;
  $('#doneBox').style.display="block";
  var adv=advisory(read());
  $('#copiedMsg').innerHTML=(adv.length
    ? "✓ Copied — includes "+adv.length+" open_items. "
    : "✓ Copied. ")+"Paste into the helm chat and ask helm to 'turn this into an md ticket.'";
  try{ navigator.clipboard.writeText(token); }catch(e){ $('#token').select(); }
  committed=true;
  this.textContent="✓ Copied — click again to re-copy";
  var s3=$('#flow .step[data-step="3"]'),s4=$('#flow .step[data-step="4"]');
  if(s3){ s3.className="step done"; $('.s',s3).textContent="S3 ✓"; }
  if(s4){ s4.className="step now"; $('.s',s4).textContent="S4 ●"; }
  var cp=$('#cstatePath');
  if(cp) cp.innerHTML=".ct2/plans/canvas/<b>answered</b>/"+C.ticket+"-r"+C.round+".canvas.html";
  render();
});
$('#dlBtn').addEventListener('click',function(){
  // download a bare JSON object so decision-*.json is valid JSON;
  // ct2-helm-canvas recover --file (parse_token) accepts a bare object.
  var rec=recordObj(read()); rec.answered_at=new Date().toISOString();
  var blob=new Blob([JSON.stringify(rec,null,2)],{type:"application/json"});
  var a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download="decision-"+(C.decision||"canvas")+".json";
  document.body.appendChild(a); a.click();
  setTimeout(function(){a.remove();URL.revokeObjectURL(a.href);},0);
});

(function(){
  var saved=null;
  try{ saved=localStorage.getItem(SKEY); }catch(e){}
  if(saved){ try{ applyState(JSON.parse(saved)); }catch(e){} }
})();

render();
"""


def render(record: dict) -> str:
    """Render a decision record into a self-contained canvas HTML string."""
    canvas = record.get("canvas") or {}
    config = _safe_json_for_script(
        {
            "decision": record.get("id"),
            "ticket": record.get("ticket"),
            "round": canvas.get("round", 0),
            "nonce": record.get("nonce"),
        }
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f"<title>Helm Canvas — {esc(canvas.get('title') or record.get('ticket'))}</title>"
        f"<style>{_CSS}</style></head><body>"
        '<div class="wrap">'
        f"<header>{_header(record, canvas)}</header>"
        f"{_flow()}"
        '<div class="grid"><div class="left">'
        f"{_panel_interpret(canvas)}{_panel_scope(canvas)}{_panel_split(canvas)}"
        f"{_panel_ac(canvas)}{_panel_prio(canvas)}{_panel_con(canvas)}{_panel_note()}"
        "</div>"
        f"{_right_column()}"
        "</div>"
        '<footer class="note">CT2 Helm Canvas · self-contained HTML (zero external deps) · '
        f"provider format(html) — spec/helm-canvas.md</footer>"
        "</div>"
        f"<script>window.CANVAS={config};</script>"
        f"<script>{_JS}</script>"
        "</body></html>\n"
    )


def parse_token(text: str) -> dict:
    """Parse a 'CT2-DECISION {json}' token into a dict.

    Raises ValueError with line/column, an excerpt of the offending region,
    and hints for common paste-time corruption (smart quotes, trailing commas,
    truncated tokens).
    """
    text = (text or "").strip()
    prefix = "CT2-DECISION"
    if text.startswith(prefix):
        text = text[len(prefix):].strip()
    if not text:
        raise ValueError("empty decision token")
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        snippet = _excerpt(text, exc.pos)
        hints = _diagnose_json(text)
        if text.count("{") > text.count("}") or text.count("[") > text.count("]"):
            hints.append("token looks truncated — braces/brackets do not balance")
        hint_text = ("\n  hint: " + "; ".join(hints)) if hints else ""
        raise ValueError(
            f"malformed decision token at line {exc.lineno} col {exc.colno}: {exc.msg}"
            f"\n  near: {snippet}{hint_text}"
        ) from exc
    if not isinstance(obj, dict):
        raise ValueError("decision token must be a JSON object")
    return obj
