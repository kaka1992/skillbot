---
title: GPP-电商业务线分享|E-commerce Introduction
category: 业务场景
source_url: https://bytedance.sg.larkoffice.com/wiki/BS4owO25UicSLEk8vc6cEKk6n5f
source_token: BS4owO25UicSLEk8vc6cEKk6n5f
source_type: wiki
doc_type: 业务介绍
tags: [电商, TTS, PIPO, GPP, 成功率, 指标]
metrics: [GMV, PSR, NPS, CSAT, 转化率, COD占比]
business_lines: [电商]
summary: 介绍TikTok Shop电商业务模式、角色分工、支付能力及各国市场展业与PIPO合作方案
last_synced: 2026-08-12
---

## 适用场景
面向需要了解 TikTok Shop（TTS）电商业务全景的读者，介绍电商的业务模式、参与角色、买卖家与机构侧支付能力，以及各展业国家的支付解决方案与 PIPO 合作模式。适用于风控、支付及业务对接人员理解电商场景。

## 核心概念
- 业务模式：本地商家卖本地买家（L2L）、跨境 POP、跨境全托管（GS/S）、跨境自营电商 Seitu。
- 经营模式：全托管（Full-Service，商家只供货）与自运营（POP，商家把控全流程）。
- 重要角色：买家、商家、达人（Creator）、机构（MCN/TAP）。
- 购物入口：兴趣电商（短视频、直播、主页橱窗）+ 货架电商（商城）。
- 支付能力：收单（合单支付、先绑后付、支付营销、组合支付、TikTok Paylater、One Click Pay、Express Checkout）、退款（原路退、退到 credit account、退款转代发）、分账、结算、平台打款/自主提现、结汇、B-wallet。
- 主体关系：业务主体与 PIPO 主体一一对应，分托管（MOR/escrow）与自营（self-managing）两种经营模式。
- 展业市场：美国、东南亚（ID/MY/VN/TH/PH/SG）、欧洲（UK/ES/IE，Stripe 托管）、沙特（SA）、墨西哥、巴西、日本等。

## 关键指标口径
- 达人带货 GMV 占比：达人（含商家官方达人）带货金额占该国 TTS GMV 的比例（2024 Q2：SG 54%、US 53%、ID/VN 47%、TH 41%、UK 39%、PH 30%）。
- COD 占比：货到付款交易占该国 payin 的比例（如 ID 77%、VN 90%、TH 76%、PH 87%、SA 91%）。
- PSR（Payment Success Rate）：按支付方式统计的支付成功率（如 US payout PSR ~99%）。
- 其余指标（GMV、NPS、CSAT、转化率）文中给出数值但未定义统一口径。

## 规则 / 策略要点
- 主体本地化：业务主体本地化（TH、VN）、支付主体/牌照本地化（ID、MY 等），SEA 自 2023 年底推进本地化改造。
- 支付预授权模式（US Auth/Capture 拆分）：先确认支付授权成功再创建订单，发货前或授权到期前再 Capture 扣款；高客单价/用户行为异常交易触发风控人审。
- 降低 COD 占比：通过 BNPL、CCDC 支付营销等方式降低货到付款比例（SA 场景）。
- Tokopedia 融合专项：ID 市场收购 Tokopedia，切换 MOR 模式并整合 27 个 payin/3 个 payout 支付方式，目标 GMV 1+1>2。
- 快捷下单：One Click Pay（首单后 3/12 小时内快捷下单）、ApplePay Express Checkout（跳过地址与提单页一步支付）。

## 原文正文

<!-- source_type: wiki | doc_id: BS4owO25UicSLEk8vc6cEKk6n5f | title: GPP-电商业务线分享 E-commerce Introduction -->

<title>GPP-电商业务线分享|E-commerce Introduction</title>

<callout emoji="🥖">
分享录屏：https://bytedance.sg.larkoffice.com/minutes/obsg9hy3p24346b46ut415bs
</callout>

# 业务展业介绍|Business Introduction 

