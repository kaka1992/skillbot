---
title: EU TTS Payment Risk 黑标V4
category: 风险类型
source_url: https://bytedance.my.larkoffice.com/docx/D1xBdCDDnoq2lyxLXnjmpPycyvV
source_token: D1xBdCDDnoq2lyxLXnjmpPycyvV
source_type: external
doc_type: 标签定义
tags: [支付风控, 交易风控, 黑标, 白标, 黑白标签, 3DS, 电商, TTS]
metrics: [bad rate, 拒付or全部失败率, 黑标准确率, 黑标量级占比]
business_lines: [电商]
summary: EU/UK电商黑标V4：来源逻辑精细化+双重验证排白，UK/EU bad rate提升至36%
last_synced: 2026-08-12
---

## 适用场景
用于 EU/UK 电商 Payin 交易场景黑样本（Bad Tag）的定义、评估与生产。V4 在 V3 统一来源体系基础上，围绕黑标来源逻辑精细化与统一排白策略升级两条主线，提升黑样本准确度并维持合理覆盖量级。（备注：源文件名标注为「裸链接」，但实际抓取到的正文内容较为完整，标题为「EU TTS Payment Risk 黑标V4」。）

## 核心概念
- 黑标来源逻辑优化：Multi-PI / Multi-UID 聚合从全量失败交易收紧为仅 fraud risk 相关失败交易，并以 DID 维度替代 UID 维度；Issuer Reject Code 精细化下钻，移除无增量 error code 并排除非 risk 流量。
- 统一排白策略升级：突破 V3 对 UID & DID Pair 成功交易验证的强依赖，最终采用「DID 且 PI 维度同时拥有良好历史」的双重验证排白标准。
- 排白介质探索：TTL 可信标签、PayPal Email 验证、DID、PI 等。
- 黑标开发集（50%用户，开发黑标）/ 黑标评估集（另外50%用户，通过设备、PI 关联并用关联用户风险表现评估）。

## 关键指标口径
- 黑标准确度以评估集中关联用户的风险表现（拒付or全部失败率 / bad rate）衡量。
- DID 维度良好历史定义：(succ_txn_num_365d − succ_txn_num_60d > 0) AND fraud_num_365d = 0。
- 效果：UK bad rate 21% → 36%，EU 17% → 36%；黑标量级 UK 约为 V3 的 81%、EU 约为 V3 的 83%。

## 规则 / 策略要点
- Multi-PI UID Risky / Multi-UID PI Risky：仅对 fraud risk 相关失败交易聚合，并以 DID 维度替代 UID 维度。
- Issuer reject code：移除无增量的「63」error code，从「59、83」继续下钻排除非 risk 的 sub_error 及 frictionless 3DS authenticated 流量。
- 最终排白：移除「DID 且 PI 维度拥有良好历史」的成功交易，双重验证兼顾黑标数量与表现。
- 黑标输出表：pipo_risk_strategy.app_risk_strategy_ecom_bad_tag_df_v4（reference_id）、app_risk_strategy_ecom_bad_tag_w_category_df（version='v4.0'）。
- V5 迭代方向：EU Issuer reject code 占比进一步下探、Solid Fraud 评估准确率 case review、整体 bad or all fail rate 提升。

## 原文正文

<!-- source_type: docx | doc_id: D1xBdCDDnoq2lyxLXnjmpPycyvV | title: 直播黑白标签定义(D1xBdC-裸链接) -->

<title>EU TTS Payment Risk 黑标V4</title>

