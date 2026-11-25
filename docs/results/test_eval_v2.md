Box AP50 (IoU 0.5), mean over structure_permanent, structure_temporary, vegetation, vehicle_parked; 95 % bootstrap intervals from 1000 paired resamples of the test photos.

| Model | all (66) | India (42) | other countries (24) |
|---|---|---|---|
| baseline | 0.167 [0.084, 0.259] | 0.223 [0.085, 0.347] | 0.115 [0.049, 0.222] |
| railvigil-s | 0.117 [0.053, 0.217] | 0.164 [0.043, 0.254] | 0.097 [0.037, 0.264] |
| v2-s-f10 | 0.068 [0.039, 0.173] | 0.111 [0.056, 0.303] | 0.059 [0.022, 0.187] |
| v2-m-f10 | 0.166 [0.089, 0.322] | 0.159 [0.080, 0.341] | 0.248 [0.105, 0.506] |

Paired differences (row model minus column model), all photos:

| Difference | Value | 95 % interval | Resamples above 0 |
|---|---|---|---|
| railvigil-s - baseline | -0.050 | [-0.107, 0.018] | 7% |
| v2-s-f10 - baseline | -0.099 | [-0.164, -0.010] | 2% |
| v2-m-f10 - baseline | -0.002 | [-0.078, 0.154] | 57% |
| v2-s-f10 - railvigil-s | -0.049 | [-0.134, 0.063] | 20% |
| v2-m-f10 - railvigil-s | 0.048 | [-0.033, 0.198] | 88% |
| v2-m-f10 - v2-s-f10 | 0.097 | [0.029, 0.192] | 100% |

Per class, all photos (objects in brackets):

| Model | structure_permanent (23) | structure_temporary (12) | vegetation (52) | vehicle_parked (11) |
|---|---|---|---|---|
| baseline | 0.065 [0.031, 0.143] | 0.001 [0.000, 0.005] | 0.298 [0.165, 0.458] | 0.305 [0.027, 0.579] |
| railvigil-s | 0.018 [0.004, 0.065] | 0.051 [0.002, 0.205] | 0.206 [0.099, 0.369] | 0.193 [0.000, 0.472] |
| v2-s-f10 | 0.018 [0.004, 0.065] | 0.041 [0.002, 0.160] | 0.154 [0.080, 0.300] | 0.059 [0.000, 0.444] |
| v2-m-f10 | 0.059 [0.000, 0.163] | 0.160 [0.008, 0.500] | 0.237 [0.133, 0.382] | 0.206 [0.000, 0.667] |

Left out of the mean (fewer than the minimum objects): material_dump (1)

Ultralytics metrics of the fine-tuned models on the same labels (mask mAP50 / mask mAP50-95 / box mAP50):

| Model | all | India | other countries |
|---|---|---|---|
| railvigil-s | 0.086 / 0.029 / 0.101 | 0.141 / 0.042 / 0.150 | 0.074 / 0.032 / 0.093 |
| v2-s-f10 | 0.069 / 0.023 / 0.074 | 0.134 / 0.041 / 0.119 | 0.058 / 0.022 / 0.069 |
| v2-m-f10 | 0.151 / 0.044 / 0.143 | 0.183 / 0.050 / 0.173 | 0.190 / 0.064 / 0.193 |
