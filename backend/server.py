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
from planner_agent import PlannerAgent
from memory_manager import MemoryManager
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
    import win32clipboard
except ImportError:
    win32gui = None
    win32con = None
    win32api = None
    win32clipboard = None
    print("WARNING: pywin32 modules not fully installed. Some remote features will be degraded.")

app = Flask(__name__)
# Enable CORS for socket connection too
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Secure remote token from .env or fallback to random
REMOTE_TOKEN = os.getenv('REMOTE_TOKEN')
if not REMOTE_TOKEN:
    REMOTE_TOKEN = secrets.token_hex(16)
    print(f"!!! GENERATED RANDOM REMOTE CONTROL TOKEN: {REMOTE_TOKEN} !!!")
else:
    print(f"!!! PERSISTENT REMOTE CONTROL TOKEN LOADED !!!")

# Disable pyautogui failsafe and pause for faster mobile control
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

coordinator = MultiAgentCoordinator()
reasoning_agent = ReasoningAgent()
planner_agent = PlannerAgent()
memory_manager = MemoryManager()
LAST_OPENED_APP = None

# Configuration
BACKEND_PORT = int(os.getenv('BACKEND_PORT', 3001))
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FILE_EXTENSIONS = {'.txt', '.py', '.json', '.csv', '.md', '.log', '.js', '.html', '.css', '.pdf', '.docx'}
MAX_SEARCH_DEPTH = 3
SEARCH_TIMEOUT = 5  # seconds

# 🔐 SECURITY: Command Whitelist
ALLOWED_COMMANDS = {
    "sleep": 'powershell -Command "Add-Type -Assembly System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState(\'Suspend\', $false, $false)"',
    "shutdown": 'shutdown /s /t 10',
    "restart": 'shutdown /r /t 10',
    "lock": 'rundll32.exe user32.dll,LockWorkStation'
}

# Specialized Prompt for Structured Device Control
SYSTEM_COMMAND_PROMPT = """
You are a Windows desktop AI assistant.

Return ONLY JSON.

If user wants to control system (sleep, shutdown, restart, lock):
{{
  "action": "system",
  "command": "<associated shell command>"
}}

If user wants to open an app, file, or folder:
{{
  "action": "open",
  "target": "<name of app/file/folder>"
}}

If user asks a general question, conversational query, or needs complex reasoning:
{{
  "action": "suggest_ai",
  "reason": "That's a great question! I'm currently in Local Mode, designed to help you control your computer (opening apps, system actions, etc.). For general knowledge or creative tasks, would you like me to switch to my AI Brain?"
}}

If unclear:
{{
  "action": "none",
  "reason": "I'm not quite sure how to handle that in Local Mode. Try switching to my AI Brain for more complex requests!"
}}

VALID SYSTEM COMMANDS:
- Sleep: {sleep_cmd}
- Shutdown: {shutdown_cmd}
- Restart: {restart_cmd}
- Lock: {lock_cmd}
""".format(
    sleep_cmd=ALLOWED_COMMANDS["sleep"],
    shutdown_cmd=ALLOWED_COMMANDS["shutdown"],
    restart_cmd=ALLOWED_COMMANDS["restart"],
    lock_cmd=ALLOWED_COMMANDS["lock"]
)

def sanitize_command_input(user_input):
    """Sanitize user input to prevent command injection"""
    # Remove dangerous characters and patterns
    dangerous_patterns = [';', '&&', '||', '|', '`', '$', '(', ')', '<', '>', '&']
    sanitized = user_input
    for pattern in dangerous_patterns:
        if pattern in sanitized and not sanitized.startswith(('http://', 'https://', 'ms-', 'shell:')):
            sanitized = sanitized.replace(pattern, '')
    return sanitized.strip()

def get_local_ip():
    """Detect the local IP address of this machine, prioritizing WiFi/LAN adapters over virtual ones."""
    import socket
    try:
        # Strategy 1: The UDP connection trick (usually most accurate)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith('127.'):
            return ip
    except:
        pass
        
    try:
        # Strategy 2: Iterate over all interfaces (for offline environments)
        # We look for common private network ranges
        import os
        if platform.system() == 'Windows':
            # Fast way on windows to get real IPs
            output = subprocess.check_output("ipconfig", shell=True).decode('utf-8')
            ips = re.findall(r"IPv4 Address[.\s]*: ([\d.]+)", output)
            for ip in ips:
                if ip.startswith(('192.168.', '10.', '172.16.', '172.31.')):
                    return ip
            if ips: return ips[0]
    except:
        pass
        
    return "localhost"

