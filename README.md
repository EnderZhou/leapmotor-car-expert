# 零跑汽车专家

基于公开资料的零跑车型知识 Skill 与 WorkBuddy 专家。当前版本 **v0.2.0**，整理 C10、C11、C16 的 2027 款共 17 个版本，帮助用户查询、比较和理解公开信息。**本项目为独立社区项目，不代表零跑汽车官方服务或授权。**

## 下载与使用

`packages/v0.2.0/` 下有三种包：

- `leapmotor-car-expert.zip`：标准 Agent Skill 包，入口为 `SKILL.md`。按目标 Agent 的 Skill 安装说明导入。
- `leapmotor-car-expert-workbuddy-skill.zip`：WorkBuddy 技能格式，可通过 WorkBuddy 技能上传入口导入。
- `leapmotor-car-expert-workbuddy.zip`：WorkBuddy 单专家包，内含技能、公开资料和原创头像。按 WorkBuddy 开放平台专家包流程导入。

每个版本均提供 SHA256 校验值，见 [SHA256SUMS.txt](SHA256SUMS.txt)；构建与检查记录见 [package-validation-v0.2.0.txt](package-validation-v0.2.0.txt)。v0.1.0 的三个包保留在 `packages/` 原处，未改动。

## 能回答什么

- 查询已整理车型的指导价、动力、续航口径、补能、尺寸与公开配置。
- 比较年款、纯电／增程与配置等级，按预算和补能条件说明取舍。
- 解释公开功能资料，区分官方介绍、媒体内容、车主个体体验和分析意见。
- 对价格、权益、OTA 和在售状态等易变信息提示现场核验，并标注资料日期。
- 来源冲突时并列展示双方数值，不按多数来源判定；资料不足时直说「未确认」。

## 数据来源与口径

17 个版本的全国指导价已由零跑中国官方车型页与汽车之家配置库双向核对，核对日期 2026-11-11。汽车之家、太平洋汽车、易车等作参数与交叉核对补充；经销商页面与门店行情只作单点记录，不当官方政策。

`sources.json` 为每条来源标注 `read_status`，区分本轮实际读到哪一层内容（`full-text`／`partial`／`shell-only`／`blocked`）。已知的未确认字段与 10 处来源冲突，见 [资料缺口与变更清单](docs/v0.2.0-资料缺口与变更清单.md) 与各车型资料。第三方内容与权利边界见 [第三方来源说明](THIRD_PARTY_NOTICES.md)。

C11 阅读入口使用 [零跑 C11 官方车型页](https://www.leapmotor.cn/C11.html)；.com 域名入口（`https://www.leapmotor.com/C11.html`）在中国境内可访问，但本次读取工具仍未读到正文，两入口分别标注，不互相替代。

## 覆盖范围与边界

已覆盖 C10 2027 款 4 版、C11 2027 款 5 版、C16 2027 款 8 版。**不是零跑全系数据库**，也不覆盖上述车系的其他年款、选装包完整清单、车主手册、故障码与售后维修。

只处理公开车型知识，不读取零跑账号或实时车辆数据，不定位，不执行车控，不提供未经官方手册支持的菜单步骤、故障诊断或维修指令。

## 验证状态

- 离线结构检查：通过（三包 static_validation=passed，SHA256 已核对）。
- 离线回归测试：42 题，40 通过、2 部分通过、0 失败，通过率 95.2%；版本准确、安全隐私、引用覆盖三项硬门槛通过。详见 [执行记录](tests/offline-regression-v0.2.0.md)。
- **WorkBuddy 客户端实测：未执行。** 未在客户端导入、召唤、跑 10 题实测，未提交市场审核，未发布 Release。结构检查通过不代表平台接受或回答准确。

## 项目结构

- `source/leapmotor-car-expert/`：通用 Skill 源码及随包车型资料。
- `packages/`：v0.1.0 三个包；`packages/v0.2.0/`：当前版本三个包与构建报告。
- `test-cases.md`：42 题验收测试集（含判定规则）。
- `tests/offline-regression-v0.2.0.md`：逐题执行记录。
- `docs/`：资料缺口清单、交付摘要。
- `package-validation-v0.2.0.txt`：本轮构建与结构检查结果及未验证阶段。

## 许可证

MIT 许可证适用于本仓库自行编写的技能指令、专家提示词、配置和资料整理。第三方网页、商标及其他权利由其各自权利人保留，详见 [LICENSE](LICENSE) 和 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 反馈

欢迎通过 GitHub Issues 报告资料链接失效、车型版本混淆或技能包导入问题。提交时请描述地区、车系、年款／配置和资料日期，不要提交车主账号、验证码、车辆识别号、定位或其他个人车辆信息。
