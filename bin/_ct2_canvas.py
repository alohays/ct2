#!/usr/bin/env python3
"""Render a CT2 helm decision record into a self-contained canvas HTML page.

This module is the HTML provider format for the Decision Bridge. See
spec/helm-canvas.md. Standard library only; the output references no external
CSS, fonts, or scripts and works from file://.
"""

from __future__ import annotations

import html
import json
from typing import Any

PRIORITIES = ["low", "medium", "high", "critical"]

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
transition:background .12s,box-shadow .12s}
.edit:hover{background:var(--accent-soft)}
.edit:focus{background:#fff;box-shadow:0 0 0 2px var(--accent)}
.edit:empty::before{content:attr(data-ph);color:var(--faint)}
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
        '<button class="pick" data-misread="ok" aria-pressed="false">정확합니다<small>이대로 진행</small></button>'
        '<button class="pick warn" data-misread="wrong" aria-pressed="false">고칠 부분이 있습니다<small>아래에 적어주세요</small></button>'
        '</div>'
        '<textarea class="free" id="misreadNote" style="display:none" '
        'placeholder="helm이 어떻게 이해해야 하나요? 자유롭게 적으세요."></textarea>')
    return _panel("01", "helm의 해석", "interpret", "확인 권장", body)


def _panel_scope(canvas: dict) -> str:
    chips = []
    for item in canvas.get("scope") or []:
        state = item.get("state", "in")
        chips.append(
            f'<span class="chip" data-s="{esc(state)}" data-key="{esc(item.get("key",""))}">'
            f'<span class="dot"></span><span class="lbl edit" contenteditable="true">{esc(item.get("label"))}</span>'
            f'<span class="st" role="button" tabindex="0">{esc(state.upper())}</span>'
            f'<span class="x" role="button" tabindex="0" aria-label="삭제">&#10005;</span></span>')
    body = (f'<div class="chips" id="scope">{"".join(chips)}</div>'
            '<button class="addbtn" id="addScope" type="button">+ 범위 항목 추가</button>'
            '<p class="edithint">칩 라벨은 <b>직접 편집</b> · <b>IN/OUT/HOLD</b> 배지로 상태 순환 · &#10005;로 삭제</p>')
    return _panel("02", "범위", "scope", "보류 항목 확인 권장", body)


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
            '<span class="x" role="button" tabindex="0" aria-label="티켓 삭제">&#10005;</span></div>'
            f'<span class="t-size edit" contenteditable="true">{esc(tk.get("size"))}</span>'
            f'<ul class="t-items">{items}</ul>'
            '<button class="addbtn mini add-item" type="button">+ 항목</button></div>')
    body = (f'<div class="cards" id="cards">{"".join(cards)}</div>'
            '<button class="addbtn" id="addTicket" type="button">+ 티켓 추가</button>'
            '<p class="edithint">제목·규모·세부 항목 모두 <b>직접 편집</b> · &#10005;로 티켓·항목 삭제 · '
            '필요하면 더 쪼개거나 합치세요</p>')
    return _panel("03", "티켓 분할", "split", "PR 단위로 자유롭게", body)


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
            f'<button class="flag{flag_on}" type="button">&#9873; 모호</button>'
            '<span class="x" role="button" tabindex="0" aria-label="삭제">&#10005;</span></div>')
    body = (f'<div id="aclist">{"".join(rows)}</div>'
            '<button class="addbtn" id="addAC" type="button" style="margin-top:10px">+ 인수 기준 추가</button>'
            '<p class="edithint"><b>&#9873; 모호</b>는 helm이 검증 기준이 흐릿하다고 본 항목입니다. '
            '문구를 직접 고치고 모호를 해제하거나, &#10005;로 빼거나, 그대로 두셔도 됩니다.</p>')
    return _panel("04", "인수 기준", "ac", "검증 가능하게", body)


def _panel_prio(canvas: dict) -> str:
    priority = canvas.get("priority", "medium")
    idx = PRIORITIES.index(priority) if priority in PRIORITIES else 1
    body = (
        '<div class="prio"><span style="font-size:12px;color:var(--mut)">low</span>'
        f'<input type="range" id="prio" min="0" max="3" step="1" value="{idx}">'
        '<span style="font-size:12px;color:var(--mut)">critical</span>'
        f'<span class="prio-val" id="prioVal">{esc(priority)}</span></div>'
        '<div class="depedit"><span class="k">의존성</span>'
        f'<span class="v edit" id="depText" contenteditable="true">{esc(canvas.get("dependency"))}</span></div>'
        '<p class="edithint">의존 관계는 자유롭게 적으세요.</p>')
    return _panel("05", "우선순위 &amp; 의존성", "prio", "백로그 위치", body)


