import os
import json
import httpx
import sys
import time
from dotenv import load_dotenv

load_dotenv()

class ReasoningAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        # Primary model: DeepSeek R1 (Reasoning)
        self.model = "deepseek/deepseek-r1"
        # Fallback model: Gemini 2.0 Flash Lite (Reliable)
        self.fallback_model = "google/gemini-2.0-flash-lite-001"

    async def think(self, user_query):
        """
        Executes a reasoning chain to answer the user's query with high fidelity.
        Uses OpenRouter's reasoning capabilities, including a verification step.
        """
        start_time = time.time()
        
        if not self.api_key:
            return "Error: OPENROUTER_API_KEY not found in backend/.env. Please add it."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/nana-ai",
            "X-Title": "Nana AI"
        }

        async def call_model(async_client, model_id, query):
            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": query}],
                "reasoning": {"enabled": True} 
            }
            try:
                print(f"[ReasoningAgent] Connecting to {model_id}...", file=sys.stderr)
                response = await async_client.post(
                    url=self.base_url,
                    headers=headers,
                    content=json.dumps(payload),
                    timeout=90 # Increased timeout for slow reasoning models
                )
                print(f"[ReasoningAgent] Response status: {response.status_code}", file=sys.stderr)
                if response.status_code != 200:
                     print(f"[ReasoningAgent] Error content: {response.text}", file=sys.stderr)
                return response
            except Exception as e:
                print(f"[ReasoningAgent] Request failed with exception: {str(e)}", file=sys.stderr)
                return None

        async with httpx.AsyncClient() as async_client:
            # Step 1: Initial reasoning call
            response = await call_model(async_client, self.model, user_query)
            
            current_model = self.model
            # Fallback if failed
            if not response or response.status_code != 200:
                print(f"[ReasoningAgent] Primary model failed. Trying fallback...", file=sys.stderr)
                response = await call_model(async_client, self.fallback_model, user_query)
                current_model = self.fallback_model
                
            if not response or response.status_code != 200:
                 duration = time.time() - start_time
                 print(f"[ReasoningAgent] Think failed after {duration:.2f}s", file=sys.stderr)
                 return f"Error: Both primary and fallback models failed. (Last status: {response.status_code if response else 'None'})"

            try:
                data = response.json()
                if 'choices' not in data or not data['choices']:
                    return "Error: Empty response from reasoning model."

                first_choice = data['choices'][0]
                first_message = first_choice['message']
                initial_content = first_message.get('content', '')
                reasoning_details = first_message.get('reasoning_details', None)

                final_answer = initial_content

                # Verification Step
                if reasoning_details:
                    print(f"[ReasoningAgent] Reasoning captured. Verifying...", file=sys.stderr)
                    
                    messages = [
                        {"role": "user", "content": user_query},
                        {
                            "role": "assistant",
                            "content": initial_content,
                            "reasoning_details": reasoning_details
                        },
                        {"role": "user", "content": "Review your reasoning and provide the final, most accurate answer."}
                    ]
                    
                    payload2 = {
                        "model": current_model,
                        "messages": messages,
                        "reasoning": {"enabled": True}
                    }
                    
                    response2 = await async_client.post(
                        url=self.base_url,
                        headers=headers,
                        content=json.dumps(payload2),
                        timeout=90
                    )
                    
                    if response2.status_code == 200:
                        data2 = response2.json()
                        final_answer = data2['choices'][0]['message']['content']
                    else:
                        print(f"[ReasoningAgent] Verification failed, using initial answer.", file=sys.stderr)
                
                duration = time.time() - start_time
                print(f"[ReasoningAgent] Think process successful in {duration:.2f}s", file=sys.stderr)
                return final_answer

            except Exception as e:
                duration = time.time() - start_time
                print(f"[ReasoningAgent] Think process crashed after {duration:.2f}s: {e}", file=sys.stderr)
                return f"My reasoning process crashed: {str(e)}"

