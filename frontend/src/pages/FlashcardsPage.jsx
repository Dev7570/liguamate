/**
 * Flashcards Page — Custom deck management with 3D flip-card SRS review
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import '../styles/flashcards.css';

const LANGUAGES = ['English','Spanish','French','German','Italian','Japanese','Mandarin','Portuguese','Russian','Arabic','Hindi','Korean'];

export default function FlashcardsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [view, setView] = useState('decks'); // 'decks' | 'cards' | 'review'
  const [decks, setDecks] = useState([]);
  const [activeDeck, setActiveDeck] = useState(null);
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNewDeck, setShowNewDeck] = useState(false);
  const [showAddCard, setShowAddCard] = useState(false);
  const [newDeck, setNewDeck] = useState({ name: '', language: user?.target_language||'English' });
  const [newCard, setNewCard] = useState({ front: '', back: '', phonetic: '', example: '' });
  const [saving, setSaving] = useState(false);

  // Review state
  const [reviewQueue, setReviewQueue] = useState([]);
  const [reviewIdx, setReviewIdx] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [reviewDone, setReviewDone] = useState(false);
  const [reviewStats, setReviewStats] = useState({ correct: 0, incorrect: 0 });

  useEffect(() => { loadDecks(); }, []);

  const loadDecks = async () => {
    try { setLoading(true); const d = await api.getFlashcardDecks(); setDecks(d); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const openDeck = async (deck) => {
    setActiveDeck(deck);
    setLoading(true);
    try { const c = await api.getFlashcardCards(deck.id); setCards(c); setView('cards'); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const createDeck = async (e) => {
    e.preventDefault(); if (!newDeck.name.trim()) return;
    setSaving(true);
    try { const d = await api.createFlashcardDeck(newDeck); setDecks(prev => [...prev, d]); setNewDeck({ name:'', language: user?.target_language||'English' }); setShowNewDeck(false); }
    catch (e) { alert(e.message); }
    finally { setSaving(false); }
  };

  const deleteDeck = async (id) => {
    if (!confirm('Delete this deck and all its cards?')) return;
    await api.deleteFlashcardDeck(id);
    setDecks(prev => prev.filter(d => d.id !== id));
    if (activeDeck?.id === id) { setActiveDeck(null); setView('decks'); }
  };

  const addCard = async (e) => {
    e.preventDefault(); if (!newCard.front.trim() || !newCard.back.trim()) return;
    setSaving(true);
    try { const c = await api.addFlashcard(activeDeck.id, newCard); setCards(prev => [...prev, {...c, is_due: true}]); setNewCard({ front:'', back:'', phonetic:'', example:'' }); setShowAddCard(false); }
    catch (e) { alert(e.message); }
    finally { setSaving(false); }
  };

  const deleteCard = async (cardId) => {
    await api.deleteFlashcard(cardId);
    setCards(prev => prev.filter(c => c.id !== cardId));
  };

  const startReview = () => {
    const due = cards.filter(c => c.is_due || c.times_reviewed === 0);
    if (due.length === 0) { alert('No cards due for review! Come back tomorrow.'); return; }
    setReviewQueue(due);
    setReviewIdx(0);
    setIsFlipped(false);
    setReviewDone(false);
    setReviewStats({ correct: 0, incorrect: 0 });
    setView('review');
  };

  const handleReview = async (quality) => {
    const card = reviewQueue[reviewIdx];
    try { await api.reviewFlashcard(card.id, quality); }
    catch (e) { console.error(e); }
    const correct = quality >= 3;
    setReviewStats(s => ({ correct: s.correct + (correct?1:0), incorrect: s.incorrect + (correct?0:1) }));
    if (reviewIdx + 1 >= reviewQueue.length) { setReviewDone(true); }
    else { setReviewIdx(i => i+1); setIsFlipped(false); }
  };

  const importVocab = async () => {
    const name = prompt('Name for your imported deck:', 'My Vocabulary');
    if (!name) return;
    try { const d = await api.importVocabAsFlashcards({ name, language: user?.target_language||'English' }); alert(d.message); loadDecks(); }
    catch (e) { alert(e.message||'Import failed'); }
  };

  if (loading && view === 'decks') return <div className="fc-layout"><div className="fc-loading"><div className="fc-spinner"/><p>Loading your flashcards...</p></div></div>;

  // ── Review Mode ─────────────────────────────────────────────────────────────
  if (view === 'review') {
    const card = reviewQueue[reviewIdx];
    return (
      <div className="fc-layout">
        <header className="fc-header">
          <button className="fc-back-btn" onClick={() => { setView('cards'); loadDecks(); }}>← Exit Review</button>
          <h1>🗂️ Review Mode</h1>
          <div className="fc-review-progress">{reviewIdx+1} / {reviewQueue.length}</div>
        </header>
        <div className="fc-review-area">
          {reviewDone ? (
            <div className="fc-review-done">
              <div className="fc-done-icon">🎉</div>
              <h2>Review Complete!</h2>
              <div className="fc-done-stats">
                <div className="fc-done-stat correct">✅ {reviewStats.correct} Correct</div>
                <div className="fc-done-stat incorrect">❌ {reviewStats.incorrect} Incorrect</div>
              </div>
              <div className="fc-done-pct">{Math.round((reviewStats.correct/reviewQueue.length)*100)}% accuracy</div>
              <button className="fc-btn-primary" onClick={() => { setView('cards'); openDeck(activeDeck); }}>Back to Deck</button>
            </div>
          ) : (
            <>
              <div className="fc-review-meta">
                <div className="fc-review-bar"><div className="fc-review-bar-fill" style={{width:`${((reviewIdx)/reviewQueue.length)*100}%`}}/></div>
              </div>
              <div className={`fc-flip-card${isFlipped?' flipped':''}`} onClick={() => setIsFlipped(!isFlipped)}>
                <div className="fc-flip-inner">
                  <div className="fc-flip-front">
                    <div className="fc-card-side-label">Front</div>
                    <div className="fc-card-word">{card.front}</div>
                    {card.phonetic && <div className="fc-card-phonetic">{card.phonetic}</div>}
                    <div className="fc-tap-hint">Tap to reveal →</div>
                  </div>
                  <div className="fc-flip-back">
                    <div className="fc-card-side-label">Back</div>
                    <div className="fc-card-word">{card.back}</div>
                    {card.example && <div className="fc-card-example">"{card.example}"</div>}
                  </div>
                </div>
              </div>
              {isFlipped && (
                <div className="fc-quality-btns">
                  <p className="fc-quality-label">How well did you know it?</p>
                  <div className="fc-quality-row">
                    <button className="fc-q-btn fc-q-bad" onClick={() => handleReview(1)}>😣 Forgot</button>
                    <button className="fc-q-btn fc-q-ok" onClick={() => handleReview(3)}>🙂 Got it</button>
                    <button className="fc-q-btn fc-q-good" onClick={() => handleReview(5)}>🌟 Easy!</button>
                  </div>
                </div>
              )}
              {!isFlipped && <p className="fc-flip-instruction">Click the card to flip it</p>}
            </>
          )}
        </div>
      </div>
    );
  }

  // ── Cards View ──────────────────────────────────────────────────────────────
  if (view === 'cards') return (
    <div className="fc-layout">
      <header className="fc-header">
        <button className="fc-back-btn" onClick={() => setView('decks')}>← Decks</button>
        <h1>🗂️ {activeDeck?.name}</h1>
        <div className="fc-header-actions">
          <button className="fc-btn-secondary" onClick={() => setShowAddCard(true)}>+ Add Card</button>
          <button className="fc-btn-primary" onClick={startReview} disabled={cards.filter(c=>c.is_due||c.times_reviewed===0).length===0}>
            Review ({cards.filter(c=>c.is_due||c.times_reviewed===0).length} due)
          </button>
        </div>
      </header>
      <div className="fc-content">
        <div className="fc-deck-stats">
          <div className="fc-stat"><div className="fc-stat-n">{cards.length}</div><div className="fc-stat-l">Total</div></div>
          <div className="fc-stat"><div className="fc-stat-n fc-due">{cards.filter(c=>c.is_due||c.times_reviewed===0).length}</div><div className="fc-stat-l">Due</div></div>
          <div className="fc-stat"><div className="fc-stat-n fc-master">{cards.filter(c=>c.is_mastered).length}</div><div className="fc-stat-l">Mastered</div></div>
        </div>
        {showAddCard && (
          <div className="fc-modal-overlay" onClick={() => setShowAddCard(false)}>
            <div className="fc-modal" onClick={e=>e.stopPropagation()}>
              <h3>Add New Card</h3>
              <form onSubmit={addCard} className="fc-form">
                <input className="fc-input" placeholder="Front (word / question) *" value={newCard.front} onChange={e=>setNewCard({...newCard,front:e.target.value})} required/>
                <textarea className="fc-input fc-textarea" placeholder="Back (definition / answer) *" value={newCard.back} onChange={e=>setNewCard({...newCard,back:e.target.value})} required/>
                <input className="fc-input" placeholder="Phonetic (optional)" value={newCard.phonetic} onChange={e=>setNewCard({...newCard,phonetic:e.target.value})}/>
                <input className="fc-input" placeholder="Example sentence (optional)" value={newCard.example} onChange={e=>setNewCard({...newCard,example:e.target.value})}/>
                <div className="fc-modal-actions">
                  <button type="button" className="fc-btn-secondary" onClick={() => setShowAddCard(false)}>Cancel</button>
                  <button type="submit" className="fc-btn-primary" disabled={saving}>{saving?'Adding...':'Add Card'}</button>
                </div>
              </form>
            </div>
          </div>
        )}
        <div className="fc-cards-grid">
          {cards.length === 0 && <div className="fc-empty"><p>No cards yet!</p><p>Add your first card using the button above.</p></div>}
          {cards.map(c => (
            <div key={c.id} className={`fc-card-item${c.is_mastered?' mastered':c.is_due?' due':''}`}>
              <div className="fc-card-status">{c.is_mastered?'🏆 Mastered':c.is_due?'📅 Due':'✅ Reviewed'}</div>
              <div className="fc-card-front">{c.front}</div>
              {c.phonetic && <div className="fc-card-phonetic-sm">{c.phonetic}</div>}
              <div className="fc-card-back">{c.back}</div>
              {c.example && <div className="fc-card-example-sm">"{c.example}"</div>}
              <div className="fc-card-footer">
                <span>{c.times_reviewed}x reviewed</span>
                <button className="fc-delete-btn" onClick={() => deleteCard(c.id)}>🗑️</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  // ── Decks View (default) ─────────────────────────────────────────────────────
  return (
    <div className="fc-layout">
      <header className="fc-header">
        <button className="fc-back-btn" onClick={() => navigate('/chat')}>← Back to Chat</button>
        <h1>🗂️ My Flashcard Decks</h1>
        <div className="fc-header-actions">
          <button className="fc-btn-secondary" onClick={importVocab}>📥 Import Vocab</button>
          <button className="fc-btn-primary" onClick={() => setShowNewDeck(true)}>+ New Deck</button>
        </div>
      </header>
      <div className="fc-content">
        {showNewDeck && (
          <div className="fc-modal-overlay" onClick={() => setShowNewDeck(false)}>
            <div className="fc-modal" onClick={e=>e.stopPropagation()}>
              <h3>Create New Deck</h3>
              <form onSubmit={createDeck} className="fc-form">
                <input className="fc-input" placeholder="Deck name (e.g. IELTS Words) *" value={newDeck.name} onChange={e=>setNewDeck({...newDeck,name:e.target.value})} required autoFocus/>
                <select className="fc-input" value={newDeck.language} onChange={e=>setNewDeck({...newDeck,language:e.target.value})}>
                  {LANGUAGES.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
                <div className="fc-modal-actions">
                  <button type="button" className="fc-btn-secondary" onClick={() => setShowNewDeck(false)}>Cancel</button>
                  <button type="submit" className="fc-btn-primary" disabled={saving}>{saving?'Creating...':'Create'}</button>
                </div>
              </form>
            </div>
          </div>
        )}
        {decks.length === 0 && !loading && (
          <div className="fc-empty fc-empty-center">
            <div className="fc-empty-icon">🗂️</div>
            <h2>No decks yet!</h2>
            <p>Create your first deck or import from your tracked vocabulary.</p>
            <div className="fc-empty-actions">
              <button className="fc-btn-primary" onClick={() => setShowNewDeck(true)}>+ Create Deck</button>
              <button className="fc-btn-secondary" onClick={importVocab}>📥 Import Vocabulary</button>
            </div>
          </div>
        )}
        <div className="fc-decks-grid">
          {decks.map(deck => (
            <div key={deck.id} className="fc-deck-card" onClick={() => openDeck(deck)}>
              <div className="fc-deck-header">
                <div className="fc-deck-icon">🗂️</div>
                <button className="fc-deck-delete" onClick={e=>{e.stopPropagation();deleteDeck(deck.id);}}>✕</button>
              </div>
              <div className="fc-deck-name">{deck.name}</div>
              <div className="fc-deck-lang">{deck.language}</div>
              <div className="fc-deck-meta">
                <span>{deck.card_count} cards</span>
                {deck.due_count > 0 && <span className="fc-deck-due">{deck.due_count} due</span>}
                {deck.mastered_count > 0 && <span className="fc-deck-mastered">🏆 {deck.mastered_count}</span>}
              </div>
              <div className="fc-deck-progress">
                <div className="fc-deck-bar"><div className="fc-deck-bar-fill" style={{width:`${deck.card_count>0?(deck.mastered_count/deck.card_count)*100:0}%`}}/></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