def _panel_con(canvas: dict) -> str:
    rows = []
    for con in canvas.get("constraints") or []:
        rows.append(
            '<div class="con">'
            f'<span class="k edit" contenteditable="true">{esc(con.get("label"))}</span>'
            f'<span class="v edit" contenteditable="true">{esc(con.get("text"))}</span>'
            '<span class="x" role="button" tabindex="0">&#10005;</span></div>')
    body = (f'<div id="conlist">{"".join(rows)}</div>'
            '<button class="addbtn" id="addCon" type="button" style="margin-top:9px">+ 제약 추가</button>'
            '<p class="edithint">분류 라벨과 내용 모두 편집 가능 · helm이 놓친 제약은 직접 추가하세요.</p>')
    return _panel("06", "제약 &amp; 엣지케이스", "con", "helm 추정 · 자유 편집", body)


def _panel_note() -> str:
    body = ('<p style="font-size:13px;color:var(--mut)">패널에 안 들어가는 어떤 말이든 — '
            '우려, 맥락, 바꾸고 싶은 방향. 그대로 토큰에 실려 helm에게 전달됩니다.</p>'
            '<textarea class="free" id="freeNote" placeholder="helm에게 하고 싶은 말을 자유롭게 적으세요."></textarea>')
    return _panel("07", "helm에게 — 자유 메모", "note", "선택", body)


def _header(record: dict, canvas: dict) -> str:
    ticket = record.get("ticket") or "ticket"
    rnd = canvas.get("round", 0)
    return (
        f'<div class="eyebrow">Helm Canvas · 결정 레코드 {esc(record.get("id"))}</div>'
        f'<h1 class="title">{esc(canvas.get("title") or ticket)}</h1>'
        '<p class="lede">helm이 <b>제안</b>한 계획안입니다 — 양식이 아닙니다. 어떤 텍스트든 직접 고치고, '
        '항목을 더하거나 빼세요. 확인 권장 항목이 남아 있어도 <b>언제든 확정·복사할 수 있습니다</b>.</p>'
        '<div class="cstate">이 캔버스 파일: '
        f'<code id="cstatePath">.ct2/plans/canvas/<b>open</b>/{esc(ticket)}-r{esc(rnd)}.canvas.html</code></div>')


def _flow() -> str:
    steps = [
        ("done", "S1 ✓", "유저 ↔ helm 대화로 계획"),
        ("done", "S2 ✓", "helm이 캔버스 HTML 생성"),
        ("now", "S3 ●", "지금 — 결정하고 복사"),
        ("", "S4", "helm이 토큰 회수 → md 티켓"),
        ("", "S5", "backlog에 forge용 티켓"),
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
        '<div class="hd">이 계획 한눈에</div>'
        '<div class="stats">'
        '<div class="stat"><div class="v" id="stTickets">0</div><div class="l">티켓 (PR)</div></div>'
        '<div class="stat"><div class="v" id="stScope">0</div><div class="l">In-scope 항목</div></div>'
        '<div class="stat"><div class="v" id="stAC">0</div><div class="l">인수 기준</div></div>'
        '<div class="stat"><div class="v adv" id="stAdv">0</div><div class="l">helm 확인 권장</div></div>'
        '</div>'
        '<div class="block delta"><div class="lbl">helm 제안 → 내 결정</div>'
        '<ul id="deltaList"></ul></div>'
        '<div class="block advis"><div class="lbl">helm이 확인을 권하는 항목</div>'
        '<ul id="advisList"></ul><p class="hint" id="advisHint"></p></div>'
        '<div class="block"><div class="lbl">결정 레코드 (진실원천)</div>'
        '<pre class="json" id="json"></pre></div>'
        '<div class="commit">'
        '<button class="go" id="commitBtn">📋 결정 확정 → helm으로 복사</button>'
        '<button class="dl" id="dlBtn">또는 decision.json 파일로 다운로드</button>'
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
    +'<span class="lbl edit" contenteditable="true" data-ph="새 범위 항목…"></span>'
    +'<span class="st" role="button" tabindex="0">'+((item.state||'in').toUpperCase())+'</span>'
    +'<span class="x" role="button" tabindex="0" aria-label="삭제">✕</span>';
  $('.lbl',c).textContent=item.label||'';
  return c;
}
function itemNode(text){
  var li=document.createElement('li'); li.className='t-item';
  li.innerHTML='<span class="it edit" contenteditable="true" data-ph="세부 항목…"></span>'
    +'<span class="li-x" role="button" tabindex="0">✕</span>';
  $('.it',li).textContent=text||'';
  return li;
}
function ticketNode(tk){
  var c=document.createElement('div'); c.className='tcard';
  c.innerHTML='<div class="tcard-top">'
    +'<h3 class="t-title edit" contenteditable="true" data-ph="새 티켓 제목…"></h3>'
    +'<span class="x" role="button" tabindex="0" aria-label="티켓 삭제">✕</span></div>'
    +'<span class="t-size edit" contenteditable="true" data-ph="규모·기간 (예: small · ~1일)"></span>'
    +'<ul class="t-items"></ul><button class="addbtn mini add-item" type="button">+ 항목</button>';
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
    +'<span class="txt edit" contenteditable="true" data-ph="새 인수 기준 — 검증 가능하게…"></span>'
    +'<button class="flag'+(ac.flagged?' on':'')+'" type="button">⚑ 모호</button>'
    +'<span class="x" role="button" tabindex="0" aria-label="삭제">✕</span>';
  $('.txt',row).textContent=ac.text||'';
  return row;
}
function conNode(con){
  var row=document.createElement('div'); row.className='con';
  row.innerHTML='<span class="k edit" contenteditable="true" data-ph="분류"></span>'
    +'<span class="v edit" contenteditable="true" data-ph="제약·엣지케이스 내용…"></span>'
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
  if(s.misread===null) a.push({t:"helm의 해석이 맞는지 아직 확인 안 됨",jump:"#p-interpret"});
  if(s.misread==="wrong"&&!s.misreadNote) a.push({t:"고칠 부분을 골랐지만 내용이 비어 있음",jump:"#p-interpret"});
  s.scope.filter(function(x){return x.state==="hold"}).forEach(function(x){
    a.push({t:"범위 '"+x.label+"' 가 보류 상태",jump:"#p-scope"}); });
  s.ac.filter(function(x){return x.accepted&&x.flagged}).forEach(function(x){
    a.push({t:"인수 기준 '"+x.text.slice(0,20)+"…' 가 모호 표시됨",jump:"#p-ac"}); });
  return a;
}

