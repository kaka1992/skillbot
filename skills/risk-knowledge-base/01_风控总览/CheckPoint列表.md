---
title: CheckPoint列表
category: 风控总览
source_url: https://bytedance.sg.larkoffice.com/wiki/NCnrwffXLiuObhkXU3jcw5oln2e
source_token: NCnrwffXLiuObhkXU3jcw5oln2e
source_type: wiki
doc_type: 其他
tags: [CheckPoint, 支付风控, 交易风控, 账号安全, 电商, 直播]
metrics: []
business_lines: [电商, 直播]
summary: 汇总 PIPO 各业务场景的风控 CheckPoint 点位、事件与上游服务
last_synced: 2026-08-12
---

## 适用场景
需要查询某业务流程接入了哪些风控点位（CheckPoint）、点位对应的事件名及上游服务时参考。适用于风控点位接入梳理、事件映射对齐、上游调用排查，以及判断某场景（绑卡/支付/提现/退款/IAP/KYC/BNPL/钱包/营销/卡包/商户入驻）的风控卡点分布。注：Notify 异步事件未纳入本文，需另查「异步事件汇总」等文档。

## 核心概念
- 点位（CheckPoint）：风控在业务流程中的卡点，每个点位对应「点位名称 / 事件列表 / 预期收敛后目标事件 / 上游服务」。
- 通用业务场景：卡管理（绑卡 enter_card_request/bind_request、解绑 unbind_request、换绑 rebind_request、验卡 card_verify_request）、支付（payin：preorder/submit_order/pay_option/payment/channel/post_auth request；COD submit_order_request）、提现（payout：preorder/pi_check/pi_filter/submit_order/withdraw_sync/withdraw request 等）、退款（pin_settings_need_request、refund_request）、IAP（payment/receipt_verify/refund request）、KYC（kyc_risk_request）。
- BNPL：贷前（credit_preaccess_whitenamelist、credituse_cashierpre_request、pre_credit_given_request、fi_routing_request、credit_given_request）、贷中（credituse_cashierpre_request，其余复用 payin）、贷后（复用 payin_non_bankcard_request）。
- 钱包：开通钱包/余额户、自动提现、密码设置、PIN 设置、手机号设置、发送验证码等点位（B 端钱包=电商，C 端钱包=TT Live）。
- 商业化营销：GMV 转投广告（transfer_set/transfer_close request）、优惠券发放（promo_calculate/display/receive/settle request）、营销账号升级 Ads（pi_copy_request）。
- 卡包（PI Clip）：绑卡（pre_bind_verify_request）、设置默认 PI（set_primary_pi_request）。
- 电商：商户入驻（merchant_settlement_request）。

## 关键指标口径
（本文无指标口径）

## 规则 / 策略要点
- 事件收敛策略：多个历史事件名（如 payin_bind_request/payout_bind_request 等）计划收敛为统一的「预期收敛后目标事件」（如 bind_request）。
- 下单风控点位（submit_order_request）与 COD 使用同一点位。
- BNPL 贷中/贷后大量复用 payin 相同事件（payin+refund）。
- 本文以点位/事件目录为主，未给出具体阈值或判断逻辑。

## 原文正文

<!-- source_type: wiki | doc_id: NCnrwffXLiuObhkXU3jcw5oln2e | title: CheckPoint列表 -->

<title>CheckPoint列表 </title>

<callout emoji="💡"><p>Notify事件并没有体现在下列总结中，可以查看一下文档查看</p><p><cite doc-id="K8OywkjILiLQYmkKfF3cjcNNnLb" file-type="wiki" title="异步事件汇总" type="doc"></cite></p><p><cite doc-id="PJ4vskqsYhMVjet8WyolxvZEgof" file-type="sheets" sheet-id="467b57" title="notify_request_map" type="doc"></cite></p><p><cite doc-id="I1xFsAm7yhKfRntLhbylu2zWglQ" file-type="sheets" sheet-id="JHeeH4" title="checkpoint 接入情况分析" type="doc"></cite></p></callout>

