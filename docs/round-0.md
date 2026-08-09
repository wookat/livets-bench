# Live Round-0（首个真实滚动评测轮）

协议：`docs/protocol-prereg.md` v1.0 + A1（冻结，不回溯改分）。

## 日程（月度节奏）

| 事件 | 时间（UTC） |
|---|---|
| Round-0 cutoff | 2026-09-01 00:00 |
| 提交窗口 | cutoff 后 7 天内（2026-09-01 ~ 2026-09-08 23:59） |
| 目标窗口 | cutoff 后的 4 个 forecast origin，horizon=14（与历史模拟同构） |
| 评分与公布 | 最后一个 target 窗口数据完整落库后（约 2026-10-中旬），带全量 JSONL 溯源 |

此后每月 1 日一个新 round，同样节奏滚动。

## 提交格式

每个模型每 round 一次提交，JSON：

```json
{
  "model": "your-model-name",
  "release_date": "YYYY-MM-DD",
  "round": "2026-09",
  "forecasts": [
    {
      "series_id": "weather:berlin:t2m_mean",
      "origin": "2026-09-05",
      "quantiles": {"0.1": [..14 值..], "0.2": [...], "...": "...", "0.9": [...]}
    }
  ]
}
```

- `release_date`：权重最早公开可验证时间戳（HF createdAt 保守登记），首次参赛前必须注册；cutoff ≤ release_date 的 round 不计入洁净成绩。
- 仅接受分位数预测（9 档 0.1–0.9）；纯点预测模型提交 `{"0.5": [...]}`，只计 MASE。
- 提交时 target 尚未产生：物理防泄漏。输入数据以 R2 上 cutoff 时点快照（SHA-256 manifest）为准。

## 反作弊

- 每模型每 round 一次提交；重复提交拒绝。
- release date 注册先于首次参赛，不可回改。
- 原始快照哈希公开可第三方审计；聚合代码确定性且开源。

## 评分

与历史模拟完全一致：MASE / CRPS(9 分位) / WQL，序列内均值 → 跨序列几何平均，bootstrap CI，DM+HLN+Holm 显著性。
