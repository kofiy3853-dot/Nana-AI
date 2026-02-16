import pygetwindow as gw
import time

class SessionManager:
    def __init__(self):
        self.active_app_name = None
        self.active_window_title = None
        self.active_window_hwnd = None

    def update_context(self, app_name=None):
        """Update the current session context based on the active window or explicit app launch."""
        try:
            active_win = gw.getActiveWindow()
            if active_win:
                self.active_window_title = active_win.title
                self.active_window_hwnd = active_win._hWnd
                
                # If an app_name was explicitly provided (e.g. from a launch), use it
                if app_name:
                    self.active_app_name = app_name
                else:
                    # Otherwise, try to infer it from the title if we don't have one
                    if not self.active_app_name:
                        self.active_app_name = self.active_window_title.split(' - ')[-1]
            
            print(f"[SessionManager] Active App: {self.active_app_name} | Window: {self.active_window_title}")
        except Exception as e:
            print(f"[SessionManager] Error updating context: {e}")

    def get_context_summary(self):
        """Returns a string description of the current session for the AI Planner."""
        if not self.active_app_name:
            return "No application currently in focus."
        return f"Currently controlling: {self.active_app_name} (Window: '{self.active_window_title}')"

    def set_active_app(self, app_name):
        self.active_app_name = app_name
        time.sleep(1) # Give it a second to focus
        self.update_context(app_name)
