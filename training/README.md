# Training the RailVigil encroachment model

This guide goes from your own photos to a trained **YOLOv8s-seg** model that the backend uses. Every number you report comes from a frozen test set.

All commands run from the **repo root** (`E:\Dev\RailVigil`) in PowerShell. `T` below means the training Python:

```powershell
$T = "training\.venv\Scripts\python.exe"     # GPU environment (training, pre-labelling)
$B = "backend\.venv\Scripts\python.exe"      # backend environment (baseline evaluation)
```

## 0. One-time setup

```powershell
powershell -ExecutionPolicy Bypass -File training\setup_training.ps1
```

This creates `training\.venv` with the CUDA build of PyTorch (about a 3 GB download), separate from the backend. The last line must print your GPU, e.g. `GPU: NVIDIA GeForce RTX 3050 Laptop GPU`.

The pre-labelling step also needs the baseline weights in `backend\models\` (`yolov8s-oiv7.pt`, `yolov8s-world-railvigil.pt`); see `docs/ENCROACHMENT_SPEC.md`.

## 1. Collect photos

Put each batch in its own folder under `datasets\incoming\` (git-ignored). Keep the licence of every photo.

| Source | How | Licence to record |
|---|---|---|
| **Your own** (best) | Phone camera with **location on**. Take them from platforms, foot-over-bridges, level crossings or public roads, **never on the track**. | `own` |
| Wikimedia Commons | Search e.g. "railway track India slum", "railway line encroachment". | The file's licence, e.g. `CC BY-SA 4.0` |
| Mapillary | Street-level images near tracks (CC BY-SA). | `CC BY-SA 4.0` |
| Flickr | Only photos with a Creative Commons licence. | The CC licence shown |
| TACO / Roboflow Universe | Extra garbage and debris examples. | The dataset's licence |

**Also collect "clean" photos.** These show empty track and **legitimate railway structures** (signal cabins, relay huts, station sheds, platforms). They teach the model what *not* to flag.

**Do not use Reddit.** Its terms forbid using its content to train AI.

For internet photos, put a `credits.csv` in the batch folder:

```csv
filename,source_url,author,licence
img001.jpg,https://commons.wikimedia.org/wiki/File:...,Jane Doe,CC BY-SA 4.0
```

### Automatic collectors (India only)

```powershell
& $T training\collect_mapillary.py --per-city 50   # street-level photos near tracks, 6 metros (needs MAPILLARY_TOKEN in training\.env)
& $T training\collect_commons.py --limit 100       # freely licensed Wikimedia Commons photos
& $T training\import_taco.py --limit 400           # TACO litter outlines -> debris_waste, TRAIN ONLY
& $T training\remove_images.py <id> <id> --reason "no track visible"   # drop irrelevant photos after a look
```

- **Mapillary:** only photos taken on an OpenStreetMap railway line (within 8 m: from a train or at a level crossing), not on a road or foot bridge, at least 100 m apart. Photos from roads beside the track rarely show it. Licence CC BY-SA 4.0; the photographer is recorded.
- **Commons:** only free licences (never NC or ND). Photos must be inside India by coordinates, or carry Indian place names and no foreign ones.
- **TACO** is not Indian, so its photos are marked `train_only`. They never reach val or test, so every reported number is measured on Indian photos only.
- Run the collectors **one at a time**: each rewrites `datasets\manifest.csv`.
- `MAPILLARY_TOKEN` lives in `training\.env` (git-ignored). Use a READ-only client token, and never commit or share it.

## 2. Add your own photos to the dataset

```powershell
& $T training\add_images.py datasets\incoming\own_kalyan --source own --licence own --author "Gurpreet"
& $T training\add_images.py datasets\incoming\commons01 --source wikimedia --credits credits.csv
```

Each photo is copied to `datasets\images\<id>.jpg`. Its GPS and capture time are read, and a row is added to `datasets\manifest.csv`. Re-running is safe, because duplicates are skipped. Photos without a licence are refused.

If several photos show **the same place** but have no GPS, add `--group "kalyan-km42"`. That keeps them all in the same split.

## 3. Pre-label (the computer draws first guesses)

```powershell
& $T training\prelabel.py --name batch01
```

This writes `datasets\upload\batch01\`: images, labels and a `data.yaml`.
- Each guess comes from the pretrained models, and MobileSAM turns it into an outline. MobileSAM is a ~40 MB download the first time.
- The guesses have the baseline's known mistakes: missed garbage and bushes, rickshaws labelled as stalls, station sheds flagged. **Treat them as a starting point only.**

## 4. Correct the labels (the main human work)

**Roboflow (easiest, free tier):**
1. Create a project of type **Instance Segmentation** with the six classes, named **exactly** as below:
   - `structure_permanent`
   - `structure_temporary`
   - `vegetation`
   - `debris_waste`
   - `material_dump`
   - `vehicle_parked`
2. Upload the whole `datasets\upload\batch01` folder. Roboflow reads the labels.
3. Check **every** photo: fix outlines and classes, delete wrong objects, and **draw what was missed**.
4. Export with **Generate → Export → format "YOLOv8"** (segmentation), as a zip. Unzip it anywhere.

**CVAT** works too: import "Ultralytics YOLO Segmentation 1.0", then export in the same format.

**Labelling rules:**
- Outline only the parts of objects that are actually visible.
- `vehicle_parked`: only vehicles that look parked or abandoned, not ones driving past.
- **Do not label legitimate railway buildings.** Leave them unlabelled; that is how the model learns they're fine.
- Trains and people are **not** encroachment classes; leave them unlabelled.
- A photo with nothing to label is fine. Keep it: it becomes a "clean" example.

## 5. Import the corrected labels

```powershell
& $T training\import_labels.py C:\path\to\unzipped-export
```

This **refuses** the `datasets\upload\...` folder itself. Uncorrected guesses must never become ground truth, or the evaluation would measure the baseline against its own guesses.

## 6. Build the dataset (train / val / test)

```powershell
& $T training\build_dataset.py
```

- The split is 70/15/15 **by place**: photos within 300 m of each other, or with the same `--group`, always land in the same split.
- **Existing splits never change**, so the test set stays frozen as you add photos.
- It prints the object counts per class. Aim for about **300+ per class** in train.

## 7. Train (on the GPU)

```powershell
& $T training\train.py --name smoke --epochs 3     # quick check (~1 min)
& $T training\train.py --name seg-v1               # real run: 100 epochs, stops early if no progress
```

- On the RTX 3050 (4 GB), use `--batch 4` if you see "CUDA out of memory".
- Expect roughly 1–4 hours for ~1000 photos.
- Results go to `training\runs\seg-v1\`: curves, a confusion matrix, `weights\best.pt`, and `railvigil_run.json`, which records the git commit, a fingerprint of the dataset and the settings.

## 8. Evaluate on the frozen test split

```powershell
& $T training\evaluate.py --name seg-v1           # trained model: mask + box metrics per class
& $B backend\scripts\evaluate_baseline.py         # pretrained baseline on the same photos (box AP50)
```

Both print Markdown tables.
- Compare the trained model's **mAP50 (box)** column with the baseline's **AP50 (box)**.
- These are the only numbers that may go in the paper, the README or the UI.
- Add them to the results log in `docs/EVALUATION.md`.

## 9. Use the model in the app

```powershell
& $T training\promote.py --name seg-v1
```

This copies `best.pt` to `backend\models\railvigil-seg.pt` and prints a results-log row. Then add this line to `backend\.env` and restart the backend:

```
ENC_MODELS=railvigil-seg
```

With the trained model:
- The pipeline measures overlap with the railway land using the **mask outline** instead of the box.
- The annotated images show outlines.

To go back to the baseline, remove the line.

## Throwaway test runs

Point the tools at another folder so the real dataset is never touched:

```powershell
$env:RAILVIGIL_DATASETS = "C:\temp\rv-smoke\datasets"; $env:RAILVIGIL_RUNS = "C:\temp\rv-smoke\runs"
```

`import_labels.py --allow-prelabels` accepts uncorrected pre-labels **for such smoke tests only**.