<synced-source><table><colgroup><col/><col/><col/><col/><col/></colgroup><thead><tr><th>买家所在国家或地区<blockquote><p>Buyer country and region</p></blockquote></th><th>2024.Q2 GMV占比<blockquote><p>2024.Q2 GMV proportion</p></blockquote></th><th>业务模式<blockquote><p>Biz model</p></blockquote></th><th>业务主体<blockquote><p>Biz entity</p></blockquote></th><th>PIPO主体<blockquote><p>PIPO entity</p></blockquote></th></tr></thead><tbody><tr><td>美国<blockquote><p>US</p></blockquote></td><td>24.95%</td><td><ol><li seq="1">本地商家卖给本地买家POP业务模式（Q2占美国GMV比82%）</li><li>跨境POP模式（Q2占美国GMV比2%）</li><li>跨境全托管模式（Q2占美国GMV比16%）</li><li>跨境自营电商Seitu（目前业务量占比很少）</li></ol><blockquote><ol><li seq="1">L2L POP model（82% of US GMV in Q2）</li><li>Xborder POP model（（2% of US GMV in Q2）</li><li>Xborder Full-service model (16% of US GMV in Q2）</li><li>Internal entity: Seitu(small volume）</li></ol></blockquote></td><td>TT US</td><td><ul><li>业务本地商户服务商：PIPO US（托管），<ul><li>TTS电商平台对于本地商家卖给本地买家商家进行进行KYC，PIPO和外部渠道不做</li></ul></li><li>业务跨境商户服务商：PIPO SG（自营）</li></ul><blockquote><ol><li seq="1">L2L merchants Payment Service Provider：PIPO US<ol><li seq="1">TTS does KYC for local merchants/creators/MCN/TAP, PIPO and external channels don't do KYC</li></ol></li><li>Xborder merchants Technical Service Provider：PIPO SG</li></ol></blockquote></td></tr><tr><td>印尼<blockquote><p>ID</p></blockquote></td><td>18.90%</td><td><ol><li seq="1">本地商家卖给本地买家POP业务模式</li></ol><blockquote><ol><li seq="1">L2L POP model</li></ol></blockquote></td><td>Tokopedia</td><td>Tokopedia Payment System（托管）<ul><li>TTS电商平台对于本地商家卖给本地买家商家进行进行KYC，PIPO和外部渠道不做</li></ul><blockquote><p>Technical Service Provider：Tokopedia Payment System</p><ol><li seq="1">TTS does KYC for local merchants/creators/MCN/TAP, PIPO and external channels don't do KYC</li></ol></blockquote></td></tr><tr><td>泰国<blockquote><p>TH</p></blockquote></td><td>17.68%</td><td><ol><li seq="1">本地商家卖给本地买家POP业务模式</li><li>跨境POP模式</li></ol><blockquote><ol><li seq="1">L2L POP model</li><li>Xborder POP model</li></ol></blockquote></td><td>TT TH</td><td>PIPO HK（自营）<blockquote><p>Payment Service Provider： PIPO HK</p></blockquote><ul><li>PIPO TH切换中</li></ul></td></tr><tr><td>越南<blockquote><p>VN</p></blockquote></td><td>13.03%</td><td><ol><li seq="1">本地商家卖给本地买家POP业务模式</li><li>跨境POP模式</li></ol><blockquote><ol><li seq="1">L2L POP model</li><li>Xborder POP model</li></ol></blockquote></td><td>TT SG</td><td>PIPO HK（自营）<blockquote><p>Payment Service Provider：PIPO HK</p></blockquote></td></tr><tr><td>马来<blockquote><p>MY</p></blockquote></td><td>9.96%</td><td><ol><li seq="1">本地商家卖给本地买家POP业务模式</li><li>跨境POP模式</li></ol><blockquote><ol><li seq="1">L2L POP model</li><li>Xborder POP model</li></ol></blockquote></td><td>TT MY</td><td>PIPO HK（自营）<blockquote><p>Payment Service Provider：PIPO HK</p></blockquote><ul><li>PIPO MY切换中</li></ul></td></tr><tr><td>菲律宾<blockquote><p>PH</p></blockquote></td><td>9.74%</td><td><ol><li seq="1">本地商家卖给本地买家POP业务模式</li><li>跨境POP模式</li></ol><blockquote><ol><li seq="1">L2L POP model</li><li>Xborder POP model</li></ol></blockquote></td><td>BD PH</td><td>业务本地商户服务商：PIPO PH（自营）<br/>业务跨境商户服务商：PIPO HK（自营）<blockquote><ol><li seq="1">L2L merchants Payment Service Provider：PIPO PH</li><li>Xborder merchants  Payment Service Provider：PIPO HK</li></ol></blockquote></td></tr><tr><td>英国<blockquote><p>GB</p></blockquote></td><td>4.87%</td><td><ol><li seq="1">本地商家卖给本地买家POP业务模式（Q2占英国GMV比65%）</li><li>跨境POP模式（Q2占英国GMV比2%）</li><li>跨境全托管模式（Q2占英国GMV比33%）</li><li>跨境自营电商Seitu（目前业务量占比很少）</li></ol><blockquote><ol><li seq="1">L2L POP model (65% of US GMV in Q2(</li><li>Xborder POP model (2% of US GMV in Q2)</li><li>Xborder Full-service model (33% of US GMV in Q2)</li><li>Internal entity: Seitu (small volume)</li></ol></blockquote></td><td>TT UK</td><td>业务本地商户服务商：PIPO UK（托管）<ul><li>商家/达人/机构需要在stripe进行入驻&amp;KYC</li></ul><br/>业务跨境商户服务商：PIPO SG（自营）<blockquote><ol><li seq="1">L2L merchants Technical Service Provider：PIPO UK<ol><li seq="1">Stripe does KYC for local merchants/creators/MCN/TAP</li></ol></li><li>Xborder merchants Payment Service Provider：PIPO SG</li></ol></blockquote></td></tr><tr><td>新加坡<blockquote><p>SG</p></blockquote></td><td>0.84%</td><td><ol><li seq="1">本地商家卖给本地买家POP业务模式</li><li>跨境POP模式</li></ol><blockquote><ol><li seq="1">L2L POP model</li><li>Xborder POP model</li></ol></blockquote></td><td>TT SG</td><td>PIPO SG（自营）<blockquote><p>Payment Service Provider：PIPO SG</p></blockquote></td></tr><tr><td>沙特<blockquote><p>SA</p></blockquote></td><td>0.03%</td><td><ol><li seq="1">跨境全托管模式</li><li>跨境自营电商Seitu</li></ol><blockquote><ol><li seq="1">Xborder POP model</li><li>Internal entity: Seitu (small volume)</li></ol></blockquote></td><td>TT SG</td><td>PIPO SG（自营）<blockquote><p>Payment Service Provider：PIPO SG</p></blockquote></td></tr><tr><td>西班牙/德国/法国/意大利<blockquote><p>ES/DE/FR/IT</p></blockquote></td><td>西班牙2024.12上线<br/>德国/法国/意大利<br/>2025.3月上线</td><td><ol><li seq="1">本地商家卖给本地买家POP业务模式</li><li>跨境全托管模式</li><li>跨境POP模式</li></ol><blockquote><ol><li seq="1">L2L POP model </li><li>Xborder POP model </li><li>Xborder Full-service model</li></ol></blockquote></td><td>TT IE</td><td>业务本地商户服务商：PIPO EU（托管）<ul><li>商家/达人/机构需要在stripe进行入驻&amp;KYC</li></ul><br/>业务跨境商户服务商：PIPO SG（自营）<blockquote><ol><li seq="1">L2L merchants Technical Service Provider：PIPO EU <ol><li seq="1">Stripe does KYC for local merchants/creators/MCN/TAP</li></ol></li><li>Xborder merchants Payment Service Provider：PIPO SG</li></ol></blockquote></td></tr><tr><td>爱尔兰<blockquote><p>IE</p></blockquote></td><td>2024.12上线</td><td><ol><li seq="1">本地商家卖给本地买家POP业务模式（2024.10 C端开量）</li></ol><blockquote><ol><li seq="1">L2L POP model (upcoming in 2024.10)</li></ol></blockquote></td><td>TT IE</td><td>PIPO EU（托管）<ul><li>商家/达人/机构需要在stripe进行入驻&amp;KYC</li></ul><blockquote><p>Technical Service Provider：PIPO EU </p><ol><li seq="1">Stripe does KYC for local merchants/creators/MCN/TAP</li></ol></blockquote></td></tr><tr><td>墨西哥</td><td>2025.02上线</td><td><ol><li seq="1">本地商家卖给本地买家POP业务模式</li><li>跨境全托管模式</li></ol><blockquote><ol><li seq="1">L2L POP model </li><li>Xborder Full-service model</li></ol></blockquote></td><td>TT MX</td><td><ul><li>业务本地商户服务商：PIPO SG（托管），<ul><li>TTS电商平台对于本地商家卖给本地买家商家进行进行KYC，PIPO和外部渠道不做</li></ul></li><li>业务跨境商户服务商：PIPO SG（自营）</li></ul><blockquote><ol><li seq="1">L2L merchants Payment Service Provider：PIPO SG<ol><li seq="1">TTS does KYC for local merchants/creators/MCN/TAP, PIPO and external channels don't do KYC</li></ol></li><li>Xborder merchants Technical Service Provider：PIPO SG</li></ol></blockquote></td></tr><tr><td>巴西</td><td>未上线</td><td><ol><li seq="1">本地商家卖给本地买家POP业务模式</li></ol></td><td>TT BR</td><td>PIPO SG（托管）<ul><li>商家需要在Ebanx进行入驻&amp;KYC</li></ul><blockquote><p>Technical Service Provider：PIPO SG</p><ol><li seq="1">Ebanx does KYC for local merchants</li></ol></blockquote></td></tr><tr><td>日本</td><td>未上线</td><td><ol><li seq="1">本地商家卖给本地买家POP业务模式</li><li>跨境全托管模式</li><li>跨境POP模式</li></ol><blockquote><ol><li seq="1">L2L POP model </li><li>Xborder POP model </li><li>Xborder Full-service model</li></ol></blockquote></td><td>TT JP</td><td>业务本地商户服务商：PIPO JP（自营）<ul><li>TTS电商平台对商家/达人等进行KYC，PIPO做KYC，外部渠道对商家进行sanction screening</li></ul><br/>业务跨境商户服务商：PIPO SG（自营）</td></tr></tbody></table></synced-source>

1. 本地商家卖给本地买家：商家与买家所在国相同，有时写成L2L，Local to Local。
2. 跨境：CN、HK商家去买家所在国经营。
3. POP模式：“Platform Open Plan”开放式平台。商家把控商品上架、营销、物流、售后等全流程，适合有电商运营经验的商家，此模式货权在商家。一般电商说POP代表跨境POP商家，本地商家虽然是POP模式，一般用本本指代。
4. 跨境自营电商：集团内主体，新加坡Seitu采购国内供应商商品，在海外转售，目前已主要转为全托管模式，此模式货权在Seitu。
5. 跨境全托管模式：商家只需要供货，而运营、物流履约、售后服务等后续工作都由平台完成，适合有供应链优势的商家，此模式货权在商家。
6. 因为目前本地商家卖给本地买家场景下只有POP模式，跨境才有POP和全托管模式区分。电商一般用本地商家卖给本地买家/L2L指代本地商家，用POP指代跨境POP商家，全托管/GS（Global Selling）/S（S项目演变而来）指代跨境全托管商家。
7. 其余国家业务暂未提供分业务模式GMV暂无，故未列出。



> 1. L2L: Merchants and buyers are at the same markets, local to local
> 2. Cross-border: CN and HK merchants sell goods in the target country
> 3. POP mode: "Platform Open Plan" open platform. Merchants control the entire process of product listing, marketing, logistics, after-sales, etc., which is suitable for merchants with experience in e-commerce operations. Ownership of goods belongs to merchants.
> 4. Cross-border Internal entity: Seitu, a Singaporean entity owned by bytedance, purchases goods from CN/HK suppliers and resells them overseas. Currently, it has mainly shifted to a full-service model, and the ownership of goods in this model belongs to Seitu.
> 5. Cross-border full-service model: Merchants only need to supply goods, and the platform completes work such as operation, logistics performance, and after-sales service. This model is suitable for merchants with supply chain advantages, and the ownership of goods belongs to the merchants. 
> 6. Currently, L2L only has POP model, and Cross-border has POP and full-service models. The E-commerce team uses L2L to refer to local merchants, POP to refer to cross-border POP merchants, and Full-Service/GS/S to refer to cross-border full-service merchants.
> 7. Other countries have not yet provided a separate business model GMV, so it is not listed.

# 重要角色|Main Roles

买家、商家、达人、机构（MCN/TAP）

商家需要入驻TikTok shop进行卖货，MCN培养孵化达人，TAP帮商家找达人，达人帮商家带货，买家在Tiktok内购买商品。

> Buyers, merchants, creators, partners (MCN/TAP)
> 
> Merchants join TikTok shop to sell goods, MCN cultivates creators, TAP helps merchants to find creators to sell goods, and buyers purchase products on TikTok



**覆盖国家| countries and regions**

<table><colgroup><col/><col/></colgroup><tbody><tr><td>角色<blockquote><p>roles</p></blockquote></td><td>国家<blockquote><p>countries and regions</p></blockquote></td></tr><tr><td>买家<blockquote><p>buyers</p></blockquote></td><td>北美：美国<br/>东南亚：印尼/马来/泰国/越南/菲律宾/新加坡<br/>中东：沙特<br/>欧洲：英国<blockquote><p>North America: United States</p><p>Southeast Asia: Indonesia/Malaysia/Thailand/Vietnam/Philippines/Singapore</p><p>Middle East: Saudi Arabia</p><p>Europe: UK</p></blockquote></td></tr><tr><td>商家<blockquote><p>merchants</p></blockquote></td><td>本地、中国大陆、中国香港、新加坡（集团自营主体Seitu）<blockquote><p>Local markets, Chinese Mainland, Hong Kong, Singapore (Seitu)</p></blockquote></td></tr><tr><td>达人<blockquote><p>creators</p></blockquote></td><td>本地<blockquote><p>Local markets</p></blockquote></td></tr><tr><td>MCN</td><td>本地、中国大陆、中国香港<blockquote><p>Local markets, Chinese Mainland, Hong Kong</p></blockquote></td></tr><tr><td>TAP</td><td>本地、中国大陆、中国香港<blockquote><p>Local markets, Chinese Mainland, Hong Kong</p></blockquote></td></tr></tbody></table>

## **买家侧|Buyers**

### **购物入口|Shopping entrances**

**兴趣电商+货架电商 Interest-based E-commerc+Shelf-based E-commerce**

> ![图片展示了TikTok电商基于商城拓展满足用户不同程度购物需求的模式。用户购物需求分为潜在、模糊、明确三类。在内容场景下，潜在需求对应首页Feed的直播间和短视频，模糊需求对应私域关注的主播，明确需求对应综合搜索；货架场景中，有商城推荐、频道、橱窗/店铺、商城搜索等。种草和交易行为可促进精准推荐，基础链路包括收藏夹/足迹、购物车、订单中心等，体现了从种草到成交的过程，与上下文介绍的兴趣和货架电商模式相呼应。](https://feishu.cn/file/KzHObLBOOo3Zv9xPVbmlsNrUgQc)

Tioktok是结合兴趣电商与货架电商的综合平台。兴趣电商：用户购买意愿不明确，通过短视频、直播等内容引导用户发现、种草商品，直至最后下单购买；货架电商：用户购买意愿很明确，直接通过商城搜索商品购买。用户的购买行为可以促进更精准的推荐策略，形成良性循环。

> Tioktok is a comprehensive platform that combines interest-based e-commerce with shelf-based e-commerce. interest-based e-commerce: Users don't have clear purchasing intentions and are guided to discover products through short videos, and live streams; Shelf-based e-commerce: Users have a clear purchasing intention and will directly search for products through the mall tap to purchase. Users' purchasing behavior can promote more precise recommendation strategies and form a virtuous cycle.

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><td vertical-align="middle"><b>短视频</b><blockquote><p>Short videos</p></blockquote></td><td vertical-align="middle"><b>直播</b><blockquote><p>Livestream</p></blockquote></td><td vertical-align="middle"><b>主页橱窗</b><blockquote><p>Product Showcase</p></blockquote></td><td vertical-align="middle"><b>商城</b><blockquote><p>Mall</p></blockquote></td></tr><tr><td colspan="3"><img name="f4vI2lRwJ6DP.png" mime="image/png" scale="0.682508" src="JsHHb8TgwobM8UxMnZll6LO4gyc"/></td><td><img name="ZpoC5HldrZ4g.png" mime="image/png" scale="0.179367" src="GQfdblbDyoTKHdxKcfHl3saCgDc"/></td></tr></tbody></table>

TikTok用户主要可通过以上四种方式发现并购买商品：带商品锚点的**短视频**、带购物车的**直播、**TikTok账户主页的**橱窗**和Shop Tab首页**中心化商城**。

> TikTok users can mainly discover products through the above four methods: short videos with product anchors, live broadcasts with shopping carts, TikTok account homepage showcase, and Shop Tab to centralized shopping mall.

### 如何支付|How to pay

<table><colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>订单详情页</b><blockquote><p>Checkout Page</p></blockquote></td><td colspan="2"><b>选择支付方式</b><blockquote><p>Choose Payment Method</p></blockquote></td><td><b>跳转到第三方</b><blockquote><p>Jump to third-party page </p></blockquote></td><td><b>支付完成</b><blockquote><p>Payment Completed</p></blockquote></td></tr><tr><td><img name="3c47eacd38a483d8ad981d6facdebcb.jpg" mime="image/jpeg" scale="1.000000" src="GAfhbKzFXodzNVxmRXslb7kBgvh"/></td><td><img name="8aba2d275f9db64f358618f506e91f8.jpg" mime="image/jpeg" scale="1.000000" src="SEggbcL04oaMysxjx3ZlNDGEgab"/></td><td><img name="a708df0b9e7010970458da14c1065c3.jpg" mime="image/jpeg" scale="1.000000" src="TCwbbL4jWoTk7Yx2pyNlb0U3gec"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="BboDbffY4oRiJVxCaxAloi64g9Z"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="QJlBbFXzRo4lLTx8dlXle8wKgEd"/></td></tr></tbody></table>

<blockquote><ul><li>这里以跳转到第三方页面流程举例，是否跳转取决于支付方式</li><li>更多支付方式流程录屏：<cite doc-id="shtcn33sF5SRyP0BxP7zKUZKPsf" file-type="sheets" sheet-id="OjYqEE" title="TTS&amp;保证金&amp;Warehouse&amp;S&amp;Fanno涉及支付方式" type="doc"></cite></li></ul></blockquote>



<blockquote><ul><li>Taking the process of redirecting to the third-party page as an example, whether to redirect depends on the payment method</li><li>More payment method flow recordings: <cite doc-id="shtcn33sF5SRyP0BxP7zKUZKPsf" file-type="sheets" sheet-id="OjYqEE" title="TTS&amp;保证金&amp;Warehouse&amp;S&amp;Fanno涉及支付方式" type="doc"></cite></li></ul></blockquote>

### 支付能力|Payment capabilities

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td colspan="2">能力<blockquote><p>Capabilities</p></blockquote></td><td>图示<blockquote><p>FLow</p></blockquote></td></tr><tr><td rowspan="7">收单<blockquote><p>Collection</p></blockquote></td><td>合单支付：电商购物车场景，一笔订单中购买多个卖家的商品<blockquote><p>Shipping cart payment: In the e-commerce shopping cart scenario, users buy goods from multiple merchants in one payment transaction</p></blockquote></td><td><grid><column width-ratio="0.500000"><img name="b1cd080f0cbf9227e781451929d8d42.jpg" mime="image/jpeg" scale="1.000000" src="MnnzbsdfPoiv3hxnxu5lUrYygpf"/></column><column width-ratio="0.500000"><img name="473c2e96279d7b6ed0bb33f5d27d32d.jpg" mime="image/jpeg" scale="1.000000" src="VZpxbNYuYoCUfRxOU7klPqeOgTe"/></column></grid></td></tr><tr><td>先绑后付：对于ccdc、钱包类支付方式，支付先绑定，绑定成功后再付款，用户后续无需再输入支付要素，简化操作，提升成功率<blockquote><p>Tokenization payment： For payment methods such as CCDC and wallet, the buyer can generate a token first, and then use the token to pay</p></blockquote></td><td><img name="image.png" mime="image/png" scale="0.305046" src="Jux0bto91oMfs2xjKNclXLTugEe"/></td></tr><tr><td>支付营销：支持在支付时做营销优惠，促进转化<blockquote><p>Payment promotion： Support discounts during payment to promote conversion</p></blockquote></td><td><grid><column width-ratio="0.333333"><img name="image.png" mime="image/png" scale="1.000000" src="KFQfbnQ8Mo3gnwx2aN3lBJYRgSH"/></column><column width-ratio="0.333333"><img name="image.png" mime="image/png" scale="1.000000" src="AI8Ob8AQsoHX4jxLJPSlSJx0gbc"/></column><column width-ratio="0.333333"><img name="image.png" mime="image/png" scale="1.000000" src="MuHIbRCeZonpJSxCzSylR8z8gZd"/></column></grid></td></tr><tr><td>组合支付：支持内部（credit account）、外部资产组合支付<blockquote><p>Hybrid payment: Support paying with internal (credit account) and external assets in one order</p></blockquote></td><td></td></tr><tr><td>Tiktok Paylater：提升GMV</td><td><grid><column width-ratio="0.200000"><img name="image.png" mime="image/png" scale="1.000000" src="Q1Vsbf0G7oqWovxnym5lqQvCg2c"/><p></p></column><column width-ratio="0.200000"><img name="image.png" mime="image/png" scale="1.000000" src="CkokbbFHBoSidexcrhnlDpC4g1c"/><p></p></column><column width-ratio="0.200000"><img name="image.png" mime="image/png" scale="1.000000" src="KCRsb8okFoyAOUxaW3pl18aogpb"/></column><column width-ratio="0.200000"><img name="img_v2_9d334c87-6ebe-462f-be59-12f674797c9g.jpg" mime="image/jpeg" scale="1.000000" src="JWcYbiRouoPLghx1WPol4qt9g5f"/><p></p></column><column width-ratio="0.200000"><img name="image.png" mime="image/png" scale="1.000000" src="L80IbZycFoc1QWxJBrnlv5YPgpf"/><p></p></column></grid></td></tr><tr><td>One Click Pay：当用户完成第一单购买后，在支付结果页上，业务会推荐带有“OneClickPay”按钮的商品，用户可以在12小时内使用上单支付方式快速完成下单支付<blockquote><p>One Click Pay: After the user completes their first purchase, on the payment results page, the business will recommend products with a "OneClickPay" button. The user can quickly complete the order payment within 12 hours using the payment method in the first order</p></blockquote></td><td><bookmark name="www.figma.com" href="https://www.figma.com/file/5gwD9BOavp8qECrA8VxWs2/AOV-23&#39;?type=design&amp;node-id=1-36&amp;mode=design&amp;t=nEXFSU2Z9bTjFskI-0"></bookmark><img name="image.png" mime="image/png" scale="1.000000" src="Poigbt9kGopXbGxE5v3lJetHgkc"/></td></tr><tr><td>Express Checkout：PDP以及购物车接入Apple Pay快捷下单能力，支持获取用户Apple设备的地址信息，跳过地址填写页以及提单页，一步完成提单以及支付，简化支付流程。<blockquote><p>Express Checkout: With the ability to quickly place orders through PDP and shopping cart pages by integrating Apple Pay, it can obtain the user's address from Apple Pay, and skip the address filling page、checkout page, complete payment in one step.</p></blockquote></td><td><img name="image.png" mime="image/png" scale="1.000000" src="FWWibivcLoOm3ux2fqplcjtXgbh"/><img name="image.png" mime="image/png" scale="1.000000" src="IfRAbI70Fo2ZaoxJT5XlsIt3gNU"/></td></tr><tr><td rowspan="3">退款<blockquote><p>Refund</p></blockquote></td><td>支持退款到原支付方式，如原支付方式是apple pay<blockquote><p>Refund to the original payment method</p></blockquote></td><td><grid><column width-ratio="0.333333"><img name="image.png" mime="image/png" scale="1.000000" src="KvJrbWxcYoHV6TxwInEl85wsgX9"/></column><column width-ratio="0.333333"><img name="image.png" mime="image/png" scale="1.000000" src="UQUHbcVCaob7IixelPOlnKKKggf"/></column><column width-ratio="0.333333"><img name="image.png" mime="image/png" scale="1.000000" src="PacibMJXLoA0RuxXu1IlSbU0gjf"/></column></grid></td></tr><tr><td>支持退款到credit account<blockquote><p>Refund to credit account</p></blockquote></td><td><img name="image.png" mime="image/png" scale="0.198397" src="S5Ctb5XFPoK1v3xOrKglTnvUgAc"/><br/><source name="credit退.mp4" mime="video/mp4" origin-height="1560.000000" origin-width="720.000000" size="4218836" token="IHiIbXjggogzLux75Vyl9U8dgZe"/></td></tr><tr><td>支持退款转代发，如原支付方式是cod<blockquote><p>Refund to payout</p></blockquote></td><td><grid><column width-ratio="0.200000"><img name="image.png" mime="image/png" scale="1.000000" src="ImjNbFpBgo2YKCxisG9lEboDgid"/></column><column width-ratio="0.200000"><img name="image.png" mime="image/png" scale="1.000000" src="E1Wsbz1tRoXyAaxgrIFlV25fgpb"/></column><column width-ratio="0.200000"><img name="image.png" mime="image/png" scale="1.000000" src="Q9xCb9dKHo4s53xT51Zl4LPugGc"/></column><column width-ratio="0.200000"><img name="image.png" mime="image/png" scale="1.000000" src="MSz5bzQNBofkwOxSx6rlaVuUg62"/></column><column width-ratio="0.200000"><img name="image.png" mime="image/png" scale="1.000000" src="UL5MbeIWBoJko8xEcgklrX4Kgus"/></column></grid></td></tr></tbody></table>

## **商家侧|Merchants**

**商家经营模式：全托管&自运营**

> Merchants operating model：Full-Service and POP

![图片展示了电商业务中商家的两种经营模式。左侧为全托管模式，背景为红色，强调专注备货、更省心，适合有供应链优势的商家，目前在美国、沙特阿拉伯、英国火热招商，有“了解更多”和“立即入驻”按钮。右侧是商家自运营模式，背景为蓝色，突出自主运营、更灵活，适合有电商运营经验的商家，可把控全流程，有“了解更多”“美国跨境店入驻”“东南亚跨境店入驻”选项。图片与上下文内容相呼应，直观呈现两种经营模式。](https://feishu.cn/file/Dy22bxBGzoktEbxGHB9lmuALgog)

|  | Full service(全托管商家) | POP（自运营商家） |
|-|-|-|
| L2L | × | √ |
| XB | √ （GS3P） | √ （GS POP； GS1P(seitu)） |

**S业务发展**

> Project S roadmap

![图片展示了S业务发展的时间线。绿色箭头标识的独立站 - IF Yooou于2022年1月启动，2022年6月发布；橙色箭头标识的TTS商家 - Seitu SG于2022年10月启动，2023年2月发布；蓝色箭头标识的全托管服务商 - Preceiver SG于2023年6月启动，2023年8月发布。该图片与文档中“S业务发展(Project S roadmap)”的内容相关，直观呈现了各业务模式的启动和发布时间节点。](https://feishu.cn/file/Km84bYXChorSq0xDLRilAMGjgVc)

<grid>
<column width-ratio="0.333333">
If Yooou business model
</column>
<column width-ratio="0.333333">
Seitu business model
</column>
<column width-ratio="0.333333">
Full-service business model
</column>
</grid>

<grid><column width-ratio="0.333333"><whiteboard token="WDs8wMdc2hQ8r3bWb00llufcgVf"></whiteboard></column><column width-ratio="0.333333"><whiteboard token="COcrwdogXhAVXAbi255lDoF3gpe"></whiteboard></column><column width-ratio="0.333333"><whiteboard token="DYbRwZbHXhEDh7b5wAAlnklRghO"></whiteboard></column></grid>



### 如何成为商家**|**How to become a merchant

**商户门户**

> Merchant Portal

<table><colgroup><col/><col/></colgroup><tbody><tr><td>本地商户<blockquote><p>Local merchants</p></blockquote></td><td>https://seller-us.tiktok.com（其它站点替换国家名称，如英国是https://seller-uk.tiktok.com/） <blockquote><p>Replace country names for other sites, such as us -&gt; uk（id、th、my、vn、ph、sg、sa）</p></blockquote></td></tr><tr><td>跨境商户<blockquote><p>Cross border merchants</p></blockquote></td><td>跨境总门户：https://www.tiktokshopglobalselling.com/zh-cn?target=seller<br/>POP门户: https://seller.tiktokglobalshop.com/<br/>全托管门户: https://mmo.fanczs.com/</td></tr></tbody></table>

> 由于跨境全托管是由凡尘演变过来的，所以它的门户与跨境POP是不同的。
> 
> X-border full-service's portal is different from POP's since it comes from S project.

**注册流程**

> Register

<table><colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>注册账号</b><blockquote><p>Register account</p></blockquote></td><td><b>填写基本信息</b><blockquote><p>Fill in basic information</p></blockquote></td><td><b>填写KYC信息</b><blockquote><p>Fill in KYC information</p></blockquote></td><td><b>入驻结果</b><blockquote><p><b>Onboarding results</b></p></blockquote></td><td><b>绑定银行账户//非必需</b><blockquote><p>Bind bank account//Not required</p></blockquote></td></tr><tr><td><grid><column width-ratio="0.539487"><img name="image.png" mime="image/png" scale="0.266393" src="C5h4bCadiopALqxijOLlnnXvgzb"/></column><column width-ratio="0.460513"><img name="image.png" mime="image/png" scale="1.096096" src="DWIObi1CgoCVW2xtvnXlKhzEgTh"/></column></grid></td><td><img name="image.png" mime="image/png" scale="0.624465" src="JnFPbZOgDoq7ZQxbp32lBIlig9d"/></td><td><grid><column width-ratio="0.500000"><img name="image.png" mime="image/png" scale="0.195614" src="DXgSbLbmlogVyLx8o1Plsozrglt"/><p></p></column><column width-ratio="0.500000"><img name="image.png" mime="image/png" scale="0.179262" src="ERUIbhzGlonL3pxSWLclG34Wgag"/></column></grid></td><td><grid><column width-ratio="0.562232"><img name="image.png" mime="image/png" scale="1.119632" src="Ar16bbLbaopW6HxtWghlArT8grd"/></column><column width-ratio="0.437768"><img name="image.png" mime="image/png" scale="1.666667" src="GdYzbEBTCoaGVhxBmNLl6l3Mg4b"/></column></grid></td><td><grid><column width-ratio="0.588343"><img name="image.png" mime="image/png" scale="0.747951" src="Y0wNbdZurobkDkxcgDrlMuUyg2d"/></column><column width-ratio="0.411657"><img name="image.png" mime="image/png" scale="1.020979" src="BuywbPZXYocQVUxQMYklCeSEgvb"/></column></grid></td></tr></tbody></table>

### 如何卖货**|**How to sell products

卖家首先需要在Seller center或Seller app上传商品，审核通过后即商品即可售卖。

> Merchants first need to upload the product in the Seller center（PC） or Seller app. Once approved, the product can be sold.

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td><b>卖货场景</b><blockquote><p>Selling Scenarios</p></blockquote></td><td><b>场景描述</b><blockquote><p>Description</p></blockquote></td><td><b>操作流程</b><blockquote><p>Flow</p></blockquote></td></tr><tr><td>商城<blockquote><p>Mall</p></blockquote></td><td>商家添加商品，发布并且审核通过后可在商城被搜索到<blockquote><p>Merchants upload the product in the Seller center（PC） or Seller app. Once approved, the product can be searched in the mall.</p></blockquote></td><td><img name="image.png" mime="image/png" scale="0.144144" src="Lef3byZOloRrhexuZ0HldmLqgmf"/><grid><column width-ratio="0.500000"><img name="img_v3_02bq_d99d2d3e-14ba-4adb-b88f-fa370f789chu.jpg" mime="image/jpeg" scale="0.062037" src="JyiDbVMNpoRl6IxVRmvlaaU3gZd"/></column><column width-ratio="0.500000"><img name="image.png" mime="image/png" scale="0.179803" src="MwVXbEP6Jo8w5exH8qWlxu8EgKh"/></column></grid></td></tr><tr><td>直播卖货<blockquote><p>Live stream</p></blockquote></td><td>商家开直播卖货，买家可以在直播中下单购买商品<blockquote><p>Merchants add product links to short videos live-stream</p></blockquote></td><td><img name="image.png" mime="image/png" scale="0.112918" src="P4eZb4rYvobF65xyjrglP73ggih"/></td></tr><tr><td>短视频<blockquote><p>Short video</p></blockquote></td><td>发布带商品的短视频，买家可在短视频中点击商品购买<blockquote><p>Merchants add product links to short videos</p></blockquote></td><td><grid><column width-ratio="0.167123"><img name="image.png" mime="image/png" scale="1.002747" src="Uj2KbnEuxoBCHnxPce0lydSlg0d"/></column><column width-ratio="0.167123"><img name="image.png" mime="image/png" scale="1.016713" src="MZ6SbphQ6o3IIIxYecTlzOIrgWb"/></column><column width-ratio="0.167336"><img name="image.png" mime="image/png" scale="0.051105" src="Vg1obsJnHo2YWOxju6IlbHRUgqj"/></column><column width-ratio="0.165687"><img name="image.png" mime="image/png" scale="1.013889" src="UYXAbL6KYoQl8GxhRitlvJg0gvf"/></column><column width-ratio="0.166025"><img name="image.png" mime="image/png" scale="1.425781" src="NcKmbgEtuooSIox3bo0lmcDMgIe"/></column><column width-ratio="0.166707"><img name="image.png" mime="image/png" scale="1.011080" src="RhO7bLIn5oZhukx46eBl66r3g7d"/></column></grid></td></tr><tr><td>主页橱窗<blockquote><p>Showcases</p></blockquote></td><td>商家官方达人账户下会自动同步店铺中添加的商品<blockquote><p>The official creator account of the merchant can automatically synchronize the products added in seller center</p></blockquote></td><td><img name="image.png" mime="image/png" scale="1.000000" src="DEmLb5wrzoUJyfxX3oclIjTugjh"/></td></tr></tbody></table>

### 支付能力|Payment capabilities

<table><colgroup><col/><col/></colgroup><tbody><tr><td>能力<blockquote><p>Capabilities</p></blockquote></td><td>图示<blockquote><p>FLow</p></blockquote></td></tr><tr><td>入驻<blockquote><p>Onboard</p></blockquote></td><td>PIPO提供接口能力，信息填写页面由电商设计，具体入驻页面参考前述入驻流程<blockquote><p>PIPO provides API, and the information-filling page is designed by e-commerce. Please refer to the registration flow </p></blockquote></td></tr><tr><td>分账<blockquote><p>Split</p></blockquote></td><td rowspan="2"><grid><column width-ratio="0.500000"><p>PIPO提供接口能力，由业务方调用</p><blockquote><p>PIPO provides API that can be called by business </p></blockquote></column><column width-ratio="0.500000"><p>电商资金中心结算流程</p><blockquote><p>E-commerce Fund Center Settlement Flow</p></blockquote></column></grid><grid><column width-ratio="0.500000"><whiteboard token="Q2ySw1NoLh3CKobW36ul9A8Eg6b"></whiteboard></column><column width-ratio="0.500000"><img name="image.png" mime="image/png" scale="0.267875" src="DlbWbXQzpoG8Grxky7PldiyXg55"/></column></grid></td></tr><tr><td>结算<blockquote><p>Settlement</p></blockquote></td></tr><tr><td>平台打款/自主提现<blockquote><p>Disbursement</p></blockquote></td><td><readonly-block href="https://www.figma.com/embed?embed_host=share&amp;url=https://www.figma.com/file/KdVyUCOvBzkEpvm7A0AGPv/Payment-methods?node-id=4228%3A56687" type="iframe"></readonly-block></td></tr><tr><td>结汇<blockquote><p>Foreign Exchange Settlement</p></blockquote></td><td><img name="image.png" mime="image/png" scale="1.000000" src="DlZBbx9uwoKBAWx62hilhWeNgKg"/></td></tr><tr><td>收款（B-wallet）<blockquote><p>目前提供给全托管跨境卖家，后续会覆盖POP跨境卖家</p><p>Currently provided to fully-service merchants, will cover POP merchants in the future</p></blockquote></td><td><grid><column width-ratio="0.250000"><img name="image.png" mime="image/png" scale="1.000000" src="PLfTbiMpSodpUcxpmVOlpsjTgX3"/></column><column width-ratio="0.250000"><img name="image.png" mime="image/png" scale="0.114433" src="KO5AbIaNQoskCAxKJbPl5vpbggg"/></column><column width-ratio="0.250000"><img name="image.png" mime="image/png" scale="0.161119" src="Jpa1bojZIo1fkTxCuNklfHkngud"/></column><column width-ratio="0.250000"><img name="image.png" mime="image/png" scale="0.143894" src="XUS0b3mQUoSAFVxsffxlQuVkgWd"/></column></grid></td></tr><tr><td rowspan="2">付款<blockquote><p>Payment</p></blockquote></td><td><grid><column width-ratio="0.166667"><p>跨境POP卖家支付保证金</p><blockquote><p>POP merchants pay deposit</p></blockquote></column><column width-ratio="0.166667"><img name="image.png" mime="image/png" scale="1.000000" src="Yf8Fb1nJEoiz7ex3STJlh0d1gzf"/></column><column width-ratio="0.166667"><img name="image.png" mime="image/png" scale="1.000000" src="FgwVb068OoNNSUxPGK3lfcBJgvb"/></column><column width-ratio="0.166667"><img name="image.png" mime="image/png" scale="1.000000" src="X1Psb6ytUo1oEcxTjMAlg60rgZd"/></column><column width-ratio="0.166667"><img name="image.png" mime="image/png" scale="1.000000" src="Wh04bPqEyowUURxkN8yl4pSsgyc"/></column><column width-ratio="0.166667"><img name="image.png" mime="image/png" scale="1.000000" src="TrrgbQehmoswRdxFSIql2U92gth"/></column></grid></td></tr><tr><td><grid><column width-ratio="0.250000"><p>本地卖家支付仓储费（UK与US 业务提供本地仓，商家可以把货物存放其中）</p><blockquote><p>Local merchants pay storage fees (Biz provides local warehouses service in UK and US)</p></blockquote></column><column width-ratio="0.250000"><ol><li seq="1">主动支付</li></ol><blockquote><p>Instant payment</p></blockquote><img name="image.png" mime="image/png" scale="1.000000" src="DYJBb0Gogo4HetxBtHclxGHOgKd"/><p></p></column><column width-ratio="0.250000"><ol><li seq="2">协议支付</li></ol><blockquote><p>Agreement deduction</p></blockquote><bookmark name="www.figma.com" href="https://www.figma.com/file/goBP00kLTP5xWd1obkMShv/FBT%C2%B7UK%E8%B4%A7%E4%B8%BB%E7%BB%93%E7%AE%97%E8%87%AA%E5%8A%A8%E6%89%A3%E6%AC%BE?node-id=0%3A1&amp;t=XTRgHpj3wotuqJ9U-0"></bookmark><p></p></column><column width-ratio="0.250000"><ol><li seq="3">销售收入支付</li></ol><blockquote><p>GMV payment (using booktransfer product）</p></blockquote><bookmark name="www.figma.com" href="https://www.figma.com/design/O5S7zKOjU08TsULA20PPKD/FBT-Merchant-GMV-Deduction?node-id=0-1&amp;t=hkldxDQ16FUz9sWN-0"></bookmark></column></grid></td></tr></tbody></table>

## **达人侧|Creators**

达人带货的整体流程：达人获得带货权限及确认协议->进行电商开户->选品加入橱窗->内容创作带货（短视频&直播）->结算提现

Tiktok Shop是兴趣电商出身，2024.Q2达人（含商家官方达人）带货占TTS该国的GMV占比：

1. SG：54%
2. US：53%
3. ID：47%
4. VN：47%
5. TH：41%
6. UK：39%
7. PH：30%

> The overall flow: creators obtain promotion authorization and confirm agreements ->open an e-commerce account ->select products to add to the showcase ->content creation to promote goods (short videos&live broadcasts) ->settlement and withdrawal

> TikTok Shop starts with interested-based e-commerce, the proportion of GMV brought by creators (including official creators of merchants) in Q2 2024：
> 
> 1. SG：54%
> 2. US：53%
> 3. ID：47%
> 4. VN：47%
> 5. TH：41%
> 6. UK：39%
> 7. PH：30%

### 如何成为带货达人**|How to become a Tiktok Shop Creator**

视频创作者在满足电商达人准入条件后都可成为**带货达人**。成为带货达人的方式有三种：

Creators can become Tiktok Shop creators after meeting the requirements. There are three ways to become a Tiktok Shop creator:

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td><b>方式</b><blockquote><p>Methods</p></blockquote></td><td><b>说明</b><blockquote><p>Description</p></blockquote></td><td><b>图示</b><blockquote><p>Flow</p></blockquote></td></tr><tr><td>达人自助申请<blockquote><p>Creators apply by themselves</p></blockquote></td><td>所有的达人在达到带货准入门槛之后，都可以在TikTok app内完成自助申请<blockquote><p>Creators can complete applications within the TikTok app after reaching the threshold </p></blockquote></td><td><img name="image.png" mime="image/png" scale="1.000000" src="HDyPbCELOo4IYwxQ581lqMfVgKh"/></td></tr><tr><td>TikTok商家绑定官方达人<blockquote><p>Merchants link their official creators</p></blockquote></td><td>直接把商家的商品同步到官方达人的橱窗中，也可以通过Add from shop把商品手动添加到橱窗、视频和直播中，一个商家只能有一个官方达人。<blockquote><p>Directly synchronize the merchant's products to the official creator's showcase, or manually add the products to the showcase, video, and live stream. Each merchant can only have one official creator.</p></blockquote></td><td><grid><column width-ratio="0.333333"><img name="image.png" mime="image/png" scale="1.000000" src="VnpIbYg9toAu3uxE7xWlIHXhgid"/><p></p></column><column width-ratio="0.333333"><img name="image.png" mime="image/png" scale="1.000000" src="ReqmbO5IRoRE2vxLsrelomgng5f"/><p></p></column><column width-ratio="0.333333"><img name="image.png" mime="image/png" scale="1.000000" src="RXInb8x6koA4MsxNfZnlDNwzgpc"/></column></grid></td></tr><tr><td>TikTok商家绑定渠道达人<blockquote><p>Merchants link their channel creators</p></blockquote></td><td>可以直接在渠道达人的橱窗中，通过Add from shop把商品手动添加到橱窗、视频和直播中，一个商家可以有四个渠道达人。<blockquote><p>Creatos can manually add products to the showcase, videos, and live stream. A merchant can have four channel creators.</p></blockquote></td><td><grid><column width-ratio="0.333333"><img name="image.png" mime="image/png" scale="1.000000" src="N92Sbj1BAoQ1eExMk9VlV1cOgTe"/></column><column width-ratio="0.333333"><img name="image.png" mime="image/png" scale="1.000000" src="TOOub0sDsof7iYxKXTBluVy9gzc"/></column><column width-ratio="0.333333"><img name="image.png" mime="image/png" scale="1.000000" src="PENzbPDH4oEShDx1b7flxIqmgSb"/></column></grid></td></tr></tbody></table>

### 如何带货**|How to promote products**

- 商家在Seller center发布推广计划：

> - The merchants can launch a promotion plan at the Seller Center:

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><td></td><td><b>店铺计划</b><blockquote><p><b>Shop plan</b></p></blockquote></td><td><b>公开计划</b><blockquote><p><b>Open plan</b></p></blockquote></td><td><b>定向计划</b><blockquote><p><b>Targeted plan</b></p></blockquote></td></tr><tr><td><b>商品</b><blockquote><p><b>Products</b></p></blockquote></td><td>店铺所有商品<blockquote><p>All products in the shop</p></blockquote></td><td>商家指定商品<blockquote><p>Targeted Products</p></blockquote></td><td>商家指定商品<blockquote><p>Targeted Products</p></blockquote></td></tr><tr><td><b>佣金</b><blockquote><p><b>Commission</b></p></blockquote></td><td>所有商品佣金一致<blockquote><p>All products have the same commission rate</p></blockquote></td><td>设置该计划内商品佣金<blockquote><p>Set commission for products within this plan</p></blockquote></td><td>设置该计划内商品佣金<blockquote><p>Set commission for products within this plan</p></blockquote></td></tr><tr><td><b>达人</b><blockquote><p><b>Creators</b></p></blockquote></td><td>面向所有达人<blockquote><p>To all creators</p></blockquote></td><td>面向所有达人<blockquote><p>To all creators</p></blockquote></td><td>面向指定达人<blockquote><p>To targeted creators</p></blockquote></td></tr></tbody></table>

> 三种计划中佣金比例的展示优先级为：“定向计划 > 公开计划 > 店铺计划”。 
> 
> The priority for displaying the commission rate in the three plans is "Targeted Plan>Open Plan>Shop Plan



- **达人找商品| Creators find products**

达人可以主动添加店铺计划和公开计划中的商品

<table><colgroup><col/><col/></colgroup><tbody><tr><td><b>选品入口</b><blockquote><p>Add products entrance</p></blockquote></td><td><b>选品广场</b><blockquote><p>Add products </p></blockquote></td></tr><tr><td><img name="img_v2_7b28f6ca-2b88-4198-ba2d-b700cc19331g.jpg" mime="image/jpeg" scale="1.000000" src="DwDnbVtpBot7o5x1EQulMzgfg5d"/></td><td><img name="img_v2_3b024c6e-a4a4-4254-a90b-e209980e6d3g.jpg" mime="image/jpeg" scale="1.000000" src="ALgrbVUUno0oshxvh7ylJwAAgQg"/></td></tr></tbody></table>

- **商家找达人|Merchants find creators**

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td><b>发布推广计划</b></td><td><b>选达人</b></td><td><b>和达人联系</b></td></tr><tr><td><img name="img_v2_70c3302d-e842-453c-9a8f-608bd208bcfg.jpg" mime="image/jpeg" scale="0.380208" src="A9GJbbNdIoh8BLxMLW4lVX2Ugvh"/></td><td><img name="img_v2_dc8ea091-4646-4690-8a98-48b4234c51ag.jpg" mime="image/jpeg" scale="0.380208" src="SDYzb8vIFo4aErxvfBSlAm6Hgof"/></td><td><img name="img_v2_ee494c49-7c86-4eb5-a2a2-6be62d3b296g.jpg" mime="image/jpeg" scale="0.380208" src="WsMObVrVJoIqYYxkdLqlHgKUg3A"/></td></tr></tbody></table>

- **带货场景**

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td><b>带货场景</b><blockquote><p>Scenarios</p></blockquote></td><td><b>场景描述</b><blockquote><p>Description</p></blockquote></td><td><b>操作流程</b><blockquote><p>Flow</p></blockquote></td></tr><tr><td>直播卖货<blockquote><p>Livestream</p></blockquote></td><td>达人开直播带货，买家在直播中购买商品，达人即可分佣<blockquote><p>Creators open a livestream to promote products. Buyers can purchase goods and the creator can receive commission</p></blockquote></td><td><img name="image.png" mime="image/png" scale="0.112918" src="IL7QbN4zpoO3mexaTqXlimO7gwe"/></td></tr><tr><td>短视频<blockquote><p>Short videos</p></blockquote></td><td>达人发布带货短视频，买家在短视频中购买达人带的货，达人将获得分佣。<br/>通常达人的带货视频只会在本国分发，如US达人的视频在US分发，目前业务上线了US视频往UK分发的功能，带跨境商家的商品。后续会支持多国视频分发且支持带本地商家货。<blockquote><p>Creators post a short video featuring their products. Buyers can purchase goods and the creator can receive commission</p><p>Usually, creators' videos with goods are only distributed in their home country, such as US creators' videos being distributed in the US. Currently, the business has launched a feature for US videos to be distributed in the UK, promoting products from cross-border merchants. In the future, it will support video distribution to multiple countries and support promoting goods from local merchants.</p></blockquote></td><td><grid><column width-ratio="0.168397"><img name="image.png" mime="image/png" scale="1.002747" src="Y2ShbZeIaoBcmTxDVBmlNuE7gZd"/></column><column width-ratio="0.165848"><img name="image.png" mime="image/png" scale="1.016713" src="JxNeb2Mi4oBgizxFhEQlVB7agXh"/></column><column width-ratio="0.167336"><img name="image.png" mime="image/png" scale="0.084254" src="GR8Bbeef9o23emxZ3iGltrTag3g"/></column><column width-ratio="0.165687"><img name="image.png" mime="image/png" scale="1.013889" src="HkFkboJF5ooxcuxIWyKl5rwugXe"/></column><column width-ratio="0.166025"><img name="image.png" mime="image/png" scale="1.425781" src="BbyfbNzuTo75qDx9Ss1lTxzegIh"/></column><column width-ratio="0.166707"><img name="image.png" mime="image/png" scale="1.011080" src="X3WSbaSa7okuiRxck3CluaFqgKg"/></column></grid></td></tr><tr><td>主页橱窗<blockquote><p>Product Showcases</p></blockquote></td><td>达人选品后展示在橱窗，买家下单购买后达人即可分佣<blockquote><p>Creators can add products to the showcase. Buyers can purchase goods and the creator can receive commission</p></blockquote></td><td><grid><column width-ratio="0.333033"><img name="image.png" mime="image/png" scale="0.184000" src="SZTQbCGgrocwi2xrlK6lIoPggGX"/></column><column width-ratio="0.333033"><img name="image.png" mime="image/png" scale="0.196121" src="NW8XbQUDvoDIUOxiWM1lC5SOgfg"/></column><column width-ratio="0.333935"><img name="image.png" mime="image/png" scale="0.182540" src="DtMmbE2cpoSyWAxYF89lyg83gOg"/></column></grid></td></tr></tbody></table>

### 支付能力|Payment capabilities

<table><colgroup><col/><col/></colgroup><tbody><tr><td>能力<blockquote><p>Capabilities</p></blockquote></td><td>图示<blockquote><p>FLow</p></blockquote></td></tr><tr><td>入驻<blockquote><p>Onboard</p></blockquote></td><td>PIPO提供接口能力，信息填写页面由电商设计，具体入驻页面参考：<blockquote><p>PIPO provides API, and the information-filling page is designed by e-commerce. Please refer to the following page for reference</p></blockquote><grid><column width-ratio="0.500000"><p>US达人开户</p><blockquote><p>US Creators open account</p></blockquote><img name="image.png" mime="image/png" scale="1.000000" src="BHtLb3XUto6Kxsx8ChMljaEMg9c"/><p></p></column><column width-ratio="0.500000"><p>US达人提现前补充资料</p><blockquote><p>US Creators do KYC before withdraw </p></blockquote><img name="image.png" mime="image/png" scale="1.000000" src="Wi0xbhouDoazBqx2qqRl3XvzgZb"/></column></grid></td></tr><tr><td>分账<blockquote><p>Split</p></blockquote></td><td rowspan="2"><grid><column width-ratio="0.500000"><p>PIPO提供接口能力，由业务方调用</p><blockquote><p>PIPO provides API that can be called by business </p></blockquote></column><column width-ratio="0.500000"><p>电商资金中心结算流程</p><blockquote><p>E-commerce Fund Center Settlement Flow</p></blockquote></column></grid><grid><column width-ratio="0.500000"><whiteboard token="ExEhwixrXh1QVZbBI6qliqUxgRg"></whiteboard></column><column width-ratio="0.500000"><img name="image.png" mime="image/png" scale="0.267875" src="L5Elb2ZhwoVim2xF7DTlxzLGgrd"/></column></grid></td></tr><tr><td>结算<blockquote><p>Settlement</p></blockquote></td></tr><tr><td>平台打款/自主提现<blockquote><p>Disbursement</p></blockquote></td><td vertical-align="middle"><grid><column width-ratio="0.500000"><p>绑卡&amp;自主提现</p><figure view-type="Preview"><source name="us bankaccount达人.mp4" mime="video/mp4" origin-height="1040.000000" origin-width="480.000000" size="18588226" token="IRwIbqQ1koRx7uxX5lSl1N7EgGh"/></figure></column><column width-ratio="0.500000"><p>达人开通内容互通后，仅绑卡，平台打款</p><figure view-type="Preview"><source name="69aae2d9da243269060f65eb5c703643.mp4" mime="video/mp4" origin-height="960.000000" origin-width="432.000000" size="36730586" token="B5BZbKyNSoZLp3xC8v8leMXFgTe"/></figure></column></grid></td></tr></tbody></table>

## **机构侧|Partners** 

<sheet sheet-id="nlkJHr" token="KqFhsTn2ChK0dOtnuTklzJwzgaf"></sheet>

> PIPO目前服务MCN（CAP）和TAP，Tiktok主要帮TSP向商家做服务展示，引流，没有参与结算，机构门户：https://partner.tiktokshop.com/
> 
> Currently, PIPO serves MCN (CAP) and TAP, Tiktok mainly helps TSP showcase services to merchants, attract traffic, and does not participate in the settlement, portal：https://partner.tiktokshop.com/

### 如何成为机构**|How to become partners** 

<table><colgroup><col/><col/><col/><col/><col/><col/></colgroup><tbody><tr><td vertical-align="middle">注册账户<blockquote><p>Register</p></blockquote></td><td colspan="2" vertical-align="middle">填写必填信息<blockquote><p>Fill out details</p></blockquote></td><td vertical-align="middle">提交申请<blockquote><p>Submission</p></blockquote></td><td colspan="2" vertical-align="middle">选择服务商身份（MCN为creator management；TAP为Seller and Scalable Creator Match-up）<blockquote><p>Choose category and markets(Creator management for MCN, Seller and Scalable Creator Match-up for TAP)</p></blockquote></td></tr><tr><td><img name="image.png" mime="image/png" scale="1.000000" src="KvgUbNBuAoRQhWxoxcDlM7QVgde"/></td><td><img name="image.png" mime="image/png" scale="0.155469" src="OOV4bcGiUoACNbx8SLKlu7FcgNb"/></td><td><img name="image.png" mime="image/png" scale="0.179310" src="Rjg5b80taox4r6xAMU1lzwtig6d"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="SOaNbaqAzoQU1QxVGcClv4FLg4f"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="M6jObjSvPo3btwxH7yhl7opAgIb"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="KtWCbIbLioUTYnxuMZ4lC09fgIg"/></td></tr></tbody></table>

### 如何带货**|How to promote products** 

MCN可以与达人建立分佣计划，后续达人带货的产生的佣金按此比例分成。

> MCN can establish a commission-sharing plan with creators, and the commission generated by creators will be shared according to this ratio.

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><td>MCN -发送分佣计划邀约<blockquote><p>MCN - request fee Agreement</p></blockquote></td><td>MCN -计划详情<blockquote><p>MCN - Fee Agreement details</p></blockquote></td><td>达人 - 收到计划邀约<blockquote><p>Creator - Got notification</p></blockquote></td><td>达人- 确认邀约<blockquote><p>Creator - Confirm Agreement</p></blockquote></td></tr><tr><td><img name="image.png" mime="image/png" scale="1.000000" src="Q2wmb29XBo63FixYh4glkUINgDb"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="PBkEbfOUmoJmgwxYcQqlT5qigbB"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="A9VzbRz21oox3vxiQ2QlZvY5gkb"/></td><td><img name="image.png" mime="image/png" scale="0.304000" src="QF3rbpkUjof7f1xWhvDlLUvSgJd"/></td></tr></tbody></table>

TAP可以创建活动，帮商家撮合达人带货，并根据商家设置的分佣比例分成。

> TAP can create campaigns to help match merchants and creators to sell products, and distribute commission based on the commission rate set by the merchants.

<table><colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr><td>总览<blockquote><p>Overall Flow</p></blockquote></td><td>TAP创建活动并分享给商家<blockquote><p>TAP creates campaigns and shares them with merchants</p></blockquote></td><td>商家在活动中添加商品并设置的TAP和达人的佣金比例<blockquote><p>Merchants add products to the campaigns and set commission rates for TSP and creator</p></blockquote></td><td>TAP确认商品<blockquote><p>TAP confirms product </p></blockquote></td><td>TAP分享活动链接给达人，达人添加商品<blockquote><p>TAP share the campaign link to creators, creators add produtcs</p></blockquote></td></tr><tr><td><img name="img_v3_02c9_7db1ea83-bebf-48e8-b704-02c4de6d1fhu.png" mime="image/png" scale="1.000000" src="Ye1DbdQpvot3WZxRa2hl2kEmgUh"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="BWpabTlBzomrDGx9pvzlwx3ggYb"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="ZNpubHaFBohA63xtBbKlMkLjgph"/><img name="image.png" mime="image/png" scale="1.000000" src="WG1BbzcgHoEjEOxo5zglSyM2gGh"/><img name="image.png" mime="image/png" scale="1.000000" src="VHyWbYxBAoosa7xag9DlNmkIgMh"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="BLjJbLJGQouzCbxzuz1lTjEagxc"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="YLtTbGVG2oKi7oxnr3plOsACg8g"/></td></tr></tbody></table>

### 支付能力|Payment capabilities

<table><colgroup><col/><col/></colgroup><tbody><tr><td>能力<blockquote><p>Capabilities</p></blockquote></td><td>图示<blockquote><p>Flow</p></blockquote></td></tr><tr><td>入驻<blockquote><p>Onboard</p></blockquote></td><td>PIPO提供接口能力，信息填写页面由电商设计，具体入驻页面参考：<blockquote><p>PIPO provides API, and the information-filling page is designed by e-commerce. Please refer to above registration flow</p></blockquote></td></tr><tr><td>分账<blockquote><p>Split</p></blockquote></td><td rowspan="2"><grid><column width-ratio="0.500000"><p>PIPO提供接口能力，由业务方调用</p><blockquote><p>PIPO provides API that can be called by business </p></blockquote></column><column width-ratio="0.500000"><p>电商资金中心结算流程</p><blockquote><p>E-commerce Fund Center Settlement Flow</p></blockquote></column></grid><grid><column width-ratio="0.500000"><whiteboard token="IEE0wLL7ghQtAybDNrLlckangTd"></whiteboard></column><column width-ratio="0.500000"><img name="image.png" mime="image/png" scale="0.267875" src="KFRnbcDAToL0GXxbxqily8PAgFe"/></column></grid></td></tr><tr><td>结算<blockquote><p>Settlement</p></blockquote></td></tr><tr><td>平台打款<blockquote><p>Disbursement</p></blockquote></td><td><img name="image.png" mime="image/png" scale="0.419531" src="CqqObGN6couXkSxbhVYlGwidgKa"/><img name="image.png" mime="image/png" scale="0.062229" src="QxfGbtSERoULaqxhNFZloTACgPg"/></td></tr><tr><td>结汇<blockquote><p>Foreign exchange settlement</p></blockquote></td><td><img name="image.png" mime="image/png" scale="1.000000" src="NfFObhVyXogZoOxvDS2lfhO5gpc"/></td></tr></tbody></table>

# 展业国家**|Launched markets** 

## 美国|**US**

### 服务模式**|Payment solution**

美国市场支付解决方案，整体采用托管模式，先后迭代了单一PSP、MOR+FBO和MOR+双FBO模式，满足不同阶段业务发展和法务合规的诉求。

The managed mode is adopted as the payment solution for the US market. And the payment team have successively iterated the single PSP model, the MOR+FBO model and the MOR+dual FBO model to meet the requirements of business development and legal compliance at different stages.

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><td><b>阶段</b><br/><b>Phase</b></td><td><b>主要目标</b><br/><b>Target</b></td><td><b>协议关系</b><br/><b>Agreement Relationship</b></td><td><b>资金方案</b><br/><b>Fund Flow</b></td></tr><tr><td>Phase 1 <br/>PayPal PPCP + Hyperwallet Payout</td><td><ul><li>支持业务MVP L2L场景如期展业</li></ul><ul><li>Support business MVP L2L scenarios to launch as scheduled</li></ul></td><td><whiteboard token="WEk8wkzE5hMlRMbHBA2l8BeDgod"></whiteboard></td><td><whiteboard token="HHtjwHx2shUWsSbc6qslRnyfgee"></whiteboard></td></tr><tr><td>Phase 2<br/>MOR + FBO</td><td><ul><li>提升买家可用支付方式丰富度</li><li>增加收单场景备份渠道</li><li>搭建e-kyc能力，优化商家入驻体验</li></ul><ul><li>Improve the variety of payment methods available to buyers</li><li>Increase the backup channels for payment collection scenarios</li><li>Build e-kyc capabilities and optimize the merchant onboarding experience</li></ul></td><td><whiteboard token="JBXKwx1puhZCHAba6t8lfUCXgxg"></whiteboard></td><td><whiteboard token="RbBNwrJa3hqsqcbnt1clWh0WgJg"></whiteboard></td></tr><tr><td>Phase 3<br/>MOR + Multiple FBO</td><td><ul><li>增加付款场景备份渠道</li><li>降级法务合规风险</li></ul><ul><li>Increase backup channels for payout scenarios</li><li>Mitigate legal and compliance risk</li></ul></td><td><whiteboard token="M3RxwMalahkDqpbklSZlKUmQghd"></whiteboard></td><td><whiteboard token="RY9EwWbWzhGDhNbmVBklWWfugSc"></whiteboard></td></tr></tbody></table>

> [ ](https://bytedance.sg.larkoffice.com/docx/HGC2dDd5coOFBtxND4UcQSX1nag) 

### 支付能力**|Payment capabilities**

- **Product Capabilities**

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td colspan="2">产品<br/>Product</td><td>是否有应用 <br/>live or not</td></tr><tr><td colspan="2">入驻<br/>onboarding</td><td>✅</td></tr><tr><td rowspan="7">收单collection</td><td>合单支付<br/>shipping cart payment</td><td>✅</td></tr><tr><td>先绑后付 <br/>tokenisation payment</td><td>✅</td></tr><tr><td>支付营销 <br/>payment promotion</td><td>✅</td></tr><tr><td>组合支付 <br/>hybird payment</td><td>WIP</td></tr><tr><td>TikTok Paylater</td><td>/</td></tr><tr><td>One Click Pay</td><td>✅</td></tr><tr><td>Express Checkout</td><td>✅</td></tr><tr><td rowspan="3">退款<br/>refund</td><td>支持退款到原支付方式 <br/>refund to the original payment method</td><td>✅</td></tr><tr><td>支持退款到TikTok Balance<br/>refund to credit</td><td>WIP</td></tr><tr><td>支持退款转代发<br/>refund via payout</td><td>/</td></tr><tr><td colspan="2">分账 <br/>split</td><td>✅</td></tr><tr><td colspan="2">结算 <br/>settlement</td><td>✅</td></tr><tr><td colspan="2">平台打款/自主提现 <br/>disbursement</td><td>✅</td></tr><tr><td colspan="2">结汇 <br/>foreign exchange settlement</td><td>✅</td></tr><tr><td colspan="2">Bwallet (Merchant Balance)</td><td>✅</td></tr></tbody></table>

- **Payment Method**

<table><colgroup><col/><col/><col/><col/><col/><col/></colgroup><tbody><tr><td>Market</td><td>Payment Direction</td><td>Roles</td><td>Payment Type</td><td>Payment Method</td><td>Data Metrics</td></tr><tr><td rowspan="14">US</td><td rowspan="5">payin<br/>(Q2 Successful Payment Users 52,991,789）</td><td rowspan="4">Buyer </td><td>CCDC</td><td>Visa, MasterCard, Amex, Discover</td><td rowspan="5"><grid><column width-ratio="0.500000"><img name="PSR.png" mime="image/png" scale="1.000000" src="GOU7baMZmoBw5mxaJwVl8Fs6gKe"/></column><column width-ratio="0.500000"><img name="ORDER NO.png" mime="image/png" scale="1.000000" src="LRwsbMjOJotk9tx1OwMlc4JsgMf"/></column></grid></td></tr><tr><td>eWallet</td><td>ApplePay (CCDC-based), GooglePay (CCDC-based), PayPal, Venmo</td></tr><tr><td>BNPL</td><td>Klarna, Affirm, CC Installment(WIP)</td></tr><tr><td>Balance (WIP)</td><td>TT Consumer Balance (Giftcard-based, WIP)</td></tr><tr><td>Creator</td><td>GiftCard</td><td>PIPO_GiftCard</td></tr><tr><td rowspan="9">payout</td><td rowspan="2">Local Creator</td><td>Bank Account</td><td>Bank Account</td><td rowspan="9">PSR: ~99%</td></tr><tr><td>eWallet</td><td>PayPal</td></tr><tr><td>Local Seller/MCN/TAP</td><td>Bank Account</td><td>Bank Account</td></tr><tr><td>Seitu SG  (EC self-managed)</td><td>eWallet</td><td>Lianlian</td></tr><tr><td rowspan="2">CN/HK POP Seller</td><td>Bank Account</td><td>Bank Account</td></tr><tr><td>eWallet</td><td>Lianlian, Payoneer, Pingpong, Airwallex(gray scale), Merchant Balance(WIP)</td></tr><tr><td>CN/HK Full-Service Seller</td><td>eWallet</td><td>Merchant Balance</td></tr><tr><td rowspan="2">CN/HK MCN/TAP</td><td>Bank Account</td><td>Bank Account</td></tr><tr><td>eWallet</td><td>Lianlian</td></tr></tbody></table>

### 特色场景|Distinctive features

1. **下单支付流程重构 - 支付预授权模式  Order placement and payment process revamp - Manual Capture payment model**基于用户[调研](https://bytedance.sg.larkoffice.com/docx/JddhdCo07ooA0jxtnMecbZ2UnA2)和商家反馈，发现如下几个问题：以达到：^由于交易下单新流程会产生支付成功，但相关资源不足需要撤销支付的场景（\~0.5%），比普通退款场景对逆向时效要求更高。

   <blockquote><p><cite doc-id="ZR7QdJFWPob4A6xlhY7cckT7nHd" file-type="docx" title="TTS US - Auth Capture Delink Project - Product Solution PRD" type="doc"></cite></p><p><cite doc-id="L1Wadw3qXo3GfnxOaFalxtoEgQc" file-type="docx" title="TTS US 交易下单和支付流程重构项目效果回收 // TTS US - Auth Capture Delink Project - Data Retrospective♻️" type="doc"></cite></p></blockquote>

   1. **背景：TikTok Shop 目前通用的交易流程是「先下单再支付」。**用户在电商提单页选择支付方式、点击Place order后，电商交易先创建订单，初始状态为「待支付」，后进入支付流程。**支付成功后，会立即扣款（auto capture）。**若用户放弃支付或支付失败，订单停留在「待支付」状态，用户可选择其他支付方式重新尝试支付，也可以手动关闭订单。若用户无操作，则平台会自动关闭超时未支付的交易。仅当订单关闭后，订单已占用的库存、营销优惠等资源才会释放。

   - **用户侧**
   
     - US用户不理解订单“待支付”状态，倾向「支付授权」后才会生成订单，代表交易确定。若支付失败，预期是立即重新尝试支付，若放弃支付，表示不想购买，对应商品应留在购物车中，不应生成待支付订单；
     - 未支付成功/支付失败最终平台关单的订单（\~3.5%），占用了用户营销、限购资格等资源，且商品没有被保留在购物车中，由于C端屏蔽了该类型的订单的展示，导致用户无法理解资源被占用和商品从购物车中消失的原因；
     - 下单后立即对用户扣款，而不是发货后扣款；用户支付成功后取消的订单（\~3.6%），需要等待退款，与欧美主流电商平台体验不一致；
   - **商户侧**
   
     - 未支付成功/支付失败最终平台关单的订单（\~3.5%），占用了商家库存等资源，影响低库存商品销售；
     - 商家误以为平台创建订单成功则用户支付成功，误认为过期关单是被平台/风控拦截，造成商家焦虑。

   > a.Background: The current general transaction process of TikTok Shop is "order first, then pay". After the user selects the payment method on the checkout page and clicks to place order, EC Transaction Platform first creates an order, the initial status is "pending payment", and then requests PIPO to start the payment process. After the payment is successful, the money will be deducted immediately (auto capture). If the user gives up the payment or the payment fails, the order remains in the "pending payment" status. The user can choose another payment method to pay again, or close the order manually. If the user does not take any action, the platform will automatically close the timed-out unpaid transaction. Only when the order is closed will the inventory, marketing discounts and other resources occupied by the order be released.
   > 
   > Based on user surveys and merchant feedback, the following problems were found:
   > 
   > - User side
   > 
   >   - US users do not understand the "pending payment" status of the order, and tend to generate an order only after "payment authorization", which means the transaction is confirmed. If payment fails, it is expected that payment will be retried immediately. If payment is abandoned, it means that the purchase is not wanted. The corresponding product should be left in the shopping cart and no pending order should be generated;
   >   - Orders that are not successfully paid/failed to be paid and are eventually closed by the platform (\~3.5%) occupy resources such as user marketing and purchase restriction qualifications, and the products are not retained in the shopping cart. Since the display of this type of order is blocked on the C-end, users cannot understand why resources are occupied and products disappear from the shopping cart;
   >   - Users are deducted money immediately after placing an order, rather than after delivery; orders canceled after successful payment by users (\~3.6%) need to wait for a refund, which is inconsistent with the experience of mainstream e-commerce platforms in Europe and the United States;
   > - Merchant side
   > 
   >   - Orders that are not successfully paid/failed to be closed by the platform (\~3.5%) occupy resources such as merchant inventory, affecting the sales of low-inventory products;
   >   - Merchants mistakenly believe that the user payment is successful if the platform successfully creates an order, and mistakenly believe that the overdue order closure is intercepted by the platform/risk control, causing anxiety for merchants.

   1. **核心产品逻辑调整和目标**

   - 优化交易下单流程 - **先确认成功支付授权结果，再创建交易订单，占用相关库存、营销等资源**；
   - 优化支付流程 - **支付流程拆分Auth和Capture流程，下单前确认用户Auth成功结果，发货时点/auth有效期截止前，再进行Capture真实扣款**；对于高客单价/用户行为异常交易，触发风控人审流程；

   - 提升商家体验：支付成功后占用库存、营销额度等；
   - 提升用户体验：提升逆向场景的到账时效^；支付成功后占用营销券等；
   - 节省平台支付成本（对应Capture前取消的订单）和优化支付风险控制流程（添加发货前风控人审流程）。

   > **b.Key Product Logic**
   > 
   > #1 Optimize the order placement process - place an order after confirming the successful payment authorization result, then occupy the relevant inventory, marketing and other resources;
   > 
   > #2 Optimize the payment process - Switch from Payin mode to Manual Capture mode. Place the order after confirming the authorisation result. Actual Capture will be completed at delivery time or once the auth validity period expires; risk manual review process will be triggered for transactions with high customer unit price/abnormal user behavior.
   > 
   > Aiming to
   > 
   > - improve customers' experience: improve the timeliness of payment when the customer cancels the order before capture; deduct promotion coupons after successful payment, etc.
   > - enhance buyers' experience and decrease unnecessary inventory & promotion occupation
   > - save platform payment cost and optimise risk review process
   > 
   > ^Due to the new order placement process, when the payment is successful but the relevant resources are insufficient, the payment needs to be canceled (\~0.5%), requiring more timeliness than original refund scenarios.

   1. **用户体验 User Experience**

   <table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><td></td><td><b>Order Placement Process</b><br/><b>正向下单流程</b></td><td><b>Second Payment Process</b><br/><b>二次支付流程</b></td><td><b>Cancel Process</b><br/><b>逆向流程</b></td></tr><tr><td><b>现有流程</b><br/><b>Before</b></td><td><img name="image.png" mime="image/png" scale="1.000000" src="LROvbUQFOoO32oxt26Tl6w3hgFd"/><ul><li>The buyer always places an order before payment.  用户先下单再支付</li></ul></td><td><grid><column width-ratio="0.496189"><img name="image.png" mime="image/png" scale="0.722772" src="S62fbKBU5oVr7sxI8j7lWqCDgH0"/></column><column width-ratio="0.503811"><img name="image.png" mime="image/png" scale="0.825792" src="OzlRbATQTowCXBxhzBdlJEcMg4g"/></column></grid><ul><li>The buyer can only reselect the payment method on this page. Shipping methods, item quantity, discount and order notes are NOT allowed to be modified.  用户在本页面只能修改支付方式，不能修改其他订单信息，包括物流方式、商品数量、折扣、备注等</li></ul></td><td><grid><column width-ratio="0.223166"><img name="image.png" caption="Order Details Page&#xA;订单详情页&#xA;" mime="image/png" scale="0.981183" src="QNVmbrTHmoqOIZx8hL7lSwF0gGE"/><p></p></column><column width-ratio="0.382314"><img name="image.png" caption="Cancelled Order&#xA;订单取消状态展示&#xA;" mime="image/png" scale="0.935897" src="E2bkbbadRosJHLxTplelAzU0gCc"/><p></p></column><column width-ratio="0.197269"><img name="image.png" caption="Refund Time Efficiency&#xA;退款时效展示&#xA;" mime="image/png" scale="0.675926" src="ClU2bZ8c7oCK9lxOOwrliBRsgeh"/></column><column width-ratio="0.197250"><img name="image.png" caption="AfterSales Email&#xA;售后邮件展示&#xA;" mime="image/png" scale="0.623932" src="KubZba8M1otwePxDU7nle5hCgPg"/></column></grid></td></tr><tr><td><b>新流程</b><br/><b>After</b></td><td><ul><li>No interaction flow change for C-end.</li><li>Add expressions for new reasons for order placement failure. In addition to payment failure, insufficient inventory/marketing resources are also involved. Corresponding error codes will be displayed on C-end. 本期新增下单失败的原因表达，除了支付失败，还可能包括库存、营销等资源不足等，C端会为用户提示相应错误原因</li></ul></td><td><img name="image.png" mime="image/png" scale="1.000000" src="KmTHbDWaCoeUiNxzMV9lUB8VgNb"/><ul><li>The buyer can edit all the detailed info on this page.  用户在本页面能修改所有信息</li><li>If the buyer leaves this page, the order details will be hidden from the user. And the products will be added back to the shopping cart. 用户退出本页面，相关订单信息不会被展示，商品会加到购物车中</li></ul></td><td><grid><column width-ratio="0.604246"><img name="image.png" caption="Authcancel Time Efficiency&#xA;取消预授权时效展示&#xA;" mime="image/png" scale="0.217333" src="UlQxbRhMjosMjcxbX6xlJnOXgRf"/></column><column width-ratio="0.395754"><img name="image.png" caption="AfterSales Email&#xA;售后邮件展示&#xA;" mime="image/png" scale="0.183333" src="KTFwblgvtodB21xK04Ll3XfXgpc"/></column></grid><ul><li>Add expressions for cancellation process. 新增authcancel相关对客表达</li></ul></td></tr></tbody></table>

   1. **一期实验收益：**

   - **支付侧：**Manual Capture流程对用户售后体验有益。主要体现在电商售后5分满意度指标有显著正向效果（+2.15%）；同时，在电商交易新流程下单失败取消支付场景中，\~30%命中authcancel流程，减少了业务原因交易失败对用户下单支付体验的损害，同时减少了相关成本。
   - **业务侧：**
   
     - 用户流程调整，满足了用户放弃支付/支付失败时修改信息的诉求，对二次提单转化有正向影响，提升了用户体验。
     - 新下单支付流程对商家体验提升较大，未支付占用库存的订单量大幅下滑，实验组占比从对照组的近4%降为不足0.1%，收益显著。

   > d.Experimental benefits:
   > 
   > - Payment: The Manual Capture process is beneficial to the user’s after-sales experience. It is mainly reflected in the significant positive effect of the 5-point satisfaction index of CSAT (+2.15%); at the same time, in the scenario of failed order cancellation and payment cancellation, \~30% hit the authcancel process, mitigating the damage of the user experience while reducing related costs.
   > - Ecommerce:
   > 
   >   - Adjustment of user journey satisfies users’ requests to modify information when giving up payment/payment failure, has a positive impact on the conversion of secondary order placement, and improves user experience.
   >   - The new order placement and payment process has greatly improved the merchant experience. The number of unpaid orders occupying inventory has dropped sharply. The proportion of the experimental group has dropped from nearly 4% of the control group to less than 0.1%, and the benefits have been significant.
2. **用户快捷下单  One Click Pay**

   <blockquote><p><cite doc-id="JarOdMyckoPDbjxTOLRc5EFInmd" file-type="docx" title="[GPP Doc] Global Selling US/UK - OneClickPay - Product Solution PRD" type="doc"></cite></p></blockquote>

   1. **背景：**针对Global Selling活动商品，当用户完成第一单购买后，在支付结果页上，业务会推荐带有“OneClickPay”按钮的商品，用户可以在3小时内使用上单支付方式（多数情况；可能存在需要让用户重新选择支付方式的场景）快速完成下单支付。同时，业务侧上线次单免邮需求，以最大程度提升CO和GMV。

   > a.Background: For Global Selling products, when users complete their first purchase, the business will recommend products with a "OneClickPay" button on the payment result page. Users can use the previous payment method within 3 hours (in most cases; there may be scenarios where users need to reselect the payment method) to quickly complete the order and payment. At the same time, the business side launches the first order free shipping requirement to maximize CO and GMV.

   1. **用户体验 User Experience:**

   ![图片展示了美国展业国家下用户快捷下单的“OneClickPay”业务用户体验流程。从带有商品展示和“OneClickPay”按钮的页面开始，呈现了用户点击按钮后可能经历的一系列页面交互流程，包括不同状态和操作下的页面变化。这些页面展示了从商品推荐到下单支付等环节的用户操作路径。该图与上下文介绍的针对Global Selling活动商品，用户在支付结果页使用“OneClickPay”按钮快速下单支付的内容相呼应，直观呈现了用户体验流程。](https://feishu.cn/file/VrAZbtylgocAbExJdPYlKMWrgad)

   1. **实验效果及后续：**
   
      - 根据成单分布，加购按钮改为一键支付按钮带来直播、搜索、视频来源的sku单量增多。
      - 立即购买链路下，由于立即购买入口增多&跳过提单页，立即购买总转化提升（0.75%->0.86%）。
      - 电商侧优化活动选品逻辑后，一键支付将配合业务在电商活动中对客。

   > c.Experimental benefits:
   > 
   > - According to the order distribution, the add to cart button was changed to the one-click-pay button, which increased the number of sku orders from live broadcast, search, and video sources.
   > - In the buy now scenario, the total conversion rate increased (0.75%->0.86%) due to the increase of buy now entrances and skipping the order summary page.
   > - After the e-commerce side optimizes the activity selection logic, one-click payment will cooperate with the business to connect with customers in e-commerce activities.
3. **用户快捷下单 - ApplePay Express Checkout**PDPShopping cart一期实验发现存在以下流程及用户体验问题待解决：无地址新用户在前置页面无法查看包含物流费用和税费的最终商品价格；地址校验失败后的对客提示不够明确；地址校验多次失败后，未提供使用普通提单流程的选项，用户只能持续尝试。基于以上问题，[电商C端](https://bytedance.sg.larkoffice.com/docx/YmPVdT7MLon0vJxCTqtl2TKYgQh)将通过限制新客使用，简化用户流程，支持新客自动领券，强化地址错误提示，新增普通提单流程兜底，对整体用户流程进行优化，预计7月上线。新版用户交互示意如下：

   1. **背景：**为提升新客转化，对标竞品快捷支付能力，在TTS PDP以及购物车接入Apple Pay快捷下单能力，支持获取由Apple Pay提供的用户地址信息，跳过TTS原本的地址填写页以及提单页，一步完成提单以及支付。

   > a.Background: In order to improve the conversion of new customers and benchmark the quick payment capabilities of competing products, offer the Apple Pay Express Checkout capability in the TTS PDP and shopping carts scenarios. It supports obtaining user address information provided by Apple Pay, skipping the original address filling page and the order summary page of TTS, and completing the order placement and payment in one step.

   1. **用户体验 User Experience**

   ![图片展示了美国电商业务中TTS PDP场景下Apple Pay快捷下单的用户体验流程。从左至右依次呈现商品展示页、可使用的优惠提示页、支付页等多个页面，显示了从浏览商品到完成支付的过程。最后两个页面展示了支付成功提示以及订单详情。该图片与上下文紧密相关，直观呈现了上文所述的在TTS PDP接入Apple Pay快捷下单能力后的用户交互流程，帮助理解用户体验环节。](https://feishu.cn/file/FoTAbNsbNoMTq1x5WxjltZ5EgRc)

   ![图片展示了美国特色场景中TTS PDP及购物车接入Apple Pay快捷下单的用户交互流程。从左至右依次呈现点击“Use Apple Pay”、确认支付、选择支付方式等界面，还包括订单确认和支付完成等页面。画面以灰白色调为主，红色部分突出显示关键操作按钮。该图片与上下文紧密相关，是对电商业务线在美国展业时Apple Pay快捷下单用户体验流程的直观展示，也为后续问题及优化计划提供了场景参考。](https://feishu.cn/file/R4LPbRqY3oWHQwxSWJelm5aigAe)

   1. **问题及优化计划：**

   ![图片展示了美国电商业务中用户快捷下单-Apple Pay Express Checkout的新版用户交互示意。左侧是商品展示页，显示一件售价80美元的旅行包；中间是选择结账方式页，有“Checkout”和“Pay”按钮；右侧两页为支付信息页，显示支付卡片、联系邮箱、配送地址及预计到货时间等信息。该图片与上文提到的针对一期实验问题，由电商C端于7月上线的优化后的用户交互流程相关，直观呈现了优化后的操作流程界面。](https://feishu.cn/file/A1uRbBZBIolZEdxlBiol9wWhgPe)

> c.Drawbacks and optimization:
> 
> It is found that there are some problems to be solved in the 1st round experiment: new users without addresses cannot view the final product price including logistics costs and taxes on the EC page; the prompts to customers after address verification fails are not clear enough; after multiple address verification failures, the option of using the EC order summary page to finish the order placement is not provided.
> 
> TTS C-end will optimize the overall user experience and journey by restricting the use of new customers, simplifying the user process, supporting new customers to automatically receive coupons, strengthening the prompts for address errors, and adding the EC order summary page as a backup option, and it is expected to be launched in July. The new version of user interaction is shown above.

### 后续重点项目|Upcoming Key Projects

1. 用户体验优化

   1. 基于用户调研和众测，对电商收银台及快捷下单用户流程进行不断优化 - WIP
2. 支持业务多样化场景对客

   1. 用户场景
   
      1. 预售/定制订单下单支付流程搭建 - WIP
      2. 用户捐款支付流程搭建 - Q3
      3. 拍卖
   2. 商家场景
   
      1. 商家欠款扣缴 - WIP
3. User experience optimization

   1. Based on user research and field testing, continuously optimize the user experience of the checkout cashier and fast checkout  - WIP
4. Support diversified and new business scenarios

   1. Buyer
   
      1. Design the order placement and payment process for pre-sale/customized orders - WIP
      2. Design the order placement and payment process for the donation scenario - Q3
      3. Design the order placement and payment process for auction orders
   2. Merchant
   
      1. Handle the negative balance - WIP



## 东南亚-印尼、马来、越南、泰国、菲律宾、新加坡 SEA- ID, MY, VN, TH, PH, SG

### 服务模式**|Payment Solution**

SEA地区，最早历史上采用的是统一的服务模式：TT.SG作为业务主体，PIPO.HK作为支付主体并提供给业务提供自营的支付解决方案

> 以TTS-VN为例，说明此服务模式的解决方案



For SEA, previously we used the same solution, which is TT.SG be the business entity, and PIPO.HK be the payment entity and provide self-managing solution to ecommerce

> Take TTS-VN as an example. Explain more about the solution

<grid><column width-ratio="0.500000"><p><b>协议关系 agreement</b></p><whiteboard token="VGCvwZdHfhVgmKbDlafleID7g8d"></whiteboard></column><column width-ratio="0.500000"><p><b>资金方案 fund flow</b></p><whiteboard token="MMwqwkiUghXM3xbxzR5l8L7Rgih"></whiteboard></column></grid>

随着外部市场监管环境的不断严格，对于业务主体本地化以及支付主体本地化的要求也在不断的变高，为了保证各市场能够更合规的展业，从2023年底开始针对SEA的各国家，业务与PIPO也进行主体本地化改造，目前菲律宾、印尼、马来已经完成了一轮改造，泰国进行中。（新加坡无需进行）

> As the external market regulatory environment has become increasingly strict, the requirements for business entity localization and payment entity localization have been continuously rising. In order to ensure conduct business within regulation across different markets, starting from the end of 2023, business and PIPO entities have been undergoing reforms for SEA countries.

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><td vertical-align="middle"><b>国家 country</b></td><td><b>改造内容 content</b></td><td><b>协议关系 agreement</b></td><td><b>资金方案 fund flow</b></td></tr><tr><td>菲律宾 PH</td><td>业务主体：TT.SG→BD.PH<br/>支付主体：<ul><li>业务本地主体服务商：PIPO.HK→PIPO.PH（自营）</li><li>业务跨境主体服务商：PIPO HK（自营）</li></ul><br/> <br/>Business entity：TT.SG→BD.PH<br/>Payment entity：<ul><li>L2L：PIPO.HK→PIPO.PH（self-managing）</li><li>crossborder：PIPO HK（self-managing）</li></ul></td><td><whiteboard token="Bea4weAQNheaCxbmG4XllQ1ig7c"></whiteboard></td><td><whiteboard token="DFzQwblF4h3wOsbDxAFl4GlOgze"></whiteboard></td></tr><tr><td>印尼 ID<blockquote><p>印尼无跨境商家</p><p>Do not have crossborder sellers in ID</p></blockquote></td><td>业务主体：TT.SG→Tokopedia<br/>支付主体：PIPO.HK（自营→托管）<br/>Business entity：TT.SG→Tokopedia<br/>Payment entity：PIPO.HK（self-managing→escow）</td><td><whiteboard token="DcbbwacHOh0gKmbOUpSlxrEJgie"></whiteboard></td><td><whiteboard token="XnGzwQzdVhYq7jbhgValcunFgRb"></whiteboard></td></tr><tr><td>马来 MY</td><td>业务主体：TT.SG→TT.MY<br/>支付主体：PIPO.HK（自营）<br/>Business entity：TT.SG→TT.MY<br/>Payment entity：PIPO HK（self-managing）</td><td><whiteboard token="Ksh7wNXHBhnP9RbZI8ZlWrcwgod"></whiteboard></td><td><whiteboard token="SgJ5wtXRqhwtnIbB4XrlXY2Jgdd"></whiteboard></td></tr><tr><td>泰国 TH<blockquote><p>与业务联调中，尚未上线</p></blockquote></td><td>业务主体：TT.SG→TT.TH<br/>支付主体：PIPO.HK（自营）<br/>Business entity：TT.SG→TT.TH<br/>Payment entity：PIPO HK（self-managing）</td><td><whiteboard token="GRUoweyRzh16ckb9otKldHO4gEd"></whiteboard></td><td><whiteboard token="CL0mwDdynhWJCGbzrEzlalfsgnb"></whiteboard></td></tr></tbody></table>



### **支付能力|Payment capabilities**

**Product capabilities**

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td colspan="2">Product</td><td>是否有应用 live or not</td></tr><tr><td colspan="2">入驻 onboarding</td><td>✅</td></tr><tr><td rowspan="7">收单<br/>collection</td><td>合单支付 shipping cart payment</td><td>✅</td></tr><tr><td>先绑后付 tokenisation payment</td><td>✅</td></tr><tr><td>支付营销 payment promotion</td><td>✅</td></tr><tr><td>组合支付 hybird payment</td><td>✅</td></tr><tr><td>TikTok Paylater</td><td>✅</td></tr><tr><td>One Click Pay</td><td>/</td></tr><tr><td>Express Checkout</td><td>/</td></tr><tr><td rowspan="3">退款<br/>refund</td><td>支持退款到原支付方式 Refund to the original payment method</td><td>✅</td></tr><tr><td>支持退款到 credit account Refund to credit</td><td>✅</td></tr><tr><td>支持退款转代发 Refund to payout</td><td>✅</td></tr><tr><td colspan="2">分账 split-profit</td><td>✅</td></tr><tr><td colspan="2">结算 settlement</td><td>✅</td></tr><tr><td colspan="2">平台打款/自主提现 disbursement</td><td>✅</td></tr><tr><td colspan="2">结汇 foreign exchange settlement</td><td>✅</td></tr><tr><td colspan="2">Bwallet</td><td>✅</td></tr></tbody></table>



**Payment method**

<table><colgroup><col/><col/><col/><col/><col/><col/></colgroup><tbody><tr><td>Market</td><td>Payment Direction</td><td>Roles</td><td>Payment Type</td><td>Payment Method</td><td>Data Metrics<blockquote><p>Time range: May 1st~June 15th</p></blockquote></td></tr><tr><td rowspan="9">ID</td><td rowspan="6">Payin</td><td rowspan="6">Buyer<br/>（Q2 User count：178788332 ）</td><td>CCDC</td><td>Visa、MasterCard、Amex、JCB</td><td rowspan="6"><chart-embedded thumbnail-url="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZjJkYzY1ZWRjNDA4YjE2MTFhMjlhNTBkNzA1YjRkNmRfZDI2ZDE1ZWViNTVmMmJkYjExZmU2MTU2OTNjNzVkYzJfSUQ6NzY3MjY2ODU2OTc1NDI0Mjc5Ml8xNzg2NDUwNzM5OjE3ODY1MzcxMzlfVjM" token="chtlgM9UgyyZ7MWTsL3AkLi4BPb"></chart-embedded><chart-embedded thumbnail-url="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MDU0NjY0YzJiOTA4MTEzYzFhYzkwZTg0OGI5NDc5NmFfYjUzMWRhNDYxYTY0NDUxY2ZjYzc5Y2Q4MzQ0YjU1YWJfSUQ6NzY3MjY2ODU3NTYwOTQ1ODM5OF8xNzg2NDUwNzM5OjE3ODY1MzcxMzlfVjM" token="chtlgbsKOYCvBfB65JFFTXPGw3I"></chart-embedded><br/>COD Proportion ：77%</td></tr><tr><td>eWallet</td><td>Dana、GoPay、OVO、LinkAja</td></tr><tr><td>Bank transfer</td><td>BCA、BRI、BNI、Mandiri、BSI、CIMB and other 12 banks</td></tr><tr><td>OTC (over the counter)</td><td>Indomaret、Alfa、Circle K、POSPAY</td></tr><tr><td>BNPL</td><td>TikTok Paylater</td></tr><tr><td>COD (cash on delivery)</td><td>COD</td></tr><tr><td rowspan="3">Payout</td><td rowspan="2">Local Creator（Creator count 492477）</td><td>Bank account</td><td>Bank account</td><td rowspan="2">PSR<br/>Bank account： 97.70%<br/>Dana：99.70%</td></tr><tr><td>eWallet</td><td>Dana</td></tr><tr><td>Local Seller/MCN/TAP<br/>(Seller count 201924)</td><td>Bank account</td><td>Bank account</td><td>PSR Bank account: 98.89%</td></tr><tr><td rowspan="9">MY</td><td rowspan="5">Payin</td><td rowspan="5">Buyer<br/>（Q2 User count：67377552）</td><td>CCDC &amp; Credit card installment</td><td>Visa、MasterCard、Amex（do not support installment）</td><td rowspan="5"><chart-embedded thumbnail-url="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MDYzNDJhMmMyNjIzMzQ4NTYzMGU5NDkwN2JkMDk2YWJfYTViODU2OTA0Mjc1YWVjZmFlYzJkMzcxODcyZDlkMTBfSUQ6NzY3MjY2ODU3OTI2MjY5NzE4Ml8xNzg2NDUwNzM5OjE3ODY1MzcxMzlfVjM" token="chtlgfYNAEYRLrRImK5eDGnleNf"></chart-embedded><chart-embedded thumbnail-url="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NzVhNDJmYjY5M2Y3YjllM2FmNTlkMDA0NmMyYzY0YTdfNmU0YWZhZTQ5ODQzM2QyN2E4Y2M3Y2IzZmZkMDAxNjNfSUQ6NzY3MjY2ODU4MzY2NjY2NzIzMV8xNzg2NDUwNzM5OjE3ODY1MzcxMzlfVjM" token="chtlg3vJ3krbM30FTH5FR7ibe3d"></chart-embedded><br/>COD Proportion ：47%</td></tr><tr><td>eWallet</td><td>TouchnGo、GrabPay、Boost</td></tr><tr><td>iBanking（FPX）</td><td>MayBank、CIMB、BANKISLAM and other 15 banks</td></tr><tr><td>BNPL</td><td>Atome</td></tr><tr><td>COD (cash on delivery)</td><td>COD</td></tr><tr><td rowspan="4">Payout</td><td>Local Creator<br/>（Creator count 153851）</td><td>Bank account</td><td>Bank account</td><td>PSR: Bank account: 98.65%</td></tr><tr><td>Local Seller/MCN/TAP<br/>(Seller count 58329 )</td><td>Bank account</td><td>Bank account</td><td>PSR: Bank account: 98.90%</td></tr><tr><td rowspan="2">Xcross-border POP seller<br/>(Seller count 26562)</td><td>Bank account</td><td>Bank account</td><td rowspan="2">PSR<br/>LIANLIAN_PAY：99.94%<br/>AIRWALLEXEWALLET：95.40%<br/>BANK ACCOUNT:  99.67%<br/>PINGPONG: 99.99%<br/>PAYONEER: 99.36%</td></tr><tr><td>eWallet</td><td>Lianlian、Payoneer、Pingpong、Airwallex</td></tr><tr><td rowspan="10">VN</td><td rowspan="5">Payin</td><td rowspan="5">Buyer<br/>（Q2 User count：115845933 ）</td><td>CCDC &amp; Credit card installment</td><td>Visa、MasterCard、Amex</td><td rowspan="5"><chart-embedded thumbnail-url="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NzFhN2Q1NGE4N2UxYzg3NWIxODEzOTEzYWE3OTIwNTJfM2IxYTc5MjlmOTI3MGQwN2M0YzZmMzE5Zjc4ODZmZDJfSUQ6NzY3MjY2ODU4ODQ5ODY4NTY2MV8xNzg2NDUwNzQwOjE3ODY1MzcxNDBfVjM" token="chtlgTKGvSiuMS0LxZUHKRe20qe"></chart-embedded><chart-embedded thumbnail-url="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZGVmMDlhZjA1NmVhNGVkNDRlODFjYjZhYmViMjQ4ZTVfYzI4ODMyMmZhYmU4MzJhYzI5NDQ5MThiNzg4Y2U3MzVfSUQ6NzY3Mjc0NzQ5NTcxMzI2MzY3Ml8xNzg2NDUwNzQwOjE3ODY1MzcxNDBfVjM" token="chtlgnriwbYwss6EEDbcykQtc0f"></chart-embedded><br/>COD proportion: 90%</td></tr><tr><td>Domestic ATM Card</td><td>VIETCOMBANK、VIETINBANK、TECHCOMBANK、MBBANK and other 37 banks</td></tr><tr><td>eWallet</td><td>MoMo、ZaloPay</td></tr><tr><td>Mobile banking（VNPay）</td><td>VIETCOMBANK、VIETINBANK、BIDV and other 14 banks</td></tr><tr><td>COD (cash on delivery)</td><td>COD</td></tr><tr><td rowspan="5">Payout</td><td rowspan="2">Local Creator<br/>（Creator count：361766）</td><td>Bank account</td><td>Bank account</td><td rowspan="2">PSR:<br/>Bank account: 99.65%<br/>ZaloPay: 94.42%</td></tr><tr><td>eWallet</td><td>ZaloPay</td></tr><tr><td>Local Seller/MCN/TAP<br/>(Seller count 134230)</td><td>Bank account</td><td>Bank account</td><td>PSR: Bank account: 99.51%</td></tr><tr><td rowspan="2">Xcross-border POP seller<br/>(Seller count 36788 including both TH and VN)</td><td>Bank account</td><td>Bank account</td><td rowspan="2">PSR (Including both TH and VN)<br/>LIANLIAN_PAY：99.97%<br/>BANK ACCOUNT: 98.33%<br/>AIRWALLEXEWALLET: 97.90%<br/>PAYONEER: 99.01%<br/>PINGPONG: 99.94%</td></tr><tr><td>eWallet</td><td>Lianlian、Payoneer、Pingpong、Airwallex</td></tr><tr><td rowspan="11">TH</td><td rowspan="5">Payin</td><td rowspan="5">Buyer<br/>（Q2 User count：146308368）</td><td>CCDC &amp; Credit card installment</td><td>Visa、MasterCard、Amex（do not support installment）</td><td rowspan="5"><chart-embedded thumbnail-url="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ODQxODZjMmNkNzg4NjE2YTdkNWQwYTZmNTRhNjA3M2JfM2Y4MTJlNDEyZDk2OGNkNjk2OTk3YWUwYjZhZDlkYTJfSUQ6NzY3MjY2ODU5NDE2OTIwNDQ0NF8xNzg2NDUwNzQxOjE3ODY1MzcxNDFfVjM" token="chtlgFhPGaZYe8FiEK9QHrP6CEe"></chart-embedded><chart-embedded thumbnail-url="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NjFhMGFjZjhjZTM1MTBjMGMyNzdjNDVhMTkzMzQzYzFfNTk0Y2ZmMmRlZWU3YjY3YzhmNTg0YTY1NWI0ZDgxZjVfSUQ6NzY3MjY2ODU5OTczMDg2NzkzNl8xNzg2NDUwNzQxOjE3ODY1MzcxNDFfVjM" token="chtlg3ygBP5a5YqUMZ7nonVfdAh"></chart-embedded><br/>COD Proportion ：76%</td></tr><tr><td>eWallet</td><td>Truemoney，RabbitLinePay，TTS Credit</td></tr><tr><td>Mobile banking</td><td>Kbank、SCB、KTB、Bay、BBL</td></tr><tr><td>iBanking（老版本only）</td><td>Kbank、SCB</td></tr><tr><td>COD (cash on delivery)</td><td>COD</td></tr><tr><td rowspan="6">Payout</td><td rowspan="3">Local Creator<br/>(Creator count:439099)</td><td>Bank account</td><td>Bank account</td><td rowspan="3">PSR<br/>Bank account: 99.41%<br/>Promptpay: 98.73%<br/>Truemoney: 99.86%</td></tr><tr><td>Bank account proxy</td><td>Promptpay</td></tr><tr><td>eWallet</td><td>Truemoney</td></tr><tr><td>Local Seller/MCN/TAP<br/>(Seller count 105209)</td><td>Bank account</td><td>Bank account</td><td>PSR Bank account:99.36%</td></tr><tr><td rowspan="2">Xcross-border POP seller</td><td>Bank account</td><td>Bank account</td><td rowspan="2">Please see VN part</td></tr><tr><td>eWallet</td><td>Lianlian、Payoneer、Pingpong、Airwallex</td></tr><tr><td rowspan="10">PH</td><td rowspan="5">Payin</td><td rowspan="5">Buyer<br/>（Q2 User count：114296007 ）</td><td>CCDC</td><td>Visa、MasterCard、Amex</td><td rowspan="5"><chart-embedded thumbnail-url="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NDA0OWE0NmY2MWQ3YzRjYTIwYzBlM2Y3OTZhNDMxYzZfNjg3NDUwZjY5ZDg2YWZjYTg3YzdlNTdjYTljYzc5ODRfSUQ6NzY3MjY2ODYwMDc5MjE1NzkxNV8xNzg2NDUwNzQxOjE3ODY1MzcxNDFfVjM" token="chtlgwnrJO8XZfZRcf7VdstXxqB"></chart-embedded><chart-embedded thumbnail-url="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NDRhNGM4NzY3ZTQ1MzEyMWVmMTZjZDA4YTBjOTk3NjBfZWQwOGU5ZDc3MTRjZDIxNzE2NDNmNmY1Y2MwYjdkZjlfSUQ6NzY3MjY2ODYwNjgxMDgzNjcxMF8xNzg2NDUwNzQxOjE3ODY1MzcxNDFfVjM" token="chtlgWGivV1OWxKHPpIKLcAB5hb"></chart-embedded><br/>COD Proportion ：87%</td></tr><tr><td>eWallet</td><td>Gcash、PayMaya</td></tr><tr><td>iBanking</td><td>BPI、Union Bank</td></tr><tr><td>BNPL</td><td>TikTok Paylater</td></tr><tr><td>COD (cash on delivery)</td><td>COD</td></tr><tr><td rowspan="5">Payout</td><td rowspan="2">Local Creator<br/>(Creator count:345607)</td><td>Bank account</td><td>Bank account</td><td rowspan="2">PSR：<br/>Bank account: 97.54% <br/>Gcash:96.96%</td></tr><tr><td>eWallet</td><td>Gcash</td></tr><tr><td>Local Seller/MCN/TAP<br/>(Seller count: 59137)</td><td>Bank account</td><td>Bank account</td><td>PSR Bank account: 98.34%</td></tr><tr><td rowspan="2">Xcross-border POP seller<br/>(Seller count：19008)</td><td>Bank account</td><td>Bank account</td><td rowspan="2">PSR<br/>LIANLIAN_PAY: 99.98%<br/>BANK ACCOUNT: 99.56%<br/>PINGPONG: 99.83%<br/>AIRWALLEXEWALLET: 100.00%<br/>PAYONEER: 99.33%</td></tr><tr><td>eWallet</td><td>Lianlian、Payoneer、Pingpong、Airwallex</td></tr><tr><td rowspan="6">SG</td><td rowspan="2">Payin</td><td rowspan="2">Buyer<br/>（Q2 User count：1441232 ）</td><td>CCDC</td><td>Visa、MasterCard、Amex</td><td rowspan="2"><chart-embedded thumbnail-url="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YmJlMzVkZDcxYzE0M2ZlMDc3NTUzYjdiOTMzNjdjNzJfZjhiMjY1YzI5OWU4YTA2ZGVkODVmNTgyNjZlMzIwMTRfSUQ6NzY3MjY2ODYwNzUwNzIwNTg1Ml8xNzg2NDUwNzQxOjE3ODY1MzcxNDFfVjM" token="chtlgfVbFTwD32aPzmYKiP6rsFf"></chart-embedded><chart-refer-host-perm thumbnail-url="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZDkxY2YxNGRkYTE4YjcwZTZkNmYyY2Y2OWJmZDdmZDBfZjgzZGZhMzNlNTg2MWFlMjNhODEzN2E4ZGYyYzY3OTlfSUQ6NzY3MjY2ODYxMzAzNTMxNDkwOF8xNzg2NDUwNzQxOjE3ODY1MzcxNDFfVjM" token="chtlgOHO4GS8smjgAh8mXRTYP7d"></chart-refer-host-perm></td></tr><tr><td>eWallet</td><td>ApplePay、GrabPay</td></tr><tr><td rowspan="4">Payout</td><td>Local Creator<br/>(Creator count:1475)</td><td>Bank account</td><td>Bank account</td><td>PSR:Bank account:99.05%</td></tr><tr><td>Local Seller/MCN/TAP<br/>(Seller count: 4378)</td><td>Bank account</td><td>Bank account</td><td>PSR: Bank account: 83.54%</td></tr><tr><td rowspan="2">Xcross-border POP seller<br/>(Seller：9069)</td><td>Bank account</td><td>Bank account</td><td rowspan="2">PSR<br/>LIANLIAN_PAY: 99.97%<br/>AIRWALLEXEWALLET: 99.53%<br/>BANK ACCOUNT: 97.03%<br/>PAYONEER: 99.68%<br/>PINGPONG: 100.00%</td></tr><tr><td>eWallet</td><td>Lianlian、Payoneer、Pingpong、Airwallex</td></tr></tbody></table>



### 特色场景|Distinctive features

在ID市场，为了满足当地政府合规要求，电商收购了Tokopedia。随着收购的完成，电商业务也开展了一系列关于合规和业务拓展的改造。

In the Indonesian (ID) market, in order to meet the local government's compliance requirements, the e-commerce company acquired Tokopedia. Following the completion of the acquisition, the e-commerce business has undertaken a series of reforms and initiatives focused on compliance and business expansion.

<table><colgroup><col/><col/><col/><col/></colgroup><tbody><tr><td colspan="2"><b>项目阶段 Stage</b></td><td><b>项目目标 Target</b></td><td><b>备注 Remark</b></td></tr><tr><td colspan="2">Phase 1： 业务合规改造<br/>时间：1~2月<br/>Phase 1：Business Compliance Reforms<br/>Time: Jan~Feb</td><td><ul><li>修改品牌名为Tokopedia</li><li>电商业务主体TT.SG切换为Tokopedia</li></ul><ul><li>Change the brand name to Tokopeida</li><li>The business entity switches from TT.SG to Tokopedia</li></ul></td><td><grid><column width-ratio="0.225870"><img name="image.png" mime="image/png" scale="0.973333" src="MH2lbnKqwolSp3xaS3vl0OU8gAg"/></column><column width-ratio="0.386942"><img name="image.png" mime="image/png" scale="0.648889" src="JzUoboSFcoIPzAxkF6Vlfae9gIg"/></column><column width-ratio="0.387187"><img name="image.png" mime="image/png" scale="0.675926" src="TJj8bqXAmoNaz1xunEGlcNjgg8g"/></column></grid></td></tr><tr><td rowspan="2">Phase 2： 系统融合<br/>Phase 2: System merge</td><td>Phase 2.1 支付合规改造<br/>时间：2月~4月<br/>Phase 2.1 Payment compliance reforms<br/>Time: Feb~Apr</td><td>满足Payment is processed by Tokopedia的要求<ul><li>TTS-ID切换经营模式，从PIPO自营切换至MOR模式</li><li>对于TTS-ID，通过PIPO接入TKPD payment，并集成其背后的27个Payin支付方式和3个Payout支付方式</li></ul><br/>Meeting the requirement of payment is processed by Tokopedia<ul><li>TTS-ID's business mode switches from self-managing to escow mode</li><li>Payment method expansion: integrate with 27 payin payment methods and 3 payout payment methods via Tokopedia payment</li></ul></td><td><whiteboard token="DyygwqTyhhhHB5bH7RllzxsZgVS"></whiteboard></td></tr><tr><td>Phase 2.2 业务场景拓展<br/>时间：4月~至今<br/>Phase 2.2 Business expansion<br/>Time: Apr~ now</td><td><ul><li>B端商家/达人进行迁移融合，实现“一个B端两个C端”的模式，并以TTS seller center作为唯一的商家后台；预计10月底灰度上线；</li><li>C端买家账户关联，通过打通用户在TTS和Tokopedia的双端的行为数据，进一步促进用户转化，提升ID市场GMV；预计电商侧6月底上线。</li></ul><ul><li>Merge Tokopedia seller/creator to TikTok: let TikTok seller center and TikTok seller app be the only platform for sellers, meaning that after seller publishes the good, it can be sold both on Tokopedia app and TikTok app;</li><li>Link buyer account between Tokopedia and TikTok: connect user behavior data across TTS and Tokopedia Platforms after account linking, to further enhance user conversion and boost ID market GMV.</li></ul></td><td><grid><column width-ratio="0.273714"><img name="image.png" mime="image/png" scale="0.501374" src="VNIrb72ZhoBROuxlkKclB35bgnd"/></column><column width-ratio="0.726286"><img name="image.png" mime="image/png" scale="0.264493" src="CUj0bfbIQo2nNyxF6kuln2lEgwh"/></column></grid></td></tr></tbody></table>



### 后续重点项目|Upcoming Key Projects

1. 推进Tokopedia融合专项，以达到业务GMV的1+1>2（TTS和Tokopedia合并后GMV提升）的业务目标；
2. PSR&用户支付NPS提升：PSR提升以及接入更多支付方式
3. 主体本地化：

   1. 业务主体本地化：TH，VN
   2. 支付主体本地化：支付牌照申请 ID，MY等
4. 创新产品搭建：保险、Seller loan等



1. Tokopedia Integration Advancement:

   - The goal is to achieve a 1+1>2 synergy in terms of GMV (Gross Merchandise Value) by merging Tokopedia's operations.
   - This aims to drive an increase in the combined GMV after integrating Tokopedia's business.
2. PSR & User Payment NPS Improvement:

   - PSR enhancement
   - Integrating more payment methods to improve the user payment experience
3. Entity Localization:

   - Business entity localization in Thailand (TH) and Vietnam (VN)
   - Payment entity localization, including payment license applications in Indonesia (ID) and Malaysia (MY)
4. New Product Development:

   - Building innovative products such as insurance and seller loans



## 欧洲-英国、西班牙、爱尔兰**|Europe - UK, ES, IE**

### 服务模式**|Payment Solution**

英国、西班牙、爱尔兰是单渠道（Stripe）托管模式，协议关系与资金方案如下：

> 在西班牙、爱尔兰方案中我们突破了Paypal不与平台间接对接的限制，通过Stripe接入了Paypal，后续在英国也会使用同样的方案。



The UK, Spain, and Ireland adopted a single channel (Stripe) escrow solution. The agreement relationship and fund flow are as follows:

> In the Spanish and Irish solutions, we broke through the limitation of PayPal not directly connecting with the platform and connected to PayPal through Stripe. We will also use the same solution in the UK in the future.

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td vertical-align="middle"><b>国家</b><blockquote><p>Countries</p></blockquote></td><td><b>协议关系</b><blockquote><p>Agreement </p></blockquote></td><td><b>资金方案</b><blockquote><p>Fund flow</p></blockquote></td></tr><tr><td vertical-align="middle"><b>英国</b><blockquote><p>UK</p></blockquote></td><td><whiteboard token="JkddwTTaGhDdiebE7kFlXijJgke"></whiteboard></td><td><whiteboard token="Q6LmwTbKChvOA7bEzeglgjqugVb"></whiteboard></td></tr><tr><td vertical-align="middle"><b>西班牙、爱尔兰</b><blockquote><p>Spain, and Ireland</p></blockquote></td><td><whiteboard token="KFnCwcYtfheUofbwD8Fljgr0gUe"></whiteboard></td><td><whiteboard token="IEJPwJflohaRRyboTtelvKYPgme"></whiteboard></td></tr></tbody></table>



### **支付能力|Payment capabilities**

**Product capabilities**

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td colspan="2">Product</td><td>是否有应用 live or not</td></tr><tr><td colspan="2">入驻 onboarding</td><td>✅</td></tr><tr><td rowspan="7">收单<br/>collection</td><td>合单支付 shipping cart payment</td><td>✅</td></tr><tr><td>先绑后付 tokenisation payment</td><td>✅</td></tr><tr><td>支付营销 payment promotion</td><td>✅</td></tr><tr><td>组合支付 hybird payment</td><td>/</td></tr><tr><td>TikTok Paylater</td><td>/</td></tr><tr><td>One Click Pay</td><td>✅</td></tr><tr><td>Express Checkout</td><td>✅</td></tr><tr><td rowspan="3">退款<br/>refund</td><td>支持退款到原支付方式 Refund to the original payment method</td><td>✅</td></tr><tr><td>支持退款到 credit account Refund to credit</td><td>/</td></tr><tr><td>支持退款转代发 Refund to payout</td><td>/</td></tr><tr><td colspan="2">分账 split</td><td>✅</td></tr><tr><td colspan="2">结算 settlement</td><td>✅</td></tr><tr><td colspan="2">平台打款/自主提现 disbursement</td><td>✅</td></tr><tr><td colspan="2">结汇 foreign exchange settlement</td><td>✅</td></tr><tr><td colspan="2">Bwallet</td><td>✅</td></tr></tbody></table>



**Payment Methods**

<table><colgroup><col/><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>Market</b></td><td><b>Payment Direction</b></td><td><b>Roles</b></td><td><b>Payment Type</b></td><td><b>Payment Method</b></td><td><b>Data Metrics</b></td></tr><tr><td rowspan="11"><b>UK</b></td><td rowspan="3">payin</td><td rowspan="3">Buyers（Q2 user with successful payment：9,228,441）</td><td>CCDC</td><td>Visa、MasterCard、Amex、Diners Club</td><td rowspan="3"><grid><column width-ratio="0.500000"><img name="成功单量占比.png" mime="image/png" scale="1.000000" src="JhL2bfPJvoF1kaxpAsMlJDnNgwt"/></column><column width-ratio="0.500000"><img name="成功率.png" mime="image/png" scale="1.000000" src="YpRQbAloqoCofjxNUghlpPfDgxh"/></column></grid></td></tr><tr><td>eWallet</td><td>Applepay、 GooglePay</td></tr><tr><td>BNPL</td><td>Klarna、Clearpay</td></tr><tr><td rowspan="8">payout</td><td>Local creators</td><td>bankaccount</td><td>bankaccount</td><td rowspan="8"><img name="成功率 (1).png" mime="image/png" scale="1.000000" src="IkWKbHIV3o8XLexf1CwlHWbBgHf"/></td></tr><tr><td>Local Merchants/MCN/TAP</td><td>bankaccount</td><td>bankaccount</td></tr><tr><td>Seitu</td><td>eWallet</td><td>Lianlian</td></tr><tr><td rowspan="2">CN/HK POP Merchants</td><td>bankaccount</td><td>bankaccount</td></tr><tr><td>eWallet</td><td>Lianlian、Payoneer、Pingpong、Airwallex（灰度中）</td></tr><tr><td>CN/HK Full-service Merchants</td><td>eWallet</td><td>PIPOWALLET</td></tr><tr><td rowspan="2">CN/HK MCN/TAP</td><td>bankaccount</td><td>bankaccount</td></tr><tr><td>eWallet</td><td>Lianlian、Pingpong</td></tr><tr><td rowspan="10"><b>Spain,  Ireland</b></td><td rowspan="3">payin</td><td rowspan="3">Buyers</td><td>CCDC</td><td>Visa、MasterCard、Amex、Cartesbancaires</td><td rowspan="10">Upcoming in October, no data yet</td></tr><tr><td>eWallet</td><td>Applepay、 GooglePay</td></tr><tr><td>BNPL</td><td>Klarna</td></tr><tr><td rowspan="7">payout</td><td>Local creators</td><td>bankaccount</td><td>bankaccount</td></tr><tr><td>Local Merchants/MCN/TAP</td><td>bankaccount</td><td>bankaccount</td></tr><tr><td rowspan="2">CN/HK POP Merchants</td><td>bankaccount</td><td>bankaccount</td></tr><tr><td>eWallet</td><td>Lianlian、Payoneer、Pingpong、Airwallex</td></tr><tr><td>CN/HK Full-service Merchants</td><td>eWallet</td><td>PIPOWALLET</td></tr><tr><td rowspan="2">CN/HK MCN/TAP</td><td>bankaccount</td><td>bankaccount</td></tr><tr><td>eWallet</td><td>Lianlian、Pingpong</td></tr></tbody></table>



### 特色场景|Distinctive features

2024.6.13支持US达人带货视频分发至UK，在UK产生交易后，达人可以获取佣金。目的是提升内容分发效率，提升UK GMV。目前商品来源为CN、HK商户商品。数据表现观察中。



流程：

1. GS运营选择可以在US和UK都可售卖的商品（这些商品来自CN、HK卖家，卖家在两国均有店铺），加入选品广场。
2. 达人选择可以支持多国售卖的商品，在短视频中添加商品，视频发布后在US和UK均会被推送。
3. US的买家点击商品链接，会进入商家US店铺进行下单，UK的买家点击商品链接，会进入商家UK店铺进行下单。达人可以收到卖家两国不同店铺产生的佣金。



> UK: On June 13, 2024, we support the distribution of US creators videos with product links to the UK. After transactions are generated in the UK, creators can receive commissions. It can improve content distribution efficiency and enhance UK GMV. At present, products are from CN and HK merchants. Tracking data performance.
> 
> Process:
> 
> 1. The operation team selects products that are supported for sale in both the US and UK (these products come from CN and HK merchants who have shops in both countries), and let creators add them.
> 2. Creators can choose products that can be sold in multiple countries, add products in short videos, and after the video is posted, it will be pushed in both the US and UK.
> 3. US buyers who click on the product link will enter the merchant's US shop to place an order, while UK buyers who click on the product link will enter the merchant's UK shop to place an order. Creators can receive commissions generated by different shops in the two countries.



<grid><column width-ratio="0.333333"><p>圈品、分发流程</p><blockquote><p>Product selection and distribution flow</p></blockquote><p></p><whiteboard token="HMgZwkJYEhbNt4b0CScluV1PguL"></whiteboard><p></p></column><column width-ratio="0.333333"><p>达人选品</p><blockquote><p>Creators add products</p></blockquote><figure view-type="Preview"><source name="飞书20240603-092911.mp4" mime="video/mp4" origin-height="1556.000000" origin-width="720.000000" size="93712564" token="ZtQGbp6OKooTuRxm7IAl9r3RgEf"/></figure></column><column width-ratio="0.333333"><p>达人佣金展示</p><blockquote><p>Commission fee display</p></blockquote><figure view-type="Preview"><source name="LR.mp4" mime="video/mp4" origin-height="1170.000000" origin-width="540.000000" size="20274770" token="VoRqblL9Uo57hqxuDtllJhTjgUf"/></figure></column></grid>



### 后续重点项目|Upcoming Key Projects

1. 支持美国达人带**英国本地商家**商品的视频分发至英国；一期复用待跨境商户货方案，ETA 7.31；二期为达人提供钱包能力，汇集各国佣金，与渠道沟通中；

   1. 美国达人带货（视频选择的货在美国店铺有售）的视频分发到英国，用户进入相似商品的店铺进行购买（目前没有美国商家在英国开店）
2. 接入Paypal：丰富支付方式，提升GMV；ETA 7月初
3. 接入多Payin通道：探索接入Stripe之外的Payin渠道，降低渠道成本；与渠道沟通中



> 1. Support distributing US creators' videos to the UK, promoting local merchants' products; The first phase is to reuse promoting cross-border merchants' goods solution with an ETA of 7.31; the second phase is to provide creators with wallet products, collecting commissions from various countries. Discussing with channels;
> 
>    1. After the video is distributed to the UK, US buyers who click on the product link will enter shops with similar products to make purchases (currently, there are no American merchants opening stores in the UK)
> 2. Support PayPal: Enriching payment methods and improving GMV; ETA early July
> 3. Support multiple Payin channels: Exploring Payin channels outside of Stripe to reduce channel costs; Discussing with channels



## 沙特**|SA**

### 服务模式**|Payment solution**

SA当前仅有跨境全托管模式和跨境自营电商Seitu，采用PIPO.SG自营模式。

> SA currently only has cross-border full-service merchants and Seitu, adopting PIPO SG self-managed solution

<grid>
<column width-ratio="0.500000">
**协议关系**
> Agreement 
</column>
<column width-ratio="0.500000">
**资金方案**
> Fund flow
</column>
</grid>

<grid><column width-ratio="0.500000"><whiteboard token="WRfswjMGVhcLg8b2y7Klw1ewgGc"></whiteboard></column><column width-ratio="0.500000"><whiteboard token="Q0tqwsqGEhV2oBbE0mxlpW0MgBb"></whiteboard></column></grid>

### **支付能力|Payment capabilities**

**Product capabilities**

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td colspan="2">Product</td><td>是否有应用 live or not</td></tr><tr><td colspan="2">入驻 onboarding</td><td>✅</td></tr><tr><td rowspan="7">收单<br/>collection</td><td>合单支付 shipping cart payment</td><td>✅</td></tr><tr><td>先绑后付 tokenisation payment</td><td>✅</td></tr><tr><td>支付营销 payment promotion</td><td>✅</td></tr><tr><td>组合支付 hybird payment</td><td>/</td></tr><tr><td>TikTok Paylater</td><td>/</td></tr><tr><td>One Click Pay</td><td>/</td></tr><tr><td>Express Checkout</td><td>/</td></tr><tr><td rowspan="3">退款<br/>refund</td><td>支持退款到原支付方式 Refund to the original payment method</td><td>✅</td></tr><tr><td>支持退款到 credit account Refund to credit</td><td>✅</td></tr><tr><td>支持退款转代发 Refund to payout</td><td>/</td></tr><tr><td colspan="2">分账 split</td><td>✅</td></tr><tr><td colspan="2">结算 settlement</td><td>✅</td></tr><tr><td colspan="2">平台打款/自主提现 disbursement</td><td>✅</td></tr><tr><td colspan="2">结汇 foreign exchange settlement</td><td>✅</td></tr><tr><td colspan="2">Bwallet</td><td>✅</td></tr></tbody></table>



**Payment Methods**

<table><colgroup><col/><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>Market</b></td><td><b>Payment Direction</b></td><td><b>Roles</b></td><td><b>Payment Type</b></td><td><b>Payment Method</b></td><td><b>Data Metrics</b></td></tr><tr><td rowspan="8">SA</td><td rowspan="4">payin</td><td rowspan="4">Buyers<br/>（Q2 user with successful payments：99,406）</td><td>CCDC</td><td>Visa、 MasterCard</td><td rowspan="4">91% of transactions are COD payments, 7% are CCDC, and the remaining are Apple Pay and Google Pay.<br/>At present, PIPO is working on reducing the proportion of COD together with the business side through BNPL offering, CCDC payment promotion, etc</td></tr><tr><td>eWallet</td><td>Applepay、 GooglePay</td></tr><tr><td>BNPL </td><td>Tabby</td></tr><tr><td>COD</td><td>COD</td></tr><tr><td rowspan="4">payout</td><td rowspan="2">Local creators</td><td>bankaccount</td><td>bankaccount</td><td rowspan="4"><img name="成功率 (2).png" mime="image/png" scale="1.000000" src="XUXDbob7Wo1CBPx5JABlTZoKgDc"/></td></tr><tr><td>eWallet</td><td>Paypal</td></tr><tr><td>Seitu</td><td>eWallet</td><td>Lianlian</td></tr><tr><td>CN/HK Full-service merchants</td><td>eWallet</td><td>PIPOWALLET</td></tr></tbody></table>



### 后续重点项目|Upcoming Key Projects

1. 7月底支持美国、英国带货视频分发至沙特，提升沙特GMV。
2. 降低Payin的COD占比。

> 1.  By the end of July, videos with product links from the United States and the United Kingdom can be distributed to Saudi Arabia, in order to enhance Saudi Arabia's GMV.
> 2. Lower the percentage of COD in payin



# 体验物料|Test materials

1. 买家：<cite doc-id="doccnYk5aN18SDSxAihFDf0y1yg" file-type="doc" title="电商流程体验入口" type="doc"></cite> 
2. 商家：<cite doc-id="shtcnmX0NWIhnbgVrWHHTTQ1Yob" file-type="sheets" sheet-id="05456b" title="东南亚账号资料" type="doc"></cite> 

   1. 本地商家网址： seller-us.tiktok.com（其它站点替换国家名称，如英国是seller-uk.tiktok.com） 
   2. 跨境POP模式商家站点: https://seller.tiktokglobalshop.com/
   3. 跨境全托管模式商家站点: https://mmo.fanczs.com/
3. 机构：

   1. 入驻地址：https://partner.tiktokshop.com/
   2. 测试物料：<cite doc-id="DKOKdsGfmo4Svex2jTAcHngZnWf" file-type="docx" title="Launch Review for US/UK/SEA agency affiliate match-making tool" type="doc"></cite>



<blockquote><ol><li seq="1">Buyer: <cite doc-id="doccnYk5aN18SDSxAihFDf0y1yg" file-type="doc" title="电商流程体验入口" type="doc"></cite></li><li seq="2">Merchants: <cite doc-id="shtcnmX0NWIhnbgVrWHHTTQ1Yob" file-type="sheets" sheet-id="05456b" title="东南亚账号资料" type="doc"></cite><ol><li seq="1">Local merchant website:  seller-us.tiktok.com (Replace country names for other sites, such as us -&gt; uk https://seller-uk.tiktok.com/（id、th、my、vn、ph、sg、sa）)</li><li>Cross-border POP merchant website: https://seller.tiktokglobalshop.com/</li><li>Cross border full-service merchant website: https://mmo.fanczs.com/</li></ol></li><li>Partners：<ol><li seq="1">Website:https://partner.tiktokshop.com/</li><li>Test material:<cite doc-id="DKOKdsGfmo4Svex2jTAcHngZnWf" file-type="docx" title="Launch Review for US/UK/SEA agency affiliate match-making tool" type="doc"></cite></li></ol></li></ol></blockquote>



# 文档

<table><colgroup><col/><col/></colgroup><tbody><tr><td>业务文档</td><td>商家入驻：https://www.tiktokshopglobalselling.com/zh-cn?target=seller<br/>商家商品发布：https://seller.tiktokglobalshop.com/university/essay?identity=1&amp;role=1&amp;knowledge_id=6837845927446273&amp;from=feature_guide<br/>商家使用联盟带货：https://seller.tiktokglobalshop.com/university/course?learning_id=7517882342885122&amp;role=1&amp;course_type=1&amp;from=search&amp;content_id=6837834707273473&amp;identity=1<br/>官方达人：https://seller.tiktokglobalshop.com/university/essay?knowledge_id=6837844107331329&amp;role=1&amp;course_type=1&amp;from=search&amp;identity=1<br/>渠道达人：https://seller.tiktokglobalshop.com/university/essay?knowledge_id=6837833055160065&amp;role=1&amp;course_type=1&amp;from=search&amp;identity=1<br/>机构入驻：https://seller.tiktokglobalshop.com/university/essay?identity=1&amp;role=2&amp;knowledge_id=2496344989255425&amp;from=feature_guide<br/>达人入驻：<cite doc-id="JqPpd6GiAoKId2xLbrVuHpzdskg" file-type="docx" title="PRD[Creator]Defer Payment Account Opening at Withdrawal Step (US Solution)" type="doc"></cite><br/>机构分类：https://partner.tiktokshop.com/docv2/page/64f1989064ed2e0295f3c1b5#Back%20To%20Top<br/><cite doc-id="FlLWdA7wdoPl1Gxzq3ncsPqTnsh" file-type="docx" title="【One-Pager】Partner (MCN &amp; TSP &amp; TAP) Product Domain Oncall FAQ_ Non-US" type="doc"></cite><br/>MCN创建计划：https://partner.tiktokshop.com/docv2/page/650a34b4f1fd3102b9206dbc#Back%20To%20Top<br/>团长创建计划：https://partner.tiktokshop.com/docv2/page/650a395adefece02be63046f#Back%20To%20Top</td></tr><tr><td>电商开国</td><td>US：<cite doc-id="doxcnvXYzDWymT6BmKRgx65sGKQ" file-type="docx" title="TTS US Local to Local TPM Product Solution" type="doc"></cite> <cite doc-id="CH66dkPcvoYuvhxMti4cqax5nkd" file-type="docx" title="【PIPO】TTS-US_Capricorn MOR Phase 1&amp;2+ Staged KYC Project Plans" type="doc"></cite><cite doc-id="GBXudui7GoC19kxK1j2cZ96hnIe" file-type="docx" title="[GPP Doc] TTS US Cross Border Project - Product Solution PRD" type="doc"></cite> <br/>SA：<cite doc-id="JxtmdgPFXovIe4x8aRzcjjUvnBA" file-type="docx" title="【PIPO】S[in TTS]-SA MVP Production Solution" type="doc"></cite><br/>GB：<cite doc-id="doccn8JiEKAWipuOdMlbWCR8G50" file-type="doc" title="【TT.UK 】UK Xborder E-commerce  Solution" type="doc"></cite> <cite doc-id="JMAPdrTStoHsNqxt8QKcl1pqnAe" file-type="docx" title="TTS UK跨境场景-Clover机房迁移&amp;PIPO主体迁移（PIPO HK到PIPO SG）" type="doc"></cite><br/>ES/IE/FR/DE/IT：<cite doc-id="VIEtdHV10oFnQDxCWTXlhktyg3d" file-type="docx" title="【TTS  EU - ES/IE/DE/FR/IT Local to Local &amp; Xborder】PIPO Product Solution" type="doc"></cite><br/>MX：<cite doc-id="D41PdSMFpoiywZxiNaTlVenKghc" file-type="docx" title="【TTS MX】New Country Launch For TTS MX" type="doc"></cite><br/>全托管：<cite doc-id="GI9gdjIa6oGS3Cxic9KcqDidnZe" file-type="docx" title="[S项目] 电商S - SA/UK/US平台模式改造Solution PRD" type="doc"></cite></td></tr><tr><td>产品能力</td><td><cite doc-id="DSXdd7ywXoCgunxHZ2ocRFoWnyb" file-type="docx" title="[PRD]TTS-US-Paypal 支付营销能力接入" type="doc"></cite><br/><cite doc-id="C8MydSFgNol3slx4YZKlJj1Egrd" file-type="docx" title="【2023 Q3】E-commerce - TTS VN - MoMo eWallet Bind and Pay" type="doc"></cite><br/><cite doc-id="EfxKdL3Qxo2GbCxBflXloyFrgFc" file-type="docx" title="[Test Design] Refund to Credit PH/MY/ID/KSA" type="doc"></cite><br/><cite doc-id="Gusywo8eOikWNlkB7jLcY2ccnU3" file-type="wiki" title="退款产品说明文档" type="doc"></cite><br/><cite doc-id="Af0ldUgTloSl7Xxopiyc6OE9nwc" file-type="docx" title="关退触达场景处理测试方案" type="doc"></cite><br/><cite doc-id="wikcnQ77tY36fBfTlRmBAyTOCne" file-type="wiki" title="跨境电商结汇入境-Payout部分" type="doc"></cite><br/><cite doc-id="JarOdMyckoPDbjxTOLRc5EFInmd" file-type="docx" title="[GPP Doc] Global Selling US/UK - OneClickPay - Product Solution PRD" type="doc"></cite><br/><cite doc-id="DhXDd0uxeo347BxXxNblHJQ0gDf" file-type="docx" title="Refund to Credit TH Launch Review" type="doc"></cite><br/><cite doc-id="CzBrwUVqeiqd7RklXLTceLcennh" file-type="wiki" title="Business Wallet - As a Start" type="doc"></cite><br/><cite doc-id="BD0OdP96voAaJ2xtcYelqWZlgug" file-type="docx" title="[GN PRD] Enable ApplePay Express Checkout" type="doc"></cite><br/><cite doc-id="F6AzdggtmoHRdaxMlEPcMLNFn0g" file-type="docx" title="[Trade] TTS US Project - Apple Pay Express Checkout" type="doc"></cite><br/><cite doc-id="A2iuddjZfoqRCAxvwbzca5i2nXe" file-type="docx" title="【PIPO】Express Apple Pay 技术文档" type="doc"></cite></td></tr><tr><td>TAP结算</td><td><cite doc-id="K0dRdS4HXoFIjWxk69pclrsnnlb" file-type="docx" title="TTS US&amp;UK 撮合机构业务支持-PIPO侧" type="doc"></cite></td></tr><tr><td>内容互通</td><td><cite doc-id="BHuEdvxMwodsGkxWKqvc65Lmnbg" file-type="docx" title="【一期】TTS US&amp;UK达人带货视频互通（带GS商户货）" type="doc"></cite><br/><cite doc-id="Jc6LdS0QAoVxkuxII6IlNgKvgZb" file-type="docx" title="【二期】TTS 达人带货视频互通（带GS商户货）" type="doc"></cite><br/><cite doc-id="R1RodIHMBoP8XoxGD2nlmSYsgWf" file-type="docx" title="GS短视频互通美—&gt;英LR" type="doc"></cite></td></tr><tr><td>保证金</td><td><cite doc-id="doxcnXNlxbKkiLRdvJ8Av7X9CNc" file-type="docx" title="TTS保证金payin交易及整体方案" type="doc"></cite><br/><cite doc-id="doxcn2LnTcKXfSYDunDezTFQusg" file-type="docx" title="[Payin] TTS保证金三期Payin整体方案" type="doc"></cite></td></tr><tr><td>仓储费</td><td><cite doc-id="wikcnTjjVQHy9A8AQWflKUetiFc" file-type="wiki" title="【7/8】E-commerce - TTS UK/US - In house Warehouse Service" type="doc"></cite><br/><cite doc-id="VfL1diAcPovDbTxdkOqcJmhYnrf" file-type="docx" title="协议扣款产品接入说明-For电商" type="doc"></cite><br/><cite doc-id="SZ3KdSODGoie5Hx0Hnslwy8XgJg" file-type="docx" title="【TTS UK】物流主体切换" type="doc"></cite><br/><cite doc-id="L1YTdZOP4oOnFcxNDR9lgV62gXd" file-type="docx" title="【TTS UK&amp;US】支持商家使用货款支付仓储费" type="doc"></cite></td></tr><tr><td>其它</td><td><cite doc-id="TF6vdB5MpoFXeHxdvYscqXuznTf" file-type="docx" title="Poject S的“前世今生”" type="doc"></cite><br/><cite doc-id="doccnsnO8AVX5OFuJCwCGwXSLFc" file-type="doc" title="【麦哲伦MVP】支付结算中台需求文档1.1" type="doc"></cite><br/><cite doc-id="Vi8ud0U4oo11hDxAB4IcLHB2nBc" file-type="docx" title="TTS All Regions - Customer Compensation - Payout - Local Currency" type="doc"></cite><br/><cite doc-id="TONJdDGixofLTsxGfTScp2Lrnrc" file-type="docx" title="UK&amp;US&amp;SG 消费者赔付" type="doc"></cite></td></tr></tbody></table>
