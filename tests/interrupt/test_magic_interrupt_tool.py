"""Test real KeyboardInterrupt flow using SIGALRM (closest to kernel.interrupt())."""
import os
import signal
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agent import AgentSession
from agent.prompt import PromptBuilder


def test():
    test_key = f"test-magic-alrm-{os.getpid()}"
    print("=== SIGALRM Interrupt Test ===\n")

    s = AgentSession("claude-code", timeout=60)
    s.init_session(system_prompt=PromptBuilder.main(), session_key=test_key)
    if s.client is None:
        print("[FAIL] init")
        return False
    print(f"[1] Session ready: {s.session_id}")

    result = {"interrupted": False, "error": "", "raw": ""}

    def handler(signum, frame):
        raise KeyboardInterrupt()

    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.alarm(2)  # Interrupt after 2 seconds

    print("[2] Streaming (SIGALRM in 2s)...")
    try:
        raw = s.stream(
            "Write a complete Python script that analyzes a CSV file:\n"
            "1. Read CSV with pandas\n"
            "2. Clean data\n"
            "3. Generate summary statistics\n"
            "4. Create matplotlib charts\n"
            "5. Save results\n"
            "Write full code with imports.",
            show_text=False,
        )
        result["raw"] = raw
    except KeyboardInterrupt:
        result["interrupted"] = True
        print("    caught KeyboardInterrupt")
    except Exception as e:
        result["error"] = str(e)
        print(f"    error: {e}")
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

    print(f"    interrupted={result['interrupted']}")

    # Second query
    print("\n[3] Second query: 'What is 7+7? one word'")
    try:
        raw2 = s.stream("What is 7+7? Answer in one word.", show_text=False)
        print(f"    Response: {raw2.strip()[:200]}")
        if "14" in raw2 or "fourteen" in raw2.lower():
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
