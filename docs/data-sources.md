# LiveTS 数据源清单（M0）

> 选型要求：免费或免 key 可长期采集、更新频率 ≥ 日级、每域至少 1 个冗余备选。
> 状态标注：✅ = 已在采集器中实现并本机跑通（2026-08-03 验证）；🔁 = 备选（部分已实现未默认启用）。

| 域 | 主源 | API / 免key | 频率 | 状态 | 备选源 |
|---|---|---|---|---|---|
| 能源 | 英国 NESO Historic Demand（CKAN datastore） | `api.neso.energy`，免 key | 30min | ✅ | 🔁 德国 SMARD（`smard.de/app/chart_data`，免 key，电价/负荷/发电，已实现 parser）；EIA v2（免费 key） |
| 气象 | Open-Meteo Forecast API（多站点气温/风速/降水） | `api.open-meteo.com`，免 key | 1h | ✅ | 🔁 US NWS `api.weather.gov`（免 key）；Open-Meteo Archive（历史回填，已用于 pilot eval） |
| 加密货币/外汇 | Coinbase Exchange candles（BTC-USD 等） | `api.exchange.coinbase.com`，免 key | 1d（可到 1min） | ✅ | 🔁 OKX/Kraken 公共行情（免 key；Binance 在部分地区受限已验证）；外汇主源 Frankfurter（ECB 参考汇率，免 key）✅，备选 ECB SDW CSV |
| 空气质量 | Open-Meteo Air Quality（PM2.5/PM10/O3，多城市） | `air-quality-api.open-meteo.com`，免 key | 1h | ✅ | 🔁 OpenAQ v3（免费 key）；WAQI（免费 token） |
| 交通 | 纽约 MTA Daily Ridership（Socrata 开放数据） | `data.ny.gov`，免 key | 1d | ✅ | 🔁 其他 Socrata 城市开放数据（西雅图自行车计数器等，同一 parser 即可复用） |
| 网络流量 | Wikimedia Pageviews REST API（每日条目访问量） | `wikimedia.org/api/rest_v1`，免 key（需 UA） | 1d（滞后 1–3 天） | ✅ | 🔁 Cloudflare Radar API（现有 token 可用）；互联网交换中心（AMS-IX/DE-CIX）流量统计 |

## 采集语义（PIT）
- 每次采集把 API 原始响应**逐字节快照**到 `raw/{domain}/{source_id}/{date}/{ts}.json`，附 `collected_at` 时间戳。
- 解析后的 tidy 记录（series_id/timestamp/value/collected_at）追加写入 `tidy/{domain}/{source_id}.csv`，加载时按 (series_id, timestamp) 取最早 collected_at 去重，实现 as-of 语义（数据修订可追溯）。
- 已知数据滞后：Wikimedia 1–3 天（采集器自动回退 end date）；MTA 约 1–2 天；NESO 按半小时结算周期滚动发布。

## 扩容到 ≥200 条序列的路径（M0 目标）
- Open-Meteo 站点从 5 → 50+（气象 150+ 序列）、空气质量城市 4 → 30+；
- Coinbase 交易对 1 → 20+；Frankfurter 已含 29 币种；
- Wikimedia 条目 4 → 50+；MTA 14 条 + 其他城市 Socrata 数据集。
仅需修改 `configs/sources.yaml`，无需改代码。