def run_command(cmd, shell=True, timeout=10):
    """Execute a shell command and return output with timeout"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timeout - operation took too long", 1
    except FileNotFoundError:
        return "", "Command not found", 1
    except PermissionError:
        return "", "Permission denied", 1
    except Exception as e:
        return "", f"Error executing command: {str(e)}", 1

def read_pdf(filepath):
    """Extract text from a PDF file"""
    if not PdfReader:
        return "PDF Reader not installed. Run: pip install PyPDF2"
    try:
        path = Path(filepath)
        # Check file size
        if path.stat().st_size > MAX_FILE_SIZE:
            return f"PDF file too large (max {MAX_FILE_SIZE // (1024*1024)}MB)"
        
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages[:10]:  # Limit to first 10 pages
            text += page.extract_text() or ""
        return text[:8000]  # Limit output size
    except FileNotFoundError:
        return f"Error: PDF file not found at {filepath}"
    except PermissionError:
        return f"Error: Permission denied to read {filepath}"
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def read_docx(filepath):
    """Extract text from a DOCX file"""
    if not Document:
        return "DOCX Reader not installed. Run: pip install python-docx"
    try:
        path = Path(filepath)
        # Check file size
        if path.stat().st_size > MAX_FILE_SIZE:
            return f"DOCX file too large (max {MAX_FILE_SIZE // (1024*1024)}MB)"
        
        doc = Document(filepath)
        text = "\n".join([para.text for para in doc.paragraphs[:50]])  # Limit to 50 paragraphs
        return text[:8000]  # Limit output size
    except FileNotFoundError:
        return f"Error: DOCX file not found at {filepath}"
    except PermissionError:
        return f"Error: Permission denied to read {filepath}"
    except Exception as e:
        return f"Error reading DOCX: {str(e)}"

def read_file_content(filepath):
    """Read content based on file extension with validation"""
    try:
        path = Path(filepath)
        # Validate file exists
        if not path.exists():
            return f"Error: File not found at {filepath}"
        
        # Check file size
        if path.stat().st_size > MAX_FILE_SIZE:
            return f"File too large (max {MAX_FILE_SIZE // (1024*1024)}MB)"
        
        # Get file extension
        ext = Path(filepath).suffix.lower()
        
        # Update memory
        memory_manager.update_context(last_file=filepath, last_command=f"Read file {Path(filepath).name}")
        
        # Validate extension
        if ext not in ALLOWED_FILE_EXTENSIONS:
            return f"Unsupported file type: {ext}"
        
        if ext in [".txt", ".py", ".json", ".csv", ".md", ".log", ".js", ".html", ".css"]:
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read(8000)  # Limit to 8KB
            except PermissionError:
                return f"Error: Permission denied to read {filepath}"
            except Exception as e:
                return f"Error reading file: {str(e)}"
        elif ext == ".pdf":
            return read_pdf(filepath)
        elif ext == ".docx":
            return read_docx(filepath)
        
        return "Unsupported file format"
    except Exception as e:
        return f"Error processing file: {str(e)}"

def discover_target(target):
    """Search for a target app or file in common Windows locations using pathlib"""
    program_files = Path(os.environ.get('ProgramFiles', 'C:\\Program Files'))
    program_files_x86 = Path(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'))
    local_app_data = Path(os.environ.get('LocalAppData', f"C:\\Users\\{os.getlogin()}\\AppData\\Local"))
    user_profile = Path(os.environ.get('USERPROFILE', f"C:\\Users\\{os.getlogin()}"))
    
    common_roots = [
        program_files,
        program_files_x86,
        user_profile / 'Desktop',
        user_profile / 'Documents',
        local_app_data / 'Programs'
    ]
    
    # Try common formats
    search_names = [target, f"{target}.exe", f"{target}.lnk"]
    
    for root in common_roots:
        if not root.exists(): continue
        for name in search_names:
            path = root / name
            if path.exists():
                return str(path)
            # Check one level deeper for folders (e.g., C:\Program Files\App\App.exe)
            sub_path = root / target / name
            if sub_path.exists():
                return str(sub_path)
            
    local_path = Path.cwd() / target
    if local_path.exists():
        return str(local_path)
        
    return None

def deep_search_file(filename, timeout=SEARCH_TIMEOUT):
    """Walk the user's home directory to find a file with timeout protection using pathlib"""
    user_home = Path.home()
    search_dirs = [
        user_home / 'Documents',
        user_home / 'Desktop',
        user_home / 'Downloads',
        user_home / 'Pictures',
        user_home / 'Videos'
    ]
    
    # Sanitize filename
    filename = sanitize_command_input(filename).lower()
    
    try:
        result = [None]
        
        def search_worker():
            for base in search_dirs:
                if not base.exists():
                    continue
                try:
                    # Using glob for faster/cleaner pattern matching
                    # We look for files containing the filename (smart match)
                    # Limit depth manually or use a generator
                    for path in base.rglob('*'):
                        # Check depth to prevent infinite recursion/performance hit
                        try:
                            depth = len(path.relative_to(base).parts)
                            if depth > MAX_SEARCH_DEPTH:
                                continue
                            
                            # Skip hidden/system directories
                            if any(part.startswith('.') or part in ['$RECYCLE.BIN', 'System Volume Information'] for part in path.parts):
                                continue
                                
                            if path.is_file() and filename in path.name.lower():
                                result[0] = str(path)
                                return
                        except ValueError:
                            continue
                except PermissionError:
                    continue
                except Exception:
                    continue
        
        search_thread = threading.Thread(target=search_worker, daemon=True)
        search_thread.start()
        search_thread.join(timeout=timeout)
        
        return result[0]
    except Exception as e:
        print(f"Search error: {e}")
        return None

def get_latest_file(folder_path):
    """Find the most recently modified file in a given folder Path or string"""
    try:
        path = Path(folder_path)
        if not path.exists() or not path.is_dir():
            # Try to resolve common names
            if str(folder_path).lower() == 'downloads':
                path = Path.home() / 'Downloads'
            elif str(folder_path).lower() == 'documents':
                path = Path.home() / 'Documents'
            elif str(folder_path).lower() == 'desktop':
                path = Path.home() / 'Desktop'
        
        if not path.exists():
            return None
            
        files = [f for f in path.iterdir() if f.is_file()]
        if not files:
            return None
            
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        return str(latest_file)
    except Exception as e:
        print(f"DEBUG: get_latest_file failed: {e}")
        return None

def force_focus(hwnd):
    """Aggressively bring a window to the front"""
    if not win32gui or not hwnd:
        return
    try:
        # 1. Restore if minimized
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        
        # 2. Bypass Foreground Lock Timeout (The "ALT" trick)
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
        win32gui.SetForegroundWindow(hwnd)
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
        
        # 3. Ensure visible
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    except AttributeError as e:
        print(f"Win32 module not available: {e}")
    except Exception as e:
        print(f"Focus Error: {e}")

def focus_window_native(target_name):
    """Use native win32gui to find and focus a window. Returns True if found."""
    if not win32gui: return False
    
    found = [False]
    def callback(hwnd, extra):
        title = win32gui.GetWindowText(hwnd).lower()
        if target_name.lower() in title:
            force_focus(hwnd)
            found[0] = True
            return False
        return True
    
    win32gui.EnumWindows(callback, None)
    return found[0]

