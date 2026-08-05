import { useState, useEffect } from 'react';
import api from '../../services/api';
import '../../styles/games.css';

export default function WordMatchGame({ onComplete }) {
  const [cards, setCards] = useState([]);
  const [selectedCards, setSelectedCards] = useState([]);
  const [matchedIds, setMatchedIds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [moves, setMoves] = useState(0);

  useEffect(() => {
    loadGame();
  }, []);

  const loadGame = async () => {
    try {
      setLoading(true);
      const res = await api.getMatchGame();
      const pairs = res.pairs;
      
      // Create separate cards for word and meaning, shuffle them
      let generatedCards = [];
      pairs.forEach(p => {
        generatedCards.push({ id: `w-${p.id}`, type: 'word', text: p.word, matchId: p.id });
        generatedCards.push({ id: `m-${p.id}`, type: 'meaning', text: p.meaning, matchId: p.id });
      });
      
      // Fisher-Yates shuffle
      for (let i = generatedCards.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [generatedCards[i], generatedCards[j]] = [generatedCards[j], generatedCards[i]];
      }
      
      setCards(generatedCards);
    } catch (err) {
      setError('Failed to load game');
    } finally {
      setLoading(false);
    }
  };

  const handleCardClick = (card) => {
    if (matchedIds.includes(card.matchId) || selectedCards.find(c => c.id === card.id)) return;
    if (selectedCards.length >= 2) return;

    const newSelected = [...selectedCards, card];
    setSelectedCards(newSelected);

    if (newSelected.length === 2) {
      setMoves(m => m + 1);
      
      // Check match
      if (newSelected[0].matchId === newSelected[1].matchId && newSelected[0].type !== newSelected[1].type) {
        setMatchedIds(prev => [...prev, newSelected[0].matchId]);
        setSelectedCards([]);
        
        // Check win
        if (matchedIds.length + 1 === cards.length / 2) {
          setTimeout(() => {
            if (onComplete) onComplete({ moves: moves + 1, perfect: moves + 1 === cards.length / 2 });
          }, 500);
        }
      } else {
        setTimeout(() => setSelectedCards([]), 1000);
      }
    }
  };

  if (loading) return <div>Loading game...</div>;
  if (error) return <div className="text-danger">{error}</div>;

  return (
    <div className="match-game-container">
      <div className="match-stats">
        <span>Moves: {moves}</span>
        <span>Matched: {matchedIds.length} / {cards.length / 2}</span>
      </div>
      
      <div className="match-grid">
        {cards.map(card => {
          const isSelected = selectedCards.some(c => c.id === card.id);
          const isMatched = matchedIds.includes(card.matchId);
          
          return (
            <div
              key={card.id}
              className={`match-card ${isSelected ? 'selected' : ''} ${isMatched ? 'matched' : ''}`}
              onClick={() => handleCardClick(card)}
            >
              {card.text}
            </div>
          );
        })}
      </div>
    </div>
  );
}
