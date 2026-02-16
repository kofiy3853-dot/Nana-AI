import json
import os
import time
from pathlib import Path

try:
    import pygetwindow as gw
except ImportError:
    gw = None

class MemoryManager:
    def __init__(self, memory_file="nana_memory.json"):
        self.memory_file = Path(memory_file)
        self.memory = {
            "active_app_name": None,
            "active_window_title": None,
            "last_folder": None,
            "last_file": None,
            "last_command": None,
            "timestamp": time.time()
        }
        self.load_memory()

    def load_memory(self):
        """Load memory from JSON file if it exists."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memory.update(data)
                print(f"[MemoryManager] Loaded persistent memory from {self.memory_file}")
            except Exception as e:
                print(f"[MemoryManager] Error loading memory: {e}")

    def save_memory(self):
        """Save current memory state to JSON file."""
        try:
            self.memory["timestamp"] = time.time()
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, indent=4)
        except Exception as e:
            print(f"[MemoryManager] Error saving memory: {e}")

    def update_context(self, app_name=None, last_folder=None, last_file=None, last_command=None):
        """Update any part of the memory and persist it."""
        if app_name: self.memory["active_app_name"] = app_name
        if last_folder: self.memory["last_folder"] = str(last_folder)
        if last_file: self.memory["last_file"] = str(last_file)
        if last_command: self.memory["last_command"] = last_command

        # Auto-detect active window if possible
        if gw:
            try:
                active_win = gw.getActiveWindow()
                if active_win:
                    self.memory["active_window_title"] = active_win.title
                    # In Windows, if no app_name given, we can try to derive from title
                    if not app_name:
                        self.memory["active_app_name"] = active_win.title.split(' - ')[-1]
            except Exception as e:
                print(f"[MemoryManager] Error detecting active window: {e}")

        self.save_memory()

    def activate_app(self, app_name):
        """Finds and brings an application window to the front."""
        if not gw: return False
        try:
            # Try exact title match first
            wins = gw.getWindowsWithTitle(app_name)
            if not wins:
                # Try partial match (e.g. "Notepad" in "Untitled - Notepad")
                all_wins = gw.getAllWindows()
                wins = [w for w in all_wins if app_name.lower() in w.title.lower()]
            
            if wins:
                win = wins[0]
                if win.isMinimized:
                    win.restore()
                win.activate()
                time.sleep(0.5) # Wait for animation/focus
                return True
            return False
        except Exception as e:
            print(f"[MemoryManager] Error activating app '{app_name}': {e}")
            return False

    def verify_focus(self, expected_app):
        """Verifies if the currently active window matches the expected application with retries."""
        if not gw: return True
        expected = expected_app.lower()
        
        # Try up to 3 times with short delays to account for Windows focus shifts
        for i in range(3):
            try:
                active_win = gw.getActiveWindow()
                if active_win:
                    active_title = active_win.title.lower()
                    if expected in active_title or active_title in expected:
                        return True
                    # Check for common executable names if title doesn't match
                    if expected.endswith('.exe') and expected[:-4] in active_title:
                        return True
                
                time.sleep(0.3)
            except:
                time.sleep(0.3)
        return False

    def get_active_window_info(self):
        """Returns details about the current foreground window."""
        if not gw: return "Window detection unavailable."
        try:
            win = gw.getActiveWindow()
            if win:
                return f"Active Window: '{win.title}' (HWND: {win._hWnd})"
            return "No active window detected."
        except:
            return "Error detecting active window."

    def get_context_summary(self):
        """Returns a formatted string summary for the AI Planner."""
        lines = []
        if self.memory["active_app_name"]:
            lines.append(f"- Active App: {self.memory['active_app_name']} (Window: '{self.memory['active_window_title']}')")
        if self.memory["last_folder"]:
            lines.append(f"- Last Folder used: {self.memory['last_folder']}")
        if self.memory["last_file"]:
            lines.append(f"- Last File opened: {self.memory['last_file']}")
        if self.memory["last_command"]:
            lines.append(f"- Last Action performed: {self.memory['last_command']}")
        
        if not lines:
            return "No previous context recorded."
        return "Current Session Memory:\n" + "\n".join(lines)

    @property
    def active_app_name(self):
        return self.memory["active_app_name"]
    
    @property
    def last_folder(self):
        return self.memory["last_folder"]

    @property
    def last_file(self):
        return self.memory["last_file"]
