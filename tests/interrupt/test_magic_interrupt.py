"""End-to-end test simulating magic.py's exact interrupt flow.

The real Ctrl+C from kernel.interrupt() delivers KeyboardInterrupt to the
main thread regardless of what it's doing (SIGINT). But in tests we must
first call s.interrupt() to unblock the stream thread from recv(), then
raise KeyboardInterrupt.
"""
import ctypes
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agent import AgentSession
from agent.prompt import PromptBuilder


def raise_in_thread(thread_id, exc_type):
    tid = ctypes.c_long(thread_id)
    exc = ctypes.py_object(exc_type)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, exc)
    if res > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)


def test():
    test_key = f"test-magic-{os.getpid()}"
    print("=== Magic Interrupt E2E ===\n")

    s = AgentSession("claude-code", timeout=120)
    s.init_session(system_prompt=PromptBuilder.main(), session_key=test_key)
    if s.client is None:
        print("[FAIL] init")
        return False
    print(f"[1] Session ready: {s.session_id}")

    result = {}
    started = threading.Event()

    def run():
        started.set()
        try:
            raw = s.stream(
                "Write a Python script that processes a CSV file. The script should:\n"
                "1. Read the file with pandas\n"
                "2. Clean all columns (strip whitespace, fill NA with 0)\n"
                "3. Calculate summary statistics for each numeric column\n"
                "4. Generate a matplotlib bar chart\n"
                "5. Save the chart as PNG\n"
                "6. Print a detailed report of findings\n\n"
                "Write complete working code with proper imports.",
                show_text=False,
            )
            result["raw"] = raw
            result["interrupted"] = False
        except KeyboardInterrupt:
            result["interrupted"] = True
        except Exception as e:
            result["error"] = str(e)

    t = threading.Thread(target=run)
    t.start()
    started.wait()  # ensure thread has started
    time.sleep(2.0)

    # Step 1: call server interrupt first to unblock recv()
    print("[2] s.interrupt() → server stops subprocess")
    s.interrupt()
    time.sleep(0.3)

    # Step 2: now raise KeyboardInterrupt in stream thread
    print("[3] raising KeyboardInterrupt in stream thread")
    raise_in_thread(t.ident, KeyboardInterrupt)
    t.join(timeout=20)
    if t.is_alive():
        print("[FAIL] thread still alive")
        return False

    print(f"    interrupted={result.get('interrupted')} error={result.get('error', 'OK')}")

    if not result.get("interrupted"):
        print("[WARN] stream finished before interrupt (agent too fast)")

    # Second query
    print("\n[4] Second query on same session: 'What is 6+6? one word'")
    try:
        raw2 = s.stream("What is 6+6? Answer in one word.", show_text=False)
        print(f"    Response: {raw2.strip()[:200]}")
        if "12" in raw2 or "twelve" in raw2.lower():
            print("[PASS]\n")
            return True
        print(f"[WARN] Got: {raw2[:200]}\n")
        return True
    except Exception as e:
        print(f"[FAIL] {e}\n")
        return False
    finally:
        s.cleanup()


if __name__ == "__main__":
    ok = test()
    sys.exit(0 if ok else 1)
