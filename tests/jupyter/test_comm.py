"""Comm functionality test — run in a Jupyter notebook cell to verify."""

# Test: create a comm and see if a new cell appears with the test code.
# If the extension is active, a new cell with "print('comm works!')" should appear.

TEST_CODE = "print('comm works!')"

try:
    from comm import create_comm
    comm = create_comm("skillbot:execute-cell",
                       data={"code": TEST_CODE, "trace": False})

    @comm.on_msg
    def _on_reply(msg):
        data = msg.get("content", {}).get("data", {})
        if data.get("success"):
            print("[comm test] SUCCESS — frontend created and executed the cell")
        else:
            print(f"[comm test] FAILED — {data.get('error', 'unknown')}")
        comm.close()

    print(f"[comm test] comm sent: {TEST_CODE}")
    print("[comm test] waiting for frontend reply... (check if a new cell appeared)")
except Exception as e:
    print(f"[comm test] ERROR creating comm: {e}")
    print("[comm test] extension likely not active — check JupyterLab restart")
