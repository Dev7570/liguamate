import { useState, useEffect } from 'react';
import api from '../../services/api';
import '../../styles/games.css';

export default function FillBlanksGame({ onComplete }) {
  const [rounds, setRounds] = useState([]);
  const [currentRound, setCurrentRound] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [isRevealed, setIsRevealed] = useState(false);
  const [score, setScore] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadGame();
  }, []);

  const loadGame = async () => {
    try {
      setLoading(true);
      const res = await api.getBlanksGame();
      setRounds(res.rounds);
    } catch (err) {
      setError('Failed to load game');
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (idx) => {
    if (isRevealed) return;
    setSelectedOption(idx);
    setIsRevealed(true);
    
    if (idx === rounds[currentRound].correct) {
      setScore(s => s + 1);
    }
  };

  const handleNext = () => {
    if (currentRound < rounds.length - 1) {
      setCurrentRound(c => c + 1);
      setSelectedOption(null);
      setIsRevealed(false);
    } else {
      if (onComplete) {
        onComplete({ score, total: rounds.length });
      }
    }
  };

  if (loading) return <div>Loading game...</div>;
  if (error) return <div className="text-danger">{error}</div>;
  if (!rounds.length) return <div>No rounds available.</div>;

  const round = rounds[currentRound];
  const parts = round.sentence.split('_____');

  return (
    <div className="blanks-game-container">
      <div className="match-stats">
        <span>Question {currentRound + 1} / {rounds.length}</span>
        <span>Score: {score}</span>
      </div>

      <div className="blanks-sentence-card">
        <div className="blanks-sentence">
          {parts[0]}
          <span className="blank-slot">
            {isRevealed && selectedOption !== null ? round.options[selectedOption] : '_____'}
          </span>
          {parts[1]}
        </div>

        <div className="blanks-options">
          {round.options.map((opt, idx) => {
            let btnClass = 'blank-option-btn';
            if (isRevealed) {
              if (idx === round.correct) btnClass += ' correct';
              else if (idx === selectedOption && idx !== round.correct) btnClass += ' incorrect';
            } else if (idx === selectedOption) {
              btnClass += ' selected';
            }

            return (
              <button
                key={idx}
                className={btnClass}
                onClick={() => handleSelect(idx)}
                disabled={isRevealed}
              >
                {opt}
              </button>
            );
          })}
        </div>
      </div>

      <div className="blanks-controls">
        {isRevealed && (
          <button className="btn btn-primary" onClick={handleNext}>
            {currentRound < rounds.length - 1 ? 'Next Sentence ➔' : 'Finish Game'}
          </button>
        )}
      </div>
    </div>
  );
}
