# LiveTS leaderboard service

Cloudflare Worker `livets-leaderboard` — 提交 API + 在线榜单。
线上地址: https://livets-leaderboard.wookat520.workers.dev

## 架构

- **Workers**: `src/index.js` — 榜单页 + REST API（注册/提交/查询）。
- **R2** (`livets-snapshots`): 状态（`state/*.json`）、原始提交（`submissions/<round>/<model>.json`，不可覆盖）、数据快照与 SHA-256 manifest。
- **D1**: schema 已就绪（`schema.sql`），但当前 `CLOUDFLARE_API_TOKEN` 无 D1 权限，暂用 R2 JSON 状态（流量极低，语义等价）；token 补权限后按 `schema.sql` 迁移。

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 榜单 HTML |
| GET | `/api/leaderboard` | 已发布成绩 JSON |
| GET | `/api/rounds` | round 日程/状态 |
| POST | `/api/register` | `{model, release_date}`，一次性注册，release date 不可改 |
| POST | `/api/submit` | 提交预测（格式见 `docs/round-0.md`），每模型每 round 一次 |

校验：分位数档位 ∈ {0.1..0.9}、必须含 0.5、horizon=14、有限值；round 状态与截止时间；release date 与注册一致。

## 部署

wrangler 需要 R2/D1 API 权限；当前 token 只有 Workers Scripts 权限，故用 REST API 直传：

```bash
curl -X PUT "https://api.cloudflare.com/client/v4/accounts/<ACCOUNT_ID>/workers/scripts/livets-leaderboard" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -F "metadata=@meta.json;type=application/json" \
  -F "index.js=@src/index.js;type=application/javascript+module"
```

`meta.json`: `{"main_module":"index.js","compatibility_date":"2026-07-01","bindings":[{"type":"r2_bucket","name":"SNAPSHOTS","bucket_name":"livets-snapshots"}]}`
