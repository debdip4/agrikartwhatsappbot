# Use an official Python runtime
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install dependencies (add build tools only if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire app
COPY . .

# Expose the port used in app.py (make sure app.py uses port 5000 or change this)
EXPOSE 5000

# Start app using plain Python (Flask's built-in dev server)
CMD ["python", "app.py"]
