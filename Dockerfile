FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN apt update && apt install -y chromium && rm -rf /var/lib/apt/lists/*
RUN pip install -r requirements.txt && playwright install chromium
CMD python playwright_login.py && python bot.py