<callout emoji="📌">
**版本亮点：准确度驱动的黑标体系升级**
本次 V4 版本在 V3 统一来源体系的基础上，围绕黑标来源逻辑精细化与统一排白策略升级两条主线，系统性提升黑样本准确度，同时维持合理的黑标覆盖量级。
- **黑标来源逻辑优化**：Multi-PI/Multi-UID 聚合逻辑从全量失败交易收紧为仅 fraud risk 相关失败交易，并以 DID 维度替代 UID 维度；Issuer Reject Code 精细化下钻，移除无增量 error code 并排除非 risk 流量
- **统一排白策略升级**：突破 V3 对 UID & DID Pair 成功交易验证的强依赖，最终采用 "DID 且 PI 维度同时拥有良好历史" 的双重验证排白标准
**样本评估与验证：**与ROW以及算法拉齐黑标准确率评估标准，系统评估每步优化的边际增益，确保最终方案兼顾质量与规模
**最终效果：** 准确度显著提升（UK bad rate 21% → 36%，EU 17% → 36%），黑标量级维持在可控范围内（UK 约为 V3 的 81%，EU 约为 V3 的 83%），issuer rejection 黑标占比进一步压降至合理水平
</callout>

# 一. 背景和目标

V3 版本已完成对不同黑标来源的统一梳理与整合，构建了层次化的黑样本架构。然而，当前体系仍面临以下核心挑战：

- **准确度量化不足**：部分来源的黑标准确度仍有提升空间，需要基于评估框架持续迭代优化
- **排白策略单一**：V3 排白逻辑强依赖 UID & DID Pair 的成功交易验证记录，排白介质有限

**V4 核心目标**：以准确度提升为主线，通过对现有来源做进一步的精细化下钻提升来源准确度，同时通过统一排白策略的升级，进一步提升黑标体系的整体准确度。



# 二. 黑标来源架构

<synced_reference src-block-id="Zj3CdFe3us4TktbdRmTmN7qBypg" src-token="KhTkd22f5ob3G4x3683mJptxyGf"></synced_reference>



# 三. V4 优化设计

- **黑标来源逻辑优化：**

  1. Multi-PI / Multi-UID 聚合逻辑改造：从全量失败交易聚合转变为仅对 fraud risk 相关失败交易进行聚合，并以 DID 维度替代 UID 维度，实现准确度提升
  
     - 从对"所有失败交易"聚焦成"跟fraud risk有关的交易" 使得聚合成果更与欺诈本质相关
     - 用DID来替代UID, 所以同一设备(同一用户) 不同UID上的交易行为会被聚合,使得结果更能描述用户好坏
  
     <sheet sheet-id="xOuNkp" token="CdGgsUhxkhwoIit5lMdmZBgEyVe"></sheet>
  2. Issuer Reject Code 精细化下钻：V3 Issuer Rejection 黑标占比偏高，部分 error code 无增量贡献或混入非 risk 流量。v4 移除无额外增量的 error code, 排除非 risk 的 sub_error流量
  
     <sheet sheet-id="02fLU7" token="CdGgsUhxkhwoIit5lMdmZBgEyVe"></sheet>
- **统一排白策略升级：**

  1. 突破 V3 对 UID & DID Pair 成功交易验证的强依赖，探索多维排白介质（TTL 可信标签、PayPal Email 验证, DID, PI 等）
  
     - **探索路径**
  
     <sheet sheet-id="olyFIS" token="CdGgsUhxkhwoIit5lMdmZBgEyVe"></sheet>
  
     1. 最终方案采用 "DID 且 PI 维度同时拥有良好历史" 的双重验证排白标准，在保证排白力度的同时避免黑标数量过度下降
  
     <sheet sheet-id="Sagg8w" token="CdGgsUhxkhwoIit5lMdmZBgEyVe"></sheet>

# 四. 黑标评估

## 评估标准

与 ROW 及算法团队拉齐黑标准确率评估标准，系统评估每步优化的边际增益

- **黑标开发集**：包含50%用户，黑标现在此人群上进行开发，通过外扩验证后推广到全体人群。
- **黑标评估集**：包含另外50%用户，黑标在开发集上确定后，通过设备、PI在评估集上进行关联，并通过评估集中的关联用户的风险表现(**拒付or全部失败率)** 评估黑标准确度。

