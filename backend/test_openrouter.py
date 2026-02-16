import os
from dotenv import load_dotenv
import httpx

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

print(f"Testing OpenRouter API...")
print(f"API Key: {api_key[:20]}...{api_key[-10:]}")
print()

try:
    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Say 'Hello' in 3 words"}]
        },
        timeout=10.0
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("\n✅ OpenRouter is WORKING!")
    elif response.status_code == 401:
        print("\n❌ API Key is INVALID or EXPIRED")
    elif response.status_code == 402:
        print("\n❌ INSUFFICIENT CREDITS - Please add credits to your OpenRouter account")
    else:
        print(f"\n⚠️ Unexpected error: {response.status_code}")
        
except httpx.TimeoutException:
    print("❌ REQUEST TIMEOUT - OpenRouter is not responding")
except Exception as e:
    print(f"❌ ERROR: {e}")
