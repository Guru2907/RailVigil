# Evaluation

**Rule:** no accuracy, precision, recall, speed or dataset-size figure appears in the README, UI, reports or paper unless it was produced by the evaluation script on a frozen test set and can be reproduced. Measured figures: the **2026-10-24 encroachment results**, and the **2026-11-26 results** (blind test set, intrusion) below. The 2026-11-26 results supersede the earlier test numbers; read the section on answer keys before quoting either.

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
First logged run: 2026-11-26 (see "Intrusion results" below). It supports **`CONFIRM_DWELL_SEC` = 1.0** over the current 0.6 (same recall, fewer extra alerts); the default is not changed in this PR. The other defaults in `backend/app/core/config.py` remain **candidates**. Do not change comments to "validated" until a row is added below with reproducible metrics. Paper draft "3 s" confirmation is **not** adopted until measured recall/precision support it.

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

## Results 2026-11-26: blind test set, ablations, intrusion

Code at `main` 299d55e plus `training/evaluate_test.py` (added with these results). Raw numbers: `docs/results/`.

### What changed since 2026-10-24
- **Dataset:** 561 photos (India + 13 other countries), labels cleaned, 6 classes (`debris_waste` folded into `material_dump`). Train 412 (including 100 TACO litter photos, train only), val 75, test 66.
- **Test answer key:** the 66 test photos (the 39 original ones plus 27 new; 42 Indian, 24 from other countries) were labelled **from scratch, without any model's pre-labels**, by labeller A (`datasets/labels_test/A`). A second labeller (B) independently labelled a random 20 of them (`random.Random(2026)`: 13 Indian + 7 other) to measure agreement.
- **Models declared before the test set was scored:** the pretrained ensemble (`baseline`, as the app runs it), `railvigil-s` (previous fine-tuned model), `v2-s-f10` (main pick on validation), `v2-m-f10` (YOLOv8m, best overall on validation).

### Human agreement (20 photos, A vs B)
| Class | A | B | Matched (IoU ≥ 0.5) | Box agreement | Kappa (present/absent) |
|---|---|---|---|---|---|
| structure_permanent | 10 | 10 | 5 | 0.50 | 0.37 |
| structure_temporary | 4 | 7 | 2 | 0.36 | 0.69 |
| vegetation | 13 | 19 | 9 | 0.56 | 0.62 |
| vehicle_parked | 3 | 4 | 1 | 0.29 | 0.77 |
| all | 30 | 41 | 17 | **0.48** | |

- Railway zone: mean IoU **0.72**.
- Ignoring the class, agreement rises only to 0.54; at IoU ≥ 0.3 it is 0.62. The disagreement is mostly about *what* counts as an object (B marked 37 % more) and box extent, not about the class.
- **This is the ceiling on this key:** two careful people match on about half the objects.
- File: `results/label_agreement_v2.md`.

### The answer key decides the gap (same 39 photos, same 4 classes)
| Answer key | Objects | Baseline | `railvigil-s` | Difference |
|---|---|---|---|---|
| Old: made by correcting the baseline's pre-labels | 139 | 0.792 [0.688, 0.905] | 0.378 [0.301, 0.472] | −0.415 [−0.531, −0.304] |
| Blind: labeller A from scratch | 62 | 0.236 [0.102, 0.349] | 0.181 [0.056, 0.265] | −0.054 [−0.161, 0.000] |

Box AP50 with 95 % paired bootstrap intervals (1000 resamples). The old key reproduces the 2026-10-24 gap exactly; on the blind key **almost all of it disappears**. The old key was anchored on the baseline's own detections (it has more than twice the objects), so the 2026-10-24 baseline figure overstated the baseline. File: `results/test_eval_v2_same39.json`.

### Blind test: all 66 photos
Box AP50, mean over structure_permanent (23 objects), structure_temporary (12), vegetation (52), vehicle_parked (11); `material_dump` has 1 test object and is left out. 95 % intervals from 1000 paired resamples.

| Model | All (66) | India (42) | Other countries (24) |
|---|---|---|---|
| Pretrained ensemble (baseline) | 0.167 [0.084, 0.259] | 0.223 [0.085, 0.347] | 0.115 [0.049, 0.222] |
| `railvigil-s` (previous) | 0.117 [0.053, 0.217] | 0.164 [0.043, 0.254] | 0.097 [0.037, 0.264] |
| `v2-s-f10` | 0.068 [0.039, 0.173] | 0.111 [0.056, 0.303] | 0.059 [0.022, 0.187] |
| `v2-m-f10` | 0.166 [0.089, 0.322] | 0.159 [0.080, 0.341] | 0.248 [0.105, 0.506] |

