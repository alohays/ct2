# CT2-Status: State Query

You are executing a **one-shot CT2 status query**. Output the current state and exit — no loop, no user interaction required.

---

## Execution

1. **Verify `.ct2/` exists** in the current working directory. If absent:
   ```
   This project has not been initialized with ct2.
   Run 'ct2-init' in your project directory first.
   ```
   Then stop.

2. **Run `ct2-status`** if available in PATH:
   ```bash
   ct2-status
   ```

3. If `ct2-status` is not in PATH, produce the output manually by reading each directory:

```
CT2 Status: {absolute path to project}
─────────────────────────────────────────────────────────
DRAFT      {count}   {filenames with priority tags}
BACKLOG    {count}   {filenames with [priority] tags, sorted by priority then sealed}
IN-PROG    {count} ● {filename [elapsed time]}
IN-REVIEW  {count}   {filename (r{n}: cc={status}, cx={status})}
REJECTED   {count}
ESCALATED  {count}
DONE       {count}
─────────────────────────────────────────────────────────
Forge:    {ACTIVE (heartbeat Xm ago) | IDLE | DEAD (last seen Xh ago)}
Lens-CC:  {ACTIVE (heartbeat Xm ago) | IDLE | DEAD}
Lens-CX:  {ACTIVE (heartbeat Xm ago) | IDLE | DEAD}
─────────────────────────────────────────────────────────
INBOX
  ct2-helm    {N} unread   {type} from {role} [{ticket-id}]
  ct2-forge   {N} unread
  ct2-lens-cc {N} unread
  ct2-lens-cx {N} unread
─────────────────────────────────────────────────────────
```

### How to Read Review Status for IN-REVIEW tickets

For each ticket in `.ct2/in-review/`:
- Read `review-round` from frontmatter
- Check for `.ct2/reviews/{id}-cc-r{round}.md` → cc verdict
- Check for `.ct2/reviews/{id}-cx-r{round}.md` → cx verdict
- Show as `(r{round}: cc={verdict}, cx={verdict})` where verdict is `pending`, `approved`, or `rejected`

### How to Read Heartbeat Status

For each role (`forge`, `lens-cc`, `lens-cx`):
- Read `.ct2/.meta/ct2-{role}.heartbeat` modification time
- `heartbeat_timeout_min` from `harness.yaml` (default 15)
- If file missing: `IDLE`
- If mtime < timeout: `ACTIVE (heartbeat Xm ago)`
- If mtime ≥ timeout: `DEAD (last seen Xh ago)`

### How to Count Inbox Unread

For each role's inbox directory `.ct2/inbox/{role}/`:
- Count `.md` files **directly** in that directory (not in `processing/` or `done/` subdirectories)
- Show the first two messages' `type` and `from` fields

---

This skill is one-shot. After displaying the status, your task is complete.