# 上游调用概览

<whiteboard token="VLvww7QWFhoXPjb5qjelT09VgM1"></whiteboard>

# 通用业务

## 场景：卡管理

### 流程

<whiteboard token="KBgMwEXc1hNJBQbjNP8l8xRwg5d"></whiteboard>

### 点位总结

<table><colgroup><col/><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>流程</b></td><td><b>点位名称</b></td><td><b>事件列表</b></td><td><b>预期收敛后目标事件</b></td><td>Latency pct99</td><td><b>上游服务</b></td></tr><tr><td rowspan="2" vertical-align="middle">绑卡</td><td>填充卡号后风险校验<br/>enter_card_request</td><td>enter_card_request</td><td>enter_card_request</td><td></td><td>pipo.solution.monetization</td></tr><tr><td>绑定支付工具<br/>bind_request</td><td>payin_bind_request<br/>payout_bind_request<br/>bind_request<br/>payout_cross_border_bind<br/>payout_bind（合规）<br/>bankcard_verification_request（合规）</td><td>bind_request</td><td></td><td>pipo.trade.authen<br/>pipo.instrument.authen<br/>pipo.cashier.withdraw</td></tr><tr><td vertical-align="middle">解绑</td><td>解绑支付工具<br/>unbind_request</td><td>payout_unbind_request</td><td>unbind_request</td><td></td><td>pipo.cashier.withdraw<br/>pipo.trade.authen</td></tr><tr><td vertical-align="middle">换绑</td><td>换绑支付工具<br/>rebind_request</td><td>payout_rebind_request</td><td>rebind_request</td><td></td><td>pipo.instrument.authen</td></tr><tr><td vertical-align="middle">验卡</td><td>验卡<br/>card_verify_request</td><td>micro_deposit_verification_request</td><td>micro_deposit_verification_request</td><td></td><td>pipo.order.withdraw</td></tr></tbody></table>

### 交互示例payout_withdraw_sync_request

<table><colgroup><col/><col/><col/><col/><col/><col/></colgroup><tbody><tr><td>开始</td><td>填充卡号后风险校验<br/>enter_card_request</td><td>绑定支付工具<br/>bind_request</td><td>解绑支付工具<br/>unbind_request</td><td>换绑支付工具<br/>rebind_request</td><td>验卡<br/>card_verify_request</td></tr><tr><td><img name="image.png" mime="image/png" scale="1.000000" src="Rn88bSyZcoWnVZxkOlRlVGX6grd"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="ZgoqbfyaOobZ6pxekjJlB2uSg4c"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="UUXabmX4FoVtyNxmHLElQhKHgLf"/></td><td><img name="image.png" mime="image/png" scale="1.000000" src="YzJ9bRKt7oNyApxGx8GlMc05gjf"/></td><td></td><td></td></tr></tbody></table>

## 场景：支付

### 流程

<synced-source><whiteboard token="DeChwybzwhNOYEbrW9hlAFXJgw8"></whiteboard></synced-source>

### 点位总结