def delayed_focus(target_names, delay=0.5, retries=10, interval=0.5):
    """Run native focus in a background thread with multiple retries"""
    if isinstance(target_names, str):
        target_names = [target_names]
        
    def worker():
        time.sleep(delay)
        for _ in range(retries):
            for name in target_names:
                if focus_window_native(name):
                    print(f"DEBUG: Successfully focused {name}")
                    return # Exit worker once any target is focused
            time.sleep(interval)
            
    threading.Thread(target=worker, daemon=True).start()

# --- SocketIO Remote Control Handlers ---

@socketio.on('connect')
def handle_connect(auth=None):
    token = request.args.get('token')
    print(f"DEBUG: Remote connection attempt with token: {token}")
    if token != REMOTE_TOKEN:
        print(f"ERROR: Token mismatch! Expected {REMOTE_TOKEN}, got {token}")
        return False
    print("Remote control connected successfully.")
    emit('status', {'connected': True})
    # Sync current state
    if LAST_OPENED_APP:
        emit('app_opened', {'app': LAST_OPENED_APP})

@socketio.on('mouse_move')
def handle_mouse_move(data):
    dx = int(data.get('dx', 0))
    dy = int(data.get('dy', 0))
    
    try:
        if win32api:
            # Use native win32api for direct, zero-lag movement
            x, y = win32api.GetCursorPos()
            win32api.SetCursorPos((x + dx, y + dy))
        else:
            pyautogui.moveRel(dx, dy, _pause=False)
    except Exception as e:
        print(f"ERROR: Mouse move failed: {e}")

@socketio.on('mouse_click')
def handle_mouse_click(data):
    button = data.get('button', 'left')
    print(f"DEBUG: Mouse click: {button}")
    pyautogui.click(button=button)

@socketio.on('mouse_scroll')
def handle_mouse_scroll(data):
    direction = data.get('direction', 'down')
    clicks = -10 if direction == 'down' else 10
    pyautogui.scroll(clicks)

@socketio.on('type_text')
def handle_type_text(data):
    text = data.get('text', '')
    if text:
        print(f"DEBUG: Remote typing: {text}")
        try:
            # Use native Windows clipboard for instant and accurate 'typing'
            if win32clipboard:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
                
                # Trigger Ctrl+V to paste
                pyautogui.hotkey('ctrl', 'v')
            else:
                pyautogui.write(text)
        except Exception as e:
            print(f"DEBUG: Clipboard paste failed ({e}). Falling back to typing...")
            pyautogui.write(text)

@socketio.on('key_press')
def handle_key_press(data):
    key = data.get('key', '')
    if key:
        mapping = {
            'win': 'win',
            'enter': 'enter',
            'backspace': 'backspace',
            'tab': 'tab',
            'esc': 'esc',
            'ctrl': 'ctrl',
            'alt': 'alt',
            'space': 'space'
        }
        actual_key = mapping.get(key.lower(), key.lower())
        pyautogui.press(actual_key)

# Serve Remote UI
@app.route('/remote')
def remote_ui():
    token = request.args.get('token')
    if token != REMOTE_TOKEN:
        return "Unauthorized", 401
    from flask import render_template
    return render_template('remote.html')

# --- Existing App Implementation ---

def get_ai_summarization(content):
    """Use Gemini to summarize the file content"""
    try:
        from google import genai
        from agents import client
        
        # Limit content size for API
        content_preview = content[:2000] if len(content) > 2000 else content
        
        prompt = f"Analyze and summarize this file content clearly and simply for the user. Keep it informative but concise:\n\n{content_preview}"
        
        response = client.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=prompt
        )
        return response.text.strip()
    except ImportError:
        return "(AI summarization unavailable - check API configuration)"
    except Exception as e:
        return f"(Could not summarize: {str(e)})"

def run_steps(steps):
    """Execute a series of atomic steps from the Task Planner"""
    results = []
    for step in steps:
        action = step.get('action')
        target = step.get('target', '')
        text = step.get('text', '')
        duration = step.get('duration', 0)
        
        if action == 'open_application':
            # Reuse existing logic via a simulated request if needed, or extract logic
            # For simplicity, we'll wrap the core logic.
            res = execute_core('open_app', target)
            memory_manager.update_context(app_name=target, last_command=f"Planned: Open {target}")
            results.append(res)
        elif action == 'navigate_folder':
            res = execute_core('open_folder', target)
            memory_manager.update_context(last_folder=target, last_command=f"Planned: Navigate to {target}")
            results.append(res)
        elif action == 'search_file':
            path = deep_search_file(target)
            if path:
                memory_manager.update_context(last_file=path, last_command=f"Planned: Search for {target}")
            results.append(f"Search for '{target}': Found {path if path else 'nothing'}")
        elif action == 'open_file':
            res = execute_core('open_file', target)
            memory_manager.update_context(last_file=target, last_command=f"Planned: Open file {target}")
            results.append(res)
        elif action == 'open_latest_file':
            folder = step.get('folder', target)
            latest = get_latest_file(folder)
            if latest:
                res = execute_core('open_file', latest)
                results.append(f"Opened latest file in {folder}: {Path(latest).name}")
            else:
                results.append(f"Could not find any files in {folder}")
        elif action == 'type_text':
            # Safety: Ensure the correct app is focused with retries
            current_app = memory_manager.active_app_name
            focused = True
            if current_app:
                focused = memory_manager.verify_focus(current_app)
                if not focused:
                    # Attempt activation and re-verify
                    memory_manager.activate_app(current_app)
                    focused = memory_manager.verify_focus(current_app)
            
            if focused:
                handle_type_text({'text': text})
                memory_manager.update_context(last_command=f"Planned: Typed '{text}'")
                results.append(f"Typed: {text}")
            else:
                results.append(f"Warning: Focus verification failed for {current_app}. Typing anyway...")
                handle_type_text({'text': text})
        elif action == 'press_key':
            # Safety Check
            current_app = memory_manager.active_app_name
            focused = True
            if current_app:
                focused = memory_manager.verify_focus(current_app)
                if not focused:
                    memory_manager.activate_app(current_app)
                    focused = memory_manager.verify_focus(current_app)
                
            pyautogui.press(step.get('key', 'enter'))
            memory_manager.update_context(last_command=f"Planned: Pressed key {step.get('key', 'enter')}")
            results.append(f"Pressed key: {step.get('key', 'enter')}")
        elif action == 'switch_to_app':
            if memory_manager.activate_app(target):
                memory_manager.update_context(app_name=target, last_command=f"Planned: Switched focus to {target}")
                results.append(f"Switched to {target}")
            else:
                results.append(f"Could not find or focus window: {target}")
        elif action == 'click':
            # Safety Check
            current_app = memory_manager.active_app_name
            focused = True
            if current_app:
                focused = memory_manager.verify_focus(current_app)
                if not focused:
                    memory_manager.activate_app(current_app)
                    focused = memory_manager.verify_focus(current_app)

            handle_mouse_click({'button': step.get('button', 'left')})
            memory_manager.update_context(last_command=f"Planned: Clicked {step.get('button', 'left')} mouse")
            results.append("Clicked mouse")
        elif action == 'move_mouse':
            handle_mouse_move({'dx': step.get('dx', 0), 'dy': step.get('dy', 0)})
            results.append("Moved mouse")
        elif action == 'wait':
            time.sleep(float(duration))
            results.append(f"Waited {duration}s")
            
    return "\n".join([str(r) for r in results])

