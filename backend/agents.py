import os
import httpx
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class BaseAgent:
    def __init__(self, name, role):
        self.name = name
        self.role = role

    def log(self, message):
        print(f"[{self.name}] {message}")

    async def call_llm(self, system_prompt, user_prompt):
        try:
            # Try Gemini first via async client if available, or wrap in thread if not
            # But the plan says use async client. 
            # In google-genai, it's client.aio.models.generate_content
            full_prompt = f"{system_prompt}\n\nUser Request: {user_prompt}"
            
            # Note: Assuming the client has .aio for async support as per standard library
            response = await client.aio.models.generate_content(
                model='models/gemini-2.5-flash',
                contents=full_prompt
            )
            return response.text
        except Exception as e:
            self.log(f"Gemini failed: {e}. Trying OpenRouter fallback...")
            fallback_response = await self.call_openrouter(system_prompt, user_prompt)
            if fallback_response:
                return fallback_response
            return f"Error: Both Gemini and OpenRouter failed. ({str(e)})"

    async def call_openrouter(self, system_prompt, user_prompt):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key or "your_openrouter" in api_key:
            self.log("OpenRouter API key not configured.")
            return None
            
        try:
            async with httpx.AsyncClient() as async_client:
                response = await async_client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "google/gemini-2.0-flash-lite-001", 
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    },
                    timeout=30.0
                )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                self.log(f"OpenRouter Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.log(f"OpenRouter request failed: {e}")
            return None

class Researcher(BaseAgent):
    def __init__(self):
        super().__init__("Researcher", "Knowledge Gathering")

    async def work(self, prompt):
        self.log(f"Searching for information on: {prompt}")
        system_prompt = "You are a specialized Researcher agent. Your goal is to gather detailed information, context, and key facts about the user's topic. Provide a structured research summary."
        return await self.call_llm(system_prompt, prompt)

class Writer(BaseAgent):
    def __init__(self):
        super().__init__("Writer", "Content Creation")

    async def work(self, research_data):
        self.log("Drafting content based on research...")
        system_prompt = "You are a specialized Writer agent. Use the provided research data to draft a comprehensive and engaging report or document. Focus on clarity, flow, and quality."
        return await self.call_llm(system_prompt, f"Draft a report based on this research:\n\n{research_data}")

class Reviewer(BaseAgent):
    def __init__(self):
        super().__init__("Reviewer", "Quality Control")

    async def work(self, draft):
        self.log("Reviewing and polishing draft...")
        system_prompt = "You are a specialized Reviewer agent. Critique and polish the provided draft. Ensure it is professional, accurate, and well-structured. Provide the final polished version."
        return await self.call_llm(system_prompt, f"Review and polish this draft:\n\n{draft}")

class MultiAgentCoordinator:
    def __init__(self):
        self.researcher = Researcher()
        self.writer = Writer()
        self.reviewer = Reviewer()

    async def run_workflow(self, user_prompt):
        research = await self.researcher.work(user_prompt)
        draft = await self.writer.work(research)
        final = await self.reviewer.work(draft)
        
        return {
            "steps": [
                {"agent": "Researcher", "output": research},
                {"agent": "Writer", "output": draft},
                {"agent": "Reviewer", "output": final}
            ],
            "final_data": final
        }

    async def process(self, user_prompt):
        """Alias for backward compatibility."""
        return await self.run_workflow(user_prompt)

