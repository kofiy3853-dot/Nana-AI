import requests
import json
import time

url = "http://127.0.0.1:3001/api/execute"
payload = {
    "command": "Open notepad and type 'Nana is now much safer!'",
    "intent": "unknown",
    "mode": "local"
}
headers = {
    "Content-Type": "application/json"
}

try:
    print(f"Sending request to {url}...")
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
