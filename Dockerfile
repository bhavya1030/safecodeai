FROM python:3.11-slim

# Install C++ and Java compilers for semantic code analysis
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    default-jdk-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

EXPOSE 8000

# Run from backend/ directory (main.py adds /app to sys.path for src/ imports)
WORKDIR /app/backend

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-1}"]