function delta(s){
  var d=[],nm={in:"포함",out:"제외",hold:"보류"};
  if(s.misread==="wrong") d.push({f:"해석",t:"helm 해석을 수정"+(s.misreadNote?"":" (내용 비어 있음)")});
  s.scope.forEach(function(x){
    var k=x.key||x.label,base=BASELINE.scope[k];
    if(base===undefined){ d.push({f:"범위",t:"'"+(x.label||"(빈 항목)")+"' 추가"}); }
    else if(base!==x.state){ d.push({f:"범위",t:"'"+x.label+"' "+nm[base]+"→"+nm[x.state]}); }
  });
  if(s.priority!==BASELINE.priority) d.push({f:"우선순위",t:BASELINE.priority+" → "+s.priority});
  var seen={};
  s.ac.forEach(function(x){
    seen[x.id]=1;
    if(x.orig===null){ d.push({f:"인수기준",t:"'"+(x.text.slice(0,20)||"(빈 항목)")+"…' 추가"}); return; }
    if(!x.accepted){ d.push({f:"인수기준",t:"'"+x.orig.slice(0,18)+"…' 제외"}); return; }
    if(x.text!==x.orig){ d.push({f:"인수기준",t:"'"+x.orig.slice(0,18)+"…' 문구 수정"}); }
    else if(x.flagged!==BASELINE.acFlags[x.id]){ d.push({f:"인수기준",t:"'"+x.text.slice(0,16)+"…' "+(x.flagged?"모호 표시":"명확화")}); }
  });
  BASELINE.origAC.forEach(function(id){ if(!seen[id]) d.push({f:"인수기준",t:id+" 항목 삭제"}); });
  if(JSON.stringify(s.tickets)!==BASELINE.ticketsSig) d.push({f:"티켓",t:"분할안 수정 (총 "+s.tickets.length+"건)"});
  if(JSON.stringify(s.constraints)!==BASELINE.conSig) d.push({f:"제약",t:"제약 목록 수정 (총 "+s.constraints.length+"건)"});
  if(s.dependency!==BASELINE.dependency) d.push({f:"의존성",t:"의존성 기술 수정"});
  if(s.note) d.push({f:"메모",t:"자유 메모 작성"});
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
    answered_at:"<확정 시각>"
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

var lastJSON="",committed=false;
function render(){
  var s=read(),adv=advisory(s),d=delta(s);
  $('[data-meta="interpret"]').innerHTML = s.misread===null?"확인 권장"
    :s.misread==="ok"?'<span class="resolved-tick">✓ 정확</span>'
    :'<span class="open-tick">✎ 수정 요청</span>';
  var holds=s.scope.filter(function(x){return x.state==="hold"}).length;
  $('[data-meta="scope"]').innerHTML = holds?'<span class="open-tick">보류 '+holds+'건</span>'
    :'<span class="resolved-tick">✓ 모두 결정</span>';
  var fl=s.ac.filter(function(x){return x.accepted&&x.flagged}).length;
  $('[data-meta="ac"]').innerHTML = fl?'<span class="open-tick">⚑ '+fl+'건</span>'
    :'<span class="resolved-tick">✓ 모두 명확</span>';
  $('#stTickets').textContent=s.tickets.length;
  $('#stScope').textContent=s.scope.filter(function(x){return x.state==="in"}).length;
  $('#stAC').textContent=s.ac.filter(function(a){return a.accepted}).length;
  var sa=$('#stAdv'); sa.textContent=adv.length; sa.className="v "+(adv.length?"adv":"adv0");
  $('#deltaList').innerHTML = d.length
    ? d.map(function(x){return '<li><span class="f">'+x.f+'</span><span>'+esc(x.t)+'</span></li>'}).join("")
    : '<li class="none">아직 helm 제안과 동일합니다</li>';
  var al=$('#advisList'),ah=$('#advisHint');
  if(adv.length){
    al.innerHTML=adv.map(function(x){
      return '<li data-jump="'+x.jump+'"><span class="ic">⚑</span><span>'+esc(x.t)+'</span></li>'; }).join("");
    ah.textContent="이 항목들은 복사를 막지 않습니다. 그대로 두면 토큰의 open_items 에 실려 helm이 이어서 확인합니다.";
  } else { al.innerHTML='<li class="none">helm이 확인을 권하는 항목이 없습니다 ✓</li>'; ah.textContent=""; }
  var pre=$('#json'),nj=JSON.stringify(recordObj(s));
  pre.innerHTML=colorJSON(recordObj(s));
  if(nj!==lastJSON&&lastJSON!==""){ pre.classList.add('flash');
    setTimeout(function(){pre.classList.remove('flash')},420); }
  lastJSON=nj;
  var gm=$('#gateMsg');
  if(committed) gm.innerHTML="";
  else if(adv.length) gm.innerHTML="복사하면 <b>"+adv.length+"건의 확인 권장 항목</b>도 함께 helm에 전달됩니다";
  else gm.innerHTML="모든 항목이 정리되었습니다 — 깔끔하게 전달됩니다 ✓";
  try{ localStorage.setItem(SKEY,JSON.stringify(s)); }catch(e){}
}

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
  var row=conNode({label:'기타'});
  $('#conlist').appendChild(row); $('.v',row).focus(); committed=false; render();
});

