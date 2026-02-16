import os
import sys
import json
import logging
import secrets
import threading
import subprocess
import re
import platform
import shutil
import time
import asyncio
import webbrowser
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Nana AI Backend")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Core Component Imports ---
try:
    from agents import MultiAgentCoordinator
    from reasoning_agent import ReasoningAgent
    from planner_agent import PlannerAgent
    from memory_manager import MemoryManager
    from auth import verify_token, authenticate_user, create_access_token
except ImportError as e:
    print(f"ERROR: Missing core components: {e}")
    sys.exit(1)

# --- Configuration & Security ---
load_dotenv()
REMOTE_TOKEN = os.getenv('REMOTE_TOKEN')
if not REMOTE_TOKEN:
    REMOTE_TOKEN = secrets.token_hex(16)
    print(f"!!! GENERATED RANDOM REMOTE CONTROL TOKEN: {REMOTE_TOKEN} !!!")
else:
    print(f"!!! PERSISTENT REMOTE CONTROL TOKEN LOADED: {REMOTE_TOKEN} !!!")

BACKEND_PORT = int(os.getenv('BACKEND_PORT', 3001))
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FILE_EXTENSIONS = {'.txt', '.py', '.json', '.csv', '.md', '.log', '.js', '.html', '.css', '.pdf', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
MAX_SEARCH_DEPTH = 5
SEARCH_TIMEOUT = 10

# --- Logging Setup ---
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "nana.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("NanaAI")

# Suppress annoying EDID parsing warnings from screen_brightness_control
logging.getLogger('screen_brightness_control').setLevel(logging.ERROR)

# --- Global Exception Handler (must be after logger init) ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    error_msg = traceback.format_exc()
    logger.error(f"GLOBAL ERROR: {exc}\n{error_msg}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "data": f"Internal Server Error: {str(exc)}"},
    )

# --- Advanced Support ---
try:
    from PyPDF2 import PdfReader
    from docx import Document
except ImportError:
    PdfReader = Document = None

try:
    import win32gui, win32con, win32api, win32process, win32clipboard
except ImportError:
    win32gui = win32con = win32api = win32process = win32clipboard = None
    logger.warning("pywin32 not found. Window management features disabled.")

import pyautogui
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

# --- Advanced Utilities ---
import psutil
try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    import screen_brightness_control as sbc
except ImportError:
    AudioUtilities = sbc = None
    logger.warning("Optional utility libraries (pycaw, screen-brightness-control) not found.")

# --- Initialize Components ---
coordinator = MultiAgentCoordinator()
reasoning_agent = ReasoningAgent()
planner_agent = PlannerAgent()
memory_manager = MemoryManager()

# --- Security: Command Whitelist ---
# --- Security: Command Whitelist ---
ALLOWED_COMMANDS = {
    "sleep": 'powershell -Command "Add-Type -Assembly System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState(\'Suspend\', $false, $false)"',
    "shutdown": 'shutdown /s /t 10',
    "restart": 'shutdown /r /t 10',
    "lock": 'rundll32.exe user32.dll,LockWorkStation'
}

# --- FastAPI Setup ---
# Using app initialized at start for global error handling
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CommandRequest(BaseModel):
    command: str
    intent: Optional[str] = "unknown"
    metadata: Optional[Dict[str, Any]] = {}
    mode: Optional[str] = "local"
    history: Optional[List[Dict[str, Any]]] = []

class LoginRequest(BaseModel):
    username: str
    password: str

import socketio
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# --- Socket.IO Setup ---
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*', max_http_buffer_size=10000000)

# --- Templates & Static Files ---
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)

# --- Socket.IO Events ---

@sio.event
async def connect(sid, environ, auth=None):
    # Retrieve token from query string
    query_string = environ.get('QUERY_STRING', '')
    token = ""
    if 'token=' in query_string:
        token = query_string.split('token=')[1].split('&')[0]
    
    if token != REMOTE_TOKEN:
        logger.warning(f"Unauthorized Socket.IO connection attempt: {sid} (Token: {token})")
        return False # Reject connection
        
    logger.info(f"Socket.IO Connected: {sid}")

@sio.event
async def disconnect(sid):
    logger.info(f"Socket.IO Disconnected: {sid}")

