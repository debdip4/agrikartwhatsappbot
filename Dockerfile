# Use an official Python runtime
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Command to run the Flask app using Gunicorn
# This looks for the 'app' variable inside your 'app.py' file
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