var prio=$('#prio');
prio.addEventListener('input',function(){
  $('#prioVal').textContent=PRIO[+prio.value]; committed=false; render(); });

document.addEventListener('input',function(e){
  if(e.target.classList&&e.target.classList.contains('edit')){ committed=false; render(); }
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
    ? "✓ 복사됨 — open_items "+adv.length+"건 포함. "
    : "✓ 복사됨. ")+"helm 대화창에 붙여넣고 'md 티켓으로 만들어줘'라고 하세요.";
  try{ navigator.clipboard.writeText(token); }catch(e){ $('#token').select(); }
  committed=true;
  this.textContent="✓ 복사됨 — 다시 복사하려면 클릭";
  var s3=$('#flow .step[data-step="3"]'),s4=$('#flow .step[data-step="4"]');
  if(s3){ s3.className="step done"; $('.s',s3).textContent="S3 ✓"; }
  if(s4){ s4.className="step now"; $('.s',s4).textContent="S4 ●"; }
  var cp=$('#cstatePath');
  if(cp) cp.innerHTML=".ct2/plans/canvas/<b>answered</b>/"+C.ticket+"-r"+C.round+".canvas.html";
  render();
});
$('#dlBtn').addEventListener('click',function(){
  var blob=new Blob([buildToken()],{type:"application/json"});
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
    config = json.dumps(
        {
            "decision": record.get("id"),
            "ticket": record.get("ticket"),
            "round": canvas.get("round", 0),
            "nonce": record.get("nonce"),
        },
        ensure_ascii=False,
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ko"><head><meta charset="UTF-8">'
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
        '<footer class="note">CT2 Helm Canvas · 자기완결 HTML(외부 의존성 0) · '
        f"provider format(html) — spec/helm-canvas.md</footer>"
        "</div>"
        f"<script>window.CANVAS={config};</script>"
        f"<script>{_JS}</script>"
        "</body></html>\n"
    )


def parse_token(text: str) -> dict:
    """Parse a 'CT2-DECISION {json}' token into a dict. Raises ValueError."""
    text = (text or "").strip()
    prefix = "CT2-DECISION"
    if text.startswith(prefix):
        text = text[len(prefix):].strip()
    if not text:
        raise ValueError("empty decision token")
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed decision token: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError("decision token must be a JSON object")
    return obj
