# AI-Powered Smart Study Planner

An evidence-driven, adaptive learning platform that manages student state, memory, mastery, and scheduling deterministically—utilizing AI for Socratic tutoring, explanation, and grounded question generation without allowing LLMs to directly dictate authoritative academic truth.

---

## 🏗️ Architecture & Philosophy

```text
STUDENT STATE
      ↓
EVIDENCE (Knowledge, Memory, Behavior, Self-Rating)
      ↓
LEARNER INTELLIGENCE (Bayesian Knowledge Tracing + FSRS Spaced Repetition + Prerequisite Graph)
      ↓
DECISION & RECOMMENDATION ENGINE ("What should I study now and why?")
      ↓
CONSTRAINT-AWARE ADAPTIVE PLANNER (Google OR-Tools CP-SAT)
      ↓
INTERVENTIONS (Study Sessions, Grounded Quizzes, Notes RAG, Socratic AI Tutor)
      ↓
LEARNING OUTCOMES & REPAIR EVIDENCE
      ↓
UPDATED DETERMINISTIC STUDENT STATE ↺
```

### Core Separation of Concerns
- **Deterministic Knowledge State**: Bayesian Knowledge Tracing (BKT) and Free Spaced Repetition Scheduling (FSRS) run deterministically on the backend. Skipping a task records behavioral latency without degrading knowledge mastery (Anti-Feedback Rule).
- **Non-Authoritative LLM (Google Gemini / Local)**: Generates explanations, analogies, Socratic questions, and 10-point summaries from parsed vector chunks. It does *not* set grades, mastery probabilities, or deadlines.
- **Dual-Database Architecture**:
  - **MongoDB** (`mongodb://localhost:27017`): User identity, sessions, academic profiles, 6-step onboarding wizard state, user preferences, settings, and cached 10-point document summaries.
  - **PostgreSQL + pgvector** (`localhost:5432`): Authoritative relational data, BKT posterior states, FSRS retrievability matrices, study tasks, exam milestones, audit trails, and vector chunks/embeddings.

---

## 🚀 Student Journey & Pages

The application is structured into a streamlined educational journey:

1. **Landing Page** (`/`): Value proposition, cognitive engine architecture, and feature highlights.
2. **Registration & Auth** (`/signup`, `/login`, `/forgot-password`): Secure Argon2/bcrypt password hashing, JWT sessions, demo quick-fill helper.
3. **6-Step Onboarding Wizard** (`/onboarding`):
   - Step 1: Educational Track Selection (College / High School / Competitive Exams)
   - Step 2: University & Degree Profile
   - Step 3: Automated Syllabus Discovery (Curriculum search and unit extraction)
   - Step 4: Syllabus Confirmation & Topic Customization
   - Step 5: Goals, Deadlines & Weekly Availability Windows
   - Step 6: Baseline Diagnostic Quiz & Automatic First Plan Generation
4. **Cockpit Home** (`/home`): "What should I study now?", top recommended task with explainable rationale, today's agenda, and study session launcher.
5. **My Plan** (`/plan`): Interactive agenda, task lock/unlock, reschedule, skip with anti-feedback safety, live countdown timer session modal, and OR-Tools rebalancer.
6. **Curriculum Subjects** (`/subjects`): Catalog of registered courses, curriculum health barometer, and search filter.
7. **Subject Breakdown** (`/subjects/[subjectId]`): Unit topics, BKT mastery status badges (Mastered, Developing, Needs Attention), and direct intervention triggers.
8. **Topic Intelligence** (`/subjects/[subjectId]/topics/[topicId]`): Deep drilldown into BKT mastery probability, uncertainty interval, FSRS memory stability half-life, and metacognitive self-calibration slider.
9. **Practice Hub** (`/practice`): Weak topics rescue drill, FSRS spaced review, lecture notes recall, and custom practice builder.
10. **Interactive Quiz Runner** (`/practice/[sessionId]`): Step-by-step assessment, instant answer verification with pedagogical explanations, and automated BKT posterior updates.
11. **Socratic AI Tutor** (`/tutor`): Multimodal tutor with topic curriculum context, 5 instructional modes (Socratic Dialog, ELI5, Deep Dive, Exam Rubric, Step Hint), and grounded document citations.
12. **Materials & Notes RAG** (`/materials`, `/materials/[documentId]`): Document upload (PDF, DOCX, TXT, MD), vector chunking, 10-point pedagogical synthesis, interactive 3D flip flashcard deck, and notes quiz generator.
13. **Progress Dashboard** (`/progress`): Comprehensive analytics, topic mastery distribution, FSRS review queue, exam countdowns, and study session history.
14. **Profile & Settings** (`/profile`, `/settings`): Academic profile editor, daily capacity slider, preferred study time, tutor default mode, reduced motion accessibility, weekly availability schedule, target exams, and study goals.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js 16 (Turbopack), React 19, TypeScript, Tailwind CSS v4, TanStack Query |
| **Backend** | FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic, Motor (MongoDB async) |
| **Databases** | PostgreSQL 16 + pgvector, MongoDB 7.0, Valkey 7.2 (Redis-compatible) |
| **Optimization** | Google OR-Tools (CP-SAT Constraint Programming Solver) |
| **AI / LLM** | Google Gemini AI (`gemini-2.5-flash`), Ollama fallback, Qwen embeddings |

---

## 📦 Getting Started

### 1. Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.11+

### 2. Environment Configuration
Copy the template configuration:
```bash
cp .env.example .env
```

Set your credentials in `.env`:
```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=smart_study_planner
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/smart_study_planner
POSTGRES_URL=postgresql+psycopg://postgres:postgres@localhost:5432/smart_study_planner
GOOGLE_API_KEY=your_google_ai_key_here
GOOGLE_AI_MODEL=gemini-2.5-flash
```

### 3. Launch Docker Database Services
```bash
docker compose up -d postgres valkey mongodb
```

### 4. Run Backend Server
```bash
cd apps/api
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available at: `http://localhost:8000/docs`

### 5. Run Frontend Web App
```bash
cd apps/web
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 🧪 Testing & Verification

### Run Backend Unit & Integration Tests (85 tests)
```bash
cd apps/api
.venv/bin/pytest -v
```

### Run Full Student Journey End-to-End Test
```bash
cd apps/api
.venv/bin/pytest tests/test_full_student_journey.py -v
```

### Run Frontend Production Build & TypeScript Check
```bash
cd apps/web
npm run build
```

---

## 🛡️ Security & Tenant Isolation
- **Authentication**: JWT tokens with strict bearer validation.
- **Tenant Isolation**: Every subject, topic, document chunk, and study task enforces `user_id` ownership checks in database queries and vector similarity searches.
- **Anti-Prompt Injection**: Document chunks retrieved during RAG are bounded in strict delimiter blocks with instructions preventing prompt hijacking.
- **SSRF Defense**: Research and discovery crawlers block private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`).
- **Secret Isolation**: All AI and database credentials remain server-side; zero secrets exposed to client browsers.
# AI_Smart_Study_Planner_Student_Product_Spec
