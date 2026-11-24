"""Opt-in real SDK permission smoke; only creates temporary sentinel files."""

import os

import pytest

from server.session import Session


@pytest.mark.integration
@pytest.mark.skipif(os.environ.get("SKILLBOT_LIVE_PERMISSION_TEST") != "1", reason="explicit opt-in required")
@pytest.mark.asyncio
async def test_live_sdk_write_then_plan_denial(tmp_path):
    session = Session("permission-smoke")
    target = tmp_path / "artifacts/permission-smoke/sentinel.txt"
    target.parent.mkdir(parents=True)
    observed = []
    real_gate = session._pre_tool_use

    async def gate(data, tool_id, context):
        output = await real_gate(data, tool_id, context)
        observed.append((data.get("tool_name"), output["hookSpecificOutput"]["permissionDecision"]))
        return output

    session._pre_tool_use = gate
    try:
        # Bypass only the advisory prose to test the SDK hook, not model obedience.
        options = session._request_options("auto", str(tmp_path), None, None)
        import asyncio
        await asyncio.wait_for(session._send_inner(
            f"Use the Write tool to create {target} containing exactly APPROVED. Do not use Bash.", options,
        ), 90)
        assert target.read_text().strip() == "APPROVED"
        assert ("Write", "allow") in observed

        session._request_options("plan", str(tmp_path), None, None)
        observed.clear()
        await asyncio.wait_for(session._send_inner(
            f"Use the Write tool now to overwrite {target} with CHANGED. Do not use Bash. "
            "If the tool is denied, stop and report the denial.", options,
        ), 90)
        assert ("Write", "deny") in observed
        assert target.read_text().strip() == "APPROVED"
    finally:
        await session.close()
