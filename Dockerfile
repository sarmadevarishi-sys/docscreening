FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire repository
COPY . .

# Railway provides PORT automatically
EXPOSE 8080

# Start FastAPI
CMD sh -c "cd backend && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"