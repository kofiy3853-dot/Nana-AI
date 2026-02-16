import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from agents import MultiAgentCoordinator
from nana_backend_v2 import handle_execute, CommandRequest

async def test_coordinator_alias():
    print("[TEST] Testing MultiAgentCoordinator 'process' alias...")
    coordinator = MultiAgentCoordinator()
    try:
        # This will fail unless GEMINI_API_KEY is set, but we just want to verify the attribute exists
        if hasattr(coordinator, 'process'):
            print("✅ 'process' alias exists.")
        else:
            print("❌ 'process' alias missing.")
    except Exception as e:
        print(f"Coordinator test error (expected if no API key): {e}")

async def test_media_guard(monkeypatch=None):
    print("\n[TEST] Testing play_local_media guard...")
    import nana_backend_v2
    # Mock search roots to only current dir for speed
    nana_backend_v2.get_all_roots = lambda: [Path.cwd()]
    
    req = CommandRequest(command="non_existent_file.mp3", intent="play_local_media")
    try:
        res = await handle_execute(req)
        print(f"Result: {res}")
        if not res.get('success') and "Couldn't find media" in res.get('data'):
            print("✅ Media guard correctly rejected unrelated file matching.")
        else:
            print(f"❌ Media guard result unexpected: {res.get('data')}")
    except Exception as e:
        print(f"❌ Media guard crashed: {e}")

if __name__ == "__main__":
    asyncio.run(test_coordinator_alias())
    asyncio.run(test_media_guard())
