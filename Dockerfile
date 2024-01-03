FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libmagic1

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

ENV TELEGRAM_TOKEN='your telegram bot token here'
ENV OPENAI_API_KEY='your openai api key here'

CMD ["python", "goodsecretarybot.py"]