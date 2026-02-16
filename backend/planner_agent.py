import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

class PlannerAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "google/gemini-2.0-flash-001" # Fast and reliable for JSON structuring

    async def plan(self, user_command, session_context="No application currently in focus."):
        """
        Converts natural language user commands into structured JSON instructions.
        """
        if not self.api_key:
            return {"error": "API Key missing"}

        system_prompt = """
You are an AI Task Planner for a desktop automation agent.
Your job is to convert natural language user commands into structured JSON instructions for execution.

Rules:
1. Break multi-step commands into atomic actions.
2. Use clear action names.
3. Return only valid JSON.
4. Do not explain anything.
5. Do not add extra text.

Available actions:
- open_application (target: string)
- navigate_folder (target: string)
- search_file (target: string)
- open_file (target: string)
- open_latest_file (target: string, folder: string)
- type_text (text: string)
- press_key (key: string)
- click (button: "left"|"right")
- move_mouse (dx: int, dy: int)
- switch_to_app (target: string)
- wait (duration: int seconds)

Context Awareness Rules:
1. If the user says "type hello" and an app is active in context, use "type_text".
2. If the user says "significant" but ambiguous terms like "it", "that", or "again", refer to "Current Session Context" (e.g., "open it again" might mean open the "Last File used").
3. If the user says "save" or "close it", use "press_key" with "ctrl+s" or "alt+f4".
4. Use "switch_to_app" if the user wants to change focus to an already open app.

Current Session Context:
{session_context}

Example Output (Multi-step):
{{
  "intent": "file_navigation",
  "steps": [
    {{"action": "open_application", "target": "file_explorer"}},
    {{"action": "navigate_folder", "target": "downloads"}},
    {{"action": "search_file", "target": "reference"}},
    {{"action": "open_file", "target": "reference"}}
  ]
}}

Example Output (Latest/Recent):
{{
  "intent": "latest_file",
  "steps": [{{"action": "open_latest_file", "folder": "downloads"}}]
}}

Example Output (Contextual):
{{
  "intent": "context_action",
  "steps": [
    {{"action": "type_text", "text": "hello from context"}}
  ]
}}

If you cannot fulfill the request with the available actions, or if the request doesn't make sense as a multi-step task, return an empty steps list:
{{
  "intent": "unknown",
  "steps": []
}}
"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt.format(session_context=session_context)},
                {"role": "user", "content": f"USER_COMMAND: {user_command}\n\nReturn only JSON."}
            ],
            "response_format": { "type": "json_object" }
        }

        try:
            async with httpx.AsyncClient() as async_client:
                response = await async_client.post(self.base_url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    content = response.json()['choices'][0]['message']['content']
                    # Strip markdown code blocks if present
                    if "```" in content:
                        content = content.split("```")[1]
                        if content.startswith("json"):
                            content = content[4:]
                        content = content.strip()
                    return content
                return json.dumps({"error": f"API error: {response.status_code}"})
        except Exception as e:
            return json.dumps({"error": str(e)})


if __name__ == "__main__":
    # Quick Test
    planner = PlannerAgent()
    p = planner.plan("Open notepad and type 'hello'")
