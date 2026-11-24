---
title: 直播黑白标签定义和False Positive分析 TTLive Bad Tagging Definition and False Positive Analysis
category: 风险类型
source_url: https://bytedance.sg.larkoffice.com/docx/EW59dcy88osQ3vxud6mlbJCfg1z
source_token: EW59dcy88osQ3vxud6mlbJCfg1z
source_type: docx
doc_type: 标签定义
tags: [支付风控, 交易风控, 黑标, 白标, 黑白标签, False Positive, 误杀率, 直播, TikTokLive]
metrics: [FPR, TPR, FTR, EVIL率, EVIL+BAD率, ANGEL占比, ANGEL+GOOD占比]
business_lines: [直播]
summary: 直播黑白标签基于黑白种子强介质关联传播打5级标签，并用于已拦截交易FP分析
last_synced: 2026-08-12
---

## 适用场景
用于直播（TTLive）ROW 场景对被拦截、交易失败等非成功交易进行黑白标注，支撑 FP Evaluation（评估规则准确率与误伤率）、Block Release（拦截释放风险确认）与 Model Building（为模型提供更多黑样本）三类场景。

## 核心概念
- 黑白种子：黑种子=欺诈报回（Fraud CB/EFW/Claim/Ethoca EFW）、黑名单（直播人审MKF黑名单、直播策略Payin Group Attack黑名单、其他MKF黑名单）、高精度拦截规则（本版暂不纳入以避免循环论证）；白种子=可信流量（强可信且长时间无欺诈报回）、白名单（Escalation人审客诉白名单、Appeal通过白名单）。
- 传播方案：方案一(A)强介质一度关联、方案一(B)强介质二度关联、方案二基于图论全连接传播；强介质为用户、PI、设备。
- 打标输出：按好坏分5级 EVIL、BAD、GREY、GOOD、ANGEL；依据关联黑白种子加权和 D（黑正白负），D 越大越坏。
- 代充场景：直播业务代充常见，正常用户经代充服务商 PI/设备关联成大群组，可能使白种子被降为 GOOD/GREY。

## 关键指标口径
- FPR（False Positive Rate，白交易占比）= #(ANGEL) / #(TXN)。
- TPR（True Positive Rate，黑交易占比）= #(EVIL+BAD) / #(TXN)。
- FTR（False-to-True Ratio，每单位黑交易的白交易误伤）= #(ANGEL) / #(EVIL+BAD)。
- 分级阈值（二度关联）：EVIL D>20、BAD 0<D<=20、GREY -10<D<=0、GOOD -20<D<=-10、ANGEL D<=-20；（一度关联）：EVIL D>8、BAD 1<D<=8、GREY -1<D<=1、GOOD -3<D<-1、ANGEL D<=-3。
- 整体：FPR(PV)月均约10%、TPR约5%；UV FPR 8%、TPR 4.5%。已拦截交易：PV FPR约4%、TPR约25%、FTR约0.18；UV FPR约3.5%、TPR约25%、FTR约0.15。

## 规则 / 策略要点
- 标签传播：先取已知黑白种子，再按强介质关联获取关联交易中的黑白种子，最后加权求和确定当笔交易标签。
- 一度关联统计强关联交易中的已知黑白数量；二度关联统计更大范围黑白种子，信息更全。
- 使用建议：拦截释放用黑标 EVIL+BAD 评估潜在风险；规则优化用优质白标 ANGEL 释放头部最确定白交易。
- 落表：统计表 pipo_risk_strategy.risk_payin_webapp_txn_tagging_stats；打标结果表 risk_payin_webapp_txn_tagging_2hop_output（Row key=request_id，标签字段 tag2_level / vip_tag_level）。

## 原文正文

<!-- source_type: docx | doc_id: EW59dcy88osQ3vxud6mlbJCfg1z | title: 直播黑白标签定义和False Positive分析 TTLive Bad Tagging Definition and False Positive Analysis -->

