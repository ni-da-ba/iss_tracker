FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY iss_tracker.py .

USER app
EXPOSE 5000

CMD ["python", "iss_tracker.py", "--host", "0.0.0.0", "--port", "5000"]
