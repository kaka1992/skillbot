
## 数据字典
### `{CODE}_ohlcv.csv`

历史 K 线数据，每行一个交易日：

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
