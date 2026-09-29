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
- **Non-Authoritative LLM (Google Gemini / Local Ollama)**: Generates explanations, analogies, Socratic questions, and 10-point summaries from parsed vector chunks. It does *not* set grades, mastery probabilities, or deadlines.
- **Dual-Database Architecture**:
  - **MongoDB** (`mongodb://localhost:27017`): User identity, sessions, academic profiles, 6-step onboarding wizard state, user preferences, settings, and cached 10-point document summaries.
  - **PostgreSQL + pgvector** (`localhost:5432`): Authoritative relational data, BKT posterior states, FSRS retrievability matrices, study tasks, exam milestones, audit trails, and vector chunks/embeddings.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js 16 (Turbopack), React 19, TypeScript, Tailwind CSS v4, TanStack Query, Lucide Icons |
| **Backend** | FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic, Motor (MongoDB async), Structlog |
| **Databases** | PostgreSQL 16 + pgvector, MongoDB 7.0, Valkey 7.2 (Redis-compatible) |
| **Optimization** | Google OR-Tools (CP-SAT Constraint Programming Solver) |
| **AI / LLM** | Google Gemini AI (`gemini-2.5-flash`), Ollama fallback (`qwen2.5-coder`), Qwen embeddings |

---

## 🚀 How to Load and Run the Project

You can run the project using **Local Development Mode** (recommended for code iteration) or **Full Docker Compose Mode**.

### Prerequisites
- **Git**
- **Docker & Docker Compose** (for running databases or all containerized services)
- **Node.js 20+** and **npm** (for the Next.js frontend)
- **Python 3.11+** (for the FastAPI backend)

---

### Method A: Local Development Setup (Recommended)

#### Step 1: Clone the Repository
```bash
git clone https://github.com/Krinz-hub/AI_Smart_Study_Planner_Student_Product_Spec.git
cd AI_Smart_Study_Planner_Student_Product_Spec
```

#### Step 2: Configure Environment Variables
Copy the template configuration into `.env`:
```bash
cp .env.example .env
```
Open `.env` and verify or set your keys. For Google Gemini AI integration, add your key:
```env
GOOGLE_API_KEY=your_actual_google_api_key_here
GOOGLE_AI_MODEL=gemini-2.5-flash
```
*(Note: If `GOOGLE_API_KEY` is omitted, the backend will automatically fallback to local Ollama inference).*

#### Step 3: Start Database Services via Docker
Start PostgreSQL (with `pgvector`), MongoDB, and Valkey (Redis-compatible cache) in the background:
```bash
docker compose up -d postgres valkey mongodb
```
To check that the database containers are healthy:
```bash
docker compose ps
```

#### Step 4: Set Up and Run the Backend API (FastAPI)
1. Navigate to the API directory:
   ```bash
   cd apps/api
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   # On Windows (cmd/PowerShell):
   # .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Run database migrations to apply the schema to PostgreSQL:
   ```bash
   alembic upgrade head
   ```
5. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   - API is live at: `http://localhost:8000`
   - Interactive Swagger API Documentation: `http://localhost:8000/docs`
   - Alternative ReDoc API Documentation: `http://localhost:8000/redoc`

#### Step 5: Set Up and Run the Frontend (Next.js)
Open a new terminal window:
1. Navigate to the web directory:
   ```bash
   cd apps/web
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Launch the Next.js Turbopack development server:
   ```bash
   npm run dev
   ```
4. Access the web application:
   Open [http://localhost:3000](http://localhost:3000) in your web browser.

---

### Method B: Full Docker Compose Setup (All-in-One)

To spin up all services (PostgreSQL + pgvector, MongoDB, Valkey, FastAPI backend, and Next.js frontend) in isolated Docker containers:

1. Configure `.env`:
   ```bash
   cp .env.example .env
   ```
2. Build and run all containers:
   ```bash
   docker compose up --build
   ```
3. Run migrations inside the API container (first launch only):
   ```bash
   docker compose exec api alembic upgrade head
   ```
4. Access:
   - Web App: `http://localhost:3000`
   - Backend API Docs: `http://localhost:8000/docs`

---

## 📖 How to Use the Application: Complete Walkthrough

### 1. Register or Sign In
- Navigate to `http://localhost:3000/signup`.
- Enter your name, email, and password to create an account.
- **Evaluation / Demo Helper**: On the `/login` page, you can click the **Testing & Evaluation helper** button to quick-fill demo credentials (`student_demo@example.com` / `Password123!`).

