"""Integration test for AgentSession + ChatClient → ClaudeBackend interrupt chain.

Tests the exact path magic.py uses:
  _stream() catches KeyboardInterrupt
  → ChatClient.interrupt(session)
  → gen.close() (triggers finally: resp.close())
  → server CancelledError → lock released
  → next query on same session works
"""

import ctypes
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agent.session import AgentSession


def _raise_in_thread(thread_id, exc_type):
    """Raise an exception in the given thread (CPython only)."""
    tid = ctypes.c_long(thread_id)
    exc = ctypes.py_object(exc_type)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, exc)
    if res == 0:
        raise ValueError("invalid thread id")
    elif res > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def test_keyboard_interrupt_in_stream():
    """Simulate real Ctrl+C: KeyboardInterrupt thrown into _stream()."""
    agent = "claude-code"
    timeout = 120
    session_key = "test-agent-kbi-1"

    print("=== Test: KeyboardInterrupt in AgentSession.stream() ===\n")

    s = AgentSession(agent, timeout)
    s.init_session(
        system_prompt="You are a test assistant. Keep responses brief.",
        session_key=session_key,
    )
    if s.client is None:
        print("[FAIL] Session init failed")
        return False
    print(f"[1] Session ready: {s.session_id}")

    stream_result = {}

    def run_stream():
        try:
            raw = s.stream(
                "Write a Python script that counts from 1 to 100 with time.sleep(0.1) between each number",
                show_text=False,
            )
            stream_result["raw"] = raw
            stream_result["interrupted"] = False
        except KeyboardInterrupt:
            stream_result["interrupted"] = True
            print("    [KeyboardInterrupt caught in _stream()]")
        except Exception as e:
            stream_result["error"] = str(e)
            print(f"    [stream error: {e}]")

    t = threading.Thread(target=run_stream)
    t.start()

    # Let the stream produce some output, then simulate Ctrl+C
    time.sleep(3)
    print("[2] Simulating Ctrl+C (raising KeyboardInterrupt in stream thread)...")
    _raise_in_thread(t.ident, KeyboardInterrupt)

    t.join(timeout=15)
    if t.is_alive():
        print("[FAIL] Stream thread still running after 15s — interrupt didn't work")
        return False

    if stream_result.get("error"):
        print(f"[FAIL] Stream error: {stream_result['error']}")
        return False

    interrupted = stream_result.get("interrupted", False)
    print(f"[3] Stream terminated. Interrupted: {interrupted}")

    # Now send a second query on the same session
    print("[4] Sending second query on same session...")
    try:
        raw2 = s.stream("What is 4+4? Answer in one word.", show_text=False)
        print(f"    Response: {raw2.strip()[:200]}")
        if "8" in raw2 or "eight" in raw2.lower():
            print("\n[PASS] KeyboardInterrupt handled correctly, session preserved.\n")
            return True
        else:
            print(f"\n[WARN] Unexpected response but query worked: {raw2[:100]}")
            return True
    except Exception as e:
        print(f"\n[FAIL] Second query failed: {e}")
        return False
    finally:
        s.cleanup()


if __name__ == "__main__":
    ok = test_keyboard_interrupt_in_stream()
    sys.exit(0 if ok else 1)
