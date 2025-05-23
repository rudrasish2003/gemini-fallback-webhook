FROM python:3.10-slim

WORKDIR /app
COPY main.py .

# Add httpx to requirements
RUN pip install fastapi uvicorn httpx

EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