### 2. Complete the 6-Step Onboarding Wizard (`/onboarding`)
Upon first login, the platform guides you through the onboarding wizard:
1. **Track Selection**: Choose your learning context (e.g., University / College, High School, or Competitive Exam Prep).
2. **Academic Profile**: Specify your institution, degree program, and major (e.g., "Computer Science", "Stanford University").
3. **Automated Syllabus Discovery**: Type a curriculum topic or course title (e.g., "Data Structures and Algorithms") and click **Discover Syllabus**. The system queries curricula and structures units and topics.
4. **Syllabus Confirmation**: Review, edit, add, or remove topics and modules to reflect your exact course syllabus.
5. **Goals & Availability**: Set your target exam date, target grades, and weekly availability schedule (e.g., 2 hours on weekdays, 4 hours on weekends).
6. **Diagnostic Baseline Quiz**: Take a brief baseline diagnostic quiz. The Bayesian Knowledge Tracing (BKT) engine initializes your topic mastery posteriors and Google OR-Tools builds your personalized adaptive study plan.

### 3. Cockpit Dashboard (`/home`)
- **"What Should I Study Now and Why?"**: The intelligent decision card displays your top-priority study recommendation computed from BKT mastery gaps, FSRS retrievability, and upcoming exam urgency.
- **Explainable Rationale**: Understand the exact pedagogical reason why a task was recommended (e.g., "Memory half-life critical; retrievability fell below 70%").
- **Today's Agenda**: View your scheduled study sessions for the day and jump straight into them.

### 4. Interactive Study Plan (`/plan`)
- **Interactive Schedule**: View planned study sessions across days and time slots.
- **Live Focus Timer**: Click **Start Session** on any task to open the dedicated study modal with a live countdown timer, focus notes, and completion logging.
- **Task Management**:
  - **Lock/Unlock**: Pin specific sessions so the optimizer won't move them.
  - **Reschedule**: Move tasks to convenient slots.
  - **Skip (Anti-Feedback Rule)**: Safely skip tasks when life happens. The system updates behavioral latency without penalizing your knowledge mastery score.
- **Rebalance Plan**: Click **Rebalance** to invoke the Google OR-Tools CP-SAT constraint solver to reschedule remaining sessions within your availability windows.

### 5. Curriculum & Topic Mastery (`/subjects`)
- Browse registered subjects and track overall curriculum health.
- Click any subject to view its unit breakdown:
  - **Mastery Status**: View deterministic labels (`Mastered`, `Developing`, `Needs Attention`).
  - **Topic Intelligence (`/subjects/[subjectId]/topics/[topicId]`)**: Inspect BKT posterior probability, confidence intervals, and FSRS memory stability half-life.
  - **Metacognitive Calibration Slider**: Adjust your self-assessed confidence to calibrate against objective quiz performance.

### 6. Practice Hub & Active Recall (`/practice`)
- Launch targeted practice sessions:
  - **Weak Topics Rescue Drill**: Focuses strictly on sub-threshold mastery concepts.
  - **FSRS Spaced Review**: Reviews items due for memory consolidation according to the spacing algorithm.
  - **Lecture Notes Recall**: Generates questions grounded in your uploaded documents.
- **Interactive Quiz Runner (`/practice/[sessionId]`)**: Answer multiple-choice and conceptual questions with instant feedback, pedagogical step explanations, and automated posterior mastery updates.

### 7. Socratic AI Tutor (`/tutor`)
- Engage in an interactive, context-aware dialogue with an AI tutor grounded in your syllabus.
- Switch between 5 specialized pedagogical modes:
  - 🧠 **Socratic Dialog**: Prompts you with guiding questions rather than spoon-feeding answers.
  - 👶 **ELI5**: Simple, intuitive analogies and plain-language explanations.
  - 🔬 **Deep Dive**: Rigorous mathematical and technical explanations.
  - 📝 **Exam Rubric**: Scoring criteria, edge cases, and common pitfalls.
  - 💡 **Step Hint**: Incremental hints to unblock your problem-solving.

### 8. Lecture Notes & Document RAG (`/materials`)
- **Upload Course Materials**: Upload lecture slides, syllabi, or reading materials (`PDF`, `DOCX`, `TXT`, `MD`).
- **Pedagogical 10-Point Summary**: Get an automatic 10-point synthesis highlighting core formulas, concepts, and key definitions.
- **Interactive 3D Flashcard Deck**: Flip through generated active recall cards to test memory retention.
- **Generate Quiz from Document**: Create custom quizzes directly grounded in your uploaded text chunks via vector search.

