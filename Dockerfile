FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
COPY guildwatcher.py .

RUN pip install -r requirements.txt

CMD ["python", "guildwatcher.py"]