<title>直播黑白标签定义和False Positive分析 TTLive Bad Tagging Definition and False Positive Analysis</title>

# 背景与动机 Background and Motivation

- FP Evaluation:在评估规则的准确率和误伤率的场景中，需要对被规则拦截、交易失败等非成功交易的好坏进行打标，用于计算和分析拦截交易的准确率和误伤率。此外，随着策略体系逐渐成熟，漏放的风险越来越少，导致可供分析的Fraud case会越来越少，对规则效能的评估结果也会出现偏差，创建好已拦截交易的标注方案，才能更客观地评估规则的效能。
- Block Release: 在可信扩量和拦截释放场景中，重点关注的是那些已被拦截的交易，对已经拦截的交易进行黑白标注是必要环节。目前依赖于人工分析来确认释放的拦截是否存在潜在风险，有必要定义一套黑标签打标逻辑，提升效率。
- Model Building: 在与模型同学沟通中，可以了解到模型当前的痛点之一是黑样本太少。仅考虑实际报回尚不足以支撑机器学习算法所需要的大数据量。因此，通过黑白标签的方案可以把那些已经拦截/失败的交易也进行标注，可以一定程度上为兄弟团队缓解痛点。

# 黑白标签 Bad Tagging

## 总览 Overview

在目前的生产链路中，部分交易是实锤的黑/白，其他部分是黑白未知。基于此现状，我们利用已知黑白的信息源，结合比较强的逻辑来定义已知黑白种子。对于未知部分，我们根据每笔交易与已知黑白种子之间的关联关系进行标签传播，以此来确定它们的黑白标签。Currently, some transactions are confirmed black/white, while others are unknown in black and white. Based on this situation, we define the known black and white as black and white seeds by some strong logic. For the unknown part, we find out the underlying linking relationship among the transactions with the known black and white seeds to determine their black/white labels.

<whiteboard token="GRD0whydnhWCpkbBWZPlkWAqg5d"></whiteboard>

## 黑白种子 Black & White Seeds Definition

目前版本采用如下一些黑白种子，未来可扩充更多来源可靠的黑白种子。

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td><b>类型</b></td><td><b>种子</b></td><td><b>主要内容</b></td></tr><tr><td>黑种子 Black Seeds</td><td>欺诈报回<br/>Fraud Report</td><td>Fraud Chargback, EFW, Claim, Early Fraud Warning(Ethoca)</td></tr><tr><td>黑种子<br/>Black Seeds</td><td>黑名单<br/>Blacklist</td><td><ul><li>直播人审黑名单：MKF Live User/Card Blacklist</li><li>直播策略黑名单：Payin Group Attack User/Card/Dev Blacklist</li><li>其他黑名单：MKF Ecom/Ads Blacklist</li></ul></td></tr><tr><td>黑种子<br/>Black Seeds</td><td>高精度拦截规则<br/>High-precision Rules</td><td>根据规则历史分析得出的准确度定义的高精度拦截规则（由于此版本黑白标签的一个主要应用场景是评估规则本身的效能，为避免陷入循环论证，这部分暂不纳入）</td></tr><tr><td>白种子<br/>White Seeds</td><td>可信流量<br/>Trust Traffic</td><td>进入强可信流量且足够长时间无欺诈报回的交易 Strong Trust traffic and no fraud reported</td></tr><tr><td>白种子<br/>White Seeds</td><td>白名单<br/>Whitelist</td><td><ul><li>人审客诉白名单： Escalation Whitelist</li><li>申诉通过白名单：发起Appeal且Appeal Status=PASS</li></ul></td></tr></tbody></table>

## 传播方案 Approaches