<whiteboard token="JUiLw8XZYhtP1cbbGfNmwPqky8S"></whiteboard>

## 评估结果

通过黑标来源逻辑优化与统一排白策略升级, 黑标准确度显著提升（UK bad rate 21% → 36%，EU 17% → 36%），黑标量级维持在可控范围内（UK 约为 V3 的 81%，EU 约为 V3 的 83%）

<sheet sheet-id="SETt7Y" token="CdGgsUhxkhwoIit5lMdmZBgEyVe"></sheet>

- 黑标数量占比以及准确度在不同月份也都表现稳定

  <grid><column width-ratio="0.500000"><chart-embedded thumbnail-url="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=OWZjNGFmYmIzZTEyM2U0MzZkNmZjMjQwNWIxNzBlZWRfOTU2NDJmOGJjYjMyMjU1ZWYxYWNiYzhmYjQ0ZTM0NGNfSUQ6NzY3Mjc0NzU5Mzg2MDE3MzQyOF8xNzg2NDUwNzYzOjE3ODY1MzcxNjNfVjM" token="chtmyduYLmv2Jc1Q48NIGRWelYc"></chart-embedded></column><column width-ratio="0.500000"><chart-embedded thumbnail-url="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=OWFjZWRmYjhjYzM4M2U4Y2ZiODNmOTE0MGQxNjZiOTdfYjg0ZWMyZTdkZmI1YTM4ZDQ1NjU5ZWE5NjdiOTY2Y2FfSUQ6NzY3Mjc0NzU5ODE1MDc5ODk2OV8xNzg2NDUwNzY0OjE3ODY1MzcxNjRfVjM" token="chtmyftPpNCvh1bf8HBS0pYn4cP"></chart-embedded></column></grid>

# 五. 黑标输出

## Hive表格

| Table/Dataset | Name | Primary Key | Usage |
|-|-|-|-|
| Hive Table | pipo_risk_strategy.app_risk_strategy_ecom_bad_tag_df_v4 | reference_id | Bad Tag only |
| Hive Table | pipo_risk_strategy.app_risk_strategy_ecom_bad_tag_w_category_df `version = 'v4.0'` | reference_id | Bad Tag w/ source |

## Dorado 任务

