FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

COPY AI/wait-for-ollama.sh /wait-for-ollama.sh
RUN chmod +x /wait-for-ollama.sh

EXPOSE 8001

ENTRYPOINT ["/wait-for-ollama.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
