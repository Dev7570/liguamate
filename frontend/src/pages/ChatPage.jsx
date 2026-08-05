/**
 * Chat Page — The core LinguaMate experience
 * Premium dark chat interface with Mira AI companion
 * Features: Real-time SSE token streaming + Voice recording (Whisper STT) + TTS voice output
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Canvas } from '@react-three/fiber';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import RoleplayScene from '../components/chat/RoleplayScene';
import '../styles/chat.css';

// Suggested conversation starters
const SUGGESTIONS = [
  "Hi Mira! I want to practice English today 😊",
  "Can you help me prepare for a job interview?",
  "Let's talk about my favorite movie!",
  "I made some mistakes yesterday. Can we review?",
  "Tell me today's speaking mission!",
  "I'm feeling nervous about my presentation...",
];

export default function ChatPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // State
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Streaming state
  const [streamingContent, setStreamingContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const abortStreamRef = useRef(null);

  // Voice recording state
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [voiceError, setVoiceError] = useState(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingTimerRef = useRef(null);

  // Text-to-Speech state
  const [autoSpeak, setAutoSpeak] = useState(() => {
    return localStorage.getItem('linguamate_autospeak') !== 'false';
  });
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speakingMsgId, setSpeakingMsgId] = useState(null);

  // Refs
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, streamingContent]);

  // Load conversation history & check for scenario redirect
  useEffect(() => {
    loadConversations();
    if (location.state?.initialPrompt) {
      setInput(location.state.initialPrompt);
    }
  }, [location.state]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortStreamRef.current) abortStreamRef.current();
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      window.speechSynthesis?.cancel();
    };
  }, []);

  // ── Text-to-Speech ────────────────────────────────────────────────────
  const speakText = useCallback((text, msgId = null) => {
    if (!window.speechSynthesis) return;

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    // Clean text — remove emojis and special chars for cleaner speech
    const cleanText = text
      .replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '')
      .replace(/[*_~`#]/g, '')
      .trim();

    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 0.95;
    utterance.pitch = 1.1;
    utterance.volume = 1;
    utterance.lang = 'en-US';

    // Try to pick a natural female English voice
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v =>
      v.lang.startsWith('en') && v.name.toLowerCase().includes('female')
    ) || voices.find(v =>
      v.lang.startsWith('en') && (v.name.includes('Zira') || v.name.includes('Samantha') || v.name.includes('Google US English'))
    ) || voices.find(v => v.lang.startsWith('en'));

    if (preferred) utterance.voice = preferred;

    utterance.onstart = () => {
      setIsSpeaking(true);
      setSpeakingMsgId(msgId);
    };
    utterance.onend = () => {
      setIsSpeaking(false);
      setSpeakingMsgId(null);
    };
    utterance.onerror = () => {
      setIsSpeaking(false);
      setSpeakingMsgId(null);
    };

    window.speechSynthesis.speak(utterance);
  }, []);

  const stopSpeaking = useCallback(() => {
    window.speechSynthesis?.cancel();
    setIsSpeaking(false);
    setSpeakingMsgId(null);
  }, []);

  const toggleAutoSpeak = useCallback(() => {
    setAutoSpeak(prev => {
      const next = !prev;
      localStorage.setItem('linguamate_autospeak', next.toString());
      if (!next) stopSpeaking();
      return next;
    });
  }, [stopSpeaking]);

  // Load voices (Chrome loads them async)
  useEffect(() => {
    window.speechSynthesis?.getVoices();
    window.speechSynthesis?.addEventListener?.('voiceschanged', () => {
      window.speechSynthesis.getVoices();
    });
  }, []);

  const loadConversations = async () => {
    try {
      const convs = await api.getConversations();
      setConversations(convs);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  const startNewConversation = async () => {
    try {
      const conv = await api.startConversation();
      setConversationId(conv.id);
      setMessages([]);
      setSidebarOpen(false);
      loadConversations();
    } catch (err) {
      console.error('Failed to start conversation:', err);
    }
  };

  const loadConversation = async (convId) => {
    try {
      const msgs = await api.getMessages(convId);
      setConversationId(convId);
      setMessages(msgs);
      setSidebarOpen(false);
    } catch (err) {
      console.error('Failed to load conversation:', err);
    }
  };

  const sendMessage = useCallback(async (messageText = null) => {
    const text = messageText || input.trim();
    if (!text || isLoading || isStreaming) return;

    // Start conversation if needed
    let activeConvId = conversationId;
    if (!activeConvId) {
      try {
        const conv = await api.startConversation();
        activeConvId = conv.id;
        setConversationId(conv.id);
      } catch (err) {
        console.error('Failed to start conversation:', err);
        return;
      }
    }

    // Add user message immediately
    const userMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);
    setIsStreaming(true);
    setStreamingContent('');

    // Use SSE streaming
    const abort = api.sendMessageStream(
      activeConvId,
      text,
      // onToken — append each token to the streaming content
      (token) => {
        setStreamingContent((prev) => prev + token);
      },
      // onDone — finalize the message with full metadata + auto-speak
      (event) => {
        setIsStreaming(false);
        setStreamingContent('');
        setIsLoading(false);

        const msgId = event.message_id || `msg-${Date.now()}`;
        const assistantMsg = {
          id: msgId,
          role: 'assistant',
          content: event.content,
          corrections: event.corrections ? event.corrections.map((c) => ({
            original: c.original,
            corrected: c.corrected,
            explanation: c.explanation,
          })) : null,
          vocab_used: event.vocab_used,
          mood_signal: event.mood_signal,
          created_at: event.created_at || new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
        loadConversations();
        inputRef.current?.focus();

        // Auto-speak Mira's response
        if (autoSpeak && event.content) {
          speakText(event.content, msgId);
        }
      },
      // onError — show error message
      (errorMsg) => {
        setIsStreaming(false);
        setStreamingContent('');
        setIsLoading(false);
        setMessages((prev) => [
          ...prev,
          {
            id: `error-${Date.now()}`,
            role: 'assistant',
            content: `I'm having trouble connecting right now. Let me try again in a moment! 😊 (${errorMsg})`,
            created_at: new Date().toISOString(),
          },
        ]);
        inputRef.current?.focus();
      }
    );

    abortStreamRef.current = abort;
  }, [input, isLoading, isStreaming, conversationId, autoSpeak, speakText]);

  // ── Voice Recording ─────────────────────────────────────────────────────
  const startRecording = async () => {
    setVoiceError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : '';
      const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);

      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        // Stop all tracks
        stream.getTracks().forEach((track) => track.stop());
        clearInterval(recordingTimerRef.current);
        setRecordingTime(0);

        const audioBlob = new Blob(audioChunksRef.current, { type: mediaRecorder.mimeType || 'audio/webm' });

        if (audioBlob.size < 1000) {
          // Too short, ignore
          setIsRecording(false);
          setVoiceError('Recording was too short. Please hold the microphone button and speak.');
          return;
        }

        // Transcribe the audio
        setIsTranscribing(true);
        try {
          const text = await api.transcribeAudio(audioBlob);
          if (text && text.trim()) {
            // Automatically send the voice message to Mira!
            sendMessage(text.trim());
          } else {
            setVoiceError('No speech detected in your recording. Please try speaking clearly.');
          }
        } catch (err) {
          console.error('Transcription failed:', err);
          setVoiceError(`Voice transcription failed: ${err.message || 'Unable to connect to voice service.'}`);
        } finally {
          setIsTranscribing(false);
          setIsRecording(false);
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(250); // Collect data every 250ms
      setIsRecording(true);

      // Start recording timer
      setRecordingTime(0);
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error('Microphone access denied:', err);
      setVoiceError('Microphone access denied. Please allow microphone permissions in your browser.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const formatRecordingTime = (seconds) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatTime = (dateStr) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <div className="chat-layout">
      {/* ── Sidebar ──────────────────────────────────────────── */}
      <aside className={`chat-sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="chat-sidebar-header">
          <div className="chat-sidebar-logo">
            <div className="chat-sidebar-logo-icon">🌟</div>
            <span className="chat-sidebar-logo-text">LinguaMate</span>
          </div>
        </div>

        <div className="chat-sidebar-actions">
          <button className="new-chat-btn" onClick={startNewConversation}>
            ✨ New Conversation
          </button>
        </div>

        <div className="chat-history-list">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`chat-history-item ${conv.id === conversationId ? 'active' : ''}`}
              onClick={() => loadConversation(conv.id)}
            >
              💬 {conv.summary || `Chat · ${conv.message_count} messages`}
            </div>
          ))}
          {conversations.length === 0 && (
            <p style={{ padding: '16px', color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center' }}>
              No conversations yet. Start chatting with Mira!
            </p>
          )}
        </div>

        <div className="chat-sidebar-footer">
          <div className="user-profile-mini">
            <div className="user-avatar">{user?.avatar_emoji || '😊'}</div>
            <div className="user-info">
              <div className="user-name">{user?.name || 'User'}</div>
              <div className="user-level">{user?.english_level || 'beginner'}</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '4px', marginTop: '8px', flexWrap: 'wrap' }}>
            <button
              className="btn btn-ghost"
              style={{ flex: 1, fontSize: '0.8rem' }}
              onClick={() => navigate('/dashboard')}
            >
              📊 Dashboard
            </button>
            <button
              className="btn btn-ghost"
              style={{ flex: 1, fontSize: '0.8rem' }}
              onClick={() => navigate('/tasks')}
            >
              🎯 Tasks
            </button>
            <button
              className="btn btn-ghost"
              style={{ flex: 1, fontSize: '0.8rem' }}
              onClick={() => navigate('/activities')}
            >
              🎮 Activities
            </button>
          </div>
          <button
            className="btn btn-ghost w-full mt-sm"
            style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}
            onClick={logout}
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* ── Main Chat ────────────────────────────────────────── */}
      <main className={`chat-main ${location.state?.scenarioTitle ? 'has-3d-scene' : ''}`}>
        
        {location.state?.scenarioTitle && (
          <div className="chat-scene-container">
            <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
              <RoleplayScene scenarioTitle={location.state.scenarioTitle} />
            </Canvas>
          </div>
        )}

        {/* Header */}
        <header className="chat-header">
          <div className="chat-header-left">
            <button
              className="btn btn-ghost btn-icon"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              style={{ display: 'none' }}
              id="menu-toggle"
            >
              ☰
            </button>
            <div className="mira-status">
              <div className="mira-avatar">🤗</div>
              <div className="mira-info">
                <h3>Mira</h3>
                <span className={isStreaming ? 'mira-typing' : ''}>
                  {isStreaming ? '● Typing...' : '● Always here for you'}
                </span>
              </div>
            </div>
          </div>
          <div className="chat-header-right">
            <button
              className={`btn btn-ghost btn-icon tts-toggle ${autoSpeak ? 'active' : ''}`}
              onClick={toggleAutoSpeak}
              title={autoSpeak ? 'Voice ON — Mira speaks aloud' : 'Voice OFF — Text only'}
              id="tts-toggle-btn"
            >
              {autoSpeak ? '🔊' : '🔇'}
            </button>
            {isSpeaking && (
              <button
                className="btn btn-ghost btn-icon stop-speaking-btn"
                onClick={stopSpeaking}
                title="Stop speaking"
              >
                ⏹️
              </button>
            )}
            <button
              className="btn btn-ghost btn-icon"
              onClick={() => navigate('/activities')}
              title="Activities & Badges"
            >
              🎮
            </button>
            <button
              className="btn btn-ghost btn-icon"
              onClick={() => navigate('/tasks')}
              title="Today's Missions"
            >
              🎯
            </button>
            <button
              className="btn btn-ghost btn-icon"
              onClick={() => navigate('/dashboard')}
              title="Dashboard"
            >
              📊
            </button>
          </div>
        </header>

        {/* Messages */}
        <div className="chat-messages">
          <div className="chat-messages-inner">
            {messages.length === 0 && !isStreaming ? (
              <div className="chat-welcome">
                <div className="welcome-icon">🤗</div>
                <h2 className="welcome-title">
                  Hey{user?.name ? `, ${user.name}` : ''}!
                </h2>
                <p className="welcome-subtitle">
                  I'm Mira, your English companion. I'm here to chat, help you practice, 
                  and make you feel confident speaking English. No judgement — just friendship! 💜
                </p>
                <div className="welcome-suggestions">
                  {SUGGESTIONS.map((s, i) => (
                    <button
                      key={i}
                      className="suggestion-chip"
                      onClick={() => sendMessage(s)}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg) => (
                  <div key={msg.id} className={`message message-${msg.role}`}>
                    <div className="message-avatar">
                      {msg.role === 'user' ? (user?.avatar_emoji || '😊') : '🤗'}
                    </div>
                    <div>
                      <div className="message-content">
                        {msg.content}
                      </div>

                      {/* Inline corrections */}
                      {msg.corrections && msg.corrections.length > 0 && (
                        <div className="message-corrections">
                          {msg.corrections.map((c, i) => (
                            <div key={i} className="correction-item">
                              <span className="correction-original">{c.original}</span>
                              <span className="correction-arrow">→</span>
                              <span className="correction-fixed">{c.corrected}</span>
                              {c.explanation && (
                                <div className="correction-explanation">{c.explanation}</div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Vocab chips */}
                      {msg.vocab_used && msg.vocab_used.length > 0 && (
                        <div className="vocab-chips">
                          {msg.vocab_used.map((word, i) => (
                            <span key={i} className="vocab-chip">📚 {word}</span>
                          ))}
                        </div>
                      )}

                      <div className="message-meta">
                        <span className="message-time">{formatTime(msg.created_at)}</span>
                        {msg.role === 'assistant' && (
                          <button
                            className={`speak-btn ${speakingMsgId === msg.id ? 'speaking' : ''}`}
                            onClick={() => speakingMsgId === msg.id ? stopSpeaking() : speakText(msg.content, msg.id)}
                            title={speakingMsgId === msg.id ? 'Stop speaking' : 'Listen to Mira'}
                          >
                            {speakingMsgId === msg.id ? '⏹️' : '🔊'}
                          </button>
                        )}
                        {msg.mood_signal && msg.mood_signal !== 'neutral' && (
                          <span className="vocab-chip" style={{ marginLeft: '4px' }}>
                            {msg.mood_signal === 'confident' ? '💪' :
                             msg.mood_signal === 'hesitant' ? '🤔' :
                             msg.mood_signal === 'excited' ? '🎉' :
                             msg.mood_signal === 'frustrated' ? '😤' : ''}
                            {' '}{msg.mood_signal}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {/* Live streaming message */}
                {isStreaming && streamingContent && (
                  <div className="message message-assistant">
                    <div className="message-avatar" style={{ background: 'var(--gradient-primary)' }}>
                      🤗
                    </div>
                    <div>
                      <div className="message-content streaming-content">
                        {streamingContent}
                        <span className="streaming-cursor" />
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Typing indicator (before first token arrives) */}
            {isLoading && !streamingContent && (
              <div className="typing-indicator">
                <div className="message-avatar" style={{ background: 'var(--gradient-primary)' }}>
                  🤗
                </div>
                <div className="typing-dots">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div className="chat-input-area">
          {voiceError && (
            <div className="voice-error-banner" style={{
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              color: '#f87171',
              padding: '8px 14px',
              borderRadius: '12px',
              fontSize: '0.85rem',
              marginBottom: '10px',
              maxWidth: 'var(--chat-max-width)',
              margin: '0 auto 10px auto',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <span>⚠️ {voiceError}</span>
              <button
                onClick={() => setVoiceError(null)}
                style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer', fontSize: '1rem', padding: '0 4px' }}
              >
                ✕
              </button>
            </div>
          )}
          <div className="chat-input-wrapper">
            {/* Voice Recording Button */}
            <button
              className={`mic-btn ${isRecording ? 'recording' : ''} ${isTranscribing ? 'transcribing' : ''}`}
              onClick={toggleRecording}
              disabled={isLoading || isStreaming || isTranscribing}
              title={isRecording ? 'Stop recording' : isTranscribing ? 'Transcribing...' : 'Voice input'}
              id="voice-record-btn"
            >
              {isTranscribing ? (
                <span className="mic-spinner" />
              ) : isRecording ? (
                <>
                  <span className="mic-pulse" />
                  <span className="recording-time">{formatRecordingTime(recordingTime)}</span>
                </>
              ) : (
                '🎙️'
              )}
            </button>

            <div className="chat-input-container">
              <textarea
                ref={inputRef}
                className="chat-input"
                placeholder={isRecording ? 'Listening...' : isTranscribing ? 'Transcribing your voice...' : 'Type your message to Mira...'}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                disabled={isRecording}
                id="chat-message-input"
              />
            </div>
            <button
              className="send-btn"
              onClick={() => sendMessage()}
              disabled={!input.trim() || isLoading || isStreaming}
              id="send-message-btn"
            >
              ➤
            </button>
          </div>
          <div className="chat-input-hint">
            {isRecording
              ? 'Tap 🎙️ to stop recording'
              : 'Press Enter to send · Shift+Enter for new line · 🎙️ for voice'}
          </div>
        </div>
      </main>
    </div>
  );
}
