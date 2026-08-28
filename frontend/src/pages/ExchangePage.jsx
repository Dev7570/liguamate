/**
 * Exchange Page — Social Language Exchange with real-time WebSocket chat
 * Auto-matches with AI partner if no human found within 10 seconds
 */
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import '../styles/exchange.css';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE = API_BASE.replace(/^http/, 'ws');

const AI_FALLBACK_SECONDS = 10;

export default function ExchangePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState('idle'); // 'idle'|'waiting'|'matched'|'chatting'|'ended'
  const [sessionId, setSessionId] = useState(null);
  const [partner, setPartner] = useState(null);
  const [isAi, setIsAi] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [sessionTime, setSessionTime] = useState(0);
  const [dots, setDots] = useState(1);
  const [waitTime, setWaitTime] = useState(0);
  const wsRef = useRef(null);
  const timerRef = useRef(null);
  const dotsRef = useRef(null);
  const msgEndRef = useRef(null);
  const typingTimerRef = useRef(null);
  const pollRef = useRef(null);
  const waitTimerRef = useRef(null);

  const language = user?.target_language || 'English';
  const token = localStorage.getItem('linguamate_token');

  useEffect(() => {
    return () => {
      clearInterval(timerRef.current);
      clearInterval(dotsRef.current);
      clearInterval(pollRef.current);
      clearInterval(waitTimerRef.current);
      wsRef.current?.close();
    };
  }, []);

  useEffect(() => {
    msgEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const joinPool = async () => {
    setStatus('waiting');
    setWaitTime(0);
    dotsRef.current = setInterval(() => setDots(d => d >= 3 ? 1 : d+1), 500);
    waitTimerRef.current = setInterval(() => setWaitTime(t => t+1), 1000);

    try {
      const data = await api.joinExchange();
      if (data.status === 'matched') {
        clearInterval(waitTimerRef.current);
        clearInterval(dotsRef.current);
        await connectToSession(data.session_id, data.partner, data.is_ai);
      } else {
        // Poll for match, with AI fallback after timeout
        pollRef.current = setInterval(async () => {
          try {
            const s = await api.getExchangeStatus();
            if (s.status === 'matched') {
              clearInterval(pollRef.current);
              clearInterval(dotsRef.current);
              clearInterval(waitTimerRef.current);
              await connectToSession(s.session_id, s.partner, s.is_ai);
            }
          } catch {}
        }, 2000);
      }
    } catch (e) { setStatus('idle'); alert(e.message||'Failed to join pool'); }
  };

  // Auto-fallback to AI after timeout
  useEffect(() => {
    if (status === 'waiting' && waitTime >= AI_FALLBACK_SECONDS) {
      matchWithAi();
    }
  }, [waitTime, status]);

  const matchWithAi = async () => {
    clearInterval(pollRef.current);
    clearInterval(dotsRef.current);
    clearInterval(waitTimerRef.current);
    try {
      const data = await api.joinAiExchange();
      if (data.status === 'matched') {
        await connectToSession(data.session_id, data.partner, true);
      }
    } catch (e) {
      setStatus('idle');
    }
  };

  const connectToSession = async (sid, partnerInfo, aiSession = false) => {
    setSessionId(sid);
    setIsAi(!!aiSession);
    const s = partnerInfo || (await api.getExchangeStatus());
    const p = s.partner || s;
    setPartner(p);
    setStatus('chatting');
    const partnerLabel = aiSession ? `${p.name || 'AI Partner'} (AI)` : (p.name || 'a partner');
    setMessages([{ type:'system', content:`You matched with ${partnerLabel}! Start chatting in ${language}. 🌟` }]);
    timerRef.current = setInterval(() => setSessionTime(t => t+1), 1000);
    const ws = new WebSocket(`${WS_BASE}/exchange/chat/${sid}?token=${token}`);
    ws.onopen = () => {};
    ws.onmessage = e => {
      const data = JSON.parse(e.data);
      if (data.type === 'message') setMessages(prev => [...prev, { type:'partner', content:data.content, sender:data.sender_name }]);
      else if (data.type === 'typing') setIsTyping(data.is_typing);
      else if (data.type === 'partner_left') { setStatus('ended'); setMessages(prev => [...prev, { type:'system', content:'Your partner left the session.' }]); clearInterval(timerRef.current); }
      else if (data.type === 'partner_connected') setMessages(prev => [...prev, { type:'system', content:`${data.partner_name} connected!` }]);
    };
    ws.onerror = () => { setStatus('ended'); setMessages(prev => [...prev, { type:'system', content:'Connection error. Session ended.' }]); };
    ws.onclose = () => { if (status === 'chatting') setStatus('ended'); };
    wsRef.current = ws;
  };

  const sendMessage = () => {
    if (!input.trim() || !wsRef.current || wsRef.current.readyState !== 1) return;
    wsRef.current.send(JSON.stringify({ type:'message', content:input.trim() }));
    setMessages(prev => [...prev, { type:'self', content:input.trim() }]);
    setInput('');
  };

  const handleTyping = (e) => {
    setInput(e.target.value);
    if (wsRef.current?.readyState === 1) {
      wsRef.current.send(JSON.stringify({ type:'typing', is_typing:true }));
      clearTimeout(typingTimerRef.current);
      typingTimerRef.current = setTimeout(() => wsRef.current?.readyState===1 && wsRef.current.send(JSON.stringify({ type:'typing', is_typing:false })), 1000);
    }
  };

  const leaveSession = async () => {
    clearInterval(timerRef.current);
    clearInterval(pollRef.current);
    clearInterval(waitTimerRef.current);
    wsRef.current?.close();
    try { await api.leaveExchange(); } catch {}
    setStatus('ended');
  };

  const formatTime = s => `${Math.floor(s/60).toString().padStart(2,'0')}:${(s%60).toString().padStart(2,'0')}`;

  return (
    <div className="ex-layout">
      <header className="ex-header">
        <button className="ex-back-btn" onClick={() => { leaveSession(); navigate('/chat'); }}>← Back to Chat</button>
        <div className="ex-header-mid">
          <span>🌐</span>
          <h1>Language Exchange</h1>
        </div>
        <div className="ex-lang-pill">{language}</div>
      </header>

      <div className="ex-content">
        {/* IDLE */}
        {status === 'idle' && (
          <div className="ex-lobby">
            <div className="ex-globe-anim">🌐</div>
            <h2>Find a Language Partner</h2>
            <p className="ex-lobby-sub">Practice <strong>{language}</strong> with a real person or AI partner.</p>
            <div className="ex-info-cards">
              <div className="ex-info-card">💬<br/>Live text chat</div>
              <div className="ex-info-card">🌍<br/>Matched by language & level</div>
              <div className="ex-info-card">🤖<br/>AI partner if no one's online</div>
            </div>
            <div className="ex-btn-group">
              <button className="ex-join-btn" onClick={joinPool} id="find-partner-btn">🔍 Find a Partner</button>
              <button className="ex-ai-btn" onClick={matchWithAi} id="ai-partner-btn">🤖 Practice with AI</button>
            </div>
          </div>
        )}

        {/* WAITING */}
        {status === 'waiting' && (
          <div className="ex-lobby">
            <div className="ex-matching-anim">
              <div className="ex-pulse-ring"/>
              <div className="ex-pulse-ring" style={{animationDelay:'0.5s'}}/>
              <div className="ex-pulse-ring" style={{animationDelay:'1s'}}/>
              <span className="ex-match-icon">🔍</span>
            </div>
            <h2>Looking for a partner{'.'.repeat(dots)}</h2>
            <p className="ex-lobby-sub">Searching for someone learning <strong>{language}</strong>...</p>
            <div className="ex-wait-info">
              <div className="ex-wait-timer">{waitTime}s</div>
              <p className="ex-wait-hint">
                {waitTime < AI_FALLBACK_SECONDS
                  ? `AI partner in ${AI_FALLBACK_SECONDS - waitTime}s if no one joins`
                  : 'Matching with AI partner...'}
              </p>
            </div>
            <div className="ex-btn-group">
              <button className="ex-ai-btn-sm" onClick={matchWithAi}>🤖 Match with AI now</button>
              <button className="ex-cancel-btn" onClick={() => { clearInterval(pollRef.current); clearInterval(dotsRef.current); clearInterval(waitTimerRef.current); api.leaveExchange().catch(()=>{}); setStatus('idle'); }}>Cancel</button>
            </div>
          </div>
        )}

        {/* CHATTING */}
        {(status === 'chatting' || status === 'ended') && (
          <div className="ex-chat-layout">
            <div className="ex-chat-header">
              <div className="ex-partner-info">
                <div className="ex-partner-avatar">{isAi ? '🤖' : '👤'}</div>
                <div>
                  <div className="ex-partner-name">{partner?.name || 'Partner'}{isAi && <span className="ex-ai-badge">AI</span>}</div>
                  <div className="ex-partner-level">{language} · {partner?.level || 'learner'}</div>
                </div>
              </div>
              <div className="ex-session-timer">{formatTime(sessionTime)}</div>
              {status === 'chatting' && <button className="ex-leave-btn" onClick={leaveSession}>End Session</button>}
            </div>

            <div className="ex-messages">
              {messages.map((m, i) => (
                <div key={i} className={`ex-msg ex-msg-${m.type}`}>
                  {m.type === 'system' ? (
                    <div className="ex-system-msg">{m.content}</div>
                  ) : (
                    <div className="ex-bubble-wrap" style={{justifyContent:m.type==='self'?'flex-end':'flex-start'}}>
                      <div className={`ex-bubble ex-bubble-${m.type}`}>{m.content}</div>
                    </div>
                  )}
                </div>
              ))}
              {isTyping && <div className="ex-typing-indicator"><span/><span/><span/></div>}
              <div ref={msgEndRef}/>
            </div>

            {status === 'chatting' && (
              <div className="ex-input-bar">
                <input className="ex-input" placeholder={`Chat in ${language}...`} value={input} onChange={handleTyping}
                  onKeyDown={e => e.key==='Enter'&&!e.shiftKey&&(e.preventDefault(),sendMessage())}/>
                <button className="ex-send-btn" onClick={sendMessage} disabled={!input.trim()}>Send →</button>
              </div>
            )}
            {status === 'ended' && (
              <div className="ex-ended-bar">
                <p>Session ended — great practice! 🌟</p>
                <button className="ex-join-btn" onClick={() => { setStatus('idle'); setMessages([]); setSessionTime(0); setIsAi(false); }}>Find Another Partner</button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
