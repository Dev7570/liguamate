/**
 * Tests Page — Mock IELTS/TOEFL Speaking Tests with AI evaluation
 */
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import '../styles/tests.css';

const TEST_CONFIG = {
  ielts: {
    label: 'IELTS Speaking',
    color: '#3b82f6',
    icon: '📋',
    parts: [
      { id:'part1', label:'Part 1', sub:'Personal Introduction', desc:'Answer questions about yourself, your home, family, work, studies and interests.', prep:0, speak:90 },
      { id:'part2', label:'Part 2', sub:'Individual Long Turn', desc:'Speak for 1-2 minutes on a given topic after 1 minute of preparation.', prep:60, speak:120 },
      { id:'part3', label:'Part 3', sub:'Two-way Discussion', desc:'Discuss abstract ideas and issues related to the Part 2 topic.', prep:0, speak:90 },
    ],
    scale: { min:0, max:9, label:'Band Score' },
    criteria: ['Fluency & Coherence', 'Lexical Resource', 'Grammatical Range', 'Pronunciation'],
  },
  toefl: {
    label: 'TOEFL Speaking',
    color: '#10b981',
    icon: '📝',
    parts: [
      { id:'task1', label:'Task 1', sub:'Independent Task', desc:'Express and defend your opinion about a familiar topic.', prep:15, speak:45 },
      { id:'task2', label:'Task 2', sub:'Integrated Task', desc:'Discuss an academic concept after reading and listening to related content.', prep:15, speak:60 },
    ],
    scale: { min:0, max:30, label:'Score' },
    criteria: ['Delivery', 'Language Use', 'Topic Development', 'Pronunciation'],
  },
};

