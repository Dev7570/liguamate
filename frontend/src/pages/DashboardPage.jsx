/**
 * Dashboard Page — Progress stats, streaks, vocabulary, and encouragement
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import '../styles/dashboard.css';

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState(null);
  const [vocabulary, setVocabulary] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const [dashData, vocabData, leadData] = await Promise.all([
        api.getDashboard(),
        api.getVocabulary(),
        api.getLeaderboard(),
      ]);
      setDashboard(dashData);
      setVocabulary(vocabData);
      setLeaderboard(leadData.leaderboard || []);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="dashboard-page">
        <div className="dashboard-container" style={{ textAlign: 'center', paddingTop: '100px' }}>
          <div className="animate-float" style={{ fontSize: '3rem' }}>🌟</div>
          <p style={{ color: 'var(--text-secondary)', marginTop: '16px' }}>Loading your progress...</p>
        </div>
      </div>
    );
  }

  const d = dashboard || {};

  return (
    <div className="dashboard-page">
      <div className="dashboard-container">
        {/* Header */}
        <div className="dashboard-header">
          <div className="dashboard-greeting">
            <h1>
              <span className="text-gradient">Your Progress</span> 📊
            </h1>
            <p>Hey {user?.name || 'there'}! Here's how you're doing.</p>
          </div>
          <div className="dashboard-nav">
            <button className="btn btn-primary" onClick={() => navigate('/chat')}>
              💬 Chat with Mira
            </button>
            <button className="btn btn-secondary" onClick={() => navigate('/tasks')}>
              🎯 Tasks
            </button>
            <button className="btn btn-secondary" onClick={() => navigate('/activities')}>
              🎮 Activities
            </button>
            <button className="btn" style={{ background: 'transparent', border: '1px solid var(--color-border)', color: 'var(--color-text-muted)' }} onClick={() => { logout(); navigate('/'); }}>
              🚪 Logout
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="stats-grid">
          <div className="glass-card stat-card">
            <div className="stat-icon stat-icon-purple">🔥</div>
            <div className="stat-value text-gradient">{d.current_streak || 0}</div>
            <div className="stat-label">Day Streak</div>
          </div>
          <div className="glass-card stat-card">
            <div className="stat-icon stat-icon-cyan">💬</div>
            <div className="stat-value">{d.total_conversations || 0}</div>
            <div className="stat-label">Conversations</div>
          </div>
          <div className="glass-card stat-card">
            <div className="stat-icon stat-icon-green">📚</div>
            <div className="stat-value">{d.total_words_learned || 0}</div>
            <div className="stat-label">Words Learned</div>
          </div>
          <div className="glass-card stat-card">
            <div className="stat-icon stat-icon-orange">🏆</div>
            <div className="stat-value">{d.words_mastered || 0}</div>
            <div className="stat-label">Words Mastered</div>
          </div>
        </div>

        {/* Encouragement Card */}
        <div className="encouragement-card">
          <div className="encouragement-avatar">🤗</div>
          <div className="encouragement-content">
            <h3>Mira says...</h3>
            <p>{d.encouragement || "You're doing amazing! Keep going! 💜"}</p>
          </div>
        </div>

        {/* Tasks + Corrections + Vocabulary */}
        <div className="dashboard-grid">
          {/* Today's Tasks */}
          <div className="glass-card-static dashboard-section">
            <h2>🎯 Today's Missions</h2>
            <div style={{ marginBottom: '12px' }}>
              <div className="tasks-progress-bar">
                <div
                  className="tasks-progress-fill"
                  style={{
                    width: d.tasks_total_today
                      ? `${(d.tasks_completed_today / d.tasks_total_today) * 100}%`
                      : '0%',
                  }}
                />
              </div>
              <div className="tasks-progress-text">
                {d.tasks_completed_today || 0} / {d.tasks_total_today || 0} completed
              </div>
            </div>
            <button
              className="btn btn-secondary w-full"
              onClick={() => navigate('/tasks')}
            >
              View All Missions →
            </button>
          </div>

          {/* Recent Corrections */}
          <div className="glass-card-static dashboard-section">
            <h2>✏️ Recent Corrections</h2>
            {d.recent_corrections && d.recent_corrections.length > 0 ? (
              <div className="corrections-list">
                {d.recent_corrections.slice(0, 4).map((c, i) => (
                  <div key={i} className="correction-card">
                    <div>
                      <span className="correction-original">{c.original}</span>
                      <span className="correction-arrow" style={{ margin: '0 6px', color: 'var(--accent-primary-light)' }}>→</span>
                      <span className="correction-fixed">{c.corrected}</span>
                    </div>
                    {c.explanation && (
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                        {c.explanation}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                No corrections yet. Start chatting to see them here!
              </p>
            )}
          </div>

          {/* Vocabulary */}
          <div className="glass-card-static dashboard-section">
            <h2>📖 Vocabulary (SRS Due)</h2>
            {vocabulary.length > 0 ? (
              <div className="vocab-list">
                {vocabulary.slice(0, 5).map((v, i) => (
                  <div key={i} className="vocab-row">
                    <span className="vocab-word">{v.word}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className="vocab-uses">Used {v.times_used}x</span>
                      <span className={`badge badge-${v.mastery_level}`}>
                        {v.mastery_level}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                Words you use in conversations will appear here!
              </p>
            )}
          </div>

          {/* Leaderboard */}
          <div className="glass-card-static dashboard-section">
            <h2>🌍 Global Leaderboard</h2>
            {leaderboard.length > 0 ? (
              <div className="leaderboard-list">
                {leaderboard.map((lb, i) => (
                  <div key={i} className={`leaderboard-row ${lb.id === user?.id ? 'leaderboard-self' : ''}`}>
                    <span className="leaderboard-rank">#{lb.rank}</span>
                    <span className="leaderboard-avatar">{lb.avatar_emoji}</span>
                    <span className="leaderboard-name">{lb.name} {lb.id === user?.id && '(You)'}</span>
                    <span className="leaderboard-xp">{lb.xp} XP</span>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                No one is on the leaderboard yet!
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Nav */}
      <nav className="nav-bar">
        <button className="nav-item" onClick={() => navigate('/chat')}>
          <span className="nav-icon">💬</span>
          Chat
        </button>
        <button className="nav-item" onClick={() => navigate('/tasks')}>
          <span className="nav-icon">🎯</span>
          Tasks
        </button>
        <button className="nav-item active" onClick={() => navigate('/dashboard')}>
          <span className="nav-icon">📊</span>
          Progress
        </button>
      </nav>
    </div>
  );
}
