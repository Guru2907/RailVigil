# Contributing

## Ownership

| Area | Owner | Paths |
|---|---|---|
| Physical encroachment | Gurpreet | `backend/app/cv/encroachment/`, its tests, `docs/ENCROACHMENT_SPEC.md`, `docs/DATASET.md` |
| Intrusion | Siddeshwar | `backend/app/cv/intrusion/`, its tests, `docs/INTRUSION_SPEC.md` |
| Shared | both | `backend/app/cv/common/`, `backend/app/core/`, `backend/app/db/` (models, repositories), `backend/alembic/`, `backend/app/services/job_queue.py`, `backend/app/services/job_runner.py`, `backend/app/api/router.py`, `backend/app/main.py`, requirement files, CI |

A change to a shared path needs a review from the other owner.

## Workflow
- Branch from an up-to-date `main`: `feat/<topic>`, `fix/<topic>`, `chore/<topic>`, `docs/<topic>`.
- Open a pull request into `main`. It merges when CI is green and the review is done. Small agreed chores may be pushed directly by the repository owner.
- Commit messages: `type(scope): summary` — e.g. `feat(encroachment): add zone overlap rule`, `fix(intrusion): close events on video end`.
- No co-author trailers on commits or pull requests.

## Rules every change must follow
- **Tests:** new behaviour comes with tests; `pytest` and `ruff check .` pass in `backend/`, `npm run lint` and `npm run build` pass in `frontend/`.
- **Schema changes** come with an Alembic migration (`alembic revision --autogenerate -m "..."`, then review the file). `tests/db/test_migrations.py` fails if models and migrations drift.
- **Zones:** always go through `ZoneResolver` (`backend/app/cv/common/zones.py`). Never hard-code zones for specific clips and never fall back to the whole frame.
- **Terminology:** intrusion code never calls its events "encroachment", and encroachment code never calls its findings "intrusions". Both are *potential* findings for an officer to review.
- **Claims:** no accuracy, speed or dataset figure goes into the README, UI, docs or paper unless it was measured with the evaluation script and the run is reproducible (see `docs/EVALUATION.md`).
- **Never commit** databases, uploaded media, outputs, model weights, datasets or `.env` files.
- **Thresholds** are configuration values with a comment saying whether they are provisional or validated.
- **Dependencies** are pinned; add new ones to `requirements.txt` (runtime) or `requirements-dev.txt` (tests/tools).
