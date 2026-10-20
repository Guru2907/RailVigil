## What and why

<!-- One or two sentences. Link the spec section or backlog item. -->

## Module
- [ ] Encroachment
- [ ] Intrusion
- [ ] Shared (`cv/common`, core, db, migrations, job queue, CI) — needs the other owner's review

## Checklist
- [ ] Tests added or updated; `pytest` and `ruff check .` pass in `backend/`
- [ ] `npm run lint` and `npm run build` pass in `frontend/` (if frontend changed)
- [ ] Schema changes include an Alembic migration
- [ ] Zones go through `ZoneResolver`; no clip-specific zones, no whole-frame fallback
- [ ] No unmeasured accuracy/speed claims added to docs, UI or README
- [ ] No data, media, weights, databases or `.env` committed
- [ ] Docs/spec updated if behaviour changed

## How I tested it

<!-- Commands run, clips or images used, what you saw. -->
