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

const LANGUAGES = [
  { value: 'English',    flag: '🇬🇧', label: 'English' },
  { value: 'Spanish',    flag: '🇪🇸', label: 'Spanish' },
  { value: 'French',     flag: '🇫🇷', label: 'French' },
  { value: 'German',     flag: '🇩🇪', label: 'German' },
  { value: 'Italian',    flag: '🇮🇹', label: 'Italian' },
  { value: 'Japanese',   flag: '🇯🇵', label: 'Japanese' },
  { value: 'Mandarin',   flag: '🇨🇳', label: 'Mandarin' },
  { value: 'Portuguese', flag: '🇧🇷', label: 'Portuguese' },
  { value: 'Russian',    flag: '🇷🇺', label: 'Russian' },
  { value: 'Arabic',     flag: '🇸🇦', label: 'Arabic' },
  { value: 'Hindi',      flag: '🇮🇳', label: 'Hindi' },
  { value: 'Korean',     flag: '🇰🇷', label: 'Korean' },
  { value: 'Dutch',      flag: '🇳🇱', label: 'Dutch' },
  { value: 'Swedish',    flag: '🇸🇪', label: 'Swedish' },
  { value: 'Turkish',    flag: '🇹🇷', label: 'Turkish' },
];

export default function SignupPage() {
  const [step, setStep] = useState(1);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [level, setLevel] = useState('beginner');
  const [goal, setGoal] = useState('casual_fluency');
  const [companion, setCompanion] = useState('mira');
  const [targetLanguage, setTargetLanguage] = useState('English');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { signup } = useAuth();
  const navigate = useNavigate();

  const totalSteps = 3;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (step < totalSteps) {
      setStep(step + 1);
      return;
    }

    setError('');
    setLoading(true);
    try {
      await signup({ name, email, password, english_level: level, goal, companion, target_language: targetLanguage });
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
              {step === 1 ? 'Join the family!' : step === 2 ? 'Pick your language' : 'Tell us about you'}
            </h1>
            <p className="auth-subtitle">
              {step === 1
                ? 'Create your account to get started'
                : step === 2
                ? 'Which language do you want to learn?'
                : 'So your AI companion can personalize your experience'}
            </p>
            {/* Step indicator */}
            <div style={{ display: 'flex', gap: '6px', justifyContent: 'center', marginTop: '12px' }}>
              {[1, 2, 3].map(s => (
                <div key={s} style={{
                  width: s === step ? '24px' : '8px',
                  height: '8px',
                  borderRadius: '4px',
                  background: s <= step ? 'var(--primary)' : 'var(--border)',
                  transition: 'all 0.3s ease',
                }} />
              ))}
            </div>
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
                    placeholder="What should we call you?"
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
            ) : step === 2 ? (
              <>
                <div className="input-group">
                  <label className="input-label">Choose a Language to Learn</label>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: '8px',
                    maxHeight: '320px',
                    overflowY: 'auto',
                    paddingRight: '4px',
                  }}>
                    {LANGUAGES.map((lang) => (
                      <button
                        key={lang.value}
                        type="button"
                        id={`lang-${lang.value.toLowerCase()}`}
                        className={`level-option ${targetLanguage === lang.value ? 'active' : ''}`}
                        onClick={() => setTargetLanguage(lang.value)}
                        style={{ flexDirection: 'column', gap: '4px', padding: '10px 4px', fontSize: '0.8rem' }}
                      >
                        <span style={{ fontSize: '1.4rem' }}>{lang.flag}</span>
                        {lang.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-lg"
                    onClick={() => setStep(1)}
                  >
                    ← Back
                  </button>
                  <button type="submit" className="btn btn-primary btn-lg" style={{ flex: 1 }}>
                    Continue →
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="input-group">
                  <label className="input-label">Your {targetLanguage} Level</label>
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
                  <label className="input-label">Your Companion</label>
                  <div className="level-selector" style={{ display: 'flex', gap: '8px' }}>
                    <button
                      type="button"
                      className={`level-option ${companion === 'mira' ? 'active' : ''}`}
                      onClick={() => setCompanion('mira')}
                      style={{ flex: 1 }}
                    >
                      🤗 Mira (Female)
                    </button>
                    <button
                      type="button"
                      className={`level-option ${companion === 'leo' ? 'active' : ''}`}
                      onClick={() => setCompanion('leo')}
                      style={{ flex: 1 }}
                    >
                      👦 Leo (Male)
                    </button>
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
                    onClick={() => setStep(2)}
                  >
                    ← Back
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary btn-lg"
                    style={{ flex: 1 }}
                    disabled={loading}
                  >
                    {loading ? '✨ Creating...' : '🎉 Get Started'}
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
