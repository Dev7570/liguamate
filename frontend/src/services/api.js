/**
 * LinguaMate AI — API Service
 * Handles all backend communication including SSE streaming & audio transcription
 */
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiService {
  constructor() {
    this.token = localStorage.getItem('linguamate_token');
  }

  setToken(token) {
    this.token = token;
    localStorage.setItem('linguamate_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('linguamate_token');
    localStorage.removeItem('linguamate_user');
  }

  async request(endpoint, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...(this.token && { Authorization: `Bearer ${this.token}` }),
      ...options.headers,
    };

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.clearToken();
      window.location.href = '/login';
      throw new Error('Unauthorized');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Network error' }));
      throw new Error(error.detail || 'Request failed');
    }

    if (response.status === 204) {
      return null;
    }

    return response.json();
  }

  // ── Auth ──────────────────────────────────────────────────
  async signup(data) {
    const result = await this.request('/auth/signup', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(result.access_token);
    localStorage.setItem('linguamate_user', JSON.stringify({
      id: result.user_id,
      name: result.name,
    }));
    return result;
  }

  async login(email, password) {
    const result = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(result.access_token);
    localStorage.setItem('linguamate_user', JSON.stringify({
      id: result.user_id,
      name: result.name,
    }));
    return result;
  }

  async getProfile() {
    return this.request('/auth/me');
  }

  async updateProfile(data) {
    return this.request('/auth/me', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // ── Conversations ─────────────────────────────────────────
  async startConversation(channel = 'text') {
    return this.request('/conversations', {
      method: 'POST',
      body: JSON.stringify({ channel }),
    });
  }

  async deleteConversation(conversationId) {
    return this.request(`/conversations/${conversationId}`, {
      method: 'DELETE',
    });
  }

  async sendMessage(conversationId, content) {
    return this.request(`/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  }

  /**
   * Send a message and stream Mira's response via Server-Sent Events.
   *
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The user's message
   * @param {function} onToken - Called with each text token as it arrives
   * @param {function} onDone - Called with the final metadata object when streaming is complete
   * @param {function} onError - Called with an error message if something goes wrong
   * @returns {function} abort - Call this function to cancel the stream
   */
  sendMessageStream(conversationId, content, onToken, onDone, onError) {
    const abortController = new AbortController();

    const streamFetch = async () => {
      try {
        const response = await fetch(
          `${API_BASE}/conversations/${conversationId}/messages/stream`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(this.token && { Authorization: `Bearer ${this.token}` }),
            },
            body: JSON.stringify({ content }),
            signal: abortController.signal,
          }
        );

        if (response.status === 401) {
          this.clearToken();
          window.location.href = '/login';
          return;
        }

        if (!response.ok) {
          const error = await response.json().catch(() => ({ detail: 'Stream error' }));
          onError?.(error.detail || 'Stream failed');
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events from buffer
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event = JSON.parse(line.slice(6));
                if (event.type === 'token') {
                  onToken?.(event.content);
                } else if (event.type === 'done') {
                  onDone?.(event);
                } else if (event.type === 'error') {
                  onError?.(event.content);
                }
              } catch {
                // Skip malformed JSON lines
              }
            }
          }
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          onError?.(err.message || 'Connection lost');
        }
      }
    };

    streamFetch();

    // Return abort function
    return () => abortController.abort();
  }

  /**
   * Transcribe an audio blob to text using Whisper (Groq/OpenAI).
   *
   * @param {Blob} audioBlob - The recorded audio blob
   * @param {string} filename - Optional filename for the audio
   * @returns {Promise<string>} The transcribed text
   */
  async transcribeAudio(audioBlob, filename = 'recording.webm') {
    const formData = new FormData();
    formData.append('audio', audioBlob, filename);

    const response = await fetch(`${API_BASE}/conversations/transcribe`, {
      method: 'POST',
      headers: {
        ...(this.token && { Authorization: `Bearer ${this.token}` }),
      },
      body: formData,
    });

    if (response.status === 401) {
      this.clearToken();
      window.location.href = '/login';
      throw new Error('Unauthorized');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Transcription failed' }));
      throw new Error(error.detail || 'Transcription failed');
    }

    const result = await response.json();
    return result.text;
  }

  async endConversation(conversationId) {
    return this.request(`/conversations/${conversationId}/end`, {
      method: 'POST',
    });
  }

  async getMessages(conversationId) {
    return this.request(`/conversations/${conversationId}/messages`);
  }

  async getConversations() {
    return this.request('/conversations');
  }

  // ── Tasks ─────────────────────────────────────────────────
  async getTodayTasks() {
    return this.request('/tasks/today');
  }

  async completeTask(taskId, performanceNotes = null) {
    return this.request(`/tasks/${taskId}/complete`, {
      method: 'POST',
      body: JSON.stringify({ performance_notes: performanceNotes }),
    });
  }

  // ── Progress ──────────────────────────────────────────────
  async getDashboard() {
    return this.request('/progress/dashboard');
  }

  async getVocabulary(mastery = null) {
    const params = mastery ? `?mastery=${mastery}` : '';
    return this.request(`/progress/vocabulary${params}`);
  }

  async getLeaderboard() {
    return this.request('/progress/leaderboard');
  }

  // ── Activities, Quizzes & Badges ────────────────────────────
  async getQuiz() {
    return this.request('/activities/quiz');
  }

  async submitQuiz(score, total) {
    return this.request('/activities/quiz/submit', {
      method: 'POST',
      body: JSON.stringify({ score, total }),
    });
  }

  async getScenarios() {
    return this.request('/activities/scenarios');
  }

  async getMatchGame() {
    return this.request('/activities/games/match');
  }

  async getBlanksGame() {
    return this.request('/activities/games/blanks');
  }

  async getAchievements() {
    return this.request('/activities/achievements');
  }

  // ── Pronunciation ──────────────────────────────────────────
  async getPronunciationWords(level = 'beginner') {
    return this.request(`/pronunciation/words?level=${level}`);
  }

  async evaluatePronunciation(audioBlob, target, level = 'beginner') {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'pronunciation.webm');
    formData.append('target', target);
    formData.append('level', level);
    const response = await fetch(`${API_BASE}/pronunciation/evaluate`, {
      method: 'POST',
      headers: { ...(this.token && { Authorization: `Bearer ${this.token}` }) },
      body: formData,
    });
    if (!response.ok) { const e = await response.json().catch(()=>({detail:'Failed'})); throw new Error(e.detail); }
    return response.json();
  }

  // ── Flashcards ─────────────────────────────────────────────
  async getFlashcardDecks() { return this.request('/flashcards/decks'); }

  async createFlashcardDeck(data) {
    return this.request('/flashcards/decks', { method: 'POST', body: JSON.stringify(data) });
  }

  async deleteFlashcardDeck(id) {
    return this.request(`/flashcards/decks/${id}`, { method: 'DELETE' });
  }

  async getFlashcardCards(deckId) { return this.request(`/flashcards/decks/${deckId}/cards`); }

  async addFlashcard(deckId, data) {
    return this.request(`/flashcards/decks/${deckId}/cards`, { method: 'POST', body: JSON.stringify(data) });
  }

  async deleteFlashcard(cardId) {
    return this.request(`/flashcards/cards/${cardId}`, { method: 'DELETE' });
  }

  async reviewFlashcard(cardId, quality) {
    return this.request(`/flashcards/cards/${cardId}/review`, { method: 'POST', body: JSON.stringify({ quality }) });
  }

  async importVocabAsFlashcards(data) {
    return this.request('/flashcards/decks/import-vocab', { method: 'POST', body: JSON.stringify(data) });
  }

  // ── Language Exchange ──────────────────────────────────────
  async joinExchange() { return this.request('/exchange/join', { method: 'POST' }); }
  async getExchangeStatus() { return this.request('/exchange/status'); }
  async leaveExchange() { return this.request('/exchange/leave', { method: 'DELETE' }); }

  // ── Speaking Tests ─────────────────────────────────────────
  async getTestPrompts(testType = 'ielts', part = 'part1') {
    return this.request(`/tests/prompts?test_type=${testType}&part=${part}`);
  }

  async evaluateTest(audioBlob, testType, part, promptUsed) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'test.webm');
    formData.append('test_type', testType);
    formData.append('part', part);
    formData.append('prompt_used', promptUsed);
    const response = await fetch(`${API_BASE}/tests/evaluate`, {
      method: 'POST',
      headers: { ...(this.token && { Authorization: `Bearer ${this.token}` }) },
      body: formData,
    });
    if (!response.ok) { const e = await response.json().catch(()=>({detail:'Evaluation failed'})); throw new Error(e.detail); }
    return response.json();
  }

  async getTestHistory() { return this.request('/tests/history'); }

  // ── Insights ──────────────────────────────────────────────
  async getLiveInsights(conversationId) {
    return this.request(`/insights/live/${conversationId}`);
  }

  async getHistoricalInsights() {
    return this.request('/insights/history');
  }
}

const api = new ApiService();
export default api;
