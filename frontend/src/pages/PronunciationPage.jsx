/**
 * Pronunciation Page — Real-time voice pronunciation scoring
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import '../styles/pronunciation.css';

const LEVEL_LABELS = { beginner: '🌱 Beginner', intermediate: '🌿 Intermediate', advanced: '🌳 Advanced' };

export default function PronunciationPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const level = user?.english_level || 'beginner';

  const [words, setWords] = useState([]);
  const [phrases, setPhrases] = useState([]);
  const [currentItem, setCurrentItem] = useState(null);
  const [isPhrase, setIsPhrase] = useState(false);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [showConfetti, setShowConfetti] = useState(false);
  const [history, setHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('words');

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);
  const waveformRef = useRef(null);
  const analyserRef = useRef(null);
  const animFrameRef = useRef(null);

  useEffect(() => {
    loadWords();
    return () => { clearInterval(timerRef.current); cancelAnimationFrame(animFrameRef.current); };
  }, [level]);

  const loadWords = async () => {
    try {
      setLoading(true);
      const data = await api.getPronunciationWords(level);
      setWords(data.words || []);
      setPhrases(data.phrases || []);
      if (data.words?.length) { setCurrentItem(data.words[0]); setIsPhrase(false); }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const selectItem = (item, phrase = false) => { setCurrentItem(item); setIsPhrase(phrase); setResult(null); setShowConfetti(false); };

  const drawWaveform = useCallback(() => {
    if (!analyserRef.current || !waveformRef.current) return;
    const canvas = waveformRef.current;
    const ctx = canvas.getContext('2d');
    const data = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteTimeDomainData(data);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = 'rgba(139,92,246,0.9)';
    ctx.shadowBlur = 8;
    ctx.shadowColor = '#8b5cf6';
    ctx.beginPath();
    const sliceWidth = canvas.width / data.length;
    let x = 0;
    for (let i = 0; i < data.length; i++) {
      const v = data[i] / 128;
      const y = (v * canvas.height) / 2;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      x += sliceWidth;
    }
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();
    animFrameRef.current = requestAnimationFrame(drawWaveform);
  }, []);

  const startRecording = async () => {
    setResult(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 1024;
      source.connect(analyser);
      analyserRef.current = analyser;
      drawWaveform();
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';
      const recorder = new MediaRecorder(stream, { mimeType });
      audioChunksRef.current = [];
      recorder.ondataavailable = e => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        cancelAnimationFrame(animFrameRef.current);
        clearInterval(timerRef.current);
        setRecordingTime(0);
        const blob = new Blob(audioChunksRef.current, { type: mimeType });
        submitEvaluation(blob);
      };
      recorder.start(200);
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
      setRecordingTime(0);
      timerRef.current = setInterval(() => setRecordingTime(t => t + 1), 1000);
    } catch (e) { alert('Microphone access denied.'); }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state !== 'inactive') { mediaRecorderRef.current.stop(); setIsRecording(false); }
  };

  const submitEvaluation = async (blob) => {
    if (!currentItem) return;
    setIsEvaluating(true);
    try {
      const target = isPhrase ? currentItem.phrase : currentItem.word;
      const data = await api.evaluatePronunciation(blob, target, level);
      setResult(data);
      setHistory(prev => [{ ...data, item: target, timestamp: new Date().toLocaleTimeString() }, ...prev.slice(0, 9)]);
      if (data.score >= 80) { setShowConfetti(true); setTimeout(() => setShowConfetti(false), 3000); }
    } catch (e) { setResult({ error: e.message || 'Evaluation failed.' }); }
    finally { setIsEvaluating(false); }
  };

  const getScoreColor = s => s >= 90 ? '#10b981' : s >= 75 ? '#3b82f6' : s >= 55 ? '#f59e0b' : '#ef4444';
  const getAccuracyLabel = acc => ({ excellent: '🌟 Excellent!', good: '👍 Good!', fair: '🙂 Fair', needs_work: '💪 Keep Practicing!' })[acc] || '';
  const formatTime = s => `${Math.floor(s/60).toString().padStart(2,'0')}:${(s%60).toString().padStart(2,'0')}`;

  if (loading) return (
    <div className="pron-layout"><div className="pron-loading"><div className="pron-spinner"/><p>Loading practice words...</p></div></div>
  );

  return (
    <div className="pron-layout">
      {showConfetti && (
        <div className="pron-confetti-overlay">
          {[...Array(24)].map((_, i) => <div key={i} className="pron-confetti-particle" style={{ '--delay': `${Math.random()*1.5}s`, '--x': `${Math.random()*100}vw`, background: ['#8b5cf6','#10b981','#f59e0b','#3b82f6','#ec4899'][i%5] }} />)}
        </div>
      )}
      <header className="pron-header">
        <button onClick={() => navigate('/chat')} className="pron-back-btn">← Back to Chat</button>
        <div className="pron-header-title"><span>🎙️</span><h1>Pronunciation Coach</h1></div>
        <div className="pron-level-badge">{LEVEL_LABELS[level]}</div>
      </header>
      <div className="pron-content">
        <div className="pron-tabs">
          {[['words','📝 Words'],['phrases','💬 Phrases'],['history','📊 History']].map(([t,l]) => (
            <button key={t} className={`pron-tab${activeTab===t?' active':''}`} onClick={() => setActiveTab(t)}>{l}</button>
          ))}
        </div>
        <div className="pron-main-grid">
          <div className="pron-word-list">
            {activeTab==='words' && words.map((w,i) => (
              <button key={i} className={`pron-word-card${currentItem?.word===w.word&&!isPhrase?' selected':''}`} onClick={() => selectItem(w,false)}>
                <div className="pron-word-main">{w.word}</div>
                <div className="pron-word-phonetic">{w.phonetic}</div>
                <div className="pron-word-meaning">{w.meaning}</div>
              </button>
            ))}
            {activeTab==='phrases' && phrases.map((p,i) => (
              <button key={i} className={`pron-word-card${currentItem?.phrase===p.phrase&&isPhrase?' selected':''}`} onClick={() => selectItem(p,true)}>
                <div className="pron-word-main" style={{fontSize:'0.9rem'}}>{p.phrase}</div>
                <div className="pron-word-meaning">💡 {p.tip}</div>
              </button>
            ))}
            {activeTab==='history' && (history.length===0
              ? <div className="pron-empty">No history yet. Start practicing!</div>
              : history.map((h,i) => (
                <div key={i} className="pron-history-item">
                  <div className="pron-history-word">{h.item}</div>
                  <div className="pron-history-score" style={{color:getScoreColor(h.score)}}>{h.score}%</div>
                  <div className="pron-history-time">{h.timestamp}</div>
                </div>
              ))
            )}
          </div>

          {activeTab!=='history' && currentItem && (
            <div className="pron-practice-panel">
              <div className="pron-target-card">
                <div className="pron-target-label">Say this {isPhrase?'phrase':'word'}:</div>
                <div className="pron-target-word">{isPhrase?currentItem.phrase:currentItem.word}</div>
                {!isPhrase && <div className="pron-target-phonetic">{currentItem.phonetic}</div>}
                <div className="pron-target-meaning">{isPhrase?`💡 ${currentItem.tip}`:currentItem.meaning}</div>
              </div>

              <div className="pron-waveform-container">
                <canvas ref={waveformRef} className={`pron-waveform${isRecording?' active':''}`} width={480} height={80}/>
                {!isRecording && !isEvaluating && <div className="pron-waveform-idle">🎙️ Press the button below to start recording</div>}
                {isEvaluating && <div className="pron-waveform-idle"><div className="pron-spinner-sm"/>Evaluating your pronunciation...</div>}
              </div>

              <div className="pron-record-section">
                <button className={`pron-record-btn${isRecording?' recording':''}${isEvaluating?' disabled':''}`} onClick={isRecording?stopRecording:startRecording} disabled={isEvaluating} id="record-btn">
                  {isRecording ? <><div className="pron-record-pulse"/><span className="pron-btn-time">{formatTime(recordingTime)}</span><small>Tap to stop</small></>
                    : <><span style={{fontSize:'2rem'}}>🎙️</span><small>Tap to record</small></>}
                </button>
              </div>

              {result && !result.error && (
                <div className="pron-result-card">
                  <div className="pron-score-ring-wrap">
                    <svg className="pron-score-ring" viewBox="0 0 120 120">
                      <circle cx="60" cy="60" r="50" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="10"/>
                      <circle cx="60" cy="60" r="50" fill="none" stroke={getScoreColor(result.score)} strokeWidth="10"
                        strokeDasharray={`${(result.score/100)*314} 314`} strokeLinecap="round" transform="rotate(-90 60 60)"
                        style={{transition:'stroke-dasharray 1.2s ease'}}/>
                    </svg>
                    <div className="pron-score-center">
                      <div className="pron-score-number" style={{color:getScoreColor(result.score)}}>{result.score}</div>
                      <div className="pron-score-sub">/ 100</div>
                    </div>
                  </div>
                  <div className="pron-result-info">
                    <div className="pron-accuracy-badge">{getAccuracyLabel(result.accuracy)}</div>
                    <p className="pron-feedback">{result.feedback}</p>
                    <div className="pron-tip-box">💡 {result.tip}</div>
                    {result.what_they_said && <div className="pron-heard">Heard: <em>"{result.what_they_said}"</em></div>}
                    {result.xp_earned > 0 && <div className="pron-xp-badge">+{result.xp_earned} XP earned! 🎉</div>}
                  </div>
                </div>
              )}
              {result?.error && <div className="pron-error">{result.error}</div>}
              <button className="pron-refresh-btn" onClick={loadWords}>🔄 Get New Words</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
