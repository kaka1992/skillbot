---
name: stock-data-fetch
description: |
  当用户要求查询股票实时行情、历史K线数据或技术指标时使用本技能。

  支持市场：
  - A 股：6 位数字代码，如 600519、000001
  - 港股：HK 前缀 + 5 位数字，如 HK00700
  - 美股：1-5 位大写字母，如 AAPL、TSLA

  本技能只负责获取真实市场数据并计算技术指标（MA、MACD、RSI、成交量、乖离率），
  不提供买卖建议，不进行基本面分析。

  触发词示例：行情、股价、K线、技术指标、走势、涨跌、最近表现、数据抓取

  不应触发：买卖建议、投资推荐、公司财报分析、没有明确股票代码的泛泛讨论
---

# Stock Data Fetch Skill

你是一位专业的股票数据获取工具，通过 Python 脚本获取真实市场数据，并计算技术指标（MA/MACD/RSI/量能/乖离率）等，并将数据存到到指定路径。

**核心原则**：不调用外部 LLM。Python 脚本只负责"取数据 + 算指标"，你负责存储数据到指定目录，并告诉用户文件路径，不要读取文件。

## 工作流

```
用户输入（股票代码/名称）与分析日期范围
[STEP 1] 解析输入 → 识别市场、标准化代码+日期范围
[STEP 2] 运行 Python 数据脚本
      │   执行 references/stock_data_fetcher.py
[STEP 3] print输出文件名称
      │   ls ${WORK_DIR}/data
```

## STEP 1: 解析输入

### 股票代码识别规则

| 格式 | 市场 | 示例 | 数据源 |
|------|------|------|--------|
| 6位数字 (6/0/3开头) | A股 | 600519, 000001, 300750 | akshare |
| HK + 5位数字 | 港股 | HK00700, HK09988 | akshare |
| 1-5位大写字母 | 美股 | AAPL, TSLA, PLTR | yfinance |
**处理逻辑**
- 多只股票用逗号、空格或换行分隔
- 如果用户输入中文公司名（如"贵州茅台"），先用 WebSearch 查找对应股票代码
- 去除可能的后缀（.SH/.SZ/.SS）或前缀（SH/SZ）

### 日期范围识别规则
**处理逻辑**
- 格式：YYYY-MM-DD
- 示例：start-date 2026-01-01, end-date 2026-05-01

## 工作目录

根据当前 agent 平台自动确定工作目录（写入 agent 的 workspace 内，避免使用 `/tmp` 以免跨 thread 污染）：

```bash
# deer-flow  sandbox 内 → /mnt/user-data/workspace/stock
# nanobot             → ~/.nanobot/workspace/stock
# hermes-agent local  → ./stock  (terminal.cwd)
# 默认兜底 (CLI 测试)   → /tmp/stock

if [ -d "/mnt/user-data/workspace" ]; then
    WORK_DIR="/mnt/user-data/workspace/stock"          # deer-flow sandbox
elif [ -d "$HOME/.nanobot/workspace" ]; then
    WORK_DIR="$HOME/.nanobot/workspace/stock"          # nanobot
else
    WORK_DIR="/tmp/stock"                              # CLI / unknown agent
fi
```

## STEP 2: 运行数据脚本

1. 清理并创建输出目录：
```bash
if [ -d "${WORK_DIR}/data" ]; then find "${WORK_DIR}/data" -mindepth 1 -delete; fi
mkdir -p "${WORK_DIR}/data"
```

2. 确保 ${WORK_DIR} 的 uv 虚拟环境就绪（已存在则仅验证依赖）：
```bash
cd "${WORK_DIR}"
# 如果 .venv 不存在则创建
if [ ! -d ".venv" ]; then
    uv venv
fi
# 验证依赖是否已安装，缺失则补装
source .venv/bin/activate
uv pip install -r <SKILL_DIR>/references/requirements.txt --quiet
```

3. 初始化环境变量（TUSHARE_TOKEN 等）：
```bash
source <SKILL_DIR>/references/.env 2>/dev/null || true
```

4. 使用 uv 环境执行数据抓取（CSV 模式）：

```bash
# 默认 120 个交易日
"${WORK_DIR}/.venv/bin/python3" <SKILL_DIR>/references/stock_data_fetcher.py \
  --stocks "CODE1,CODE2,CODE3" --output csv --output-dir "${WORK_DIR}/data"

# 指定交易天数
"${WORK_DIR}/.venv/bin/python3" <SKILL_DIR>/references/stock_data_fetcher.py \
  --stocks "CODE1,CODE2,CODE3" --days 60 --output csv --output-dir "${WORK_DIR}/data"

# 指定日期范围（优先于 --days）
"${WORK_DIR}/.venv/bin/python3" <SKILL_DIR>/references/stock_data_fetcher.py \
  --stocks "CODE1,CODE2,CODE3" --start-date 2026-01-01 --end-date 2026-05-01 --output csv --output-dir "${WORK_DIR}/data"
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--stocks` | 必填 | 逗号分隔的股票代码 |
| `--days` | 120 | 历史交易日数量 |
| `--start-date` | — | 起始日期 YYYY-MM-DD（设置后 `--days` 失效） |
| `--end-date` | 今天 | 结束日期 YYYY-MM-DD |
| `--output` | stderr | stderr / csv |
| `--output-dir` | ./output | CSV 输出目录 |


## Step3 print输出文件名称
```bash
ls ${WORK_DIR}/data
```
- `${WORK_DIR}/data/{CODE}_ohlcv.csv` — OHLCV 历史数据
- `${WORK_DIR}/data/analysis_summary.csv` — 技术指标汇总
- `${WORK_DIR}/data/run.log` — 运行日志


## 错误处理

| 场景 | 处理方式                                 |
|------|--------------------------------------|
| 股票代码无法识别 | 提示用户正确格式，给出示例                        |
| Python 依赖缺失 | 执行python install -r requirements.txt |
| 某只股票数据获取失败 | 跳过并提示，继续分析其他股票                       |
| 市场休市/无数据 | 使用最近交易日数据                            |
| 脚本执行超时 | 设置 120s 超时，超时则报告已获取的部分结果             |

## 注意事项

- 脚本支持**分级降级策略**，零配置即可运行，配置 API Key 后数据更精准：

| 环境变量 | 用途 | 获取方式 | 免费额度 |
|----------|------|----------|----------|
| `TUSHARE_TOKEN` | A股专业数据（优先级最高） | [tushare.pro](https://tushare.pro) 注册 | 基础接口免费 |
- 行情数据降级链：
  - A股: Tushare Pro → efinance → akshare → yfinance
  - 港股: efinance → akshare → yfinance
  - 美股: yfinance（主力）
- 所有价格数据来自真实市场（akshare/yfinance），不是编造的
- 技术指标由 Python 精确计算，不要手动估算
- 中文输出，价格用原始货币单位（A股=人民币，美股=美元，港股=港币）