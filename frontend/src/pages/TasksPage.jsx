/**
 * Tasks Page — Daily speaking missions
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import '../styles/dashboard.css';

export default function TasksPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    try {
      const data = await api.getTodayTasks();
      setTasks(data);
    } catch (err) {
      console.error('Failed to load tasks:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async (taskId) => {
    try {
      await api.completeTask(taskId);
      setTasks((prev) =>
        prev.map((t) =>
          t.id === taskId
            ? { ...t, completed: true, completed_at: new Date().toISOString() }
            : t
        )
      );
    } catch (err) {
      console.error('Failed to complete task:', err);
    }
  };

  const completed = tasks.filter((t) => t.completed).length;
  const total = tasks.length;
  const progressPct = total > 0 ? (completed / total) * 100 : 0;

  if (loading) {
    return (
      <div className="tasks-page">
        <div className="tasks-container" style={{ textAlign: 'center', paddingTop: '100px' }}>
          <div className="animate-float" style={{ fontSize: '3rem' }}>🎯</div>
          <p style={{ color: 'var(--text-secondary)', marginTop: '16px' }}>Loading your missions...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="tasks-page">
      <div className="tasks-container">
        {/* Header */}
        <div className="tasks-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h1>
              <span className="text-gradient">Today's Missions</span> 🎯
            </h1>
            <p>Complete these to level up your English!</p>
          </div>
          <div className="dashboard-nav">
            <button className="btn btn-primary" onClick={() => navigate('/chat')}>
              💬 Chat with Mira
            </button>
            <button className="btn btn-secondary" onClick={() => navigate('/dashboard')}>
              📊 Dashboard
            </button>
            <button className="btn btn-secondary" onClick={() => navigate('/activities')}>
              🎮 Activities
            </button>
          </div>
        </div>

        {/* Progress */}
        <div className="tasks-progress">
          <div className="tasks-progress-bar">
            <div
              className="tasks-progress-fill"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <div className="tasks-progress-text">
            {completed} of {total} missions completed
            {completed === total && total > 0 && ' 🎉 All done!'}
          </div>
        </div>

        {/* Task List */}
        <div className="task-list">
          {tasks.map((task) => (
            <div
              key={task.id}
              className={`glass-card task-card ${task.completed ? 'completed' : ''}`}
            >
              <button
                className={`task-check ${task.completed ? 'checked' : ''}`}
                onClick={() => !task.completed && handleComplete(task.id)}
                disabled={task.completed}
              >
                {task.completed ? '✓' : ''}
              </button>
              <div className="task-info">
                <div className="task-title">
                  {task.title}
                  <span className={`badge badge-${task.difficulty}`}>
                    {task.difficulty}
                  </span>
                </div>
                <div className="task-description">{task.description}</div>
                {task.completed && (
                  <div style={{ marginTop: '8px', fontSize: '0.8rem', color: 'var(--accent-success)' }}>
                    ✅ Completed!
                  </div>
                )}
              </div>
            </div>
          ))}

          {tasks.length === 0 && (
            <div className="glass-card" style={{ padding: '48px', textAlign: 'center' }}>
              <div style={{ fontSize: '3rem', marginBottom: '16px' }}>🌟</div>
              <h3 style={{ marginBottom: '8px' }}>No missions today</h3>
              <p style={{ color: 'var(--text-secondary)' }}>
                Start a conversation with Mira and new missions will appear!
              </p>
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div style={{ display: 'flex', gap: '12px', marginTop: '24px', justifyContent: 'center' }}>
          <button className="btn btn-primary" onClick={() => navigate('/chat')}>
            💬 Chat with Mira
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/dashboard')}>
            📊 Dashboard
          </button>
        </div>
      </div>

      {/* Bottom Nav */}
      <nav className="nav-bar">
        <button className="nav-item" onClick={() => navigate('/chat')}>
          <span className="nav-icon">💬</span>
          Chat
        </button>
        <button className="nav-item active" onClick={() => navigate('/tasks')}>
          <span className="nav-icon">🎯</span>
          Tasks
        </button>
        <button className="nav-item" onClick={() => navigate('/dashboard')}>
          <span className="nav-icon">📊</span>
          Progress
        </button>
      </nav>
    </div>
  );
}
