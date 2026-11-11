# 独立复核工作表｜25 个关键事实｜v0.4.0

**用途：** 交由**非本项目编写者**执行来源复核。复核人只需打开链接、看页面、判断，不需要懂零跑产品。

**状态：未执行。** 本文件是待填表格，不是复核结果。填完前不得在任何文档里写"已独立复核通过"。

## 相对 v0.3.0 的修改

1. 去掉全部"同上"，每条都给完整可点击 URL，避免复核人跳错页面。
2. 第 12、13 条来源只到易车移动站首页，**明确标为间接证据**，复核结果里单列。
3. 第 20 条来源是公众号转载，原始出处未确认，单列。
4. 汇总口径改为分别报告**计划／可核验／支持／反证／版本不明／无法读取**，不再用"支持÷可读取"，避免"只读到 2 条、2 条都对就 100%"。

## 怎么填

对每一条：

1. 打开该行的完整 URL，看页面现在能不能读到正文。
2. 找页面上有没有这条数值或说法，且**是否针对同一版本**（年款、动力形式、座位数）。
3. 页面是否写了限制（如"非全系标配""以配置表为准""指导价为全国统一价"）。
4. "复核判定"填一项：`支持` ／ `反证` ／ `版本不明` ／ `无法读取`。

判定口径：

- **支持**：页面明确写出该数值／说法，版本一致。
- **反证**：页面写了，但数值或适用范围不同（不是"我印象里不是这样"）。
- **版本不明**：页面上有该数据，但看不出对应哪年款／配置／座位数。
- **无法读取**：打不开、要登录、只返回导航页脚框架，或 URL 只到首页。

## 复核记录

| # | 事实主张 | 适用版本 | 来源 ID | 完整 URL | 可读性 | 是否直接支持 | 页面是否声明限制 | 复核判定 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | C10 290 智享版指导价 12.58 万元 | C10 2027 增程 | official-c10-page | https://www.leapmotor.cn/C10.html | | | | | |
| 2 | C10 660 智享版指导价 13.28 万元 | C10 2027 纯电 | official-c10-page | https://www.leapmotor.cn/C10.html | | | | | |
| 3 | C10 增程 CLTC 290 km、WLTC 190 km | C10 2027 增程 | autohome-c10-config-2027 | https://www.autohome.com.cn/config/series/7382.html | | | | | |
| 4 | C10 纯电电池 81.9 kWh | C10 2027 纯电 | yiche-c10-config-2027 | https://car.m.yiche.com/lingpaob11/m166506/ | | | | | |
| 5 | C10 增程电池 38.7 kWh | C10 2027 增程 | yiche-c10-config-2027 | https://car.m.yiche.com/lingpaob11/m166506/ | | | | | |
| 6 | C10 轴距 2825 mm | C10 2027 | zjchewang-c10-discount | http://www.zjchewang.com/html/news/20261028/676877_1.html | | | | | |
| 7 | C10 后备箱 510–1809 L | C10 2027 | yiche-c10-config-2027 | https://car.m.yiche.com/lingpaob11/m166506/ | | | | | |
| 8 | C10 智享版 14 个 PSS、激光雷达版 18 个 | C10 2027 增程两款 | yoojia-c10-trim-diff | https://www.yoojia.com/article/9417727368469186838.html | | | | | 两文同源转载，不算独立验证 |
| 9 | C11 640 智享版指导价 14.38 万元 | C11 2027 纯电 | official-c11-page-cn | https://www.leapmotor.cn/C11.html | | | | | |
| 10 | C11 增程 300 激光雷达版指导价 14.38 万元 | C11 2027 增程 | official-c11-page-cn | https://www.leapmotor.cn/C11.html | | | | | 本库标 L1\*，读到与否都请如实记录 |
| 11 | C11 轴距 2930 mm | C11 2027 | official-c11-page-cn | https://www.leapmotor.cn/C11.html | | | | | |
| 12 | C11 纯电电池 81.9 kWh | C11 2027 纯电 | yiche-c11-config-2027 | https://car.m.yiche.com/ | | | | | **URL 只到移动站首页，属间接证据**；读不到车款页请记"无法读取" |
| 13 | C11 增程电池 41.7 kWh | C11 2027 增程 | yiche-c11-config-2027 | https://car.m.yiche.com/ | | | | | 同上，间接证据 |
| 14 | C11 激光雷达为禾赛 AT128、128 线、1 颗 | C11 2027 纯电激光雷达版 | autohome-c11-config-2027 | https://www.autohome.com.cn/config/series/5205.html | | | | | 该页覆盖范围若只有纯电，不能外推到增程 |
| 15 | C11 纯电后备箱 537–1203 L | C11 2027 纯电 | autohome-c11-config-2027 | https://www.autohome.com.cn/config/series/5205.html | | | | | 另有 523 L 说法，见 modiauto-c11-14799：https://m.modiauto.com.cn/xuanche/m_14799.html |
| 16 | C11 纯电版全系搭载热泵空调 | C11 2027 纯电 | official-c11-page-cn | https://www.leapmotor.cn/C11.html | | | | | |
| 17 | C16 增程 280 激光雷达智尊版六座 16.28 万元 | C16 2027 增程 6 座 | official-c16-page-cn | https://www.leapmotor.cn/C16.html | | | | | |
| 18 | C16 纯电 630 尊享版五座 15.28 万元 | C16 2027 纯电 5 座 | official-c16-page-cn | https://www.leapmotor.cn/C16.html | | | | | |
| 19 | C16 增程电池 38.9 kWh | C16 2027 增程 | autohome-c16-config-2027 | https://www.autohome.com.cn/config/series/7674.html | | | | | |
| 20 | C16 纯电电池 81.9 kWh | C16 2027 纯电 | weixin-c16-guide | http://mp.weixin.qq.com/s?__biz=MzA4NTM1NzIzNw==&mid=2649497268&idx=1&sn=1fbe3625e3cc926ecaf6bd91e15adde2 | | | | | 公众号转载，**发布方与原刊出处未确认**；若页面标注了原始出处请抄录 |
| 21 | C16 轴距 2825 mm | C16 2027 | sina-c16-2027 | https://k.sina.cn/article_7879996685_1d5af350d06802gvl2.html | | | | | |
| 22 | C16 车长 4925 mm | C16 2027 | autohome-c16-config-2027 | https://www.autohome.com.cn/config/series/7674.html | | | | | 另有 4915 说法：https://youjia-pc.bdstatic.com/article/10017307573517102205.html |
| 23 | C16 增程 CLTC 综合续航 1230 km | C16 2027 增程 | autohome-c16-config-2027 | https://www.autohome.com.cn/config/series/7674.html | | | | | |
| 24 | C16 激光雷达智尊版比尊享版贵 1.4 万元 | C16 2027 | weixin-c16-guide | http://mp.weixin.qq.com/s?__biz=MzA4NTM1NzIzNw==&mid=2649497268&idx=1&sn=1fbe3625e3cc926ecaf6bd91e15adde2 | | | | | 同第 20 条来源 |
| 25 | 官方声明"配置非全系标配，部分辅助驾驶功能仅激光雷达版、可能需后续 OTA" | C16 全系 | official-c16-page-polymerization | https://www.leapmotor.cn/C16-polymerization.html | | | | | |

