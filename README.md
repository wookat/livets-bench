# livets-bench

LiveTS：防泄漏动态时序预测基准（P1 · M0 工程实现）。

核心主张：**只在模型权重发布时点之后产生的数据上评测**（future-only / as-of evaluation），物理上杜绝 TSFM 预训练泄漏与静态 test set 过拟合。

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

## Pilot 结果（2026-08-03，固定 seed=42，cutoff = Chronos-Bolt 发布日 2024-11-26）
6 条日频序列（气象×2 / BTC / 外汇 / 页面访问×2）× 4 个发布日之后的 origin，horizon=14：

| 模型 | geo-mean MASE | geo-mean CRPS | geo-mean WQL |
|---|---|---|---|
| seasonal naive | 1.171 | 21.00 | 0.0779 |
| chronos-bolt-small（零样本，CPU） | 1.089 | 18.24 | 0.0676 |

完整逐窗口结果见 `results/pilot.json`（含运行环境记录）。
