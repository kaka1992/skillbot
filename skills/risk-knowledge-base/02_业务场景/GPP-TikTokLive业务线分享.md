---
title: GPP-TikTok Live业务线分享//GPP-TikTok Live sharing
category: 业务场景
source_url: https://bytedance.sg.larkoffice.com/wiki/ACYSwba3RiKyahkkcrAcxVx1nLb
source_token: ACYSwba3RiKyahkkcrAcxVx1nLb
source_type: wiki
doc_type: 业务介绍
tags: [直播, TikTokLive, PIPO, GPP, 成功率, 3DS, 指标]
metrics: [支付成功率, TSR, Payout成功率, PSR, 到账时长, 自营占比, 健康度]
business_lines: [直播]
summary: 介绍TikTok直播打赏体系及官网充值、主播提现、周期性打款、订阅等场景与PIPO支付能力
last_synced: 2026-08-12
---

## 适用场景
面向需要理解 TikTok 直播营收与支付场景的读者，介绍直播打赏体系及官网充值、主播提现、周期性打款、官网订阅等重点场景的用户链路、PIPO 产品能力、支付方式与数据表现。适用于风控、支付对接人员理解直播场景。

## 核心概念
- 四个角色：平台、用户（观众）、主播（创作者）、公会（Creator Network）。
- 打赏体系：金币（Coins，用户以法币购买的平台虚拟代币，1 金币=0.01USD）、钻石（Diamonds，激励/荣誉符号）、礼物（Gifts，用金币兑换赠送主播）。
- 主要场景：官网充值（Webapp Recharge）、主播提现（Live Gift Rewards）、周期性打款（Monthly Earnings）、官网订阅（Webapp Subscription）、Income+。
- 团队归属：官网充值、主播提现属 Revenue 团队；其余场景属 Money Platform。
- 主播提现/income+/周期性打款区别：美国因 “Stored Value” 合规限制走周期性打款（每月 15 日被动打款，仅 USD，FBO/Non-FBO）。
- PIPO 能力：Payin 即时付与协议扣、Payout 标准代发、绑卡 hostedpage、dropin 收银台、iframe 组件、3DS 认证、原路退款/Payout 退款。

## 关键指标口径
- 自营占比：官网充值在总体充值交易中的占比（直播重要目标之一，官网非 IAP 渠道费用更低）。
- Paycore 支付成功率 / TSR：分支付类型统计的支付成功率（如 CCDC 69.48%、E_WALLET 77.45%、BANK_TRANSFER 86.60%）。
- Payout 成功率：主播提现总体约 96.5%，每月约 200 万笔打款。
- 到账时长（Arrival Time，min-50 分位数）：各支付方式的提现到账时间中位数。
- 金币定价口径：初始价值 1 金币=0.01USD，叠加渠道费、税费构成用户所见价格。

## 规则 / 策略要点
- 提升官网充值占比与健康度，降低渠道支付成本以提升营收。
- 绑定并支付（bind and pay）：电子钱包包装为可勾选 savebox 的绑定支付，经 A/B 验证提升支付成功率。
- 退款政策：正常不支持退款；例外为购入 14 天内未使用（日本除外）及未成年人退款（每账户一次）。
- 主播提现区域逻辑：绑定 PI 时可在商户号支持的国家中选 2 个国家/地区绑定支付方式。
- 周期性打款：应对未持牌 Money Transmission 与 Stored Value 风险，Batch Payout 通过事前 dry run、事中调度保障打款安全。
- 风控：钱包页请求 pipo 风控 event=payout_pre_withdraw_request；直播为黑产高发场景，需拦截黑产并减少对正常用户影响。

## 原文正文

<!-- source_type: wiki | doc_id: ACYSwba3RiKyahkkcrAcxVx1nLb | title: GPP-TikTok Live业务线分享 -->

<title>GPP-TikTok Live业务线分享//GPP-TikTok Live sharing</title>

# 业务信息概览 // Overview

<blockquote><p><cite doc-id="AdeEdCxzHoag9wxMDaRlFS0Ogqh" file-type="docx" title="TikTok LIVE Wallet &amp; Payment Business Overview" type="doc"></cite></p><p><cite doc-id="Ur7cdfEGBo4v5sxYxPKcit4Gnpp" file-type="docx" title="[Global Payment ONLY] TikTok LIVE One Page" type="doc"></cite></p></blockquote>

直播不是一个业务，而是一个业务组合，对应着多个业务团队和多种业务场景。直播业务里有四个主要角色：平台、用户、主播（也称创作者）、公会。平台提供能力，主播提供内容，公会管理主播，用户为这些服务付费。为了激励公会引入更多优质主播、主播持续生产优质内容，从而促进用户付费，平台也会发放奖励给主播。这些场景交织在一起，形成了直播业务组合。

> TikTok Live is not a single business line, it's a comibination of mulitiple business line including several business teams and business scenarios. There are four main roles in the LIVE Business Ecosystem: Livestream Platform, Viewers, Creators and Creator Network. The Platform provides capability, Creators provide content, Creator Network manages creators, while Viewers pay for those services. In order to encourage Creator Networks to bring in more high-quality creators to the platform and creators to continually post high-quality content to draw more viewers to pay, the Platform will give rewards to them. These scenarios are intertwined to form the overall live streaming business.

<whiteboard token="LGfswuxdRhLvUFbdNAElUdPEglo"></whiteboard>

<callout emoji="💎">
**打赏体系的几个概念**
**金币：**属于平台的虚拟代币，用户需要使用法定货币购买。金币在平台系统内具有固定价值，类似于游戏厅的游戏币。从法律角度看，此类代币只能在平台内流通，例如购买虚拟礼物等增值服务，但不能兑换成现金或转让给他人。
**钻石：**平台为鼓励创作者持续生产高质量内容而给予的一种激励符号/荣誉符号。这种荣誉符号代表创作者内容的受欢迎程度。根据收集到的钻石数量，平台会奖励创作者相应的法定货币作为平台激励。具体激励政策由平台制定，平台保留根据业务发展进行调整的权利。
**礼物**：赠送给主播的虚拟礼物，用于表达用户对主播的喜爱。用户可使用Coins 兑换虚拟礼物，并向主播送礼。
> **Several Concepts of the Reward System**
> 
> **Coins**: As a matter of platform virtual tokens, the coins are purchased with fiat money by users. It has a fixed value within the platform, similar to the game tokens in game centers. From a legal perspective, such tokens shall only circulate within the platform, like purchasing value-added services such as virtual gifts, and cannot be redeemed for cash nor transferred to other people. 
> 
> **Diamonds**: An incentive symbol/honor symbol given by the platform to encourage creators to continuously generate high-quality content, which represents the popularity of creators' content. Based on the number of Diamonds collected, the platform rewards equivalent fiat money to creators as platform incentives. The specific incentive policy is formulated by and subject to the platform.
> 
> **Gifts**: Virtual gifts given to the hosts are an expression of users' affection. Users can exchange coins for virtual gifts and send gifts to the hosts.
</callout>



其中，官网充值、主播提现由直播Revenue团队与PIPO对接，其他场景主要由Money Platform与PIPO对接。

> Among them, the Webapp Recharge and Live Gift Rewards belong to the Revenue team, while other scenarios belong to the Money Platform team.

<whiteboard token="Oem3wgm1hhffjPbplg0lWRMYgZf"></whiteboard>

