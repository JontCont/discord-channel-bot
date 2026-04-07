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

# Change ownership of the app directory to the non-root user
RUN chown -R botuser:botuser /app

# Switch to non-root user
USER botuser

# Run the bot
CMD ["python", "bot.py"]
