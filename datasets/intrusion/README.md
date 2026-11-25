# Intrusion evaluation: clips, zones and labels

This folder holds the answer key for measuring the intrusion module: **which clips show a person, vehicle or animal inside the track zone, and from when to when.** With it, `backend/scripts/evaluate_intrusion.py` reports event precision, recall, false alerts per hour and confirmation delay. These are the first real intrusion numbers for the paper.

| File | In git? | What |
|---|---|---|
| `clips.csv` | yes | the 17 clips: source, licence, author, duration, size, and a guess (`intrusion_hint`) |
| `labels.csv` | yes | **you fill this**: one row per intrusion, plus one whole-clip row per clip |
| `clips/` | **no** (videos) | the clips, plus `<clip>.zone.json` zone files you draw |
| `frames/` | no | one sheet per clip: 16 frames stamped with their time |

## 0. Get set up (once)

1. `git pull` on `main`. The tools are in `training/draw_zone.py` and `training/clip_frames.py`.
2. Get **`intrusion_clips_for_labelling.zip`** from Gurpreet (about 340 MB; the videos are not in git). Unzip it into this folder so you have:
   ```
   datasets/intrusion/clips/*.mp4 | *.webm | *.ogv   (17 clips; 3 already have a .zone.json)
   datasets/intrusion/frames/*.jpg                   (17 frame sheets)
   ```
3. Use the backend Python (it has OpenCV): `backend\.venv\Scripts\python.exe`, written `$B` below. From the repo root:
   ```powershell
   $B = "backend\.venv\Scripts\python.exe"
   ```
4. The YOLO weights `backend/models/yolov8n.pt` must be present (they are on the machine that runs the app).

## 1. Draw a track zone for each clip (about 15 min)

The pipeline only counts something as an intrusion **inside the zone**, so every clip needs one. The 3 `showcase_*` clips with a `.zone.json` already have one; check them and redraw if wrong.

```powershell
& $B training\draw_zone.py datasets\intrusion\clips --missing      # the 14 without a zone
& $B training\draw_zone.py datasets\intrusion\clips\pixabay_3178.mp4 --at 5   # redo one, frame at 5 s
```

A window opens with one frame. **Left-click around the danger area**: the track (rails and sleepers) plus about a metre either side; at a level crossing, the part of the road between the barriers. Then:
- **Enter** saves `<clip>.zone.json` and opens the next clip;
- **u** undoes a point, **r** starts again, **n** skips, **q** quits.

Rules:
- Draw the zone where the track is **in that clip**. If the camera moves a little, draw it for the first seconds.
- Do not include platforms, roads beside the track or the barrier arms themselves.
- If the camera moves a lot (filmed from a moving train), skip the clip (**n**) and add `camera moves` in its notes later.

## 2. Watch each clip and write `labels.csv` (about 45 min)

Open the frame sheet `frames/<clip>.jpg` to see roughly when things happen, then play the clip (VLC shows the time; **E** steps one frame). For each clip write:

**a) One whole-clip row** (always, even if there are intrusions): it tells the script how long the clip is, for the false-alerts-per-hour figure.
```
<clip>,0,<duration_sec from clips.csv>,*,0,whole clip
```

**b) One row per intrusion**: each separate person, vehicle or animal that **enters the zone**.
```
<clip>,<start_sec>,<end_sec>,<class>,1,<what happens>
```
- `start_sec` = the moment it is first **inside** the zone; `end_sec` = when it has left (or the clip ends). One decimal is enough.
- `class` = the YOLO name of what it is: `person`, `bicycle`, `car`, `motorcycle`, `bus`, `truck`, `cow`, `dog`, `horse`, `sheep`, `elephant`. Use `*` if unsure.
- A group walking together across the track = **one row per person** if you can tell them apart; a crowd that you cannot count = one row with `person` and the note `crowd`.
- Someone **near** the track but never inside the zone is **not** an intrusion: no row (the whole-clip row covers it).
- A train passing through the zone is **not** an intrusion.

Example, using two of our clips:
```csv
clip,start_sec,end_sec,class,is_intrusion,notes
pixabay_3178,0,12,*,0,whole clip
pixabay_3178,0.0,9.5,person,1,passengers crossing tracks between trains
pixabay_48588,0,15,*,0,whole clip
```
Use the **file name without the extension** in `clip`. Keep `notes` short and without commas.

### The 17 clips

| Clip | Length (s) | Likely content |
|---|---|---|
| `commons_20110525Bahnuebergang_Heuweg` | 34.4 | level crossing, train passes, probably no intrusion |
| `commons_Caltrain_locomotive_905_passing_by_San_Mateo_gk` | 18.5 | train passes a crossing |
| `commons_FR_17_Saint_Vaize__Passage_niveau_de_la_Borderie` | 55 | train passes a French crossing |
| `commons_Luebben_Trains_01_webmhd` | 56.2 | trains and a car at a crossing (car waits: no intrusion unless it enters) |
| `pixabay_385824` | 26 | rural level crossing, cars crossing |
| `pixabay_384221` | 24 | cars crossing a level crossing |
| `pixabay_3178` | 12 | **people crossing tracks** at an Indian station |
| `pixabay_132311` | 41 | cyclist on a path **beside** the track (not in the zone) |
| `pixabay_48588` | 15 | Japanese level crossing, train passes |
| `pixabay_218495` | 11 | train approaching, empty track |
| `pixabay_18905` | 31 | freight train passing |
| `pixabay_4346` | 13 | empty track, train in the distance |
| `showcase_rescue_vangani` | 73.2 | **child on the track, railway worker runs across** (several replays in the clip) |
| `showcase_shivamogga` | 26.6 | train passing only |
| `showcase_ludhiana` | 197.1 | station platform; **people step down onto the track** |
| `showcase_malavli_crossing` | 41.5 | **people crossing near a moving train** (stock footage: numbers only, never shown) |
| `showcase_man_on_tracks` | 9.1 | **man walking on the tracks** (stock footage: numbers only, never shown) |

## 3. Run the evaluation

From `backend/`:
```powershell
.venv\Scripts\python.exe scripts\evaluate_intrusion.py --clips-dir ..\datasets\intrusion\clips --run-pipeline
.venv\Scripts\python.exe scripts\evaluate_intrusion.py --clips-dir ..\datasets\intrusion\clips --run-pipeline --sweep confirm_dwell 0.3,0.6,1.0,2.0
```
The first prints precision, recall, false alerts per hour and mean confirmation delay; the second repeats it for several confirmation times (CPU: a few minutes per run). Save both outputs and share them, along with `labels.csv` and the zone files, in a PR (only `labels.csv` is committed; zip the `.zone.json` files for Gurpreet).

## Rules
- **Only label clips that are in `clips/`**; times must come from watching the clip. No placeholder rows.
- Negatives matter as much as positives: train-only clips and the cyclist beside the track check that the system does **not** raise alerts.
- Stock clips (`showcase_malavli_crossing`, `showcase_man_on_tracks`) have no clear licence: use them for numbers only, never in figures or slides.

See also `docs/EVALUATION.md` (intrusion section) and issue #3 part B.
