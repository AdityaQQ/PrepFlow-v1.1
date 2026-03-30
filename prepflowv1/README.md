# InterviewAI — AI-Powered Interview Preparation Platform

> Built by [Aditya Upadhyay](https://github.com/AdityaQQ) · Open Source

A production-ready, full-stack AI interview preparation platform with dark minimal aesthetics, real-time AI feedback, coding interviews, and resume-based sessions.

---

## Features

- **AI Interview Simulation** — AI-generated questions based on role, topic, and difficulty
- **Real-time AI Feedback** — Score, strengths, improvements, and model answers powered by Claude AI
- **Coding Interview** — Built-in code editor with AI evaluation of correctness and complexity
- **Resume-Based Interview** — Upload resume → AI generates tailored questions
- **Progress Dashboard** — Charts, analytics, weak areas, and performance tracking
- **Session History** — Full history of all interview sessions
- **Secure Authentication** — PBKDF2 password hashing, session management

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | HTML5, Tailwind CSS, Vanilla JS, Chart.js |
| Backend | Python Flask |
| Database | SQLite |
| AI | Anthropic Claude API |
| Fonts | JetBrains Mono, Inter |

---

## Project Structure

```
ai-interview-platform/
├── app.py                  # Main Flask app, routes
├── config.py               # Configuration
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── models/
│   └── database.py         # SQLite schema & connection
├── routes/
│   ├── auth.py             # Signup, login, logout
│   ├── interview.py        # AI question gen, feedback, coding
│   └── dashboard.py        # Stats, progress, resume upload
└── templates/
    ├── base.html           # Navbar, footer, watermark
    ├── index.html          # Landing page
    ├── login.html          # Login
    ├── signup.html         # Signup
    ├── dashboard.html      # User dashboard
    ├── interview.html      # AI interview simulator
    ├── coding.html         # Coding interview
    ├── resume.html         # Resume-based interview
    └── history.html        # Session history
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/AdityaQQ/ai-interview-platform
cd ai-interview-platform
```

### 2. Set up virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key
```

```env
SECRET_KEY=your-secure-random-key
DATABASE=interview_platform.db
ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Run the application

```bash
python app.py
```

Visit `http://localhost:5000`

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/signup` | Create account |
| POST | `/api/login` | Sign in |
| POST | `/api/logout` | Sign out |
| GET | `/api/me` | Current user |

### Interview
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/interview/start` | Start AI interview session |
| POST | `/api/interview/submit` | Submit answer, get AI feedback |
| POST | `/api/interview/end` | End session, get final score |
| GET | `/api/interview/history` | Past sessions |
| GET | `/api/interview/:id/answers` | Session answers |

### Coding
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/coding/problems` | Get coding problems |
| POST | `/api/coding/evaluate` | Evaluate code submission |

### Dashboard & Resume
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/stats` | User statistics |
| GET | `/api/dashboard/progress` | Score over time |
| POST | `/api/resume/upload` | Upload resume |
| POST | `/api/resume/interview` | Start resume interview |

---

## Database Schema

```sql
users (id, name, email, password, role, avatar, created_at)
interviews (id, user_id, role, topic, difficulty, score, total_questions, completed, interview_type, date)
answers (id, interview_id, question, answer, feedback, score, created_at)
resumes (id, user_id, filename, content, uploaded_at)
```

---

## Design Philosophy

Inspired by [mistilteinn.xyz](https://www.mistilteinn.xyz/) — minimal dark aesthetic with:
- Background: `#0a0a0a`
- Text: `#ffffff`
- Accent: `#888888`
- Fonts: JetBrains Mono + Inter
- Clean grid layouts, subtle borders, zero visual clutter

---

## Author

**Aditya Upadhyay**
- GitHub: [github.com/AdityaQQ](https://github.com/AdityaQQ)

---

© 2026 Aditya Upadhyay · Built by Aditya Upadhyay · Open Source by Aditya Upadhyay
