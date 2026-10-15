# Use official lightweight Python image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and templates
COPY . .

# Ensure data directory exists for DuckDB
RUN mkdir -p data

# Expose FastAPI port
EXPOSE 8080

# Run Uvicorn production server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]