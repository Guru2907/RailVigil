# Evaluation

**Rule:** no accuracy, precision, recall, speed or dataset-size figure appears in the README, UI, reports or paper unless it was produced by the evaluation script on a frozen test set and can be reproduced. The only measured figures so far are the **encroachment results** below. Intrusion metrics are recorded only once a real run is logged.

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

## Encroachment results (2026-10-24)

### Dataset
| | Train | Val | Test |
|---|---|---|---|
| Indian photos (Wikimedia Commons + Mapillary) | 139 | 39 | 39 |
| TACO litter photos (`train_only`, never val/test) | 100 | – | – |
| `structure_permanent` / `structure_temporary` objects | 136 / 80 | 36 / 27 | 35 / 18 |
| `vegetation` / `vehicle_parked` objects | 210 / 37 | 67 / 7 | 62 / 24 |
| `material_dump` objects (TACO litter mapped here) | 337 | 2 | 1 |
| Clean photos (no objects) | 25 | 3 | 6 |

- **Photos:**
  - 217 Indian photos: Commons, plus Mapillary photos taken on OpenStreetMap railway lines (HDX "Railways of India") in Uttar Pradesh, Delhi, West Bengal, Bihar, Haryana, Punjab and Assam.
  - Every photo was filtered to India and reviewed by eye; off-topic photos and duplicates were removed.
- **Labels:** pre-labelled by the pretrained baseline + MobileSAM, then corrected by hand in Roboflow (755 objects; 34 photos with no encroachment).
- **Splits:** by place (photos within 300 m, or a known duplicate scene, share a split); the test set is frozen.
- **Classes:** `debris_waste` was not used; waste and construction leftovers were labelled `material_dump`.

### Model selection (validation split only)
| Run | Model | Best epoch | Val mask mAP50 | Val mask mAP50–95 | Val box mAP50 |
|---|---|---|---|---|---|
| **`railvigil-s`** | YOLOv8s-seg, first 10 layers frozen, 640 px, batch 4, patience 50 | 76 / 87 | **0.299** | **0.150** | **0.356** |
| `railvigil-m` | YOLOv8m-seg, same settings, batch 2 | 37 / 115 | 0.294 | 0.148 | 0.297 |

`railvigil-s` was chosen on validation. Only the chosen model was run on the test split, and only once.

### Results on the 39 test photos
**Main comparison, box AP50:**

| Class | Pretrained baseline (P / R at conf 0.25) | Trained `railvigil-s` (P / R) | Test objects |
|---|---|---|---|
| `structure_permanent` | **0.673** (0.63 / 0.34) | 0.255 (0.43 / 0.34) | 35 |
| `structure_temporary` | **0.698** (0.75 / 0.17) | 0.186 (0.32 / 0.11) | 18 |
| `vegetation` | **0.982** (0.98 / 0.98) | 0.576 (0.65 / 0.56) | 62 |
| `vehicle_parked` | **0.817** (1.00 / 0.46) | 0.527 (0.64 / 0.38) | 24 |
| `material_dump` | 0.000 | 0.000 | 1 |
| **Mean over classes** | **0.634** | **0.309** | |

**Trained `railvigil-s` masks:**
- mask mAP50 **0.291**, mAP50–95 0.145, P 0.607, R 0.279;
- per class: vegetation 0.559, vehicle_parked 0.502, structure_permanent 0.261, structure_temporary 0.132.

### Confidence intervals
95 % bootstrap intervals come from 1000 resamples of the 39 test photos (`training/bootstrap_ci.py`).
- Box AP50 is computed with the same definition for both models (`rvdata.evaluate_boxes`).
- Classes with fewer than 5 test objects are excluded, which leaves `material_dump` (1 object) out.

| Class | Baseline | Fine-tuned `railvigil-s` | Test objects |
|---|---|---|---|
| `structure_permanent` | 0.673 [0.474, 0.899] | 0.274 [0.115, 0.452] | 35 |
| `structure_temporary` | 0.698 [0.421, 1.000] | 0.180 [0.019, 0.454] | 18 |
| `vegetation` | 0.982 [0.941, 1.000] | 0.567 [0.386, 0.714] | 62 |
| `vehicle_parked` | 0.817 [0.682, 1.000] | 0.489 [0.250, 0.629] | 24 |
| **Mean of these 4** | **0.792** [0.688, 0.905] | **0.378** [0.301, 0.472] | |

- **Paired difference** (fine-tuned − baseline): **−0.415 [−0.531, −0.304]**. The gap is far larger than chance.
- The wide per-class intervals (e.g. temporary structures, 18 objects) show how much a bigger test set is needed.

### Reading the numbers
- **The fine-tuned model reaches about half the baseline's box AP50, so the baseline stays the default** (`ENC_MODELS` unchanged; `railvigil-s` is not promoted).
  - With ~140 Indian training photos, structures (especially temporary ones) are learned poorly.
  - Vegetation and vehicles transfer best.
- **The baseline figures are likely optimistic.** The ground truth was made by correcting the baseline's own pre-labels (anchoring). Treat 0.634 as an upper estimate.
- **The test set is small** (18–62 objects per class), and `material_dump` has a single test object, so its score is not interpretable.
- **Method:** baseline AP comes from `evaluate_baseline.py` (all-point interpolation); trained-model AP from Ultralytics validation (COCO-style).
- **Next:** more Indian photos (the team's own trackside photos, structures first), and a test set labelled independently of any model's pre-labels.

### Reproduce
`training/build_dataset.py` → `training/train.py --name railvigil-s --epochs 150 --batch 4 --patience 50 --freeze 10` (≈11 min on an RTX 3050 Laptop 4 GB) → `training/evaluate.py --name railvigil-s` → `backend/scripts/evaluate_baseline.py` → `training/bootstrap_ci.py --name railvigil-s`.

## Results log
| Date | Module | Model / config | Test set | Metrics | Run |
|---|---|---|---|---|---|
| 2026-10-24 | Encroachment | Baseline: `oiv7-v8s@4663086e1b8e` + `world-v8s-railvigil@533a607ff9f2` | 39 Indian test photos, dataset `d7297135357c1df5` | box AP50 0.634 (mean of classes with test objects) | `training/runs/baseline_eval_test.json` |
| 2026-10-24 | Encroachment | `railvigil-s` (YOLOv8s-seg, freeze 10, best epoch 76), weights `9b43e1832858` | same | box mAP50 0.309; mask mAP50 0.291, mAP50–95 0.145, P 0.607, R 0.279 | `training/runs/railvigil-s/eval_test.json` (not promoted) |

**Intrusion:** nothing measured yet.
- Event-level metrics: `python scripts/evaluate_intrusion.py --clips-dir $CLIPS --run-pipeline`, once `datasets/intrusion/labels.csv` lists the team's clips.
- Golden-clip regression: `tests/regression/test_golden_clips.py` via `pytest -m requires_weights`.
