# 零跑汽车专家

基于公开资料的零跑车型知识 Skill 与 WorkBuddy 专家。当前版本 **v0.4.0**，覆盖 C10、C11、C16 的 2027 款共 17 个版本（中国市场）。**本项目为独立社区项目，不代表零跑汽车官方服务或授权。**

## 下载与使用

`packages/v0.4.0/` 下有三种包：

- `leapmotor-car-expert.zip`：标准 Agent Skill 包，入口为 `SKILL.md`。
- `leapmotor-car-expert-workbuddy-skill.zip`：WorkBuddy 技能格式，可通过技能上传入口导入。
- `leapmotor-car-expert-workbuddy.zip`：WorkBuddy 单专家包，内含技能、公开资料和原创头像。

校验值见 [SHA256SUMS.txt](SHA256SUMS.txt)，构建记录见 [package-validation-v0.4.0.txt](package-validation-v0.4.0.txt)。v0.1.0、v0.2.0、v0.3.0 的历史包保留在原处，未被覆盖。

## 能回答什么

- 查 17 个版本的价格、续航（CLTC／WLTC）、电池、功率、补能、尺寸、座位。
- 算差价：贵一万元买到哪些具体配置、五座六座差在哪、增程比纯电贵多少。
- **算落地成本**：含 2026—2027 年购置税减半（每辆上限 1.5 万元）的税额计算、保险与上牌待核项、贷款总支出比较。
- **按预算筛候选**：先问裸车还是落地、是否硬上限；超预算的车型只作标注差额的备选，不当合格推荐。
- **判断补能是否可行**：家充四道门（车位／物业／电力／施工）、公共桩时间成本、长途补能估算。
- 解释辅助驾驶：硬件有什么、官方说支持什么、是否已交付——三层分开，不混为一谈。
- 给试驾与订车清单：家庭成员实车验证、座椅与行李、同版本辅助驾驶试驾、合同与验车核对。
- 资料不足直说“未确认”，来源冲突并列展示并注明冲突类型。

## 主要资料文件

| 想知道什么 | 查哪个 |
|---|---|
| 版本参数 | [trim-comparison.md](source/leapmotor-car-expert/references/trim-comparison.md)（由事实记录生成） |
| 差价与配置增量 | [trim-deltas.md](source/leapmotor-car-expert/references/trim-deltas.md) |
| 辅助驾驶可用性 | [adas-matrix.md](source/leapmotor-car-expert/references/adas-matrix.md) |
| 落地成本与购置税 | [purchase-cost.md](source/leapmotor-car-expert/references/purchase-cost.md) |
| 家充与续航 | [charging-and-range.md](source/leapmotor-car-expert/references/charging-and-range.md) |
| 家庭适配与试驾 | [family-test-drive.md](source/leapmotor-car-expert/references/family-test-drive.md) |
| 质保、保养、订车 | [ownership-and-order.md](source/leapmotor-car-expert/references/ownership-and-order.md) |
| 新手选车入口 | [buyer-intake.md](source/leapmotor-car-expert/references/buyer-intake.md) |

## 数据来源与口径

17 个版本的价格按**来源级别**标注：

- **L1（15 个版本）**：零跑中国官方车型页可复现，且配置库数值一致（C10 4 版、C11 纯电 3 版、C16 8 版）。
- **L1\*（2 个版本）**：C11 增程两款。官方页读到过这两档价格，但另一人独立复核时只重现纯电三档。**原因是未确认的**，可能涉及缓存或 CDN、页面版本、请求参数、前端渲染方式，也可能其中一次提取不完整；现有材料没有响应体或截图，不足以定位原因。这两档另有配置库与第二来源支持，因此标 L1\*，**不能表述为“17 个版本均由官方双向核对”**。

级别只作用于价格。电池、芯片、续航等字段各有独立状态，不能继承价格的级别。

`sources.json` 共 **38 条**来源，每条标 `read_status`（full-text／partial／shell-only／blocked）。逐字段的事实记录在 `references/fact-records.json`（**244 条**，17 个版本），由 `scripts/facts.py` 生成并校验；配置矩阵是它的派生视图，`check` 会拒绝过期矩阵。官方页面采集元数据与差异说明见 [证据文件](docs/evidence/2026-11-11-官方页面采集摘录.md)。

已知未确认字段与来源冲突逐项记录在各车型文档。v0.2.0 与 v0.3.0 的记录错误已在 [勘误记录 v0.2.0](docs/勘误记录-v0.2.0.md) 与 [勘误记录 v0.4.0](docs/勘误记录-v0.4.0.md) 中说明并修正。

## 覆盖范围与边界

已覆盖 C10 2027 款 4 版、C11 2027 款 5 版、C16 2027 款 8 版。**不是零跑全系数据库**，也不覆盖其他车系、其他年款、选装包完整清单与当前价格、车主手册、故障码与售后维修。质保条款原文、服务网点实时信息、软件订阅价格、订车合同模板**均未收录**。

不读取零跑账号或实时车辆数据，不定位，不执行车控，不提供未经手册支持的菜单步骤、故障诊断或维修指令。不承诺交付时间、优惠幅度、OTA 时间表或辅助驾驶开通范围。

## 验证状态

三个指标分开看，不能加总：

| 指标 | 结果 | 说明 |
|---|---|---|
| 事实正确性（80 题） | 80/80 | 衡量“资料是否足以支撑预期答案”，不是模型实际输出 |
| 需求完成度（26 题适用） | **22/26 = 84.6%，未达 90% 门槛** | 缺口集中在质保条款、服务网点、软件订阅、订车合同四类；B 组 16/20 |
| 客户端运行 | **未执行** | 8 功能 + 8 安全 + 3 多轮 + 2 注入，见清单 |

| 其他检查 | 状态 |
|---|---|
| 离线结构与一致性检查 | 通过：三包 static_validation=passed，事实记录校验 PASS，SHA256 一致 |
| 25 条事实独立复核 | **未执行**，表格见 [工作表](tests/independent-review-worksheet-v0.4.0.md) |
| Git 推送 / tag / Release | 未执行 |

**v0.3.0 记录的 58/60、96.7% 已撤回**：其中 6 道题的预期答案本身是错的，详见 [勘误记录 v0.4.0](docs/勘误记录-v0.4.0.md)。

离线回归由构建者自评，且预期与资料出自同一批人，存在同错风险。**在独立复核与客户端实测完成前，本版本不称“验收通过”。**

## 项目结构

- `source/leapmotor-car-expert/`：通用 Skill 源码与 **17 个**参考资料文件（含 `fact-records.json`）。
- `packages/`：v0.1.0／v0.2.0／v0.3.0 历史包；`packages/v0.4.0/`：当前版本三包与构建报告。
- `scripts/facts.py`：事实记录生成与一致性检查（`build`／`render`／`check`／`all`）。
- `test-cases.md`：80 题验收测试集（60 回归 + 20 购车场景）。
- `tests/`：离线回归记录、独立复核工作表、客户端实测清单。
- `docs/`：资料缺口清单、勘误记录、交付摘要、官方页面采集摘录。

## 许可证

MIT 许可证适用于本仓库自行编写的技能指令、专家提示词、配置与资料整理。第三方网页、商标及其他权利由其各自权利人保留，详见 [LICENSE](LICENSE) 与 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 反馈

欢迎通过 GitHub Issues 报告资料链接失效、版本混淆或包导入问题。提交时请描述地区、车系、年款／配置与资料日期，不要提交车主账号、验证码、车辆识别号、定位或其他个人车辆信息。
