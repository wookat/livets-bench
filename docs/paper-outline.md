# LiveTS 论文大纲（目标：NeurIPS Datasets & Benchmarks；备选 ICML/ICLR D&B、VLDB）

工作标题：**LiveTS: A Leakage-Proof, Continuously-Refreshed Benchmark for Zero-Shot Time Series Forecasting**

## 1. Introduction
- 评测危机三联症：预训练泄漏（TSFM 语料 ⊇ 老基准）、静态 test-set 社区过拟合、协议不统一。
- 主张：future-only / as-of 评测把"防泄漏"从统计检测问题变成物理不可能问题。
- 贡献：① LiveTS 基准（6 域实时采集 + 月度滚动 round + PIT 快照审计）；② 预注册评测协议（release-date 门控、geo-mean+bootstrap、DM+Holm）；③ 首批 TSFM 洁净成绩与"污染增益"分析；④ 全开源工具链。

## 2. Related Work
GIFT-Eval / fev-bench（静态、事后标泄漏）；Monash（饱和）；M6（live 金标准但一次性、单域）；LiveBench/LMSYS（LLM 动态评测范式）；评测方法学（Hewamalage 等）；污染审计（P2 线）。

## 3. LiveTS Design
- 3.1 数据层：6 域公开实时源、PIT 采集语义、快照哈希；冗余备选。
- 3.2 时间边界：release_date 登记（HF createdAt，保守取早）、cutoff 门控、洁净成绩定义。
- 3.3 协议层：预注册（v1.0 全文附录）、指标、聚合、显著性、禁 per-dataset 调参。
- 3.4 服务层：滚动榜单（R2 + Workers + D1），月度 round 流程。

## 4. Historical-Simulation Experiments（论文主实验）
- 4.1 设置：25 序列 × 3 cutoff × 4 origin × horizon 14；模型 6 个 TSFM + seasonal naive（+ 计划：AutoETS、DLinear/PatchTST/iTransformer 重训线）。
- 4.2 主表：geo-MASE/CRPS/WQL + 95% CI（见 docs/main-table.md，数字以 results/matrix*.jsonl 为准）。
- 4.3 分域异质性：无普适冠军（金融域 naive 难被击败 vs 周期域 TSFM 占优）。
- 4.4 洁净 vs 老基准差值 → 污染增益估计（联动 P2；老基准数字引用原论文报告值）。
- 4.5 稳健性：cutoff 敏感性、seed 方差、CI 重叠分析、DM 检验矩阵。

## 5. The Live Benchmark
round-0 启动流程、提交 API、防作弊机制、社区治理（新模型登记、amendment 制）。

## 6. Limitations & Ethics
单变量日频为主；免 key 源限流风险；域覆盖偏公共基础设施数据；发布日期以公开可证为准可能偏保守。

## 7. 附录
预注册全文、数据源表、逐域逐模型完整表、复现实验命令、JSONL schema。

---
## 待补实验（投稿前）
1. 统计基线 AutoETS/AutoARIMA（statsforecast）+ 监督基线 DLinear/PatchTST/iTransformer（cutoff 前重训，xu-4 3090）。
2. Chronos-2 / TiRex / Toto / Time-MoE-200M 扩充（部分需 GPU / 更大内存）。
3. DM + Holm 显著性矩阵脚本化（scripts/significance.py）。
4. 序列扩容 25 → 200+（配置化）。
5. live round-0（真实未来数据）作为 camera-ready 增量证据。