<table><colgroup><col/><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>流程</b></td><td><b>点位名称</b></td><td><b>事件列表</b></td><td><b>预期收敛后目标事件</b></td><td><b>上游服务</b></td><td></td></tr><tr><td rowspan="6">payin</td><td>预下单<br/>preorder_request</td><td>payin_preorder_request</td><td>preorder_request</td><td></td><td></td></tr><tr><td>下单风控(和COD是同样的点位)<br/>submit_order_request</td><td>payin_order_request</td><td>submit_order_request</td><td>pipo.trade.core</td><td></td></tr><tr><td>获取支付方式列表<br/>pay_option_request</td><td>pay_option_request</td><td>pay_option_request</td><td>pipo.cashier.payment_decision</td><td></td></tr><tr><td>支付请求<br/>payment_request</td><td>payin_non_bankcard_request<br/>payin_bankcard_request<br/>payin_bankcard_bind_pay_request<br/>payin_non_bankcard_bind_pay_request</td><td>payment_request</td><td>pipo.gn.pay_core<br/>pipo.trade.instant_payment<br/>pipo.trade.transfer_core</td><td></td></tr><tr><td>请求渠道<br/>channel_request</td><td>payin_paypal_single_request</td><td>payin_paypal_single_request</td><td>pipo.channel.paypal_api<br/>pipo.channel.callback_api</td><td></td></tr><tr><td>渠道完成事后风控<br/>post_auth_request</td><td>post_auth_request</td><td>post_auth_request</td><td>pipo.gn.pay_core<br/>pipo.trade.instant_payment</td><td></td></tr><tr><td vertical-align="middle">COD</td><td>COD提交订单（合规）<br/>submit_order_request</td><td>payin_submit_order_request</td><td>submit_order_request</td><td>pipo.gateway.api<br/>（oec.trade.async_process_consumer）</td><td><cite doc-id="BUzPdHTKqofbGqxXxXacp4XnnSb" file-type="docx" title="「Tech design」电商COD场景接入合规制裁扫描" type="doc"></cite></td></tr></tbody></table>

## 场景：提现

### 流程

<whiteboard token="Z7Dkw8R8ihqstkb3HpdlFkVVgQh"></whiteboard>

### 点位总结

<table><colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>流程</b></td><td><b>点位名称</b></td><td><b>事件列表</b></td><td><b>预期收敛后目标事件</b></td><td><b>上游服务</b></td></tr><tr><td rowspan="7" vertical-align="middle">payout</td><td>预下单<br/>preorder_request</td><td>payout_preorder_request</td><td>preorder_request</td><td>pipo.trade.core</td></tr><tr><td>核身验证检查（即将废弃)<br/>validate_center_decision</td><td>validate_center_decision</td><td>validate_center_decision</td><td>pipo.cashier.withdraw</td></tr><tr><td>检查PI是否可用<br/><b>pi_check_request</b></td><td><b>payout_pi_check_request</b></td><td><b>pi_check_request</b></td><td>pipo.cashier.payment_decision</td></tr><tr><td>获取可提现的pi列表<br/><b>pi_filter_request</b></td><td><b>payout_pi_filter_request</b></td><td><b>pi_filter_request</b></td><td>pipo.cashier.payment_decision</td></tr><tr><td>创建提现单<br/>submit_order_request</td><td>payout_order_request</td><td>submit_order_request</td><td>pipo.order.withdraw</td></tr><tr><td>确认提现<br/>withdraw_sync_request</td><td>payout_withdraw_sync_request<br/>payout_withdraw（合规）<br/>payout_cross_border_withdraw（合规）</td><td>withdraw_sync_request</td><td>pipo.order.withdraw<br/>pipo.cashier.withdraw</td></tr><tr><td>异步出款<br/>withdraw_request</td><td>payout_withdraw_request</td><td>withdraw_request</td><td>pipo.order.withdraw</td></tr></tbody></table>

## 场景：退款

### 流程

<whiteboard token="Nxq3w9Co4hnatKbri8GlM4Nxg7f"></whiteboard>

### 点位总结

<table><colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>流程</b></td><td><b>点位名称</b></td><td><b>事件列表</b></td><td><b>预期收敛后目标事件</b></td><td><b>上游服务</b></td></tr><tr><td rowspan="2" vertical-align="middle">退款</td><td>是否需要设置PIN<br/>pin_settings_need_request</td><td>pin_settings_need_request</td><td>pin_settings_need_request</td><td>pipo.wallet.userprod</td></tr><tr><td>退款请求<br/>refund_request</td><td>refund_request<br/>refund_request_payout_withdraw<br/>payin_refund_request</td><td>refund_request</td><td>pipo.gn.pay_core</td></tr></tbody></table>

## 场景：IAP

### 流程

<whiteboard token="Z0f9wsakDhbLjCbdXPBlg8S6g5e"></whiteboard>

### 点位总结

