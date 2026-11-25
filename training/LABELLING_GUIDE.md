# Labelling guide (Roboflow)

Three jobs. Do them in this order; each one ends with sending the export back, then a command.

| Job | Who | Photos | Starting point | Time (rough) |
|---|---|---|---|---|
| 1. Correct the new train/val photos | you | 217 | machine guesses to fix | 2–4 h |
| 2. Label the test photos **blind** | you **and** one teammate, **separately** | 66 each | empty: nothing drawn | 1.5–2.5 h each |
| 3. Mark intrusions in the clips | you or Siddeshwar | 17 clips | frame sheets | 1 h |

`$T` below is the training Python: `$T = "training\.venv\Scripts\python.exe"` (run from the repo root).

## Classes (type them **exactly**; Roboflow keeps the spelling)

| Class | Draw it on |
|---|---|
| `structure_permanent` | brick/concrete houses, walls, shops built on or against railway land |
| `structure_temporary` | huts, shacks, tarpaulin or tin shelters, stalls, tents |
| `vegetation` | bushes, overgrowth, crops on the track bed or right beside it (not distant trees) |
| `material_dump` | garbage, litter piles and scrap, **and** heaps of sand, bricks, gravel, construction leftovers (waste is labelled here too; `debris_waste` is not used) |
| `vehicle_parked` | vehicles that look parked or abandoned (not ones driving past) |
| `railway_zone` | **test photos only (job 2):** ONE polygon around the railway land |

Do **not** label: trains, people, legitimate railway buildings (stations, signal cabins, platforms, relay huts). A photo with nothing to label is fine; leave it empty, it becomes a "clean" example.

---

## Job 1 · Correct the new train/val photos (you)

Folder to upload: `datasets\upload\new_trainval` (images + machine guesses + `data.yaml`).

1. **roboflow.com → sign in → your workspace → "New Project".**
   - Project type: **Instance Segmentation**.
   - Name: `railvigil-trainval-2026`. "What are you detecting": `encroachment`.
2. **Upload:** open the project → **Upload Data** → drag in the **whole `new_trainval` folder** (not just `images`).
   - Roboflow shows the photos with outlines already drawn. If it asks about the format, it is **YOLOv8 / YOLO segmentation**.
   - Click **Save and Continue**. When asked how to split, choose **"Use existing values"** or put everything in **Train**. The split does not matter; we keep our own.
3. **Annotate:** go to **Annotate**, open the batch, assign it to yourself, and start. For **each** photo:
   - wrong class → click the shape and change the class;
   - wrong object (a station shed, a train) → select it and press **Delete**;
   - outline badly off → drag its points, or delete and redraw;
   - **missed object** (garbage and bushes are often missed): press **P** (Polygon) and click around it, Enter to finish; or use **Smart Polygon** (the magic-wand icon), one click on the object.
   - Then the right arrow to the next photo. Changes save on their own.
4. **Export:** **Versions → Generate New Version → Continue → Generate** (no preprocessing or augmentation is needed, so untick anything ticked) → **Download Dataset** → format **COCO Segmentation** → **Download zip to computer**.
5. Unzip it anywhere and send me the folder path, or run:
   ```powershell
   & $T training\import_labels.py C:\path\to\unzipped-export
   ```

---

## Job 2 · Label the test photos blind (you AND a teammate, separately)

File to upload: `datasets\upload\test_blind\test_blind.zip` (66 photos, **no** guesses drawn). Send the same zip to your teammate.

**Rule:** do not look at each other's labels until both are exported. The point is two independent answer keys.

1. Each person makes **their own** project: **Instance Segmentation**, named `railvigil-test-A` (you) and `railvigil-test-B` (teammate).
2. **Upload** the zip → **Save and Continue** (everything in Train is fine).
3. **Add the 6 classes** (Classes & Tags → Add Class, or type the name the first time you draw), spelled exactly as in the table above, including `railway_zone`. Both labellers must use the same 6 names.
4. **Annotate** each photo:
   - **objects:** press **B** (Bounding Box) and drag a box. A box is enough on the test set; outlines are not needed.
   - **railway_zone:** press **P** (Polygon) and click around the railway land: the track bed and the land beside it up to the fence, wall, drain or the edge of the railway strip. Enter to finish. **One per photo.** If you cannot tell where railway land ends, follow the ballast and a few metres beyond it.
5. **Export** exactly as in job 1 (**COCO Segmentation**, zip), and send me the paths, or run:
   ```powershell
   & $T training\import_labels.py C:\path\to\export-A --labels-dir datasets\labels_test\A
   & $T training\import_labels.py C:\path\to\export-B --labels-dir datasets\labels_test\B
   & $T training\label_agreement.py datasets\labels_test\A datasets\labels_test\B
   ```
   The last command prints how closely the two of you agreed (a table for the paper).

---

## Job 3 · Mark intrusions in the clips

Clips: `datasets\intrusion\clips\`. Frame sheets with timestamps: `datasets\intrusion\frames\` (one image per clip; make them with `& $T training\clip_frames.py`).

For each clip, add rows to `datasets\intrusion\labels.csv`:

```csv
clip,start_sec,end_sec,class,is_intrusion,notes
pixabay_3178,2.0,9.5,person,1,people crossing the tracks at the station
pixabay_48588,0.0,14.8,train,0,train only: no intrusion
```

- `clip` = the file name without extension.
- One row per intrusion (a person, vehicle or animal inside the track zone). Read the rough times off the frame sheet, then check them in a video player.
- Clips with no intrusion get one row with `is_intrusion` = 0 (the whole clip).
- Follow `datasets\intrusion\README.md`. Siddeshwar owns the intrusion module, so ask him to check the rows.

---

## If something goes wrong

- **"Unknown class names in the export"** → a class is misspelled in Roboflow. Rename it there (Classes tab) and export again.
- **Export is "YOLOv8" but the outlines turned into boxes** → that export is under "Convert to Object Detection". Use **COCO Segmentation** instead.
- **The import says photos are "not in the manifest"** → Roboflow renamed the files. Our id is the first 12 characters of the name, which Roboflow keeps; tell me the warning and I will match them.
- **Roboflow's screens look different** → it changes its interface now and then. The steps keep the same names: New Project, Upload Data, Annotate, Versions / Generate, Download Dataset.
