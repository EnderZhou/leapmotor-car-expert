# 零跑汽车专家 Skill｜0.4.0

基于公开网页资料的非官方车型知识助手。已整理 C10、C11、C16 的 2027 款共 17 个版本（中国市场）；不是零跑全系数据库。

## 使用范围

车型与配置查询、年款与版本比较、差价构成解释、辅助驾驶可用性说明、按预算与补能条件整理候选、含购置税的落地成本估算、试驾与订车核验清单。

## 先查这几张表

| 想知道什么 | 查哪张 |
|---|---|
| 某版本的价格、续航、电池、功率、补能、尺寸、座位 | `references/trim-comparison.md` |
| 贵一万元买到什么、五座六座差在哪、增程比纯电贵多少 | `references/trim-deltas.md` |
| 激光雷达版能不能用某项功能、是否需 OTA | `references/adas-matrix.md` |
| 落地多少钱、购置税怎么算、补贴能不能叠 | `references/purchase-cost.md` |
| 能不能装桩、冬天高速能跑多远 | `references/charging-and-range.md` |
| 一家人怎么试、婴儿车放不放得下 | `references/family-test-drive.md` |
| 质保、用车成本、订车交车 | `references/ownership-and-order.md` |
| 新手选车、不知道看哪款 | `references/buyer-intake.md` |

## 其他资料

- 回答规则与工作流程：`SKILL.md`
- 车型叙事（边界、冲突、不能得出的结论）：`references/model-c10.md`、`model-c11.md`、`model-c16.md`、`model-index.md`
- 场景回答骨架与六项自检：`references/answer-patterns.md`
- 口径术语：`references/glossary.md`
- 来源索引、读取状态与级别：`references/sources.json`
- 引用、级别与冲突处理规则：`references/source-policy.md`
- 逐字段事实记录（244 条，17 个版本）：`references/fact-records.json`

## 资料状态

17 个版本的价格按来源级别标注：**L1** 15 个（官方车型页可复现，且配置库一致）、**L1\*** 2 个（C11 增程，官方页读到过但独立复核未重现，另有配置库与第二来源支持）。引用 L1\* 时须说明该限制，不得称“官方双向核对”；差异原因未确认，不要替它编技术解释。

38 条来源，`read_status` 区分本轮实际读取深度：`full-text`／`partial`／`shell-only`／`blocked`。汽车之家配置页直接抓取只返回页面框架，配置字段来自搜索索引渲染的正文，已在对应来源注明。`yiche-c11-config-2027` 的 URL 只到移动站首页，属**间接证据**，已在来源条目与矩阵中标注。

未确认字段与来源冲突逐项记录在各车型文档与矩阵中，回答时须如实披露，不得补值。三态严格区分：有／无／**未确认**（未确认不等于没有）。来源矛盾且无法裁决的列为**争议项**，不作加价理由。

`trim-comparison.md` 由 `fact-records.json` 生成，请勿手改；改数值请走仓库里的 `scripts/facts.py`。

## 发布状态

源码与三类客户端包均已生成并通过离线结构检查。**未**在 WorkBuddy 客户端实测导入、召唤，**未**提交市场审核，不能视为已上架或官方授权产品。

## 已知缺口

质保条款原文、官方服务网点实时信息、软件订阅与免费期、订车合同条款四类资料未收录，相关问题只能给核验清单与查询入口，不能给条款与费用。

MIT 许可证仅覆盖本项目原创技能指令、资料整理与配置文件；第三方网页、图片、商标和其他权利不在本许可范围内。第三方页面保留原文链接，仅整理必要摘要。对外发布者应复核所采用的第三方资料使用方式。
