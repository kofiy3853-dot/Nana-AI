import os
from openai import OpenAI
try:
    client = OpenAI(api_key="sk-test")
    print("OpenAI client initialized successfully")
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    import traceback
    traceback.print_exc()