export default function TestsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [testType, setTestType] = useState('ielts');
  const [selectedPart, setSelectedPart] = useState(null);
  const [prompts, setPrompts] = useState([]);
  const [chosenPrompt, setChosenPrompt] = useState('');
  const [phase, setPhase] = useState('select'); // 'select'|'prep'|'recording'|'evaluating'|'result'
  const [prepTimeLeft, setPrepTimeLeft] = useState(0);
  const [speakTimeLeft, setSpeakTimeLeft] = useState(0);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('test'); // 'test'|'history'
  const [loadingPrompts, setLoadingPrompts] = useState(false);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const prepTimerRef = useRef(null);
  const speakTimerRef = useRef(null);

  useEffect(() => { loadHistory(); }, []);

  const loadHistory = async () => {
    try { const h = await api.getTestHistory(); setHistory(h); } catch {}
  };

  const selectPart = async (part) => {
    setSelectedPart(part);
    setResult(null);
    setChosenPrompt('');
    setLoadingPrompts(true);
    try {
      const data = await api.getTestPrompts(testType, part.id);
      setPrompts(data.prompts || []);
      if (data.prompts?.length) setChosenPrompt(data.prompts[0]);
    } catch (e) { console.error(e); }
    finally { setLoadingPrompts(false); }
    setPhase('select');
  };

  const startTest = () => {
    if (!chosenPrompt) return;
    if (selectedPart.prep > 0) {
      setPhase('prep');
      setPrepTimeLeft(selectedPart.prep);
      prepTimerRef.current = setInterval(() => {
        setPrepTimeLeft(t => {
          if (t <= 1) { clearInterval(prepTimerRef.current); startRecording(); return 0; }
          return t - 1;
        });
      }, 1000);
    } else { startRecording(); }
  };

  const startRecording = async () => {
    setPhase('recording');
    setSpeakTimeLeft(selectedPart.speak);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';
      const recorder = new MediaRecorder(stream, { mimeType });
      audioChunksRef.current = [];
      recorder.ondataavailable = e => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      recorder.onstop = () => { stream.getTracks().forEach(t => t.stop()); clearInterval(speakTimerRef.current); submitTest(new Blob(audioChunksRef.current, { type: mimeType })); };
      recorder.start(200);
      mediaRecorderRef.current = recorder;
      speakTimerRef.current = setInterval(() => {
        setSpeakTimeLeft(t => {
          if (t <= 1) { clearInterval(speakTimerRef.current); recorder.stop(); return 0; }
          return t - 1;
        });
      }, 1000);
    } catch { alert('Microphone access denied.'); setPhase('select'); }
  };

  const stopEarly = () => {
    if (mediaRecorderRef.current?.state !== 'inactive') { clearInterval(speakTimerRef.current); mediaRecorderRef.current.stop(); }
  };

  const submitTest = async (blob) => {
    setPhase('evaluating');
    try {
      const data = await api.evaluateTest(blob, testType, selectedPart.id, chosenPrompt);
      setResult(data);
      setPhase('result');
      loadHistory();
    } catch (e) { alert(e.message||'Evaluation failed'); setPhase('select'); }
  };

  const cfg = TEST_CONFIG[testType];
  const formatTime = s => `${Math.floor(s/60).toString().padStart(2,'0')}:${(s%60).toString().padStart(2,'0')}`;

  const getScoreColor = (score, max) => {
    const pct = score / max;
    return pct >= 0.78 ? '#10b981' : pct >= 0.55 ? '#3b82f6' : pct >= 0.33 ? '#f59e0b' : '#ef4444';
  };

  const getBandLabel = (score, max) => {
    const pct = score / max;
    return pct >= 0.78 ? 'Good 🌟' : pct >= 0.55 ? 'Fair 🙂' : pct >= 0.33 ? 'Developing 📈' : 'Needs Work 💪';
  };

  return (
    <div className="ts-layout">
      <header className="ts-header">
        <button className="ts-back-btn" onClick={() => navigate('/chat')}>← Back to Chat</button>
        <div className="ts-header-mid"><span>📝</span><h1>Speaking Tests</h1></div>
        <div className="ts-tab-pills">
          <button className={`ts-pill${activeTab==='test'?' active':''}`} onClick={() => setActiveTab('test')}>Take Test</button>
          <button className={`ts-pill${activeTab==='history'?' active':''}`} onClick={() => setActiveTab('history')}>History</button>
        </div>
      </header>

      <div className="ts-content">
        {activeTab === 'history' ? (
          <div className="ts-history">
            <h2>Your Test History</h2>
            {history.length === 0 && <div className="ts-empty">No tests taken yet. Complete your first test to see results here!</div>}
            <div className="ts-history-list">
              {history.map(t => (
                <div key={t.id} className="ts-history-card">
                  <div className="ts-history-type">{t.test_type.toUpperCase()} {t.part}</div>
                  <div className="ts-history-score" style={{color:getScoreColor(t.band_score,t.test_type==='ielts'?9:30)}}>{t.band_score}</div>
                  <div className="ts-history-date">{new Date(t.created_at).toLocaleDateString()}</div>
                  {t.prompt_used && <div className="ts-history-prompt">"{t.prompt_used.substring(0,80)}..."</div>}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <>
            {/* Test Type Switcher */}
            <div className="ts-type-selector">
              {Object.entries(TEST_CONFIG).map(([type, c]) => (
                <button key={type} className={`ts-type-btn${testType===type?' active':''}`} onClick={() => { setTestType(type); setSelectedPart(null); setResult(null); setPhase('select'); }} style={testType===type?{borderColor:c.color,background:`${c.color}18`}:{}}>
                  <span style={{fontSize:'1.5rem'}}>{c.icon}</span>
                  <div><div className="ts-type-name">{c.label}</div><div className="ts-type-scale">Score: {c.scale.min}–{c.scale.max}</div></div>
                </button>
              ))}
            </div>

            {/* Part Selector */}
            <div className="ts-parts">
              {cfg.parts.map(part => (
                <button key={part.id} className={`ts-part-btn${selectedPart?.id===part.id?' active':''}`} onClick={() => selectPart(part)}>
                  <div className="ts-part-label">{part.label}</div>
                  <div className="ts-part-sub">{part.sub}</div>
                  <div className="ts-part-timing">⏱️ {part.prep>0?`${part.prep}s prep + `:''}{part.speak}s speaking</div>
                </button>
              ))}
            </div>

            {/* Main Test Area */}
            {selectedPart && (
              <div className="ts-test-area">
                <div className="ts-question-panel">
                  <div className="ts-panel-label">{selectedPart.label}: {selectedPart.sub}</div>
                  <p className="ts-panel-desc">{selectedPart.desc}</p>
                  {loadingPrompts ? <div className="ts-loading-prompt">Loading questions...</div> : (
                    <>
                      <div className="ts-prompt-label">Your question:</div>
                      <div className="ts-prompt-text">{chosenPrompt}</div>
                      {prompts.length > 1 && phase === 'select' && (
                        <div className="ts-prompt-alts">
                          <div className="ts-alts-label">Or try:</div>
                          {prompts.filter(p=>p!==chosenPrompt).map((p,i) => (
                            <button key={i} className="ts-alt-prompt" onClick={() => setChosenPrompt(p)}>{p.substring(0,70)}...</button>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>

                {/* Prep Phase */}
                {phase === 'prep' && (
                  <div className="ts-phase-card ts-phase-prep">
                    <div className="ts-phase-title">📖 Preparation Time</div>
                    <div className="ts-big-timer" style={{color:'#f59e0b'}}>{formatTime(prepTimeLeft)}</div>
                    <p>Read the question and gather your thoughts. Recording starts automatically.</p>
                  </div>
                )}

                {/* Recording Phase */}
                {phase === 'recording' && (
                  <div className="ts-phase-card ts-phase-record">
                    <div className="ts-phase-title">🎙️ Recording...</div>
                    <div className="ts-big-timer" style={{color:'#ef4444'}}>{formatTime(speakTimeLeft)}</div>
                    <div className="ts-record-pulse-row">{[...Array(5)].map((_,i)=><div key={i} className="ts-bar-wave" style={{'--i':i}}/>)}</div>
                    <button className="ts-stop-btn" onClick={stopEarly}>⏹ Stop Early</button>
                  </div>
                )}

                {/* Evaluating Phase */}
                {phase === 'evaluating' && (
                  <div className="ts-phase-card">
                    <div className="ts-spinner"/>
                    <div className="ts-phase-title">Evaluating your response...</div>
                    <p style={{color:'var(--text-secondary)'}}>Our AI examiner is scoring your speaking. This takes 10-20 seconds.</p>
                  </div>
                )}

                {/* Start Button */}
                {phase === 'select' && (
                  <button className="ts-start-btn" onClick={startTest} disabled={!chosenPrompt} id="start-test-btn">
                    🎙️ Start {selectedPart.prep>0?`Prep (${selectedPart.prep}s) `:''}Test
                  </button>
                )}

                {/* Result */}
                {phase === 'result' && result && (
                  <div className="ts-result">
                    <div className="ts-result-header">
                      <h3>Your {testType.toUpperCase()} {selectedPart.label} Result</h3>
                      <div className="ts-overall-score" style={{color:getScoreColor(result.band_score,cfg.scale.max)}}>
                        <div className="ts-score-big">{result.band_score}</div>
                        <div className="ts-score-max">/ {cfg.scale.max}</div>
                        <div className="ts-band-label">{getBandLabel(result.band_score,cfg.scale.max)}</div>
                      </div>
                    </div>

                    <div className="ts-criteria-grid">
                      {[['fluency',cfg.criteria[0]],['lexical',cfg.criteria[1]],['grammar',cfg.criteria[2]],['pronunciation',cfg.criteria[3]]].map(([key,label])=>(
                        <div key={key} className="ts-criterion">
                          <div className="ts-crit-label">{label}</div>
                          <div className="ts-crit-score" style={{color:getScoreColor(result[key],cfg.scale.max)}}>{result[key]}</div>
                          <div className="ts-crit-bar"><div className="ts-crit-fill" style={{width:`${(result[key]/cfg.scale.max)*100}%`,background:getScoreColor(result[key],cfg.scale.max)}}/></div>
                        </div>
                      ))}
                    </div>

                    {result.strengths && <div className="ts-feedback-section ts-strengths"><div className="ts-fb-label">✅ Strengths</div><p>{result.strengths}</p></div>}
                    {result.improvements && <div className="ts-feedback-section ts-improvements"><div className="ts-fb-label">📈 Areas to Improve</div><p>{result.improvements}</p></div>}
                    {result.overall_feedback && <div className="ts-feedback-section ts-overall"><div className="ts-fb-label">💬 Examiner Feedback</div><p>{result.overall_feedback}</p></div>}
                    {result.transcript && <div className="ts-transcript"><div className="ts-fb-label">📄 Your Response (transcribed)</div><p>{result.transcript}</p></div>}
                    {result.xp_earned > 0 && <div className="ts-xp-earned">+{result.xp_earned} XP earned! 🎉</div>}

                    <button className="ts-retry-btn" onClick={() => { setPhase('select'); setResult(null); setChosenPrompt(prompts[0]||''); }}>Try Another Question</button>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
