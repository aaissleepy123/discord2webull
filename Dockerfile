FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    curl wget unzip gnupg ca-certificates fonts-liberation \
    libnss3 libatk-bridge2.0-0 libxss1 libasound2 libx11-xcb1 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/google-chrome

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && python -m spacy download en_core_web_sm

COPY . /app
WORKDIR /app

CMD ["python", "full_trade_bot.py"]