| Paired difference | Value | 95 % interval |
|---|---|---|
| `v2-m-f10` − baseline, all photos | −0.002 | [−0.078, 0.154] |
| `v2-m-f10` − baseline, other countries | +0.134 | [−0.014, 0.337] |
| `v2-m-f10` − baseline, India | −0.064 | [−0.130, 0.179] |
| `v2-m-f10` − `v2-s-f10`, all photos | +0.097 | [0.029, 0.192] |
| `railvigil-s` − baseline, all photos | −0.050 | [−0.107, 0.018] |

Per class (all photos):

| Model | structure_permanent | structure_temporary | vegetation | vehicle_parked |
|---|---|---|---|---|
| baseline | 0.065 | **0.001** | **0.298** | **0.305** |
| `railvigil-s` | 0.018 | 0.051 | 0.206 | 0.193 |
| `v2-s-f10` | 0.018 | 0.041 | 0.154 | 0.059 |
| `v2-m-f10` | 0.059 | **0.160** | 0.237 | 0.206 |

Ultralytics mask mAP50 on the same key (all photos): `railvigil-s` 0.086, `v2-s-f10` 0.069, `v2-m-f10` 0.151. Files: `results/test_eval_v2.{md,json}`.

Per-class paired differences for `v2-m-f10` (box AP50, 1000 paired resamples, seed 0):

| Class | vs baseline | vs `railvigil-s` |
|---|---|---|
| structure_temporary | **+0.159 [+0.006, +0.500]** (98 % of resamples above 0) | +0.110 [−0.002, +0.326] (96 %) |
| structure_permanent | −0.005 [−0.090, +0.086] | +0.041 [−0.026, +0.138] |
| vegetation | −0.061 [−0.158, +0.032] | +0.030 [−0.058, +0.106] |
| vehicle_parked | −0.099 [−0.357, +0.428] | +0.013 [−0.327, +0.635] |

Temporary structures (shacks, huts, stalls) are the only class where a difference clears zero: the fine-tuned model finds them and the pretrained ensemble does not. With 8 comparisons, read it as strong evidence rather than proof; 12 test objects is few.

### Seeds and ablations on the test set (reported, not used to choose)
| `v2-s-f10` variant | All | India | Other countries |
|---|---|---|---|
| seed 0 (declared main pick) | 0.068 | 0.111 | 0.059 |
| seed 1 | 0.124 | 0.181 | 0.076 |
| seed 2 | 0.119 | 0.168 | 0.121 |
| without foreign photos | 0.121 | 0.126 | 0.119 |
| without TACO | 0.088 | 0.128 | 0.116 |

Validation tables: `results/val_models_v2.md`, `results/val_ablations_v2.md`. Test: `results/test_eval_v2_ablations.{md,json}`.

### Reading the numbers
- **No fine-tuned model beats the pretrained ensemble overall** on the blind key. `v2-m-f10` ties it (−0.002) and is ahead on photos from other countries (+0.134, interval just touching 0). The declared main pick `v2-s-f10` is the weakest model on test.
- **The two are complementary by class.** Only fine-tuning detects temporary structures (0.160 vs 0.001: the pretrained vocabularies have no "shack"). The pretrained models are better on vegetation and parked vehicles, classes they already know from millions of images.
- **Run-to-run noise is as large as most differences.** Three seeds of the same configuration span 0.068–0.124 on test. Removing the foreign photos or TACO stays inside that spread: neither has a measurable effect here.
- **Validation over-predicted test** (mask mAP50 about 0.25 on val vs 0.07–0.15 on test). Val labels are corrected pre-labels; the test key is from scratch and sparser. Choosing `v2-s-f10` on val did not carry over; `v2-m-f10` did.
- **Absolute numbers are low partly because the task is ambiguous:** human box agreement is 0.48.
- **Limits:** one labeller for the full key; 66 photos (11–52 objects per class); `material_dump` cannot be measured (1 object).
- **App default unchanged:** `ENC_MODELS` stays the pretrained ensemble. A hybrid (pretrained for vegetation and vehicles, `v2-m-f10` for structures) is the obvious next step, but it must be chosen on validation, not on these test numbers.

### Per-class hybrid chosen on validation (declared before scoring)
Rule fixed in advance: candidates = baseline and `v2-m-f10`; each class goes to the candidate with the higher validation AP50; the hybrid is scored on the test key once (`training/evaluate_test.py hybrid`).

| Class | Baseline, val | `v2-m-f10`, val | Chosen | Baseline, blind test | `v2-m-f10`, blind test |
|---|---|---|---|---|---|
| structure_permanent | 0.543 | 0.133 | baseline | 0.065 | 0.059 |
| structure_temporary | 0.651 | 0.225 | baseline | **0.001** | **0.160** |
| vegetation | 0.974 | 0.600 | baseline | 0.298 | 0.237 |
| vehicle_parked | 0.804 | 0.436 | baseline | 0.305 | 0.206 |

