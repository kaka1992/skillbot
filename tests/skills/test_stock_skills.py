"""Test stock-data-fetch + stock-analysis skills via claude-code."""

import os
import subprocess
import sys

import pytest

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_DIR = os.path.join(PROJECT_DIR, "src")
RUN_SH = os.path.join(PROJECT_DIR, "scripts", "run.sh")
sys.path.insert(0, SRC_DIR)


def _agent_running(agent: str) -> bool:
    """Check if agent is running via run.sh status."""
    try:
        result = subprocess.run(
            ["bash", RUN_SH, "status", agent],
            capture_output=True, text=True, timeout=10, cwd=PROJECT_DIR,
        )
        return "RUNNING" in result.stdout
    except Exception:
        return False


@pytest.fixture(scope="module")
def client():
    """ChatClient connected to claude-code."""
    if not _agent_running("claude-code"):
        pytest.skip("claude-code not running (run.sh start claude-code)")
    from chat import ChatClient

    return ChatClient("claude-code", timeout=600)


# ============================================================
# stock-data-fetch skill
# ============================================================


class TestStockDataFetch:
    """Test the stock-data-fetch skill via hermes-agent REST API."""

    def test_fetch_single_stock_a_share(self, client):
        reply = client.chat(
            "使用stock-data-fetch skill获取600519最近10天的行情数据",
            session="fetch-a",
        )
        assert isinstance(reply, str) and len(reply) > 0
        # Should mention the stock code or price data
        keywords = ["600519", "贵州茅台", "行情", "数据", "price", "K线", "OHLCV"]
        assert any(kw in reply for kw in keywords), (
            f"Expected stock data keywords in reply, got: {reply[:200]}"
        )

    def test_fetch_multi_market(self, client):
        reply = client.chat(
            "使用stock-data-fetch skill获取HK00700最近10天行情",
            session="fetch-hk",
        )
        assert isinstance(reply, str) and len(reply) > 0


# ============================================================
# stock-analysis skill
# ============================================================


class TestStockAnalysis:
    """Test the stock-analysis skill via hermes-agent REST API."""

    def test_analyze_single_stock(self, client):
        reply = client.chat(
            "使用stock-analysis skill分析600519最近10天的走势",
            session="analysis-a1",
        )
        assert isinstance(reply, str) and len(reply) > 0
        keywords = ["600519", "分析", "技术", "MA", "MACD", "RSI", "贵州茅台", "评分", "信号"]
        assert any(kw in reply for kw in keywords), (
            f"Expected analysis keywords in reply, got: {reply[:200]}"
        )

    def test_analyze_with_date_range(self, client):
        reply = client.chat(
            "用stock-analysis skill快速分析600519近5日走势，给一句话结论",
            session="analysis-tsla",
        )
        assert isinstance(reply, str) and len(reply) > 0


# ============================================================
# skill chaining
# ============================================================


class TestSkillChaining:
    """Test stock-data-fetch → stock-analysis chaining."""

    def test_fetch_then_analyze(self, client):
        # Step 1: fetch data
        client.chat(
            "使用stock-data-fetch skill获取600519最近10天行情",
            session="chain-1",
        )
        # Step 2: analyze the fetched data
        reply = client.chat(
            "使用stock-analysis skill对刚才获取的600519数据进行技术分析，给出操作建议",
            session="chain-1",
        )
        assert isinstance(reply, str) and len(reply) > 0
        keywords = ["600519", "买入", "持有", "观望", "卖出", "止损", "目标价"]
        assert any(kw in reply for kw in keywords), (
            f"Expected trading advice keywords, got: {reply[:200]}"
        )