## 附加 2 条（政策类，供交叉确认）

| # | 事实主张 | 来源 ID | 完整 URL | 复核判定 | 备注 |
|---|---|---|---|---|---|
| 26 | 2026-01-01 至 2027-12-31 新能源汽车购置税减半，每辆乘用车减税额不超过 1.5 万元 | cn-tax-2023-no10 | https://szs.mof.gov.cn/zhengcefabu/202306/t20230620_3891500.htm | | 财政部／税务总局／工信部公告 2023 年第 10 号 |
| 27 | 购置日期按机动车销售统一发票开具日期确定 | cn-tax-shanghai-qa-2026 | https://shanghai.chinatax.gov.cn/bsfw/nszx/hdfk/202602/t479413.html | | 地方税务机关答复，作地方口径参考 |

## 汇总（复核人填写）

**分母必须用 25／27，不能只用"可读取"当分母。** 读不到也是复核结果的一部分。

| 项目 | 结果 |
|---|---|
| 复核人（非编写者） | |
| 复核日期 | |
| 复核环境（地区／是否登录／浏览器或工具） | |
| 计划复核条数 | 25（政策附加 2 条单列） |
| 可核验条数（支持＋反证＋版本不明） | /25 |
| 支持 | /25 |
| 反证 | /25 |
| 版本不明 | /25 |
| 无法读取 | /25 |
| 覆盖率（支持 ÷ 25） | |
| 有条件覆盖率（支持 ÷ 可核验） | |
| 间接证据条数（第 12、13 条） | /2 是否读到 |
| 转载来源条数（第 20、24 条） | /2 是否能看到原始出处 |

**门槛：** 要求"支持 ÷ 25 ≥ 98%"。25 条的 98% 是 24.5，所以实际必须 **25/25**；24/25 只有 96%，不达标。

凡出现"反证"，回到资料修正结论，不改判定迁就文档。凡"无法读取"超过 3 条，视为来源可复核性不足，须补直接链接或换来源，不靠"读不到就算过"。

## 给复核人的提示

- 官方页面是动态渲染的。C11 页面分"纯电／增程"两组，不同工具可能只返回一组。遇到这种情况记"无法读取"，**不要记"反证"**——本库已因此把增程价格标为 L1\*。
- 汽车之家配置页直接打开需滚动加载，若只看到导航与页脚，记"无法读取"。
- 第 12、13 条的 URL 是易车移动站首页，本身无法直达车款页。这一条请在备注里如实写"URL 不可直达"，**不要因为找不到就说数值错**。
- 不需要判断哪个数值更合理，只判断页面有没有这么写。