- **Validation chose the baseline for every class, so the hybrid is the baseline** (test 0.167, difference 0.000).
- The reason is the validation key: like the old test key, it was made by correcting pre-labels, so it favours the baseline. On validation the baseline scores 0.651 on temporary structures; on the blind test key it scores 0.001. This is a second, independent sign of the anchoring found above.
- A fair per-class choice needs a validation key labelled from scratch. Files: `results/val_eval_v2_hybrid_routing.{md,json}`, `results/test_eval_v2_hybrid.{md,json}`.

### Intrusion results
15 clips, 13 labelled intrusions (5 crossing traffic, 8 people on the track), 372 s of scored video (`ignore` ranges removed); labels and zones in `datasets/intrusion/`. Default pipeline except `CONFIRM_DWELL_SEC`; RTX 3050 (a CPU run gave identical counts). File: `results/intrusion_sweep_v2.json`.

| `confirm_dwell` | Caught | Extra alerts on a real intrusion | Alerts on nothing | Precision (strict) | Time to alert |
|---|---|---|---|---|---|
| 0.3 s | 13/13 | 20 | 2 | 0.37 | 0.79 s |
| 0.6 s (default) | 13/13 | 17 | 1 | 0.42 | 1.16 s |
| **1.0 s** | **13/13** | **12** | **1** | **0.50** | **1.75 s** |
| 1.5 s | 11/13 | 10 | 1 | 0.50 | 2.32 s |
| 2.0 s | 10/13 | 10 | 1 | 0.48 | 2.84 s |

- "Extra alerts on a real intrusion" (`fp_duplicate`) overlap a labelled intrusion of the same class: the same person alerted again, or another member of a crowd labelled as one row (most are the Malavli crowd). Strict precision counts them as false.
- At most 2 alerts in 372 s were on nothing (about 10–20 per hour).
- **1.0 s** keeps every intrusion and cuts extra alerts by 30 %; from 1.5 s, short intrusions are missed.
- Small set (13 intrusions, about 6 minutes of video): indicative, not definitive.

### Reproduce
```
training/train.py --name v2-s-f10 --base yolov8s-seg.pt --freeze 10 --batch 4 --imgsz 640 --epochs 150 --patience 50 [--seed N] [--exclude foreign|taco]
training/import_labels.py <export> --labels-dir datasets/labels_test/A        # and B
training/label_agreement.py datasets/labels_test/A datasets/labels_test/B
training/evaluate_test.py predict --model <run> --labels datasets/labels_test/A      # training venv (GPU)
training/evaluate_test.py predict --model baseline --labels datasets/labels_test/A   # backend venv
training/evaluate_test.py score --labels datasets/labels_test/A --models baseline railvigil-s v2-s-f10 v2-m-f10 --report docs/results/test_eval_v2
backend/scripts/evaluate_intrusion.py --clips-dir ../datasets/intrusion/clips --run-pipeline --sweep confirm_dwell 0.3,0.6,1.0,1.5,2.0
```

## Results log
| Date | Module | Model / config | Test set | Metrics | Run |
|---|---|---|---|---|---|
| 2026-10-24 | Encroachment | Baseline: `oiv7-v8s@4663086e1b8e` + `world-v8s-railvigil@533a607ff9f2` | 39 Indian test photos, dataset `d7297135357c1df5` | box AP50 0.634 (mean of classes with test objects) | `training/runs/baseline_eval_test.json` |
| 2026-10-24 | Encroachment | `railvigil-s` (YOLOv8s-seg, freeze 10, best epoch 76), weights `9b43e1832858` | same | box mAP50 0.309; mask mAP50 0.291, mAP50–95 0.145, P 0.607, R 0.279 | `training/runs/railvigil-s/eval_test.json` (not promoted) |
| 2026-11-26 | Encroachment | baseline, `railvigil-s`, `v2-s-f10`, `v2-m-f10` | 66 test photos, blind key A | box AP50 0.167 / 0.117 / 0.068 / 0.166 (4 classes; bootstrap intervals in the file) | `docs/results/test_eval_v2.json` |
| 2026-11-26 | Encroachment | same models, old key vs blind key | the 39 original test photos | gap baseline − `railvigil-s`: 0.415 (old key) vs 0.054 (blind key) | `docs/results/test_eval_v2_same39.json` |
| 2026-11-26 | Intrusion | default pipeline, `confirm_dwell` sweep | 15 clips, 13 intrusions, 372 s | dwell 1.0 s: 13/13 caught, 1 alert on nothing, time to alert 1.75 s | `docs/results/intrusion_sweep_v2.json` |

**Intrusion:** first measured run 2026-11-26 (above).
- Golden-clip regression: `tests/regression/test_golden_clips.py` via `pytest -m requires_weights`.
