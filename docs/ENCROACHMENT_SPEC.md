# Physical encroachment module — specification

Owner: Gurpreet. Code: `backend/app/cv/encroachment/`. The first section describes what is implemented; the rest is the agreed design.

## Implemented — Phase 1 baseline (images, command line)
- **Run it:** `python scripts/run_image.py <image|folder> --zone "<points>"` from `backend/` (or a `<image>.zone.json` sidecar per image). Prints the findings and writes evidence — `annotated.jpg`, one crop per finding, `findings.json` — to `outputs/encroachment/<timestamp>/<image>/`.
- **Pipeline** (`pipeline.analyze_image`): load image with EXIF orientation applied → zone from `ZoneResolver` (manual / sidecar / camera; no zone = rejected) → detectors → `rules.classify_finding` per detection → evidence.
- **Zone:** only Z3, the right-of-way polygon given by the user. Z1/Z2 from detected rails are future work.
- **Object shape:** the mask outline when the model is a segmentation model (the trained `railvigil-seg`, selected with `ENC_MODELS=railvigil-seg`), otherwise the detection box as a polygon (the pretrained baseline). The rule is the same either way. Training and evaluation tools: [training/README.md](../training/README.md).
- **Detection cut-offs:** per model, `ENC_MODEL_MIN_CONFIDENCE` — 0.25 for Open Images, 0.10 for YOLO-World, whose open-vocabulary scores run lower (on a test frame a real tarpaulin shelter scored 0.20 and was missed by a shared 0.25 cut-off).
- **Rule** (`rules.py`): finding when `confidence ≥ ENC_MIN_CONFIDENCE` (floor 0.10) and `overlap_ratio ≥ ENC_MIN_OVERLAP` (0.2); `severity_score = ENC_CATEGORY_WEIGHT[class] × overlap_ratio`; bands critical ≥ 0.75, high ≥ 0.5, medium ≥ 0.25, else low; `vehicle_parked` capped at medium with the note "stationarity not verified"; findings below `ENC_LOW_CONFIDENCE_NOTE` (0.25) keep their severity but carry a "low detection confidence — verify" note (severity = how serious the object would be; confidence = how sure the model is). All values provisional (`core/config.py`).
- **Models** (`cv/common/model_registry.py`; weights git-ignored in `backend/models/`; every finding records `name@version`, version = first 12 hex of the file's SHA-256):

  | Name | File | Source | SHA-256 (first 12) |
  |---|---|---|---|
  | `oiv7-v8s` | `yolov8s-oiv7.pt` | Ultralytics release asset (Open Images V7, 601 classes) | `4663086e1b8e` |
  | `world-v8s-railvigil` | `yolov8s-world-railvigil.pt` | built from `yolov8s-worldv2.pt` (`9b2c17ab6124`) by `scripts/build_world_model.py` with `taxonomy.WORLD_MODEL_PROMPTS` (19 encroachment prompts + 6 distractors) | `533a607ff9f2` |

  Label mapping is in `taxonomy.py`; `Train` is deliberately unmapped. **Distractor prompts** (train, railway platform, platform shelter, railway signal, concrete kerb, person) give YOLO-World somewhere to put legitimate look-alikes; they map to no class. Boxes covering ≥ `ENC_MAX_BOX_SHARE` (80 %) of the image are dropped as not-an-object. Duplicate detections of the same class across models (box IoU ≥ `ENC_MERGE_IOU`, 0.5) are merged.
- **YOLO-World build:** setting text prompts needs OpenAI CLIP, which Ultralytics installs from GitHub into the venv and whose weights the script caches in `backend/models/clip/`. This is a one-time, developer-only step; the saved model carries the text embeddings, so the app needs neither CLIP nor a network connection. Rebuild when `WORLD_PROMPTS` changes.
- **Status:** baseline with pretrained models; **accuracy not measured**. Output is for officer review only.
- **Known limits seen on a 10-photo visual check** (2026-10-22; a check, not a measurement): garbage and debris are not detected at all (scores ≤ 0.03 even on heavily littered track); legitimate railway buildings such as station sheds are flagged as structures; bushes along a corridor were missed; most detections are low-confidence. The fine-tuned segmentation model was trained to address these; its measured results are in [EVALUATION.md](EVALUATION.md).

## Definition
A **potential encroachment** is an object of an encroachment category that lies on railway land or inside the track clearance. The software cannot decide legality — that needs land records — so every finding is reviewed by an officer. UI, reports and the paper say "potential encroachment" until an officer verifies it.

## Categories (detector classes)

| Class | Examples | Output |
|---|---|---|
| `structure_permanent` | pucca house, wall, shop building | segmentation mask |
| `structure_temporary` | hut/jhuggi, tin or tarpaulin shed, tent, stall | segmentation mask |
| `vegetation` | tree canopy over the track, bushes on the ballast or near OHE | segmentation mask |
| `debris_waste` | garbage heap, dumped waste, scrap | segmentation mask |
| `material_dump` | sand, bricks, construction material, stacked goods | segmentation mask |
| `vehicle_parked` | vehicle left standing on railway land | box + stationarity |
| `rail_track` (helper) | rails / track bed, used to place the zones | segmentation mask |

Masks rather than boxes because canopies and waste are irregular: a box would overstate the area on railway land.

## Zones
- **Z1 – track/fouling zone:** rail mask plus a clearance buffer. Highest severity.
- **Z2 – railway corridor:** a wider buffer on both sides of the track (configurable metres; right-of-way width varies, so this is a setting, not a fact).
- **Z3 – operator right-of-way polygon:** drawn by the user or saved per camera; overrides Z1/Z2 when the real boundary is known.

Scale: the two rails of broad gauge are 1676 mm apart, which converts pixels to approximate metres near the track. This is approximate under perspective and is reported as such. Without visible rails and without a drawn polygon a finding is `zone: unknown` and is never reported automatically.

## Decision rule (`classify_finding`, a pure function)
A finding is raised when `class ∈ ENCROACHMENT_CLASSES`, `confidence ≥ τ_c` and one of:
- mask ∩ Z1 ≥ a₁ → **critical**;
- mask ∩ (Z2 or Z3) ≥ a₂ % of the object, or distance to the nearest rail ≤ d m → **high / medium / low** from category weight and distance.

τ_c, a₁, a₂, d and the weights are configuration values marked provisional until validated (see [EVALUATION.md](EVALUATION.md)).

## Sites, reports and the API — implemented (Phase 2)
- **Upload:** `POST /api/media` — one or more photos plus the railway zone (`zone_points`, `zone_format` pixel/normalized, or `zone_sidecar`) and an optional map pin (`latitude`, `longitude`). The whole batch is checked before anything is stored; the same file uploaded again returns the existing photo (`duplicate: true`).
- **Location:** EXIF GPS → map pin → none. A photo **without a location is still analysed** and its findings stored, but it gets no site and no map point.
- **Sites:** a finding joins the nearest site of the same class within `ENC_SITE_RADIUS_M` (25 m, provisional; PostGIS `ST_DWithin` with a spatial index), otherwise starts a new one.
- **Review workflow** (`PATCH /api/encroachment/sites/{id}`): `reported → under_review → verified → action_taken → resolved`, or `→ false_positive`; invalid moves return 409; every change is in the site history. A **resolved** site found again is reopened as re-encroached; a **false_positive** site is not.
- **Reports** (`RV-ENC-YYYY-NNNNNN`), **at most one per site per photo** (a photo of five huts at one spot is one event):
  - `new_site` — a finding started a new site;
  - `re_encroached` — a resolved site was found again;
  - `critical_finding` — an existing site's worst severity just became critical, or (once per photo) a photo without a location has a critical finding.
- **Map:** `GET /api/map/features` returns sites as GeoJSON (`[longitude, latitude]`), filterable by area, class, severity, status and date.
- **Not yet:** source metadata and camera locations as location sources (Phase 3+), photos from video keyframes (future work).

## Video
Encroachment is static, so video is sampled into keyframes and processed like images; the same object across frames is de-duplicated by mask overlap.

## Models
1. Baseline without training: YOLOv8 Open Images V7 weights and YOLO-World prompts — labelled "baseline" wherever shown.
2. Fine-tuned YOLOv8-seg on the categories above (see [DATASET.md](DATASET.md)). Every finding stores the model name and version.

## Evidence stored per finding
Original image, annotated image, cropped evidence, class, confidence, mask, zone hit, overlap area, distance to rail, severity, model version, location and source, timestamps, report number.
