import requests
import json

url = "http://localhost:3001/api/execute"

# Test multi-agent workflow
data = {
    "command": "what is the meaning of life",
    "intent": "multi_agent_workflow"
}

print("Testing multi-agent workflow with Gemini...")
print()

try:
    response = requests.post(url, json=data, timeout=30)
    result = response.json()
    
    if result.get('success'):
        print("✅ Multi-Agent Workflow is WORKING!")
        print()
        print("Final Response:")
        print(result['data'])
        print()
        if 'steps' in result:
            print("Agent Steps:")
            for step in result['steps']:
                print(f"  - {step['agent']}: {step['output'][:100]}...")
    else:
        print(f"❌ Failed: {result.get('data')}")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
