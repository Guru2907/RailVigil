# Intrusion evaluation labels

`labels.csv` columns: `clip, start_sec, end_sec, class, is_intrusion, notes`

- **Clip files are not committed.** Point `evaluate_intrusion.py --clips-dir` at the owner’s local folder.
- Prefer clip **stems** (no extension).
- **Only list clips we actually have.** Times must be checked by watching each clip — no placeholder rows.
- Negatives required: empty track, person outside the zone, train passing through the zone.

Owner will share the latest intrusion clips; then fill `labels.csv` and the source/licence table in `backend/tests/regression/README.md`.

See `docs/EVALUATION.md` and issue #3 part B.
