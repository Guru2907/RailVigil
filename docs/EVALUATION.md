# Evaluation

**Rule:** no accuracy, precision, recall, speed or dataset-size figure appears in the README, UI, reports or paper unless it was produced by the evaluation script on a frozen test set and can be reproduced. As of now **nothing has been measured.** Intrusion metrics below are only recorded when a real run is logged.

## Encroachment
- Detector: mask mAP50 and mAP50-95 per class on the location-split test set.
- Findings: precision, recall and false findings per 100 images against labels of the form "object X is an encroachment in zone Z".
- Zones: IoU of automatic zones against hand-drawn right-of-way on a sample.
- Sites: clustering purity (wrong merges and splits).

## Intrusion
- Labels: `datasets/intrusion/labels.csv` (`clip, start_sec, end_sec, class, is_intrusion, notes`). Negatives include empty zones, person near but outside the zone, and trains passing through the zone.
- Script: `backend/scripts/evaluate_intrusion.py` — event-level precision / recall (time-overlap matching), false alerts per hour, mean confirmation delay; optional `--sweep` for `confirm_dwell`, `miss_grace`, `frame_sample`, `persistent_dwell`.
- Regression: `backend/tests/regression/` on three golden clips via `GOLDEN_CLIPS_DIR` (skipped in CI with `@pytest.mark.requires_weights`).
- Used to choose final values for `CONFIRM_DWELL_SEC`, `MISS_GRACE_SEC`, `FRAME_SAMPLE_INTERVAL`, risk weights and severity bands; the chosen values and the run that justified them are recorded here.

### How to run (intrusion)
```bash
cd backend
# offline matching against saved predictions
python scripts/evaluate_intrusion.py --preds path/to/preds.json

# live pipeline (needs weights + clips + .zone.json sidecars)
python scripts/evaluate_intrusion.py --clips-dir /path/to/clips --run-pipeline

# threshold sweep
python scripts/evaluate_intrusion.py --clips-dir /path/to/clips --run-pipeline \
  --sweep confirm_dwell 0.3,0.6,1.0,2.0,3.0
```

### Threshold status (issue #3)
Defaults in `backend/app/core/config.py` remain **candidates pending a logged evaluation run** on the labelled set. Do not change comments to "validated" until a row is added below with reproducible metrics. Paper draft "3 s" confirmation is **not** adopted until measured recall/precision support it.

Rows in `labels.csv` must match clips we actually have, with start/end times checked by watching each clip (no placeholder rows).

## Paper
The draft paper's 96-track benchmark results are not backed by code or data in this repository. They must be reproduced from code added here or removed from the paper.

## How to produce the numbers
- **Trained model:** `training/evaluate.py --name <run>`. Ultralytics validation on the frozen **test** split gives mask and box precision, recall, mAP50 and mAP50-95 per class. Saved as `training/runs/<run>/eval_test.json`.
- **Pretrained baseline:** `backend/scripts/evaluate_baseline.py` runs the same photos through the baseline pipeline. It gives box AP50 per class, plus precision and recall at confidence 0.25. Compare it with the trained model's box mAP50.
- **Ground truth must be human-corrected.** `import_labels.py` refuses uncorrected pre-labels, because measuring the baseline against its own guesses would be meaningless.
- Each training run records the git commit and a dataset fingerprint (`railvigil_run.json`).

## Results log
| Date | Module | Model / config | Test set | Metrics | Run |
|---|---|---|---|---|---|
| — | — | — | — | — | — |
| — | intrusion | yolov8n + defaults | `datasets/intrusion/labels.csv` + owner clips | **not yet measured** — awaiting labelled clips | `python scripts/evaluate_intrusion.py --clips-dir $CLIPS --run-pipeline` |
| — | intrusion regression | same | `GOLDEN_CLIPS_DIR` 3 clips | pass/skip via `pytest -m requires_weights` | `tests/regression/test_golden_clips.py` |