主要业务场景及使用的PIPO能力，概括如下 // Busniess scenario and the capability PIPO provide：

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><td><b>业务</b><b>场景 // Scenario</b></td><td><b>场景概述 // Description</b></td><td><b>所属业务团队 // Team</b></td><td><b>PIPO 能力概述 // PIPO product description</b></td></tr><tr><td>Webapp Recharge<blockquote><p>官网充值</p></blockquote></td><td>观看直播时，用户可以选择使用金币兑换礼物，送给主播。该场景支持用户在手机、PC官网购买金币。相较于TikTok内的IAP充值，官网充值价格更加优惠。<blockquote><p>When watching live streams, viewers can exchange coins for gifts and send them to the creators. This scenario supports viewers purchasing coins on mobile and the PC official website. Compared with the IAP recharge within TikTok, the recharge price on the official website is more favorable.</p></blockquote></td><td>TikTok LIVE-Revenue Product</td><td><ul><li><b>服务端能力：</b>Payin场景，即时付能力</li><li><b>前端能力：</b>Live自建收银台，CCDC使用PIPO iframe组件</li></ul><blockquote><ul><li>Server end capabilities: Payin scenario, instant payment capability</li><li>Front-end capabilities: Live self-built cashier, CCDC uses the PIPO iframe component</li></ul></blockquote></td></tr><tr><td>Live Gift Rewards<blockquote><p>主播提现</p></blockquote></td><td>主播直播时收到的礼物，会按照一定业务逻辑转换成可提现余额。该场景支持主播进行收入的提现。<blockquote><p>The gifts received by creators during live streaming will be converted into withdrawable balances according to certain business logic. This scenario helps the creators to withdraw their income.</p></blockquote></td><td>TikTok LIVE-Revenue Product</td><td><ul><li><b>服务端能力：</b>Payout场景，标准代发能力</li><li><b>前端能力：</b>使用PIPO 绑卡 hostedpage，提现 Drop-in （one wallet 项目范围的国家，该页面由MP维护）</li></ul><blockquote><ul><li>Server end capabilities: Payout scenario, standard payout product</li><li>Front-end capabilities: Use the PIPO card binding hosted page, withdrawal dropin component (for countries within the scope of the one wallet project, this page is maintained by MP)</li></ul></blockquote></td></tr><tr><td>Monthly Earnings<blockquote><p>周期性打款</p></blockquote></td><td>除打赏外，主播在平台上有多种其他类型收入。如，平台发放的奖励、订阅、发布付费视频等。这些非打赏类型收入，大部分通过Monty Platform 提供的Monthly Earnings产品，周期性向用户进行打款。<blockquote><p>In addition to rewards, the creators have various other types of income on the platform. For example, rewards issued by the platform, subscriptions, publishing paid videos, etc. Most of these non-reward types of income are disbursed to users periodically through the Monthly Earnings product provided by Monty Platform.</p></blockquote></td><td>Money Platform</td><td><ul><li><b>服务端能力：</b>Payout场景，标准代发能力</li><li><b>前端能力：</b>使用PIPO 绑卡 hostedpage</li></ul><blockquote><ul><li>Server end capabilities: Payout scenario, standard payout product</li><li>Front-end capabilities: Use the PIPO card binding hostedpage</li></ul></blockquote></td></tr><tr><td>Webapp Subscription<blockquote><p>官网订阅</p></blockquote></td><td>订阅是独立于礼物打赏的营收场景，主播以一定周期的契约方式，向希望增强“直播间-主粉关系”体验的用户，提供的付费增值服务。<blockquote><p>Subscription is a revenue scenario independent of gift rewards. The creator provides paid value-added services to users who wish to enhance the "live room - creator &amp; fan relationship" experience.</p></blockquote></td><td>Money Platform</td><td><ul><li><b>服务端能力：</b>Payin场景，即时付和协议扣产品</li><li><b>前端能力：</b>使用PIPO dropin收银台</li></ul><blockquote><ul><li>Server end capabilities: Payin scenario, instant payment and agreement deduction products</li><li>Front-end capabilities: Use the PIPO dropin component</li></ul></blockquote></td></tr><tr><td>Income + </td><td>除打赏外，主播在平台上有多种其他类型收入。其中，部分业务的收入会进入到Income +钱包，创作者可按需进行提现。<blockquote><p>In addition to rewards, the creators have various other types of income on the platform. Among them, the income from some businesses will enter the Income + wallet, and the creators can withdraw as needed.</p></blockquote></td><td>Money Platform</td><td><ul><li><b>服务端能力：</b>Payout场景，标准代发能力</li><li><b>前端能力：</b>使用PIPO 完整 hostedpage Payout收银台</li></ul><blockquote><ul><li>Server end capabilities: Payout scenario, standard payout product</li><li>Front-end capabilities: Use the PIPO hostedpage withdrawal cashier</li></ul></blockquote></td></tr></tbody></table>

<callout emoji="🤖">
**主播提现、income+、周期性打款 三者区别：**
- **主播提现：**处理主播的直播收入，主要是用户赠送礼物产生的主播收益，主播在TikTok能够看到打赏产生的收益余额，进行主动提现。除美国外，所有国家打赏产生的收入，均通过主播提现处理。美国的特殊之处在于，根据美国合规要求，TikTok现有的账户余额概念落入了监管定义的“Stored Value”范围内，从事该类业务需要持相关牌照。TikTok和PIPO均暂无牌照，为规避合规风险，需要弱化余额概念，通过Money Platform 提供的周期性打款方案支付主播收入。
- **income+：**TikTok内场景众多，多个场景存在向创作者支付酬劳的诉求，有多种打款方式、多个钱包并存。income+ 诞生之初，旨在打造一个TikTok 内的统一钱包，提供本地币提现能力。但是牌照限制，income+ 逐渐被周期性打款替代。
- **周期性打款：**为了应对未持牌处理用户间交易、未持牌stored value风险，衍生出的打款模式。上线之初只支持FBO 模式，目前经过法务合规认可，在部分国家逐步上线Non-FBO支付方式。与主播提现、income+不同，周期性打款不允许用户主动提现，创作者只能在每个月15号被动接受平台打款。此外，周期性打款标价币种只有USD。
**The differences between Live Gift Reward, income+, Monthly Earnings:**
- **Live Gift Rewards:** It handles the earnings of live Gifts. Creators can see the balance of earnings from rewards on TikTok and make withdrawals. In all countries except the United States, the income generated from rewards is processed through Live Gift Reward. The special case of the United States is that, according to the compliance requirements in the United States, the existing account balance concept of TikTok falls within the "Stored Value" range defined by regulation. To engage in such business, relevant licenses are required. Both TikTok and PIPO do not have licenses currently. To avoid compliance risks, the concept of balance needs to be weakened, and the creators' income is paid through Monthly Earnings provided by the Money Platform.
- **Income+:** There have been numerous business lines within TikTok, and multiple business lines have the demand to pay income to creators. Historically, there have been multiple disbursement methods and multiple wallets coexisting. Income+ aims to create a unified wallet within TikTok and provide the ability to withdraw in local currency. However, due to license and qualification limitations, income+ has gradually migrated to monthly earnings.
- **Monthly Earnings:** It is a disbursement mode derived to deal with the risks of unlicensed processing of transactions between users and unlicensed stored value. At the beginning of its launch, only the FBO mode was supported. Currently, with the approval of legal compliance, the Non-FBO payment method has been gradually launched in some countries. Different from Live Gift Rewards and income+, Monthly Earnings does not allow users to make withdrawals. Creators can only passively receive disbursements on the 15th of each month. In addition, monthly earnings only support USD.
</callout>

# 重点场景介绍 // Key Scenarios

## 官网充值 // Webapp Recharge

<callout emoji="🎁"><p>官网充值体验方式 // How to recharge in WebAPP</p><p><cite doc-id="doccnhZjd7rFqnQ1s1iKikZeT2b" file-type="doc" title="我要在TikTok官网充值！// I Wanna Go TikTok Recharge in WebApp" type="doc"></cite> </p></callout>

用户观看直播时，可以选择使用金币兑换礼物，将礼物送给主播。充值即购买金币的过程。目前主要存在两种购买金币的途径，官网充值和端内充值：

- 端内充值是指用户使用Google, Apple提供的IAP（In app purchase）能力进行充值。
- 官网充值则是在TikTok 官网（https://www.TikTok.com/coin/），使用PIPO提供的非IAP支付方式进行充值。