def execute_core(intent, command, metadata={}):
    """Helper for internal execution of single intents without HTTP dependencies"""
    if intent == 'open_app' or intent == 'open_folder' or intent == 'open_file':
        target = sanitize_command_input(command)
        
        uri_map = {
            'netflix': 'netflix:',
            'youtube': 'https://youtube.com',
            'microsoft store': 'ms-windows-store:',
            'store': 'ms-windows-store:',
            'camera': 'microsoft.windows.camera:',
            'clock': 'ms-clock:',
            'photos': 'ms-photos:',
            'calendar': 'ms-calendar:',
            'recycle bin': 'shell:RecycleBinFolder',
            'settings': 'ms-settings:home',
            'edge': 'msedge:',
            'outlook': 'outlookmail:',
            'notepad': 'notepad.exe',
            'calculator': 'calc.exe',
            'task manager': 'taskmgr.exe',
            'sticky notes': 'explorer.exe shell:appsFolder\\Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe!App'
        }

        clean_target = target.lower().replace('folder', '').strip()
        if clean_target in uri_map:
            uri = uri_map[clean_target]
            try:
                if uri.startswith(('http', 'www')):
                    import webbrowser
                    webbrowser.open(uri)
                else:
                    os.startfile(uri)
                return f"Opened URI: {target}"
            except Exception as e:
                return f"Failed to open URI: {e}"

        path = discover_target(target) or deep_search_file(target)
        if path:
            try:
                os.startfile(path)
                return f"Successfully opened {os.path.basename(path)}"
            except Exception as e:
                return f"Error opening path: {e}"
        return f"Could not find or open '{target}'"
    
    return f"Intent '{intent}' not yet supported in planner core."

