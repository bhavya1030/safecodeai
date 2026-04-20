# SafeCodeAI

SafeCodeAI is a local, full-stack AI-powered code review tool for Python, C++, and Java — built for developers and DSA practitioners who want instant, deep static analysis without sending code to the cloud.

- **Next.js frontend** (`frontend/`) — auth, multi-tab Monaco editor, review history dashboard
- **FastAPI backend** (`backend/`) — JWT auth, SQLite/PostgreSQL storage, review API
- **Static analysis engine** (`src/`) — 30+ bug detectors across Python, C++, and Java

---

## Tech Stack

### Frontend
| Technology | Purpose |
|------------|---------|
| [Next.js 14](https://nextjs.org/) (App Router) | React framework, routing, SSR |
| [TypeScript](https://www.typescriptlang.org/) | Type-safe frontend code |
| [Tailwind CSS](https://tailwindcss.com/) | Utility-first styling |
| [Monaco Editor](https://microsoft.github.io/monaco-editor/) | In-browser code editor (same engine as VS Code) |
| [Material Symbols](https://fonts.google.com/icons) | Icon set |

### Backend
| Technology | Purpose |
|------------|---------|
| [FastAPI](https://fastapi.tiangolo.com/) | REST API framework (Python) |
| [SQLAlchemy](https://www.sqlalchemy.org/) | ORM for database access |
| [SQLite](https://www.sqlite.org/) / [PostgreSQL](https://www.postgresql.org/) | Storage (dev / prod) |
| [python-jose](https://github.com/mpdavis/python-jose) | JWT auth token generation and verification |
| [passlib + bcrypt](https://passlib.readthedocs.io/) | Password hashing |
| [uvicorn](https://www.uvicorn.org/) | ASGI server |

### Analysis Engine
| Technology | Purpose |
|------------|---------|
| Python `ast` module | AST-based static analysis for Python code |
| `g++` (GCC) | C++ compiler — catches semantic errors and warnings |
| `javac` (JDK) | Java compiler — catches type errors and undefined symbols |
| [scikit-learn](https://scikit-learn.org/) | RandomForest + CalibratedClassifierCV per-language ML models |
| [numpy](https://numpy.org/) | Feature arrays for model training and inference |

### DevOps
| Technology | Purpose |
|------------|---------|
| [Docker](https://www.docker.com/) | Containerised production build |
| [docker-compose](https://docs.docker.com/compose/) | Local multi-service dev stack |
| [Railway](https://railway.app/) / [Render](https://render.com/) | Backend deployment (via `Procfile`) |
| [Vercel](https://vercel.com/) | Frontend deployment |

---

## Features

### Code Review
- Multi-language support: Python, C++, Java (auto-detected from file extension or code hints)
- Syntax error detection with line numbers
- ML-based bug-risk confidence score (per-language calibrated RandomForest)
- Rule-based issue detection with fix suggestions
- Review score (0–100) shown per file

### Python Checks
- Infinite loop (`while True` without break)
- Division by zero
- Recursion without base case
- Nested loops (O(n²) risk)
- Input / sort inside loop
- Loop variable overwrite (e.g. `result = char` instead of `result += char`)
- Accumulator not accumulated inside for-loop
- Wrong argument count (too few/many args to user-defined functions)
- Mutable default argument (`def f(dp=[])`)
- Shadowing built-in names (`list`, `min`, `len`, etc.)
- `None` comparison with `==` instead of `is`
- `is` / `is not` used with non-singleton literals
- Float equality comparison (`== 0.1`)
- Nested loop variable shadowing (inner loop reuses outer loop variable)
- Unreachable code after `return`
- Missing `return` in one branch of if/else
- Modifying a collection while iterating over it
- Bare `except:` clause
- `return` inside `finally` block

### C++ Checks
- Compiler errors and warnings (via `g++`)
- Nested loops (O(n²) risk)
- Infinite loop (`while(true)`, `for(;;)`)
- Division by zero
- Assignment in condition (`if (x = 5)` instead of `if (x == 5)`)
- `std::endl` inside loop (flushes buffer every iteration — TLE risk)
- `pow()` result stored in `int`/`long` (floating-point truncation)
- Unsafe C functions (`gets`, `strcpy`)
- Mixed `printf`/`cout` without `sync_with_stdio(false)`
- Integer overflow risk (large constants assigned to `int`)
- Missing `break` in switch-case (fall-through)
- Empty catch block
- Possible memory leak (`new`/`malloc` without `delete`/`free`)
- Function missing return on all paths
- Recursion without base case
- Input / sort inside loop

### Java Checks
- Compiler errors and warnings (via `javac`)
- Nested loops (O(n²) risk)
- Infinite loop
- Division by zero
- Assignment in condition
- String compared with `==` instead of `.equals()`
- String concatenation in loop (use `StringBuilder`)
- Catching broad `Exception`
- Empty catch block
- Integer overflow risk (int multiplication)
- Missing `break` in switch-case
- Resource not closed (Scanner, BufferedReader — use try-with-resources)
- Possible NullPointerException (missing null check)
- Function missing return on all paths
- Recursion without base case
- Input / sort inside loop

### App Features
- Email/password signup and login (JWT auth)
- In-browser Monaco code editor with multi-tab workflow
- Drag-and-drop file upload
- Review history per user with score distribution chart
- Quick Fix button (applies fixes directly in the editor where possible)
- Dark mode UI

---

## Project Structure

```
safecodeai/
├── backend/                # FastAPI app — auth, DB models, review routes
│   ├── auth.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   └── routes/
│       └── review.py
├── frontend/               # Next.js UI
│   ├── app/
│   │   ├── dashboard/      # Main editor + review panel
│   │   ├── login/
│   │   └── signup/
│   └── components/
│       ├── ReviewPanel.tsx
│       ├── WorkspaceView.tsx
│       └── DocsView.tsx
├── src/                    # ML + static analysis engine
│   ├── predict.py          # Issue detectors (Python AST + C++/Java regex)
│   ├── model.py            # Model training
│   ├── features.py         # Feature extraction
│   ├── load_data.py        # Dataset loader
│   └── preprocess.py
├── datasets/               # Curated training data (JSONL)
├── bug_risk_model.pkl      # Trained per-language model artifact
├── Dockerfile              # Production Docker image
├── docker-compose.yml      # Local Docker dev stack
├── Procfile                # Railway / Render deployment
├── start-backend.bat       # Windows: start FastAPI
└── start-frontend.bat      # Windows: start Next.js
```

---

## Prerequisites

- Python 3.10+
- Node.js 18.17+ (20+ recommended)
- npm
- `g++` (for C++ compiler checks) — `sudo apt install g++` on Linux, included in Docker image
- `javac` (for Java compiler checks) — `sudo apt install default-jdk-headless` on Linux, included in Docker image

---

## Quick Start

### 1) Backend (FastAPI)

```bash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
set DATABASE_URL=sqlite:///./safecodeai.db   # Windows
uvicorn main:app --reload --reload-dir . --reload-dir ../src --port 8000
```

Health check: `http://localhost:8000/` | Swagger docs: `http://localhost:8000/docs`

### 2) Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` (may switch to `3002` if port is taken).

### Windows shortcuts

From repo root:

```bat
start-backend.bat
start-frontend.bat
```

---

## Environment Variables

### Frontend (`frontend/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend

```env
DATABASE_URL=sqlite:///./safecodeai.db      # dev default
JWT_SECRET_KEY=your-secret-key-here
CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:3002
```

See `.env.example` and `frontend/.env.example` for full reference.

---

## API Endpoints

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/signup` | Create account |
| `POST` | `/api/auth/login` | Login, returns JWT |
| `POST` | `/api/review` | Submit code for analysis (auth required) |
| `GET` | `/api/reviews` | Get review history (auth required) |

---

## Docker (Local Dev)

```bash
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
docker-compose up --build
```

Backend: `http://localhost:8000` | Frontend: `http://localhost:3000`

---

## Deployment

### Backend → Railway / Render

| Variable | Value |
|----------|-------|
| `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | Provided by the platform's Postgres plugin |
| `CORS_ALLOW_ORIGINS` | `https://your-app.vercel.app` |

### Frontend → Vercel

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://your-backend.railway.app` |

---

## Training a Model (Optional)

```bash
# 1. Build feature arrays from datasets/
python main.py --data-path datasets --languages python,cpp,java --max-files 200 --max-rows 200000

# 2. Train and save the model
python src/model.py --x-path X_features.npy --y-path y_labels.npy --langs-path language_labels.npy \
  --model-out bug_risk_model.pkl --metrics-out model_metrics.json
```

`main.py` accepts:
- `*.jsonl` files (CodeSearchNet-style)
- C++ source files (`.cpp`, `.cc`, `.cxx`, `.h`, `.hpp`)
- Java CSV datasets with a `snippet`, `scode`, or `code` column

Place `bug_risk_model.pkl` at the repo root. The backend supports both legacy pickles and the newer packaged artifact format. If a language has too few samples or only one class, it is skipped and reported in `model_metrics.json`.

---

## Data Storage

- SQLite (dev): `backend/safecodeai.db` — created automatically on first run
- PostgreSQL (prod): configured via `DATABASE_URL`
- Tables: `users`, `reviews`

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: psycopg2` | Set `DATABASE_URL=sqlite:///./safecodeai.db` before starting uvicorn |
| `401 Invalid token` | Sign out and log in again — JWT secret changed |
| CORS errors | Ensure backend is on port 8000; add your frontend URL to `CORS_ALLOW_ORIGINS` |
| Review works but score is always generic | Confirm `bug_risk_model.pkl` exists at repo root |
| C++ / Java compiler checks missing | Install `g++` and `javac` and ensure they are on PATH |
| Backend doesn't pick up `src/predict.py` changes | Restart uvicorn — the `--reload-dir ../src` watcher may miss external edits |
#   s a f e c o d e a i  
 