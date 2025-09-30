FROM python:3.12-slim

# lint hint:
# docker run --rm -i hadolint/hadolint < Dockerfile
#
# rules:
# https://github.com/hadolint/hadolint?tab=readme-ov-file#rules

RUN apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements.txt

# hadolint ignore=DL3013
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY src/ src/

CMD ["python", "src/goodsecretarybot.py"]
