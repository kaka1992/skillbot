---
title: GPP- TikTok Local Service Sharing
category: 业务场景
source_url: https://bytedance.sg.larkoffice.com/wiki/XRxwwwQA2ifnSgkc6qrc2rZanzd
source_token: XRxwwwQA2ifnSgkc6qrc2rZanzd
source_type: wiki
doc_type: 业务介绍
tags: [LocalService, PIPO, GPP, TTS, 指标]
metrics: [GMV, GTV, CAGR, 市占率]
business_lines: [LocalService]
summary: 介绍TikTok本地生活服务开环/闭环模式、券商品形态及与PIPO在印尼泰国的合作方案
last_synced: 2026-08-12
---

## 适用场景
面向需要了解 TikTok 本地生活服务（TTLS）业务的读者，介绍其市场概况、开环与闭环模式区别、商家经营与商品形态，以及与国际支付 PIPO 在印尼、泰国的合作模式与支付能力。适用于业务对接及风控人员理解生服场景。

## 核心概念
- 模式区别：开环（用户外跳商家侧完成下单支付核销）与闭环（入驻、上品、交易、核销、结算全部在 TikTok 内完成）；后续开环全部切闭环。
- 品类：餐饮（F&B）、酒旅（Travel）、到综（In-store service）。
- 商家经营模式：纯直营、直管为主、加盟为主，差异在总部/门店盈亏承担与决策下放程度。
- 商品形态：MVP 仅上线团购券、代金券（均为预付券）；附录含次卡、预售券、平台通兑券、预订、配送等类型。
- 合作主体：ID 由 PT Tokopedia 托管（MOR），TH 由 PIPO HK 自营（TikTok Shop Thailand）。
- PIPO 能力：商家/达人入驻（CPT/CPS）、嵌入式与六分屏收银台、Payin 即时付/二次支付、Payout 代付、退款（原路/二次/Refund to Credit）、周期性结算、关退、Chargeback、KYB/KYC 合规、营销补差与商家返佣（book transfer）。
- TTLS vs TTS 区别：商家结构与账户（组织根节点总属关系）、订单模型（item 维度核销分账、扩展一层单）、退款（虚拟物品合规更严，不支持退款转代发、credit 不可提现）。

## 关键指标口径
（本文无指标口径）

## 规则 / 策略要点
- 战略方向：开环仅接极少量已有团购券能力 KA/渠道商，长期全部切闭环；垂类聚焦高毛利行业。
- 商品策略：MVP 仅上线团购券、代金券（预付券）。
- 结算与差错：MVP 统一 T+7 结算（后续可按商家配置），关退 24 小时关单，PIPO 将 chargeback 通知生服。
- 退款规则：支持核销前用户发起退款、核销前过期退、核销后 7 天内申诉退款；credit 不可提现且需有过期时间，仅与 TTS 互通。
- 营销策略：营销补差保证全网最低价（平台补贴差额，商家仍得团购价结算）；商家 GMV 达标返佣。
- 支付方式：ID 支持 CCDC、Virtual Account、DANA、GoPay 等；TH 支持 CCDC、mBanking、TrueMoney 等；PI Clip 与 TTS/TTL 互通。

## 原文正文

<!-- source_type: wiki | doc_id: XRxwwwQA2ifnSgkc6qrc2rZanzd | title: GPP- TikTok Local Service Sharing -->

<title>GPP- TikTok Local Service Sharing</title>

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><td><b>Version </b></td><td><b>Content Change</b></td><td><b>Author</b></td><td><b>Date</b></td></tr><tr><td>V1.0</td><td>Drafting</td><td><cite type="user" user-id="ou_10d86b850c644f473c93269fbe246733" user-name="di zeng"></cite></td><td>Jun 2024</td></tr></tbody></table>

# 业务简介 | Business Introduction

## 市场概况 | Market Overview

2025年，中国以外地区的本地服务在线市场规模预估达到1.89万亿美元。同时，用户在线浏览本地服务信息、预定、购买本地服务的习惯和心智尚未发展成熟。

> In 2025, the estimated scale of the online local service market in areas outside China will reach 1.89 trillion US dollars. At the same time, the habits and mentalities of users browsing local service information, making reservations, and purchasing local services online have not yet fully developed.