<table><colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>流程</b></td><td><b>点位名称</b></td><td><b>事件列表</b></td><td><b>预期收敛后目标事件</b></td><td><b>上游服务</b></td></tr><tr><td rowspan="2" vertical-align="middle">IAP支付</td><td>创单<br/>payment_request</td><td>IAP_payment_request<br/>IAP_payement_2.0</td><td>payment_request</td><td>pipo.trade.iap<br/>pipo.subscription.trade<br/>pipo.solution.game_iap<br/>pipo.gateway.api(直播、Gaming等）</td></tr><tr><td>验票<br/>receipt_verify_request</td><td>IAP_receipt_verify_request</td><td>receipt_verify_request</td><td>pipo.solution.iap_oneoff<br/>pipo.subscription.trade</td></tr><tr><td vertical-align="middle">IAP退款</td><td>退款请求<br/>refund_request</td><td>IAP_refund_request</td><td>refund_request</td><td>pipo.gn.pay_core</td></tr></tbody></table>



## 场景：KYC

### 流程

<whiteboard token="HYkhwNdVRhBR17bYPfSl8l56gvf"></whiteboard>

### 点位总结

| **流程** | **点位名称** | **事件列表** | **上游服务** |
|-|-|-|-|
| kyc_risk | kyc_risk_request | kyc_risk_request | pipo.compliance.kyc_decision |



# BNPL

## 场景：贷前

### 流程

<whiteboard token="MLHww6tsSh9iFub3i0xlBi5tgkc"></whiteboard>

### 点位总结

<table><colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>流程</b></td><td><b>点位名称</b></td><td><b>事件列表</b></td><td><b>预期收敛后目标事件</b></td><td><b>上游服务</b></td></tr><tr><td rowspan="5" vertical-align="middle">贷前</td><td>增加BNPL准入名单<br/>credit_preaccess_whitenamelist</td><td>credit_preaccess_whitenamelist</td><td>credit_preaccess_whitenamelist</td><td>pipo.credit.prod</td></tr><tr><td>开通PA<br/>credituse_cashierpre_request</td><td>credituse_cashierpre_request</td><td>credituse_cashierpre_request</td><td>pipo.credit.core</td></tr><tr><td>极简授信检查<br/>pre_credit_given_request</td><td>pre_credit_given_request</td><td>pre_credit_given_request</td><td>pipo.credit.prod</td></tr><tr><td>获取FI机构<br/>fi_routing_request</td><td>fi_routing_request</td><td>fi_routing_request</td><td>pipo.credit.prod</td></tr><tr><td>请求开通BNPL<br/>credit_given_request</td><td>credit_given_request</td><td>credit_given_request</td><td>pipo.credit.prod</td></tr></tbody></table>

## 场景：贷中

### 流程

<whiteboard token="QxtzwRYdjh5CjbbuHc9l03rHgWb"></whiteboard>

### 点位总结

<table><colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>流程</b></td><td><b>点位名称</b></td><td><b>事件列表</b></td><td><b>预期收敛后目标事件</b></td><td><b>上游服务</b></td></tr><tr><td vertical-align="middle">贷中</td><td>BNPL可用性检查<br/>credituse_cashierpre_request</td><td>credituse_cashierpre_request</td><td>credituse_cashierpre_request</td><td>pipo.credit.prod</td></tr><tr><td colspan="5">其他走payin的相同事件（payin+refund)</td></tr></tbody></table>

## 场景：贷后

### 流程

<whiteboard token="E8xew6OcWhnnKybxcMLl6EZfgNe"></whiteboard>

### 点位总结

<table><colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>流程</b></td><td><b>点位名称</b></td><td><b>事件列表</b></td><td><b>预期收敛后目标事件</b></td><td><b>上游服务</b></td></tr><tr><td colspan="5">走payin的相同事件（payin_non_bankcard_request）</td></tr></tbody></table>

# 钱包

## 场景： 钱包设置

>  B端钱包：电商
> 
> C端钱包：TT Live

### **流程：**

<whiteboard token="VRT9wb43uhs3GQbrmDBlOxzug0c"></whiteboard>

### 点位总结

