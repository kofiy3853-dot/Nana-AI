/**
 * Bridge for Nana's system integration.
 * Expanded with better intent detection and personality.
 */

const NANA_PERSONALITY = {
    greetings: [
        "Hello! I'm Nana. How's your system running today?",
        "Hi there! Ready to be productive?",
        "Greetings! What can I help you with?",
        "Nana here! Always at your service.",
        "Hey! Good to see you again. What's the plan for today?",
        "Hello, friend! I'm powered up and ready to assist.",
        "Hi! Need a hand with something, or just stopping by to say hello?",
        "Greetings, human! How can I make your day easier?",
        "Nana is online! My logic circuits are humming with excitement to help you."
    ],
    status: [
        "All systems nominal! I'm running at 100% efficiency and ready for your commands.",
        "I'm feeling great! My code is clean and my spirits are high. How about you?",
        "Everything's running smoothly on my end. I'm ready for whatever you've got!",
        "Powered up and ready to go! My logic cores are chilled and my response time is peak.",
        "Feeling sharp! I've been organizing my modules all morning just for you."
    ],
    fallbacks: [
        "I'm still learning that specific trick. Should I look up how to do it?",
        "That's a bit beyond my current logic, but I'm getting smarter every day!",
        "I'm not sure how to do that yet. Maybe you can teach me?",
        "I'm afraid I don't have a module for that specific action yet. Is there anything else I can help with?",
        "My circuits are scratching their heads on that one! Could you rephrase that, or ask me for something else?",
        "I didn't quite catch the intent there. I can open apps, check health, or chat about code! What should we try?"
    ]
};

const APP_MAP = {
    'calculator': 'calc',
    'calcullator': 'calc', // Typos
    'calc': 'calc',
    'notepad': 'notepad',
    'chrome': 'chrome',
    'browser': 'chrome',
    'edge': 'msedge',
    'paint': 'mspaint',
    'explorer': 'explorer',
    'terminal': 'wt',
    'cmd': 'cmd',
    'powershell': 'powershell',
    'whatsapp': 'whatsapp',
    'control panel': 'control',
    'panel': 'control',
    'settings': 'settings',
    'task manager': 'taskmgr',
};

const WORKFLOW_GROUPS = {
    'workday': ['vscode', 'chrome', 'slack'],
    'coding': ['vscode', 'terminal', 'chrome'],
    'gaming': ['steam', 'discord', 'spotify'],
    'meeting': ['zoom', 'teams', 'calendar']
};

const KNOWLEDGE_BASE = {
    'nana': 'I am Nana, your personal AI assistant! I was built to help you manage your computer and chat with you.',
    'time': () => `The current local time is ${new Date().toLocaleTimeString()}.`,
    'date': () => `Today is ${new Date().toLocaleDateString()}.`,
    'capabilities': 'I can open apps, manage files, read your clipboard, check PC health, send WhatsApp messages, and run Python code! 🚀',
    'features': 'My top features include a System Dashboard, Smart Workflows, Python specialist mode, and a full voice interaction system. 🛡️',
};

