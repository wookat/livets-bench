# livets-bench

LiveTS：按模型发布日分层的回溯评测基准（release-date-stratified retrospective evaluation）。

核心主张：**只在模型权重发布时点之后产生的数据上评测**——对权重冻结的模型，在已归档的多域历史上按发布日分层回放，等价于一个从各模型发布日起就在运行的 live 平台，且今天即可一次性给出所有历史模型的洁净成绩。与并行的 live 平台（Impermanent [arXiv:2603.08707]、TS-Arena [arXiv:2512.20761]）互补：它们只能评「从现在起」的未来数据且各自单域（GitHub 活动 / 能源），LiveTS 提供 6 域回溯分层 + 月度 live track 衔接。

> **定位调整（2026-08-10）**：按课题组战略决定，LiveTS 不再作为独立主会投稿主力；
> 数据资产已改造为 P2 污染审计（wookat/tsfm-contamination-audit）的 post-cutoff
> 非成员对照来源（`scripts/export_p2_nonmember.py`，8 数据集 × 6 域，冻结 NPZ +
> SHA-256 清单已入 P2 仓库 `data_livets/`）。采集管道 / 榜单 / 月度 round 照常运行，
> 作为长期基础设施；重定位版论文（paper/）保留归档，将来作为 D&B workshop 论文或
> P2 配套资源发布。

## 结构
- `configs/sources.yaml` — 数据源配置（6 域 7 源，全部免 key；配置化、无硬编码路径）
- `livets/collectors/` — 采集器：原始快照落盘 + tidy CSV，PIT 语义（`collected_at` 时间戳）
- `livets/eval/` — 指标（MASE/CRPS/WQL）、滚动 origin 回测、模型（seasonal naive / Chronos-Bolt）
- `scripts/run_collect.py` — 逐日采集入口（cron 友好）
- `scripts/run_pilot_eval.py` — 历史模拟 live 评测（按模型发布日期切分）
- `docs/data-sources.md` — 数据源清单与冗余备选
- `docs/protocol-prereg.md` — 评测协议预注册草案
- `docs/proposal.md` — 研究 proposal

## 快速开始
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/run_collect.py                 # 采集一次（数据根目录可用 LIVETS_DATA_ROOT 覆盖）
.venv/bin/pip install -r requirements-eval.txt           # torch(CPU) + chronos
.venv/bin/python scripts/run_pilot_eval.py               # 历史模拟 live 评测
```

## 部署（VPS cron）
```
15 2 * * * cd /opt/livets-bench && .venv/bin/python scripts/run_collect.py >> logs/cron.log 2>&1
```

## 论文阶段评测矩阵

### 扩容矩阵（当前主表来源，协议 amendment A1）
11 模型（6 TSFM + 3 监督基线 + seasonal naive + AutoETS）× **205 序列** × 6 域 × 3 滚动 cutoff（2025-01-01 / 2025-07-01 / 2026-01-01），共 **50,284 窗口**，合并去重于 `results/matrix-expanded-all.jsonl`（分片：`matrix-expanded*.jsonl`、`results/gpu/*.jsonl`、`matrix-supervised.jsonl`）。主表 `docs/main-table.md`，显著性 `docs/significance.md`，协议 v1.0+A1 `docs/protocol-prereg.md`。
- 零样本 TSFM：`scripts/run_matrix.py`（GPU 侧经 `dell@xu-1` sgpu 调度，launch 脚本 `ops/sgpu/`，回传经 sha256 校验）。
- 监督基线 DLinear/PatchTST/iTransformer：`scripts/run_supervised.py`，每个 cutoff 用严格早于 cutoff 的数据重训全局模型（MQ 分位损失，seeds {0,1,2}）。
- 已知注记：iTransformer 以 `n_series=1` 单变量方式接入（与其多变量设计不符，成绩偏弱属配置保守而非调参结论，论文中将注明）。

### 25 序列 pilot（保留）
8 模型 × 25 序列 × 3 cutoff，`results/matrix.jsonl`（3400 窗口）。

复现注记：pilot 中 Moirai 的 900 窗口在 xu-4 RTX 3090 上直跑（未经 sgpu 调度器，属一次性例外，环境记录于 JSONL；xu-4 需 `HF_ENDPOINT=https://hf-mirror.com`）；扩容矩阵 GPU 任务已全部改为经 `dell@xu-1` 的 `/home/dell/.local/bin/sgpu submit` 排队执行。

## Pilot 结果（2026-08-03，固定 seed=42，cutoff = Chronos-Bolt 发布日 2024-11-26）
6 条日频序列（气象×2 / BTC / 外汇 / 页面访问×2）× 4 个发布日之后的 origin，horizon=14：

| 模型 | geo-mean MASE | geo-mean CRPS | geo-mean WQL |
|---|---|---|---|
| seasonal naive | 1.171 | 21.00 | 0.0779 |
| chronos-bolt-small（零样本，CPU） | 1.089 | 18.24 | 0.0676 |

完整逐窗口结果见 `results/pilot.json`（含运行环境记录）。
