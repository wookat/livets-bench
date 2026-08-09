# LiveTS 评测协议预注册文档（v1.0 定稿）

> 状态：v1.0（2026-08-09 定稿）。冻结后任何改动以带时间戳的 amendment 追加于文末，不得回溯修改。
> 实现即协议：本文所有参数与 `livets/eval/` + `scripts/run_matrix.py` / `scripts/make_table.py` 一一对应，结果 JSONL 全量溯源（git commit、环境、运行时间戳）。

## 1. 核心主张（防泄漏时间边界）
- **future-only / as-of evaluation**：模型 m 的洁净成绩只统计满足 `cutoff > release_date(m)` 的评测窗口。
- `release_date(m)` 取该权重在公开渠道**最早可证发布时间**（本轮以 HuggingFace Hub 仓库 `createdAt` 为准，UTC 日期）；存疑取更早（保守，宁可少记洁净窗口）。
- 输入仅允许 origin 之前的观测值；target 为 origin 之后 horizon 步。数据带 `collected_at` 采集时间戳（PIT），live round 中 target 在 cutoff 后才物理存在。

## 2. 数据
- 6 域 25 条日频序列（能源 SMARD、气象与空气质量 Open-Meteo、加密/外汇 Coinbase+ECB、交通 NYC MTA、网络流量 Wikimedia），每条 ≥800 点历史；清单见 `docs/data-sources.md`，加载与缓存代码 `livets/eval/data_loaders.py`。
- 缺失处理：源数据缺失日直接跳过（不填补）；序列内时间索引严格递增去重（保留最早采集值）。

## 3. 评测网格（冻结值）
| 参数 | 值 |
|---|---|
| 滚动 cutoff | 2025-01-01, 2025-07-01, 2026-01-01（UTC） |
| 每 cutoff 评测窗口 | cutoff 后 180 天内均匀取 4 个 origin |
| horizon | 14 步（日频） |
| look-back | 模型自身最大 context（≤2048），不做 per-series 调参 |
| season_length（MASE 尺度） | 周期性域=7（气象/空气/交通/能源/网络），金融=1 |
| quantile 档位 | 0.1–0.9 共 9 档 |
| seeds | 采样型模型 {0,1,2}；确定性模型 seed=0 并标注 |

**禁止 per-dataset 调参**：所有模型全域一套推理配置。

## 4. 指标与聚合
- **MASE**：scale = 全部 origin 前历史的 in-sample seasonal-naive MAE（season_length 如上）。
- **CRPS**：9 档分位数 pinball 均值 ×2（分位数近似）。**WQL**：2·mean_q(pinball 总和)/Σ|y|。
- point-only 模型（如 Time-MoE）只记 MASE，CRPS/WQL 记缺失（不以点预测冒充分位数）。
- 聚合：序列内先对 origin×seed 取算术平均 → 跨序列**几何平均**；95% CI 为跨序列 bootstrap（B=1000，seed=12345）。
- 显著性：模型两两比较用逐窗口配对差值的 bootstrap 检验 + Diebold-Mariano（HLN 小样本校正），多重比较 Holm 校正，α=0.05。

## 5. 评测对象与发布日期登记（本轮）
| 模型 | 权重 | release_date（HF createdAt） | 洁净 cutoff |
|---|---|---|---|
| seasonal naive | — | — | 全部 |
| chronos-bolt-small / base | amazon/chronos-bolt-* | 2024-11-25 | 全部 3 个 |
| chronos-t5-small | amazon/chronos-t5-small | 2024-02-21 | 全部 3 个 |
| Time-MoE-50M | Maple728/TimeMoE-50M | 2024-09-21 | 全部 3 个 |
| Moirai-1.1-R-small | Salesforce/moirai-1.1-R-small | 2024-06-14 | 全部 3 个 |
| TimesFM-2.5-200M | google/timesfm-2.5-200m-pytorch | 2025-09-02 | 仅 2026-01-01 |

## 6. 防作弊与公开性
- 每轮 live target 在 cutoff 后才产生；原始快照落盘并计划哈希入库（R2）供审计。
- 评测代码、数据加载、聚合脚本全部开源；每条结果记录 git commit + 环境版本 + 运行时间戳。
- live round 中每模型每轮一次提交；新模型须先登记 release_date。
- 协议冻结后新增模型/数据域不改动已有结果，只能扩表。

## 7. 与 P2 的衔接
模型在老基准（ETT/Monash/GIFT-Eval）成绩与 LiveTS 洁净成绩的差值，联合 P2 污染审计给出污染增益估计。

---
## Amendments
（无）
