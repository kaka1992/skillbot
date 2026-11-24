# index.md — 风控知识库总目录（路由表）

> 供 orientation 快速定位。字段完整清单见 `manifest.json`；类目/约定见 `SCHEMA.md`。

当前收录 **13 篇**（含指标口径 12 篇）。空类目 6 个占位待补。

## _global（元层）
- [全局约束与可信规则](_global/constraints.md) — 问题类型判断 + 可信规则 + 输出纪律，检索作答第一步必读

## 01_风控总览
- [3DS2.0分享](01_风控总览/3DS2.0分享.md) — 介绍 3DS2.0 的原理、实现流程、优势及未来演进方向
- [CheckPoint列表](01_风控总览/CheckPoint列表.md) — 汇总 PIPO 各业务场景的风控 CheckPoint 点位、事件与上游服务
- [PIPO 支付风控核心指标口径 One Pager](01_风控总览/PIPO支付风控核心指标口径OnePager.md) — 定义 PIPO 支付风控核心指标（拦截率/资损率/净资损率/ATO 等）的口径与计算逻辑
- [国际支付账号体系介绍 GP Account System Introduction（2024.06）](01_风控总览/国际支付账号体系介绍.md) — 介绍国际支付(GP)账号体系模型、标识定义、功能现状与迭代规划

## 02_业务场景
- [GPP-TikTok Live业务线分享//GPP-TikTok Live sharing](02_业务场景/GPP-TikTokLive业务线分享.md) — 介绍TikTok直播打赏体系及官网充值、主播提现、周期性打款、订阅等场景与PIPO支付能力
- [GPP- TikTok Local Service Sharing](02_业务场景/GPP-TikTokLocalService分享.md) — 介绍TikTok本地生活服务开环/闭环模式、券商品形态及与PIPO在印尼泰国的合作方案
- [GPP-电商业务线分享|E-commerce Introduction](02_业务场景/GPP-电商业务线分享.md) — 介绍TikTok Shop电商业务模式、角色分工、支付能力及各国市场展业与PIPO合作方案

## 03_风险类型
- [TTS ROW交易黑标V3](03_风险类型/TTS-ROW交易黑标V3.md) — 电商ROW交易黑标V3：统一一度外扩评估口径，标准化银行返回码，覆盖扩至3-4倍
- [TTS ROW交易黑标V4](03_风险类型/TTS-ROW交易黑标V4.md) — 电商ROW交易黑标V4：以一度外扩反推评估准确度，收紧规则并提纯，覆盖扩至3倍
- [EU TTS Payment Risk 黑标V4](03_风险类型/外链-D1xBdCDDnoq2.md) — EU/UK电商黑标V4：来源逻辑精细化+双重验证排白，UK/EU bad rate提升至36%
- [直播黑白标签定义和False Positive分析 TTLive Bad Tagging Definition and False Positive Analysis](03_风险类型/直播黑白标签定义与FP分析.md) — 直播黑白标签基于黑白种子强介质关联传播打5级标签，并用于已拦截交易FP分析
- [黑白标优化](03_风险类型/黑白标优化.md) — 更适合拦截模型训练/评估的黑白标：黑种子剔FF，仅1度关联，简化EVIL/ANGEL打标

## 04_规则与策略
- [智能规则优化](04_规则与策略/智能规则优化.md) — 面向策略专家的规则调优与规则生成组件化方案：标准库+特征库+约束优化+专家决策

## 05_攻防对抗
_（预留空目录，源索引暂无文档）_

## 06_模型建设
_（预留空目录，源索引暂无文档）_

## 07_平台能力
_（预留空目录，源索引暂无文档）_

## 08_监控运营
_（预留空目录，源索引暂无文档）_

## 09_合规治理
_（预留空目录，源索引暂无文档）_

## 10_复盘案例
_（预留空目录，源索引暂无文档）_