@sio.event
async def mouse_move(sid, data):
    dx, dy = data.get('dx', 0), data.get('dy', 0)
    pyautogui.moveRel(dx, dy)

@sio.event
async def mouse_click(sid, data):
    button = data.get('button', 'left')
    pyautogui.click(button=button)

@sio.event
async def mouse_scroll(sid, data):
    direction = data.get('direction', 'down')
    amount = -100 if direction == 'down' else 100
    pyautogui.scroll(amount)

@sio.event
async def key_press(sid, data):
    key = data.get('key', '').lower()
    if not key: return
    
    # Mapping for special keys
    key_map = {
        'win': 'win', 'ctrl': 'ctrl', 'alt': 'alt', 'shift': 'shift',
        'enter': 'enter', 'backspace': 'backspace', 'tab': 'tab', 'esc': 'esc', 'space': 'space'
    }
    action_key = key_map.get(key, key)
    try:
        pyautogui.press(action_key)
    except:
        pass

@sio.event
async def type_text(sid, data):
    text = data.get('text', '')
    if text:
        pyautogui.write(text, interval=0.01)

# --- FastAPI Routes ---

@app.get("/remote")
async def remote_page(request: Request, token: str = None):
    if token != REMOTE_TOKEN:
        return JSONResponse({"success": False, "error": "Unauthorized"}, status_code=401)
    return templates.TemplateResponse("remote.html", {"request": request})

# --- Helper Logic ---

def sanitize_command_input(user_input):
    dangerous = [';', '&&', '||', '|', '`', '$', '(', ')', '<', '>', '&']
    for p in dangerous:
        if p in user_input and not user_input.startswith(('http', 'ms-', 'shell:')):
            user_input = user_input.replace(p, '')
    return user_input.strip().strip('"\'')

def get_local_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith('127.'): return ip
    except: pass
    return "localhost"

def run_command(cmd, shell=True, timeout=10):
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def force_focus(hwnd):
    if not win32gui or not hwnd: return
    try:
        if win32gui.IsIconic(hwnd): win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
        win32gui.SetForegroundWindow(hwnd)
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
    except: pass

def get_all_roots(include_system=True):
    """Dynamically detect roots, prioritizing user directories."""
    home = Path.home()
    user_roots = []
    
    # 1. Primary User folders (OneDrive First)
    subdirs = ['Documents', 'Desktop', 'Downloads', 'Music', 'Videos', 'Pictures']
    for sd in subdirs:
        # Check OneDrive variations first (usually where active files are)
        for od_base in [home / 'OneDrive', home / 'OneDrive - Personal']:
            p_od = od_base / sd
            if p_od.exists(): user_roots.append(p_od)
        
        # Check standard home
        p = home / sd
        if p.exists(): user_roots.append(p)
            
    # 2. Fixed Drives (excluding C: root for speed)
    try:
        if platform.system() == "Windows":
            import string
            from ctypes import windll
            bitmask = windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drive = f"{letter}:\\"
                    if letter != 'C':
                        dtype = windll.kernel32.GetDriveTypeW(drive)
                        if dtype == 3: # FIXED
                            user_roots.append(Path(drive))
                bitmask >>= 1
    except: pass
    
    system_roots = []
    if include_system:
        system_roots = [
            Path("C:\\Program Files"),
            Path("C:\\Program Files (x86)"),
            home / 'AppData' / 'Local' / 'Programs'
        ]
    
    # Deduplicate while preserving order
    all_roots = user_roots + system_roots
    seen = set()
    return [x for x in all_roots if x.exists() and not (x in seen or seen.add(x))]

def delayed_focus(targets, delay=0.5):
    if isinstance(targets, str): targets = [targets]
    def worker():
        time.sleep(delay)
        if not win32gui: return
        def callback(hwnd, _):
            title = win32gui.GetWindowText(hwnd).lower()
            for t in targets:
                if t.lower() in title:
                    force_focus(hwnd)
                    return False
            return True
        win32gui.EnumWindows(callback, None)
    threading.Thread(target=worker, daemon=True).start()

def discover_target(target):
    # App discovery checks both user and system roots
    roots = get_all_roots(include_system=True)
    
    for root in roots:
        if not root.exists(): continue
        for name in [target, f"{target}.exe", f"{target}.lnk"]:
            path = root / name
            if path.exists(): return str(path)
            sub = root / target / name
            if sub.exists(): return str(sub)
    return None

