# 🌟 LinguaMate AI

> **Your AI family member who helps you become fluent in English.**

LinguaMate AI is an AI-powered English learning companion that teaches through natural conversation — like talking to a caring family member who remembers your life, adapts to your level, and helps you grow.

## ✨ Features

- **🤗 Meet Mira** — Your AI companion who talks like a caring friend, not a textbook
- **🧠 Family Memory** — Remembers your job, exams, hobbies, and references them naturally
- **✏️ Gentle Corrections** — Models correct English inside replies instead of saying "WRONG"
- **🎯 Daily Missions** — Personalized speaking tasks based on your level
- **📚 Vocabulary Builder** — Tracks words you use and suggests richer alternatives
- **💪 Confidence Mode** — Detects hesitation and responds with encouragement
- **📊 Progress Dashboard** — Streaks, vocabulary growth, corrections history

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| Styling | Vanilla CSS (dark glassmorphism design) |
| Backend | Python + FastAPI |
| Database | PostgreSQL + pgvector |
| Cache | Redis |
| AI | OpenAI GPT API |

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker Desktop (for PostgreSQL + Redis)
- OpenAI API key

### 1. Start the databases

```bash
docker-compose up -d
```

This starts PostgreSQL (with pgvector) on port 5432 and Redis on port 6379.

### 2. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set up environment
copy ..\.env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run the server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

### 4. Open the app

Visit **http://localhost:5173** — create an account and start chatting with Mira! 🤗

## 📁 Project Structure

```
linguamate/
├── frontend/          # React + Vite
│   └── src/
│       ├── pages/     # ChatPage, DashboardPage, TasksPage, LoginPage, SignupPage
│       ├── context/   # AuthContext
│       ├── services/  # API service
│       └── styles/    # Design system CSS
│
├── backend/           # Python + FastAPI
│   └── app/
│       ├── models/    # SQLAlchemy ORM (User, Conversation, Message, Memory, etc.)
│       ├── schemas/   # Pydantic request/response schemas
│       ├── routers/   # API endpoints (auth, conversations, tasks, progress)
│       ├── services/  # Business logic (AI, memory, chat pipeline, vocab, tasks)
│       └── utils/     # JWT auth, embeddings
│
├── docker-compose.yml # PostgreSQL + Redis
└── .env.example       # Environment variables template
```

## 🧠 How It Works

Every message flows through a 10-step pipeline:

1. **Store** user message
2. **Fetch** last 6 conversation turns
3. **Search** long-term memories (semantic/vector search)
4. **Load** today's task context
5. **Build** system prompt with all context
6. **Call** LLM with Mira persona + tool calling
7. **Extract** corrections, vocabulary, new memories, mood
8. **Store** AI reply with metadata
9. **Update** vocabulary tracking
10. **Stream** reply to the user

## 📄 License

MIT
