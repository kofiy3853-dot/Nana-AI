import requests
import json

url = "http://localhost:3001/api/execute"

def test_intent(label, command, intent):
    print(f"Testing {label}: '{command}'...")
    data = {
        "command": command,
        "intent": intent
    }
    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        if result.get('success'):
            print(f"✅ SUCCESS: {result['data']}")
        else:
            print(f"❌ FAILED: {result.get('data')}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    print("-" * 30)

# Test File Launching
test_intent("File Launch", "test_launch.txt", "open_file")

# Test Folder Launching (Common folder)
test_intent("Folder Launch (Downloads)", "Downloads", "open_folder")

# Test Folder Launching (Current)
test_intent("Folder Launch (Current)", ".", "open_folder")