提出两种方案，方案一是用直观的逻辑计算，方案二是借力于图论算法。

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><td></td><td>简介</td><td>优势</td><td>局限</td></tr><tr><td>方案一(A)<br/>Approach 1A</td><td>基于强介质一度关联传播</td><td><ul><li>纯白盒，可解释，可定制</li><li>易实施，用SQL脚本</li></ul></td><td><ul><li>仅支持一度或二度关联，会漏掉复杂的关联关系</li><li>受限于计算资源，运行慢</li></ul></td></tr><tr><td>方案一(B)<br/>Approach 1B</td><td>基于强介质二度关联传播</td><td><ul><li>比一度关联可以拿到更多信息</li></ul></td><td></td></tr><tr><td>方案二<br/>Approach 2</td><td>基于图论的全连接传播</td><td><ul><li>信息全，支持全图关联，不会漏掉关联信息</li><li>灵活性，增删关联介质很便捷</li></ul></td><td><ul><li>某些步骤是黑盒，不可调整</li><li>需要具备图论知识和相应的工程能力的优秀人士</li></ul></td></tr></tbody></table>

### 方案一：基于强介质关联进行传播

#### 整体思路 Key Steps

1. 按照前文逻辑获取已知黑白种子 Find black & white seeds 
2. 根据强介质关联获取到关联交易中黑白种子 Find connections with the target transaction.
3. 根据关联黑白种子加权决定当笔交易的黑白标签 Get weighted sum of the black & white seeds and define the risk labels.

<whiteboard token="DTgpwKJQLhGudSbdApblMo5Ngtg"></whiteboard>

#### 一度关联 1-hop linking

以上图为例，中央绿色区域是一度关联的范围，想要判断中心的NoTag Txn应该是黑还是白，我们统计与他具有强关联的交易中的已知黑白交易数量。图中通过用户为介质关联到2笔黑交易，通过PI关联到1笔黑交易，通过设备关联到两笔白交易。直观来看，图中这笔交易关联到3笔黑交易，2笔白交易，1笔未知交易（不参与计算），我们认为这笔交易为黑。

#### 二度关联 2-hop linking

仍以上图为例，绿色和蓝色区域整体是二度关联的范围。计算时对二度关联范围内的所有黑白种子进行统计，得出最终标签。图NoTag Txn的交易在二度关联范围内，总共关联到12个黑种子，5个白种子，以及4个未知交易，我们认为这笔交易为黑。



#### 打标输出 Define the label

- 当前版本打标的输出结果是按照好坏程度将交易分为5个等级，由坏到好分别是EVIL，BAD，GREY，GOOD，ANGEL。The output result of the current version is that the transactions are divided into 5 levels, from bad to good, as EVIL, BAD, GREY, GOOD, ANGEL.
- 分级的依据：定义关联到的黑种子权重为正数，白种子权重为负数，将关联黑白种子数加权求和，得到的结果代表黑白种子数量之差***D***。该差值越大表明交易越坏，该差值越小表明该交易越好，差值接近0的则则属于本方案难以判断的灰色地带（可以通过未来方案迭代，或寻找别的方法来处理）。We assign positive weight to black seeds and negative weight to white seeds, and get the weighted sum ***D***. The transaction would be regarded as worse with larger D value, and as better with smaller minus value. The below table shows the thresholds of each level. 

