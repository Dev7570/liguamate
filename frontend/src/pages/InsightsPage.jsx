/**
 * Insights Page — Conversation Intelligence Dashboard
 * Premium animated analytics with live session stats + historical journey
 * Pure CSS rings + HTML5 Canvas charts — zero external chart libraries
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import '../styles/insights.css';

// ── Mood emoji map ─────────────────────────────────────────────────────────
const MOOD_EMOJI = {
  confident: '💪',
  hesitant: '🤔',
  excited: '🎉',
  frustrated: '😤',
  neutral: '😐',
  happy: '😊',
  curious: '🧐',
};

// ── Canvas: Draw a sparkline/line chart ────────────────────────────────────
function drawLineChart(canvas, dataPoints, {
  lineColor = '#7c3aed',
  fillColor = 'rgba(124, 58, 237, 0.15)',
  lineWidth = 2.5,
  dotRadius = 3,
  labelKey = 'score',
  labelXKey = 'date',
  showDots = true,
  showLabels = true,
  yMin = 0,
  yMax = 100,
} = {}) {
  if (!canvas || !dataPoints || dataPoints.length === 0) return;

  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();

  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;
  const padTop = 20;
  const padBottom = showLabels ? 30 : 10;
  const padLeft = 10;
  const padRight = 10;
  const chartW = w - padLeft - padRight;
  const chartH = h - padTop - padBottom;

  ctx.clearRect(0, 0, w, h);

  // Map data to coordinates
  const points = dataPoints.map((d, i) => {
    const x = padLeft + (i / Math.max(dataPoints.length - 1, 1)) * chartW;
    const val = typeof d === 'number' ? d : d[labelKey];
    const y = padTop + chartH - ((val - yMin) / (yMax - yMin)) * chartH;
    return { x, y, val, label: typeof d === 'object' ? d[labelXKey] : '' };
  });

  // Draw gradient fill
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  points.forEach(p => ctx.lineTo(p.x, p.y));
  ctx.lineTo(points[points.length - 1].x, padTop + chartH);
  ctx.lineTo(points[0].x, padTop + chartH);
  ctx.closePath();

  const gradient = ctx.createLinearGradient(0, padTop, 0, padTop + chartH);
  gradient.addColorStop(0, fillColor);
  gradient.addColorStop(1, 'transparent');
  ctx.fillStyle = gradient;
  ctx.fill();

  // Draw line
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);

  // Smooth curve via quadratic bezier
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const cpx = (prev.x + curr.x) / 2;
    ctx.quadraticCurveTo(prev.x, prev.y, cpx, (prev.y + curr.y) / 2);
  }
  ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);

  ctx.strokeStyle = lineColor;
  ctx.lineWidth = lineWidth;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  ctx.stroke();

  // Draw dots
  if (showDots) {
    points.forEach((p, i) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, dotRadius, 0, Math.PI * 2);
      ctx.fillStyle = lineColor;
      ctx.fill();
      ctx.strokeStyle = '#0a0a0f';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Value label on last point
      if (i === points.length - 1) {
        ctx.fillStyle = '#f1f5f9';
        ctx.font = 'bold 12px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(Math.round(p.val), p.x, p.y - 10);
      }
    });
  }

  // X-axis labels
  if (showLabels && points.length > 1) {
    ctx.fillStyle = '#64748b';
    ctx.font = '10px Inter, sans-serif';
    ctx.textAlign = 'center';
    const step = Math.max(1, Math.floor(points.length / 6));
    points.forEach((p, i) => {
      if (i % step === 0 || i === points.length - 1) {
        const label = p.label ? p.label.slice(5) : `${i + 1}`;
        ctx.fillText(label, p.x, h - 6);
      }
    });
  }
}

// ── Canvas: Draw vocab growth chart ────────────────────────────────────────
function drawVocabChart(canvas, dataPoints) {
  if (!dataPoints || dataPoints.length === 0) return;
  const maxVal = Math.max(...dataPoints.map(d => d.total_words), 10);
  drawLineChart(canvas, dataPoints, {
    lineColor: '#06b6d4',
    fillColor: 'rgba(6, 182, 212, 0.12)',
    labelKey: 'total_words',
    labelXKey: 'date',
    yMax: Math.ceil(maxVal * 1.15),
  });
}

// ── Live Session Tab ──────────────────────────────────────────────────────
function LiveSessionTab({ conversationId }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const sparklineCanvasRef = useRef(null);

  const fetchStats = useCallback(async () => {
    if (!conversationId) {
      setLoading(false);
      return;
    }
    try {
      const data = await api.getLiveInsights(conversationId);
      setStats(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [conversationId]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  // Draw sparkline for message lengths
  useEffect(() => {
    if (stats?.message_lengths?.length > 1 && sparklineCanvasRef.current) {
      const maxWords = Math.max(...stats.message_lengths.map(m => m.words), 5);
      drawLineChart(sparklineCanvasRef.current, stats.message_lengths, {
        lineColor: '#f59e0b',
        fillColor: 'rgba(245, 158, 11, 0.1)',
        labelKey: 'words',
        labelXKey: 'index',
        yMax: Math.ceil(maxWords * 1.2),
        showLabels: false,
      });
    }
  }, [stats]);

  if (!conversationId) {
    return (
      <div className="no-conv-banner">
        <p>Start a conversation with Mira to see live analytics here!</p>
        <button className="btn btn-primary" onClick={() => window.location.href = '/chat'}>
          💬 Start Chatting
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="insights-loading">
        <div className="insights-loading-icon">📊</div>
        <p>Analyzing your conversation...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="no-conv-banner">
        <p>Could not load live stats. The conversation may have no messages yet.</p>
        <button className="btn btn-secondary" onClick={fetchStats}>🔄 Retry</button>
      </div>
    );
  }

  if (!stats || stats.user_messages === 0) {
    return (
      <div className="no-conv-banner">
        <p>Send some messages in your conversation to see live analytics!</p>
      </div>
    );
  }

  const fluencyDeg = (stats.fluency_score / 100) * 360;
  const gaugeColor = stats.grammar_accuracy >= 80
    ? '#10b981'
    : stats.grammar_accuracy >= 50
      ? '#f59e0b'
      : '#ef4444';

  return (
    <div className="insights-grid">
      {/* Fluency Score Ring */}
      <div className="insight-card">
        <div className="insight-card-title">
          <span className="insight-card-title-icon">🎯</span> Fluency Score
        </div>
        <div className="fluency-ring-container">
          <div className="fluency-ring">
            <div className="fluency-ring-bg" />
            <div
              className="fluency-ring-progress"
              style={{
                background: `conic-gradient(
                  #7c3aed 0deg,
                  #06b6d4 ${fluencyDeg}deg,
                  transparent ${fluencyDeg}deg
                )`,
                mask: 'radial-gradient(farthest-side, transparent calc(100% - 14px), #fff calc(100% - 13px))',
                WebkitMask: 'radial-gradient(farthest-side, transparent calc(100% - 14px), #fff calc(100% - 13px))',
              }}
            />
            <div className="fluency-ring-inner">
              <span className="fluency-score-value">{stats.fluency_score}</span>
              <span className="fluency-score-label">out of 100</span>
            </div>
          </div>
          <div className="fluency-breakdown">
            <div className="fluency-factor">
              <span className="fluency-factor-value">{stats.avg_words_per_message}</span>
              <span className="fluency-factor-label">Avg Words</span>
            </div>
            <div className="fluency-factor">
              <span className="fluency-factor-value">{stats.vocab_diversity}</span>
              <span className="fluency-factor-label">Unique Words</span>
            </div>
            <div className="fluency-factor">
              <span className="fluency-factor-value">{stats.user_messages}</span>
              <span className="fluency-factor-label">Messages</span>
            </div>
          </div>
        </div>
      </div>

      {/* Grammar Accuracy */}
      <div className="insight-card">
        <div className="insight-card-title">
          <span className="insight-card-title-icon">✅</span> Grammar Accuracy
        </div>
        <div className="stat-big">
          <span className="stat-big-value" style={{ WebkitTextFillColor: gaugeColor, color: gaugeColor, background: 'none' }}>
            {stats.grammar_accuracy}%
          </span>
          <span className="stat-big-label">
            {stats.corrections_count} correction{stats.corrections_count !== 1 ? 's' : ''} detected
          </span>
        </div>
        <div style={{ marginTop: 'var(--space-lg)' }}>
          <div className="metric-bar-track">
            <div
              className={`metric-bar-fill ${stats.grammar_accuracy >= 80 ? 'success' : stats.grammar_accuracy >= 50 ? 'warm' : ''}`}
              style={{ width: `${stats.grammar_accuracy}%` }}
            />
          </div>
        </div>
      </div>

      {/* Vocabulary Complexity */}
      <div className="insight-card">
        <div className="insight-card-title">
          <span className="insight-card-title-icon">📚</span> Vocabulary Complexity
        </div>
        <div className="metric-bar-container">
          <div className="metric-bar-header">
            <span className="metric-bar-label">Diversity Ratio</span>
            <span className="metric-bar-value">{stats.vocab_complexity}%</span>
          </div>
          <div className="metric-bar-track">
            <div className="metric-bar-fill" style={{ width: `${stats.vocab_complexity}%` }} />
          </div>
        </div>
        <div style={{ marginTop: 'var(--space-lg)' }}>
          <div className="metric-bar-container">
            <div className="metric-bar-header">
              <span className="metric-bar-label">Filler Ratio</span>
              <span className="metric-bar-value">{stats.filler_ratio}%</span>
            </div>
            <div className="metric-bar-track">
              <div className="metric-bar-fill warm" style={{ width: `${Math.min(stats.filler_ratio * 5, 100)}%` }} />
            </div>
          </div>
        </div>
      </div>

      {/* Filler Words */}
      <div className="insight-card">
        <div className="insight-card-title">
          <span className="insight-card-title-icon">🫧</span> Filler Words
        </div>
        <div className="filler-counter">
          <span className="filler-count-display">{stats.total_fillers}</span>
          <div className="filler-info">
            <span className="filler-label">filler words detected</span>
            <span className="filler-ratio">
              {stats.filler_ratio}% of your words • {stats.total_fillers === 0 ? 'Perfect! 🎉' : stats.filler_ratio < 5 ? 'Great control! 👏' : 'Try reducing fillers'}
            </span>
          </div>
        </div>
      </div>

      {/* Mood Timeline */}
      <div className="insight-card insight-card-full">
        <div className="insight-card-title">
          <span className="insight-card-title-icon">🎭</span> Mood Timeline
        </div>
        {stats.mood_timeline && stats.mood_timeline.length > 0 ? (
          <div className="mood-timeline">
            {stats.mood_timeline.map((m, i) => (
              <div key={i} style={{ display: 'contents' }}>
                <div className="mood-bubble">
                  <div className="mood-emoji">{MOOD_EMOJI[m.mood] || '😐'}</div>
                  <span className="mood-label">{m.mood}</span>
                </div>
                {i < stats.mood_timeline.length - 1 && <div className="mood-connector" />}
              </div>
            ))}
          </div>
        ) : (
          <div className="mood-empty">No mood signals detected yet.</div>
        )}
      </div>

      {/* Message Length Trend */}
      <div className="insight-card">
        <div className="insight-card-title">
          <span className="insight-card-title-icon">📏</span> Message Length Trend
        </div>
        {stats.message_lengths && stats.message_lengths.length > 1 ? (
          <div className="chart-container">
            <canvas ref={sparklineCanvasRef} />
          </div>
        ) : (
          <div className="sparkline-row">
            {stats.message_lengths?.map((m, i) => (
              <div
                key={i}
                className="sparkline-bar"
                style={{ height: `${Math.max((m.words / Math.max(...stats.message_lengths.map(x => x.words), 1)) * 100, 8)}%` }}
                title={`${m.words} words`}
              />
            ))}
          </div>
        )}
      </div>

      {/* Top Words */}
      <div className="insight-card">
        <div className="insight-card-title">
          <span className="insight-card-title-icon">🔤</span> Top Words Used
        </div>
        <div className="words-cloud">
          {stats.top_words?.map((w, i) => (
            <span
              key={i}
              className={`word-tag ${i < 3 ? 'word-tag-lg' : i > 6 ? 'word-tag-sm' : ''}`}
              style={{ animationDelay: `${i * 0.05}s` }}
            >
              {w.word}
              <span className="word-count">×{w.count}</span>
            </span>
          ))}
          {(!stats.top_words || stats.top_words.length === 0) && (
            <span style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>
              Keep chatting to build your word cloud!
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── My Journey Tab (Historical) ───────────────────────────────────────────
function JourneyTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const fluencyChartRef = useRef(null);
  const vocabChartRef = useRef(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await api.getHistoricalInsights();
        setData(result);
      } catch (err) {
        console.error('Failed to load historical insights:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Draw fluency trend chart
  useEffect(() => {
    if (data?.fluency_trend?.length > 1 && fluencyChartRef.current) {
      drawLineChart(fluencyChartRef.current, data.fluency_trend, {
        lineColor: '#7c3aed',
        fillColor: 'rgba(124, 58, 237, 0.12)',
        labelKey: 'score',
        labelXKey: 'date',
      });
    }
  }, [data]);

  // Draw vocab growth chart
  useEffect(() => {
    if (data?.vocab_growth?.length > 1 && vocabChartRef.current) {
      drawVocabChart(vocabChartRef.current, data.vocab_growth);
    }
  }, [data]);

  if (loading) {
    return (
      <div className="insights-loading">
        <div className="insights-loading-icon">📈</div>
        <p>Loading your learning journey...</p>
      </div>
    );
  }

  if (!data || data.total_conversations === 0) {
    return (
      <div className="insights-empty">
        <div className="insights-empty-icon">🚀</div>
        <h2>Your Journey Starts Here</h2>
        <p>Complete a few conversations with Mira to unlock your personalized analytics dashboard.</p>
        <button className="btn btn-primary btn-lg" onClick={() => window.location.href = '/chat'}>
          💬 Start Your First Conversation
        </button>
      </div>
    );
  }

  // Compute heatmap max for level scaling
  const heatmapMax = Math.max(...(data.activity_heatmap?.map(h => h.count) || [1]), 1);
  const getHeatLevel = (count) => {
    if (count === 0) return 0;
    const ratio = count / heatmapMax;
    if (ratio <= 0.25) return 1;
    if (ratio <= 0.5) return 2;
    if (ratio <= 0.75) return 3;
    return 4;
  };

  // Group heatmap by day
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const hours = [0, 3, 6, 9, 12, 15, 18, 21];
  const hourLabels = ['12a', '3a', '6a', '9a', '12p', '3p', '6p', '9p'];

  const correctionMax = Math.max(...(data.correction_categories?.map(c => c.count) || [1]), 1);
  const catColorMap = {
    'Tense': 'cat-tense',
    'Articles': 'cat-articles',
    'Prepositions': 'cat-prepositions',
    'Plurals': 'cat-plurals',
    'Spelling': 'cat-spelling',
  };

  return (
    <div className="insights-grid">
      {/* Summary Stats Row */}
      <div className="insight-card">
        <div className="insight-card-title">
          <span className="insight-card-title-icon">📊</span> Overview
        </div>
        <div className="weekly-stats">
          <div className="weekly-stat">
            <div className="weekly-stat-value">{data.total_conversations}</div>
            <div className="weekly-stat-label">Total Conversations</div>
          </div>
          <div className="weekly-stat">
            <div className="weekly-stat-value">{data.total_practice_days}</div>
            <div className="weekly-stat-label">Practice Days</div>
          </div>
          <div className="weekly-stat">
            <div className="weekly-stat-value">{data.total_unique_words}</div>
            <div className="weekly-stat-label">Unique Words</div>
          </div>
        </div>
      </div>

      {/* Weekly Summary */}
      <div className="insight-card">
        <div className="insight-card-title">
          <span className="insight-card-title-icon">📅</span> This Week
        </div>
        <div className="weekly-stats">
          <div className="weekly-stat">
            <div className="weekly-stat-value">{data.weekly_summary?.conversations_this_week || 0}</div>
            <div className="weekly-stat-label">Conversations</div>
          </div>
          <div className="weekly-stat">
            <div className="weekly-stat-value">{data.weekly_summary?.messages_this_week || 0}</div>
            <div className="weekly-stat-label">Messages</div>
          </div>
          <div className="weekly-stat">
            <div className="weekly-stat-value">{data.weekly_summary?.practice_days_this_week || 0}</div>
            <div className="weekly-stat-label">Active Days</div>
          </div>
        </div>
      </div>

      {/* Fluency Trend Chart */}
      <div className="insight-card insight-card-full">
        <div className="insight-card-title">
          <span className="insight-card-title-icon">📈</span> Fluency Score Trend
        </div>
        {data.fluency_trend?.length > 1 ? (
          <div className="chart-container">
            <canvas ref={fluencyChartRef} />
          </div>
        ) : (
          <div className="mood-empty">Need at least 2 conversations to show trends.</div>
        )}
      </div>

      {/* Vocabulary Growth */}
      <div className="insight-card">
        <div className="insight-card-title">
          <span className="insight-card-title-icon">📚</span> Vocabulary Growth
        </div>
        {data.vocab_growth?.length > 1 ? (
          <div className="chart-container">
            <canvas ref={vocabChartRef} />
          </div>
        ) : (
          <div className="mood-empty">Keep chatting to track your vocabulary growth!</div>
        )}
      </div>

      {/* Correction Categories */}
      <div className="insight-card">
        <div className="insight-card-title">
          <span className="insight-card-title-icon">✏️</span> Grammar Weak Spots
        </div>
        {data.correction_categories?.length > 0 ? (
          <div className="correction-categories">
            {data.correction_categories.map((cat, i) => (
              <div key={i} className="correction-cat-row">
                <span className="correction-cat-label">{cat.category}</span>
                <div className="correction-cat-bar">
                  <div
                    className={`correction-cat-fill ${catColorMap[cat.category] || 'cat-default'}`}
                    style={{ width: `${(cat.count / correctionMax) * 100}%` }}
                  />
                </div>
                <span className="correction-cat-count">{cat.count}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="mood-empty">No corrections recorded yet — great grammar! 🎉</div>
        )}
      </div>

      {/* Activity Heatmap */}
      <div className="insight-card insight-card-full">
        <div className="insight-card-title">
          <span className="insight-card-title-icon">🗓️</span> Practice Activity
        </div>
        <div className="heatmap-grid">
          {days.map(day => (
            <div key={day} style={{ display: 'contents' }}>
              <div className="heatmap-day-label">{day}</div>
              {hours.map(hour => {
                const cell = data.activity_heatmap?.find(h => h.day === day && h.hour === hour);
                const count = cell?.count || 0;
                return (
                  <div
                    key={`${day}-${hour}`}
                    className={`heatmap-cell level-${getHeatLevel(count)}`}
                    title={`${day} ${hour}:00 — ${count} session${count !== 1 ? 's' : ''}`}
                  />
                );
              })}
            </div>
          ))}
        </div>
        <div className="heatmap-hour-labels">
          <div />
          {hourLabels.map(label => (
            <div key={label} className="heatmap-hour-label">{label}</div>
          ))}
        </div>
        <div className="heatmap-legend">
          <span>Less</span>
          <div className="heatmap-legend-cell level-0" style={{ background: 'var(--bg-tertiary)' }} />
          <div className="heatmap-legend-cell level-1" style={{ background: 'rgba(124, 58, 237, 0.2)' }} />
          <div className="heatmap-legend-cell level-2" style={{ background: 'rgba(124, 58, 237, 0.4)' }} />
          <div className="heatmap-legend-cell level-3" style={{ background: 'rgba(124, 58, 237, 0.6)' }} />
          <div className="heatmap-legend-cell level-4" style={{ background: 'rgba(124, 58, 237, 0.85)' }} />
          <span>More</span>
        </div>
      </div>

      {/* Top Words Cloud */}
      <div className="insight-card">
        <div className="insight-card-title">
          <span className="insight-card-title-icon">🔤</span> Most Used Words
        </div>
        <div className="words-cloud">
          {data.top_words?.map((w, i) => (
            <span
              key={i}
              className={`word-tag ${i < 3 ? 'word-tag-lg' : i > 9 ? 'word-tag-sm' : ''}`}
              style={{ animationDelay: `${i * 0.04}s` }}
            >
              {w.word}
              <span className="word-count">×{w.count}</span>
            </span>
          ))}
          {(!data.top_words || data.top_words.length === 0) && (
            <span style={{ color: 'var(--text-muted)' }}>No word data yet.</span>
          )}
        </div>
      </div>

      {/* Milestones */}
      <div className="insight-card">
        <div className="insight-card-title">
          <span className="insight-card-title-icon">🏅</span> Milestones
        </div>
        <div className="milestones-grid">
          {data.milestones?.map((m, i) => (
            <div key={i} className={`milestone-badge ${m.achieved ? 'achieved' : 'upcoming'}`}>
              <span className="milestone-icon">{m.icon}</span>
              <span className="milestone-label">{m.label}</span>
            </div>
          ))}
          {(!data.milestones || data.milestones.length === 0) && (
            <span style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>
              Start chatting to earn milestones!
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Insights Page ─────────────────────────────────────────────────────
export default function InsightsPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('journey');
  const [conversations, setConversations] = useState([]);
  const [selectedConvId, setSelectedConvId] = useState(null);

  // Load recent conversations for Live tab
  useEffect(() => {
    const loadConvs = async () => {
      try {
        const convs = await api.getConversations();
        setConversations(convs);
        if (convs.length > 0) {
          setSelectedConvId(convs[0].id);
        }
      } catch (err) {
        console.error('Failed to load conversations:', err);
      }
    };
    loadConvs();
  }, []);

  return (
    <div className="insights-page">
      <div className="insights-container">
        {/* Header */}
        <div className="insights-header">
          <div className="insights-header-left">
            <h1>
              <span className="text-gradient">Insights</span> 📈
            </h1>
            <p>Deep analytics of your language learning journey</p>
          </div>
          <div className="insights-nav">
            <button className="btn btn-primary" onClick={() => navigate('/chat')}>
              💬 Chat
            </button>
            <button className="btn btn-secondary" onClick={() => navigate('/dashboard')}>
              📊 Dashboard
            </button>
            <button
              className="btn"
              style={{ background: 'transparent', border: '1px solid var(--color-border, var(--border-subtle))', color: 'var(--text-muted)' }}
              onClick={() => { logout(); navigate('/'); }}
            >
              🚪 Logout
            </button>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="insights-tabs">
          <button
            className={`insights-tab ${activeTab === 'live' ? 'active' : ''}`}
            onClick={() => setActiveTab('live')}
          >
            <span className="pulse-dot" style={{ display: activeTab === 'live' ? 'inline-block' : 'none' }} />
            ⚡ Live Session
          </button>
          <button
            className={`insights-tab ${activeTab === 'journey' ? 'active' : ''}`}
            onClick={() => setActiveTab('journey')}
          >
            🗺️ My Journey
          </button>
        </div>

        {/* Live Tab — Conversation Selector */}
        {activeTab === 'live' && conversations.length > 0 && (
          <div style={{ marginBottom: 'var(--space-lg)', animation: 'fadeIn 0.3s ease-out' }}>
            <label style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: '8px', display: 'block' }}>
              Select conversation to analyze:
            </label>
            <select
              className="input"
              value={selectedConvId || ''}
              onChange={(e) => setSelectedConvId(e.target.value)}
              style={{ maxWidth: '500px' }}
            >
              {conversations.map((conv) => (
                <option key={conv.id} value={conv.id}>
                  {conv.summary || `Chat · ${conv.message_count} messages`} — {new Date(conv.started_at).toLocaleDateString()}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Tab Content */}
        {activeTab === 'live' ? (
          <LiveSessionTab conversationId={selectedConvId} />
        ) : (
          <JourneyTab />
        )}
      </div>

      {/* Bottom Nav */}
      <nav className="nav-bar">
        <button className="nav-item" onClick={() => navigate('/chat')}>
          <span className="nav-icon">💬</span>
          Chat
        </button>
        <button className="nav-item" onClick={() => navigate('/dashboard')}>
          <span className="nav-icon">📊</span>
          Progress
        </button>
        <button className="nav-item active" onClick={() => navigate('/insights')}>
          <span className="nav-icon">📈</span>
          Insights
        </button>
      </nav>
    </div>
  );
}
