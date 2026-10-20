# Physical encroachment module — specification

Owner: Gurpreet. Code: `backend/app/cv/encroachment/` (in development). Everything below is the agreed design; sections move from *planned* to *implemented* as code lands.

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

## Sites and persistence
Each finding gets a location (EXIF GPS → source metadata → map pin → camera location; otherwise "location unknown", listed but not mapped). Findings of compatible categories within R metres are grouped into one **encroachment site** (PostGIS). Site lifecycle: `reported → under_review → verified → action_taken → resolved`, or `false_positive`; a new finding at a resolved site reopens it as re-encroached. Repeat reports over time are the evidence of persistence.

## Video
Encroachment is static, so video is sampled into keyframes and processed like images; the same object across frames is de-duplicated by mask overlap.

## Models
1. Baseline without training: YOLOv8 Open Images V7 weights and YOLO-World prompts — labelled "baseline" wherever shown.
2. Fine-tuned YOLOv8-seg on the categories above (see [DATASET.md](DATASET.md)). Every finding stores the model name and version.

## Evidence stored per finding
Original image, annotated image, cropped evidence, class, confidence, mask, zone hit, overlap area, distance to rail, severity, model version, location and source, timestamps, report number.
