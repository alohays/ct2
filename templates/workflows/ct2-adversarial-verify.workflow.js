/*
 * ct2-adversarial-verify.workflow.js
 *
 * CT2-blessed adversarial-verify workflow template (reference, forward-looking).
 *
 * STATUS — OPTIONAL CONTENT-TIER MATERIAL, NOT PROTOCOL SURFACE.
 *   CT2 core never depends on this file. Deleting templates/workflows/
 *   changes nothing about the CT2 protocol, its tools, or its tests. The
 *   template exists so users who point a native dynamic workflow at a CT2
 *   ticket do not hand-roll a leaky verify pass (strategy gaps G3/G10,
 *   docs/ct2-dynamic-workflow-strategy-2026-06.md).
 *
 * AUTHORITY — SELF-VERIFICATION OUTPUT IS EVIDENCE, NEVER A VERDICT.
 *   Whatever this workflow concludes, the ticket still requires independent
 *   cross-vendor dual review (lens-cc AND lens-cx sidecars; either reviewer
 *   rejecting means rejected), and only ct2-reconcile moves a ticket to
 *   done/. This run re-enters CT2 through exactly one return channel — an
 *   evidence record — plus a pointer-only advisory inbox notification that
 *   carries no findings. It never moves a ticket, never writes
 *   .ct2/.meta/ct2-active-role, and never claims the in-progress slot.
 *
 * SURFACE — Claude Code dynamic workflows (research preview, v2.1.154+).
 *   Copy into .claude/workflows/ to use; the runtime provides agent(),
 *   parallel(), pipeline(), phase(), log(), and workflow() in scope. The
 *   runtime disables Date.now(), Math.random(), and argless new Date() for
 *   journaled resume, so every identifier below derives from ticket id +
 *   content hash + round counter. If the research-preview surface drifts,
 *   defer to the official workflow docs; the independence wiring documented
 *   in templates/workflows/README.md is the part to preserve.
 */

export const meta = {
  name: "ct2-adversarial-verify",
  description:
    "Adversarial self-verification of one CT2 ticket artifact. Findings re-enter CT2 through one return channel — an evidence record — with a pointer-only advisory inbox notification; the run is evidence only, never a verdict.",
  version: "0.1.0",
  args: {
    ticket: {
      type: "string",
      required: true,
      description:
        "CT2 ticket id this run is attributed to (the Named-ticket rule of the Native-Workflow Re-Entry Contract, spec/conformance.md), e.g. 042-fix-reconciler-lock",
    },
    artifact: {
      type: "string",
      required: true,
      description:
        "Artifact under review: a file path or git ref readable from the project root",
    },
    round: {
      type: "string",
      required: false,
      description:
        "Round counter folded into the derived run id (default 1); pass the ticket's review-round when known",
    },
  },
};

// ---------------------------------------------------------------------------
// Verifier lenses. A static literal table: nothing computed at run time can
// leak into a lens definition. To add skeptics, add rows here — never new
// inputs to buildVerifierPrompt.
// ---------------------------------------------------------------------------
const SKEPTIC_LENSES = [
  {
    id: "skeptic-correctness",
    charge:
      "Hunt for logic errors, broken invariants, and unhandled edge cases. Assume the artifact is wrong and try to prove it.",
  },
  {
    id: "skeptic-regression",
    charge:
      "Hunt for behavior the change silently breaks: callers, tests, specs, and documented contracts the artifact contradicts.",
  },
  {
    id: "skeptic-scope",
    charge:
      "Hunt for requirement drift: ticket requirements the artifact does not satisfy, and changes the ticket never asked for.",
  },
];

const CROSS_VENDOR_LENS = {
  id: "cx-advisory",
  charge:
    "Second-model-family adversarial pass: hunt for defects, contract violations, and unjustified claims in the artifact relative to the ticket. Report findings only.",
};

// ---------------------------------------------------------------------------
// Structured-output schemas for agent(prompt, { schema }).
// ---------------------------------------------------------------------------
const INGEST_SCHEMA = {
  type: "object",
  properties: {
    ticketText: { type: "string" },
    artifactText: { type: "string" },
  },
  required: ["ticketText", "artifactText"],
};

const FINDINGS_SCHEMA = {
  type: "object",
  properties: {
    findings: {
      type: "array",
      items: {
        type: "object",
        properties: {
          title: { type: "string" },
          detail: { type: "string" },
          blocking: { type: "boolean" },
        },
        required: ["title", "detail", "blocking"],
      },
    },
  },
  required: ["findings"],
};

const CODEX_RUNNER_SCHEMA = {
  type: "object",
  properties: {
    status: { type: "string", enum: ["run", "not-run"] },
    output: { type: "string" },
    note: { type: "string" },
  },
  required: ["status", "output", "note"],
};

