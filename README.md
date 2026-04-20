![SafeCodeAI Banner](assets/banner.png)

# 🛡️ SafeCodeAI

**SafeCodeAI** is a state-of-the-art, local, full-stack AI-powered code review platform. Designed for developers and DSA practitioners, it provides instant, deep static analysis and bug risk prediction without ever sending your code to the cloud.

---

## ✨ Core Highlights

*   **🔍 Deep Analysis**: Over 30+ specialized bug detectors across Python, C++, and Java.
*   **🤖 ML-Powered**: Per-language calibrated RandomForest models provide high-confidence risk scores.
*   **💻 Local-First**: Complete privacy—your code remains on your machine.
*   **🛠️ Full-Stack**: Seamlessly integrated Next.js frontend, FastAPI backend, and a custom ML analysis engine.

---

## 🛠️ Technology Stack

### 🎨 Frontend
- **Framework**: [Next.js 14](https://nextjs.org/) (App Router)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **Editor**: [Monaco Editor](https://microsoft.github.io/monaco-editor/) (The engine behind VS Code)
- **Language**: [TypeScript](https://www.typescriptlang.org/)

### ⚡ Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (High-performance Python API)
- **Database**: [SQLAlchemy](https://www.sqlalchemy.org/) (SQLite for Dev, PostgreSQL ready)
- **Security**: JWT Authentication (python-jose + passlib)

### 🧠 Analysis Engine
- **Python**: AST-based static analysis (`ast` module)
- **C++/Java**: Compiler-integrated checks (`g++`, `javac`)
- **Machine Learning**: [scikit-learn](https://scikit-learn.org/) RandomForest with confidence calibration
- **Features**: Specialized extraction via `numpy`

---

## 🚀 Key Features

### 📡 Multi-Language Code Review
SafeCodeAI automatically detects your programming language and performs specialized checks:
- **Python**: Detects infinite loops, mutable defaults, unreachable code, shadowing, and more.
- **C++**: Identifies memory leaks, compiler warnings, unsafe C functions, and O(n²) risks.
- **Java**: Catches resource leaks, string comparison errors, and fall-through switch cases.

### 📊 Intelligence & UI
- **Risk Scoring**: Real-time 0–100 risk distribution charts.
- **Quick Fixes**: One-click remediation for common architectural and logical flaws.
- **History Tracking**: Maintain a full audit trail of your code review evolution.
- **Modern Workflow**: Multi-tab Monaco editor with drag-and-drop support.

---

## 📂 Project Structure

```text
safecodeai/
├── 🌐 backend/      # FastAPI REST API (Auth, DB, Logic)
├── 🎨 frontend/     # Next.js Modern UI & Monaco Workspace
├── 🧠 src/          # ML & Static Analysis Engine (Core)
├── 📊 datasets/     # Curated training data (JSONL/CSV)
├── 🐳 Dockerfile     # Production-ready containerization
└── 📜 README.md      # You are here!
```

---

## 🏁 Quick Start

### 📋 Prerequisites
- **Python**: 3.10+
- **Node.js**: 18.17+
- **Compilers**: `g++` and `javac` installed and on your PATH.

### 1. ⚡ Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
*Health Check: http://localhost:8000 | Docs: http://localhost:8000/docs*

### 2. 🎨 Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
*Visit: http://localhost:3000*

---

## 🐳 Docker Deployment
For a quick, isolated environment:
```bash
docker-compose up --build
```

---

## 🛡️ Security & Privacy
SafeCodeAI was built with a **"No-Cloud"** philosophy. All code analysis happens locally, ensuring that proprietary logic and sensitive algorithms never leave your internal network.

---

## 🤝 Contributing
Contributions are welcome! If you have a new bug detector or model optimization, feel free to open a PR.

---
<p align="center">
  Built with ❤️ by the SafeCodeAI Team
</p>