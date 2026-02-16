from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import os
import httpx
import tempfile
import json
import platform
import shutil
import threading
import time
import re
from pathlib import Path
from flask_socketio import SocketIO, emit
import pyautogui
import secrets
import sys
from agents import MultiAgentCoordinator
from reasoning_agent import ReasoningAgent
from dotenv import load_dotenv

load_dotenv()

# Advanced File & Window Support
try:
    from PyPDF2 import PdfReader
    from docx import Document
except ImportError:
    PdfReader = None
    Document = None

try:
    import win32gui
    import win32con
    import win32api
    import win32process
except ImportError:
    win32gui = None
    win32con = None

app = Flask(__name__)
# Enable CORS for socket connection too
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Secure remote token
REMOTE_TOKEN = secrets.token_hex(16)
print(f"!!! REMOTE CONTROL TOKEN: {REMOTE_TOKEN} !!!")

# Disable pyautogui failsafe for smoother mobile control
pyautogui.FAILSAFE = False

coordinator = MultiAgentCoordinator()
reasoning_agent = ReasoningAgent()

# Configuration
BACKEND_PORT = int(os.getenv('BACKEND_PORT', 3001))
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FILE_EXTENSIONS = {'.txt', '.py', '.json', '.csv', '.md', '.log', '.js', '.html', '.css', '.pdf', '.docx'}
MAX_SEARCH_DEPTH = 3
SEARCH_TIMEOUT = 5  # seconds
