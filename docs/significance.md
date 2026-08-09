# 模型两两显著性检验（mase，重叠窗口，Holm 校正）

配对 bootstrap B=10000（seed=20260809）+ DM(HLN)；seeds 先平均。

| model_a            | model_b            |   n_windows |   mean_mase_diff(a-b) |   p_bootstrap |   p_dm_hln |   p_bootstrap_holm |   p_dm_hln_holm | significant(α=0.05)   |
|:-------------------|:-------------------|------------:|----------------------:|--------------:|-----------:|-------------------:|----------------:|:----------------------|
| autoets            | chronos-bolt-base  |        2460 |                0.2022 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| autoets            | chronos-bolt-small |        2460 |                0.2138 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| autoets            | chronos-t5-small   |        2460 |                0.0406 |        0.2934 |     0.2887 |             0.8802 |          0.8661 | False                 |
| autoets            | moirai-1.1-r-small |        2460 |                0.1302 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| autoets            | seasonal_naive     |        2460 |               -0.0232 |        0.1208 |     0.1083 |             0.6888 |          0.6315 | False                 |
| autoets            | time-moe-50m       |        2460 |               -0.0228 |        0.4472 |     0.4480 |             0.8944 |          0.8960 | False                 |
| autoets            | timesfm-2.5-200m   |         820 |                0.2931 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| chronos-bolt-base  | chronos-bolt-small |        2484 |                0.0109 |        0.0984 |     0.0998 |             0.6888 |          0.6315 | False                 |
| chronos-bolt-base  | chronos-t5-small   |        2460 |               -0.1616 |        0.0001 |     0.0000 |             0.0031 |          0.0001 | True                  |
| chronos-bolt-base  | moirai-1.1-r-small |        2460 |               -0.0720 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| chronos-bolt-base  | seasonal_naive     |        2460 |               -0.2254 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| chronos-bolt-base  | time-moe-50m       |        2460 |               -0.2250 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| chronos-bolt-base  | timesfm-2.5-200m   |         820 |                0.0452 |        0.0030 |     0.0043 |             0.0270 |          0.0389 | True                  |
| chronos-bolt-small | chronos-t5-small   |        2460 |               -0.1733 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| chronos-bolt-small | moirai-1.1-r-small |        2460 |               -0.0837 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| chronos-bolt-small | seasonal_naive     |        2460 |               -0.2371 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| chronos-bolt-small | time-moe-50m       |        2460 |               -0.2366 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| chronos-bolt-small | timesfm-2.5-200m   |         820 |                0.0504 |        0.0012 |     0.0008 |             0.0120 |          0.0093 | True                  |
| chronos-t5-small   | moirai-1.1-r-small |        2460 |                0.0896 |        0.0042 |     0.0134 |             0.0336 |          0.1075 | False                 |
| chronos-t5-small   | seasonal_naive     |        2460 |               -0.0638 |        0.0994 |     0.0902 |             0.6888 |          0.6315 | False                 |
| chronos-t5-small   | time-moe-50m       |        2460 |               -0.0634 |        0.1418 |     0.1374 |             0.6888 |          0.6315 | False                 |
| chronos-t5-small   | timesfm-2.5-200m   |         820 |                0.2102 |        0.0001 |     0.0010 |             0.0031 |          0.0099 | True                  |
| dlinear            | itransformer       |        2484 |               -2.6647 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| dlinear            | patchtst           |        2484 |                1.5215 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| itransformer       | patchtst           |        2484 |                4.1861 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| moirai-1.1-r-small | seasonal_naive     |        2460 |               -0.1534 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| moirai-1.1-r-small | time-moe-50m       |        2460 |               -0.1530 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| moirai-1.1-r-small | timesfm-2.5-200m   |         820 |                0.1245 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| seasonal_naive     | time-moe-50m       |        2460 |                0.0004 |        0.9858 |     0.9880 |             0.9858 |          0.9880 | False                 |
| seasonal_naive     | timesfm-2.5-200m   |         820 |                0.3039 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
| time-moe-50m       | timesfm-2.5-200m   |         820 |                0.2460 |        0.0001 |     0.0000 |             0.0031 |          0.0000 | True                  |
