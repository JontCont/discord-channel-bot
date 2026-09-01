# Use official Python slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Create a non-root user to run the bot
RUN useradd -m -u 1000 botuser

# Copy only requirements.txt first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Prepare writable runtime directories, then drop privileges permanently.
RUN mkdir -p /app/data /app/logs && chown -R botuser:botuser /app

USER botuser

CMD ["python", "bot.py"]
