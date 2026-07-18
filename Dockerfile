FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    CODYSSEY_DB_PATH=/app/codyssey_coach.sqlite3

CMD ["python", "-m", "codyssey_coach.bot"]