def deep_search_file(filename, timeout=SEARCH_TIMEOUT):
    result = [None]
    def worker():
        # Document search skips slow system roots
        roots = get_all_roots(include_system=False)
        for root in roots:
            root_str = str(root)
            for dirpath, dirnames, filenames in os.walk(root_str):
                try:
                    depth = len(Path(dirpath).relative_to(root).parts)
                    if depth > MAX_SEARCH_DEPTH:
                        dirnames[:] = [] 
                        continue
                    for f in filenames:
                        if filename.lower() in f.lower():
                            result[0] = os.path.join(dirpath, f)
                            return
                except: continue
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout)
    return result[0]

def get_latest_file(folder_path):
    try:
        path = Path(folder_path)
        if not path.exists() or not path.is_dir():
            if str(folder_path).lower() == 'downloads': path = Path.home() / 'Downloads'
            elif str(folder_path).lower() == 'documents': path = Path.home() / 'Documents'
            elif str(folder_path).lower() == 'desktop': path = Path.home() / 'Desktop'
        
        if not path.exists(): return None
        files = [f for f in path.iterdir() if f.is_file()]
        if not files: return None
        return str(max(files, key=lambda f: f.stat().st_mtime))
    except: return None

def find_media(roots, tokens, depth=5):
    """Search for media files and return the BEST match based on token score and extension prioritization"""
    matches = [] # List of (path, score)
    
    # Define extension groups
    audio_video_exts = {'.mp4', '.mp3', '.mkv', '.avi', '.wav', '.mov', '.flac'}
    image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    
    # Check if user explicitly asked for an extension
    target_ext = next((t for t in tokens if t.startswith('.')), None)
    if not target_ext:
        # Check tokens that look like extensions but without dot
        all_exts = audio_video_exts.union(image_exts)
        for t in tokens:
            if f".{t}" in all_exts:
                target_ext = f".{t}"
                break

    for root in roots:
        root_str = str(root)
        for dirpath, dirnames, filenames in os.walk(root_str):
            try:
                rel_depth = len(Path(dirpath).relative_to(root).parts)
                if rel_depth > depth:
                    dirnames[:] = []
                    continue
                
                for f in filenames:
                    path = Path(os.path.join(dirpath, f))
                    ext = path.suffix.lower()
                    if ext not in audio_video_exts and ext not in image_exts:
                        continue
                    
                    name_only = path.stem.lower()
                    clean_name = re.sub(r'[\.\-_]', ' ', name_only)
                    
                    score = 0
                    for token in tokens:
                        # Skip if token is the extension part we extracted
                        if f".{token}" == target_ext or token == target_ext:
                            continue
                            
                        if token in clean_name:
                            score += 10 # Strong match
                        elif len(token) > 4 and any(token[:4] in word for word in clean_name.split()):
                            score += 5 # Prefix match
                    
                    # Extension matching bonus / penalty
                    if target_ext:
                        if ext == target_ext:
                            score += 20 # Massive bonus for exact extension
                        elif (target_ext in audio_video_exts and ext in image_exts) or \
                             (target_ext in image_exts and ext in audio_video_exts):
                            score -= 20 # Heavy penalty for cross-type matching
                    elif ext in audio_video_exts:
                        score += 2 # Slight priority for AV over images
                    
                    # Strict threshold: after penalty, must still be positive and significant
                    if score >= 10: 
                        matches.append((path, score))
                
                # If we have very high score matches in this root, we can stop searching deep
                if any(m[1] >= 25 for m in matches):
                    break

            except: continue
    
    if not matches:
        return None
        
    # Sort by score, then by recency
    matches.sort(key=lambda x: (x[1], x[0].stat().st_mtime if x[0].exists() else 0), reverse=True)
    return matches[0][0]

# --- Core Execution Handler ---