### 9. Progress Analytics (`/progress`)
- View your global learning trajectory, mastery distributions across subjects, retention curves, upcoming exam milestones, and study time logs.

### 10. Profile & Custom Settings (`/profile`, `/settings`)
- Adjust daily capacity limits, preferred study times, tutor mode defaults, and accessibility preferences (e.g., reduced motion).

---

## ⚙️ Environment Configuration Reference

The application is configured using environment variables in `.env`:

| Variable | Description | Default | Required? |
|---|---|---|---|
| `APP_ENV` | Application environment (`development`, `production`, `testing`) | `development` | Yes |
| `SECRET_KEY` | Secret key used for signing JWT tokens | `supersecret-...` | Yes (change in prod) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiration time in minutes | `1440` (24h) | Yes |
| `DATABASE_URL` | PostgreSQL connection string with `psycopg` driver | `postgresql+psycopg://postgres:postgres@localhost:5432/smart_study_planner` | Yes |
| `MONGODB_URI` | MongoDB connection URI | `mongodb://localhost:27017` | Yes |
| `MONGODB_DATABASE` | MongoDB database name | `smart_study_planner` | Yes |
| `VALKEY_URL` | Redis/Valkey cache connection URI | `redis://localhost:6379/0` | Yes |
| `GOOGLE_API_KEY` | Google Gemini AI API key | `""` | Optional (falls back to Ollama) |
| `GOOGLE_AI_MODEL` | Gemini AI model identifier | `gemini-2.5-flash` | Yes |
| `LLM_PROVIDER` | Primary LLM provider (`gemini` or `ollama`) | `gemini` | Yes |
| `LLM_BASE_URL` | Base URL for local Ollama instance | `http://localhost:11434` | If using Ollama |
| `OLLAMA_LITE_MODEL` | Lightweight Ollama model for fallback | `qwen2.5-coder:1.5b` | If using Ollama |
| `NEXT_PUBLIC_API_URL` | Public API endpoint for frontend requests | `http://localhost:8000/api/v1` | Yes |

---

## 🧪 Testing & Verification

The project includes automated test suites covering authentication, BKT & FSRS learner intelligence, OR-Tools planner, document RAG, and the full student journey:

### Run Backend Unit & Integration Tests (85+ tests)
```bash
cd apps/api
source .venv/bin/activate
pytest -v
```

### Run Full Student Journey End-to-End Test
```bash
cd apps/api
source .venv/bin/activate
pytest tests/test_full_student_journey.py -v
```

### Test Academic Fact-Checking & Socratic Tutor Modes
```bash
cd apps/api
source .venv/bin/activate
pytest tests/test_academic_fact_check.py tests/test_tutor_all_modes.py -v
```

### Run Frontend Build & TypeScript Check
```bash
cd apps/web
npm run build
```

---

## 🔧 Troubleshooting & FAQs

### 1. Database Connection Errors
- **PostgreSQL**: Ensure the container is up (`docker compose ps`). Verify connectivity:
  ```bash
  docker compose exec postgres pg_isready -U postgres -d smart_study_planner
  ```
- **MongoDB**: Ensure MongoDB container is up. Verify ping:
  ```bash
  docker compose exec mongodb mongosh --eval "db.adminCommand('ping')"
  ```
- **Alembic Table Missing**: If you see errors like `relation "users" does not exist`, run:
  ```bash
  cd apps/api && .venv/bin/alembic upgrade head
  ```

### 2. AI / LLM Generation Issues
- If Google Gemini queries fail, check that `GOOGLE_API_KEY` in `.env` is valid and has quota.
- The system automatically degrades gracefully: if Gemini is unreachable, it logs a warning and attempts local Ollama or returns deterministic fallback responses.

### 3. Port Conflicts
- Ensure standard ports are free on your host:
  - `3000`: Next.js web application
  - `8000`: FastAPI backend
  - `5432`: PostgreSQL
  - `27017`: MongoDB
  - `6379`: Valkey / Redis

---

## 🛡️ Security & Privacy
- **JWT Authentication**: Password hashing via Argon2 and secure Bearer tokens.
- **Tenant Isolation**: Every subject, topic, document chunk, and study task enforces strict `user_id` authorization in database queries and vector similarity searches.
- **Anti-Prompt Injection**: Document chunks retrieved during RAG are bounded in strict delimiter blocks with defensive prompt wrappers.
- **SSRF Defense**: Research and discovery crawlers block private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`).
- **Zero Client Secrets**: All AI API keys and database credentials remain strictly server-side.
