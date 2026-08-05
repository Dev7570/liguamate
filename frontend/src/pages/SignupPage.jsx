/**
 * Signup Page — Onboarding with level selection and goal input
 */

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import '../styles/auth.css';

const LEVELS = ['beginner', 'intermediate', 'advanced'];

const GOALS = [
  { value: 'casual_fluency', label: '🗣️ Daily conversation' },
  { value: 'interview_prep', label: '💼 Interview preparation' },
  { value: 'exam_prep', label: '📝 Exam preparation' },
  { value: 'business', label: '🏢 Business English' },
  { value: 'academic', label: '🎓 Academic English' },
];

export default function SignupPage() {
  const [step, setStep] = useState(1);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [level, setLevel] = useState('beginner');
  const [goal, setGoal] = useState('casual_fluency');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { signup } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (step === 1) {
      setStep(2);
      return;
    }

    setError('');
    setLoading(true);
    try {
      await signup({ name, email, password, english_level: level, goal });
      navigate('/chat');
    } catch (err) {
      setError(err.message || 'Failed to create account');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-bg-orb auth-bg-orb-1" />
      <div className="auth-bg-orb auth-bg-orb-2" />

      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <div className="auth-logo">
              <div className="auth-logo-icon">🌟</div>
              <span className="auth-logo-text">LinguaMate</span>
            </div>
            <h1 className="auth-title">
              {step === 1 ? 'Join the family!' : 'Tell us about you'}
            </h1>
            <p className="auth-subtitle">
              {step === 1
                ? 'Create your account and meet Mira'
                : 'So Mira can personalize your experience'}
            </p>
          </div>

          {error && <div className="auth-error">{error}</div>}

          <form className="auth-form" onSubmit={handleSubmit}>
            {step === 1 ? (
              <>
                <div className="input-group">
                  <label className="input-label" htmlFor="signup-name">Your Name</label>
                  <input
                    id="signup-name"
                    type="text"
                    className="input"
                    placeholder="What should Mira call you?"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    autoFocus
                  />
                </div>

                <div className="input-group">
                  <label className="input-label" htmlFor="signup-email">Email</label>
                  <input
                    id="signup-email"
                    type="email"
                    className="input"
                    placeholder="your@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>

                <div className="input-group">
                  <label className="input-label" htmlFor="signup-password">Password</label>
                  <input
                    id="signup-password"
                    type="password"
                    className="input"
                    placeholder="At least 6 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={6}
                  />
                </div>

                <button type="submit" className="btn btn-primary btn-lg w-full">
                  Continue →
                </button>
              </>
            ) : (
              <>
                <div className="input-group">
                  <label className="input-label">Your English Level</label>
                  <div className="level-selector">
                    {LEVELS.map((l) => (
                      <button
                        key={l}
                        type="button"
                        className={`level-option ${level === l ? 'active' : ''}`}
                        onClick={() => setLevel(l)}
                      >
                        {l === 'beginner' ? '🌱' : l === 'intermediate' ? '🌿' : '🌳'} {l}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="input-group">
                  <label className="input-label">Your Goal</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {GOALS.map((g) => (
                      <button
                        key={g.value}
                        type="button"
                        className={`level-option ${goal === g.value ? 'active' : ''}`}
                        onClick={() => setGoal(g.value)}
                        style={{ textAlign: 'left' }}
                      >
                        {g.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-lg"
                    onClick={() => setStep(1)}
                  >
                    ← Back
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary btn-lg"
                    style={{ flex: 1 }}
                    disabled={loading}
                  >
                    {loading ? '✨ Creating...' : '🎉 Meet Mira'}
                  </button>
                </div>
              </>
            )}
          </form>

          <div className="auth-footer">
            Already have an account? <Link to="/login">Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