async def run_steps(steps):
    results = []
    for step in steps:
        action = step.get('action')
        target = step.get('target', '')
        text = step.get('text', '')
        if action == 'open_application' or action == 'open_file' or action == 'navigate_folder':
            res = await handle_execute(CommandRequest(command=target, intent='open_app'))
            results.append(res.get('data', f"Tried {action} {target}"))
        elif action == 'open_latest_file':
            folder = step.get('folder', target)
            latest = get_latest_file(folder)
            if latest:
                res = await handle_execute(CommandRequest(command=latest, intent='open_file'))
                results.append(f"Opened latest file in {folder}: {Path(latest).name}")
            else: results.append(f"No files in {folder}")
        elif action == 'type_text':
            pyautogui.write(text, interval=0.01)
            results.append(f"Typed: {text}")
        elif action == 'press_key':
            pyautogui.press(step.get('key', 'enter'))
            results.append(f"Pressed: {step.get('key', 'enter')}")
        elif action == 'wait':
            await asyncio.sleep(float(step.get('duration', 1)))
            results.append(f"Waited {step.get('duration')}s")
    return "\n".join([str(r) for r in results])

async def handle_execute(req: CommandRequest):
    try:
        command = req.command.strip()
        intent = req.intent.strip()
        metadata = req.metadata or {}
        mode = req.mode or "local"
        history = req.history or []
        
        logger.info(f"Incoming: {command} [Intent: {intent}]")
        memory_manager.update_context(last_command=command)

        if intent == 'greeting':
            greetings = [
                "Hello! I'm Nana. How's your system running today?",
                "Hi there! Ready to be productive?",
                "Greetings! What can I help you with?",
                "Nana here! Always at your service."
            ]
            import random
            return {"success": True, "data": random.choice(greetings)}

        # --- Multi-Step Detection ---
        connectors = [' and ', ' then ', ' and then ', ' and also ', ' then also ', ', then ']
        smart_keywords = ['latest', 'recent', 'newest', 'last one']
        action_keywords = ['type ', 'write ', 'click ', 'wait ', 'scroll ', 'press ']
        
        is_multi_step = any(conn in command.lower() for conn in connectors) or \
                        any(word in command.lower() for word in smart_keywords) or \
                        any(word in command.lower() for word in action_keywords)
        
        if is_multi_step and intent == 'unknown':
            try:
                session_context = memory_manager.get_context_summary()
                plan_json = await planner_agent.plan(command, session_context=session_context)
                plan = json.loads(plan_json)
                if 'steps' in plan and plan['steps']:
                    results = await run_steps(plan['steps'])
                    return {"success": True, "data": f"Done! Here's what I did:\n\n{results}", "is_workflow": True}
            except Exception as e:
                logger.error(f"Planner Error: {e}")

        if intent in ['open_app', 'open_folder', 'open_file', 'unknown']:
            target = sanitize_command_input(command)
            target_app = None
            
            # Smart "Open In" Parsing
            for connector in [" in ", " with ", " using "]:
                if connector in target.lower():
                    parts = target.lower().split(connector)
                    potential_target = parts[0].strip().strip('"\'')
                    app_name = parts[1].strip().strip('"\'')
                    
                    # Validate if the second part looks like an app we know
                    known_apps = ['vscode', 'vs code', 'code', 'notepad', 'sublime', 'word', 'excel', 'chrome', 'edge']
                    if any(a in app_name for a in known_apps):
                        target = potential_target
                        target_app = app_name
                        break

            # ... existing URI Map and Folder Map logic ...
            
            # Extended URI Map
            uri_map = {
                'netflix': 'netflix:', 'youtube': 'https://youtube.com', 'store': 'ms-windows-store:',
                'camera': 'microsoft.windows.camera:', 'clock': 'ms-clock:', 'photos': 'ms-photos:',
                'calendar': 'ms-calendar:', 'recycle bin': 'shell:RecycleBinFolder', 'settings': 'ms-settings:home',
                'edge': 'msedge:', 'outlook': 'outlookmail:', 'notepad': 'notepad.exe', 'calculator': 'calc.exe',
                'whatsapp': 'whatsapp:', 'task manager': 'taskmgr.exe', 'sticky notes': 'microsoft.microsoftstickynotes:',
                'chat gpt': 'https://chat.openai.com', 'perplexity': 'https://www.perplexity.ai'
            }
            
            # Common Folder Map
            folder_map = {
                'downloads': str(Path.home() / 'Downloads'),
                'documents': str(Path.home() / 'Documents'),
                'desktop': str(Path.home() / 'Desktop'),
                'music': str(Path.home() / 'Music'),
                'pictures': str(Path.home() / 'Pictures'),
                'videos': str(Path.home() / 'Videos'),
                'home': str(Path.home())
            }

            clean = target.lower().replace('folder','').strip()
            
            # 1. Check URI Map
            if clean in uri_map:
                uri = uri_map[clean]
                if uri.startswith('http'): webbrowser.open(uri)
                else: os.startfile(uri)
                delayed_focus(target)
                await sio.emit('app_opened', {'app': target})
                return {"success": True, "data": f"Opening {target} 🚀", "intent": "open_app"}

            # 2. Check Folder Map
            if clean in folder_map:
                path = folder_map[clean]
                os.startfile(path)
                await sio.emit('app_opened', {'app': clean})
                return {"success": True, "data": f"Opening {clean} folder 📂", "intent": "open_folder"}

            # 3. Discovery / Deep Search
            path = discover_target(target) or deep_search_file(target)
            if path:
                # App-Specific Logic (VS Code / Notepad etc)
                if target_app:
                    if any(x in target_app.lower() for x in ['code', 'vscode', 'vs code']):
                        try:
                            logger.info(f"Opening {path} in VS Code")
                            subprocess.Popen(['code', str(path)], shell=True)
                            return {"success": True, "data": f"Opened {os.path.basename(path)} in VS Code 💻"}
                        except Exception as e:
                            logger.error(f"Failed to open in VS Code: {e}")
                    
                    if 'notepad' in target_app.lower():
                        subprocess.Popen(['notepad.exe', str(path)])
                        return {"success": True, "data": f"Opened {os.path.basename(path)} in Notepad 📝"}

                # Default Opening
                os.startfile(path)
                basename = os.path.basename(path).split('.')[0]
                delayed_focus(basename)
                await sio.emit('app_opened', {'app': basename})
                return {"success": True, "data": f"Opened {os.path.basename(path)}", "intent": intent if intent != 'unknown' else 'open_file'}
            
            if intent != 'unknown':
                # Try to launch as general command if specific search failed
                try:
                    if target_app and any(x in target_app.lower() for x in ['code', 'vscode', 'vs code']):
                        subprocess.Popen(['code', target], shell=True)
                        return {"success": True, "data": f"Launched {target} in VS Code"}
                    os.startfile(target)
                    return {"success": True, "data": f"Launched {target}", "intent": "open_app"}
                except:
                    return {"success": False, "data": f"Could not find or open {target}", "intent": intent}

        if intent == 'close_app':
            target = sanitize_command_input(command).lower().strip()
            
            # Friendly mapping for common apps with non-obvious process names
            kill_map = {
                'media player': 'Microsoft.Media.Player.exe',
                'chrome': 'chrome.exe',
                'browser': 'chrome.exe',
                'edge': 'msedge.exe',
                'notepad': 'notepad.exe',
                'calculator': 'calc.exe',
                'calc': 'calc.exe',
                'task manager': 'taskmgr.exe',
                'spotify': 'Spotify.exe',
                'discord': 'Discord.exe',
                'whatsapp': 'WhatsApp.exe',
                'terminal': 'WindowsTerminal.exe'
            }
            
            process_to_kill = kill_map.get(target, target)
            if '.' not in process_to_kill:
                process_to_kill += '.exe'
                
            logger.info(f"Attempting to close: {process_to_kill}")
            
            # Try graceful close first if possible, otherwise force kill
            cmd = f'taskkill /IM "{process_to_kill}" /F'
            stdout, stderr, code = run_command(cmd)
            
            if code == 0:
                return {"success": True, "data": f"Closed {target} successfully. 🛑"}
            
            # Fallback: Try to find a process that contains the target name
            logger.info(f"Fallback: Searching for processes related to '{target}'")
            ps_find = f'powershell -Command "Get-Process | Where-Object {{ $_.Name -like \'*{target}*\' -or $_.MainWindowTitle -like \'*{target}*\' }} | Select-Object -ExpandProperty Name -ErrorAction SilentlyContinue"'
            out, _, _ = run_command(ps_find)
            
            found_processes = list(set([p.strip() for p in out.splitlines() if p.strip()]))
            if found_processes:
                success_count = 0
                for p in found_processes:
                    if not p.lower().endswith('.exe'): p += '.exe'
                    _, _, c = run_command(f'taskkill /IM "{p}" /F')
                    if c == 0: success_count += 1
                
                if success_count > 0:
                    return {"success": True, "data": f"Found and closed {success_count} processes related to '{target}'. 🛑"}
            
            # Final Error
            if "not found" in stderr.lower():
                return {"success": False, "data": f"I couldn't find a running process for '{target}'.", "intent": "close_app"}
            return {"success": False, "data": f"Failed to close {target}: {stderr}", "intent": "close_app"}

        if intent == 'get_local_ip':
            ip = get_local_ip()
            return {
                "success": True,
                "data": f"📱 **Nana 2.0 Production Link**\n\n- PC IP: `{ip}`\n- Interface: [https://{ip}:5173](https://{ip}:5173)\n- Remote Control: [http://{ip}:{BACKEND_PORT}/remote?token={REMOTE_TOKEN}](http://{ip}:{BACKEND_PORT}/remote?token={REMOTE_TOKEN})\n\n*(Note: Accepted ports 3001 & 5173 in Firewall)*"
            }

        if intent == 'power_management':
            action = command.strip().lower()
            if action in ALLOWED_COMMANDS:
                run_command(ALLOWED_COMMANDS[action])
                return {"success": True, "data": f"Executing {action}..."}
            return {"success": False, "data": f"Unknown power action: {action}"}

        if intent == 'minimize_window':
            target = command.strip().lower()
            if not target:
                hwnd = win32gui.GetForegroundWindow()
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                return {"success": True, "data": "Minimized the active window. 📉", "intent": intent}
            
            # Find window by title or class
            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd) and target in win32gui.GetWindowText(hwnd).lower():
                    windows.append(hwnd)
            
            matching_windows = []
            win32gui.EnumWindows(callback, matching_windows)
            
            if matching_windows:
                for hwnd in matching_windows:
                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                return {"success": True, "data": f"Minimized windows matching '{target}'. 📉", "intent": intent}
            
            # Final Fallback: If target is just the keyword itself, it means active window
            if target in ['minimize', 'minimum']:
                hwnd = win32gui.GetForegroundWindow()
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                return {"success": True, "data": "Minimized the active window. 📉", "intent": intent}

            return {"success": False, "data": f"Could not find a window matching '{target}'.", "intent": intent}

        if intent == 'maximize_window':
            target = command.strip().lower()
            if not target:
                hwnd = win32gui.GetForegroundWindow()
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                return {"success": True, "data": "Maximized the active window. 📈", "intent": intent}
            
            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd) and target in win32gui.GetWindowText(hwnd).lower():
                    windows.append(hwnd)
            
            matching_windows = []
            win32gui.EnumWindows(callback, matching_windows)
            
            if matching_windows:
                for hwnd in matching_windows:
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                return {"success": True, "data": f"Maximized windows matching '{target}'. 📈", "intent": intent}

            if target in ['maximize', 'maximum']:
                hwnd = win32gui.GetForegroundWindow()
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                return {"success": True, "data": "Maximized the active window. 📈", "intent": intent}

            return {"success": False, "data": f"Could not find a window matching '{target}'.", "intent": intent}

        if intent == 'restore_window':
            target = command.strip().lower()
            def callback(hwnd, windows):
                if target in win32gui.GetWindowText(hwnd).lower():
                    windows.append(hwnd)
            
            matching_windows = []
            win32gui.EnumWindows(callback, matching_windows)
            
            if matching_windows:
                for hwnd in matching_windows:
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                return {"success": True, "data": f"Restored windows matching '{target}'. 🗔", "intent": intent}
            return {"success": False, "data": f"Could not find a window matching '{target}'.", "intent": intent}

        if intent == 'minimize_all':
            pyautogui.hotkey('win', 'd')
            return {"success": True, "data": "Showing Desktop. 🖥️", "intent": intent}

        if intent == 'sys_health':
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            battery = psutil.sensors_battery()
            
            health_report = [
                "📊 **Nana System Health Dashboard**",
                f"- **CPU Usage**: `{cpu}%` ⚡",
                f"- **RAM**: `{ram.percent}%` used (`{ram.available / (1024**3):.1f} GB` free) 🧠",
            ]
            
            if battery:
                plugged = "PLUGGED IN" if battery.power_plugged else "BATTERY"
                health_report.append(f"- **Battery**: `{battery.percent}%` ({plugged}) 🔋")
            
            # Simple Disk check for C:
            disk = psutil.disk_usage('C:')
            health_report.append(f"- **Disk (C:)**: `{disk.percent}%` used (`{disk.free / (1024**3):.1f} GB` free) 💾")
            
            return {"success": True, "data": "\n".join(health_report), "intent": intent}

        if intent == 'set_volume':
            if not AudioUtilities:
                return {"success": False, "data": "Audio control (pycaw) not installed."}
            
            try:
                val = command.strip().lower()
                devices = AudioUtilities.GetSpeakers()
                volume = devices.EndpointVolume
                
                if val == 'mute':
                    volume.SetMute(1, None)
                    return {"success": True, "data": "Muted system volume 🔇"}
                elif val == 'unmute':
                    volume.SetMute(0, None)
                    return {"success": True, "data": "Unmuted system volume 🔊"}
                else:
                    level = int(re.search(r'\d+', val).group())
                    level = max(0, min(100, level)) # Clamp 0-100
                    volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                    return {"success": True, "data": f"Set volume to **{level}%** 🔊"}
            except Exception as e:
                return {"success": False, "data": f"Failed to set volume: {e}"}

        if intent == 'set_brightness':
            if not sbc:
                return {"success": False, "data": "Brightness control not installed."}
            try:
                level = int(re.search(r'\d+', command).group())
                level = max(0, min(100, level))
                sbc.set_brightness(level)
                return {"success": True, "data": f"Set brightness to **{level}%** 💡"}
            except Exception as e:
                return {"success": False, "data": f"Failed to set brightness: {e}"}

        if intent == 'list_apps':
            ps_cmd = 'powershell -Command "Get-Process | Where-Object { $_.MainWindowTitle } | Select-Object Name, MainWindowTitle | ConvertTo-Json"'
            stdout, _, code = run_command(ps_cmd)
            if code == 0 and stdout.strip():
                try:
                    processes = json.loads(stdout)
                    if isinstance(processes, dict): processes = [processes]
                    app_list = [f"• **{p['Name']}** ({p['MainWindowTitle']})" for p in processes if p.get('MainWindowTitle')]
                    return {"success": True, "data": "Active apps:\n\n" + "\n".join(app_list)}
                except: pass
            return {"success": True, "data": "No major apps found."}

        if intent == 'play_local_media':
            raw_query = command.lower().strip()
            tokens = [t for t in re.split(r'[\s\.\-_]+', raw_query) if len(t) > 2]
            if not tokens: tokens = [t for t in re.split(r'[\s\.\-_]+', raw_query) if t]

            search_roots = get_all_roots()
            
            found = find_media(search_roots, tokens)
            if found:
                try:
                    if os.path.exists(found):
                        os.startfile(found)
                        delayed_focus([found.stem, "Media Player", "VLC"])
                        return {"success": True, "data": f"Playing **{found.name}**! 🎬"}
                    else:
                        raise FileNotFoundError(f"Selected media file no longer exists: {found}")
                except Exception as e:
                    logger.error(f"Play media error: {e}")
                    return {"success": False, "data": f"Found the file but couldn't play it: {e}"}
            else:
                return {
                    "success": False, 
                    "data": f"Couldn't find media matching '{raw_query}'. Try searching YouTube?"
                }

        if intent == 'media_control':
            cmd = command.lower().strip()
            if any(x in cmd for x in ['play', 'pause', 'resume']):
                pyautogui.press('playpause')
                return {"success": True, "data": "Toggled Play/Pause ⏯️"}
            if any(x in cmd for x in ['next', 'skip']):
                pyautogui.press('nexttrack')
                return {"success": True, "data": "Skipped to next track ⏭️"}
            if any(x in cmd for x in ['prev', 'back', 'last', 'preview']):
                pyautogui.press('prevtrack')
                return {"success": True, "data": "Went to previous track ⏮️"}
            if 'stop' in cmd:
                pyautogui.press('stoptrack')
                return {"success": True, "data": "Stopped media ⏹️"}
            return {"success": False, "data": f"Unknown media command: {command}"}

        if intent == 'search_on_youtube':
            # Extract query if command is just the intent trigger or full command
            query = command.replace('youtube', '').strip()
            url = f"https://www.youtube.com/results?search_query={query}"
            webbrowser.open(url)
            return {"success": True, "data": f"Searching YouTube for {query}..."}

        if intent == 'search_on_google':
            query = command.replace('google', '').strip()
            url = f"https://www.google.com/search?q={query}"
            webbrowser.open(url)
            return {"success": True, "data": f"Searching Google for {query}..."}

        if intent == 'read_clipboard':
            stdout, _, code = run_command('powershell -Command "Get-Clipboard"')
            if code == 0:
                content = stdout.strip()
                return {"success": True, "data": f"Clipboard content:\n\n```\n{content}\n```"}
            return {"success": False, "data": "Could not read clipboard."}

        if intent == 'copy_to_clipboard':
            text = metadata.get('text', command)
            escaped = text.replace("'", "''")
            cmd = f"powershell -Command \"Set-Clipboard -Value '{escaped}'\""
            run_command(cmd)
            return {"success": True, "data": "Copied to clipboard! 📋"}

        if intent == 'write_file':
            filename = metadata.get('filename', command)
            content = metadata.get('content', '')
            if not filename: return {"success": False, "data": "Filename missing."}
            
            # Smart Folder Selection: Prefer OneDrive Documents if it exists
            home = Path.home()
            docs_path = home / 'Documents'
            onedrive_docs = home / 'OneDrive' / 'Documents'
            if onedrive_docs.exists(): docs_path = onedrive_docs
            
            path = docs_path / sanitize_command_input(filename)
            if not path.suffix: path = path.with_suffix('.txt')
            
            if path.suffix not in ALLOWED_FILE_EXTENSIONS:
                 return {"success": False, "data": f"Extension {path.suffix} not allowed."}
                 
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8')
                memory_manager.update_context(last_file=str(path))
                return {"success": True, "data": f"Saved {path.name} to Documents! 💾"}
            except Exception as e:
                return {"success": False, "data": f"Write failed: {e}"}

        if intent == 'delete_file':
            filename = metadata.get('filename', command)
            clean = sanitize_command_input(filename)
            path = discover_target(clean) or deep_search_file(clean)
            
            if path:
                try:
                    p = Path(path)
                    if p.is_dir(): shutil.rmtree(p)
                    else: p.unlink()
                    return {"success": True, "data": f"Deleted {p.name} 🗑️"}
                except Exception as e:
                    return {"success": False, "data": f"Delete failed: {e}"}
            return {"success": False, "data": f"Could not find {filename} to delete."}

        # Fallback to AI Coordinator
        try:
            session_context = memory_manager.get_context_summary()
            result = await coordinator.run_workflow(command)
            response = result.get('final_data', 'Task completed!')
            
            local_ip = get_local_ip()
            remote_url = f"http://{local_ip}:{BACKEND_PORT}/remote?token={REMOTE_TOKEN}"
            
            return {
                "success": True, 
                "data": f"{response}\n\n📱 **Remote Control Active:** [Open on Phone]({remote_url})",
                "remote_url": remote_url
            }
        except Exception as e:
            logger.error(f"AI Error: {e}")
            return {"success": False, "data": f"Error: {e}"}

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        logger.error(f"Critical Backend Error:\n{error_msg}")
        return {"success": False, "data": f"Backend Error: {str(e)}"}

# --- Routes ---

@app.get("/")
async def root():
    return {"status": "Nana AI 2.0 Online", "ip": get_local_ip()}

@app.post("/api/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginRequest):
    """Authenticate user and return JWT token"""
    if not authenticate_user(credentials.username, credentials.password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": credentials.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 86400  # 24 hours in seconds
    }

@app.post("/api/execute")
@limiter.limit("100/minute")
async def api_execute(request: Request, req: CommandRequest, token: dict = Depends(verify_token)):
    """Execute command (requires authentication)"""
    return await handle_execute(req)

# --- Mount Static Files and Socket.IO (MUST be at the end) ---
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

if __name__ == "__main__":
    ip = get_local_ip()
    logger.info(f"Nana AI 2.0 Production starting on http://{ip}:{BACKEND_PORT}")
    uvicorn.run(socket_app, host="0.0.0.0", port=BACKEND_PORT, log_level="info")
