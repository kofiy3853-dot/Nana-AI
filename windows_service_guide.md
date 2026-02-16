# ⚙️ Windows Task Scheduler: Professional Setup Guide

Follow these steps to configure Nana AI as a robust, invisible background service that starts automatically on boot and recovers from crashes.

---

## 🛠️ Step-by-Step Configuration

### 1. General Tab
*   **Name**: `Nana_AI_Service`
*   **Description**: Background service for Nana AI Personal Assistant.
*   **Security Options**:
    *   Select: **"Run whether user is logged on or not"**
    *   Check: **"Do not store password"** (Optional, but safer if you don't need network share access)
    *   Check: **"Run with highest privileges"** (Required for system control)
    *   **Configure for**: Windows 10 or Windows 11

### 2. Triggers Tab
*   Click **New**:
    *   **Begin the task**: At startup
    *   **Advanced settings**:
        *   Check: **"Delay task for"**: 30 seconds (Recommended to allow network services to initialize)

### 3. Actions Tab
*   Click **New**:
    *   **Action**: Start a program
    *   **Program/script**: `D:\AI Agent\backend\.venv\Scripts\pythonw.exe`
    *   **Add arguments (optional)**: `server.py`
    *   **Start in (optional)**: `D:\AI Agent\backend`

> [!IMPORTANT]
> **Why `pythonw.exe`?**
> Using `pythonw.exe` instead of `python.exe` ensures that the assistant runs completely in the background without opening a visible command prompt window.

### 4. Conditions Tab
*   Uncheck: **"Start the task only if the computer is on AC power"** (Ensures it runs on laptops)
*   Check: **"Start only if the following network connection is available"**: Any connection

### 5. Settings Tab
*   Check: **"If the task fails, restart every"**: 1 minute
*   **Attempt to restart up to**: 3 times
*   Check: **"Allow task to be run on demand"**
*   Check: **"Run task as soon as possible after a scheduled start is missed"**
*   **If the task is already running, then the following rule applies**: Do not start a new instance

---

## 📝 Error Logging & Debugging

By default, `pythonw.exe` hides all output. To capture errors for debugging, you should modify the **Arguments** field in the **Actions** tab:

**Advanced Arguments**:
```powershell
server.py > nana_output.log 2>&1
```
*   This redirects both standard output and errors to `D:\AI Agent\backend\nana_output.log`.

### Common Mistakes
*   ❌ **Missing "Start in" path**: If left blank, Python won't find `server.py` or your `.env` file. Always set it to the `backend` directory.
*   ❌ **Incorrect Python Executable**: Ensure you point to the one *inside* your virtual environment (`.venv\Scripts\pythonw.exe`), not the system Python.

---

## 🧪 How to Test & Debug
1.  **Test Start**: Right-click the task in the Task Scheduler Library and select **Run**.
2.  **Verify Process**: Open Task Manager → Details tab. Look for `pythonw.exe`.
3.  **Verify UI**: Open your browser to `http://localhost:3001` to see if the interface loads.
4.  **Debug Failure**: If it won't start, check the **History** tab in Task Scheduler (you may need to click "Enable All Tasks History" in the right sidebar).
