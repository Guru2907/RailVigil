# Dataset plan (encroachment)

Owner: Gurpreet. Images and labels are **not** committed (`datasets/` is git-ignored); only `datasets/manifest.csv` and this guide are.

## Sources

| Source | Why | Licence notes |
|---|---|---|
| Own photos | Indian corridors, GPS on, known rights | Take them from platforms, overbridges or public roads — never by entering the track |
| Mapillary API | Street-level images with GPS near level crossings and roadside track | CC BY-SA; keep attribution |
| Wikimedia Commons | Often geotagged; categories for Indian railway lines and settlements along railways | Per-file licence; keep author and licence |
| Flickr API | Creative-Commons images with geotags | Use CC-licensed images only |
| RailSem19 | Rail and vegetation/building masks for the rail-track helper class | Research licence — check before use |
| TACO, Roboflow Universe | Litter and debris examples | Per-dataset licence |

**Reddit:** not used for training. Browser scraping breaks Reddit's user agreement, the data API terms forbid training AI models on user content without the rights-holders' permission, and Reddit strips GPS from images. At most a small set fetched through the official API may be used to *test* the model, with credit.

## Manifest
Every image gets one row in `datasets/manifest.csv`:
`image_id, file, source, source_url, licence, author, lat, lon, captured_at, location_source, split`

## Workflow (implemented)
The tools in [`training/`](../training/README.md) cover every step, run in order:
1. `add_images.py`: copy photos in, read GPS, record source and licence in the manifest.
2. `prelabel.py`: pretrained baseline + MobileSAM draw first-guess masks for upload.
3. Correct in Roboflow/CVAT, export as YOLO segmentation.
4. `import_labels.py`: bring the corrected export back. Uncorrected pre-labels are refused.
5. `build_dataset.py`: location-safe splits and the training folder.
6. `train.py`, `evaluate.py`, `promote.py`.

The step-by-step guide is in [training/README.md](../training/README.md).

## Labelling
- Tool: CVAT or Roboflow, polygon masks, classes from [ENCROACHMENT_SPEC.md](ENCROACHMENT_SPEC.md).
- Pre-label with YOLO-World / Open Images V7 + MobileSAM (`training/prelabel.py`), then correct by hand. Pre-labels are never ground truth.
- Also label "no encroachment" images (clean corridors, legitimate railway structures such as signal huts and relay rooms) as hard negatives.
- Target: about 300–500 instances per class to start.

## Splits
Split by **location**, not by image: images of the same site never appear in both training and test sets. Test set frozen once created.