@app.route('/api/execute', methods=['POST'])
def execute():
    global LAST_OPENED_APP
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'data': 'Invalid request - no data provided'}), 400
        
        command = data.get('command', '').strip()
        intent = data.get('intent', '').strip()
        metadata = data.get('metadata', {})
        mode = data.get('mode', 'local')
        
        # Update memory with the raw command
        memory_manager.update_context(last_command=command)
        
        # Validate input length
        if len(command) > 1000:
            return jsonify({'success': False, 'data': 'Command too long (max 1000 characters)'}), 400

        # --- MULTI-STEP TASK PLANNER LOGIC ---
        # Detect if this is likely a multi-step command or a descriptive "smart" command
        connectors = [' and ', ' then ', ' and then ', ' and also ', ' then also ', ', then ']
        smart_keywords = ['latest', 'recent', 'newest', 'last one']
        action_keywords = ['type ', 'write ', 'click ', 'wait ', 'scroll ', 'press ']
        
        is_multi_step = any(conn in command.lower() for conn in connectors) or \
                        any(word in command.lower() for word in smart_keywords) or \
                        any(word in command.lower() for word in action_keywords) or \
                        (len(command) > 50 and intent == 'unknown')
        
        if is_multi_step:
            try:
                # Inject session context into the planning process
                session_context = memory_manager.get_context_summary()
                plan_json = planner_agent.plan(command, session_context=session_context)
                plan = json.loads(plan_json)
                
                if 'steps' in plan and plan['steps']:
                    # Let the user know we are starting a multi-step task
                    results_text = run_steps(plan['steps'])
                    
                    return jsonify({
                        'success': True,
                        'data': f"I've completed your request! Here's what I did:\n\n{results_text}",
                        'is_workflow': True,
                        'steps': plan['steps']
                    })
                else:
                    pass # Fall back to single-step execution
            except Exception as e:
                # Fall through to single-step logic as safety fallback
                pass
        
        # --- SINGLE-STEP INTENT LOGIC ---

        if intent == 'open_app' or intent == 'open_folder' or intent == 'open_file':
            target = sanitize_command_input(command)
        
            uri_map = {
                'netflix': 'netflix:',
                'youtube': 'https://youtube.com',
                'microsoft store': 'ms-windows-store:',
                'store': 'ms-windows-store:',
                'camera': 'microsoft.windows.camera:',
                'clock': 'ms-clock:',
                'photos': 'ms-photos:',
                'calendar': 'ms-calendar:',
                'calander': 'ms-calendar:',
                'recycle bin': 'shell:RecycleBinFolder',
                'settings': 'ms-settings:home',
                'whatsapp': 'whatsapp:',
                'xbox': 'xbox:',
                'edge': 'msedge:',
                'outlook': 'outlookmail:',
                'chat gpt': 'https://chat.openai.com',
                'perplexity': 'https://www.perplexity.ai',
                'openrouter': 'https://openrouter.ai',
                'canva': 'https://www.canva.com',
                'upwork': 'https://www.upwork.com',
                'grok': 'https://grok.com'
            }
    
            clean_target = target.lower().replace('folder', '').strip()
            if clean_target in uri_map:
                uri = uri_map[clean_target]
                try:
                    if uri.startswith(('http', 'www')):
                        import webbrowser
                        webbrowser.open(uri)
                    else:
                        os.startfile(uri)
                except Exception as e:
                    print(f"DEBUG: URI Launch failed: {e}")
                
                delayed_focus(target)
                msg = f"Opening **{target}** right now! 🚀"
                
                # Register in session memory
                memory_manager.update_context(app_name=target, last_command=f"Opened URI {target}")
                
                # Trigger Mobile UI for URI maps as well
                LAST_OPENED_APP = target
                socketio.emit('app_opened', {'app': target})
                local_ip = get_local_ip()
                remote_url = f"http://{local_ip}:{BACKEND_PORT}/remote?token={REMOTE_TOKEN}"
                
                return jsonify({
                    'success': True, 
                    'data': f"{msg}\n\n📱 **Remote Control Active:** [Open on Phone]({remote_url})",
                    'remote_url': remote_url
                })

            folder_map = {
                'downloads': os.path.join(os.path.expanduser('~'), 'Downloads'),
                'documents': os.path.join(os.path.expanduser('~'), 'Documents'),
                'desktop': os.path.join(os.path.expanduser('~'), 'Desktop'),
                'music': os.path.join(os.path.expanduser('~'), 'Music'),
                'pictures': os.path.join(os.path.expanduser('~'), 'Pictures'),
                'videos': os.path.join(os.path.expanduser('~'), 'Videos'),
                'root': 'C:\\',
                'home': os.path.expanduser('~'),
                'file explorer': 'explorer.exe'
            }
    
            final_path = folder_map.get(clean_target, target)
            if not os.path.isabs(final_path) and not final_path.startswith(('http', 'www', 'ms-', 'shell:')):
                local_path = os.path.join(os.getcwd(), final_path)
                if os.path.exists(local_path):
                    final_path = local_path
    
            print(f"DEBUG: Calculated final_path: {final_path}")
            
            try:
                if final_path.startswith(('http', 'www')):
                    import webbrowser
                    webbrowser.open(final_path)
                    code = 0
                else:
                    # Windows native non-blocking open
                    os.startfile(final_path)
                    code = 0
                print(f"DEBUG: os.startfile/webbrowser launched. Code: {code}")
            except Exception as e:
                print(f"DEBUG: Launch failed: {e}")
                code = 1
                stderr = str(e)
            
            if code == 0:
                # Aggressive focus
                name_part = os.path.basename(final_path).split('.')[0]
                delayed_focus([name_part, target])
                # Register in memory
                if intent == 'open_folder':
                    memory_manager.update_context(last_folder=final_path, last_command=f"Opened folder {target}")
                elif intent == 'open_file':
                    memory_manager.update_context(last_file=final_path, last_command=f"Opened file {target}")
                else:
                    memory_manager.update_context(app_name=target, last_command=f"Opened application {target}")
            
            if code != 0:
                return jsonify({
                    'success': False,
                    'data': f'I tried to open **{target}**, but I couldn\'t find it. Is the path correct? ({stderr})'
                })
            
            msg = f"I've successfully opened **{target}** for you!"
            if intent == 'open_folder':
                msg = f"Opening the **{target}** folder right now! 📂"
            elif intent == 'open_file':
                msg = f"Launching the file **{target}**! 📄"
            
            # Trigger Mobile UI
            LAST_OPENED_APP = target
            print("DEBUG: Emitting app_opened...")
            socketio.emit('app_opened', {'app': target})
            print("DEBUG: app_opened emitted.")
            
            print("DEBUG: Getting local IP...")
            local_ip = get_local_ip()
            print(f"DEBUG: Local IP found: {local_ip}")
            remote_url = f"http://{local_ip}:{BACKEND_PORT}/remote?token={REMOTE_TOKEN}"
                
            return jsonify({
                'success': True, 
                'data': f"{msg}\n\n📱 **Remote Control Active:** [Open on Phone]({remote_url})",
                'remote_url': remote_url
            })

        elif intent == 'list_apps':
            if platform.system() == 'Windows':
                ps_cmd = 'powershell -Command "Get-Process | Where-Object { $_.MainWindowTitle } | Select-Object Name, MainWindowTitle | ConvertTo-Json"'
                stdout, stderr, code = run_command(ps_cmd)
                
                if code == 0 and stdout.strip():
                    try:
                        processes = json.loads(stdout)
                        if isinstance(processes, dict): processes = [processes]
                        
                        app_list = []
                        for p in processes:
                            name = p.get('Name', 'Unknown')
                            title = p.get('MainWindowTitle', '')
                            if title:
                                app_list.append(f"• **{name}** ({title})")
                        
                        if app_list:
                            return jsonify({
                                'success': True, 
                                'data': "Here are the applications currently on your taskbar:\n\n" + "\n".join(app_list)
                            })
                    except Exception as e:
                        print(f"Error parsing process list: {e}")
                
                return jsonify({
                    'success': True,
                    'data': "I couldn't find any major applications with open windows right now. Your taskbar seems clear! 🖥️"
                })
            else:
                return jsonify({'success': False, 'data': "Listing apps is only supported on Windows."})
        
        elif intent == 'close_app':
            target = sanitize_command_input(command).lower().rstrip('.!?;')
            
            process_map = {
                'chrome': 'chrome.exe',
                'browser': 'chrome.exe',
                'edge': 'msedge.exe',
                'notepad': 'Notepad.exe',
                'calculator': 'CalculatorApp.exe',
                'calc': 'CalculatorApp.exe',
                'paint': 'mspaint.exe',
                'whatsapp': 'WhatsApp.exe',
                'spotify': 'Spotify.exe',
                'vscode': 'Code.exe',
                'visual studio code': 'Code.exe',
                'visual studio code insider': 'Code - Insiders.exe',
                'clion': 'clion64.exe',
                'webstorm': 'webstorm64.exe',
                'code': 'Code.exe',
                'slack': 'slack.exe',
                'discord': 'Discord.exe',
                'zoom': 'Zoom.exe',
                'teams': 'Teams.exe',
                'terminal': 'WindowsTerminal.exe',
                'wt': 'WindowsTerminal.exe',
                'telegram': 'Telegram.exe',
                'postman': 'Postman.exe',
                'grammarly': 'Grammarly.exe',
                'upwork': 'Upwork.exe',
                'windsurf': 'Windsurf.exe',
                'netflix': 'Netflix.exe',
                'photos': 'Microsoft.Photos.exe',
                'clock': 'Time.exe',
                'outlook': 'Outlook.exe',
                'explorer': 'explorer.exe',
                'file explorer': 'explorer.exe',
                'settings': 'SystemSettings.exe'
            }
    
            process_name = process_map.get(target, target if target.endswith('.exe') else f"{target}.exe")
            cmd = f'taskkill /F /IM {process_name}'
            stdout, stderr, code = run_command(cmd)
            
            if code != 0:
                find_ps = f'powershell -Command "Get-Process | Where-Object {{ $_.Name -like \'*{target}*\' -or $_.MainWindowTitle -like \'*{target}*\' }} | Select-Object -ExpandProperty Name"'
                stdout_find, stderr_find, code_find = run_command(find_ps)
                
                if code_find == 0 and stdout_find.strip():
                    fallback_name = stdout_find.strip().split('\n')[0].strip()
                    cmd = f'taskkill /F /IM {fallback_name}.exe'
                    stdout, stderr, code = run_command(cmd)
    
            if code != 0:
                if "not found" in stderr.lower() or "no instance" in stderr.lower() or code == 128:
                    return jsonify({
                        'success': True,
                        'data': f"I couldn't find **{target}** running on your taskbar, so I didn't need to close anything! 🤷‍♂️"
                    })
                return jsonify({
                    'success': False,
                    'data': f"I tried to close **{target}**, but Windows gave me an error: {stderr}"
                })
                
            return jsonify({
                'success': True,
                'data': f"I've successfully closed **{target}** for you! 🛑"
            })
        
        elif intent == 'send_whatsapp':
            message = metadata.get('message', '')
            contact = metadata.get('contact', '')
            text_snippet = f'send?text={message}' if message else ''
            whatsapp_cmd = f'start whatsapp://{text_snippet}'
            
            stdout, stderr, code = run_command(whatsapp_cmd)
            if code != 0:
                return jsonify({
                    'success': False,
                    'data': "I couldn't open WhatsApp. Is it installed on your system?"
                })
            
            delayed_focus("WhatsApp")
            return jsonify({'success': True, 'data': "I've opened WhatsApp with your message!"})

        elif intent == 'reasoning_request' or command.lower().startswith(('reason:', 'think:', 'analyze:', 'solve:')):
            clean_command = re.sub(r'^(reason:|think:|analyze:|solve:)\s*', '', command, flags=re.IGNORECASE)
            print(f"DEBUG: Triggering Reasoning Agent for: {clean_command}")
            try:
                # Notify user we are thinking (frontend might not show this immediately, but useful for logs)
                result = reasoning_agent.think(clean_command)
                return jsonify({
                    'success': True, 
                    'data': f"🧠 **Reasoning Result:**\n\n{result}",
                    'intent': 'reasoning_complete'
                })
            except Exception as e:
                return jsonify({'success': False, 'data': f"Reasoning failed: {str(e)}"})

        elif intent in ['search_query', 'coding_assistance', 'unknown', 'fallback']:
            query = command.lower()
            is_coding = intent == 'coding_assistance' or any(word in query for word in ['code', 'python', 'script', 'program', 'function'])
            history = data.get('history', [])
            
            # Use MultiAgent Coordinator for complex coding/reasoning tasks
            if is_coding and coordinator:
                try:
                    results = coordinator.run_workflow(command)
                    return jsonify({
                        'success': True, 
                        'data': results['final_data'],
                        'steps': results['steps'],
                        'intent': 'coding_assistance'
                    })
                except Exception as e:
                    print(f"Coordinator error: {e}")
                    # Fallback to single agent if coordinator fails
            
            use_system_routing = (intent == 'unknown' or intent == 'fallback') and mode == 'local'
            
            system_prompt = (
                "You are Nana, a highly intelligent and witty Windows AI assistant. "
                "Respond in a concise, clear, and actionable way with a touch of personality. "
                "IMPORTANT: Always respond in the SAME LANGUAGE as the user's request."
            )
            
            if use_system_routing:
                system_prompt = SYSTEM_COMMAND_PROMPT
    
            try:
                from google import genai
                from agents import client
                
                formatted_history = []
                for msg in history:
                    formatted_history.append({"role": msg["role"], "parts": [{"text": msg["parts"][0]["text"]}]})
                
                formatted_history.append({"role": "user", "parts": [{"text": command}]})
                
                try:
                    response = client.models.generate_content(
                        model='models/gemini-2.5-flash',
                        config=genai.types.GenerateContentConfig(system_instruction=system_prompt),
                        contents=formatted_history
                    )
                    llm_response = response.text.strip()
                except Exception as e:
                    print(f"Gemini failed in server: {e}. Trying OpenRouter fallback...")
                    # Fallback to OpenRouter via a temporary agent instance or direct call
                    from agents import Reviewer
                    temp_agent = Reviewer()
                    llm_response = temp_agent.call_openrouter(system_prompt, command)
                    if not llm_response:
                        raise e # If fallback also fails, raise original error
                
                if use_system_routing:
                    try:
                        json_str = llm_response
                        if "```json" in llm_response: json_str = llm_response.split("```json")[1].split("```")[0].strip()
                        elif "```" in llm_response: json_str = llm_response.split("```")[1].split("```")[0].strip()
                        
                        start_idx = json_str.find('{')
                        end_idx = json_str.rfind('}')
                        if start_idx != -1 and end_idx != -1: json_str = json_str[start_idx:end_idx+1]
                            
                        parsed = json.loads(json_str)
                        
                        if parsed.get('action') == 'system':
                            os_cmd = parsed.get('command')
                            if os_cmd in ALLOWED_COMMANDS.values():
                                stdout, stderr, code = run_command(os_cmd)
                                return jsonify({'success': code == 0, 'data': f"Executed: {os_cmd}" if code == 0 else f"Error: {stderr}"})
                            else:
                                return jsonify({'success': False, 'data': "Safety Block: Command not in whitelist."})
    
                        elif parsed.get('action') == 'open':
                            target = parsed.get('target')
                            found_path = discover_target(target)
                            if not found_path: found_path = deep_search_file(target)
                                
                            if found_path:
                                summary = ""
                                if os.path.isfile(found_path):
                                    content = read_file_content(found_path)
                                    if content: summary = "\n\n**📄 Quick Brief:**\n" + get_ai_summarization(content)
                                
                                os.startfile(found_path)
                                # Fast Focus
                                delayed_focus([os.path.basename(found_path).split('.')[0], target])
                                return jsonify({'success': True, 'data': f"I've discovered and opened **{os.path.basename(found_path)}**! 📂" + summary})
                            else:
                                 # URI Check Fallback
                                uri_map_llm = {
                                    'netflix': 'netflix:', 
                                    'youtube': 'https://youtube.com', 
                                    'microsoft store': 'ms-windows-store:', 
                                    'camera': 'microsoft.windows.camera:', 
                                    'clock': 'ms-clock:', 
                                    'photos': 'ms-photos:', 
                                    'calendar': 'ms-calendar:', 
                                    'recycle bin': 'shell:RecycleBinFolder',
                                    'notepad': 'notepad.exe',
                                    'calculator': 'calc.exe',
                                    'task manager': 'taskmgr.exe',
                                    'sticky notes': 'microsoft.microsoftstickynotes:'
                                }
                                lt = target.lower()
                                if lt in uri_map_llm:
                                    run_command(f'start {uri_map_llm[lt]}')
                                    delayed_focus(target)
                                    return jsonify({'success': True, 'data': f"Opening **{target}**! 🚀"})
    
                                stdout, stderr, code = run_command(f'start "" "{target}"')
                                if code == 0: delayed_focus(target)
                                return jsonify({'success': code == 0, 'data': f"Launching **{target}**! 🚀" if code == 0 else f"I couldn't find or open **{target}**."})
    
                        elif parsed.get('action') == 'suggest_ai':
                            return jsonify({
                                'success': True, 
                                'data': parsed.get('reason'),
                                'intent': 'suggest_ai'
                            })
    
                        elif parsed.get('action') == 'none':
                            return jsonify({'success': True, 'data': parsed.get('reason', "I'm not sure how to do that safely.")})
                    except:
                        pass 
    
                return jsonify({'success': True, 'data': llm_response})
            except Exception as e:
                return jsonify({'success': False, 'data': f'Brain error: {e}'})

        elif intent == 'search_on_google':
            url = f'https://www.google.com/search?q={command}'
            run_command(f'start {url}')
            delayed_focus(["Chrome", "Edge", "Browser"], delay=0.5)
            return jsonify({'success': True, 'data': f'Searching Google for "{command}"...'})
    
        elif intent == 'search_on_youtube':
            url = f'https://www.youtube.com/results?search_query={command}'
            run_command(f'start {url}')
            delayed_focus(["Chrome", "Edge", "Browser"], delay=0.5)
            return jsonify({'success': True, 'data': f'Searching YouTube for "{command}"...'})

        elif intent == 'play_local_media':
            raw_query = command.lower().strip()
            # Tokenize query: split by common separators and remove short noise words
            query_tokens = [t for t in re.split(r'[\s\.\-_]+', raw_query) if len(t) > 2]
            if not query_tokens: # Fallback for very short queries
                query_tokens = [t for t in re.split(r'[\s\.\-_]+', raw_query) if t]

            search_roots = [
                Path.home() / 'Music',
                Path.home() / 'Videos',
                Path.home() / 'Downloads',
                Path.home() / 'Desktop',
                Path.cwd()
            ]
            
            def find_media(roots, tokens, depth=5):
                for root in roots:
                    if not root.exists(): continue
                    # Using rglob for modern recursive search
                    for path in root.rglob('*'):
                        # Check depth
                        try:
                            rel_depth = len(path.relative_to(root).parts)
                            if rel_depth > depth:
                                continue
                            
                            if not path.is_file():
                                continue
                                
                            f_lower = path.name.lower()
                            # Check if it's a media file
                            if path.suffix.lower() not in ('.mp4', '.mp3', '.mkv', '.avi', '.wav', '.mov', '.flac'):
                                continue
                            
                            # Clean filename for matching
                            name_only = path.stem.lower()
                            clean_name = re.sub(r'[\.\-_]', ' ', name_only)
                            
                            # Matching Logic
                            match_count = 0
                            for token in tokens:
                                if token in clean_name or (len(token) > 4 and any(token[:4] in word for word in clean_name.split())):
                                    match_count += 1
                            
                            threshold = max(1, int(len(tokens) * 0.6))
                            if match_count >= threshold:
                                return path
                        except (ValueError, PermissionError):
                            continue
                return None
    
            found_file = find_media(search_roots, query_tokens)
            if found_file:
                os.startfile(found_file)
                delayed_focus([found_file.stem, "Media Player", "VLC"], delay=0.5)
                return jsonify({'success': True, 'data': f'I found and started playing **{found_file.name}** for you! 🎬'})
            else:
                clean_query = " ".join(query_tokens)
                return jsonify({
                    'success': False, 
                    'data': f"I searched your Music, Videos, and Downloads (up to 5 levels deep), but couldn't find a matching file for '**{clean_query}**'. \n\nWould you like me to **search for it on YouTube** instead? 🎵"
                })

        elif intent == 'open_targeted_settings':
            setting_map = {'wifi': 'network-wifi', 'internet': 'network', 'display': 'display', 'sound': 'mmsys.cpl', 'bluetooth': 'bluetooth', 'update': 'windowsupdate'}
            target = setting_map.get(command.lower(), '')
            run_command(f'start ms-settings:{target}')
            delayed_focus("Settings", delay=0.5)
            return jsonify({'success': True, 'data': f'Opening Settings for {command}...'})
    
        elif intent == 'read_clipboard':
            stdout, stderr, code = run_command('powershell -Command "Get-Clipboard"')
            if code == 0:
                content = stdout.strip()
                if not content:
                    return jsonify({'success': True, 'data': "Your clipboard is currently empty! 📭"})
                return jsonify({'success': True, 'data': f"Here's what I found on your clipboard:\n\n```\n{content}\n```"})
            return jsonify({'success': False, 'data': f"I couldn't read your clipboard: {stderr}"})

        elif intent == 'copy_to_clipboard':
            text_to_copy = metadata.get('text', command)
            # Escape single quotes for PowerShell
            escaped_text = text_to_copy.replace("'", "''")
            cmd = f"powershell -Command \"Set-Clipboard -Value '{escaped_text}'\""
            stdout, stderr, code = run_command(cmd)
            if code == 0:
                return jsonify({'success': True, 'data': f"I've copied that to your clipboard! 📋"})
            return jsonify({'success': False, 'data': f"I couldn't copy that to your clipboard: {stderr}"})

        elif intent == 'write_file':
            filename = metadata.get('filename', command)
            content = metadata.get('content', '')
            
            if not filename:
                return jsonify({'success': False, 'data': "Please specify a filename."})
            
            # Sanitize and resolve path
            clean_filename = sanitize_command_input(filename)
            found_path = discover_target(clean_filename)
            
            if found_path:
                full_path = Path(found_path)
            else:
                # If not found, default to Documents
                full_path = Path.home() / 'Documents' / clean_filename
            
            # Ensure it has an extension, default to .txt if missing
            if not full_path.suffix:
                 full_path = full_path.with_suffix('.txt')
                 
            # Security: Validate extension
            if full_path.suffix.lower() not in ALLOWED_FILE_EXTENSIONS:
                 return jsonify({'success': False, 'data': f"I'm not allowed to write files with the extension '{full_path.suffix}' for safety reasons."})

            try:
                # Create directory if missing
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
                memory_manager.update_context(last_file=str(full_path), last_folder=str(full_path.parent), last_command=f"Wrote file {full_path.name}")
                return jsonify({'success': True, 'data': f"I've successfully saved **{full_path.name}**! 💾"})
            except Exception as e:
                return jsonify({'success': False, 'data': f"Error writing to file: {str(e)}"})

        elif intent == 'delete_file':
            filename = metadata.get('filename', command)
            if not filename:
                return jsonify({'success': False, 'data': "Please specify a filename to delete."})
            
            clean_filename = sanitize_command_input(filename)
            found_path = discover_target(clean_filename) or deep_search_file(clean_filename)
            
            if found_path:
                try:
                    p = Path(found_path)
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()
                    return jsonify({'success': True, 'data': f"I've deleted **{p.name}** for you. 🗑️"})
                except Exception as e:
                    return jsonify({'success': False, 'data': f"I couldn't delete the file: {e}"})
            return jsonify({'success': False, 'data': f"I couldn't find a file named '**{filename}**' to delete."})

        elif intent == 'power_management':
            action = command.strip().lower()
            if action == 'sleep':
                run_command('powershell -Command "Add-Type -Assembly \'System.Windows.Forms\'; [System.Windows.Forms.Application]::SetSuspendState(\'Suspend\', $false, $false)"')
                return jsonify({'success': True, 'data': "Sleeping... 😴"})
            elif action == 'shutdown':
                run_command('shutdown /s /t 10')
                return jsonify({'success': True, 'data': "Shutting down in 10s... 👋"})
            elif action == 'restart':
                run_command('shutdown /r /t 10')
                return jsonify({'success': True, 'data': "Restarting in 10s... 🔄"})
            elif action == 'lock':
                run_command('rundll32.exe user32.dll,LockWorkStation')
                return jsonify({'success': True, 'data': "Locked! 🔒"})
            return jsonify({'success': False, 'data': f"Unknown power action: {action}"})
    
        elif intent == 'get_local_ip':
            local_ip = get_local_ip()
            # Frontend URL (port 5173 by default)
            frontend_url = f"https://{local_ip}:5173"
            # Direct Remote Control URL (backend port)
            remote_url = f"http://{local_ip}:{BACKEND_PORT}/remote?token={REMOTE_TOKEN}"
            
            return jsonify({
                'success': True,
                'data': f"📱 **Connect your Phone!**\n\n1. Ensure your phone is on the same Wi-Fi.\n2. Open this link on your phone:\n\n• **Direct Access:** [{frontend_url}]({frontend_url})\n\n*(Note: If the link doesn't open, ensure you've run the **setup_startup.bat** as Administrator to open the firewall ports!)*",
                'remote_url': remote_url
            })

        else:
            return jsonify({'success': True, 'data': f"I understood {intent or 'unknown'}, but no system action is set!"})
    
    except ValueError as e:
        return jsonify({'success': False, 'data': f'Invalid input: {str(e)}'}), 400
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({'success': False, 'data': 'An unexpected error occurred. Please try again.'}), 500

if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"Nana System Bridge active on http://{local_ip}:{BACKEND_PORT}")
    print(f"!!! REMOTE CONTROL URL: http://{local_ip}:{BACKEND_PORT}/remote?token={REMOTE_TOKEN} !!!")
    print(f"!!! IMPORTANT: Ensure your phone is on the SAME WiFi as this PC !!!")
    print(f"!!! If 'Connecting...' persists, check your Windows Firewall for Port {BACKEND_PORT} !!!")
    print(f"Max file size: {MAX_FILE_SIZE // (1024*1024)}MB")
    print(f"Allowed extensions: {', '.join(ALLOWED_FILE_EXTENSIONS)}")
    # Use socketio.run instead of app.run
    socketio.run(app, host='0.0.0.0', port=BACKEND_PORT, debug=True, use_reloader=False)
