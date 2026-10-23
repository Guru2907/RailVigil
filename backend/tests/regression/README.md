# Intrusion regression clips

Clips live **outside** the repo. Set `GOLDEN_CLIPS_DIR` to a folder that contains:

| File | Expected |
|------|----------|
| `person_crossing.mp4` + `person_crossing.zone.json` | 1 person incident |
| `two_people.mp4` + `two_people.zone.json` | 2 person incidents |
| `empty_or_train.mp4` + `empty_or_train.zone.json` | 0 incidents |

Expected ranges are committed under `expected/`. Map these names to the owner’s real clip filenames when the clips arrive (or rename the local files to match).

## Running

```bash
# from backend/
# PowerShell: $env:GOLDEN_CLIPS_DIR="C:\path\to\golden-clips"
pytest tests/regression -m requires_weights -q
```

Without `GOLDEN_CLIPS_DIR` or YOLO weights the tests are **skipped** (CI stays green).

## Clip sources / licences

Fill in once the owner shares the latest intrusion clips:

| Clip (local name) | Maps to golden key | Source | Licence | Notes |
|------|--------|--------|---------|-------|
| _TBD_ | `person_crossing` | _owner share_ | _TBD_ | one person in zone |
| _TBD_ | `two_people` | _owner share_ | _TBD_ | two people |
| _TBD_ | `empty_or_train` | _owner share_ | _TBD_ | empty track or train-only |
