import React, { useState, useRef, useEffect } from 'react';
import { Zap, Send, Monitor, MessageSquare, Paperclip, X, FileText, Image as ImageIcon, Settings as SettingsIcon, Sun, Moon, Mic, MicOff, Copy, Clipboard, Trash2, Edit3, Smartphone } from 'lucide-react';
import { executeCommand } from './bridge';

const App = () => {
  const [messages, setMessages] = useState([
    { id: 1, type: 'ai', text: "Hello! I'm Nana, your personal AI assistant. How can I help you manage your computer today?" }
  ]);
  const [input, setInput] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [useVoice, setUseVoice] = useState(() => {
    const saved = localStorage.getItem('nana-voice');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('nana-theme') || 'theme-light';
  });
  const [showSettings, setShowSettings] = useState(false);
  const [continuousVoice, setContinuousVoice] = useState(() => {
    const saved = localStorage.getItem('nana-continuous');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const [activeBrain, setActiveBrain] = useState(() => {
    return localStorage.getItem('nana-brain-mode') || 'local';
  });
  const [dashboardStats, setDashboardStats] = useState(null);
  const [showDashboard, setShowDashboard] = useState(false);
  const [contextColor, setContextColor] = useState('blue');
  const [weather, setWeather] = useState(null);
  const [notes, setNotes] = useState(() => {
    return localStorage.getItem('nana-notes') || 'Write your quick notes here...';
  });
  const [attachment, setAttachment] = useState(null);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const continuousRef = useRef(continuousVoice);
  const recognitionRef = useRef(null);

  const [wakeWordEnabled, setWakeWordEnabled] = useState(() => {
    const saved = localStorage.getItem('nana-wakeword');
    return saved !== null ? JSON.parse(saved) : true;
  });

  const [lastHeard, setLastHeard] = useState('');

  useEffect(() => {
    continuousRef.current = continuousVoice;
  }, [continuousVoice]);

  useEffect(() => {
    localStorage.setItem('nana-theme', theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem('nana-voice', JSON.stringify(useVoice));
  }, [useVoice]);

  useEffect(() => {
    localStorage.setItem('nana-continuous', JSON.stringify(continuousVoice));
  }, [continuousVoice]);

  useEffect(() => {
    localStorage.setItem('nana-wakeword', JSON.stringify(wakeWordEnabled));
  }, [wakeWordEnabled]);

  useEffect(() => {
    localStorage.setItem('nana-notes', notes);
  }, [notes]);

  useEffect(() => {
    localStorage.setItem('nana-brain-mode', activeBrain);
  }, [activeBrain]);

  useEffect(() => {
    // Remove mock weather - would need real API integration
    // Example: fetch weather from OpenWeatherMap API
    // setWeather({ temp: '24°C', condition: 'Sunny', city: 'London' });
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "auto" });
  };

  const speak = (text) => {
    if (!useVoice) return;
    window.speechSynthesis.cancel();

    // Stop recording if active to prevent Nana from listening to herself
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) { }
    }

    const utterance = new SpeechSynthesisUtterance(text);

    // Attempt to pick a natural-sounding voice (Prefer Male/Deep)
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(v =>
      v.name.includes('Male') ||
      v.name.includes('David') ||
      v.name.includes('Mark') ||
      (v.name.includes('Google') && !v.name.includes('Female'))
    );
    if (preferredVoice) utterance.voice = preferredVoice;

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => {
      setIsSpeaking(false);
      // Auto-listen if continuous mode is on
      if (continuousRef.current) {
        setTimeout(handleListen, 500);
      }
    };
    utterance.pitch = 1.05;
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    // Visual feedback? maybe a toast? for now just silent or console
    console.log("Copied to clipboard:", text);
  };

  // Ref to track if we should auto-restart listening (Always-On mode)
  const shouldKeepListening = useRef(false);
  const isStartingRecognition = useRef(false);
  const recognitionRestartLock = useRef(false);

  const handleModeSwitch = (mode, autoRetryMessage = null) => {
    setActiveBrain(mode);
    const confirmation = mode === 'ai' ? "Switching to my AI brain! 🧠" : "Switching to Local mode. 💻";

    // Speak confirmation
    speak(confirmation);

    // If we have a message to retry (for the suggestion button)
    if (autoRetryMessage) {
      // Pass the NEW mode explicitly to ensure it's used
      setTimeout(() => handleSend(autoRetryMessage, mode), 1000);
    }
  };

  const toggleListening = () => {
    if (isListening) {
      // User wants to stop
      shouldKeepListening.current = false;
      recognitionRestartLock.current = false;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          console.log("Stop error:", e);
        }
      }
      setIsListening(false);
    } else {
      // User wants to start
      shouldKeepListening.current = true;
      recognitionRestartLock.current = false;
      handleListen();
    }
  };

  const handleListen = () => {
    if (isSpeaking) return;

    // Ensure we don't start multiple instances
    if (isListening || isStartingRecognition.current || recognitionRestartLock.current) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech Recognition is not supported in this browser. Please use Chrome or Edge.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
      isStartingRecognition.current = false;
    };

    recognition.onend = () => {
      isStartingRecognition.current = false;
      recognitionRestartLock.current = false;

      // Only update UI to "Not Listening" if we are genuinely stopping
      if (!shouldKeepListening.current || isSpeaking) {
        setIsListening(false);
      }

      // Auto-restart if we are in "Always-On" mode and not currently speaking
      if (shouldKeepListening.current && !isSpeaking && !recognitionRestartLock.current) {
        recognitionRestartLock.current = true;
        setTimeout(() => {
          // Double check locking before calling start()
          if (isStartingRecognition.current || !shouldKeepListening.current) {
            recognitionRestartLock.current = false;
            return;
          }
          try {
            isStartingRecognition.current = true;
            recognition.start();
          } catch (e) {
            console.log("Restart error:", e);
            isStartingRecognition.current = false;
            recognitionRestartLock.current = false;
            setIsListening(false);
          }
        }, 300);
      }
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setLastHeard(transcript);

      if (transcript.trim()) {
        if (wakeWordEnabled) {
          const lower = transcript.toLowerCase().trim();
          const wakeWords = ['nana', 'nanna', 'nano', 'nah nah', 'mama', 'hey nana', 'hi nana', 'okay nana', 'now now'];
          const startsWithWakeWord = wakeWords.some(w => lower.startsWith(w));

          if (!startsWithWakeWord) {
            setLastHeard(transcript + " ❌ (Say 'Nana...')");
            return;
          }
        }

        setLastHeard(transcript + " ✅");
        setInput(transcript);
        setTimeout(() => {
          handleSend(transcript);
        }, 300);
      }
    };

    recognition.onerror = (event) => {
      isStartingRecognition.current = false;
      recognitionRestartLock.current = false;

      if (event.error === 'no-speech') {
        // Silently restart for no-speech
        if (shouldKeepListening.current) {
          setTimeout(() => handleListen(), 500);
        }
        return;
      }

      if (event.error === 'network' || event.error === 'aborted') {
        if (shouldKeepListening.current) {
          setTimeout(() => handleListen(), 1000);
        }
        return;
      }

      if (event.error === 'not-allowed') {
        alert("Microphone access denied. Please allow microphone access in your browser settings.");
        shouldKeepListening.current = false;
        setIsListening(false);
        return;
      }

      console.error("Recognition error:", event.error);
      setIsListening(false);

      if (shouldKeepListening.current) {
        setTimeout(() => handleListen(), 1000);
      }
    };

    try {
      if (isStartingRecognition.current || recognitionRestartLock.current) return;
      isStartingRecognition.current = true;
      recognition.start();
    } catch (e) {
      console.error("Start error:", e);
      isStartingRecognition.current = false;
      recognitionRestartLock.current = false;
      setIsListening(false);
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (voiceInput = null, modeOverride = null) => {
    const textToSend = voiceInput !== null ? voiceInput : input;
    if (!textToSend.trim() && !attachment) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: textToSend,
      file: attachment ? { name: attachment.name, type: attachment.type } : null
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setAttachment(null);
    setIsThinking(true);

    setTimeout(async () => {
      const history = messages.slice(-10).map(m => ({
        role: m.type === 'user' ? 'user' : 'model',
        parts: [{ text: m.text }]
      }));

      const activeMode = modeOverride || activeBrain;
      const result = await executeCommand(textToSend, userMessage.file, history, activeMode);
      setIsThinking(false);

      // Handle Immediate Local UI Changes (like mode switching)
      if (result.intent === 'switch_to_ai') {
        setActiveBrain('ai');
      } else if (result.intent === 'switch_to_local') {
        setActiveBrain('local');
      }

      if (result.intent === 'system_health' && result.data && typeof result.data === 'string' && result.data.includes('|')) {
        setDashboardStats(result.data);
        setShowDashboard(true);
        setContextColor('green');
      } else {
        setContextColor('blue');
      }

      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        type: 'ai',
        text: result.data,
        intent: result.intent,
        steps: result.steps,
        remote_url: result.remote_url // Capture remote URL if provided
      }]);

      // Silence verbal response for specific intents (opening apps/files/folders)
      const SILENT_INTENTS = ['open_app', 'open_folder', 'open_file'];
      if (!SILENT_INTENTS.includes(result.intent)) {
        speak(result.data);
      } else {
        console.log(`Nana: Action performed silently for intent: ${result.intent}`);
      }
    }, 1200);
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      // Validate file size (10MB limit)
      const maxSize = 10 * 1024 * 1024;
      if (file.size > maxSize) {
        alert(`File too large! Maximum size is ${maxSize / (1024 * 1024)}MB`);
        return;
      }

      // Validate file type
      const allowedExtensions = ['.txt', '.py', '.json', '.csv', '.md', '.log', '.js', '.html', '.css', '.pdf', '.docx', '.jpg', '.png', '.gif'];
      const fileExt = '.' + file.name.split('.').pop().toLowerCase();

      if (!allowedExtensions.includes(fileExt)) {
        alert(`File type not supported. Allowed: ${allowedExtensions.join(', ')}`);
        return;
      }

      setAttachment(file);
    }
  };

  const removeAttachment = () => setAttachment(null);

  const renderMessage = (msg) => (
    <div
      key={msg.id}
      className={`message-bubble ${msg.type === 'user' ? 'message-user' : 'message-ai'}`}
    >
      {msg.file && (
        <div className="file-attachment-preview">
          {msg.file.type.startsWith('image/') ? <ImageIcon size={16} /> : <FileText size={16} />}
          <span>{msg.file.name}</span>
        </div>
      )}
      {msg.text}

      {msg.type === 'ai' && (
        <button
          className="copy-msg-btn"
          onClick={() => copyToClipboard(msg.text)}
          title="Copy to clipboard"
        >
          <Copy size={12} />
        </button>
      )}

      {msg.intent === 'suggest_ai' && (
        <div style={{ marginTop: '0.75rem' }}>
          <button
            className="mini-icon-btn tool-btn"
            onClick={() => {
              const lastUserMsg = messages.slice().reverse().find(m => m.type === 'user');
              handleModeSwitch('ai', lastUserMsg ? lastUserMsg.text : null);
            }}
            style={{ padding: '8px 12px', background: 'var(--accent-primary)', color: 'white', border: 'none' }}
          >
            <Zap size={14} style={{ marginRight: '6px' }} /> Switch to AI Brain
          </button>
        </div>
      )}

      {msg.remote_url && (
        <div style={{ marginTop: '0.75rem' }}>
          <a
            href={msg.remote_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mini-icon-btn tool-btn"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '8px 12px',
              background: '#10b981',
              color: 'white',
              textDecoration: 'none',
              borderRadius: '8px'
            }}
          >
            <Smartphone size={14} style={{ marginRight: '6px' }} /> Open Remote Control
          </a>
        </div>
      )}
      {msg.steps && (
        <div className="agent-steps-timeline">
          {msg.steps.map((step, idx) => (
            <div key={idx} className="agent-step-item">
              <div className="agent-badge">{step.agent}</div>
              <div className="agent-output-mini">{step.output.substring(0, 100)}...</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div className={`app-container ${theme}`}>
      <header className="nana-header glass">
        <div className="header-left">
          <div className={`nana-status-dot ${isSpeaking || isListening ? 'active' : ''} context-${contextColor}`}>
            <Zap size={10} color="white" fill="white" />
          </div>
          <h1 className="nana-title">Nana</h1>
        </div>

        <div className="header-center brain-selector-mobile">
          <button
            className={`brain-btn ${activeBrain === 'local' ? 'active' : ''}`}
            onClick={() => handleModeSwitch('local')}
            title="Local Engine"
          >
            <Monitor size={14} />
          </button>
          <button
            className={`brain-btn ${activeBrain === 'ai' ? 'active' : ''}`}
            onClick={() => handleModeSwitch('ai')}
            title="AI Brain"
          >
            <Zap size={14} />
          </button>
        </div>

        <div className="header-right">
          <button
            className="icon-button mobile-hide"
            onClick={() => setUseVoice(!useVoice)}
            title={useVoice ? "Mute Nana" : "Unmute Nana"}
          >
            {useVoice ? <Monitor size={18} /> : <MessageSquare size={18} />}
          </button>
          <button
            className="icon-button"
            onClick={() => setShowSettings(true)}
            title="Settings"
          >
            <SettingsIcon size={18} />
          </button>
        </div>
      </header>

      <main className="chat-container">
        <div className="messages">
          {messages.map((m) => renderMessage(m))}
          {isThinking && (
            <div className="message-bubble message-ai" style={{ display: 'flex', gap: '4px', padding: '0.75rem 1rem' }}>
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--text-secondary)' }}
                />
              ))}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-area">
          {attachment && (
            <div className="attachment-preview-bar">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={16} color="var(--accent-primary)" />
                <span style={{ fontSize: '0.8rem', maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {attachment.name}
                </span>
              </div>
              <button onClick={removeAttachment} className="remove-attachment">
                <X size={14} />
              </button>
            </div>
          )}
          <div className="quick-launch-bar">
            {isListening && lastHeard && (
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginRight: 'auto', paddingLeft: '10px' }}>
                Heard: <strong>{lastHeard}</strong>
              </span>
            )}
            <button className="mini-icon-btn" onClick={() => handleSend('Open Calculator')} title="Calculator"><Monitor size={14} /></button>
            <button className="mini-icon-btn" onClick={() => handleSend('Open Notepad')} title="Notepad"><FileText size={14} /></button>
            <button className="mini-icon-btn" onClick={() => handleSend('Open Browser')} title="Browser"><Zap size={14} /></button>
            <button className="mini-icon-btn" onClick={() => handleSend('Open Settings')} title="Settings"><SettingsIcon size={14} /></button>
            <div className="bar-separator" />
            <button className="mini-icon-btn tool-btn" onClick={() => handleSend('Read my clipboard')} title="Paste (Read Clipboard)"><Clipboard size={14} /></button>
            <button className="mini-icon-btn tool-btn" onClick={() => setInput('Nana, edit my file  with content ""')} title="Edit File"><Edit3 size={14} /></button>
            <button className="mini-icon-btn tool-btn danger-tool" onClick={() => setInput('Nana, delete the file ')} title="Delete File"><Trash2 size={14} /></button>
          </div>
          <div className="input-row">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
            <button
              className="icon-button"
              onClick={() => fileInputRef.current?.click()}
              title="Attach a file"
            >
              <Paperclip size={20} />
            </button>
            <button
              className={`icon-button ${isListening ? 'listening-active' : ''}`}
              onClick={toggleListening}
              title={isListening ? "Stop Listening" : "Start Always-On Listening"}
            >
              {isListening ? <Mic size={20} color="var(--danger)" /> : <Mic size={20} />}
            </button>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder={isListening ? "Listening..." : "Ask Nana anything..."}
              className="main-input"
            />
            <button className="send-button" onClick={handleSend}>
              <Send size={20} color="white" />
            </button>
          </div>
        </div>
      </main>

      {showDashboard && dashboardStats && (
        <div className="dashboard-panel">
          <div className="dashboard-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Monitor size={18} color="var(--accent-primary)" />
              <span style={{ fontWeight: 700 }}>System Health</span>
            </div>
            <button className="icon-button" onClick={() => setShowDashboard(false)}>
              <X size={16} />
            </button>
          </div>
          <div className="dashboard-content">
            {weather && (
              <div className="widget-card weather-widget">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span className="stat-value" style={{ fontSize: '1.5rem' }}>{weather.temp}</span>
                    <span className="stat-label" style={{ display: 'block' }}>{weather.city}</span>
                  </div>
                  <Sun size={32} color="var(--accent-primary)" />
                </div>
                <span className="stat-label">{weather.condition}</span>
              </div>
            )}

            <div className="widget-card stats-grid">
              {dashboardStats?.split('|').filter(stat => stat.includes(':')).map((stat, i) => (
                <div key={i} className="mini-stat">
                  <span className="stat-label">{stat.split(':')[0]?.trim() || 'N/A'}</span>
                  <span className="stat-value" style={{ fontSize: '0.9rem' }}>{stat.split(':')[1]?.trim() || 'N/A'}</span>
                </div>
              ))}
            </div>

            <div className="widget-card notes-widget">
              <span className="stat-label">Sticky Notes</span>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="notes-area"
              />
            </div>
          </div>
        </div>
      )}

      {showSettings && (
        <div className="settings-overlay" onClick={() => setShowSettings(false)}>
          <div className="settings-modal" onClick={e => e.stopPropagation()}>
            <div className="settings-header">
              <h2>Settings</h2>
              <button className="icon-button" onClick={() => setShowSettings(false)}>
                <X size={20} />
              </button>
            </div>

            <div className="settings-section">
              <span className="settings-label">Appearance</span>
              <div className="theme-options">
                <button
                  className={`theme-btn ${theme === 'theme-light' ? 'active' : ''}`}
                  onClick={() => setTheme('theme-light')}
                >
                  <Sun size={18} /> White Pearl
                </button>
                <button
                  className={`theme-btn ${theme === 'theme-dark' ? 'active' : ''}`}
                  onClick={() => setTheme('theme-dark')}
                >
                  <Moon size={18} /> Onyx Dark
                </button>
              </div>
            </div>

            <div className="settings-section">
              <span className="settings-label">Preferences</span>
              <div className="toggle-item">
                <span style={{ fontWeight: 500 }}>Voice Synthesis</span>
                <label className="switch">
                  <input
                    type="checkbox"
                    checked={useVoice}
                    onChange={() => setUseVoice(!useVoice)}
                  />
                  <span className="slider"></span>
                </label>
              </div>
              <div className="toggle-item">
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontWeight: 500 }}>Continuous Conversation</span>
                  <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>Auto-listen after responses</span>
                </div>
                <label className="switch">
                  <input
                    type="checkbox"
                    checked={continuousVoice}
                    onChange={() => setContinuousVoice(!continuousVoice)}
                  />
                  <span className="slider"></span>
                </label>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
