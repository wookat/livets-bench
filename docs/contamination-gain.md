# 污染增益分析（LiveTS × P2 对接表）

LiveTS 侧：skill_live = geo-MASE(model)/geo-MASE(seasonal naive)，共享洁净窗口，<1 越小越好
（生成：`scripts/contamination_gain.py`，输入 `matrix-expanded-all.jsonl`）。

P2 侧：来自 [tsfm-contamination-audit](https://github.com/wookat/tsfm-contamination-audit) `results/main_table.md`
（8 模型 × 14 数据集）。P2 的 "skill" probe 报告 member（在预训练语料中的数据集）与 non-member
数据集上的均值差；member − non-member 差值越大，越提示该模型在其训练语料覆盖的基准上的成绩被污染抬高。
注意：P2 全部 Holm 校正后无显著（最强信号 chronos-bolt-base skill probe：perm p=0.028，Holm p=0.615；
timesfm-2.0-500m skill probe perm p=0.0100，Holm p=0.240）——即在该样本量下污染效应方向一致但统计上不可断言。

| LiveTS 模型 | skill_live（洁净窗口） | P2 对应模型 | P2 skill member | P2 skill non-member | Δ(member−nonmember) | P2 Holm p |
|---|---|---|---|---|---|---|
| chronos-bolt-small | 0.754 (2460) | amazon/chronos-bolt-small | 0.2971 | −0.6731 | +0.970 | 0.860 |
| chronos-bolt-base | 0.756 (2460) | amazon/chronos-bolt-base | 0.3226 | −1.0878 | +1.410 | 0.615 |
| chronos-t5-small | 0.809 (2460) | amazon/chronos-t5-small | 0.2528 | −0.1079 | +0.361 | 1 |
| time-moe-50m | 0.850 (2460) | Maple728/TimeMoE-50M | −0.3824 | 0.1728 | −0.555 | 1 |
| moirai-1.1-r-small | 0.817 (2460) | Salesforce/moirai-**1.0**-R-small（版本不同） | −0.2160 | 0.0261 | −0.242 | 1 |
| timesfm-2.5-200m | 0.707 (820) | google/timesfm-**2.0-500m**（版本不同） | 0.4166 | −0.1337 | +0.550 | 0.240 |

版本注记：P2 审计的 Moirai-1.0-R-small 与 TimesFM-2.0-500m 与 LiveTS 评测的 1.1-R / 2.5-200m 非同一 checkpoint，
只能作方向性参照，不能逐 checkpoint 对齐。P2 的 non-member 均值受 covid_deaths 极端离群（skill 低至 −11）拉低，
Δ 的量级解释需谨慎（详见 P2 per-dataset 表）。

定性结论（写入论文 §4.3）：P2 在 Chronos 系与 TimesFM 上观测到 member 数据集 skill 一致性偏高
（Cliff's δ 0.47–0.85），方向与「legacy 基准成绩被污染抬高」假设一致，但 Holm 后不显著；
LiveTS 洁净窗口成绩因此是这些模型当前唯一不受该疑虑影响的成绩来源。两项目互补：
P2 事后探测污染迹象，LiveTS 事前使污染不可能。