const REENTRY_SCHEMA = {
  type: "object",
  properties: {
    evidenceRecorded: { type: "boolean" },
    inboxNotified: { type: "boolean" },
    note: { type: "string" },
  },
  required: ["evidenceRecorded", "inboxNotified", "note"],
};

// ---------------------------------------------------------------------------
// INDEPENDENCE BY CONSTRUCTION (strategy G3; spec/conformance.md,
// Prompt-Construction Independence).
//
// This is the only function that produces a verifier prompt, and its
// signature is the invariant: a verifier prompt is a pure function of
//   (artifactText, ticketText, lens)
// and of nothing else. There is no parameter through which a sibling
// verifier's findings, the orchestrator's running tally, or any other
// subagent return value can flow into a verifier prompt. Sibling results
// exist only downstream of every buildVerifierPrompt call (synthesis and
// re-entry). Do not add parameters to this function.
// ---------------------------------------------------------------------------
function buildVerifierPrompt(artifactText, ticketText, lens) {
  return [
    "You are an independent CT2 verifier subagent (" + lens.id + ").",
    "Your prompt contains ONLY the artifact under review and the ticket text.",
    "You have not seen, and must not ask for, any other reviewer's output.",
    "",
    "Charge: " + lens.charge,
    "",
    "Rules:",
    "- Read-only: do not edit files, do not run write commands, never touch .ct2/.",
    "- Report findings against the artifact and ticket below; cite file/line where possible.",
    "- Mark a finding blocking only when it would justify rejecting the ticket as-is.",
    "- Your output is evidence for CT2, never a verdict: claim no approval or rejection authority.",
    "",
    "## Ticket",
    ticketText,
    "",
    "## Artifact under review",
    artifactText,
  ].join("\n");
}

// Deterministic 32-bit FNV-1a content hash. The workflow runtime disables
// the nondeterministic time and random builtins, so run identifiers must
// derive from stable inputs: ticket id + content hash + round counter
// (strategy G8 determinism boundary).
function contentHash(text) {
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}

function buildIngestPrompt(ticketId, artifactRef) {
  return [
    "You are a read-only ingest subagent for CT2 ticket " + ticketId + ".",
    "",
    "1. Locate the ticket file whose name starts with '" + ticketId + "'.",
    "   Tickets live directly in the .ct2/ state directories; search them in",
    "   order — in-review/, in-progress/, backlog/, then draft/, rejected/,",
    "   escalated/, done/ — and read the first match in full.",
    "2. Read the artifact under review: '" + artifactRef + "'.",
    "   If it is a git ref, use read-only git (show/diff/log); if it is a path, read the file(s).",
    "3. Return both texts verbatim. Do not summarize detail away; verifiers see only what you return.",
    "",
    "Rules: read-only throughout. No file edits, no .ct2/ writes, no git mutations.",
  ].join("\n");
}

// Cross-vendor advisory pass (fail-soft). The lens-cx-equivalent prompt is
// built by the same buildVerifierPrompt function as every sibling, then
// handed to a Bash-running subagent that invokes the Codex CLI in a
// read-only sandbox. If codex is absent the pass is marked not-run and the
// whole run is explicitly NON-SUFFICIENT for CT2 dual review. Either way,
// the authoritative cross-vendor check remains the lens-cx sidecar at
// review time — this pass never substitutes for it.
function buildCodexRunnerPrompt(verifierPrompt) {
  return [
    "You are a runner subagent. Execute the cross-vendor verifier pass via Bash.",
    "",
    "1. Check availability: command -v codex",
    "2. If codex is NOT on PATH, do not improvise a substitute reviewer.",
    '   Return status "not-run", output "", and note "codex CLI absent; cross-vendor pass skipped".',
    "3. If codex IS available, run it from the project root in a read-only",
    "   sandbox with the review prompt delivered verbatim on stdin:",
    "",
    "   codex exec --sandbox read-only - <<'CT2_CX_PROMPT'",
    "   ...the review prompt below, byte for byte...",
    "   CT2_CX_PROMPT",
    "",
    '4. Return status "run", the codex output verbatim in output, and a one-line note.',
    "",
    "Rules: read-only throughout; never write files; never touch .ct2/.",
    "Do not add your own review opinion to output — relay codex verbatim.",
    "",
    "## Review prompt to deliver to codex",
    verifierPrompt,
  ].join("\n");
}

