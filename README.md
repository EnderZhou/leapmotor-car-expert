# 零跑汽车专家

基于公开资料的零跑车型知识 Skill 与 WorkBuddy 专家。首版整理 C10、C11、C16 的部分车型和配置资料，帮助用户查询、比较和理解公开信息。**本项目为独立社区项目，不代表零跑汽车官方服务或授权。**

## 下载与使用

[下载页](https://github.com/EnderZhou/leapmotor-car-expert/releases)附有三种包：

- `leapmotor-car-expert.zip`：标准 Agent Skill 包，入口为 `SKILL.md`。按目标 Agent 的 Skill 安装说明导入。
- `leapmotor-car-expert-workbuddy-skill.zip`：WorkBuddy 技能格式。可通过 WorkBuddy 的技能上传入口导入。
- `leapmotor-car-expert-workbuddy.zip`：WorkBuddy 单专家包，内含技能、公开资料和原创头像。按 WorkBuddy 开放平台专家包流程导入；本项目尚未经过客户端导入或市场审核。

每个版本均提供 SHA256 校验值。详见 [SHA256SUMS.txt](SHA256SUMS.txt) 与 [构建记录](package-validation.txt)。

## 能回答什么

- 查询已整理车型的动力、版本和部分公开配置。
- 比较年款、纯电／增程与车型版本，按用户的预算和补能条件说明取舍。
- 解释公开功能资料，区分官方介绍、媒体内容、车主个体体验和分析意见。
- 对价格、权益、OTA 和车型状态等易变信息提示现场核验，并标注资料日期。

## 资料范围

目前深入整理 C10、C11、C16 的部分资料，不是零跑全系数据库。车型参数、价格和功能随地区、年款、配置与软件状态变化，实际购车应核对对应地区的官方配置表。

C11 阅读入口使用项目维护者在中国验证可访问的 [零跑 C11 车型页](https://www.leapmotor.com/C11.html)；中国区参数交叉核对还列有 [零跑中国 C11 参数页](https://leapmotor.cn/parameter-pk-web.html?carTypeId=3&platform=web)。域名访问与页面渲染可能随地区和网络路径不同，两个来源分别标注，不能相互替代。

资料来源索引见 [`sources.json`](source/leapmotor-car-expert/references/sources.json)，内容与权利边界见 [第三方来源说明](THIRD_PARTY_NOTICES.md)。

## 能力边界

本项目只处理公开车型知识，不读取零跑账号或实时车辆数据，不执行车控，不提供未经官方手册支持的菜单步骤、故障诊断或维修指令。用户手册与故障排障资料留待后续在获得可合法使用的来源后补充。

WorkBuddy 包已通过本地结构检查；尚未在 WorkBuddy 客户端实际导入、召唤或提交市场审核。结构检查通过不代表平台已接受或发布。

## 项目结构

- `source/leapmotor-car-expert/`：通用 Skill 源码及随包车型资料。
- `packages/`：三个面向不同入口的 ZIP 和各自构建报告。
- `test-cases.md`：建议验收问题集；题目尚未执行，不是测试通过报告。
- `package-validation.txt`：离线包检查结果及未验证阶段。

## 许可证

MIT 许可证适用于本仓库自行编写的技能指令、专家提示词、配置和辅助脚本。第三方网页、商标及其他权利由其各自权利人保留，详见 [LICENSE](LICENSE) 和 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 反馈

欢迎通过 GitHub Issues 报告资料链接失效、车型版本混淆或技能包导入问题。提交时请描述地区、车系、年款／配置和资料日期，不要提交车主账号、验证码、车辆识别号、定位或其他个人车辆信息。
