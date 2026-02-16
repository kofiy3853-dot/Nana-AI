# Nana - Windows AI Assistant

A modern React + Python desktop AI assistant with voice control and system integration for Windows.

## Tech Stack

- **Frontend:** React 19 + Vite
- **Backend:** Python Flask + Flask-CORS
- **UI Library:** Framer Motion, Lucide React
- **Platform:** Windows-focused system integration

## 🚀 Quick Start (One-Click Install)

Nana includes an automated launcher that handles dependencies, environment setup, and startup in one go.

1.  **Clone the repository** to your local machine.
2.  **Run the launcher**: Double-click `start_nana.bat` in the root directory.
    - *The script will automatically install Node.js modules and Python virtual environments if missing.*
3.  **Configure API Keys**: When prompted, create a file named `.env` in the `backend/` folder:
    ```env
    GEMINI_API_KEY=your_key_here
    OPENROUTER_API_KEY=optional_backup_key
    ```
4.  **Access Nana**: The UI will automatically open at `http://localhost:5173`.

---

## ✨ Features (Standard & Advanced)

- 🎙️ **Multi-Modal Interaction**: Voice input (Web Speech API) and sleek text interface.
- 🧠 **AI Task Planner**: Chained commands (e.g., *"Open Notepad then type 'System Check' and save it"*).
- 💾 **Persistent Memory**: Nana remembers your active app, last file, and folder even after restart.
- 🛡️ **Interactive Safety**: Auto-focuses and verifies target windows before typing to ensure accuracy.
- 📱 **Mobile Remote**: Control your PC mouse and keyboard from your phone (QR code in chat).
- 📊 **System Dashboard**: Real-time monitoring of CPU, RAM, and Battery.
- 📂 **Advanced File Ops**: Deep search, Pathlib-powered navigation, and PDF/Docx Briefing.
- 🤖 **Auto-Start**: Production-ready background automation (see `windows_service_guide.md`).

## Available Scripts

- `npm run dev` - Start Vite dev server
- `npm run build` - Build for production
- `npm run bridge` - Start Python Flask backend
- `npm run lint` - Run ESLint
- `npm run preview` - Preview built app

## Architecture

```
Frontend (React + Vite)
    ↓
bridge.js (intent detection & routing)
    ↓
HTTP POST to localhost:3001/api/execute
    ↓
Backend (Python Flask)
    ↓
Windows System Commands (PowerShell, subprocess)
```

## Backend Features

The Python backend handles:
- Application launching
- File operations (read, list, manage)
- Clipboard access
- System health monitoring
- WhatsApp integration
- Python code execution
- Google/YouTube searches
- Windows Settings navigation

## Notes

- The application is Windows-specific due to system command integration
- Clipboard operations require PowerShell on Windows
- Python code execution runs in isolated temporary files
- Voice features work best in Chromium-based browsers (Chrome, Edge)

