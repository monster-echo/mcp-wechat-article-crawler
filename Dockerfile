FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the SSE port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HEADLESS=true

# Start the MCP server
CMD ["python", "-m", "src.server"]
