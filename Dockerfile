FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy your application code
COPY main.py .

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    httpx \
    beautifulsoup4 \
    lxml

# Expose port
EXPOSE 10000

# Run the FastAPI app using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
