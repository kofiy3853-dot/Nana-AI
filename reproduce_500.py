import httpx
import asyncio
import json

async def reproduce_error():
    url = "http://localhost:3001/api/execute"
    payload = {
        "command": "test.txt",
        "intent": "open_file",
        "metadata": {},
        "mode": "local",
        "history": []
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, json=payload, timeout=10)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(reproduce_error())