![图片展示了2019 - 2025年非中国地区本地服务在线市场规模（GTV潜力）情况。图表以柱状形式呈现，分为到餐、到店、酒旅、外卖四类服务，各年份数据以美元计，如2019年到餐服务为1,194亿美元，外卖为83亿美元。2025年各服务市场规模预测分别为到餐1,891亿美元、到店1,375亿美元、酒旅1,981亿美元、外卖279亿美元。右上角标注22 - 25年CAGR（年复合增长率）分别为14.6%、8.0%、4.1%、17.1%、12.3%。](https://feishu.cn/file/U4k9b1WYeoIyauxalvVlpEFkgzK)



## TikTok本地生活服务 | TikTok Local Service

### 开环和闭环的区别 | The difference between open-loop and closed-loop

<table><colgroup><col/><col/><col/><col/><col/><col/></colgroup><thead><tr><th rowspan="5" vertical-align="middle"><b>TT Local Service</b><whiteboard token="Pld1wVJaWhYwN6bg0Zel63j6gob"></whiteboard></th><th><b>模式</b><br/>Business Mode</th><th><b>定义</b><br/>Definition</th><th><b>支持商家类型</b><br/>Merchant Types</th><th><b>品类</b></th><th><b>策略</b><br/>Business Strategy</th></tr></thead><tbody><tr><td rowspan="3">开环<blockquote><p>Open-Loop</p></blockquote></td><td rowspan="3">商家需入驻后，将商品信息上传入库，TT只展示商品详情页；用户点击商详页后，外跳至商家侧完成下单、支付、核销等一系列动作<blockquote><p>Merchants need to register and upload product information to the TT platform. TT only displays the Product Detail Page. After users click on the detailed page, they will jump to the merchant's side to complete a series of actions, such as placing an order, payment, and redemption.</p></blockquote></td><td rowspan="3">已有团购券能力的KA（极少量）<blockquote><p>Key Accounts capable of selling coupons (only a small amount)</p></blockquote></td><td>餐饮<blockquote><p>F&amp;B</p></blockquote></td><td><ul><li>接入SaaS服务商（如印尼ESB）、已有在线履约支付技术能力和团购商品的商家（如印尼Tomoro Coffee、Kopi Kenangan）</li><li>后续不会再做开环模式，全部切到闭环</li></ul><blockquote><ul><li>Develop via SaaS service providers (such as ESB in Indonesia), merchants who already have the technical capability of online redemption and payment (such as Tomoro Coffee and Kopi Kenangan in Indonesia).</li><li>Open-loop mode will not be done in the future, and all will be switched to closed-loop.</li></ul></blockquote></td></tr><tr><td>酒旅<blockquote><p>Travel</p></blockquote></td><td><ul><li>只接渠道商</li><li>酒店不做闭环，景点门票待定；长期探索开环从渠道商抽佣</li></ul><blockquote><ul><li>Only accept channel distributors</li><li>Hotels do not do closed-loop, and the scenic spot tickets are to be determined; they will explore the open-loop and commission from the channel distributors in the long term.</li></ul></blockquote></td></tr><tr><td>到综<blockquote><p>In-store service</p></blockquote></td><td><ul><li>只接渠道商和大型KA</li></ul><blockquote><p>印尼最大的连锁美发大概50家门店</p></blockquote><ul><li>不做闭环，长期探索开环从渠道商抽佣</li><li>垂类选择上，尽量聚焦高毛利行业</li></ul><blockquote><ul><li>Only accept channel distributors and large KAs.<br/>The largest chain hair salon in Indonesia has approximately 50 stores.</li><li>Do not do closed-loop, and explore the open-loop to draw commission from the channel distributors in the long term.</li><li>In terms of vertical category selection, try to focus on industries with high gross profit margins.</li></ul></blockquote></td></tr><tr><td>闭环<blockquote><p>Closed-Loop</p></blockquote></td><td>指商家从入驻平台、上品、交易、核销、到结算提现完成，全部经营动作在TikTok内完成<blockquote><p>It means that all the operation actions of the merchant, including platform onboarding, selling products, trading, redemption, settlement and withdrawal, are all completed within TikTok.</p></blockquote></td><td>定邀KA &gt;&gt;全量商家<blockquote><p>Invited KA &gt;&gt; all merchants</p></blockquote></td><td>餐饮<blockquote><p>F&amp;B</p></blockquote></td><td><ul><li>先做KA，目标覆盖全量商家</li><li>撮合和达人分佣、服务商分佣，规模成长</li></ul><blockquote><ul><li>Do KA first, with the goal of covering all merchants.</li><li>Scale the merchant and creators matching.</li></ul></blockquote></td></tr></tbody></table>



### **餐饮规模预估 |** Closed-loop Scale in the Dining Market

- **闭环机会：**印尼泰国团购仍在早期，市场绝对规模小，其他平台也处于投入早期，**TT有机会切入带动整体团购市场增长，成为大盘驱动玩家**

  - **2025年闭环GMV激进版：**预估印尼\~\$152Mn（市占第一，35%），泰国\~\$48Mn（市占第一，31%）
  - **2025年闭环GMV保守版：**预估印尼\~\$76Mn（市占第二，23%; Grab市占第一，41%），泰国\~\$25Mn（市占第二，20%; Grab市占第一，43%）

![图片展示了2025年TikTok在印尼、泰国的餐饮团购目标与市场竞争格局预估。分为激进版和保守版两种情况。激进版预估两国团购市场规模分别为438百万美元和156百万美元，TikTok市占率分别为35%和31%；保守版预估两国市场规模分别为329百万美元和123百万美元，TikTok市占率分别为23%和20%。图中还呈现了短视频、直播、搜索、其他渠道的占比情况，以及餐饮团购渗透率。该图与文档中对TikTok在印尼、泰国团购市场预估的描述相呼应。](https://feishu.cn/file/Z0bHbhFK1o1B6nxLQOUl6NjCg2f)

- **开环可接入的规模极其有限：**仅一家平台ESB（30家商家），两家KA，共计32家开环商家；泰国暂无；2024年预估印尼产生全年GMV\~\$695k



> - **Closed-loop opportunity:** The group-buying market in Indonesia and Thailand is still in the early stage, and the absolute market scale is small. Other platforms are also in the early stages. **TT has the opportunity to become a major driver in the market.**
> 
>   - **Aggressive version of closed-loop GMV in 2025:** It is estimated that in Indonesia \~\$152 million (the first in market share, 35%), and in Thailand \~\$48 million (the first in market share, 31%).
>   - **Conservative version of closed-loop GMV in 2025:** It is estimated that in Indonesia \~\$76 million (the second in market share, 23%; the first will be Grab, 41%), and in Thailand \~\$25 million (the second in market share, 20%; the first will be Grab, 43%).
> - The scale that can be accessed in the open-loop is extremely limited: There is only one platform ESB (30 merchants), two KAs, a total of 32 open-loop merchants; there is none in Thailand for the time being; it is estimated that in 2024, the annual GMV generated in Indonesia is about \$695k.



### 为什么一定要做闭环 | The necessity of building a closed-loop platform

- **开环瓶颈：第三方平台或直连商家能撬动供给量有限，绝大多数商家不具备3方团购券能力**

  - **第三方平台团购券仍在早期，规模小：**Grab目前轻量投入团购券，体量极小（2023年GMV\~4600万），且内部仍存在组织分工问题不明确；Gojek预计今年6月启动团购券
  - **商家在线化基础差，直连商家数量有限：**走访发现印尼、泰国餐饮商家普遍数字化能力较弱，第三方SaaS服务商也基本没有团购券，目前判断可接入的已有团购券能力商家仅印尼三家（1家服务商，2家KA）
  - **折扣不可控，平台玩法有局限：**开环团购券由第三方平台或KA自身把控，TT无法干预团购折扣力度，对消费者吸引力有限
  - **商达撮合无法规模化：**开环模式依赖运营线下支持，商家需线下反选确认、以及达人到店需要展示凭证供确认身份；商家和达人结算均在平台外，TT作为平台没有调控能力



- **闭环机会：餐饮商家线上营销诉求未被满足，目前竞品的折扣力度对用户吸引力低**

  - **餐饮商家有营销诉求，被满足的不够好：**印尼商家尤为明显，走访发现多数商家都不同程度的在线上平台进行营销（多数是买达人推广，少数尝试广告），但线上营销的效果衡量不清晰，商家希望能看到明确的转化
  - **市场处于早期，竞品提供的团购折扣力度不高：**目前仅Grab、Shopeefood尝试轻量投入团购，折扣力度\~8折，TT有机会谈到优惠力度更高的deal，吸引更多用户



> - **Bottlenecks of open-loop : merchant supply is limited,including third-party platforms and direct merchants, as the majority don't have dine-in vouchers**
> 
>   - **Third-party platforms' dine-in vouchers are still in the early stage, on a small scale:** Grab currently invests lightly in dine-in vouchers, with a very small GMV generated (2023 GMV \$46Mn), and there are still internal uncertain organization issues; Gojek is expected to launch dine-in vouchers in June 2024; And thus overall cooperation needs further observation and discussion
>   - **Direct Merchants that can be integrated into the system is limited:** Field research in February revealed that the general digital capabilities of restaurants in Indonesia and Thailand are weak. Third-party SaaS providers rarely develop the dine-in voucher service. **Only three merchants** in Indonesia (one SaaS provider and two KAs) have the capability to operate dine-in voucher services.
>   - **For TT, discounts are uncontrollable, while new functions are limited:** Open-loop dine-in vouchers are controlled by third-party platforms or KAs themselves, with TT unable to intervene in the discount intensity, thus having limited attractiveness to consumers.
>   - **Merchants&Creators matching cannot be scaled:** The open-loop model relies on offline operational support, requiring merchants to confirm cooperations offline and influencers' identity verification in-store. Transactions are outside the platform, leaving TT without control ability.
> 
> - **Closed-loop opportunities: Merchants' online promotion needs haven't being met, with current discounts offered not attractive enough to users.**
> 
>   - **Merchants' marketing demands haven't been well met:** particularly evident among Indonesian merchants. Previous offline visits show that they have some online marketing already (mostly pay for influencer promotions, with a few trying online platform ads). However, the effectiveness is not clearly measured, and merchants expect clearer benefits.
>   - **The market is in its early stages, and the current discount offered by competitors is not attractive:** Only Grab and Shopeefood are making a few investments in dine-in vouchers, with a discount intensity of \~20% off. TT has the opportunity to negotiate deals with higher discounts to attract more users.



### 里程碑目标 | Milestones

- 2024年9月跑通正向链路，用于给商户演示和销售
- 2024年11月上线正式运营MVP

> - Launch the forward MVP  in September 2024 for demonstration and sales to merchants.
> - Launch the formal operation MVP in November 2024.

<whiteboard token="VlRnwDqklh3WzjbGReOlRXN7g2c"></whiteboard>

### 团队分工 | About the team

TTLS业务侧的团队分工简要示意如下（updated by May 2024）

<whiteboard token="NZZpwJWdMh8TDcbRMSTlpxlZg73"></whiteboard>



# 业务模式 | Business Pattern

## 业务想怎么做？ | What does TikTok Local Service do?

国际生服的MVP版本，希望以竞对能力作为底线，建立一套买卖通畅，且上手门槛低的闭环经营链路（For用户\商户）

> The MVP version of TTLS aims to benchmark against competitors' capabilities and create a seamless closed-loop business process with a low threshold for both buyers and sellers.

<grid><column width-ratio="0.333333"><p><b>用户能买</b></p><p>正向：锚点分发-&gt;下单履约</p><p>逆向：订单退款</p><img name="image.png" alt="图片展示了TikTok Local Service的用户主流程（ID）。流程从用户在平台浏览商品开始，经商品详情页、选择商品、填写收货地址、选择配送方式、确认订单、支付等环节，最终完成订单。若用户对商品有疑问，可点击“Contact Seller”联系卖家。若订单有问题，可点击“Contact Customer Service”联系客服。该流程与文档中介绍的用户能买（正向：锚点分发-&gt;下单履约，逆向：订单退款）相呼应，直观呈现了用户在平台的购物操作路径。" mime="image/png" scale="1.000000" src="QTXsbiBq0oeKvRxguCwlBTx4gQf"/><img name="image.png" alt="图片展示了TikTok Local Service的业务流程。左侧“2.Order part”部分，从用户浏览商品、添加到购物车、选择配送方式、填写收货地址、确认订单、支付，到订单成功、商家发货、用户收货、用户评价等环节，均以手机界面图呈现。右侧“3.Account center”部分，展示了账户中心的商家中心、订单中心、设置等界面。该图与文档中介绍的用户能买、商户能卖、平台能管的业务模式相呼应，直观呈现了业务流程。" mime="image/png" scale="1.000000" src="Ie5XbvmhNoMWJDxxfAIloOqdghd"/></column><column width-ratio="0.333333"><p><b>商户能卖</b></p><p>加入平台-&gt;开店经营</p><whiteboard token="GW8NwOgjQh80H1bbxLvlCA8FgXe"></whiteboard><p></p></column><column width-ratio="0.333333"><p><b>平台能管</b></p><p>代操作-&gt;管生态</p><whiteboard token="UzY7waOQch3RH9by9QYlT4iogog"></whiteboard></column></grid>

## 商家经营模式 | Merchants' Business Patterns

相较于中国成熟的加盟生态，泰国和印尼餐饮商家在加盟模式上的引入较为谨慎，大部分是纯直营或直营为主。加盟商的本质是付费购买品牌的使用权，和直营模式的差异主要在：**1）总部和门店谁来承担盈亏；2） 日常经营中的决策下放到什么程度**

> Compared with the mature franchise ecosystem in China, Thai and Indonesian catering merchants are more cautious in introducing the franchise model, and most of them are pure direct operation or mainly direct operation. The essence of franchisees is to pay to buy the right to use the brand, and the main differences from the direct operation model are: **1) Who will bear the profit and loss between the headquarters and the store**; **2) To what extent the decision-making in daily operations is decentralized**.

