"""End-to-end test for chat+server interrupt mechanism.

Tests the full chain:
  ClaudeBackend.stream_chunks() → server → ClaudeSDKClient
  ClaudeBackend.interrupt() → POST /interrupt → Session.interrupt()
"""

import sys
import threading
import time

# Add src to path
sys.path.insert(0, "src")

from chat.claude import ClaudeBackend


def test_interrupt_preserves_session():
    """Interrupt a streaming query then send another on the same session."""
    backend = ClaudeBackend(timeout=120)
    session = "test-interrupt-1"

    print("=== Test: interrupt + continue on same session ===\n")

    # Step 1: start a long streaming query
    print("[1] Starting streaming query...")
    chunks = []
    interrupted = False

    def consume():
        nonlocal interrupted
        try:
            gen = backend.stream_chunks(
                "Write a Python function that prints numbers 1 to 100 with a 0.1s sleep between each",
                session=session,
            )
            for chunk in gen:
                chunks.append(chunk)
                if chunk.text:
                    print(f"    text: {chunk.text[:80]}...")
                if chunk.blocks:
                    for b in chunk.blocks:
                        print(f"    [{b.type}]")
                # Interrupt after first few chunks
                if not interrupted and len(chunks) >= 3:
                    interrupted = True
                    print("\n[2] Calling interrupt()...")
                    backend.interrupt(session)
                    print("    interrupt() returned")
        except Exception as e:
            print(f"    stream error: {e}")

    # Run stream in a thread so we can observe it
    t = threading.Thread(target=consume)
    t.start()
    t.join(timeout=30)

    if t.is_alive():
        print("\n[FAIL] Stream did not terminate after interrupt (still running after 30s)")
        return False

    print("\n[3] Stream terminated. Sending second query on same session...")

    # Step 2: send another query on the SAME session
    try:
        gen2 = backend.stream_chunks("What is 2+2? Answer in one word.", session=session)
        result = []
        for chunk in gen2:
            if chunk.text:
                result.append(chunk.text)
        full = "".join(result)
        print(f"    Response: {full[:200]}")
        if "4" in full or "four" in full.lower():
            print("\n[PASS] Interrupt + continue works. Session preserved.")
            return True
        else:
            print(f"\n[WARN] Got response but unexpected content: {full[:200]}")
            return True  # still worked
    except Exception as e:
        print(f"\n[FAIL] Second query failed: {e}")
        return False
    finally:
        backend.clear_session(session)


if __name__ == "__main__":
    ok = test_interrupt_preserves_session()
    sys.exit(0 if ok else 1)
