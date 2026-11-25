Box AP50 (IoU 0.5), mean over structure_permanent, structure_temporary, vegetation, vehicle_parked; 95 % bootstrap intervals from 1000 paired resamples of the test photos.

| Model | all (66) | India (42) | other countries (24) |
|---|---|---|---|
| v2-s-f10 | 0.068 [0.039, 0.173] | 0.111 [0.056, 0.303] | 0.059 [0.022, 0.187] |
| v2-s-f10-seed1 | 0.124 [0.057, 0.225] | 0.181 [0.064, 0.310] | 0.076 [0.035, 0.285] |
| v2-s-f10-seed2 | 0.119 [0.059, 0.236] | 0.168 [0.072, 0.349] | 0.121 [0.024, 0.257] |
| v2-s-f10-india | 0.121 [0.065, 0.232] | 0.126 [0.057, 0.316] | 0.119 [0.041, 0.279] |
| v2-s-f10-notaco | 0.088 [0.054, 0.190] | 0.128 [0.058, 0.321] | 0.116 [0.037, 0.277] |

Paired differences (row model minus column model), all photos:

| Difference | Value | 95 % interval | Resamples above 0 |
|---|---|---|---|
| v2-s-f10-seed1 - v2-s-f10 | 0.056 | [-0.032, 0.131] | 87% |
| v2-s-f10-seed2 - v2-s-f10 | 0.051 | [-0.007, 0.109] | 96% |
| v2-s-f10-india - v2-s-f10 | 0.052 | [0.008, 0.103] | 100% |
| v2-s-f10-notaco - v2-s-f10 | 0.020 | [-0.022, 0.060] | 88% |
| v2-s-f10-seed2 - v2-s-f10-seed1 | -0.005 | [-0.072, 0.084] | 45% |
| v2-s-f10-india - v2-s-f10-seed1 | -0.003 | [-0.087, 0.086] | 50% |
| v2-s-f10-notaco - v2-s-f10-seed1 | -0.036 | [-0.104, 0.040] | 24% |
| v2-s-f10-india - v2-s-f10-seed2 | 0.002 | [-0.064, 0.056] | 55% |
| v2-s-f10-notaco - v2-s-f10-seed2 | -0.031 | [-0.082, 0.024] | 16% |
| v2-s-f10-notaco - v2-s-f10-india | -0.033 | [-0.087, 0.012] | 11% |

Per class, all photos (objects in brackets):

| Model | structure_permanent (23) | structure_temporary (12) | vegetation (52) | vehicle_parked (11) |
|---|---|---|---|---|
| v2-s-f10 | 0.018 [0.004, 0.065] | 0.041 [0.002, 0.160] | 0.154 [0.080, 0.300] | 0.059 [0.000, 0.444] |
| v2-s-f10-seed1 | 0.020 [0.005, 0.064] | 0.036 [0.005, 0.174] | 0.206 [0.103, 0.355] | 0.232 [0.000, 0.485] |
| v2-s-f10-seed2 | 0.023 [0.001, 0.111] | 0.046 [0.000, 0.262] | 0.247 [0.125, 0.393] | 0.160 [0.000, 0.500] |
| v2-s-f10-india | 0.015 [0.003, 0.057] | 0.101 [0.003, 0.292] | 0.234 [0.132, 0.402] | 0.132 [0.000, 0.500] |
| v2-s-f10-notaco | 0.035 [0.005, 0.098] | 0.067 [0.004, 0.242] | 0.191 [0.081, 0.343] | 0.059 [0.000, 0.345] |

Left out of the mean (fewer than the minimum objects): material_dump (1)

Ultralytics metrics of the fine-tuned models on the same labels (mask mAP50 / mask mAP50-95 / box mAP50):

| Model | all | India | other countries |
|---|---|---|---|
| v2-s-f10 | 0.069 / 0.023 / 0.074 | 0.134 / 0.041 / 0.119 | 0.058 / 0.022 / 0.069 |
| v2-s-f10-seed1 | 0.104 / 0.027 / 0.107 | 0.176 / 0.043 / 0.183 | 0.056 / 0.018 / 0.056 |
| v2-s-f10-seed2 | 0.091 / 0.030 / 0.093 | 0.163 / 0.050 / 0.158 | 0.073 / 0.038 / 0.079 |
| v2-s-f10-india | 0.074 / 0.024 / 0.077 | 0.131 / 0.042 / 0.129 | 0.052 / 0.019 / 0.069 |
| v2-s-f10-notaco | 0.075 / 0.025 / 0.077 | 0.127 / 0.043 / 0.138 | 0.078 / 0.031 / 0.074 |