> When users watch live streams, they can exchange coins for gifts and send the gifts to the creators. The process of recharging is the process of purchasing coins. Currently, there are mainly two ways to purchase coins: recharge on the official website and recharge within the app:
> 
> - Recharge within the app means that users recharge using the IAP (In-app purchase) capability provided by Google and Apple.
> - Recharge on the official website is to recharge on the TikTok official website ([https://www.](https://www.tiktok.com/coin/)[TikTok](https://www.tiktok.com/coin/)[.com/coin/](https://www.tiktok.com/coin/)) using the non-IAP payment method provided by PIPO.

对于用户而言，官网充值价格更加优惠。对于直播平台而言，非IAP 支付方式渠道费用更低。因此，提升官网充值在总体充值交易中的占比（也称自营占比），也是直播的重要目标之一，对于头部用户，直播会通过各种线下、线上运营手段，引导用户到官网进行充值。

> For users, the recharge price on the official website is more favorable. For the live streaming platform, the channel fees for the non-IAP payment method are lower. Therefore, increasing the proportion of recharges on the official website (also known as the self-operated proportion) is one of the key objectives for live streaming business. For top users, live streaming will guide them to recharge on the official website through various offline and online operations.

<whiteboard token="YWg3wMuUmhB0q3bKK2ilaOPsglg"></whiteboard>

端内引流入口示例 // Examples of in-app diversion entrances：

<grid>
<column width-ratio="0.499250">
![](https://feishu.cn/file/RXa6bxLvroKJ1gxJ38glCRHsgVg)
</column>
<column width-ratio="0.500750">
![](https://feishu.cn/file/XAkqb0X1GozvoNxoUkTl8n85gm2)
</column>
</grid>

端内充值、引流策略等由业务团队直接负责，与PIPO无直接关联。

> In-app recharge, diversion strategies, etc. are directly managed by the business team, which are not related to PIPO directly. 

#### 用户链路 // User Journey

**充值入口 // Recharge entrance**

目前官网充值有三个主要入口（仅限开通金币充值的国家）

> There are **three main entrances** for coin recharge (only available for countries where webapp top-up is enabled)

<grid>
<column width-ratio="0.333333">
**Entrance** 1⃣️  
个人主页进入充值
> Entrance 1 - go to recharge page from homepage
![](https://feishu.cn/file/ZpTFbLIWXoip06xW0n5ldso8gzh)
</column>
<column width-ratio="0.333333">
**Entrance** 2⃣️
打赏金币不足自动进入充值页面
> Entrance 2 - directed to recharge page automatically if coin balance is short while gifting
![](https://feishu.cn/file/MtExbpZQAoG11YxYhmHlAA1mgIf)
</column>
<column width-ratio="0.333333">
**Entrance 3⃣️**
直播时主动购买金币进入充值页面
> Entrance 3 - click to buy coins while gifting
![](https://feishu.cn/file/PPXHbrk69o9GCLxOlldlCTHpgHb)
</column>
</grid>

**支付流程 // Payment flow**

对于同时支持先绑定后支付和直接支付的支付方式（主要是电子钱包），PIPO会包装成“绑定并支付”形式，下发给业务。用户可通过勾选savebox，决定是否绑定当前支付方式。这种交互形式，经过直播A/B实验验证，能够确保用户有充分选择机会、不影响营收，将用户逐渐转换为绑定用户，提升支付成功率。

> For payment methods (mainly e-wallets) that support both pay after bind and direct payment, PIPO will package them in a "bind and pay" format and response to business. Users can decide whether to bind the current payment method by toggling the savebox. This experience, verified by live A/B experiments, can ensure that users have sufficient choice opportunities without affecting revenue, gradually convert users to bound users, and improve the payment success rate.

![Example](https://feishu.cn/file/BxOGbkvDAoJdpYx6JuYlH0cOgfh)

以Dana 绑定后支付流程为例的完整用户链路  //  Dana pay after bind as example:

<grid>
<column width-ratio="0.166667">
![](https://feishu.cn/file/UM3ubTrfIoFbsKxGQtilH4IlgDb)
Select coins package
</column>
<column width-ratio="0.166667">
![](https://feishu.cn/file/I6RxbT4ckodfA5xN6l5lN2iUgZe)
Select payment method
</column>
<column width-ratio="0.166667">
![](https://feishu.cn/file/PuV9bZIlWotFk8xcmXNlTkvwgJh)
Jump to Dana page
</column>
<column width-ratio="0.166667">
![](https://feishu.cn/file/R84JbdqkWockkdxBMNAlZl1Dgwg)
Input OTP
</column>
<column width-ratio="0.166667">
![](https://feishu.cn/file/AGrIbJGx5o6rTaxXq17lRVsogyg)
Confim bind
</column>
<column width-ratio="0.166667">
![](https://feishu.cn/file/E3fRb5lt9ouB77xURi3lXhHwgIy)
Jump back
</column>
</grid>

<grid>
<column width-ratio="0.200000">
![](https://feishu.cn/file/NEtTbA9OPol3Akxjklkl8Kmfgfd)
Initiate payment automatically
</column>
<column width-ratio="0.200000">
![](https://feishu.cn/file/S3grbh9sKoyhFSxAJH9lOcw0gBJ)
Jump to Dana page
</column>
<column width-ratio="0.200000">
![](https://feishu.cn/file/WxFVbNlKUoQbsIxlfq1lUBSwgVh)
Input PI
</column>
<column width-ratio="0.200000">
![](https://feishu.cn/file/VNzybRiumo8vjgxTdnUl0jCXgoc)
Jump back
</column>
<column width-ratio="0.200000">
![](https://feishu.cn/file/RHhjbl2PJoxbpJxLGBelTbBbgKd)
Payment success
</column>
</grid>

<callout emoji="🤖">
**金币是怎样定价的？**
金币初始价值以美金定价，固定为1金币=0.01USD，再加上渠道费、税费、最终组成用户看到的金币价格。除了个别交易量较小的国家（如黎巴嫩、阿塞拜疆）使用USD标价，其他国家均使用本地币标价。
> **How is the price of coins determined?**
> 
> The initial value of coins is priced in US dollars, fixed at 1 coin = 0.01 USD. In addition to channel fees and taxes, the final price of coins seen by users is composed. Except for several countries with relatively small transaction volumes (such as Lebanon and Azerbaijan) where it is priced in USD, most countries set the price with local currencies.
</callout>

**退款政策 // Refund Policy**

正常情况下直播业务不支持发起退款，两个特殊场景可以退款：

1. 金币购入后14天内未使用（不适用于日本）
2. 未成年人退款。每个账户有一次机会，以“购买人是未成年”作为原因，发起退款申请

> Generally, the live-streaming business does not support refunds. Yet there are two edge cases:
> 
> 1. Coins are not used within 14 days after purchase (not applicable to Japan).
> 2. Refunds for minors. Each account is allowed once to make a refund application due to "recharge by a minor".

PIPO 提供原路退款和Payout能力（对于不支持原路退款的支付方式）支持退款。

> PIPO provides the ability to refund to the original payment method and Payout (for payment methods that do not support refunds to the original payment method).

![原路退款，PIPO仅提供API//Refund to original payment method, PIPO provide API](https://feishu.cn/file/X0t7bzgzZoocLjxCuG4lXQZlgxg)

![通过Payout形式完成非原路退款 // Refund via Payout capability for payment methods don't support refund](https://feishu.cn/file/Pdp0bep9UoWzJbxAqSElVLpFgGd)



#### 产品能力 // Product Capability

- LIVE自建收银台，PIPO提供可用支付方式查询、支付工具管理、单次支付等能力。// LIVE self-built cashier page, PIPO provides capabilities such as querying  payment methods, payment method management, creating transactions and conducting payment.
- 充值主要接口如下 // Main API for recharge: 

<blockquote><p>Refer to <cite doc-id="IiGRdd5saoeqqIxMZiFle2vygkh" file-type="docx" title="TT Live Solution 交接文档" type="doc"></cite></p></blockquote>

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><td><b>场景 // Scenarios</b></td><td><b>API</b></td><td><b>接口描述 // API description</b></td><td><b>调用方 //Caller</b></td></tr><tr><td rowspan="2">充值页面渲染<blockquote><p>Render topup page</p></blockquote></td><td>/payment/v1/nonce</td><td>用于业务前端与PIPO交互<blockquote><p>Used for the front end of the business to interact with PIPO</p></blockquote></td><td>BE</td></tr><tr><td>/payment/v1/payment_methods_v3</td><td>在充值页面渲染可用支付方式icon<blockquote><p>Render available payment method icons on the recharge page</p></blockquote></td><td>FE</td></tr><tr><td rowspan="3">收银台渲染<blockquote><p>Render cashier page</p></blockquote></td><td>/payment/v1/cashier_basic_info</td><td>获取可用支付方式列表、可用PI、表单elements等<blockquote><p>Get the list of available payment methods, available PIs, form elements, etc.</p></blockquote></td><td>BE</td></tr><tr><td>/payment/v1/initiate_payment</td><td>初始化订单，获取pipo单号和收银台链接<blockquote><p>Initialize the order, get the pipo order number and the cashier link</p></blockquote></td><td>BE</td></tr><tr><td>/payment/v1/get_unified_bin_detail</td><td>输入卡号时，查询card bin信息<blockquote><p>When entering the card number, query the card bin information</p></blockquote></td><td>FE</td></tr><tr><td>Delete PI</td><td>/payment/v1/delete_stored_method</td><td>删PI//Delete PI</td><td>BE</td></tr><tr><td rowspan="2">Pay</td><td>/payment/v1/pay</td><td>支付接口，支持支付并绑定//The API to conduct payment and bind&amp;pay</td><td>FE</td></tr><tr><td>/payment/v1/payment_detail</td><td>查单//Order inquiry</td><td>BE</td></tr></tbody></table>



#### 支付方式 // Payment Methods

- 商户号列表 // Merchant ID list  - <cite doc-id="doxcnRVYglYakgm5qVfFsroC5Wd" file-type="docx" title="TTLive直播主体及商户号信息" type="doc"></cite>
- 备用渠道策略 // Channel Redundancy Solution - <cite doc-id="WtfFdW3t8o5oAUx9KW6lUB11gO1" file-type="docx" title="[WIP] TT Live - Payin Channel Redundancy Solution" type="doc"></cite>
- 重点国家策略 - 主要根据国家维度的营收潜力和用户活跃情况制定 // A+ Country Strategy - Mainly based on business revenue potential and user activity

<table><colgroup><col/><col/><col/></colgroup><thead><tr><th><b>支付类型</b><br/>Payment Type</th><th><b>支付方式</b><br/>Payment Method </th><th><b>适用国家</b><br/>Country or Region</th></tr></thead><tbody><tr><td>Bank Account </td><td>PIX, Bank Transfer, PayEasy</td><td>BR, ID, VN, JP</td></tr><tr><td>Cash PIN</td><td>ALFA, INDOMARET, BOLETO, FAMILYMART, LAWSON, etc.</td><td>ID, BR, JP</td></tr><tr><td>CCDC</td><td>VISA, MASTERCARD, AMEX, JCB, DINERS, DISCOVER, etc. </td><td>US, DE, GB, JP, FR, TR, BR, ID, VN, SA, AE, QA, KW, EG</td></tr><tr><td rowspan="5">E-wallets</td><td>DANA, GOPAY, OVO, SHOPEEPAY, LINKAJA</td><td>ID</td></tr><tr><td>LINEPAY, PAYPAY</td><td>JP</td></tr><tr><td>MOMO, ZALOPAY</td><td>VN</td></tr><tr><td>PAYPAL</td><td>US, BR, DE, FR, GB, JP</td></tr><tr><td>PAPARA</td><td>TR</td></tr><tr><td>GP/AP</td><td>GOOGLEPAY, APPLEPAY</td><td>US, DE, GB, FR, SA, AE, QA, KW</td></tr><tr><td>Internet banking</td><td>KLARNA</td><td>DE</td></tr></tbody></table>



#### 数据表现 // Data Performance

- **地域分布**：按交易量计算，ROW占比约71%，TTP/EU分别为22%/6%

![Webapp Transaction Volume \[by Jun.24\]](https://feishu.cn/file/PWLXbXEFxoZLd9xMklZlyczzgos)

- **交易量级**：单日交易量约45万笔，受到 [AP引流曝光事件影响](https://techcrunch.com/2024/04/30/screenshots-suggest-tiktok-is-circumventing-apple-app-store-commissions/?guccounter=1&guce_referrer=aHR0cHM6Ly9ieXRlZGFuY2Uuc2cubGFya29mZmljZS5jb20v&guce_referrer_sig=AQAAAFY2Rt9n5SrnY7uVTj9NC8I10vC7Dl7ITmnJzHEoK2zexFCGBlX4pF0ePdSwI_qrwbAw_HIELjz0ABcQpWmLXOAwZDBqDG-lUjRjrAAgm5EcF5F_bIWq5zeNmZTf2VWF3Ufvck21ozgMLTYcqCQDY5A5y0OkCt-ahJMXE_qs5Npa)\*，从5月初开始官网充值交易下滑明显

![ROW Webapp Transaction volume & Success rate \[by Jun.24\]](https://feishu.cn/file/IfeobOhaooYmQ5xZseZlz0AQgcf)

- **支付类型**：以CCDC和本地钱包为主，占比约总交易量的78%

| 支付类型  <br/>Payment Type  | 单月交易量  <br/>Monthly Volume | % | Paycore支付成功率  <br/>Paycore Success Rate |
|-|-|-|-|
| CCDC | 5,798,450  | 44% | 69.48% |
| E_WALLET | 4,528,315  | 34% | 77.45% |
| PASS_THROUGH_WALLET | 972,282  | 7% | 83.70% |
| BANK_TRANSFER | 922,675  | 7% | 86.60% |
| BANK_ACCOUNT_PROXY | 820,196  | 6% | 88.56% |
| CASH_PIN | 124,778  | 1% | 80.82% |
| INTERNET_BANKING | 67,767  | 1% | 73.37% |
| AGGREGATOR | 43,621  | 0% | 76.85% |



#### 痛点和规划 // Business Planning

- 继续支持**官网充值的占比提升**、健康度提升。通过拓展渠道营销方向帮助直播业务提升官网充值占比，以提升整体业务营收
- 充值用户体验优化，基于本地支付方式引入、支付重试、渠道优化等方式，持续提升**支付成功率**
- **降低渠道支付成本**，提升官网充值营收

> - To continually support **the expansion of webapp top-up**, and improvement of recharge health rate 
> - To optimize user experience as well as the **payment success rate** for top-up
> - **To reduce channel costs** and increase webapp recharge revenue



## 主播提现 // Live Gift Rewards

主播直播时收到的礼物，会按照一定业务逻辑转换成可提现余额。该场景支持主播进行收入的提现。主播提现主要处理用户赠送礼物产生的主播收益，主播在TikTok能够看到打赏产生的收益余额，进行主动提现。

除美国外，所有国家直播产生的收入，均通过主播提现处理。美国的特殊之处在于，根据美国合规要求，TikTok现有的账户余额概念落入了监管定义的“Stored Value”范围内，从事该类业务需要持相关牌照。TikTok和PIPO均暂无牌照，为规避合规风险，需要弱化余额概念，通过Money Platform 提供的周期性打款方案支付主播收入。

> The gifts received by creators during live streaming will be converted into withdrawable balances according to certain business logic. This scenario helps the creators to withdraw their income. It handles the earnings of Gifts. Creators can see the balance of earnings from rewards on TikTok and make withdrawals. In all countries except the United States, the income generated from rewards is processed through Live Gift Reward. 
> 
> The special case of the United States is that, according to the compliance requirements in the United States, the existing account balance concept of TikTok falls within the "Stored Value" range defined by regulation. To engage in such business, relevant licenses are required. Both TikTok and PIPO do not have licenses currently. To avoid compliance risks, the concept of balance needs to be weakened, and the creators' income is paid through Monthly Earnings provided by the Money Platform.

<callout emoji="🌍">
**复杂的“国家”逻辑**
“国家”概念，在直播场景较为复杂，包括Store region、IP region等。Wallet团队会将两个region均传入PIPO，对于TTP/Clover机房，PIPO选择Store region作为交易国家或地区，其他机房则选择IP region作为交易国家或地区。而主播提现场景，刻意模糊了国家的差异。直播认定需要尽量为所有主播提供提现能力，但是存在一些特殊情况，比如用户并不信任本国的银行，或者国家和地区国际定义上存在争议。为了尽可能保证所有主播能够提现，目前做法是：主播向自己绑定的PI提现，绑定PI时，主播可以在当前商户号支持的所有国家或地区中，选择2个国家或地区，绑定支持的支付方式。
**Complex “country” logic**
The concept of "country" is rather complex in Live Gift Rewards scenarios, including Store region, IP region, etc. The Wallet team will pass both regions to PIPO. For TTP/Clover IDC, PIPO selects the Store region as the transaction country or region, while for other IDC, it selects the IP region as the transaction country or region. In the Live Gift Rewards scenario, the difference of countries is deliberately blurred. TikTok Live aims to provide withdrawal capabilities to all creators as much as possible, but in some countries and regions, users do not trust their local banks, and there are also some countries and regions that are controversial in international definition. In order to ensure that all creators can withdraw as much as possible, the current approach is: creators withdraw to their bound PIs, and when binding PIs, creators can select 2 countries from all the countries supported by the current merchant account and bind the payment methods supported in these two countries.
</callout>

#### 用户链路 // User Journey

主播可在TikTok APP内和官网进行提现，以手机端TikTok APP内入口为例，提现体验如下 // Creators can withdraw cash in the TikTok APP and on the official website. Taking the in-app entry on the mobile TikTok APP as an example, the user experience is as follows:

<grid>
<column width-ratio="0.333333">
![](https://feishu.cn/file/LP0BbtBTXoyWjIxSzBql4vY3gIc)
Entrance example: click "Balance"
</column>
<column width-ratio="0.333333">
![](https://feishu.cn/file/PzdsbdWFwoHQQXx0kCFlSHdgglh)
Balance homepage
</column>
<column width-ratio="0.333333">
![](https://feishu.cn/file/EmSWbHFfCoLC77xxRgSl76nsgkb)
Withdrawal homepage
</column>
</grid>

![](https://feishu.cn/file/KOdpbtbLdocHzyxT6XDlZComgmc)

> 以上页面均由业务维护 // All the pages above are maintained by business side
> 
> 包括：提现收银台，PI列表页，PI详情页（含解绑） // Including: withdraw cashier, PI list, PI details(including unbind)

用户可通过PIPO提供的hostedpage进行PI 绑定 // User can bind new PI via the page provide by PIPO：

<table><colgroup><col/><col/><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><grid><column width-ratio="0.500000"><img name="IMG_8561 2.PNG" mime="image/png" scale="1.000000" src="U5GpbQ5XjoyJ7hxFndDl0o8xgHe"/></column><column width-ratio="0.500000"><img name="image.png" mime="image/png" scale="1.000000" src="Pvlibk8peoupsXxt5cJlOt2sgee"/></column></grid></td><td><img name="IMG_8562 2.PNG" mime="image/png" scale="1.000000" src="EJ7qbhIc9ouAjwxfjbllnA45g9g"/></td><td><img name="IMG_8563 2.PNG" mime="image/png" scale="1.000000" src="FQRFb9Y0JoRGjwxixxvl3QIkgAd"/></td><td><img name="IMG_8564 2.PNG" mime="image/png" scale="1.000000" src="Oa2RbpuozobGayx1FA7lFS6HgQg"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="DvhzbuAVGoIsi1xAos3lhxqugCg"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="HAPbbXCIYohdxqxvksOlbXE4gnh"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="QNpUbSvL4oNTaLxjo0VlGfNDgAf"/></td></tr><tr><td>Step 1: Select country/region and  payment method</td><td>Step 2: input OTP</td><td>Step 3: read withdrawal instructions</td><td>Step 4: input essential elements</td><td>Step 5: jump to channel page</td><td>Step 6:  jump back</td><td>Step 7: display bind result</td></tr></tbody></table>

#### 产品能力 // Product Capability

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><td><b>场景 // Scenarios</b></td><td><b>API</b></td><td><b>接口描述 // API description</b></td><td><b>调用方 //Caller</b></td></tr><tr><td>钱包页<blockquote><p>Wallet homepage</p></blockquote></td><td>/pipo_risk/v1/decision</td><td>业务后端请求pipo风控，风控event=payout_pre_withdraw_request<blockquote><p>The back-end requests PIPO risk control, and the risk control event = payout_pre_withdraw_request</p></blockquote></td><td>BE</td></tr><tr><td>提现页<blockquote><p>Withdraw page</p></blockquote></td><td>/marketing/v1/get_user_coupons</td><td>查询支付营销配置coupon<blockquote><p>Query the payment coupon</p></blockquote></td><td>BE</td></tr><tr><td rowspan="2">提现收银台渲染<blockquote><p>Withdraw cashier</p></blockquote></td><td>/payout/v1/cashier/get_preference_config</td><td>查询商户偏好配置（支付方式、到账时间、最小提现金额等）<blockquote><p>Query the merchant preference configuration (payment method, arrival time, minimum withdrawal amount, etc.)</p></blockquote></td><td>BE</td></tr><tr><td>/payout/v1/cashier/get_pi_list</td><td>查询用户PI列表（PI信息）<blockquote><p>Query the user PI list (PI information)</p></blockquote></td><td>BE</td></tr><tr><td rowspan="3">PI管理页<blockquote><p>PI manage</p></blockquote></td><td>/payout/v1/cashier/get_pi_list</td><td>渲染PI管理页会再调一次查询PI列表<blockquote><p>Rendering the PI management page will call the query PI list again</p></blockquote></td><td>BE</td></tr><tr><td>/payout/v1/cashier/unbind_pi</td><td>删除PI<blockquote><p>Delete PI</p></blockquote></td><td>BE</td></tr><tr><td>/payout/v1/cashier/get_link</td><td>获取pipo 绑卡页的URL<blockquote><p>Get the URL of the PIPO card binding page</p></blockquote></td><td>BE</td></tr><tr><td rowspan="4">提现<blockquote><p>Withdraw</p></blockquote></td><td>/payout/v1/cashier/query_fee</td><td>查询换汇结果和手续费<blockquote><p>Query the result of the FX and Fee calculation</p></blockquote></td><td>BE</td></tr><tr><td>/payout/v1/order/create</td><td>payout下单<blockquote><p>Place payout order</p></blockquote></td><td>BE</td></tr><tr><td>/payout/v1/order/submit</td><td>payout提交订单<blockquote><p>Submit payout order</p></blockquote></td><td>BE</td></tr><tr><td>/payout/v1/order/get_info_biz</td><td>payout业务查单<blockquote><p>Query payout order</p></blockquote></td><td>BE</td></tr></tbody></table>

#### 支付方式 // Payment Methods

截止到2024年6月，主播提现接入了16个支付方式，目前在推动业务接入更多本地支付方式，丰富用户选择。

> As of June 2024, 16 payment methods have been integrated for creators' withdrawals, and currently, we are promoting the business to integrate more local payment methods to enrich users' options.

| **支付方式**  <br/>**Payment Method** | **交易笔数**  <br/>**Volume** | **TSR** | **到账时间/min-50分位数**  <br/>**Arrival Time/min-median** | **适用国家**  <br/>Country or Region |
|-|-|-|-|-|
| PAYPALWALLET | 2,285,412 | 96.67% | 7.2 | AD,AE,AG,AI,AL,AM,AO,AR,AT,AU,AW,AZ,BA,BB,BE,BF,BG,BH,BI,BJ,BM,BN,BO,BR,BS,BT,BW,BY,BZ,CA,CD,CG,CH,CI,CK,CL,CM,CN,CO,CR,CV,CY,CZ,DE,DJ,DK,DM,DO,DZ,EC,EE,EG,ER,ES,ET,FI,FM,FO,FR,GA,GB,GD,GE,GF,GI,GL,GM,GN,GP,GR,GT,GW,GY,HK,HN,HR,HU,ID,IE,IL,IN,IS,IT,JM,JO,JP,KE,KG,KH,KI,KM,KN,KR,KW,KY,KZ,LA,LC,LK,LS,LT,LU,LV,MA,MC,MD,ME,MG,MH,MK,ML,MN,MQ,MR,MT,MU,MV,MW,MX,MY,MZ,NA,NC,NE,NG,NI,NL,NO,NP,NU,NZ,OM,PA,PE,PF,PG,PH,PL,PT,PW,PY,QA,RE,RO,RS,RU,RW,SA,SB,SC,SE,SG,SI,SK,SL,SN,SO,SR,ST,SV,SZ,TC,TD,TG,TH,TJ,TM,TN,TO,TT,TW,TZ,UA,UG,US,UY,VC,VE,VG,VN,WF,WS,YT,ZA,ZM,ZW |
| DANA_WALLET | 1,066,865 | 99.41% | 67.5 | ID |
| BANK_ACCOUNT | 792,741 | 98.16% | 1544.8 | AE,BH,BR,CA,EG,ID,JO,KW,MA,MY,OM,QA,SA,TH,TN,TR,VN |
| PAYONEER | 354,926 | 97.68% | 86.5 | AE,AZ,BH,BR,CA,DZ,EG,ID,JO,JP,KR,KW,LB,MY,OM,PH,QA,SA,TH,TR |
| MEEZA | 336,386 | 98.27% | 591.4 | EG |
| VISA | 140,394 | 93.82% | 10.5 | AM,AZ,BY,GE,KG,KZ,TJ,UA,UZ |
| PIX | 138,796 | 99.04% | 443.4 | BR |
| ZALOPAY | 127,414 | 96.07% | 2446.0 | VN |
| PROMPTPAY | 109,350 | 98.25% | 43.8 | TH |
| LOCAL_BANK_TRANSFER | 101,839 | 96.95% | 986.5 | JP |
| OVO | 94,662 | 98.14% | 6.2 | ID |
| WEBMONEY | 84,309 | 98.45% | 146.1 | AM,AZ,BY,GE,KG,KZ,MD,RU,TJ,TM,UA,UZ |
| MASTERCARD | 63,337 | 95.99% | 3.3 | AM,AZ,BY,GE,KG,KZ,TJ,UA,UZ |
| CASH_CASHPLUS | 55,746 | 92.23% | 29671.9 | MA |
| PAYCO_WALLET | 46,972 | 96.49% | 0.9 | KR |
| MONEYGRAM | 29,876 | 96.43% | 14149.0 | IQ,LB |

> 202404-202406 Data
> 
> https://aeolus-va.TikTok-row.net/#/dataQuery?appId=555295&id=1179621016&sid=555865

#### 数据表现 // Data Performance

- 主播提现总体Payout成功率约96.5%左右，每个月打款约2百万笔。打款金额和成功率波动如下：

> - The overall payout success rate is approximately 96.5%, with approximately 2 million payouts made each month. The fluctuations in payout amount and success rate are as follows:

![https://aeolus-va.TikTok-row.net/#/dataQuery?appId=555295&id=1179627587&sid=555865](https://feishu.cn/file/N1RXbOCbroOIGCxAJJTlkq17gAf)

#### 痛点和规划 // Business Planning

- **建设自动化用户触达能力，管理用户提现预期**。对异常事件触达用户，提升用户支付安全感、降低客诉；对新增支付方式、新开放营销活动等场景触达用户，促进用户对正向消息的感知，提升用户转化。
- **提现支付方式多样化建设**。提供更多本地化支付方式，和更加稳定高效的本地渠道，丰富主播选择。
- **成功率提升、到账时长缩减和体验优化**。定期追踪成功率波动、到账时长波动，并分析相关错误码，持续优化Payout打款核心指标，且优化用户体验。
- 帮助直播降低合规风险，逐步在不同风险级别国家上线Creator wallet。

> - Build an automated user reach capability to manage users' withdrawal expectations. Reach users for abnormal events to enhance users' sense of payment security and reduce customer complaints; Reach users in scenarios such as new payment methods and newly opened marketing activities to promote users' perception of positive news and improve user conversion.
> - Diversify the construction of withdrawal payment methods. Provide more localized payment methods and more stable and efficient local channels to enrich the choices of hosts.
> - Improve the success rate, reduce the payment processing time, and optimize the experience. Regularly track the fluctuations in the success rate and payment processing time, analyze relevant error codes, continuously optimize the core indicators of Payout payment, and optimize the user experience.
> - Help live streaming reduce compliance risks and gradually launch Creator wallets in countries with different risk levels.





## 周期性打款 // Monthly Earnings 

Monthly Earnings（周期性打款）是为了应对未持牌处理用户间交易（Money Transmission）、未持牌stored value风险，衍生出的打款模式。上线之初只支持FBO（For Benifit Of） 模式，目前经过法务合规认可，在部分国家逐步上线Non-FBO支付方式。与主播提现、income+不同，周期性打款不允许用户主动提现，创作者只能在每个月15号被动接受平台打款。此外，周期性打款只支持USD。平台发放的奖励、订阅、发布付费视频等非打赏类型收入，大部分通过Monthly Earnings产品，周期性向用户进行打款。

> Monthly Earnings is a remittance mode derived to deal with the risks of unlicensed handling of transactions between users (Money Transmission) and unlicensed stored value. At the beginning of its launch, only the FBO (For Benefit Of) mode was supported. Currently, with the approval of legal compliance, the Non-FBO payment method has been gradually launched in some countries. Different from the withdrawal of hosts and income+, Monthly Earnings does not allow users to withdraw actively. Creators can only passively receive remittances from the platform on the 15th of each month. In addition, Monthly Earnings only supports USD. Most of the non-reward types of income, such as rewards issued by the platform, subscriptions, and paid video releases, are periodically remitted to users through the Monthly Earnings product.

<grid><column width-ratio="0.500000"><p><b>FBO 模式示例 // FBO model</b></p><whiteboard token="EhZpwb3fshDfhqbIVxWlx7vUgpc"></whiteboard></column><column width-ratio="0.500000"><p><b>Non FBO 模式示例 // NON FBO model</b></p><whiteboard token="HqlTw534thAcH8bnqn4l1VeXgpe"></whiteboard></column></grid>

<blockquote><p>引用自 Queto from <cite doc-id="FZLAdOBdOowEK7xTLdIcRrQ0nOC" file-type="docx" title="[Solution] TTLive - Support Monthly Earnings with PIPOSG non-FBO channels in BR" type="doc"></cite></p></blockquote>

#### 用户链路 // User Journey

**Check income and Transaction details**

> 创作者收入会在每个月1日-14日更新，14日更新完毕。如果收入金额超过了最小支付门槛，会在15日打款到用户绑定的账户中。用户可以在打款前，查看预计收入；也可以在打款结束后，查看交易状态。
> 
> Creator's income will be updated from the 1st to the 14th of each month, and the update will be completed on the 14th. If the income amount exceeds the minimum payment threshold, the payment will be made to the user's bound account on the 15th. Users can view the estimated income before the payment is made, or check the transaction status after the payment is completed.

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td><img name="IMG_8247.PNG" mime="image/png" scale="1.000000" src="By3ib3zlIoAb18x97GxlLXP4grg"/><br/>Click "Others"</td><td><img name="img_v3_02c7_d4c73fc6-ab73-42ed-8a0a-43cf82be86hu.png" mime="image/png" scale="1.000000" src="Rxjmb9RrAoabVPx6SAOlrY4Pg7d"/><br/>Click "Monthly earnings"</td><td><img name="image.png" mime="image/png" scale="1.000000" src="ZASibs82GosCLcxsFPflKOEegYi"/><br/>Check income and transaction details</td></tr></tbody></table>



**Check PI list and details**

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><td><img name="img_v3_02c7_b5f7fd5a-809a-4458-beee-e61646e211hu.png" mime="image/png" scale="1.000000" src="N2UqbDG7koFRgUxbTT5ldhjPgTe"/><br/>Click the button in the upper right corner </td><td><img name="img_v3_02c7_517779e7-a8f6-4e7b-a8bf-b9a9142026hu.png" mime="image/png" scale="1.000000" src="RWjHbfCEBos7BdxWCYUlajaogle"/><br/>Click the "edit" button next to "Payment method"</td><td><img name="img_v3_029f_f2faac29-6255-482a-8c64-1b5e63e7c0hu.png" mime="image/png" scale="1.000000" src="ZxQUbjAP0olQDaxxukulQHu6gfg"/><br/>See PI list<blockquote><p>PIPO page</p></blockquote></td><td><img name="IMG_8254.PNG" mime="image/png" scale="1.000000" src="Oj6lbbdc2o9JjCxIqiYlaK2ZgEd"/><br/>PI details<blockquote><p>PIPO page</p></blockquote></td></tr></tbody></table>

**Bind PI** 

<table><colgroup><col/><col/><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><img name="IMG_8249.PNG" mime="image/png" scale="1.000000" src="C6dhbTiMuojuOkxBjwklFStVgNg"/><br/>Click Set up now</td><td><img name="image.png" mime="image/png" scale="1.000000" src="XzJBbSzxko2LbOxf7d0lshV8gBf"/><br/>Choose payment method<blockquote><p>PIPO page</p></blockquote></td><td><img name="IMG_8252.PNG" mime="image/png" scale="1.000000" src="SrPSbhWEzoGKx0x9MrjlxOXwgve"/><br/>Enter OTP to verify account<blockquote><p>PIPO page</p></blockquote></td><td><img name="image.png" mime="image/png" scale="1.000000" src="PnyFb8MnCoV2Uaxu3xwl4v2Agth"/><br/>Jump to bind page<blockquote><p>PIPO page</p></blockquote></td><td><img name="image.png" mime="image/png" scale="1.000000" src="UYBMbvr8kokJr8xs8azlMoDwgyd"/><br/>Toggle on Primary button, there will be a POP UP<blockquote><p>PIPO page</p></blockquote></td><td><img name="image.png" mime="image/png" scale="1.000000" src="HLPpbiWghoLxAhxSRkylrVmtgre"/><br/>Click the "Legal" button<blockquote><p>PIPO page</p></blockquote></td><td><img name="image.png" mime="image/png" scale="1.000000" src="GPkZbxGuLoib5GxxkJ6loQofgjh"/><br/>Bind success, jump back to PI list<blockquote><p>PIPO page</p></blockquote></td></tr></tbody></table>

#### 产品能力 // Product Capability

- PIPO 提供Payout PI管理hostedpage页面、标准代发API接口，供业务完成周期性打款相关的绑定、Payout能力。

> - PIPO provides the Payout PI management hosted page and the standard payment API interface for the business to complete the binding and Payout capabilities related to periodic payout.

**绑定 // Binding**

<whiteboard token="NGPAwmg42huYbXbtPnIlvaQ1gkd"></whiteboard>

- /payout/v1/cashier/get_link：https://pipopay-docs.bytedance.net/internal/reference/payout/payoutcashiergetlink
- scene = BIND_PI

**出款 // Payout**

<whiteboard token="YMKHw3Psdh3SLhbBpYOlDz0Agcf"></whiteboard>

- **Main flow:**

  - /payout/v1/cashier/get_pi_list: https://pipopay-docs.bytedance.net/internal/reference/payout/payoutcashiergetpilist
  - /payout/v1/order/direct_submit: https://pipopay-docs.bytedance.net/internal/reference/payout/payoutorderdirectsubmit
  - callback
- **Other related API:**

  - /solution/v1/consult_on_payment_methods_migration：切store region导致某些支付方式不可用，仅在切store region时候调用

  > - /solution/v1/consult_on_payment_methods_migration：invoked only in when user switch store region

  - /order/get_info_biz: https://pipopay-docs.bytedance.net/internal/reference/payout/payoutordergetinfobiz

#### 支付方式 // Payment Capability

<whiteboard token="ZfSkwoqGBhL0q9bx71NlB3PCgUg"></whiteboard>

#### 数据表现 // Data Performance

![https://aeolus-va.TikTok-row.net/#/dataQuery?appId=1000257&id=1181733135&sid=808627](https://feishu.cn/file/QVtHbO5zXoCj6Cxm1kmlGjVYgRd)

#### 痛点和规划 // Business Planning

- **提现支付方式多样化建设和Non-FBO 模式覆盖面拓展**。面向业务，提供更多本地化、高PSR的Non-FBO支付方式，和更加稳定高效的本地渠道；面向PIPO，提升资金调拨的灵活性。
- **支付方式对接效率优化**。目前业务侧新增支付方式均有一定的开发、测试工作量，未来将协同业务产研，优化对接链路，提升业务侧的可配置程度，提高对接效率；通过提供沙盒环境等方式，提升自动化测试效率。
- **建设面向业务的自动化资金调拨能力**。提供在线备款、在线转账等接口，协助业务完成自动化备款能力建设，提升业务备款效率，减少业务侧每月备款的人力投入。
- **提供稳定打款能力，保障业务资金安全**。周期性打款发生在每月固定日期，交易量大，交易额高，打款的稳定性和正确性尤为重要。目前在推进Batch Payout能力，通过事前dry run、事中调度等方式，保障打款安全。未来还需探索更多提升资金安全的方法。
- **成功率提升和体验优化**。定期回顾周期性打款数据表现和错误码分布，持续优化Payout打款成功率和用户体验。

> - Diversified construction of withdrawal payment methods and expansion of the coverage of the Non-FBO model. For the business, provide more localized, high-PSR Non-FBO payment methods, and more stable and efficient local channels; for PIPO, improve the flexibility of fund allocation.
> - Optimization of the efficiency of payment method integration. At present, the addition of new payment methods on the business side has a certain amount of development and testing workload. In the future, we will cooperate with the business RD, improve the configurability of the business side, and improve integration efficiency; through the provision of a sandbox environment, etc., improve the efficiency of automated testing.
> - Build an automated fund allocation capability for the business. Provide interfaces such as online prefund API and online transfer API to assist the business in completing the construction of an automated reserve payment capability, improve the efficiency of the business reserve payment, and reduce the manpower input of the business side for monthly reserve payment.
> - Provide stable payment capabilities to ensure the security of business funds. Periodic payout occur on a fixed date every month, with large transaction volumes and high transaction amounts. The stability and correctness of the payout are particularly important. Currently, Batch Payout capabilities are being promoted, and payment security is ensured through pre-event dry run, in-event scheduling, and other methods. In the future, more methods to improve the security of funds need to be explored.
> - Success rate improvement and experience optimization. Regularly review the performance of periodic payout data and the distribution of error codes, and continuously optimize the success rate and user experience of Payout payment.



## 官网订阅 // Webapp subscription

官网订阅是独立于礼物打赏的营收场景，主播以一定周期的契约方式，向希望增强直播间“主粉关系”体验的用户，提供的付费增值服务。用户在订阅主播后，能够获取专属聊天模式、特殊表情、专属勋章等方面的特权。订阅价值在于：

- 对主播：建立稳定长线的收入预期。主播不仅拓展了新的营收渠道，也获得了更好的服务核心粉丝丝的动力，以及维护好主粉关系的抓手
- 对用户：建立区别于礼物打赏的付费心智。用户通过较低门槛的付费，即可拥有一定周期内的某位主播的直播间特权，享受区别于礼物打赏的互动体验
- 对平台：建立礼物打赏之外的新增量营收场景。聚焦主-粉关系下“社区感”的营造，从而构建基于该心智下的付费场景

> Webapp subscription is a revenue scenario independent of gift rewards. In a contractual manner for a certain period, the anchor provides paid value-added services to users who wish to enhance the "host-fan relationship" experience in the live broadcast room. After subscribing to the creator, users can obtain privileges in terms of exclusive chat modes, special expressions, and exclusive medals. The value of subscription lies in:
> 
> - For the creators: Establish a stable and long-term income expectation. The creators not only expand a new revenue channel, but also gain better motivation to serve core fans and a way to maintain a good host-fan relationship.
> - For users: Establish a paid mentality different from gift rewards. Through relatively low-threshold payment, users can enjoy live broadcast room privileges of a certain anchor within a certain period and enjoy an interactive experience different from gift rewards.
> - For the platform: Establish a new incremental revenue scenario beyond gift rewards. Focus on creating a "sense of community" under the host-fan relationship, thereby building a paid scenario based on this mentality.

**重要里程碑 // Milestones：**

<table><colgroup><col/><col/></colgroup><tbody><tr><td><b>时间 // Time</b></td><td><b>事项 // Action</b></td></tr><tr><td>2021 Q4</td><td><ul><li>订阅MVP 版本上线。仅支持使用IAP进行端内订阅</li></ul><blockquote><ul><li>Subscription MVP version goes live. Only in-app purchases (IAP) are supported for in-app subscriptions.</li></ul></blockquote></td></tr><tr><td>2022 Q2</td><td><ul><li>官网订阅上线，支持在官网内，通过非IAP支付方式，进行订阅</li></ul><blockquote><ul><li>Subscription goes live, supporting subscriptions through non-IAP payment methods on the official website.</li></ul></blockquote></td></tr><tr><td>2024 Q1</td><td><ul><li>拓展美国、加拿大、罗马尼亚、波兰等8个国家和地区</li></ul><blockquote><ul><li>Expand to 8 countries and regions, including the United States, Canada, Romania, Poland, etc.</li></ul></blockquote></td></tr><tr><td>2024 Q2</td><td><ul><li>官网订阅与官网充值商户号拆分</li></ul><blockquote><ul><li>Split the merchant number for subscriptions and Webapp recharge.</li></ul></blockquote></td></tr></tbody></table>

#### 用户链路 // User Journey

- 主播可决定是否开放订阅、订阅价格，并且设定用户发起订阅后，能够获取的特权

> - Creators can decide whether to enable subscriptions, the subscription price, and set the privileges that users can obtain after initiating a subscription.

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td><b>Perks</b></td><td><b>Badges &amp; Emotes</b></td><td><b>Subscription-only Chat</b></td></tr><tr><td><b>Where to set it up?</b></td><td>Host can edit Badge, Emotes<grid><column width-ratio="0.500000"><img name="首次申请权限 - 条件不满足 (3).png" mime="image/png" scale="0.973333" src="QcaHbg5uao3YRkxhfwJlcrJTgTc"/></column><column width-ratio="0.500000"><img name="首次申请权限 - 条件不满足 (2).png" mime="image/png" scale="0.973333" src="Lx96b6zKnomZVcxLEnzl6yPjgVc"/></column></grid></td><td>Host can enable / disable Subscriber-only Chat<grid><column width-ratio="0.591285"><img name="image.png" mime="image/png" scale="0.336538" src="NVcMbu4iDoYb8Kx3WZgl3Oz2gwc"/></column><column width-ratio="0.408715"><img name="首次申请权限 - 条件不满足 (4).png" mime="image/png" scale="0.193333" src="PjV4bJzhsoHQWJxM27olcd6vgwg"/></column></grid></td></tr></tbody></table>

- 用户可通过直播间的各个入口，进入订阅界面：

> - Users can enter the subscription interface through various entrances in the live broadcast room:

<table><colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>直播间顶部状态栏 </b><blockquote><p>Status bar</p></blockquote></td><td><b>直播间顶部个人卡片</b><blockquote><p>Personal card</p></blockquote></td><td><b>徽章</b><blockquote><p>Badges</p></blockquote></td><td><b>订阅专属聊天入口</b><blockquote><p>Chat entry</p></blockquote></td><td><b>表情包</b><blockquote><p>Emoticons</p></blockquote></td></tr><tr><td><img name="image.png" mime="image/png" scale="1.000000" src="NWHDbtoSDoJRxZxaHJZlzrN5gdf"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="D26kbuNPGoXNQAx0lL6lp8HTgbz"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="KT4Zbhw7Fo59UHxWOS3lEdHug1d"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="LqKLbFmRAouvoTxoYvalxv5Og4b"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="TtkvbFBGOoGbSFxZgGQlI0BMgnc"/></td></tr></tbody></table>

- 用户可在端内通过IAP进行订阅，也可在官网进行订阅。提供单次（单月）订阅、连续订阅两种选项，单次订阅可支持升级为连续订阅。其中，IAP订阅为直播自建，以下为官网订阅示意图：

> - Users can subscribe in the app via IAP or on the official website. Two options are provided: one-time subscription and auto-renew subscription. One-time subscription can be upgraded to auto-renew subscription. Among them, IAP subscription is built by the live broadcast itself. The following is a schematic diagram of the webapp subscription:

<table><colgroup><col/><col/></colgroup><tbody><tr><td><b>单次订阅</b><blockquote><p>One-time subscription</p></blockquote></td><td><img name="image.png" mime="image/png" scale="1.000000" src="KteWb7U9locMVFxzBoClfkkdg1d"/></td></tr><tr><td><b>单次订阅续订</b><blockquote><p>One-time subscription renew</p></blockquote></td><td><img name="image.png" mime="image/png" scale="1.000000" src="X2rrbmtJZoVkTexbU9WlnFwggqh"/></td></tr><tr><td><b>单次订阅升级为连续订阅</b><blockquote><p>One-time subscription upgrade to auto-renew subscription</p></blockquote></td><td><img name="image.png" mime="image/png" scale="1.000000" src="JXlibF0gjoeWFIx84zCln2LGgBf"/></td></tr><tr><td><b>连续订阅</b><blockquote><p>Auto-renew subscription</p></blockquote></td><td><img name="image.png" mime="image/png" scale="1.000000" src="HCygbzkT4onyuDx8wSKlqT4Lgrc"/></td></tr></tbody></table>

- 订阅后，用户特权示例如下 // Privileges examples after user subscribe:

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td><b>专属勋章 // badge</b></td><td><b>专属表情 // emote</b></td><td><b>专属礼物 // gift</b></td></tr><tr><td><grid><column width-ratio="0.500000"><img name="image.png" mime="image/png" scale="1.000000" src="M3D2brjFeoFyUWxo1TUlrNsdgjc"/></column><column width-ratio="0.500000"><img name="image.png" mime="image/png" scale="1.000000" src="J5umbLTy6okWmRxjZtMl3iLQgvh"/></column></grid></td><td><grid><column width-ratio="0.500000"><img name="image.png" mime="image/png" scale="1.000000" src="Mcl2baGDXoJPaKxyoINlphCKgug"/></column><column width-ratio="0.500000"><img name="image.png" mime="image/png" scale="1.000000" src="GKCfbd9WkonuCFxJZeblvEkYgCT"/></column></grid></td><td><grid><column width-ratio="0.500000"><img name="image.png" mime="image/png" scale="1.000000" src="Wwk0b72JXoUDDAxXGXSlcr3BgrA"/></column><column width-ratio="0.500000"><img name="image.png" mime="image/png" scale="1.000000" src="Fl6abC0I1oD9F8xvUs0llx4Ngsc"/></column></grid></td></tr></tbody></table>

#### 产品能力 // Product Capability

**单次订阅 // One-time subscription：**

> 使用即时付dropin收银台，及配套服务端接口
> 
> Use the drop-in component and related API

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><td><b>场景 // Scenarios</b></td><td><b>API</b></td><td><b>接口描述 // API description</b></td><td><b>调用方 //Caller</b></td></tr><tr><td rowspan="3">收银台渲染<blockquote><p>Render cashier page</p></blockquote></td><td>/payment/v1/nonce</td><td>获取接口签名nonce<br/>Generate nonce</td><td>BE</td></tr><tr><td>/agreement_deduct/v1/initialize_agreement</td><td>初始化协议<br/>Initialize the protocol</td><td>BE</td></tr><tr><td>/payment/v1/agreement_basic_info</td><td>查询协议扣款相关支付方式信息<br/>Query the payment method information related to the agreement deduction</td><td>FE</td></tr><tr><td>Bind PI</td><td>/agreement_deduct/v1/bind_authorize_agreement</td><td>绑定协议扣支付方式<br/>Bind the payment method for the agreement deduction</td><td>FE</td></tr><tr><td>Delete PI</td><td>/payment/v1/delete_stored_method</td><td>删除已绑定支付方式<br/>Delete the bound payment method</td><td>FE</td></tr><tr><td rowspan="6">Create order and conduct payment</td><td>/payment/v1/initiate_payment</td><td>初始化订单<br/>Initialize the order</td><td>BE</td></tr><tr><td>/payment/v1/pay</td><td>支付并绑定接口<br/>Payment and binding API</td><td>FE</td></tr><tr><td>/payment/v1/get_three_ds_detail</td><td>查询3ds信息<br/>Query 3ds information</td><td>PIPO_FE</td></tr><tr><td>/gn/acceptance/v1/upload_metadata</td><td>前端上传metadata<br/>Front-end upload metadata</td><td>PIPO_FE</td></tr><tr><td>/payment/v1/get_three_ds_result</td><td>轮询查询3ds认证结果<br/>Poll to query the 3ds authentication result</td><td>PIPO_FE</td></tr><tr><td>/payment/v1/payment_detail</td><td>查单<br/>Query order</td><td>BE</td></tr></tbody></table>

**多次订阅 // Auto-renew subscription：**

> 使用dropin组件，及协议扣配套接口
> 
> Use the drop-in component and related API

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><td><b>场景 // Scenarios</b></td><td><b>API</b></td><td><b>接口描述 // API description</b></td><td><b>调用方 //Caller</b></td></tr><tr><td rowspan="2">收银台渲染<blockquote><p>Render cashier page</p></blockquote></td><td>/payment/v1/nonce</td><td>获取接口签名nonce<br/>Generate nonce</td><td>BE</td></tr><tr><td>/payment/v1/cashier_basic_info</td><td>获取可用支付方式列表、可用PI、绑卡表单elements等<br/>Get the list of available payment methods, available PIs, elements of the card binding form, etc</td><td>FE</td></tr><tr><td>Bind PI</td><td>/agreement_deduct/v1/bind_authorize_agreement</td><td>绑定协议扣支付方式<br/>Bind the payment method for the agreement deduction</td><td>FE</td></tr><tr><td>Delete PI</td><td>/payment/v1/delete_stored_method</td><td>删除已绑定支付方式<br/>Delete the bound payment method</td><td>FE</td></tr><tr><td rowspan="6">Create order and conduct payment</td><td>/payment/v1/initiate_payment</td><td>初始化订单<br/>Initialize the order</td><td>BE</td></tr><tr><td>/payment/v1/pay</td><td>支付并绑定接口<br/>Payment and binding API</td><td>FE</td></tr><tr><td>/payment/v1/get_three_ds_detail</td><td>查询3ds信息<br/>Query 3ds information</td><td>PIPO_FE</td></tr><tr><td>/gn/acceptance/v1/upload_metadata</td><td>前端上传metadata<br/>Front-end upload metadata</td><td>PIPO_FE</td></tr><tr><td>/payment/v1/get_three_ds_result</td><td>轮询查询3ds认证结果<br/>Poll to query the 3ds authentication result</td><td>PIPO_FE</td></tr><tr><td>/payment/v1/payment_detail</td><td>查单<br/>Query order</td><td>BE</td></tr></tbody></table>

<readonly-block token="FbQtbWwvPmdsqCnlUe3l58dzgGf" type="mindnote"></readonly-block>

#### 支付方式 // Payment Capability

- 单次订阅在几乎所有国家，都支持CCDC、Paypal支付方式，也会支持本地流行的其他支付方式
- 续订订阅仅支持CCDC、Paypal两种支付方式
- 支付方式详情见：https://sky.byteintl.net/one_stop_configuration/merchant_product_configuration?merchant_id=11202312YpZtp2

> - For one time subscriptions, in almost all countries, CCDC and Paypal payment methods are supported, and other popular local payment methods will also be supported.
> - For auto renew subscriptions, only CCDC and Paypal payment methods are supported.
> - See details at: https://sky.byteintl.net/one_stop_configuration/merchant_product_configuration?merchant_id=11202312YpZtp2

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td><b>国家/地区</b><blockquote><p><b>Country / Region</b></p></blockquote></td><td><b>业务主体</b><blockquote><p><b>Revenue entity</b></p></blockquote></td><td><b>商户号</b><blockquote><p><b>Merchant ID</b></p></blockquote></td></tr><tr><td>AE, SA, KW, QA, TR, JP, ID, EG, AU, BH, JO, MY, PH, SG, KR, TH, VN, AZ, LB, <b>UA, TW</b></td><td>TTSG</td><td>11202312YpZtp2<code>SG</code></td></tr><tr><td>BR, <b>CA, MX</b></td><td>TTUS</td><td>11202312VMf7G2<code>VA</code></td></tr><tr><td rowspan="2">DE, GB, IT, FR, AT, NL, SE, CH, <b>RO, PL, ES</b></td><td rowspan="2">TTUK</td><td>11202312EcAS62<code>Clover</code></td></tr><tr><td>11202312NzHeH2<code>VA</code></td></tr><tr><td>US</td><td>TTUS</td><td>11202312UpnyK2 <code>TTP</code></td></tr></tbody></table>

#### 数据表现 // Data Performance

> 2024Q2

![https://aeolus-va.TikTok-row.net/#/dataQuery?appId=1000257&id=1181748426&sid=1201300](https://feishu.cn/file/OHbfbb6WXorFIMxf6zblGXi5g68)

## 其他场景 // Other scenarios

<table><colgroup><col/><col/><col/></colgroup><thead><tr><th><b>业务场景</b><blockquote><p>Business Scenarios</p></blockquote></th><th>用户界面<blockquote><p>User interface</p></blockquote></th><th>场景描述<blockquote><p>Description</p></blockquote></th></tr></thead><tbody><tr><td><b>主播收入兑换金币</b><blockquote><p>Coin Exchange</p></blockquote></td><td><grid><column width-ratio="0.501108"><img name="image.png" caption="&#xA;" mime="image/png" scale="0.276000" src="TIfVb6bbrokT2Jx5BWelmLPAgPf"/></column><column width-ratio="0.498892"><img name="image.png" caption="&#xA;" mime="image/png" scale="0.305638" src="YXFJbPcNuoWRimx141ulHFKkgcc"/></column></grid><blockquote><p><cite doc-id="doccn7yJwGXgVrv3JVcGklEDBLe" file-type="doc" title="[PRD]Exchange Live Gifts Balance to Coins主播收入兑换金币" type="doc"></cite> </p></blockquote></td><td>主播收入可直接兑换金币，用于打赏其他主播，促进“内循环”<ul><li><b>对主播</b><b>：</b>刺激主播充值，满足头部主播诉求，维护社交关系</li><li><b>对直播业务</b><b>：</b>金币内部流转，不涉及外部资金流，节省渠道成本</li></ul><br/>该场景为直播直接处理，PIPO未参与，但是可作为未来PIPO提供建议方案的参考<blockquote><p>Creator's income can direct exchange to coins, which can be used to tip other creators and promote "internal circulation".</p><ul><li>For creators: Stimulate creators to recharge, to let creators maintain social relationships.</li><li>For business: The internal transfer of coins does not involve external channels, saving channel costs.</li></ul><p>This scenario is directly handled by Live. PIPO is not involved, but it can be used as a reference for future PIPO to provide suggested solutions.</p></blockquote></td></tr><tr><td><b>付费直播 </b><blockquote><p>Paid Event</p></blockquote></td><td><grid><column width-ratio="0.500217"><img name="image.png" mime="image/png" scale="0.440711" src="CNXFbdc3aoLMpAxAvy3lS7owgGg"/></column><column width-ratio="0.499783"><img name="image.png" mime="image/png" scale="0.410256" src="EUDLb7JPXo7iHHxTBq9lTNTjgwW"/></column></grid></td><td>用户付费观看主播的特定活动直播内容。为主播提供了更多收入场景，也是直播业务新的收入来源之一。<blockquote><p>Users pay to watch the live content of the creators' specific events. This provides creators with more income scenarios and is also one of the new revenue sources for the live streaming business.</p></blockquote><br/><cite doc-id="doccntvPwSVdmoQd1dtSFb1Hdrg" file-type="doc" title="Product Strategy : TikTok LIVE Events" type="doc"></cite></td></tr><tr><td><b>游戏小手柄</b><blockquote><p>GamePad</p></blockquote></td><td><whiteboard token="LiMfwrgMJhE8xkb2qvAlOJJbgQe"></whiteboard></td><td>主播通过直播与游戏公司合作，在直播前选择要推广的游戏，并从直播时用户对游戏链接的点击或下载量来获得分成。<blockquote><p>Creators cooperate with game companies through live streaming. Before the live stream, they select the game to be promoted and earn a share based on the number of clicks or downloads of the game link by users during the live stream.</p></blockquote></td></tr><tr><td><b>Income + </b></td><td><img name="image.png" mime="image/png" scale="0.222667" src="QBRob58CRomrRrxzdLYlvTGWgRc"/></td><td>除打赏外，主播在平台上有多种其他类型收入。其中，部分业务的收入会进入到Income +钱包，创作者可按需进行提现。<blockquote><p>In addition to rewards, the creators have various other types of income on the platform. Among them, the income from some businesses will enter the Income + wallet, and the creators can withdraw as needed.</p></blockquote></td></tr></tbody></table>

# 业务对接思考 // Reflection

- 在直播对接过程中，交付效率对业务满意度影响显著。怎样做到“使命必达”，是当前对接工作中的难题，需要所有下游模块予以支持。
- 直播团队标准严格、要求高，对方案设计质量和产品自身质量敏感度很高。这个要求不只对外部团队，对直播内部也适用，提升交付质量是PIPO的重点课题。
- 内部效率的提升需重点对待。配置需求的工作量人力投入需求大；涉及多个模块的复杂项目，沟通协调成本高，容易产生问题。这些情况需要采取有效的优化措施来应对。
- 要聚焦业务核心指标，主动为业务出谋划策，围绕营收、健康度、体验、成功率、支付时长等，从业务视角思考可优化之处。
- 直播是受黑产侵扰较多的场景，且有严格的合规要求。在风控与合规方面，如何拦截黑产、降低负面影响，同时减少对正常用户的影响，是日常工作需留意的。

> - In the process of live connection, delivery efficiency has a significant influence on business satisfaction. How to achieve "mission accomplished" is a difficult problem in the current connection work, which requires the support of all downstream modules.
> - The TTlive team has strict standards and high requirements, and is highly sensitive to the quality of the scheme design and the product itself. The internal requirements of the team are also extremely high. Improving the delivery quality is a key issue in the future.
> - The improvement of internal efficiency needs to be treated with emphasis. The workload of configuration requirements requires a large amount of human input. For complex projects involving multiple modules, the cost of communication and coordination is high, and problems are prone to occur. These situations require effective optimization measures to deal with.
> - It is necessary to focus on the core business indicators, take the initiative to offer suggestions for the business, and think about the areas for optimization from a business perspective, centering around revenue, healthiness, experience, success rate, payment duration, etc.
> - Live is a scene that is frequently disturbed by the black industry and has strict compliance requirements. In terms of risk control and compliance, how to intercept the black industry, reduce the negative impact, and minimize the influence on normal users at the same time is something that needs to be noticed in daily work. 



<callout emoji="📋">
GPP Product Capability Sharing | Satisfaction and Feedback Survey
https://bytedance.sg.larkoffice.com/share/base/form/shrlgxBHCAtLEM7VRWm6zfESO0b
</callout>

![](https://feishu.cn/file/WruobkKP2o5cHTx2xLzljhfkgtg)