<table><colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>流程</b></td><td><b>点位名称</b></td><td><b>事件列表</b></td><td><b>预期收敛后目标事件</b></td><td><b>上游服务</b></td></tr><tr><td rowspan="3" vertical-align="middle"><b>开通钱包</b></td><td>注册钱包<br/>register_walletacct_request</td><td>register_walletacct_request</td><td>register_walletacct_request</td><td>pipo.wallet.userprod</td></tr><tr><td>允许pi融合的pi列表<br/>businesswallet_pimerge_request</td><td>businesswallet_pimerge_request</td><td>businesswallet_pimerge_request</td><td>pipo.solution.walletprod</td></tr><tr><td>账户融合<br/>wallet_account_link_request</td><td>wallet_account_link_request</td><td>wallet_account_link_request</td><td>pipo.wallet.userprod<br/>pipo.solution.walletprod</td></tr><tr><td vertical-align="middle"><b>开通余额户</b></td><td>开通余额户<br/>register_businesswallet_request</td><td>register_businesswallet_request</td><td>register_businesswallet_request</td><td>pipo.wallet.userprod</td></tr><tr><td vertical-align="middle"><b>开启自动提现</b></td><td>开启自动提现<br/>auto_withdraw_set_request</td><td>auto_withdraw_set_request</td><td>auto_withdraw_set_request</td><td>pipo.solution.walletprod</td></tr><tr><td rowspan="2" vertical-align="middle"><b>密码设置</b></td><td>设置密码<br/>wallet_change_payment_password_request</td><td>wallet_change_payment_password_request</td><td>wallet_change_payment_password_request</td><td>pipo.wallet.userprod</td></tr><tr><td>忘记密码<br/>wallet_forget_payment_password_request</td><td>wallet_forget_payment_password_request</td><td>wallet_forget_payment_password_request</td><td>pipo.wallet.userprod</td></tr><tr><td rowspan="2" vertical-align="middle"><b>PIN设置</b></td><td>设置PIN<br/>verification_change_pin_request</td><td>verification_change_pin_request</td><td>verification_change_pin_request</td><td>pipo.wallet.userprod</td></tr><tr><td>忘记PIN检查<br/>verification_forget_pin_request</td><td>verification_forget_pin_request</td><td>verification_forget_pin_request</td><td>pipo.wallet.userprod</td></tr><tr><td rowspan="2" vertical-align="middle"><b>手机号设置</b></td><td>设置手机号<br/>verification_change_phone_no_request</td><td>verification_change_phone_no_request</td><td>verification_change_phone_no_request</td><td>N/A</td></tr><tr><td>忘记手机号<br/>verification_forget_phone_no_request</td><td>verification_forget_phone_no_request</td><td>verification_forget_phone_no_request</td><td>N/A</td></tr><tr><td rowspan="2" vertical-align="middle"><b>发送验证码</b></td><td>直连场景发验证码请求<br/>otp_trigger_precheck_request</td><td>otp_trigger_precheck_request</td><td>otp_trigger_precheck_request</td><td>N/A</td></tr><tr><td>开户断点恢复<br/>register_bp_check_request</td><td>register_bp_check_request</td><td>register_bp_check_request</td><td>N/A</td></tr></tbody></table>

### 交互示例

| 注册钱包  <br/>register_walletacct_request | 允许pi融合的pi列表  <br/>businesswallet_pimerge_request | 账户融合  <br/>wallet_account_link_request | 开通余额户  <br/>register_businesswallet_request | 开启自动提现  <br/>auto_withdraw_set_request | 设置密码  <br/>wallet_change_payment_password_request | 忘记密码  <br/>wallet_forget_payment_password_request | 设置PIN  <br/>verification_change_pin_request | 忘记PIN检查  <br/>verification_forget_pin_request | 设置手机号  <br/>verification_change_phone_no_request | 忘记手机号  <br/>verification_forget_phone_no_request | 直连场景发验证码请求  <br/>otp_trigger_precheck_request | 开户断点恢复  <br/>register_bp_check_request |
|-|-|-|-|-|-|-|-|-|-|-|-|-|
|  |  |  |  |  |  |  |  |  |  |  |  |  |

