"""Guardrails for the helm canvas: spec ingest validation, render-safe HTML.

Two failure modes drive this test file:
1. UI breaks when content escapes its container or pasted rich HTML rewrites
   the DOM — covered by markup-safety tests below.
2. The user can't see helm's judgment when a malformed spec (smart quotes,
   trailing commas, wrong types) silently produces a broken canvas — covered
   by parse/validate tests below.

The canvas lifecycle is already covered in test_canvas_lifecycle.py; this file
focuses on the guardrails themselves so a future change cannot quietly remove
them.
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CANVAS_BIN = REPO_ROOT / "bin" / "ct2-helm-canvas"
sys.path.insert(0, str(REPO_ROOT / "bin"))

import _ct2_canvas  # noqa: E402


def run_cmd(args, cwd):
    return subprocess.run(
        [str(a) for a in args],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )


MIN_SPEC = {
    "ticket": "001-demo",
    "canvas": {
        "round": 0,
        "title": "Demo",
        "interpretation": {"summary": "S", "quote": "Q"},
        "scope": [{"label": "a", "state": "in"}],
        "tickets": [{"title": "t1", "size": "small", "items": ["i1"]}],
        "acceptance_criteria": [{"text": "AC", "accepted": True, "flagged": False}],
        "priority": "high",
        "constraints": [{"label": "x", "text": "y"}],
    },
}


class ParseSpecTest(unittest.TestCase):
    def test_valid_spec_parses(self):
        obj = _ct2_canvas.parse_spec(json.dumps(MIN_SPEC))
        self.assertEqual(MIN_SPEC["ticket"], obj["ticket"])

    def test_empty_spec_rejected(self):
        with self.assertRaises(ValueError) as cm:
            _ct2_canvas.parse_spec("")
        self.assertIn("empty", str(cm.exception))

    def test_non_object_root_rejected(self):
        with self.assertRaises(ValueError) as cm:
            _ct2_canvas.parse_spec("[1,2,3]")
        self.assertIn("JSON object", str(cm.exception))

    def test_smart_quotes_named_in_hint(self):
        with self.assertRaises(ValueError) as cm:
            _ct2_canvas.parse_spec('{“ticket”:“x”}')
        msg = str(cm.exception)
        self.assertIn("smart quotes", msg)
        self.assertIn("line", msg)
        self.assertIn("col", msg)

    def test_trailing_comma_named_in_hint(self):
        with self.assertRaises(ValueError) as cm:
            _ct2_canvas.parse_spec('{"ticket":"x","canvas":{},}')
        self.assertIn("trailing comma", str(cm.exception))

    def test_comment_named_in_hint(self):
        with self.assertRaises(ValueError) as cm:
            _ct2_canvas.parse_spec('{\n  // a comment\n  "ticket":"x"\n}')
        self.assertIn("comment", str(cm.exception))

    def test_bom_stripped(self):
        # Some editors prepend a BOM; that should not block parsing.
        obj = _ct2_canvas.parse_spec("﻿" + json.dumps(MIN_SPEC))
        self.assertEqual(MIN_SPEC["ticket"], obj["ticket"])

    def test_error_carries_excerpt(self):
        with self.assertRaises(ValueError) as cm:
            _ct2_canvas.parse_spec('{"ticket":"x" "canvas":{}}')  # missing comma
        self.assertIn("<<here>>", str(cm.exception))


class ValidateSpecTest(unittest.TestCase):
    def test_valid_spec_has_no_errors(self):
        self.assertEqual([], _ct2_canvas.validate_spec(MIN_SPEC))

    def test_missing_ticket_flagged(self):
        spec = json.loads(json.dumps(MIN_SPEC))
        spec.pop("ticket")
        errors = _ct2_canvas.validate_spec(spec)
        self.assertTrue(any("ticket" in e for e in errors))

    def test_non_object_canvas_flagged(self):
        spec = {"ticket": "x", "canvas": "not an object"}
        errors = _ct2_canvas.validate_spec(spec)
        self.assertTrue(any("canvas: must be an object" in e for e in errors))

    def test_wrong_priority_flagged(self):
        spec = json.loads(json.dumps(MIN_SPEC))
        spec["canvas"]["priority"] = "urgent"
        errors = _ct2_canvas.validate_spec(spec)
        self.assertTrue(any("priority" in e and "urgent" in e for e in errors))

    def test_wrong_scope_state_flagged(self):
        spec = json.loads(json.dumps(MIN_SPEC))
        spec["canvas"]["scope"][0]["state"] = "maybe"
        errors = _ct2_canvas.validate_spec(spec)
        self.assertTrue(any("scope[0].state" in e for e in errors))

    def test_non_list_scope_flagged(self):
        spec = json.loads(json.dumps(MIN_SPEC))
        spec["canvas"]["scope"] = "not a list"
        errors = _ct2_canvas.validate_spec(spec)
        self.assertTrue(any("scope: must be a list" in e for e in errors))

    def test_round_must_be_int(self):
        spec = json.loads(json.dumps(MIN_SPEC))
        spec["canvas"]["round"] = "0"
        errors = _ct2_canvas.validate_spec(spec)
        self.assertTrue(any("round" in e and "integer" in e for e in errors))

    def test_aggregate_errors_returned(self):
        # Multiple shape problems → all surfaced in one shot.
        spec = {"ticket": "", "canvas": {"priority": "x", "scope": "y"}}
        errors = _ct2_canvas.validate_spec(spec)
        self.assertGreaterEqual(len(errors), 3)


class ScriptSafeJSONTest(unittest.TestCase):
    def test_no_raw_angle_brackets_or_amp(self):
        # `<`, `>`, `&` are the characters that can break out of a <script>
        # block (closing tag, comment delimiters, named entities). All three
        # should be unicode-escaped in the encoded form.
        encoded = _ct2_canvas._safe_json_for_script({"x": "</script><!--a-->&end"})
        for ch in ("<", ">", "&"):
            self.assertNotIn(ch, encoded, f"raw {ch!r} must be escaped")

    def test_roundtrip_preserves_content(self):
        original = {"title": "</script><!-- comment --> & ampersand"}
        encoded = _ct2_canvas._safe_json_for_script(original)
        self.assertEqual(original, json.loads(encoded))

    def test_line_terminators_escaped(self):
        # U+2028 / U+2029 are valid in JSON strings but are JS line
        # terminators in older runtimes — escape them so embedded JSON cannot
        # split the inline script across lines.
        encoded = _ct2_canvas._safe_json_for_script({"x": "a b c"})
        self.assertNotIn(" ", encoded)
        self.assertNotIn(" ", encoded)
        self.assertEqual("a b c", json.loads(encoded)["x"])


class ParseTokenTest(unittest.TestCase):
    def test_valid_token_parses(self):
        obj = _ct2_canvas.parse_token('CT2-DECISION {"decision":"d","nonce":"n"}')
        self.assertEqual("d", obj["decision"])

    def test_truncated_token_hint(self):
        with self.assertRaises(ValueError) as cm:
            _ct2_canvas.parse_token('CT2-DECISION {"a":{"b":1}')  # missing closing brace
        self.assertIn("truncated", str(cm.exception))

    def test_smart_quotes_hint(self):
        with self.assertRaises(ValueError) as cm:
            _ct2_canvas.parse_token('CT2-DECISION {“decision”:“d”}')
        self.assertIn("smart quotes", str(cm.exception))


class RenderHTMLSafetyTest(unittest.TestCase):
    """Render-side safety: rendered HTML stays well-formed even when fields
    carry payloads that would otherwise break the page (script tags, comments,
    long unbreakable strings)."""

    def _render(self, **fields):
        canvas = json.loads(json.dumps(MIN_SPEC["canvas"]))
        canvas.update(fields)
        record = {
            "id": "decision-test",
            "ticket": MIN_SPEC["ticket"],
            "nonce": "n",
            "canvas": canvas,
        }
        return _ct2_canvas.render(record)

    def test_html_well_formed(self):
        html = self._render()
        HTMLParser().feed(html)  # raises on malformed markup

    def test_inline_script_config_block_safe(self):
        # The window.CANVAS config carries ticket/nonce/decision/round into the
        # page as inline JSON. Even if the ticket id ever contained `</script>`
        # (or any of the other breakout sequences), the escape must make the
        # encoded line incapable of closing the surrounding <script>.
        record = {
            "id": "decision-test",
            "ticket": "</script><script>evil()</script>",
            "nonce": "n",
            "canvas": MIN_SPEC["canvas"],
        }
        html = _ct2_canvas.render(record)
        config_match = re.search(r"window\.CANVAS=(\{.+?\});</script>", html)
        self.assertIsNotNone(config_match, "window.CANVAS line not found")
        config_text = config_match.group(1)
        self.assertNotIn("</script>", config_text)
        self.assertNotIn("<script>", config_text)
        self.assertIn("\\u003c", config_text)
        # The HTML overall still parses with a strict HTML parser.
        HTMLParser().feed(html)

    def test_panel_text_escaped(self):
        # ticket-rendered title carries <script>; it must be HTML-escaped in
        # the panel body, never live as real markup.
        html = self._render(title="<script>x()</script>")
        self.assertNotIn("<script>x()</script>", html)
        self.assertIn("&lt;script&gt;x()&lt;/script&gt;", html)

    def test_render_failure_banner_present_and_hidden_by_default(self):
        # The visible recovery banner exists in the rendered HTML so a JS
        # render error has a place to surface — without it, a thrown error
        # would silently blank the AI-judgment panel. It must also be hidden
        # by default (no 'on' class pre-applied, CSS sets display:none).
        html = self._render()
        self.assertIn('id="renderFail"', html)
        self.assertNotIn("render-fail on", html)
        # The CSS rule that hides the banner by default must also be present.
        self.assertIn(".render-fail{", html)
        self.assertIn("display:none", html)

    def test_paste_handler_installed(self):
        html = self._render()
        self.assertIn("addEventListener('paste'", html)
        self.assertIn("text/plain", html)


class CanvasGeneratorCLITest(unittest.TestCase):
    """End-to-end checks against the bin/ct2-helm-canvas CLI."""

    def make_project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        init = run_cmd(["bash", REPO_ROOT / "bin" / "ct2-init", project], cwd=REPO_ROOT)
        self.assertEqual(0, init.returncode, init.stderr)
        return project

    def test_smart_quote_spec_rejected_with_hint(self):
        project = self.make_project()
        (project / "spec.json").write_text('{“ticket”:“x”}', encoding="utf-8")
        res = run_cmd(["python3", CANVAS_BIN, "generate", "--spec", "spec.json"], cwd=project)
        self.assertNotEqual(0, res.returncode)
        self.assertIn("smart quotes", res.stderr)
        # No canvas file should have been written.
        self.assertEqual([], list((project / ".ct2" / "plans" / "canvas" / "open").iterdir()))
        self.assertEqual(
            [], list((project / ".ct2" / "decisions" / "pending").iterdir())
        )

    def test_invalid_schema_rejected_with_aggregated_errors(self):
        project = self.make_project()
        bad = {
            "ticket": "x",
            "canvas": {"priority": "urgent", "scope": [{"state": "maybe"}]},
        }
        (project / "spec.json").write_text(json.dumps(bad), encoding="utf-8")
        res = run_cmd(["python3", CANVAS_BIN, "generate", "--spec", "spec.json"], cwd=project)
        self.assertNotEqual(0, res.returncode)
        self.assertIn("validation failed", res.stderr)
        self.assertIn("priority", res.stderr)
        self.assertIn("scope[0].state", res.stderr)

    def test_valid_spec_still_generates(self):
        project = self.make_project()
        (project / "spec.json").write_text(json.dumps(MIN_SPEC), encoding="utf-8")
        res = run_cmd(["python3", CANVAS_BIN, "generate", "--spec", "spec.json"], cwd=project)
        self.assertEqual(0, res.returncode, res.stderr)
        canvas = project / ".ct2" / "plans" / "canvas" / "open" / "001-demo-r0.canvas.html"
        self.assertTrue(canvas.exists())


if __name__ == "__main__":
    unittest.main()