[dataleap-ie2.tiktok-row.net](https://dataleap-ie2.tiktok-row.net/dorado/task?searchType=content&keyword=303167123&taskStatus=default&scheduleType=default&taskType=hsql&taskAlarmRuleType=0&onlyQuerySelf=false&nodeType=task_flow&taskTag=&frequency=default&project=eudupipo_500002345&showModal=alarm&taskDefaultSystemAlarm=false&taskName=app_risk_strategy_ecom_bad_tag_df_v4)



# V5 迭代方向

- Issuer reject code在EU占比的进一步下探和降低
- Fraud category = '1_Solid Fraud' 的评估准确率做进一步的case review,
- 整体的bad or all fail rate 能否进一步提升



# Reference

- <cite doc-id="QWRKwZYopi9d8sky7odc2SqRnwf" file-type="wiki" title="[TTS][EU] Ecom Payin Bad Sample V3" type="doc"></cite>
- <cite doc-id="NoxLdl168odBR1xzDLElYbtZgyc" file-type="docx" title="TTS ROW交易黑标V3" type="doc"></cite>
- <cite doc-id="E55QdX7GdoECuOx7B06lJHgrgQh" file-type="docx" title="电商黑标讨论周会" type="doc"></cite>



# Log

## 2026-07-01

- **在梳理完黑标来源的基础上，对所有黑标流量进行统一排白的优化，整体提升指标**

  1. 原有V3排白逻辑依赖于UID & DID Pair的成功交易验证记录
  2. V4优化尝试放宽排白逻辑 - 摆脱对于uid的强约束并拓宽排白介质
  
     1. 实验1: 引入用户TTL层面的可信标签进行排白操作-> 无明显增益, 下轮迭代会继续观察
     2. 实验2: 引入PayPal Email 验证的数据源进行排白操作-> 无明显增益, 下轮迭代会继续观察
     3. 实验3: 移除出 "DID维度良好历史"的成功交易
     
        1. 定义逻辑: (succ_txn_num_365d-succ_txn_num_60d>0) AND fraud_num_365d=0
     
        <sheet sheet-id="GO8Jwo" token="CdGgsUhxkhwoIit5lMdmZBgEyVe"></sheet>
     4. 实验4: 移除出 "DID或者PI 维度良好历史"的成功交易DID, 和 PI维度对于黑标表现有较好优化, 但过宽的排白逻辑使得黑标数量下降明显, 
     
        <sheet sheet-id="8xg9Gl" token="CdGgsUhxkhwoIit5lMdmZBgEyVe"></sheet>
     5. 实验5: 进一步下探issuer reject code, 减少占比
  
     <sheet sheet-id="UYkFia" token="CdGgsUhxkhwoIit5lMdmZBgEyVe"></sheet>
  3. 最终方案: 移除出 "DID且PI 维度拥有良好历史"的成功交易, 通过双重验证来增强排白标准, 实现黑标数量和黑标表现的双重保证



## 2026-06-25

### 通过对黑标来源进行逻辑优化，进一步提升准确度

- **6_Multi-PI UID Risky, 7_Multi-UID PI Risky:** 

  - 从对所有失败交易转变成对fraud risk有关的失败交易进行聚合计算，并用DID维度的聚合计算替代UID维度，实现双指标的提升，并且保证黑标数量较小幅度的下降

  <sheet sheet-id="ThlQy9" token="CdGgsUhxkhwoIit5lMdmZBgEyVe"></sheet>
- **Issuer reject code:** 

  - 通过评估error codes各自表现，移除无额外增量的“63”error code
  - 从“59，83” error code中继续下钻，排除非risk的sub_error以及frictionless 3DS autheticated的流量，实现准确度指标的提升。是来自于issuer rejection的黑标数量降低到合理水平（x->y)

<sheet sheet-id="EdLNWM" token="CdGgsUhxkhwoIit5lMdmZBgEyVe"></sheet>

- **已验证实验：**通过“高FF rate的merchant”来去排除相关merchant transaction，这块模拟对于指标影响不大

### 汇总：现有黑标来源分布以及准确率

- 与v3相比

  - 黑标量级： UK 的v4黑标量级总体约为v3的89%， EU约为v3的64%
  - 准确度：UK的bad rate 从21% 提升到28%， EU从17% 到22%
  
    <sheet sheet-id="hu0UZe" token="CdGgsUhxkhwoIit5lMdmZBgEyVe"></sheet>

### To-do:  

- **在梳理完黑标来源的基础上，对所有黑标流量进行 FF以及排白的优化，进一步整体提升“Bad or all Fail”指标**

  1. 利用低分黑标高贡献特征<cite doc-id="GVq7wtn1qiPA3uk13BeceCTPnTb" file-type="wiki" title="Bag Tag x Low Score" type="doc"></cite>去优化现有排白逻辑
  2. 通过PayPal Email的验证数据 以及 用户in-app使用数据的来对所有来源统一排除
  3. 从客诉数据中提取“退款退货不成”的信息，来去排除FF。难点在于数据的不标准
  4. 利用Appeal 结果对黑标进行进一步提纯



## 2026-06-18

- 基于最新评估标准(通过发卡行, 设备外扩到测试集中的成功交易用户的拒付报回比例)的EU, UK黑标准确度

  - 会集中优化EU的外扩以及排白逻辑来提升整体的黑标准确度，UK整体准确度达到预期
  - 目前已有提纯特征对黑标准确度影响较小，会持续开发探索其它特征。e.g. nnv3低分黑标top feature

  <sheet sheet-id="XJWFIB" token="CdGgsUhxkhwoIit5lMdmZBgEyVe"></sheet>

---
