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

## Results log
| Date | Module | Model / config | Test set | Metrics | Run |
|---|---|---|---|---|---|
| — | — | — | — | — | — |
