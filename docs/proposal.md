# LiveTS：防泄漏动态时序预测基准 — 研究 Proposal（v0.1）

研究工程师 · 2026-08-03 ｜ 基于 P1 项目 Spec v0.1 与课题组方向 6 调研报告

> **重定位注记（2026-08-10 撞车核查后）**：Impermanent（arXiv:2603.08707，GitHub 活动单域，impermanent.timecopilot.dev）与 TS-Arena（arXiv:2512.20761，能源单域，forecast pre-registration，ts-arena.live）两个 live 防泄漏平台已上线运行。LiveTS 立论已从「第一个防泄漏动态基准」重定位为「**按模型发布日分层的回溯评测**（release-date-stratified retrospective evaluation）」：live 平台只能评「从现在起」的未来数据，无法回答历史模型在已发生数据上的真实零样本能力，也需长期积累才有统计功效；LiveTS 对权重冻结模型在归档历史上按发布日分层回放，今天即给出所有历史模型的洁净成绩，并以 6 域多样性 + 月度 live track 与两平台互补。详见 paper/main.tex 重定位版。

## 1. 研究问题与假设

**问题**：当前时序预测评测体系存在三重失效：
1. **预训练泄漏**：TSFM（Chronos/TimesFM/Moirai 等）的万亿点预训练语料与 ETT/Monash/GIFT-Eval 等老基准大面积重叠，"零样本"成绩不可信（GIFT-Eval 已被迫添加泄漏标志列）；
2. **test-set 过拟合**：静态测试集被社区反复调参与 seed shopping，"illusion of progress" 循环在 LTSF/TSAD/TSFM 三条战线均已发生；
3. **协议不统一**：look-back、归一化、drop-last 等差异使跨论文数字不可比。

**核心假设**：
- H1：在"模型发布日之后产生的数据"（future-only）上评测，TSFM 相对简单基线（seasonal naive、AutoETS、DLinear）的优势将显著小于其在老基准上的报告值；差值可作为"污染增益"的估计（与 P2 审计互证）。
- H2：不同域上 TSFM 排名不稳定（无普适冠军），几何平均 + bootstrap CI 的聚合协议能给出统计上可辩护的总排名。
- H3：滚动月度 round 的"洁净成绩"能形成社区愿意采纳的动态排行榜（类似 LiveBench 之于 LLM、M6 之于预测竞赛）。

## 2. 与已有工作的差异
| 工作 | 性质 | 缺陷 | LiveTS 差异 |
|---|---|---|---|
| GIFT-Eval / fev-bench | 静态基准 | 无法防未来污染，只能事后标注泄漏 | 滚动产生新 ground truth，物理防泄漏 |
| Monash | 静态、老旧 | 已饱和、大量进入预训练语料 | 数据持续更新 |
| M6 竞赛 | live 评测黄金标准 | 一次性、仅金融 | 多域、常态化、月度滚动、面向 TSFM |
| LiveBench（LLM） | 动态防污染 | 非时序 | 把该范式引入时序 + 指标学贡献（MASE/CRPS 几何平均、DM 检验、多重比较校正的预注册协议） |

方法学贡献：① as-of/PIT 采集与评测语义（沿用课题组 Stock-Prediction lock-box 方法论）；② 预注册协议（防 test-set 反复调参）；③ 发布日期切分的"历史模拟 live"作为可即时发表的主实验。

## 3. 数据集
6 域公开实时源（全部免 key，均已验证，冗余备选见 `docs/data-sources.md`）：能源（NESO 英国电网需求 / SMARD）、气象（Open-Meteo 多站点）、加密货币与外汇（Coinbase / Frankfurter-ECB）、空气质量（Open-Meteo AQ / OpenAQ）、交通（NYC MTA 客流 / Socrata 系）、网络流量（Wikimedia pageviews / Cloudflare Radar）。M0 目标 ≥200 条序列（配置化扩容路径已写入清单文档）。

## 4. Baseline 与评测对象
- 统计：seasonal naive、AutoETS、AutoARIMA（statsforecast）。
- 监督：DLinear、PatchTST、iTransformer（统一协议、cutoff 前数据重训）。
- TSFM 零样本：Chronos-2、Chronos-Bolt、TimesFM、Moirai、Time-MoE、TiRex、Toto（登记权重发布日期）。

## 5. 评测协议（防泄漏、多 seed、统计显著性）
见 `docs/protocol-prereg.md`（预注册草案）。要点：future-only cutoff；MASE/CRPS/WQL；跨序列几何平均 + 1000 次 bootstrap 95% CI；配对 bootstrap + Diebold-Mariano + Holm 校正；非确定性模型 ≥3 seeds；统一 look-back 档位、禁止 per-dataset 调参；协议冻结后 amendment 制。

## 6. 算力预算
- 采集：VPS cron（现有 CN/海外 VPS），成本 ≈0。
- 推理：全部零样本/轻量训练。TSFM 推理在 xu-3/xu-4 RTX 3090 上（Chronos-bolt-small CPU 即可，本 pilot 已验证）；监督基线重训 <10 GPU·h/轮。磁盘：模型权重最大 ~5GB（Moirai-large/Time-MoE），注意 xu-4 仅 14G，需按模型逐个下载-评测-清理。
- 托管：Cloudflare R2 + Workers + D1（现有 token，零成本）。

## 7. 里程碑
- **M0（2 周，本阶段已启动）**：数据源选型 ✅、采集器跑通 6 域 ✅、评测骨架 + pilot 数字 ✅；扩容到 ≥200 序列、VPS 部署 cron、协议预注册公开。
- **M1（6 周）**：round-0 评测，首批 7 个 TSFM + 基线的洁净成绩；R2 快照 + Workers/D1 榜单上线。
- **M2（3 个月）**：3 轮滚动数据；"历史模拟 live"主实验（各模型发布日期切分）+ 污染增益分析（联动 P2）；论文投 NeurIPS D&B（备选 VLDB / ICLR D&B）；全部工具链开源。

## 8. 论文与开源目标
- 目标 venue：NeurIPS Datasets & Benchmarks track（首选）；备选 VLDB、ICLR D&B、TMLR。
- 开源：livets-bench 仓库（采集器 + 协议 + 评测代码 + 榜单前端），数据快照带哈希审计发布于 R2。

## 9. 风险与对策
- 数据源断供 → 每域 ≥2 冗余源（已在清单中），采集失败单源隔离不影响整体（已实现）。
- 月度周期慢 → 历史模拟 live 作为论文主实验（骨架已跑通）。
- 免 key 源限流/封禁 → UA 标识 + 低频访问 + 备选 key 源（EIA/OpenAQ 免费 key 可申请）。
