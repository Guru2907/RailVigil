Box AP50 (IoU 0.5), mean over structure_permanent, structure_temporary, vegetation, material_dump, vehicle_parked; 95 % bootstrap intervals from 1000 paired resamples of the test photos.

| Model | all (75) | India (41) | other countries (34) |
|---|---|---|---|
| baseline | 0.594 [0.524, 0.736] | 0.684 [0.602, 0.910] | 0.506 [0.451, 0.681] |
| v2-m-f10 | 0.279 [0.212, 0.416] | 0.249 [0.202, 0.427] | 0.308 [0.276, 0.446] |

Paired differences (row model minus column model), all photos:

| Difference | Value | 95 % interval | Resamples above 0 |
|---|---|---|---|
| v2-m-f10 - baseline | -0.316 | [-0.397, -0.198] | 0% |

Per class, all photos (objects in brackets):

| Model | structure_permanent (55) | structure_temporary (36) | vegetation (115) | material_dump (5) | vehicle_parked (14) |
|---|---|---|---|---|---|
| baseline | 0.543 [0.396, 0.737] | 0.651 [0.434, 0.825] | 0.974 [0.936, 0.999] | 0.000 [0.000, 0.000] | 0.804 [0.568, 1.000] |
| v2-m-f10 | 0.133 [0.069, 0.244] | 0.225 [0.076, 0.416] | 0.600 [0.507, 0.691] | 0.000 [0.000, 0.000] | 0.436 [0.193, 1.000] |

Ultralytics metrics of the fine-tuned models on the same labels (mask mAP50 / mask mAP50-95 / box mAP50):

| Model | all | India | other countries |
|---|---|---|---|
| v2-m-f10 | 0.260 / 0.164 / 0.282 | 0.219 / 0.129 / 0.252 | 0.300 / 0.199 / 0.319 |
