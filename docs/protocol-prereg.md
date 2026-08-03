# LiveTS 评测协议预注册文档（草案 v0.1）

> 状态：草案（M0）。正式预注册将在 round-0 启动前冻结并公开（OSF / 仓库 tag）。
> 依据：P1 项目 Spec v0.1（2026-08-01）。本文档一经冻结，任何改动须以带时间戳的 amendment 形式追加，不得回溯修改。

## 1. 核心主张
只在**模型权重发布时点之后产生的数据**上评测（future-only / as-of evaluation），从物理上杜绝预训练语料泄漏与 test-set 反复调参。

## 2. 数据与轮次
- 数据层：≥6 域公开实时源（见 `docs/data-sources.md`），VPS cron 逐日采集，原始快照落盘 + `collected_at` 时间戳（PIT 语义）。
- 滚动轮次：每月一个 evaluation round。round T 的 cutoff = 该月首日 00:00 UTC；输入只用 cutoff 之前采集的数据，target 为 cutoff 之后新产生的数据。
- 洁净成绩判定：每个模型登记其**权重发布日期**（HF model card / 官方 release 时间为准）；仅 cutoff > 发布日期的 round 记入洁净成绩。发布日期存疑时取最早可证日期（保守）。
- 论文主实验（历史模拟 live）：用相同协议在历史数据上按各模型发布日期切分（实现见 `scripts/run_pilot_eval.py`），滚动榜单作为持续贡献。

## 3. 任务与协议
- 任务：单变量点预测 + 概率预测（quantile levels 0.1–0.9）。
- horizon 档位：短（1×季节）、中（2 周/日频 14 步）、长（4 周）；按域频率映射，预注册后固定。
- look-back 档位：统一三档（512 / 1024 / 2048 时间步，不足取全量），**禁止 per-dataset 调参**；模型只允许一套全局超参。
- 缺失值：按各域预注册规则填补（前向填充上限 3 步，否则窗口作废）；不允许模型方自定义。

## 4. 指标与聚合
- 点预测：MASE（scale = in-sample seasonal naive MAE，season_length 按域预注册）。
- 概率预测：CRPS（分位数近似，9 档 pinball×2）与 WQL。
- 聚合：先对每条序列跨 origin 取平均，再跨序列取**几何平均**；报告 bootstrap（≥1000 次重采样）95% CI。
- 显著性：模型两两比较用配对 bootstrap + Diebold-Mariano；报告多重比较校正（Holm）。
- 多 seed：非确定性模型 ≥3 seeds，报告均值±std；确定性模型注明。

## 5. 基线与评测对象
- 统计基线：seasonal naive、AutoETS/AutoARIMA。
- 监督基线：DLinear、PatchTST、iTransformer（统一协议下重训，仅用 cutoff 前数据）。
- TSFM（零样本）：Chronos-2、Chronos-Bolt、TimesFM、Moirai、Time-MoE、TiRex、Toto（登记各自权重发布日期）。

## 6. 防作弊与公开性
- 每轮 target 数据在 cutoff 后才存在，物理上不可提前获取；原始快照哈希入库（后续上 R2）以供审计。
- 提交 API 只接受预测文件，评测代码开源、结果可复现（固定 seed、记录环境与版本）。
- 每模型每轮只允许一次提交；协议冻结后新增模型须登记发布日期方可参评。

## 7. 与 P2 的衔接
每个模型的"老基准成绩 vs LiveTS 洁净成绩"差值，结合 P2 污染审计结论给出污染增益估计。