// ---------------------------------------------------------------------------
// RE-ENTRY (spec/conformance.md, Native-Workflow Re-Entry Contract: the
// single-recognized-return-channel rule, the non-role-holding-subagents
// rule, and the parent-owns-writes rule; strategy G10).
//
// Exactly one subagent in this workflow may write. The evidence record
// (ct2-evidence, a claims.jsonl row) is THE single recognized return
// channel for this run's findings. The inbox message (ct2-bridge
// notify — the notify-only advisory bridge; ct2-inbox is the
// recipient-side claim/ack tool and writes no messages) is a pointer-only
// advisory notification: its body cites the claim id, the evidence path,
// and the ticket id, never the findings payload, so it is not a second
// return channel. Every other subagent is read-only. The forbidden list is
// restated to the subagent because workflow subagents run with
// auto-approved edits (forced acceptEdits).
// ---------------------------------------------------------------------------
function buildReentryPrompt(runId, ticketId, summaryLine, detailsText, exitCode) {
  return [
    "You are the single re-entry writer for CT2 adversarial-verify run " + runId + ".",
    "Run exactly the two commands below from the project root, then report.",
    "Pass the summary line and details text from the sections at the bottom,",
    "shell-quoted, as the corresponding argument values.",
    "Both CT2 tools are invoked by bare name (the CT2 installer puts",
    "~/.ct2/bin on PATH); if a bare name is not found, fall back to",
    '"$HOME/.ct2/bin/<tool>".',
    "",
    "1. Append the evidence record — the single recognized return channel",
    "   for this run's findings. An exit status of 1 from this command",
    "   means the record was written with ok=false — expected when blocking",
    "   findings exist, not a command failure (exit status 2 is a failure).",
    "   Note the claim id and evidence path the command prints; step 2",
    "   needs both:",
    "",
    "   ct2-evidence verifier \\",
    "     --ticket " + ticketId + " \\",
    "     --name ct2-adversarial-verify \\",
    "     --produced-by-agent ct2-adversarial-verify/" + runId + " \\",
    "     --exit-code " + exitCode + " \\",
    "     --summary <summary line> \\",
    "     --details <details text>",
    "",
    "2. Send the advisory inbox notification. It is a pointer to the",
    "   evidence record, not a second return channel: the body cites only",
    "   the claim id, the evidence path, and the ticket id — never the",
    "   findings themselves:",
    "",
    "   ct2-bridge notify \\",
    "     --source ct2-adversarial-verify \\",
    "     --to ct2-helm \\",
    "     --ticket " + ticketId + " \\",
    "     --subject <summary line> \\",
    "     --body 'evidence claim <claim id> at <evidence path> for ticket " + ticketId + "'",
    "",
    "Forbidden — this run holds no role and no ticket authority:",
    "- never move/copy/delete any ticket file between or out of the .ct2/",
    "  state directories (draft/, backlog/, in-progress/, in-review/,",
    "  rejected/, escalated/, done/)",
    "- never write .ct2/.meta/ct2-active-role",
    "- never claim the in-progress slot (no ct2-pickup, no lifecycle locks)",
    "- never call ct2-reconcile, ct2-seal, or ct2-revise",
    "- never edit tickets, sidecars, or source files",
    "",
    "## Summary line",
    summaryLine,
    "",
    "## Details text",
    detailsText,
  ].join("\n");
}

