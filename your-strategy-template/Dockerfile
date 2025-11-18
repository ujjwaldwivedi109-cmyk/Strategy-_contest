FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirement list first (for faster caching)
COPY requirements.txt .

# Install OS-level dependencies if needed (light to avoid rejection)
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot template files
COPY your_strategy.py .
COPY startup.py .

# Expose the dashboard port
EXPOSE 8000

# Run the trading bot
CMD ["python", "startup.py"]