| **标签** | **含义** | **阈值（二度关联）** | **阈值(一度关联）** |
|-|-|-|-|
| EVIL | 极坏：黑种子数远多于白种子数，且未关联白种子。  <br/>Black seeds are more than white seeds and no linking with white seeds | ***D***>20 | *D*> 8 |
| BAD | 较坏：黑种子数多于白种子数。Black seeds are more than white seeds. | 0<***D***<=20 | 1<*D*<=8 |
| GREY | 灰：黑种子数和白种子数差值不大，灰色地带。Linked black and white seeds are almost equal, grey space.  | -10<***D***<=0 | -1<*D*<=1 |
| GOOD | 较好：黑种子数少于白种子数。Black seeds are fewer than white seeds | -20<***D***<=-10 | -3<*D*<-1 |
| ANGEL | 极好：黑种子数远少于白种子数，且未关联黑种子。Black seeds are fewer than white seeds and no linking with black seeds | ***D***<=-20  <br/>\*ROW直播业务中的代充场景会使正常用户通过代充服务商的PI或设备会关联起来形成较大群组。 | *D*<=-3 |



### 方案二：基于图论的全连接传播

上文提到的方法，只能涵盖一度关联，但在实际中交易之间的关联关系往往比较复杂，仅靠1度关联可能无法捕捉到完整的关联关系，这会使得最终获得的标签准确度不足。因此，我们采用Graph数据库和标签传播算法对完整的关联关系进行传播。作为黑白标签的升级版本，采用更先进、更智能的方案来对整体交易进行打标。

此外，这种方法预计效果会优于一度关联，所产生的黑白结果，可以直接用于黑白名单的扩充，应用到线上策略中。

# 标签结果分析 Analysis

基于上述**方案一(B)**的实验结果，抽取ROW区域2024/04/10～2024/10/07共180天，支付方式为BANK_CARD/PAYPAL数据进行观测得到如下一组观测结果。

Based on the experimental results of Approach 1B, the ROW region 2024/04/10 to 2024/10/07 were observed for a total of 180 days. The payment method was BANK_CARD/PAYPAL for observation to obtain the following set of observation results.

## 标签分布 Label Distribution

- 黑白标签占比（PV）如下：

  <grid><column width-ratio="0.444654"><img name="image.png" mime="image/png" scale="0.305556" src="LOv2bWMQooQXxQx3dcDl7XBogTd"/></column><column width-ratio="0.555346"><table><colgroup><col/><col/><col/></colgroup><tbody><tr><td><b>标签</b></td><td>占比</td><td>使用建议</td></tr><tr><td>EVIL</td><td>0.67%</td><td rowspan="2">用于拦截释放，使用黑标EVIL+BAD，可评估释放拦截后潜在风险。</td></tr><tr><td>BAD</td><td>3.86%</td></tr><tr><td>GREY</td><td>70%</td><td>-</td></tr><tr><td>GOOD</td><td>15.46%</td><td>-</td></tr><tr><td>ANGEL</td><td>9.68%</td><td>用于规则优化，使用优质白标ANGEL用于释放头部最确定的白交易</td></tr></tbody></table></column></grid>
- 黑白种子打标结果（PV）

  - 补充数据：观测已知的黑白种子最终打标的分布情况如下（取202410～202501期间数据为例，percent指各类标签值占TotalTxn的比例）
  - 在黑种子中，两类黑种子最终95%以上被打标为evil和bad，且无黑种子被打标为ANGEL。
  - 在白种子中，两类白种子最终37%以上被打标为ANGEL，22%被打标为GOOD，且无白种子被打标为EVIL。由于代充行为在直播业务线十分常见，若白种子与黑种子存在介质关联，则无法被打为ANGEL，从而被标记为GOOD；若用户选用了存在盗卡行为的“坏代充”服务，则更有可能被打成 GREY标签。

  <sheet sheet-id="G3ObPD" token="AaNmsvQPqhA5qtt5TYClZJCjg9B"></sheet>

## 指标定义 Rule evaluation metrics

- FPR(False Positive Rate，白交易占总交易的比例) ：FPR= #(ANGEL) / #(TXN)
- TPR(True Positive Rate，黑交易占总交易的比例) : TPR=#(EVIL+BAD) / #(TXN)
- FTR(False-to-True Ratio，打击每单位黑交易需要承担多少白交易误伤) : FTR= #(ANGEL) / #(EVIL+BAD)   

## 整体 On the overall population

PV：整体里FPR表示整体白交易占比，月均约为10%；整体里TPR表示黑标占比，月均约为5%。由于黑白种子来源于Fraud报回、用户申诉等流程，需要一定的回收周期，因此近期指标会偏低。此外，随着Q3申诉流程开量，我们可以获取到的用户反馈更多了，这部分白种子有上升趋势。

![](https://feishu.cn/file/LjTjb5T3woU4ywxiEYll1rv1gAe)

UV：FPR：8%，TPR：4.5%

![](https://feishu.cn/file/DZbqbuhwLoXL0gxpltAlLO1Ng1g)

## 已拦截交易 On the Blocked Transactions

- PV指标观测：

  - FPR:月均约为4%，约为整体的40%。
  - TPR:月均约为25%，约为整体的500%。
  - FTR：月均约为0.18，意为每拦截100笔黑交易，成本为误伤18笔白交易

![](https://feishu.cn/file/PzsPbkdP3o1jzKxuWQml3hPygwg)

- UV指标观测：

  - FPR:月均约为3.5%，约为整体的44%
  - TPR:月均约为25%，约为整体的550%。
  - FTR：月均约为0.15，意为每拦截100个黑用户，成本为误伤15个白用户

![](https://feishu.cn/file/ZVr0bveXHonTNxx7RkRllFEUgWg)

# 离线落表 Hive Tables

若用于监控，可直接使用下面的统计数据表，若需要查询打标详情，可以使用打标结果表

- 统计数据表 statistics：pipo_risk_strategy.risk_payin_webapp_txn_tagging_stats

  - 维度：
  
    - cre_dt交易创建日期
    - is_cs_block是否被盗卡策略拦截
    - is_ato_block是否被盗账户策略拦截
  - 指标：
  
    - txn_cnt总交易数
    - angel_cnt白交易数
    - evil_bad_cnt黑交易数
- 打标结果表 Tagging Result：pipo_risk_strategy.risk_payin_webapp_txn_tagging_2hop_output

  - 主键 Row key：request_id
  - 标签字段 Label columns：
  
    - 二度关联标签 2-hop tagging level：tag2_level
    - VIP专用标签 Tag for vip only：vip_tag_level
  - 生效日期 available date：20241016
- 看板 Dashboard：https://aeolus-va.tiktok-row.net/#/dashboard/365623?appId=555295&sheetId=387513

# Appendix: 老版本的观测数据（下面作废，仅供参考）

### 黑标签（EVIL&BAD）

- 整体

EVIL Rate： 1.3%； EVIL+BAD Rate： 3%

![](https://feishu.cn/file/RuFnb3mZuoUggQxvxlVlXAVggkd)

- Low Risk VS Other

  - EVIL：0.4% vs 2.8%； 
  - EVIL+BAD：0.8% vs 7.5%， 峰值10%。

![](https://feishu.cn/file/TkbzbypmYoK1LPxTJMPlJTDogBe)



- 已拦截交易

  - 整体 ： EVIL Rate： 8% ； EVIL+BAD Rate：平均 27%，峰值37%。

![](https://feishu.cn/file/Z0QYboNNno3jpHxPm4ylqouYg5b)

- Low Risk vs Other

  - EVIL : 8% vs  8%
  - EVIL + BAD: 13% vs 26%

![](https://feishu.cn/file/CaL9boQtQoB3H6xAng9lxgjNgOg)

### 白标签（ANGEL / GOOD）：

- 整体： 

  - ANGEL： 10%， ANGEL+GOOD：45%

![](https://feishu.cn/file/Ubkybn2hJoBaXIxkPSFlppulgre)

- Low Risk vs Other

  - ANGEL: 15% vs 4%
  - ANGEL+GOOD: 55% vs 18%

![](https://feishu.cn/file/KJGzbV7mfoKgfQx6W30lnJZjgOe)

- 已拦截交易中

  - Low Risk vs Other
  
    - ANGEL: 45% vs 5%
    - ANGEL + GOOD : 65% vs 15%

![](https://feishu.cn/file/VVdwbnVmSoRLG6xHZ4QlBAK5gvg)
