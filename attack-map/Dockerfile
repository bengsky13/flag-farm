FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copying all python files (including attack_crawler.py and parser.py)
COPY *.py .

CMD ["python", "attack_crawler.py"]