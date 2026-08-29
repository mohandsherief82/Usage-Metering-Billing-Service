# Build Log — AI usage, honestly

Required by the brief (Section 3 & 10): AI-assisted building is encouraged, but this log
has to stay honest about where it helped, where it was wrong, and what got changed. The
bar the brief sets: you must be able to explain any 2–3 lines of your code that an
evaluator points at. "The AI wrote it" is not an answer — this file is where you show the
work of actually owning the code.

Update this **as you build**, not retroactively at submission time — specifics fade fast.
Vague entries ("AI helped with the webhook handler") aren't useful; be concrete about what
was wrong and what you changed, e.g. "AI's first draft of verify_and_parse_webhook read
the body via request.json() before verifying the signature — that reserializes the payload
and breaks signature verification. Fixed by reading request.body() raw and passing those
exact bytes to stripe.Webhook.construct_event."

## Format

### <date> — <what you were building>
- **Where AI helped**: Code generation
- **Where it was wrong / had to be corrected**: ...
- **What I changed and why**:  

---

## Entries

### 2026-08-28 — Project scaffolding, architecture, TUI
- **Where AI helped**: generated the initial folder structure, `pyproject.toml`, D2
  architecture diagram, GUIDE.md checklist, and the full Textual TUI (screens, custom
  widgets, theme, async data layer with live/demo fallback).
- **Where it was wrong / had to be corrected**: _(fill in as you review/modify the
  generated TUI and scaffolding — note anything you had to fix or disagreed with)_
- **What I changed and why**: _(fill in)_

### <next entry — data model / Tenant schema>
- **Where AI helped**: ...
- **Where it was wrong / had to be corrected**: ...
- **What I changed and why**: ...