![图片展示了不同商家类型在总部管理、经营能力和结算打款方面的模式。纯直营模式下，总部强管控，门店标准化管理，总部负责店铺选址、菜品设计等，平台打款到总部账户，总部承担盈亏；直管为主、少部分加盟模式下，总部弱管控，门店个性化管理，总部负责优惠策略等，平台打款到门店账户，门店自负盈亏，总部定期review；加盟为主、少部分直营模式下，总部弱管控，门店个性化管理，总部负责优惠策略等，平台打款到门店账户，门店自负盈亏，总部定期review。](https://feishu.cn/file/U4nVbRisLovrPux2wE3lqjlfgof)

<callout emoji="💡">
**关于商家结算打款需求的调研发现**
- **竞品商家端的使用现状**

  - **结算打款：**Grab支持直营店的收入统一打到总部账户，加盟店打到各自账户
  - **账期：**Grab和Goiek两大平台**采用T+1结算**，Grab商家支付营销费用的周期是4个月
  - **团购券抽佣：**Grab给dine-in商家提供一段免佣金时期，过了之后开始抽佣，佣金6%；Klook抽佣5-10%
  - **对账：**平台根据KA商家需求定期（通常是每天）回传销售记录，由总部财务和商家POS系统里的订单对账
  - **经营分析：**由于商家端只能看到门店维度的数据，总部的经营分析更多靠平台提供的数据报告，以及AM的分析建议
- **商家诉求**

  - **希望提供清晰的销售记录：**标明扣除多少金额、扣除的是什么金额(税/佣金)、有多少订单取消/退款在
  - **商家端能看想要的分析维度：**商家通常会看历史订单，谁在哪里买、客单价等，以及整体的趋势表现
> **Research Findings on the Requirements of Merchant Settlement and Payment**
> 
> - The current usage situation on the competitors' side
> 
>   - Settlement and payment: Grab supports the income of direct-sale stores to be uniformly transferred to the headquarters account, and that of franchise stores to be transferred to their respective accounts.
>   - Accounting period: The two major platforms, Grab and Goiek, adopt T+1 settlement, and the cycle for Grab merchants to pay marketing expenses is 4 months.
>   - Commission for vouchers: Grab provides a commission-free period for dine-in merchants, and after that, it starts to charge a commission of 6%; Klook charges a commission of 5-10%.
>   - Reconciliation: The platform regularly (usually every day) uploads sales records according to the needs of KA merchants, and the orders in the financial affairs of the headquarters and the merchant POS system are reconciled.
>   - Business analysis: Since the merchant side can only see data at the store dimension, the business analysis of the headquarters relies more on the data reports provided by the platform and the analysis suggestions of AM.
> - Merchant demands
> 
>   - Hope to provide clear sales records: indicating how much amount is deducted, what amount is deducted (tax/commission), and how many orders are cancelled/refunded.
>   - The merchant side can see the desired analysis dimension: Merchants usually look at historical orders, who bought where, the per-customer unit price, etc., and the overall trend performance.
</callout>



## 商品形态 | Products

### 商品类型 | Product Types

- **按购买方式分类**

  - 非预付券
  - **预付券——TT Local service提供的商品形态**

> - Categorized by purchase method:
> 
>   - Non-prepaid vouchers.
>   - **Prepaid vouchers - the product provided by TT Local service.**

<callout emoji="🤔">
**发现与思考**
- 现状TH全部为第三方预付券，ID以非预付券为主（尤其是有自研系统的商家），只有少量预付券。推测跟当地用户的消费习惯有关，比如印尼用户更偏好先买后付，而预付券是先付款，后享受服务。印尼用户对于预付券的心智和消费习惯、商户在市场上的供给，都处于更早期的阶段。
- TT的达人带货种草模式，更可能会存在用户先囤券，后续退款的场景
> **Findings**
> 
> - All in TH are third-party prepaid vouchers, while in ID, non-prepaid vouchers are dominant (especially for merchants with self-developed systems), and there are only a small amount of prepaid vouchers. It is speculated that it is related to the local consumers' consumption habits. For example, Indonesian users prefer to pay after purchase, while prepaid vouchers require payment first and then using the service.
> - In the model of TT, where key opinion leaders make recommendations, it is more likely that users stock up on vouchers first and then request refunds later if they don't want to consume them.
</callout>



- **按履约场景分类**

MVP版本仅上线**团购券**、**代金券（均为预付券）。**（注：后续可能会上线[其他类型商品](https://bytedance.sg.larkoffice.com/docx/VyYxdLkYvoXIMoxY1wFldP9Gg9x#part-HxgqdxYYYoBO2px1xzxlEKjrglh)）

> The MVP version only launches bundle vouchers and cash vouchers (both are prepaid vouchers). (Note: Other types of products may be launched in the future.)

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td><b>商品类型</b></td><td><b>类型含义</b></td><td><b>场景描述</b></td></tr><tr><td>卡券类-团购券<blockquote><p>Bundle voucher</p></blockquote></td><td><ul><li>商品售卖的内容：卡券</li><li>卡券兑换：服务</li><li>核销次数：1次</li></ul><blockquote><ul><li>The content of products sold: vouchers</li><li>Redemption for services</li><li>One-time redemption</li></ul></blockquote></td><td>支付后获得团购券，<b>用户</b>持团购券到店核销<blockquote><p>After payment, the user gets the voucher and redeems it at the store for the service.</p></blockquote></td></tr><tr><td>卡券类-代金券<blockquote><p>Cash voucher</p></blockquote></td><td><ul><li>商品售卖的内容：卡券</li><li>卡券兑换：现金支付</li><li>核销次数：1次</li></ul><blockquote><ul><li>The content of products sold: vouchers</li><li>Redemption for payment</li><li>One-time redemption</li></ul></blockquote></td><td>支付后获得代金券，<b>用户</b>持代金券到店核销兑换现金支付<blockquote><p>After payment, the user gets the voucher and redeems it at the store to subsidize the payment.</p></blockquote></td></tr></tbody></table>



### 商品交易订单模型 | TTLS Order Trade System

<whiteboard token="MjlkwlYujheCa6bbFJilUPEegEg"></whiteboard>

# 和国际支付的合作 Collaboration with PIPO

## 合作模式 | Collaboration Modes

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td></td><td><b>ID</b></td><td><b>TH</b></td></tr><tr><td><b>参与主体</b><br/>Entities</td><td>Payment: PT Tokopedia<br/>Business: PT Tokopedia</td><td>Payment: PIPO HK<br/>Business: TikTok Shop (Tailand) Ltd.</td></tr><tr><td><b>经营模式</b><br/>Patterns</td><td>托管 MOR</td><td>自营 Self-operated</td></tr><tr><td><b>资金流</b><br/>Funds flow</td><td><readonly-block type="diagram"></readonly-block></td><td><readonly-block type="diagram"></readonly-block></td></tr></tbody></table>

## TTLS vs TTS方案设计上的主要区别 | Main difference on the product solution design between TTLS & TTS

<table><colgroup><col/><col/><col/></colgroup><thead><tr><th></th><th>TTLS</th><th>TTS</th></tr></thead><tbody><tr><td>商家结构与账户<blockquote><p>Merchant Structure and Account</p></blockquote></td><td><whiteboard token="AFOfwfzBGhy7oxbARSllXVVGgFb"></whiteboard><ul><li>需要在PIPO入驻的（即有结算需求的）组织单元，无论是总店/组织/门店，都有独立的资质，会以一个实体形式入驻PIPO，即都会在PIPO创建一个client_id，并基于一个client_id一对一生成merchant_id</li><li>TTLS会额外传输总店（即组织根节点）及其以下的组织/门店的总属关系</li></ul><blockquote><ul><li>The organizational units that need to be settled in PIPO, whether it is the head store/organization/store, all have independent qualifications and will settle in PIPO in the form of an entity, that is, a client_id will be created in PIPO, and a merchant_id will be generated one-to-one based on a single client_id.</li><li>TTLS will additionally transmit the total ownership relationship of the head store (that is, the root node of the organization) and the organizations/stores below it.</li></ul></blockquote></td><td><whiteboard token="Yo0lwTV4dhjuy7bBZRZlKFZggdd"></whiteboard><br/>本对本场景下，电商的一个卖家主体与PIPO client_id一一对应，该主体在平台上开通的店铺与PIPO merchant_id一一对应<blockquote><p>In the local-to-local situation, an e-commerce seller entity corresponds one-to-one with a PIPO client_id, and the store opened by this entity on the platform has a one-to-one correspondence with a PIPO merchant_id.</p></blockquote></td></tr><tr><td>订单模型<br/>（交易、分账）<blockquote><p>Order System</p></blockquote></td><td><whiteboard token="XccowJAuvhqrV0b8TEGlfASNgrc"></whiteboard><br/>与TTS不同的是，由于TTLS的商品是基于item维度进行核销、分账、退款等操作，为了更清晰地记录单据依据，且对下游域包括清结算等进行信息校验、以及对于商品改价等动作需要有更精细的管控，PIPO扩展一层单去表达业务的场景<blockquote><p>Unlike TTS, since the goods of TTLS perform operations such as verification, revenue sharing, and refund based on the item dimension, in order to record the documentary basis more clearly, and to conduct information verification for downstream domains including settlement and clearing, and to have more fine-grained control for actions such as changing the price of goods, PIPO extends an additional layer to express the business scenario.</p></blockquote></td><td><whiteboard token="Hw54wEi42hgAiWbUQB7lxqgtgoc"></whiteboard><br/>基于店铺维度分账<blockquote><p>Revenue sharing at the store dimension.</p></blockquote></td></tr><tr><td>退款<blockquote><p>Refund</p></blockquote></td><td>由于是虚拟物品，相比TTS，法务合规对TTLS的要求更为严格<ul><li>不支持退款转代发（legal pending）</li><li>Refund-to-credit余额不支持提现；ID的credit需要有有效期</li></ul><blockquote><p>Since it is a virtual item, compared to TTS, the requirements of legal compliance for TTLS are more strict.</p><ul><li>It does not support refund to consignment (legal pending).</li><li>The refund-to-credit balance does not support withdrawal.</li></ul></blockquote></td><td><ul><li>支持退款转代发</li><li>Refund-to-credit余额可提现</li></ul><blockquote><ul><li>Support refund to consignment.</li><li>The balance of Refund-to-credit can be withdrawn.</li></ul></blockquote></td></tr></tbody></table>

## 支付能力 Payment Capabilities

### MVP使用的PIPO产品能力 | PIPO capabilities applied in MVP

<table><colgroup><col/><col/><col/></colgroup><thead><tr><th><b>模块</b></th><th><b>接入产品功能</b></th><th><b>说明</b></th></tr></thead><tbody><tr><td rowspan="2">商服</td><td>商家入驻</td><td><ul><li>商家通过TTLS侧治理的审核完成平台入驻后，有结算需求的商家会进入PIPO入驻环节</li><li>TTLS平台入驻时会收取的信息会传给PIPO，PIPO需要额外收取的，会由PIPO提供页面给到商家填写提交</li></ul></td></tr><tr><td>达人入驻</td><td>分为2种模式：<ul><li>CPT模式（一口价模式）<ul><li>应用场景：开环模式，平台通过MP直接给达人支付佣金（已准备上线）</li><li>入驻方式：入驻到MP，MP使用PIPO合规KYC能力</li></ul></li><li>CPS模式（带货模式）<ul><li>应用场景：闭环模式，达人带货后从商家收入进行分账</li><li>入驻方式：入驻到PIPO商服</li></ul></li></ul></td></tr><tr><td>收银</td><td>嵌入式收银台</td><td>前端采用的是Natvie收银台，分为首次支付和二次支付：<ul><li>首次支付使用的是嵌入式收银台，下单并支付请求由嵌入式收银台和TTLS的服务端进行交互</li><li>二次支付使用的是六分屏收银台，支付请求由PIPO使用nonce发起</li></ul></td></tr><tr><td rowspan="2">交易</td><td>Payin即时付；二次支付</td><td><ul><li>客户端内嵌式收银台调取一步下单接口</li><li>首次支付失败后，可以在原交易单上发起二次支付</li></ul></td></tr><tr><td>Payout代付</td><td>支持商家和达人的主动提现、平台自动打款</td></tr><tr><td>支付方式</td><td>PI Clip</td><td>ID支持和TTS互通；TH支持和TTS、TTL互通</td></tr><tr><td rowspan="2">退款</td><td>原路退款；二次退款</td><td><ul><li>支持核销前用户发起退款、核销前过期退、核销后7天内申诉退款</li><li>首次退款失败后，可以更改支付方式，在原退款单上发起二次退款</li></ul></td></tr><tr><td>Refund to Credit</td><td><ul><li>不支持原路退和退款转代发的支付方式（legal pending），需要支持退款到credit</li><li>生服场景下的credit不能提现，需要有过期时间，只能与TTS互通</li></ul></td></tr><tr><td>结算</td><td>周期性结算</td><td>MVP版本统一T+7结算，后续业务希望做成可by商家进行配置</td></tr><tr><td>差错处理</td><td>关退</td><td>24小时关单</td></tr><tr><td>拒付</td><td>Chargeback</td><td>PIPO将chargeback的交易通知给生服</td></tr><tr><td rowspan="2">合规</td><td>KYB/KYC</td><td><ul><li>TH：PIPO合规出审核系统、审核人力</li><li>ID：由业务侧GNE审核</li></ul></td></tr><tr><td>同名验真</td><td>合规接入部分渠道的同名验真能力</td></tr><tr><td rowspan="2">营销</td><td>营销补差</td><td>生服平台为保证商品全网最低，用户看到的商品定价更低，支付的金额更低。通过平台补贴，给予商家的结算款，还是保持团购价。举例：商品原价100，用户看到的价格为80，平台补贴20。用户支付成功后，待分账户+80，从平台营销账户补贴20进待分账，该笔交易待分账总金额为100</td></tr><tr><td>商家返佣</td><td>当商家GMV达到一定金额后，平台会奖励商家，将一部分平台佣金返还给商家。生服使用PIPO的book transfer转账能力，实现平台佣金户向商家基本户进行资金划转</td></tr></tbody></table>



<table><colgroup><col/><col/><col/></colgroup><thead><tr><th><b>Module</b></th><th><b>Function</b></th><th>Description</th></tr></thead><tbody><tr><td rowspan="2">Merchant Services</td><td>Merchant Onboarding</td><td><ul><li>After the merchant completes the platform settlement through the review of the raw service side governance and has the settlement demand, the merchant will enter the PIPO settlement process.</li><li>The information collected when settling on the raw service platform will be passed to PIPO, and what needs to be additionally collected by PIPO will be provided by PIPO with a page for the merchant to fill out and submit.</li></ul></td></tr><tr><td>KOL Onboarding</td><td>It is divided into 2 modes:<ul><li>CPT mode<ul><li>Application scenario: Open-loop mode, the platform directly pays the commission to the talent through MP (already ready to go online).</li><li>Onboarding: Onboard in MP, and MP uses the PIPO compliant KYC ability.</li></ul></li><li>CPS mode<ul><li>Application scenario: Closed-loop mode, after the talent brings goods, the revenue is split from the merchant's income.</li><li>Onboarding: Onboard in the PIPO merchant service.</li></ul></li></ul></td></tr><tr><td>Cashier</td><td>Embedded Cahsier</td><td>The front end adopts the Natvie cashier, which is divided into the first payment and the second payment:<ul><li>The embedded cashier is used for the first payment, and the order placement and payment request interact with the server of TTLS through the embedded cashier.</li><li>The six-screen cashier is used for the second payment, and the payment request is initiated by PIPO using nonce.</li></ul></td></tr><tr><td rowspan="2">Trade</td><td>Payin Instant Payment; Second-time Payment</td><td><ul><li>The client-side embedded cashier calls the one-step order placement interface.</li><li>After the first payment fails, the second payment can be initiated on the original transaction order.</li></ul></td></tr><tr><td>Payout</td><td>Support both periodical automatic payment and withdrawals for merchants and KOLs.</td></tr><tr><td>Payment Methods</td><td>PI Clip</td><td>ID support shared PI with TTS; TH support shared PI with TTS and TTL.</td></tr><tr><td rowspan="2">Refund</td><td>Refund to Origin; Second-time refund</td><td><ul><li>Support user-initiated refund before redemption, and appeal refund within 7 days after redemption.</li><li>After the first refund fails, the payment method can be changed, and the second refund can be initiated on the original refund order.</li></ul></td></tr><tr><td>Refund to Credit</td><td><ul><li>Do not support the original route refund and the payment method of refund to consignment transfer (legal pending), and need to support refund to credit.</li><li>The credit in the raw service scenario cannot be withdrawn, there needs to be an expiration time, and it can only be interoperable with TTS.</li></ul></td></tr><tr><td>Settlement</td><td>Periodical Settlement</td><td>The MVP version unifies T+7 settlement, and it is hoped that the subsequent business can be configured by the merchant.</td></tr><tr><td>Difference</td><td>Order Close and Refund</td><td>Close the order in 24 hours.</td></tr><tr><td>Chargeback</td><td>Chargeback</td><td>PIPO notifies TTLS of the chargeback transaction.</td></tr><tr><td rowspan="2">Compliance</td><td>KYB/KYC</td><td><ul><li>TH: PIPO compliance audit system and audit manpower.</li><li>ID: Conducted by TTLS GNE.</li></ul></td></tr><tr><td>Same-name verification</td><td>Compliance access to the same-name verification ability of some channels.</td></tr><tr><td rowspan="2">Marketing</td><td>Subsidy</td><td>In order to ensure the lowest price of goods across the whole network on the raw service platform, the product pricing seen by users is lower and the amount paid is also lower. Through the platform subsidy, the settlement amount given to the merchant still remains the group purchase price. </td></tr><tr><td>Merchant reward</td><td>When the merchant's GMV reaches a certain amount, the platform will reward the merchant and return a part of the platform commission to the merchant. The raw service uses the PIPO book transfer transfer ability to realize the transfer of funds from the platform commission account to the merchant's basic account.</td></tr></tbody></table>

 



### 支付方式 Payment Methods

- **ID**

  <table><colgroup><col/><col/><col/><col/><col/><col/><col/><col/></colgroup><thead><tr><th>Use Scenario</th><th>Payment Type</th><th>Payment Method</th><th>Payment Model</th><th>Priority <blockquote><p>P00 = 0905</p><p>P0 = 1101</p></blockquote></th><th>Get saved PI from TTS\TTLive<blockquote><p>PI Clip</p></blockquote></th><th>Support Refund</th><th>Order% <blockquote><p>Refer to TTS in May 2024</p></blockquote></th></tr></thead><tbody><tr><td rowspan="4">Checkout</td><td>✅CCDC</td><td>CCDC<blockquote><p>Visa\MasterCard\Amex\JCB</p></blockquote></td><td>Tokenize and Pay</td><td>P00</td><td>✅</td><td>✅</td><td>0.35%</td></tr><tr><td>✅Bank Transfer<br/>(18 banks)</td><td>Virtual Account</td><td>Pay</td><td>P0</td><td>❌</td><td>❌</td><td>15.04%</td></tr><tr><td>✅Wallet</td><td>DANA</td><td>Pay On Token</td><td>P0</td><td>✅</td><td>✅</td><td>3.33%</td></tr><tr><td>✅Wallet</td><td>GoPay</td><td>Pay On Token</td><td>P0</td><td>✅</td><td>✅</td><td>1.61%</td></tr><tr><td>Refund</td><td>✅Bank Account</td><td>Bank Account</td><td>Pay On Token</td><td>P0</td><td>✅</td><td>-</td><td>-</td></tr><tr><td rowspan="2">Withdrawal</td><td>✅Bank Account</td><td>Bank Account</td><td>Pay On Token</td><td>P0</td><td>✅</td><td>-</td><td>-</td></tr><tr><td>✅Wallet</td><td>DANA</td><td>Pay On Token</td><td>P0</td><td>✅</td><td>-</td><td>-</td></tr></tbody></table>
- **TH**

  <table><colgroup><col/><col/><col/><col/><col/><col/><col/><col/></colgroup><thead><tr><th>Use Scenario</th><th>Payment Type</th><th>Payment Method</th><th>Payment Model</th><th>Priority <blockquote><p>P00 = 0905</p><p>P0 = 1101</p></blockquote></th><th>Get saved PI from TTS\TTLive<blockquote><p>PI Clip</p></blockquote></th><th>Support Refund</th><th>Order% <blockquote><p>Refer to TTS in May 2024</p></blockquote></th></tr></thead><tbody><tr><td rowspan="7">Checkout</td><td>✅CCDC</td><td>CCDC<blockquote><p>Visa\MasterCard\Amex</p></blockquote></td><td>Tokenize and Pay</td><td>P00</td><td>✅</td><td>✅</td><td>1.77%</td></tr><tr><td rowspan="5">✅mBanking</td><td>Kasikorn Bank </td><td>Pay</td><td>P0</td><td>❌</td><td>❌</td><td>7.57%</td></tr><tr><td>Siam Commercial Bank(SCB)</td><td>Pay</td><td>P0</td><td>❌</td><td>❌</td><td>4.73%</td></tr><tr><td>Krungthai Bank</td><td>Pay</td><td>P0</td><td>❌</td><td>❌</td><td>3.56%</td></tr><tr><td>Bank of Ayudhya (BAY)</td><td>Pay</td><td>P0</td><td>❌</td><td>❌</td><td>0.6%</td></tr><tr><td>Bangkok Bank (BBL)</td><td>Pay</td><td>P0</td><td>❌</td><td>❌</td><td>0.03%</td></tr><tr><td>✅Wallet</td><td>TrueMoney</td><td>Pay</td><td>P0</td><td>❌</td><td>✅</td><td>5.09%</td></tr><tr><td>Refund</td><td>✅Bank Account</td><td>Bank Account</td><td>Pay On Token</td><td>P0</td><td>✅</td><td>-</td><td>-</td></tr><tr><td rowspan="3">Withdrawal</td><td rowspan="2">✅Bank Account</td><td>Bank Account</td><td>Pay On Token</td><td>P0</td><td>✅</td><td>-</td><td>-</td></tr><tr><td>Bank Account Proxy</td><td>Pay On Token</td><td>P0</td><td>✅</td><td>-</td><td>-</td></tr><tr><td>✅Wallet</td><td>Truemoney</td><td>Pay On Token</td><td>P0</td><td>✅</td><td>-</td><td>-</td></tr></tbody></table>

## 系统交互 System Interaction

<whiteboard token="GMXswFFDmhH27XbJ3ublgZnugVf"></whiteboard>





# 附录 Appendix

## 商家体验——KA商家端使用实地调研

<cite doc-id="IDYOd2CRPo1NwrxQBrVlgdf9giw" file-type="docx" title="[UR] 泰国+印尼KA商家端产品实地调研报告 - June 24" type="doc"></cite>

## 用户体验——Grab平台券 vs TTLS开环券

<callout emoji="🤔">
**作为用户的几个感受：**
1. **预付券入口和购买后券的入口普遍不容易找到**，尤其是购买后的入口容易被忽略（开环券是在inbox-notification中查看），用户体验不好
2. **Grab的下单过程整体比较丝滑，TT开环券页面多，链路长**

   1. Grab简洁易用，相比开环步骤少，方便快速搜索和挑选下单
3. **店员培训也很重要**，Grab对店员的培训更到位，核销熟练；TT开环券部分门店店员不知道怎么核销
4. **Grab在有效期内发起退款后，基本都是秒退，退款体验较好；TT开环券，受商家规则约束无法退款，用户体验一般**
</callout>

- **TTLS开环券体验**

<grid>
<column width-ratio="0.100000">
![图片展示了一位女性在TOMORO COFFEE门店外的场景。她手持一杯咖啡和一张优惠券，背景中可见店内环境。图片上方有文字“Cup-nya aku bayarin 100ribu?”，意为“我的咖啡是100000盾买的”。图片下方是TOMORO COFFEE的Instagram账号信息，显示距离约为14.5公里，以及一条关于“WAR TIKET KONSER?! WAR cup exclusivenya TOMORO COFFEE!”的帖子。该图片可能用于展示用户在TOMORO COFFEE门店消费体验。](https://feishu.cn/file/EGY9b82nGoInPRxGW04lP1yFgYH)
FYP
</column>
<column width-ratio="0.100000">
![图片展示的是TOMORO COFFEE Greenlake在Grab平台的页面。页面显示店铺位于Tangerang City，评分5.0，有3条评论。下方有“Add to Favorites”按钮。页面中部有“Deals”板块，展示了两款团购优惠，分别是“Very Matcha Series”和“Buy 2 Only 38K”，均标注使用有效期至2024年5月31日，确认即时，不可退款。该图片与文档中“Grab团购券体验”部分相关，呈现了Grab平台商家第三方页面中团购券的展示情况。](https://feishu.cn/file/Fh0tb1wM0ovZCDxOUoAlRGr4gF0)
POI Detail
</column>
<column width-ratio="0.100000">
![图片展示的是TikTok Local Service（TTLS）平台中“Best Americano Deal”团购券的详情页面。页面上方有“BEST AMERICANO DEAL”及“30RB 37RB”的价格信息，下方是饮品和面包的图片。券名为“Best Americano Deal”，使用有效期至2024年5月31日，不可退款。券价为30,000印尼盾，描述为购买一杯大号热饮或冷饮（Choco Danish或Butter Croissant）各一份，仅限堂食和外带，不适用于外卖。下方“How to use”部分说明购买后可在商家端查看券码。](https://feishu.cn/file/Vp52bi3WDoKvgNxSO25lx8NOgsh)
PDP
</column>
<column width-ratio="0.100000">
![图片展示的是TikTok Local Service共享的TikTok团购券详情页面。页面上方显示“Voucher Pack Detail”，并有“Best Americano Deal 30RB 37RB”的促销信息，配有饮品和面包的图片。下方是“Best Americano Deal”套餐介绍，包含购买1杯大号热饮和2种菜品的优惠。券码部分显示为“TikTok | Best Americano Deal”，有效期30天，原价37000印尼盾，现价30000印尼盾，有“Buy”购买按钮。该图片与文档中“查看券码”部分上下文对应，直观呈现了团购券的详细信息。](https://feishu.cn/file/VN0Gbftoqou43vx7vp9l7sjpgtx)
端内打开商家第三方页面
</column>
<column width-ratio="0.100000">
![图片展示的是TOMORO COFFEE的订单支付页面。页面显示订单号为PY2024051914491733...，需在2024年5月19日15:04前支付，金额为30,000印尼盾。支付方式有DANA、LinkAja、OVO、ShopeePay等电子钱包选项。页面左上角有关闭按钮，右上角有更多选项按钮。该图片与文档中“端内打开商家第三方页面”内容相关，展示了在TOMORO COFFEE端内打开第三方页面时的支付环节。](https://feishu.cn/file/MtSTbPtQVoyCdExqizEl8b09gih)
提单页
</column>
<column width-ratio="0.100000">
![图片展示的是Grab平台中Tomoro Coffee的订单结算页面。页面顶部显示当前时间为14:49，有网络、电量等状态图标。上方有“Checkout - #PY2024051914491733...”及网址信息。中间部分有“ORDER SUMMARY”标题，下方有“TOMORO COFFEE”店铺标识及“English”语言选项。画面中间有手拿手机的插画，下方文字提示“Redirecting you to DANA checkout page in a moment...”，底部有“POWERED BY xendit”标识。该图片与文档中Grab平台券使用体验的内容相关，呈现了其订单结算流程中的一个环节。](https://feishu.cn/file/SnUfbv3ALonYTex0XqrlHUh3gXb)
中转页跳转支付方式
</column>
<column width-ratio="0.100000">
![图片展示的是DANA支付页面，显示时间为14:50，网络为4G。上方有“DANA”标识及“你正在访问：https://m.dana.id/m/igp/new/inputP...”字样。页面提示输入DANA ID，下方输入框中显示手机号码“+62 085212109169”。下方弹出“Enter the OTP code”窗口，提示验证码已发送至+62852****9169，可通过WhatsApp接收，下方有数字键盘用于输入验证码，右下角有“X”关闭按钮。该图片与文档中支付流程相关，展示了DANA支付时输入验证码的步骤。](https://feishu.cn/file/KGEyb0zl9odzdZxKwYilfaN0gpg)
![图片展示的是Grab团购券支付页面。页面顶部显示当前时间为14:51，有电量、4G网络等图标。上方有“Let's Pay!”字样及商家信息。中间部分是支付确认信息，显示将使用DANA余额支付30,000印尼盾，有“Change”选项可修改支付方式。底部有“DANA PROTECTION”标识，说明交易受保护，且有“PAY Rp30.000”蓝色支付按钮。该图片与文档中Grab团购券支付体验的内容相关，直观呈现了支付时的界面情况。](https://feishu.cn/file/AvhobLvmMo003bxcVIPldGgyg3f)
支付
</column>
<column width-ratio="0.100000">
![图片展示的是DANA支付成功界面。上方显示“Payment Status”及访问网址，右上角有三个点。中间大圆圈内有勾选标志，下方文字为“Payment Success! Transaction paid successfully with DANA Balance”，并显示支付金额“Rp30.000”，右侧有“View Detail”按钮。下方有“Thank you for using DANA”提示，还有一段推广语“Cukup satu aplikasi untuk semua kebutuhanmu!”及下载按钮。底部有“QUICK SURVEY”问卷调查，以及“CLOSE”关闭按钮。](https://feishu.cn/file/NTufbJjhPo91vGxdyIYlU6yygHe)
支付结果页
</column>
<column width-ratio="0.100000">
![图片展示的是Grab平台Tomoro Coffee商家端支付结果页。页面显示订单已成功支付，支付金额为30,000印尼盾，支付时间为2024年5月19日2:49，支付方式为DANA。下方有“Redirecting back in 1s, or click here”提示，以及“Get Rp 100,000 Bonus in selected merchants!”的nexCard广告。该图片与文档中“Grab团购券体验”部分相关，直观呈现了Grab平台在支付成功后的页面情况。](https://feishu.cn/file/Bsmib0mI7oINzIx3C9LlLvQbgTs)
跳转回订单结果页
</column>
<column width-ratio="0.100000">
![图片展示的是TikTok Local Service在Grab平台的订单完成页面。页面显示订单已成功完成，TOMORO账户已收到优惠券，优惠券为“Best Americano Deal”，金额为30,000印尼卢比，有效期至2024年6月17日。页面还提示优惠券内容为“TikTok | Best Americano Deal，Min 2 products”，并有“Use”按钮可使用优惠券。下方说明了使用优惠券的步骤，分别是点击“Use”按钮和向店员展示二维码。该页面与文档中对Grab平台券用户体验的描述相关，体现了其购买后券的入口及使用说明。](https://feishu.cn/file/Drt7bCtsdoCl8RxZaWdl7UqWg2c)
![图片展示的是TOMORO COFFEE的优惠活动页面。页面上方显示当前时间为14:53，有网络、电量等状态图标。中间部分有“FREE TOMORO AREN LATTE”等促销信息，以及“Hanya di Aplikasi”（仅限应用）提示。下方有电话号码“+86 180****1823”。弹出窗口中提示“Show this QR Code to cashier in-store”，并显示一个二维码，下方有“SKIP THE QUEUE Order Via APP”和“Order”按钮。该图片与文档中“查看券码”部分对应，展示了查看券码时的界面。](https://feishu.cn/file/DbZQbwWtroO47Gx3FbUlfmcbgqh)
查看券码
</column>
</grid>

- **Grab团购券体验**

<grid>
<column width-ratio="0.200000">
![图片展示的是Grab平台Tomoro Coffee - Kuningan City店铺页面。页面上方显示店铺名称及搜索框，下方有“Beli Banyak Makin Hemat!”的促销信息，显示可享受35%折扣（使用Promo Code）。店铺评分4.6分，距离12.4公里。页面中部有“25% MON-SUN Rp50,000 Dine-in Vou...”的优惠券信息，右下角有“See all 312 outlets”选项。底部展示了Dum Dum Thai Drinks Express - Kuningan City店铺信息。该图片与文档中Grab平台券用户体验内容相关，直观呈现了平台券的展示样式。](https://feishu.cn/file/GAy1bAA3boPoZ9xaZRblgL3SgZf)
搜索detail
</column>
<column width-ratio="0.200000">
![图片展示的是Grab团购券的搜索详情页面。页面上方有“BELI BANYAK MAKIN HEMAT!”及“35% (dengan Promo Code)”等促销信息，下方显示“Rp25.000 Dine-in Voucher Rp18.750”及商家信息。页面中部有“Usage terms”条款，包括使用时间、有效期、每笔限用一张等内容，还标注“100% refund guaranteed if you change your mind or voucher expires”。底部有“Apply offers”按钮和“Buy for Rp18.750”购买按钮。该图片与文档中Grab团购券体验部分上下文对应，直观呈现了团购券的购买页面及信息。](https://feishu.cn/file/VRZXbEvdHo3AjUxN8pZlav6fgFh)
PDP
</column>
<column width-ratio="0.200000">
![图片展示的是Grab团购券支付结果页。上方显示订单金额为Rp19350.00，下方有“View dine - in vouchers”按钮。画面中部弹出支付成功的提示框，显示支付金额为Rp19.350，且团购券已添加至优惠券钱包。该图片与文档中“Grab团购券体验”部分相关，直观呈现了Grab团购券支付成功后的界面情况。](https://feishu.cn/file/IyGCbaQuhoDgA6xy3iXlvAhBgsg)
直接支付
</column>
<column width-ratio="0.200000">
![图片展示的是TikTok Local Service（TTLS）平台中Grab团购券的券列表页面。页面上方显示当前时间为15:22，有信号、4G及电量图标。页面标题为“Dine-in vouchers”，下方有“TOMORO COFFEE - Kuningan City”等信息，显示“Rp25.000 Dine-in Vouc... Rp19.350”及“Use Now”按钮，还有“25% MON-SUN”标识。该图片与文档中“TTLS开环券体验”部分相关，直观呈现了TTLS平台团购券的展示样式。](https://feishu.cn/file/IgeQbucVfoLYQmxiBrNlr6J0gNg)
券列表
</column>
<column width-ratio="0.200000">
![图片展示的是Grab团购券查看券码界面。上方显示“Show QR code to the cashier”字样，中间有一个二维码，下方是“Voucher ID: GV-4QN200U5”及“QR not working? Tap to refresh”提示。该图片与文档中“查看券码”部分对应，直观呈现了用户在Grab平台查看团购券二维码的操作结果，方便店员扫码核销，体现了Grab在用户使用体验方面的设计。](https://feishu.cn/file/DMpmbEDeSovYagxfTvtljFspgDh)
查看券码
</column>
</grid>



## 本地生服商品类型

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td><b>商品类型</b></td><td><b>类型含义</b></td><td><b>场景描述</b></td></tr><tr><td>卡券类-团购券</td><td><ul><li>商品售卖的内容：卡券</li><li>卡券兑换：服务</li><li>核销次数：1次</li></ul></td><td>支付后获得团购券，<b>用户</b>持团购券到店核销<blockquote><p>如：直接购买餐饮团购券</p></blockquote></td></tr><tr><td>卡券类-代金券</td><td><ul><li>商品售卖的内容：卡券</li><li>卡券兑换：现金支付</li><li>核销次数：1次</li></ul></td><td>支付后获得代金券，<b>用户</b>持代金券到店核销兑换现金支付<blockquote><p>如：直接购买商家代金券</p></blockquote></td></tr><tr><td>卡券类-次卡</td><td><ul><li>商品售卖的内容：卡券</li><li>卡券兑换：服务</li><li>核销次数：n次</li></ul></td><td>支付后获得次卡，<b>用户</b>持卡到店核销，一张卡可多次核销<blockquote><p>如：直接购买到综次卡</p></blockquote></td></tr><tr><td>卡券类-预售券</td><td><ul><li>商品售卖的内容：卡券</li><li>卡券兑换：预约服务权益</li><li>核销次数：1次</li></ul></td><td>支付后获得预约凭证，<b>用户</b>持凭证预约日历服务<blockquote><p>如：酒旅先买后约的预售单，到综先买后约的预售单</p></blockquote></td></tr><tr><td>卡券类-平台通兑券</td><td><ul><li>商品售卖的内容：卡券</li><li>卡券兑换：服务</li><li>核销次数：1次</li></ul></td><td>兑换成功后获得团购券/代金券，<b>用户</b>持券到店核销<blockquote><p>如：通兑券的兑换单，通兑品的兑换单</p></blockquote></td></tr><tr><td>服务类-预订商品</td><td><ul><li>商品售卖的内容：服务</li><li>服务方式：到店接待使用</li></ul></td><td>预订成功后，<b>用户</b>持凭证到店服务<blockquote><p>如：直接下预订单，或到综先买后约的预订单</p></blockquote><blockquote><p>如：直接购买到综次卡</p></blockquote></td></tr><tr><td>服务类-配送</td><td><ul><li>商品售卖的内容：服务</li><li>服务方式：配送到家</li></ul></td><td>预订成功后，商家接单后生成配送任务，<b>骑手</b>按约定时间配送。<blockquote><p>如：直接下预订单，或到综先买后约的预订单</p></blockquote></td></tr></tbody></table>

---

*Thanks for reading!*

*感谢阅读。若有任何建议，可随时与我<cite type="user" user-id="ou_10d86b850c644f473c93269fbe246733" user-name="di zeng"></cite>联系*

*June 2024*
