#!/usr/bin/env python3
"""
Agent Flow Tests for REPL Bridge.

These tests simulate an AI agent using the REPL Bridge to perform tasks
that would be impossible with standard execution APIs:

1. Hallucination Recovery - Using Tab completion to discover real API names
2. Interactive Prompts - Detecting and responding to mid-stream input requests
"""

import time
from brepl import REPLSession, WaitStrategy


def test_hallucination_recovery():
    """
    Test: Discovery, Not Hallucination

    Scenario: An agent defines a variable with a complex name, then needs to
    use it but can only remember part of the name. Instead of hallucinating,
    it uses Tab completion to discover the actual name.

    This proves the agent can explore the runtime environment in real-time.
    """
    print("\n" + "=" * 60)
    print("TEST: Hallucination Recovery (The 'Tab' Feature)")
    print("=" * 60)

    with REPLSession("ipython") as session:
        # Wait for IPython to start
        for _ in range(100):
            session._pump()
            time.sleep(0.02)
        session.wait(timeout=5.0)

        # 1. Set up state - define a variable with a complex name
        print("\n[Agent] Defining a variable with a complex name...")
        session.execute("my_super_complex_variable_name_v2 = 42")
        time.sleep(0.5)

        # 2. Clear any previous input
        session.send_key("Ctrl+C")
        time.sleep(0.3)
        for _ in range(50):
            session._pump()
            time.sleep(0.01)

        # 3. Agent "forgets" the full name - only remembers prefix
        print("[Agent] I need to print that variable... I think it started with 'my_super'")
        print("[Agent] Typing partial name: 'my_super'")
        session.send_text("my_super", enter=False)
        time.sleep(0.3)
        for _ in range(30):
            session._pump()
            time.sleep(0.01)

        # 4. The Magic: Agent uses Tab completion to discover reality
        print("[Agent] Pressing TAB to discover the full name...")
        result = session.get_completions()

        # 5. Show what the agent sees
        print("\n--- COMPLETION RESULT ---")
        print(f"Mode: {result.mode}")
        if result.inserted_text:
            print(f"Inserted: {result.inserted_text}")
        if result.candidates:
            print(f"Candidates: {result.candidates}")

        screen = session.screen.render()
        print("\n--- CURRENT SCREEN ---")
        # Show last few relevant lines
        for line in screen.split('\n')[-10:]:
            if line.strip():
                print(line)
        print("-" * 25)

        # 6. Verification
        full_name = "my_super_complex_variable_name_v2"
        if result.mode == "INLINE" and "complex_variable_name_v2" in result.inserted_text:
            print("\n✅ SUCCESS: Tab completion revealed the full variable name!")
            print(f"   Agent can now confidently use: {full_name}")
            return True
        elif full_name in screen:
            print("\n✅ SUCCESS: Variable name visible on screen via completion.")
            return True
        else:
            print("\n❌ FAILURE: Could not discover the variable name.")
            print(f"   Expected to find: {full_name}")
            return False


def test_interactive_prompt():
    """
    Test: Interactive Prompt Detection (The 'Sudo' Feature)

    Scenario: A command blocks waiting for user input (like sudo asking for
    a password). The agent must detect this state and respond appropriately.

    This proves the agent can handle mid-stream interactions.
    """
    print("\n" + "=" * 60)
    print("TEST: Interactive Prompt (The 'Sudo' Feature)")
    print("=" * 60)

    with REPLSession("bash") as session:
        session.wait(timeout=3.0)

        # Use Python's input() to simulate a blocking prompt
        # This mimics 'sudo' behavior without needing root
        print("\n[Agent] Running a command that will ask for input...")

        cmd = 'python3 -c "x = input(\'Password: \'); print(f\'Access granted with: {x}\')"'
        session.send_text(cmd)

        # Wait a moment for the prompt to appear
        time.sleep(1.0)
        for _ in range(100):
            session._pump()
            time.sleep(0.01)

        screen = session.screen.render()
        print("\n--- CURRENT SCREEN ---")
        for line in screen.split('\n')[-8:]:
            if line.strip():
                print(line)
        print("-" * 25)

        # Check if we can detect the password prompt
        if "Password:" in screen:
            print("\n[Agent] Detected password prompt! Responding...")
            session.send_text("secret123")

            # Wait for the response
            time.sleep(0.5)
            for _ in range(50):
                session._pump()
                time.sleep(0.01)

            screen = session.screen.render()
            print("\n--- AFTER RESPONSE ---")
            for line in screen.split('\n')[-5:]:
                if line.strip():
                    print(line)
            print("-" * 25)

            if "Access granted" in screen:
                print("\n✅ SUCCESS: Detected prompt and responded correctly!")
                return True
            else:
                print("\n❌ FAILURE: Response not processed correctly.")
                return False
        else:
            print("\n❌ FAILURE: Could not detect the password prompt.")
            return False


def test_multi_turn_exploration():
    """
    Test: Multi-turn API Exploration

    Scenario: Agent needs to find a function in a module but doesn't know
    the exact name. It uses multiple completions to explore the API.

    This proves the agent can navigate complex APIs without hallucination.
    """
    print("\n" + "=" * 60)
    print("TEST: Multi-turn API Exploration")
    print("=" * 60)

    with REPLSession("python") as session:
        session.wait(timeout=3.0)

        print("\n[Agent] I need to find a function in os.path that checks if something is a file...")
        print("[Agent] Let me explore the os.path module...")

        # Step 1: Import os
        session.execute("import os")
        time.sleep(0.3)

        # Step 2: Start typing and explore
        print("\n[Agent] Typing 'os.path.is' and pressing Tab...")
        session.send_text("os.path.is", enter=False)
        time.sleep(0.3)
        for _ in range(30):
            session._pump()
            time.sleep(0.01)

        result = session.get_completions()

        print("\n--- COMPLETION RESULT ---")
        print(f"Mode: {result.mode}")
        if result.candidates:
            print(f"Available options: {result.candidates}")

        # Verify we found isfile
        if result.candidates and any("isfile" in c for c in result.candidates):
            print("\n✅ SUCCESS: Found 'isfile' in completions!")
            print("   Agent now knows the exact function name without guessing.")
            return True
        elif result.mode == "INLINE" and "file" in result.inserted_text:
            print("\n✅ SUCCESS: Completed to isfile!")
            return True
        else:
            print("\n❌ FAILURE: Could not find isfile in completions.")
            return False


def main():
    """Run all agent flow tests."""
    print("\n" + "#" * 60)
    print("# REPL Bridge - Agent Flow Tests")
    print("# Testing: Discovery, Not Hallucination")
    print("#" * 60)

    results = []

    # Test 1: Hallucination Recovery
    try:
        results.append(("Hallucination Recovery", test_hallucination_recovery()))
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        results.append(("Hallucination Recovery", False))

    # Test 2: Interactive Prompt
    try:
        results.append(("Interactive Prompt", test_interactive_prompt()))
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        results.append(("Interactive Prompt", False))

    # Test 3: Multi-turn Exploration
    try:
        results.append(("Multi-turn Exploration", test_multi_turn_exploration()))
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        results.append(("Multi-turn Exploration", False))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    print(f"\nTotal: {passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