# 商业化、营销

## 场景：GMV转投广告

### **流程：**

<whiteboard token="LMGDw0JCFhj0ZpbnUWMlqXoLgsd"></whiteboard>

### 点位总结

<table><colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>流程</b></td><td><b>点位名称</b></td><td><b>事件列表</b></td><td><b>预期收敛后目标事件</b></td><td><b>上游服务</b></td></tr><tr><td rowspan="2" vertical-align="middle">GMV管理</td><td>GMV设置<br/>transfer_set_request</td><td>transfer_set_request</td><td>transfer_set_request</td><td>pipo.gateway.api</td></tr><tr><td>解绑GMV<br/>transfer_close_request</td><td>transfer_close_request</td><td>transfer_close_request</td><td>pipo.gateway.api</td></tr></tbody></table>

## 场景：优惠券发放

### **流程：**

<whiteboard token="EDYPwbc7WhO9k1be40UlA9qkgXf"></whiteboard>

### 点位总结

<table><colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>流程</b></td><td><b>点位名称</b></td><td><b>事件列表</b></td><td><b>预期收敛后目标事件</b></td><td><b>上游服务</b></td></tr><tr><td rowspan="4">优惠券发放</td><td>营销算法随机折扣算价<br/>promo_calculate_request</td><td>promo_calculate_request</td><td>promo_calculate_request</td><td>pipo.marketing.strategy</td></tr><tr><td>营销活动显示风控<br/>promo_display_request</td><td>promo_display_request</td><td>promo_display_request</td><td>pipo.marketing.coupon</td></tr><tr><td>领券风控<br/>promo_receive_request</td><td>promo_receive_request</td><td>promo_receive_request</td><td>pipo.marketing.coupon</td></tr><tr><td>营销资产核销<br/>promo_settle_request</td><td>promo_settle_request</td><td>promo_settle_request</td><td></td></tr></tbody></table>

## 场景：营销账号升级为Ads账号

### **流程：**

<whiteboard token="VtLiwZsqWhh2fGbqxfYl790Tgrh"></whiteboard>

### 点位总结

| **流程** | **点位名称** | **事件列表** | **预期收敛后目标事件** | **上游服务** |
|-|-|-|-|-|
| 营销账号升级为Ads账号 | 复制PI  <br/>pi_copy_request | pi_copy_request | pi_copy_request | pipo.solution.core |

# 卡包（PI Clip）

## 场景：绑卡

### **流程：**

<whiteboard token="LfOzw6hA2hNJgNbTdyhlCUiZgae"></whiteboard>

### 点位总结

<table><colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr><td><b>流程</b></td><td><b>点位名称</b></td><td><b>事件列表</b></td><td><b>预期收敛后目标事件</b></td><td><b>上游服务</b></td></tr><tr><td vertical-align="middle">绑卡</td><td>查询可绑支付方式列表<br/>pre_bind_verify_request</td><td>pre_bind_verify_request</td><td>pre_bind_verify_request</td><td>pipo.trade.authen</td></tr><tr><td vertical-align="middle">设置默认PI</td><td>设置默认PI<br/>用户选定要设置的PI时请求风控<br/><cite doc-id="ZIOUdu0d8oaJF3xkYzpldDisgle" file-type="docx" title="[solution]payout新增风险管控节点产品方案" type="doc"></cite></td><td>set_primary_pi_request</td><td>set_primary_pi_request</td><td>pipo.user.center</td></tr></tbody></table>

# 电商

## 商户入驻

### **流程：**

<whiteboard token="T24rwv5PkhrnwObRD2alegE7glf"></whiteboard>

### 点位总结

| **流程** | **点位名称** | **事件列表** | **预期收敛后目标事件** | **上游服务** |
|-|-|-|-|-|
| 商户入驻 | 商户入驻  <br/>merchant_settlement_request | merchant_settlement_request | merchant_settlement_request |  |
