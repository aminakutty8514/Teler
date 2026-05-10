RUN pip install playwright && 

playwright install --with-deps chromium

COPY . .

CMD ["python", "bot.py"]
