/**
 * Activities Page — Word Master Quizzes, Roleplay Scenarios & Achievements
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import WordMatchGame from '../components/games/WordMatchGame';
import FillBlanksGame from '../components/games/FillBlanksGame';
import '../styles/activities.css';

export default function ActivitiesPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState('quiz'); // 'quiz' | 'scenarios' | 'achievements'
  const [achievements, setAchievements] = useState(null);
  const [loading, setLoading] = useState(true);

  // Quiz state
  const [quizQuestions, setQuizQuestions] = useState([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [userAnswers, setUserAnswers] = useState([]);
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [quizResult, setQuizResult] = useState(null);
  const [submittingQuiz, setSubmittingQuiz] = useState(false);
  const [loadingQuiz, setLoadingQuiz] = useState(false);

  // Scenarios state
  const [scenarios, setScenarios] = useState([]);

  useEffect(() => {
    loadPageData();
  }, []);

  const loadPageData = async () => {
    try {
      setLoading(true);
      const [achData, scenData] = await Promise.all([
        api.getAchievements().catch(() => null),
        api.getScenarios().catch(() => null),
      ]);

      if (achData) setAchievements(achData);
      if (scenData?.scenarios) setScenarios(scenData.scenarios);

      // Load initial quiz
      await loadQuiz();
    } catch (err) {
      console.error('Failed to load activity data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadQuiz = async () => {
    try {
      setLoadingQuiz(true);
      setQuizSubmitted(false);
      setQuizResult(null);
      setCurrentIdx(0);
      setSelectedOption(null);
      setUserAnswers([]);

      const data = await api.getQuiz();
      if (data?.questions) {
        setQuizQuestions(data.questions);
      }
    } catch (err) {
      console.error('Failed to load quiz:', err);
    } finally {
      setLoadingQuiz(false);
    }
  };

  const handleSelectOption = (index) => {
    if (userAnswers[currentIdx] !== undefined || quizSubmitted) return;
    setSelectedOption(index);
  };

  const handleConfirmAnswer = () => {
    if (selectedOption === null) return;
    const newAnswers = [...userAnswers];
    newAnswers[currentIdx] = selectedOption;
    setUserAnswers(newAnswers);
  };

  const handleNextQuestion = () => {
    if (currentIdx < quizQuestions.length - 1) {
      setCurrentIdx((prev) => prev + 1);
      setSelectedOption(userAnswers[currentIdx + 1] ?? null);
    }
  };

  const handleSubmitQuiz = async () => {
    try {
      setSubmittingQuiz(true);
      let score = 0;
      quizQuestions.forEach((q, idx) => {
        if (userAnswers[idx] === q.correct) {
          score += 1;
        }
      });

      const res = await api.submitQuiz(score, quizQuestions.length);
      setQuizResult(res);
      setQuizSubmitted(true);

      // Refresh achievements after quiz score
      const freshAch = await api.getAchievements().catch(() => null);
      if (freshAch) setAchievements(freshAch);
    } catch (err) {
      console.error('Failed to submit quiz:', err);
    } finally {
      setSubmittingQuiz(false);
    }
  };

  const handleStartScenario = (scenario) => {
    // Navigate to ChatPage passing initial prompt and context
    navigate('/chat', {
      state: {
        initialPrompt: scenario.initial_prompt,
        scenarioTitle: scenario.title,
        scenarioEmoji: scenario.emoji,
      },
    });
  };

  if (loading) {
    return (
      <div className="activities-page">
        <div className="activities-container" style={{ textAlign: 'center', paddingTop: '100px' }}>
          <div className="animate-float" style={{ fontSize: '3rem' }}>🌟</div>
          <p style={{ color: 'var(--text-secondary)', marginTop: '16px' }}>Loading activities & achievements...</p>
        </div>
      </div>
    );
  }

  const ach = achievements || {
    level: 1,
    title: 'Novice Explorer',
    total_xp: 0,
    xp_in_level: 0,
    next_level_xp: 100,
    unlocked_count: 0,
    total_badges: 6,
    badges: [],
  };

  const currentQ = quizQuestions[currentIdx];
  const isAnswered = userAnswers[currentIdx] !== undefined;

  return (
    <div className="activities-page">
      <div className="activities-container">
        {/* Top Header */}
        <div className="activities-header">
          <div className="activities-title">
            <h1>
              <span className="text-gradient">Activities & Badges</span> 🎮
            </h1>
            <p>Practice with interactive quizzes, roleplay real life, and level up your English!</p>
          </div>
          <div className="activities-nav">
            <button className="btn btn-primary" onClick={() => navigate('/chat')}>
              💬 Chat with Mira
            </button>
            <button className="btn btn-secondary" onClick={() => navigate('/dashboard')}>
              📊 Dashboard
            </button>
            <button className="btn btn-secondary" onClick={() => navigate('/tasks')}>
              🎯 Tasks
            </button>
          </div>
        </div>

        {/* Level & XP Banner */}
        <div className="xp-summary-card">
          <div className="level-badge">
            <span className="level-number">{ach.level}</span>
            <span className="level-label">Level</span>
          </div>

          <div className="xp-info">
            <h2>
              <span>Level {ach.level}</span>
              <span className="user-title-tag">{ach.title}</span>
            </h2>
            <div className="xp-bar-container">
              <div className="xp-bar-track">
                <div
                  className="xp-bar-fill"
                  style={{ width: `${Math.min(100, (ach.xp_in_level / ach.next_level_xp) * 100)}%` }}
                />
              </div>
              <div className="xp-bar-labels">
                <span>{ach.xp_in_level} XP</span>
                <span>{ach.next_level_xp} XP to next level</span>
              </div>
            </div>
          </div>

          <div className="xp-total-display">
            <div className="xp-total-value">⚡ {ach.total_xp}</div>
            <div className="xp-total-label">Total XP Earned</div>
          </div>
        </div>

        {/* Tab Selection */}
        <div className="activity-tabs">
          <button
            className={`tab-btn ${activeTab === 'quiz' ? 'active' : ''}`}
            onClick={() => setActiveTab('quiz')}
          >
            🧠 Word Master Quiz
          </button>
          <button
            className={`tab-btn ${activeTab === 'match' ? 'active' : ''}`}
            onClick={() => setActiveTab('match')}
          >
            🃏 Word Match
          </button>
          <button
            className={`tab-btn ${activeTab === 'blanks' ? 'active' : ''}`}
            onClick={() => setActiveTab('blanks')}
          >
            ✍️ Fill Blanks
          </button>
          <button
            className={`tab-btn ${activeTab === 'scenarios' ? 'active' : ''}`}
            onClick={() => setActiveTab('scenarios')}
          >
            🎭 Roleplay Scenarios
          </button>
          <button
            className={`tab-btn ${activeTab === 'achievements' ? 'active' : ''}`}
            onClick={() => setActiveTab('achievements')}
          >
            🏆 Badges ({ach.unlocked_count}/{ach.total_badges})
          </button>
        </div>

        {activeTab === 'match' && (
          <WordMatchGame onComplete={({ moves, perfect }) => {
            if (perfect) alert('Perfect match! +20 XP');
            // Refresh achievements optionally
            api.getAchievements().then(setAchievements).catch(() => {});
          }} />
        )}

        {activeTab === 'blanks' && (
          <FillBlanksGame onComplete={({ score, total }) => {
            alert(`Game complete! You scored ${score}/${total}`);
            // Refresh achievements optionally
            api.getAchievements().then(setAchievements).catch(() => {});
          }} />
        )}

        {/* ── TAB 1: QUIZ ──────────────────────────────────────────────── */}
        {activeTab === 'quiz' && (
          <div>
            {loadingQuiz ? (
              <div className="quiz-card" style={{ textAlign: 'center', padding: '60px' }}>
                <div className="animate-float" style={{ fontSize: '2.5rem' }}>🧠</div>
                <p style={{ color: 'var(--text-secondary)', marginTop: '12px' }}>Generating your custom quiz...</p>
              </div>
            ) : quizSubmitted && quizResult ? (
              /* Quiz Results Screen */
              <div className="quiz-results-card">
                <div className="results-emoji">
                  {quizResult.is_perfect ? '🎉' : quizResult.score >= 3 ? '🌟' : '💪'}
                </div>
                <h2>Quiz Complete!</h2>
                <div className="results-score-badge">
                  {quizResult.score} / {quizResult.total}
                </div>
                <div>
                  <div className="xp-gained-callout">
                    ⚡ +{quizResult.xp_earned} XP Earned!
                  </div>
                </div>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
                  {quizResult.is_perfect
                    ? 'PERFECT SCORE! 50 Bonus XP awarded! You are a master!'
                    : quizResult.score >= 3
                    ? 'Great effort! Keep practicing to master every word.'
                    : 'Good attempt! Review your vocabulary and try again!'}
                </p>
                <button className="btn btn-primary btn-lg" onClick={loadQuiz}>
                  🔄 Take Another Quiz
                </button>
              </div>
            ) : currentQ ? (
              /* Quiz Question Card */
              <div className="quiz-card">
                <div className="quiz-header">
                  <span className="quiz-progress-text">
                    Question {currentIdx + 1} of {quizQuestions.length}
                  </span>
                  <div className="tasks-progress-bar" style={{ width: '120px' }}>
                    <div
                      className="tasks-progress-fill"
                      style={{ width: `${((currentIdx + 1) / quizQuestions.length) * 100}%` }}
                    />
                  </div>
                </div>

                <div className="quiz-question-box">
                  <span className="quiz-type-tag">{currentQ.type.replace('_', ' ')}</span>
                  <h3 className="quiz-question-text">{currentQ.question}</h3>
                </div>

                <div className="quiz-options">
                  {currentQ.options.map((optionText, idx) => {
                    let optionClass = 'quiz-option-btn';
                    if (isAnswered) {
                      if (idx === currentQ.correct) {
                        optionClass += ' correct';
                      } else if (userAnswers[currentIdx] === idx) {
                        optionClass += ' wrong';
                      }
                    } else if (selectedOption === idx) {
                      optionClass += ' selected';
                    }

                    return (
                      <button
                        key={idx}
                        className={optionClass}
                        onClick={() => handleSelectOption(idx)}
                        disabled={isAnswered}
                      >
                        <span className="quiz-option-index">
                          {String.fromCharCode(65 + idx)}
                        </span>
                        <span>{optionText}</span>
                      </button>
                    );
                  })}
                </div>

                {isAnswered && (
                  <div className="quiz-explanation">
                    <strong>💡 Explanation:</strong> {currentQ.explanation}
                  </div>
                )}

                <div className="quiz-actions">
                  {!isAnswered ? (
                    <button
                      className="btn btn-primary"
                      onClick={handleConfirmAnswer}
                      disabled={selectedOption === null}
                    >
                      Confirm Choice
                    </button>
                  ) : currentIdx < quizQuestions.length - 1 ? (
                    <button className="btn btn-primary" onClick={handleNextQuestion}>
                      Next Question ➔
                    </button>
                  ) : (
                    <button
                      className="btn btn-success btn-lg"
                      onClick={handleSubmitQuiz}
                      disabled={submittingQuiz}
                    >
                      {submittingQuiz ? 'Calculating Rewards...' : 'Submit Quiz & Claim XP 🏆'}
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="quiz-card" style={{ textAlign: 'center' }}>
                <p>No quiz questions available right now.</p>
                <button className="btn btn-primary" onClick={loadQuiz} style={{ marginTop: '12px' }}>
                  Try Loading Quiz
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── TAB 2: ROLEPLAY SCENARIOS ───────────────────────────────────── */}
        {activeTab === 'scenarios' && (
          <div className="scenarios-grid">
            {scenarios.map((scen) => (
              <div key={scen.id} className="scenario-card">
                <div className="scenario-card-top">
                  <div className="scenario-header">
                    <span className="scenario-emoji">{scen.emoji}</span>
                    <span className={`difficulty-tag difficulty-${scen.difficulty.toLowerCase()}`}>
                      {scen.difficulty}
                    </span>
                  </div>
                  <h3 className="scenario-title">{scen.title}</h3>
                  <div className="scenario-category">{scen.category}</div>
                  <p className="scenario-desc">{scen.description}</p>
                  <div className="scenario-sample-prompt">
                    "{scen.initial_prompt}"
                  </div>
                </div>

                <button
                  className="btn btn-primary"
                  style={{ width: '100%', marginTop: '16px' }}
                  onClick={() => handleStartScenario(scen)}
                >
                  🎭 Start Roleplay
                </button>
              </div>
            ))}
          </div>
        )}

        {/* ── TAB 3: BADGES & ACHIEVEMENTS ───────────────────────────────── */}
        {activeTab === 'achievements' && (
          <div className="badges-grid">
            {ach.badges.map((b) => (
              <div key={b.id} className={`badge-card ${b.unlocked ? 'unlocked' : 'locked'}`}>
                <div className="badge-icon">{b.emoji}</div>
                <div className="badge-info">
                  <h3>
                    <span>{b.name}</span>
                    {b.unlocked ? <span className="unlocked-check">✓ Unlocked</span> : <span>🔒</span>}
                  </h3>
                  <p>{b.description}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
