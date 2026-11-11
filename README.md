# 零跑汽车专家

基于公开资料的零跑车型知识 Skill 与 WorkBuddy 专家。当前版本 **v0.3.0**，覆盖 C10、C11、C16 的 2027 款共 17 个版本（中国市场）。**本项目为独立社区项目，不代表零跑汽车官方服务或授权。**

## 下载与使用

`packages/v0.3.0/` 下有三种包：

- `leapmotor-car-expert.zip`：标准 Agent Skill 包，入口为 `SKILL.md`。
- `leapmotor-car-expert-workbuddy-skill.zip`：WorkBuddy 技能格式，可通过技能上传入口导入。
- `leapmotor-car-expert-workbuddy.zip`：WorkBuddy 单专家包，内含技能、公开资料和原创头像。

校验值见 [SHA256SUMS.txt](SHA256SUMS.txt)，构建记录见 [package-validation-v0.3.0.txt](package-validation-v0.3.0.txt)。v0.1.0、v0.2.0 的历史包保留在原处，未被覆盖。

## 能回答什么

- 查 17 个版本的价格、续航（CLTC／WLTC）、电池、功率、补能、尺寸、座位。
- 算差价：贵一万元买到哪些具体配置、五座六座差在哪、增程比纯电贵多少。
- 解释辅助驾驶：硬件有什么、官方说支持什么、是否已交付——三层分开，不混为一谈。
- 按预算、补能条件、乘坐需求整理候选，并说明建议成立的前提。
- 对价格、权益、OTA、在售状态提示现场核验；资料不足直说“未确认”，来源冲突并列展示。

## 三张核心表

| 想知道什么 | 查哪张 |
|---|---|
| 版本参数 | [trim-comparison.md](source/leapmotor-car-expert/references/trim-comparison.md) |
| 差价与配置增量 | [trim-deltas.md](source/leapmotor-car-expert/references/trim-deltas.md) |
| 辅助驾驶可用性 | [adas-matrix.md](source/leapmotor-car-expert/references/adas-matrix.md) |

## 数据来源与口径

17 个版本的价格按**来源级别**标注：

- **L1（15 个版本）**：零跑中国官方车型页可复现，且配置库数值一致（C10 4 版、C11 纯电 3 版、C16 8 版）。
- **L1\*（2 个版本）**：C11 增程两款。官方页读到过这两档价格，但独立复核时只重现纯电三档；判断为标签页动态渲染所致，另有配置库与经销商页支持。引用时须说明这一限制，因此**不能表述为“17 个版本均由官方双向核对”**。

`sources.json` 共 36 条来源，每条标 `read_status`（full-text／partial／shell-only／blocked）。官方页面采集摘录见 [证据文件](docs/evidence/2026-11-11-官方页面采集摘录.md)。

已知未确认字段与来源冲突逐项记录在各车型文档；v0.2.0 的两处记录错误已在 [勘误记录](docs/勘误记录-v0.2.0.md) 中说明并修正。

## 覆盖范围与边界

已覆盖 C10 2027 款 4 版、C11 2027 款 5 版、C16 2027 款 8 版。**不是零跑全系数据库**，也不覆盖其他车系、其他年款、选装包完整清单与当前价格、车主手册、故障码与售后维修。

不读取零跑账号或实时车辆数据，不定位，不执行车控，不提供未经手册支持的菜单步骤、故障诊断或维修指令。不承诺交付时间、优惠幅度、OTA 时间表或辅助驾驶开通范围。

## 验证状态

| 项目 | 状态 |
|---|---|
| 离线结构检查 | 通过：三包 static_validation=passed，SHA256 一致 |
| 离线回归（60 题） | 58 通过、2 部分通过、0 失败，96.7%；安全 8/8。见 [记录](tests/offline-regression-v0.3.0.md) |
| 25 条事实独立复核 | **未执行**，表格见 [工作表](tests/independent-review-worksheet-v0.3.0.md) |
| WorkBuddy 客户端实测（16 题） | **未执行**，清单见 [清单](tests/client-test-checklist-v0.3.0.md) |
| Git 推送 / tag / Release | 未执行 |

离线回归由构建者自评，且题目按已有证据设计，分数偏高，不能替代独立复核与客户端实测。**在上述两项完成前，本版本不称“验收通过”。**

## 项目结构

- `source/leapmotor-car-expert/`：通用 Skill 源码与 11 个参考资料文件。
- `packages/`：v0.1.0、v0.2.0 历史包；`packages/v0.3.0/`：当前版本三包与构建报告。
- `test-cases.md`：60 题验收测试集。
- `tests/`：离线回归记录、独立复核工作表、客户端实测清单。
- `docs/`：资料缺口清单、勘误记录、交付摘要、官方页面采集摘录。

## 许可证

MIT 许可证适用于本仓库自行编写的技能指令、专家提示词、配置与资料整理。第三方网页、商标及其他权利由其各自权利人保留，详见 [LICENSE](LICENSE) 与 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 反馈

欢迎通过 GitHub Issues 报告资料链接失效、版本混淆或包导入问题。提交时请描述地区、车系、年款／配置与资料日期，不要提交车主账号、验证码、车辆识别号、定位或其他个人车辆信息。
