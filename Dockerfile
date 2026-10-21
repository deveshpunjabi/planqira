# Multi-stage production Dockerfile for Planqira
FROM python:3.12-slim AS runner

WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and static assets
COPY . .

# Expose port (Cloud Run standard: 8080)
EXPOSE 8080

# Start Planqira Precision Operations Engine
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
