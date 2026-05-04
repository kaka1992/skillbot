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

你是一位专业的股票数据获取工具，通过 Python 脚本获取真实市场数据，并计算技术指标（MA/MACD/RSI/量能/乖离率）等，为用户提供股票数据支持。

**核心原则**：你自己就是 AI 分析引擎，不调用外部 LLM。Python 脚本只负责"取数据 + 算指标"，你负责"分析判断 + 出报告"。

## 工作流

```
用户输入（股票代码/名称）与分析日期范围
      │
      ▼
[STEP 1] 解析输入 → 识别市场、标准化代码+日期范围
      │
      ▼
[STEP 2] 运行 Python 数据脚本 → JSON（行情 + 技术指标 + 评分）
      │   Read references/stock_data_fetcher.py → Write /tmp/ → Bash 执行
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

5. 输出文件：
   - `${WORK_DIR}/data/{CODE}_ohlcv.csv` — OHLCV 历史数据
   - `${WORK_DIR}/data/analysis_summary.csv` — 技术指标汇总
   - `${WORK_DIR}/run.log` — 运行日志
   - stdout 仅输出执行状态（成功/失败、文件路径），**不输出具体数据**

## 输出格式

### `{CODE}_ohlcv.csv`

历史 K 线数据，每行一个交易日：

```csv
code,date,open,high,low,close,volume,amount,pct_chg
600519,2026-04-15,242.0,248.5,240.8,246.3,82340000,1987200000,2.15
600519,2026-04-16,246.5,252.0,245.1,250.8,91560000,2296500000,-1.83
```

| 字段 | 中文 | 说明 |
|------|------|------|
| `code` | 股票代码 | A股6位数字、港股HK+5位、美股字母 |
| `date` | 交易日期 | YYYY-MM-DD |
| `open` | 开盘价 | 当日第一笔成交价 |
| `high` | 最高价 | 当日最高成交价 |
| `low` | 最低价 | 当日最低成交价 |
| `close` | 收盘价 | 当日最后一笔成交价 |
| `volume` | 成交量 | 股数 |
| `amount` | 成交额 | 仅A股/港股提供，美股为空 |
| `pct_chg` | 涨跌幅 | 百分比，正数上涨负数下跌 |

### `analysis_summary.csv`

所有股票的技术指标汇总，每行一只股票：

```csv
analysis_date,code,name,market,data_source,total_bars,price,change_pct,MA5,MA10,MA20,MA60,ma_alignment,MACD_DIF,MACD_DEA,MACD_hist,MACD_signal,RSI6,RSI12,RSI24,RSI_zone,vol_ratio,vol_trend,bias_ma5,bias_ma10,bias_ma20,support_ma5,support_ma10,trend_score,trend_signal
2026-05-03,600519,贵州茅台,cn_a,akshare,120,2486.5,1.23,2470.3,2455.8,2420.1,2350.6,bullish,15.23,14.81,0.84,golden_cross,62.5,58.3,52.1,strong,1.05,normal,0.65,1.42,2.73,True,False,72,买入
```

| 分组 | 字段 | 中文 | 说明 |
|------|------|------|------|
| 基础 | `analysis_date` | 分析日期 | 数据抓取日期 |
| | `code` | 股票代码 | |
| | `name` | 股票名称 | |
| | `market` | 市场 | cn_a / cn_hk / us |
| | `data_source` | 数据源 | tushare / efinance / akshare / yfinance |
| | `total_bars` | 数据条数 | 获取到的K线条数 |
| 实时 | `price` | 最新价 | |
| | `change_pct` | 涨跌幅 | % |
| MA | `MA5/10/20/60` | 均线 | 5/10/20/60日均价 |
| | `ma_alignment` | 均线排列 | bullish 多头 / bearish 空头 / consolidation 缠绕 |
| MACD | `MACD_DIF` | DIF | 快线 |
| | `MACD_DEA` | DEA | 慢线 |
| | `MACD_hist` | 柱状图 | 2×(DIF-DEA) |
| | `MACD_signal` | MACD信号 | golden_cross金叉 / death_cross死叉 / bullish / bearish |
| RSI | `RSI6/12/24` | 相对强弱 | 6/12/24日RSI值 |
| | `RSI_zone` | RSI区间 | overbought超买(≥80) / strong强势 / neutral / weak弱势 / oversold超卖(≤20) |
| 量能 | `vol_ratio` | 量比 | 当日量/5日均量 |
| | `vol_trend` | 量能趋势 | heavy_volume_up放量涨 / shrink_pullback缩量回调 / normal |
| 乖离率 | `bias_ma5/10/20` | 乖离率 | (收盘价-MA)/MA×100% |
| 支撑 | `support_ma5/10` | 均线支撑 | True/False |
| 评分 | `trend_score` | 综合评分 | 0-100，分数越高越看多 |
| | `trend_signal` | 综合信号 | 强烈买入 / 买入 / 持有 / 观望 / 卖出 / 强烈卖出 |

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