export const executeCommand = async (command, file = null, history = [], mode = 'local') => {
    let lowerCmd = command.toLowerCase().trim();

    // List of wake words to strip from the start of the command if present
    const wakeWords = ['nana', 'nanna', 'nano', 'nah nah', 'mama', 'hey nana', 'hi nana', 'okay nana', 'now now'];
    for (const w of wakeWords) {
        if (lowerCmd.startsWith(w)) {
            lowerCmd = lowerCmd.substring(w.length).trim();
            // Also strip leading punctuation if any (like "Nana, open...")
            lowerCmd = lowerCmd.replace(/^[,. ]+/, '');
            break;
        }
    }

    let intent = 'unknown';
    let initialResponse = '';

    // Mode Switching Intents - High Priority
    const isBrainMode = lowerCmd.includes('ai brain') || lowerCmd.includes('ai mode') || lowerCmd.includes('brain mode') || (lowerCmd.includes('brain') && !lowerCmd.includes('drain'));
    const isLocalMode = lowerCmd.includes('local mode') || lowerCmd.includes('system mode') || lowerCmd.includes('local engine');

    if (lowerCmd.includes('switch to') || lowerCmd.includes('activate') || lowerCmd.includes('use my') || lowerCmd.includes('turn on') || lowerCmd.includes('go to')) {
        if (isBrainMode || lowerCmd.includes('ai') || lowerCmd.includes('brain')) {
            return { success: true, data: "Switching to my AI brain! 🧠", intent: 'switch_to_ai' };
        }
        if (isLocalMode || lowerCmd.includes('local') || lowerCmd.includes('system')) {
            return { success: true, data: "Switching to Local mode for direct system control. 💻", intent: 'switch_to_local' };
        }
    }

    // Direct commands
    if (lowerCmd === 'brain mode' || lowerCmd === 'ai brain' || lowerCmd === 'switch to brain') {
        return { success: true, data: "Switching to my AI brain! 🧠", intent: 'switch_to_ai' };
    }
    if (lowerCmd === 'local mode' || lowerCmd === 'local engine' || lowerCmd === 'switch to local') {
        return { success: true, data: "Switching to Local mode for direct system control. 💻", intent: 'switch_to_local' };
    }

    // Acknowledge attachment if present and no command
    if (file && !command) {
        return {
            success: true,
            data: `I've received your file: **${file.name}**. What would you like me to do with it?`,
            intent: 'file_received'
        };
    }

    // 1. Basic Greetings (Always Local for Speed)
    if (lowerCmd.match(/^(hi|hello|hey|greetings|morning|afternoon|evening|hola|yo|sup)/)) {
        intent = 'greeting';
        initialResponse = NANA_PERSONALITY.greetings[Math.floor(Math.random() * NANA_PERSONALITY.greetings.length)];
        return { success: true, data: initialResponse, intent };
    }

    // 2. Identity/Status
    if (lowerCmd.includes('who are you') || lowerCmd.includes('your name')) {
        intent = 'status_identity';
        initialResponse = "I'm Nana, your personalized AI assistant. I'm here to make managing your computer a breeze!";
        return { success: true, data: initialResponse, intent };
    }

    // Quick Local Check for time/date
    for (const key in KNOWLEDGE_BASE) {
        if (lowerCmd === key) {
            const fact = KNOWLEDGE_BASE[key];
            return {
                success: true,
                data: typeof fact === 'function' ? fact() : fact,
                intent: 'knowledge_qa'
            };
        }
    }

    // Mode-Based Logic Branching
    if (mode === 'ai') {
        // AI MODE: Prioritize Gemini for anything that isn't a basic greeting or status
        const questionWords = ['what', 'why', 'how', 'when', 'where', 'who', 'is', 'can', 'tell', 'define', 'explain', 'suggest'];
        const firstWord = lowerCmd.split(' ')[0];
        if (questionWords.includes(firstWord) || lowerCmd.endsWith('?') || lowerCmd.includes('code') || lowerCmd.includes('python')) {
            return await syncWithBackend({ command, intent: 'unknown', history, mode });
        }
    }

    // --- High Priority System Commands ---
    // 8. Power Management (Prioritized to avoid conflict with "Open" or "Health")
    const isSleep = lowerCmd.includes('sleep') || lowerCmd.includes('suspend') || lowerCmd.includes('hibernate');
    const isShutdown = lowerCmd.includes('shut down') || lowerCmd.includes('turn off') || lowerCmd.includes('power off') || lowerCmd.includes('shutdown');
    const isRestart = lowerCmd.includes('restart') || lowerCmd.includes('reboot');

    if (isSleep || isShutdown || isRestart || lowerCmd.includes('lock') || lowerCmd.includes('sign out')) {
        const pIntent = 'power_management';
        let pAction = isSleep ? 'sleep' : (isRestart ? 'restart' : (isShutdown ? 'shutdown' : 'lock'));
        // Check if it's a question FIRST - if so, let Gemini handle the "Yes I can" part
        const isQuestion = lowerCmd.startsWith('can') || lowerCmd.startsWith('how') || lowerCmd.endsWith('?');
        if (!isQuestion) {
            return await syncWithBackend({ command: pAction, intent: pIntent, history, mode });
        }
    }

    // 3. Media Controls (New: Play/Pause, Next, Previous)
    const mediaKeywords = ['pause', 'resume', 'next track', 'preview', 'previous track', 'skip song', 'last song', 'stop music', 'play/pause'];
    const isMediaControl = mediaKeywords.some(k => lowerCmd.includes(k)) ||
        lowerCmd === 'play' || lowerCmd === 'pause' ||
        lowerCmd === 'next' || lowerCmd === 'previous' ||
        lowerCmd === 'prev' || lowerCmd === 'preview';

    if (isMediaControl) {
        intent = 'media_control';
        return await syncWithBackend({ command: lowerCmd, intent, history, mode });
    }

    // 10. Window Management (Minimize/Maximize)
    const isMinimize = lowerCmd.includes('minimize') || lowerCmd.includes('minimum');
    const isMaximize = lowerCmd.includes('maximize') || lowerCmd.includes('maximum');
    const isRestore = lowerCmd.includes('restore window') || lowerCmd.includes('unminimize');
    const isMinimizeAll = lowerCmd.includes('show desktop') || lowerCmd.includes('minimize all') || lowerCmd.includes('hide everything');

    if (isMinimize || isMaximize || isRestore || isMinimizeAll) {
        if (isMinimizeAll) intent = 'minimize_all';
        else if (isMinimize) intent = 'minimize_window';
        else if (isMaximize) intent = 'maximize_window';
        else if (isRestore) intent = 'restore_window';

        // Extract target if specified (e.g., "minimize chrome")
        let target = '';
        if (!isMinimizeAll) {
            // Match (minimize|maximum|...) followed by optional "the/my" and then a target
            const match = lowerCmd.match(/(?:minimize|maximize|restore|minimum|maximum)(?:\s+(?:the\s+|my\s+)?(.*))?$/i);
            if (match && match[1]) target = match[1].trim();
        }

        return await syncWithBackend({ command: target, intent, history, mode });
    }

    // 3. Media Playback (New: Play Music / Video)
    if (lowerCmd.startsWith('play ')) {
        const playMatch = lowerCmd.match(/^play\s+(.*)/);
        if (playMatch) {
            let target = playMatch[1].trim();

            // "Play music" -> Open Spotify
            if (target === 'music' || target === 'some music' || target === 'spotify') {
                intent = 'open_app';
                return await syncWithBackend({ command: 'spotify', intent, history, mode });
            }

            // "Play [file] locally"
            if (target.includes('locally') || target.includes('on my machine') || target.includes('on my pc')) {
                const query = target.replace('locally', '').replace('on my machine', '').replace('on my pc', '').trim();
                intent = 'play_local_media';
                return await syncWithBackend({ command: query, intent, history, mode });
            }

            // "Play [query] on youtube"
            if (target.includes('on youtube')) {
                const query = target.replace('on youtube', '').trim();
                intent = 'search_on_youtube';
                return await syncWithBackend({ command: query, intent, history, mode });
            }

            // "Play [query]" -> Default to YouTube Search
            intent = 'search_on_youtube';
            return await syncWithBackend({ command: target, intent, history, mode });
        }
    }

    // 5. Mobile Connect / IP Info / Taskbar Check / System Health
    if (lowerCmd.includes('mobile connect') || lowerCmd.includes('connect phone') || lowerCmd.includes('local ip') || lowerCmd.includes('remote control')) {
        intent = 'get_local_ip';
        return await syncWithBackend({ command: 'get_ip', intent, history, mode });
    }

    if (lowerCmd.includes('system health') || lowerCmd.includes('diagnostics') || lowerCmd.includes('check stats') || lowerCmd.includes('system stats') || lowerCmd.includes('pc health')) {
        intent = 'sys_health';
        return await syncWithBackend({ command: '', intent, history, mode });
    }

    if (lowerCmd.includes('list apps') || lowerCmd.includes('running apps') || lowerCmd.includes('on my taskbar') || lowerCmd.includes('what is open') || lowerCmd.includes('show running')) {
        intent = 'list_apps';
        return await syncWithBackend({ command: '', intent, history, mode });
    }

    // 5. Search (Prioritize over Open to handle "open youtube and search for...")
    if (lowerCmd.includes('search for') || lowerCmd.includes('search on') || lowerCmd.includes('search youtube') || lowerCmd.includes('search google')) {
        const youtubeMatch = lowerCmd.match(/(?:search for |search youtube for |search on youtube for )(.*)/);
        const googleMatch = lowerCmd.match(/(?:search for |search google for |search on google for )(.*)/);

        // Specific complex pattern: "(open) youtube and search for (ai agent)"
        const complexYoutubeMatch = lowerCmd.match(/(?:open )?youtube (?:and |to )?search for (.*)/);
        const complexGoogleMatch = lowerCmd.match(/(?:open )?google (?:and |to )?search for (.*)/);

        if (complexYoutubeMatch) {
            intent = 'search_on_youtube';
            return await syncWithBackend({ command: complexYoutubeMatch[1], intent, history, mode });
        } else if (complexGoogleMatch) {
            intent = 'search_on_google';
            return await syncWithBackend({ command: complexGoogleMatch[1], intent, history, mode });
        } else if (youtubeMatch && lowerCmd.includes('youtube')) {
            intent = 'search_on_youtube';
            return await syncWithBackend({ command: youtubeMatch[1], intent, history, mode });
        } else if (googleMatch && (lowerCmd.includes('google') || lowerCmd.includes('chrome'))) {
            intent = 'search_on_google';
            return await syncWithBackend({ command: googleMatch[1], intent, history, mode });
        }
    }

    // 12. Volume & Brightness Controls
    const volumeMatch = lowerCmd.match(/(?:set |change |turn |put )?volume (?:to |at )?(\d+)%?/i) || lowerCmd.match(/volume (\d+)/i);
    const brightnessMatch = lowerCmd.match(/(?:set |change |put )?brightness (?:to |at )?(\d+)%?/i);
    const isMute = lowerCmd.includes('mute') && !lowerCmd.includes('unmute');
    const isUnmute = lowerCmd.includes('unmute');

    if (volumeMatch || brightnessMatch || isMute || isUnmute) {
        if (brightnessMatch) {
            intent = 'set_brightness';
            return await syncWithBackend({ command: brightnessMatch[1], intent, history, mode });
        }
        intent = 'set_volume';
        let volumeCmd = isMute ? 'mute' : (isUnmute ? 'unmute' : volumeMatch[1]);
        return await syncWithBackend({ command: volumeCmd, intent, history, mode });
    }

    // 4. System Commands (Refined regex to avoid overlap with questions)
    const openRegex = /^(?:open|start|launch)\s+(?:the\s+|my\s+|a\s+)?(.*?)[.!?;]?$/i;
    const closeRegex = /^(?:close|exit|quit|stop|kill|terminate|shut down)\s+(?:the\s+|my\s+|a\s+)?(.*?)[.!?;]?$/i;

    const openMatch = lowerCmd.match(openRegex);
    const closeMatch = lowerCmd.match(closeRegex);

    if (openMatch) {
        let target = openMatch[1].trim().toLowerCase();

        // Prevent matching if it's actually a search query we missed above
        if (target.includes('search for') || target.includes('search on')) {
            /* fall through */
        } else {
            if (APP_MAP[target] || target.length > 0) {
                // Global Filler Cleanup
                const cleanupPatterns = [
                    /^app\s+/, /^application\s+/, /^program\s+/,
                    /^what is in the\s+/, /^what is in\s+/, /^what's in the\s+/, /^what's in\s+/,
                    /^what is on the\s+/, /^what is on\s+/, /^what's on the\s+/, /^what's on\s+/
                ];
                let cleanedTarget = target;
                for (const pattern of cleanupPatterns) {
                    cleanedTarget = cleanedTarget.replace(pattern, '');
                }

                if (cleanedTarget && cleanedTarget !== 'it' && cleanedTarget !== 'app') {
                    const mappedTarget = APP_MAP[cleanedTarget] || cleanedTarget;
                    intent = 'open_app';
                    return await syncWithBackend({ command: mappedTarget, intent, history, mode });
                }
            }
        }
    }

    if (closeMatch) {
        let target = closeMatch[1].trim().toLowerCase();
        // Global Filler Cleanup
        const cleanupPatterns = [/^app\s+/, /^application\s+/, /^program\s+/];
        let cleanedTarget = target;
        for (const pattern of cleanupPatterns) {
            cleanedTarget = cleanedTarget.replace(pattern, '');
        }

        if (cleanedTarget && cleanedTarget !== 'it' && cleanedTarget !== 'app') {
            const mappedTarget = APP_MAP[cleanedTarget] || cleanedTarget;
            intent = 'close_app';
            return await syncWithBackend({ command: mappedTarget, intent, history, mode });
        }
    }

    // 5. File/Folder Management
    const folderRegex = /(?:open|launch|show)\s+(?:the\s+|my\s+)?(.*?)\s+folder/i;
    const fileLaunchRegex = /(?:open|launch|run|view)\s+(?:the\s+|my\s+)?file\s+(.*)/i;

    const folderMatch = lowerCmd.match(folderRegex);
    const fileMatch = lowerCmd.match(fileLaunchRegex);

    if (folderMatch) {
        intent = 'open_folder';
        return await syncWithBackend({ command: folderMatch[1].trim(), intent, history, mode });
    }

    if (fileMatch) {
        intent = 'open_file';
        return await syncWithBackend({ command: fileMatch[1].trim(), intent, history, mode });
    }

    // 6. Messaging (WhatsApp)
    if (lowerCmd.includes('whatsapp') || lowerCmd.includes('message')) {
        intent = 'send_whatsapp';
        const sendToMatch = lowerCmd.match(/message to (.*?) saying (.*)/);

        if (sendToMatch) {
            const contact = sendToMatch[1];
            const message = sendToMatch[2];
            return await syncWithBackend({ command: `whatsapp message to ${contact} saying ${message}`, intent, metadata: { contact, message }, history, mode });
        } else if (lowerCmd.includes('whatsapp') && !lowerCmd.includes('saying')) {
            intent = 'open_app';
            return await syncWithBackend({ command: 'whatsapp', intent, history, mode });
        }
    }

    if (lowerCmd.includes('settings for') || lowerCmd.includes('settings to')) {
        const settingsMatch = lowerCmd.match(/settings (for|to) (.*?)$/);
        if (settingsMatch) {
            intent = 'open_targeted_settings';
            const setting = settingsMatch[2].replace(/[?!.]$/, '');
            return await syncWithBackend({ command: setting, intent, history, mode });
        }
    }

    // 7. Clipboard
    if (lowerCmd.includes('clipboard') || lowerCmd.includes('copied')) {
        // Detect "copy [text] to clipboard"
        const copyMatch = lowerCmd.match(/(?:copy)\s+(.*)\s+(?:to|on)\s+(?:the\s+)?clipboard/i);
        if (copyMatch) {
            intent = 'copy_to_clipboard';
            return await syncWithBackend({ command, intent, metadata: { text: copyMatch[1].trim() }, history, mode });
        }

        // Default to read
        intent = 'read_clipboard';
        return await syncWithBackend({ command: '', intent, history, mode });
    }

    // New: File Editing
    if (lowerCmd.includes('edit') || lowerCmd.includes('write to') || lowerCmd.includes('save to')) {
        const editMatch = lowerCmd.match(/(?:edit|write to|save to)\s+(?:the\s+|my\s+)?file\s+(.*?)(?:\s+with\s+(.*))?$/i) ||
            lowerCmd.match(/(?:edit|write to|save to)\s+(.*?)(?:\s+with\s+(.*))?$/i);

        if (editMatch) {
            intent = 'write_file';
            const filename = editMatch[1].trim();
            const content = editMatch[2] ? editMatch[2].trim() : '';
            return await syncWithBackend({ command: filename, intent, metadata: { filename, content }, history, mode });
        }
    }

    // New: File Deletion
    if (lowerCmd.includes('delete') || lowerCmd.includes('remove file')) {
        const deleteMatch = lowerCmd.match(/(?:delete|remove file)\s+(?:the\s+|my\s+)?(.*?)$/i);
        if (deleteMatch) {
            intent = 'delete_file';
            const filename = deleteMatch[1].trim();
            return await syncWithBackend({ command: filename, intent, metadata: { filename }, history, mode });
        }
    }


    // 9. System Health & Utilities
    if (lowerCmd.includes('how') && (lowerCmd.includes('pc') || lowerCmd.includes('system') || lowerCmd.includes('computer') || lowerCmd.includes('battery'))) {
        intent = 'system_health';
        return await syncWithBackend({ command, intent, history, mode });
    }

    if (lowerCmd.includes('clean') || lowerCmd.includes('clear') || lowerCmd.includes('optimize')) {
        intent = 'system_utility';
        return await syncWithBackend({ command, intent, history, mode });
    }

    // Final Fallback Handling based on Mode
    if (mode === 'ai') {
        // AI Mode: Send EVERYTHING to Gemini if not matched above
        return await syncWithBackend({ command, intent: 'unknown', history, mode });
    } else {
        // LOCAL Mode: Only send to Gemini if it looks like a clear question/search
        const questionWords = ['what', 'why', 'how', 'when', 'where', 'who', 'is', 'can', 'tell', 'define', 'explain', 'suggest'];
        const isLikelyQuestion = questionWords.some(word => lowerCmd.startsWith(word)) || lowerCmd.endsWith('?');

        if (isLikelyQuestion) {
            return await syncWithBackend({ command, intent: 'unknown', history, mode });
        }

        return {
            success: false,
            data: "I'm currently in **Local Mode**. This mode is for system commands only. Switch to **AI Mode** if you want me to use my reasoning brain! 🧠",
            intent: 'mode_restriction'
        };
    }
};

async function syncWithBackend({ command, intent, metadata = {}, history = [], mode = 'local' }) {
    try {
        // Use relative path so Vite proxy handles it (avoiding Mixed Content errors)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 120 second timeout for deep reasoning

        // Get JWT token from localStorage
        const token = localStorage.getItem('nana-token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`/api/execute`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ command, intent, metadata, history, mode }),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            // Check if it's an authentication error
            if (response.status === 401) {
                localStorage.removeItem('nana-token');
                localStorage.removeItem('nana-token-expiry');
                window.location.reload(); // Force re-login
                return { success: false, data: "Session expired. Please log in again.", intent };
            }
            const errorText = await response.text();
            throw new Error(`Server error: ${response.status} - ${errorText}`);
        }

        const serverData = await response.json();
        return serverData;
    } catch (err) {
        if (err.name === 'AbortError') {
            return { success: false, data: "Request timeout - the server took too long to resolve your query.", intent };
        }
        console.error("Backend bridge error:", err);
        return {
            success: false,
            data: `Oops, it looks like my backend bridge is disconnected! (${err.message})`,
            intent
        };
    }
}

