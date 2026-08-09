# 污染增益分析（LiveTS × P2 对接表）

skill = geo-MASE(model)/geo-MASE(seasonal naive)，共享洁净窗口；<1 越小越好。
legacy 列由 P2 污染审计项目按发表数字/官方榜单填入（必须带引用），本脚本不虚构。
gain = skill_legacy − skill_live：负值表示 legacy 上的相对优势大于 LiveTS 洁净窗口上的优势，
其量级是「污染 + 社区过拟合」收益的上界估计。

| 模型 | 洁净共享窗口 | skill_live (LiveTS) | skill_legacy (P2 填入) | gain |
|---|---|---|---|---|
| chronos-bolt-small | 2460 | 0.754 | TBD (P2) | TBD |
| chronos-bolt-base | 2460 | 0.756 | TBD (P2) | TBD |
| chronos-t5-small | 2460 | 0.809 | TBD (P2) | TBD |
| time-moe-50m | 2460 | 0.85 | TBD (P2) | TBD |
| moirai-1.1-r-small | 2460 | 0.817 | TBD (P2) | TBD |
| timesfm-2.5-200m | 820 | 0.707 | TBD (P2) | TBD |

生成：`scripts/contamination_gain.py`，输入 `matrix-expanded-all.jsonl`。
