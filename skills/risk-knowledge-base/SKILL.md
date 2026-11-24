---
name: risk-knowledge-base
description: >-
  风控领域知识库。当任务涉及风控计划生成、风控指标计算与口径查询、风险标签/规则/业务线相关问题时使用。
  覆盖支付风控、交易黑标(TTS ROW V3/V4)、黑白标签定义与 False Positive 分析、
  电商/直播(TikTok Live)/Local Service 业务线、3DS2.0、CheckPoint、国际支付账号体系、智能规则优化等。
  提供权威指标口径(拦截率/欺诈资损率/净资损率/ATO Rate 等，含完整 SQL)。
  不适用于 BNPL 规则集生成(走 bnpl-rule-set-generator)。
---

# 风控知识库检索指南

本知识库由飞书「风控领域知识库」索引页(docx: RaEsd9K5Hop2Gjx7rSOlUJlQgyf)下的分类文档抓取转换而来，采用 Anthropic Agent Skills 渐进式披露 + Karpathy LLM Wiki 持续编译式范式。**所有指标口径以源文档原文为准，不得臆造。**

## 何时使用
- 生成风控相关计划、方案（计划中凡涉及指标/规则，点名其来源文档）。
- 计算或核对风控指标、查询指标口径定义。
- 查询风险类型、黑白标签定义、规则策略、业务线背景。

## 会话开始必做（orientation）
1. 读 `_global/constraints.md` 了解问题类型判断、可信规则与输出纪律（作答前提）。
2. 读 `SCHEMA.md` 了解 10 类目定义与 tags 受控词表。
3. 读 `index.md` 了解现有文档及一句话摘要。

## 检索与作答流程
1. 判断问题类型（口径查询 / 计划生成 / 归因 / 复盘），依据 `_global/constraints.md`。
2. 从任务中抽取：**类目 / 指标名 / 业务线 / 关键词**。
3. 读 `manifest.json`，按 `category` / `metrics` / `business_lines` / `tags` 过滤命中文档（无需逐个打开 MD）。
4. 打开命中 MD，优先读「关键指标口径」「规则 / 策略要点」节；口径细节与完整 SQL 在「原文正文」节。
5. **输出（严格遵守 `_global/constraints.md` 的输出纪律）**：结论 + 证据（引用到具体 MD 与 `source_url`）+ 下一步 + 口径说明（本次采用的指标定义 / 时间窗 / 过滤条件；若用默认值须提示可能与预期不符）。
   - 引用格式：`来源：<类目>/<文件名>.md（source_url: <链接>）`。
   - KB 是参考不是答案：与问题不符要显式指出；KB 未覆盖如实声明并回退推理，禁止硬套。

## 指标口径入口（最常用）
- 支付风控核心指标（拦截率 / 欺诈资损率 / 欺诈净资损率 / ATO Rate 等，含完整 SQL）：`01_风控总览/PIPO支付风控核心指标口径OnePager.md`。
- 口径**严格以该文原文为准**，注意 ROW / EU / US 分区差异、分子按报回日/分母按交易日，禁止自行估算。

## 注意（防幻觉）
- 引用知识时必须标注来源 MD 与 `source_url`，不得臆造口径、阈值、规则。
- 源文档未提供的字段/口径如实说明「源文档未提供」，不要编造。
- 内嵌图表(`<sheet>`/`<whiteboard>`/`<img>`)未离线化，仅保留引用，图表内容不可见。
- BNPL 规则集生成不在本库范围，走 `bnpl-rule-set-generator`。
