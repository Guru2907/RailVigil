# Evaluation

**Rule:** no accuracy, precision, recall, speed or dataset-size figure appears in the README, UI, reports or paper unless it was produced by the evaluation script on a frozen test set and can be reproduced. As of now **nothing has been measured.**

## Encroachment
- Detector: mask mAP50 and mAP50-95 per class on the location-split test set.
- Findings: precision, recall and false findings per 100 images against labels of the form "object X is an encroachment in zone Z".
- Zones: IoU of automatic zones against hand-drawn right-of-way on a sample.
- Sites: clustering purity (wrong merges and splits).

## Intrusion
- Labels: `clip, start_sec, end_sec, class` per real intrusion; negatives include empty zones and trains passing through the zone.
- Event-level precision and recall (time-overlap matching), false alerts per hour, confirmation delay.
- Used to choose final values for `CONFIRM_DWELL_SEC`, `MISS_GRACE_SEC`, `FRAME_SAMPLE_INTERVAL`, risk weights and severity bands; the chosen values and the run that justified them are recorded here.

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
