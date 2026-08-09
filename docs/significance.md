# 模型两两显著性检验（mase，重叠窗口，Holm 校正）

配对 bootstrap B=10000（seed=20260809）+ DM(HLN)；seeds 先平均。

| model_a            | model_b            |   n_windows |   mean_mase_diff(a-b) |   p_bootstrap |   p_dm_hln |   p_bootstrap_holm |   p_dm_hln_holm | significant(α=0.05)   |
|:-------------------|:-------------------|------------:|----------------------:|--------------:|-----------:|-------------------:|----------------:|:----------------------|
| autoets            | chronos-bolt-base  |         300 |                0.1909 |        0.0001 |     0.0000 |             0.0028 |          0.0011 | True                  |
| autoets            | chronos-bolt-small |         300 |                0.1650 |        0.0001 |     0.0001 |             0.0028 |          0.0029 | True                  |
| autoets            | chronos-t5-small   |         300 |                0.1011 |        0.0234 |     0.0260 |             0.2808 |          0.3636 | False                 |
| autoets            | moirai-1.1-r-small |         300 |                0.0172 |        0.6742 |     0.6773 |             1.0000 |          1.0000 | False                 |
| autoets            | seasonal_naive     |         300 |               -0.0253 |        0.3780 |     0.4209 |             1.0000 |          1.0000 | False                 |
| autoets            | time-moe-50m       |         300 |               -0.0334 |        0.7002 |     0.7116 |             1.0000 |          1.0000 | False                 |
| autoets            | timesfm-2.5-200m   |         100 |                0.3709 |        0.0001 |     0.0002 |             0.0028 |          0.0045 | True                  |
| chronos-bolt-base  | chronos-bolt-small |         300 |               -0.0258 |        0.2898 |     0.3210 |             1.0000 |          1.0000 | False                 |
| chronos-bolt-base  | chronos-t5-small   |         300 |               -0.0897 |        0.0216 |     0.0295 |             0.2808 |          0.3636 | False                 |
| chronos-bolt-base  | moirai-1.1-r-small |         300 |               -0.1737 |        0.0001 |     0.0000 |             0.0028 |          0.0007 | True                  |
| chronos-bolt-base  | seasonal_naive     |         300 |               -0.2162 |        0.0001 |     0.0000 |             0.0028 |          0.0000 | True                  |
| chronos-bolt-base  | time-moe-50m       |         300 |               -0.2242 |        0.0016 |     0.0083 |             0.0256 |          0.1325 | False                 |
| chronos-bolt-base  | timesfm-2.5-200m   |         100 |                0.0939 |        0.0294 |     0.0722 |             0.2940 |          0.7221 | False                 |
| chronos-bolt-small | chronos-t5-small   |         300 |               -0.0639 |        0.0824 |     0.1083 |             0.6840 |          0.9366 | False                 |
| chronos-bolt-small | moirai-1.1-r-small |         300 |               -0.1479 |        0.0001 |     0.0001 |             0.0028 |          0.0016 | True                  |
| chronos-bolt-small | seasonal_naive     |         300 |               -0.1903 |        0.0001 |     0.0000 |             0.0028 |          0.0000 | True                  |
| chronos-bolt-small | time-moe-50m       |         300 |               -0.1984 |        0.0042 |     0.0129 |             0.0588 |          0.1939 | False                 |
| chronos-bolt-small | timesfm-2.5-200m   |         100 |                0.1931 |        0.0001 |     0.0027 |             0.0028 |          0.0488 | True                  |
| chronos-t5-small   | moirai-1.1-r-small |         300 |               -0.0840 |        0.0262 |     0.0347 |             0.2882 |          0.3821 | False                 |
| chronos-t5-small   | seasonal_naive     |         300 |               -0.1264 |        0.0002 |     0.0002 |             0.0034 |          0.0038 | True                  |
| chronos-t5-small   | time-moe-50m       |         300 |               -0.1345 |        0.0760 |     0.1041 |             0.6840 |          0.9366 | False                 |
| chronos-t5-small   | timesfm-2.5-200m   |         100 |                0.2289 |        0.0001 |     0.0040 |             0.0028 |          0.0672 | False                 |
| moirai-1.1-r-small | seasonal_naive     |         300 |               -0.0425 |        0.2000 |     0.2279 |             1.0000 |          1.0000 | False                 |
| moirai-1.1-r-small | time-moe-50m       |         300 |               -0.0505 |        0.5214 |     0.5438 |             1.0000 |          1.0000 | False                 |
| moirai-1.1-r-small | timesfm-2.5-200m   |         100 |                0.2774 |        0.0001 |     0.0013 |             0.0028 |          0.0240 | True                  |
| seasonal_naive     | time-moe-50m       |         300 |               -0.0080 |        0.9470 |     0.9273 |             1.0000 |          1.0000 | False                 |
| seasonal_naive     | timesfm-2.5-200m   |         100 |                0.4047 |        0.0001 |     0.0001 |             0.0028 |          0.0014 | True                  |
| time-moe-50m       | timesfm-2.5-200m   |         100 |                0.2324 |        0.0016 |     0.0262 |             0.0256 |          0.3636 | False                 |