export default async function ct2AdversarialVerify(args) {
  const ticketId = String(args.ticket || "").trim();
  const artifactRef = String(args.artifact || "").trim();
  const round = String(args.round || "1").trim();
  if (ticketId === "" || artifactRef === "") {
    throw new Error(
      "ct2-adversarial-verify: args.ticket and args.artifact are required — a workflow that names no CT2 ticket produces advisory noise that can never move state"
    );
  }

  phase("ingest");
  const ingest = await agent(buildIngestPrompt(ticketId, artifactRef), {
    schema: INGEST_SCHEMA,
  });
  const runId =
    "ct2av-" +
    ticketId +
    "-r" +
    round +
    "-" +
    contentHash(ingest.ticketText + "\n" + ingest.artifactText);
  log(
    "run id " +
      runId +
      " (ticket id + content hash + round; time/random builtins are disabled in workflows)"
  );

  phase("fan-out independent skeptics");
  // Every skeptic prompt is fully constructed from (artifactText,
  // ticketText, lens) before any skeptic returns; parallel() hands sibling
  // results back to this orchestrator only after the fact, so no verifier
  // can observe another verifier.
  const skepticResults = await parallel(
    SKEPTIC_LENSES.map(function (lens) {
      return function () {
        return agent(
          buildVerifierPrompt(ingest.artifactText, ingest.ticketText, lens),
          { schema: FINDINGS_SCHEMA }
        );
      };
    })
  );

  phase("cross-vendor advisory pass");
  const crossVendorPrompt = buildVerifierPrompt(
    ingest.artifactText,
    ingest.ticketText,
    CROSS_VENDOR_LENS
  );
  let crossVendor = {
    status: "not-run",
    output: "",
    note: "cross-vendor runner failed before reporting",
  };
  try {
    crossVendor = await agent(buildCodexRunnerPrompt(crossVendorPrompt), {
      schema: CODEX_RUNNER_SCHEMA,
    });
  } catch (err) {
    log("cross-vendor runner threw: " + String(err && err.message ? err.message : err));
  }
  const crossVendorRan = crossVendor.status === "run";
  if (!crossVendorRan) {
    log(
      "codex CLI absent or unusable (" +
        crossVendor.note +
        ") — cross-vendor pass NOT RUN; this run is NON-SUFFICIENT for CT2 dual review and advisory only"
    );
  }

  phase("synthesize");
  // Sibling outputs meet here for the first time — strictly downstream of
  // every verifier prompt. They merge into evidence; they are never fed
  // back into another verifier.
  const findings = [];
  const failedLenses = [];
  let blocking = 0;
  for (let i = 0; i < skepticResults.length; i += 1) {
    const result = skepticResults[i];
    const lensId = SKEPTIC_LENSES[i].id;
    if (result === null) {
      // parallel() yields null for a thunk that threw. A skeptic that never
      // reported is missing evidence, not a clean pass and not a finding:
      // count it separately so it fails the evidence record closed below
      // instead of folding into the finding totals.
      failedLenses.push(lensId);
      continue;
    }
    for (const finding of result.findings) {
      if (finding.blocking) {
        blocking += 1;
      }
      findings.push(
        "[" +
          lensId +
          (finding.blocking ? "][blocking" : "") +
          "] " +
          finding.title +
          " — " +
          finding.detail
      );
    }
  }
  // Fail closed: a run in which any skeptic crashed must not land as
  // ok=true evidence — exit code 1 makes ct2-evidence record the claim
  // with ok=false (zero findings from a crashed verifier is absence of
  // evidence, not evidence of absence).
  const exitCode = blocking > 0 || failedLenses.length > 0 ? 1 : 0;
  const summaryLine =
    "adversarial-verify " +
    runId +
    ": " +
    blocking +
    " blocking / " +
    findings.length +
    " total finding(s); " +
    (failedLenses.length > 0
      ? failedLenses.length + " verifier(s) failed to report; "
      : "") +
    "cross-vendor pass " +
    (crossVendorRan
      ? "run (advisory)"
      : "NOT RUN — NON-SUFFICIENT for CT2 dual review") +
    "; evidence only, not a verdict";
  const detailsText = [
    "run: " + runId,
    "ticket: " + ticketId,
    "artifact: " + artifactRef,
    "round: " + round,
    "authority: none — this is self-verification evidence; the ticket still requires independent lens-cc AND lens-cx sidecars, and only ct2-reconcile moves tickets",
    "cross-vendor pass: " +
      (crossVendorRan
        ? "run via codex exec --sandbox read-only (advisory cross-vendor evidence, not a lens-cx sidecar)"
        : "not-run (" + crossVendor.note + "); this run is NON-SUFFICIENT for CT2 dual review"),
    "verifiers failed to report: " +
      (failedLenses.length > 0
        ? failedLenses.join(", ") + " (no finding recorded; rerun if this persists)"
        : "none"),
    "",
    "findings:",
  ]
    .concat(findings.length > 0 ? findings : ["(none)"])
    .concat(crossVendorRan ? ["", "codex advisory output:", crossVendor.output] : [])
    .join("\n");

  phase("re-entry");
  let reentry = {
    evidenceRecorded: false,
    inboxNotified: false,
    note: "re-entry writer failed before reporting",
  };
  try {
    reentry = await agent(
      buildReentryPrompt(runId, ticketId, summaryLine, detailsText, exitCode),
      { schema: REENTRY_SCHEMA }
    );
  } catch (err) {
    log("re-entry writer threw: " + String(err && err.message ? err.message : err));
  }

  return {
    runId: runId,
    ticket: ticketId,
    artifact: artifactRef,
    round: round,
    blockingFindings: blocking,
    totalFindings: findings.length,
    failedVerifiers: failedLenses.length,
    crossVendorPass: crossVendorRan ? "run" : "not-run",
    sufficientForCt2DualReview: false,
    verdictAuthority: "none",
    evidenceRecorded: reentry.evidenceRecorded,
    inboxNotified: reentry.inboxNotified,
    note: crossVendorRan
      ? "Advisory self-verification evidence. Authoritative review remains independent lens-cc AND lens-cx sidecars reconciled by ct2-reconcile."
      : "Advisory only and NON-SUFFICIENT for CT2 dual review: the cross-vendor pass did not run.",
  };
}
